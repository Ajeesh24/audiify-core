from datetime import datetime
from typing import Optional
import asyncio
import logging
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.responses import JSONResponse

from app.models import (
    ArticleProcessRequest,
    ProcessArticleResponse,
    ArticleContent,
    AudioResponse,
    ProcessingStatus,
    ErrorResponse,
    HealthResponse,
    JobStartResponse,
    JobStatusResponse
)
from app.services.extractor import ArticleExtractor
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.job_storage import JobStorage
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Initialize services
article_extractor = ArticleExtractor()
llm_service = LLMService()
tts_service = TTSService()
job_storage = JobStorage()  # DynamoDB-based job storage

async def process_article_background(job_id: str, request: ArticleProcessRequest, job_storage: JobStorage):
    """Background task to process article asynchronously."""
    try:
        job_storage.update_job_status(job_id, "processing", 10, "Validating URL...")

        # Validate URL first
        is_valid = await article_extractor.validate_url(str(request.url))
        if not is_valid:
            job_storage.update_job_status(job_id, "error", 0, error="Invalid or inaccessible URL")
            return

        job_storage.update_job_status(job_id, "processing", 20, "Extracting article content...")

        # Step 1: Extract article content
        try:
            title, raw_content, is_paywalled = await article_extractor.extract_article(str(request.url))
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            job_storage.update_job_status(job_id, "error", 0, error=f"Failed to extract article content: {str(e)}")
            return

        if is_paywalled:
            job_storage.update_job_status(job_id, "error", 0, error="Article appears to be behind a paywall or requires subscription")
            return

        job_storage.update_job_status(job_id, "processing", 30, "Cleaning content...")

        # Step 2: Clean content
        cleaned_content = article_extractor.clean_content(raw_content)

        if len(cleaned_content.strip()) < 100:
            job_storage.update_job_status(job_id, "error", 0, error="Insufficient article content found after cleaning")
            return

        job_storage.update_job_status(job_id, "processing", 40, "Processing content...")

        # Step 3: Process based on mode
        final_text = cleaned_content
        summary = None

        if request.mode == "summary":
            job_storage.update_job_status(job_id, "processing", 50, "Generating summary...")
            try:
                summary = await llm_service.summarize_article(title, cleaned_content)
                final_text = summary
            except Exception as e:
                logger.error(f"Summarization failed: {str(e)}")
                job_storage.update_job_status(job_id, "error", 0, error=f"Failed to generate summary: {str(e)}")
                return

        job_storage.update_job_status(job_id, "processing", 70, "Enhancing content for audio...")

        # Step 4: Enhance text for audio (optional)
        try:
            enhanced_text = await llm_service.enhance_content_for_audio(final_text)
            final_text = enhanced_text
        except Exception as e:
            logger.warning(f"Audio enhancement failed, using original: {str(e)}")
            # Continue with non-enhanced text

        job_storage.update_job_status(job_id, "processing", 80, "Generating audio...")

        # Step 5: Generate audio
        try:
            audio_url, audio_metadata = await tts_service.generate_audio(final_text)
        except Exception as e:
            logger.error(f"TTS generation failed: {str(e)}")
            job_storage.update_job_status(job_id, "error", 0, error=f"Failed to generate audio: {str(e)}")
            return

        job_storage.update_job_status(job_id, "processing", 95, "Finalizing...")

        # Calculate metadata
        word_count = len(final_text.split())
        reading_time = article_extractor.calculate_reading_time(final_text)

        # Build response
        article_content = ArticleContent(
            title=title,
            content=cleaned_content,
            summary=summary if request.mode == "summary" else None,
            word_count=word_count,
            estimated_reading_time=reading_time
        )

        # Create audio response with S3 or local URL information
        audio_response = AudioResponse(
            audio_id=audio_metadata["audio_id"],
            duration=None,  # Could calculate with audio analysis
            size=audio_metadata.get("size"),
            url=audio_url,  # S3 URL or local path
            s3_key=audio_metadata.get("s3_key"),
            storage=audio_metadata.get("storage", "unknown")
        )

        result = ProcessArticleResponse(
            success=True,
            article=article_content,
            audio=audio_response,
            error=None
        )

        job_storage.update_job_status(job_id, "completed", 100, "Processing complete!", result=result)

        # Schedule cleanup of old files
        asyncio.create_task(cleanup_old_files_async())

    except Exception as e:
        logger.error(f"Unexpected error processing article: {str(e)}")
        job_storage.update_job_status(job_id, "error", 0, error=f"Internal server error: {str(e)}")

async def cleanup_old_files_async():
    """Async wrapper for cleanup."""
    try:
        tts_service.cleanup_old_files(24)
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@router.post("/validate-url")
async def validate_url(request: dict):
    """Validate if a URL is accessible and suitable for article extraction."""
    url = request.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        is_valid = await article_extractor.validate_url(url)
        return {"valid": is_valid, "url": url}
    except Exception as e:
        logger.error(f"URL validation error: {str(e)}")
        return {"valid": False, "url": url, "error": str(e)}


@router.post("/process-article", response_model=JobStartResponse)
async def process_article(request: ArticleProcessRequest):
    """
    Start processing an article URL asynchronously.
    Returns a job_id immediately for status tracking.
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job in DynamoDB and send to SQS
        request_data = {
            "url": str(request.url),
            "mode": request.mode
        }

        job_storage.create_job(job_id, request_data)

        logger.info(f"Started async processing for job {job_id}: {request.url} (mode: {request.mode})")

        return JobStartResponse(
            job_id=job_id,
            status="started",
            estimated_time=60  # ~1 minute estimate
        )

    except Exception as e:
        logger.error(f"Failed to start article processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.get("/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the current status of a processing job."""
    job_data = job_storage.get_job(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_data["job_id"],
        status=job_data["status"],
        progress=job_data["progress"],
        step=job_data["step"],
        result=job_data["result"],
        error=job_data["error"],
        created_at=job_data["created_at"],
        updated_at=job_data["updated_at"]
    )


@router.get("/audio/{audio_id}")
async def stream_audio(audio_id: str):
    """Stream audio file by ID (supports both S3 and local storage)."""
    try:
        # Use TTS service to get the audio URL (handles S3 and local)
        audio_url = tts_service.get_audio_url(audio_id)

        if not audio_url:
            raise HTTPException(status_code=404, detail="Audio file not found")

        # If it's an S3 presigned URL, redirect to it
        if audio_url.startswith('http'):
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=audio_url)

        # If it's a local file path, stream it
        if os.path.exists(audio_url):
            # Determine content type
            if audio_url.endswith('.mp3'):
                media_type = "audio/mpeg"
            elif audio_url.endswith('.wav'):
                media_type = "audio/wav"
            elif audio_url.endswith('.opus'):
                media_type = "audio/opus"
            else:
                media_type = "audio/mpeg"

            # Stream the local file
            return StreamingResponse(
                tts_service.stream_audio(audio_url),
                media_type=media_type,
                headers={"Accept-Ranges": "bytes"}
            )
        else:
            raise HTTPException(status_code=404, detail="Audio file not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming audio {audio_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stream audio")


@router.get("/voices")
async def get_available_voices():
    """Get available TTS voices."""
    return {"voices": tts_service.get_available_voices()}


@router.post("/estimate-cost")
async def estimate_processing_cost(request: dict):
    """Estimate the cost of processing an article."""
    text_length = request.get("text_length", 0)
    mode = request.get("mode", "full")

    if text_length <= 0:
        raise HTTPException(status_code=400, detail="Valid text_length required")

    # Estimate LLM cost (if summary mode)
    llm_cost = 0
    if mode == "summary":
        # Rough estimate: $0.001 per 1K tokens for GPT-3.5-turbo
        estimated_tokens = text_length // 4  # ~4 chars per token
        llm_cost = (estimated_tokens / 1000) * 0.001

    # Estimate TTS cost
    tts_cost = tts_service.estimate_cost(
        "x" * (text_length // 3 if mode == "summary" else text_length)
    )

    total_cost = llm_cost + tts_cost

    return {
        "estimated_cost": {
            "llm": llm_cost,
            "tts": tts_cost,
            "total": total_cost
        },
        "currency": "USD",
        "mode": mode,
        "text_length": text_length
    }