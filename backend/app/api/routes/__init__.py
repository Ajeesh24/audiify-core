from datetime import datetime
from typing import Optional
import asyncio
import logging
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
    HealthResponse
)
from app.services.extractor import ArticleExtractor
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Initialize services
article_extractor = ArticleExtractor()
llm_service = LLMService()
tts_service = TTSService()

# In-memory store for processing status (in production, use Redis)
processing_status = {}


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


@router.post("/process-article", response_model=ProcessArticleResponse)
async def process_article(
    request: ArticleProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Process an article URL and generate audio.
    This is the main endpoint that orchestrates the entire pipeline.
    """
    try:
        # Validate URL first
        is_valid = await article_extractor.validate_url(str(request.url))
        if not is_valid:
            return ProcessArticleResponse(
                success=False,
                error="Invalid or inaccessible URL"
            )

        # Start processing
        logger.info(f"Processing article: {request.url} (mode: {request.mode})")

        # Step 1: Extract article content
        try:
            title, raw_content, is_paywalled = await article_extractor.extract_article(str(request.url))
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return ProcessArticleResponse(
                success=False,
                error=f"Failed to extract article content: {str(e)}"
            )

        if is_paywalled:
            return ProcessArticleResponse(
                success=False,
                error="Article appears to be behind a paywall or requires subscription"
            )

        # Step 2: Clean content
        cleaned_content = article_extractor.clean_content(raw_content)

        if len(cleaned_content.strip()) < 100:
            return ProcessArticleResponse(
                success=False,
                error="Insufficient article content found after cleaning"
            )

        # Step 3: Process based on mode
        final_text = cleaned_content
        summary = None

        if request.mode == "summary":
            try:
                summary = await llm_service.summarize_article(title, cleaned_content)
                final_text = summary
            except Exception as e:
                logger.error(f"Summarization failed: {str(e)}")
                return ProcessArticleResponse(
                    success=False,
                    error=f"Failed to generate summary: {str(e)}"
                )

        # Step 4: Enhance text for audio (optional)
        try:
            enhanced_text = await llm_service.enhance_content_for_audio(final_text)
            final_text = enhanced_text
        except Exception as e:
            logger.warning(f"Audio enhancement failed, using original: {str(e)}")
            # Continue with non-enhanced text

        # Step 5: Generate audio
        try:
            audio_path, audio_metadata = await tts_service.generate_audio(final_text)
        except Exception as e:
            logger.error(f"TTS generation failed: {str(e)}")
            return ProcessArticleResponse(
                success=False,
                error=f"Failed to generate audio: {str(e)}"
            )

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

        audio_response = AudioResponse(
            audio_id=audio_metadata["audio_id"],
            duration=None,  # Could calculate with audio analysis
            size=audio_metadata.get("size")
        )

        # Schedule cleanup of old files
        background_tasks.add_task(tts_service.cleanup_old_files, 24)

        return ProcessArticleResponse(
            success=True,
            article=article_content,
            audio=audio_response,
            error=None
        )

    except Exception as e:
        logger.error(f"Unexpected error processing article: {str(e)}")
        return ProcessArticleResponse(
            success=False,
            error=f"Internal server error: {str(e)}"
        )


@router.get("/audio/{audio_id}")
async def stream_audio(audio_id: str):
    """Stream audio file by ID."""
    try:
        # Find the audio file
        import os
        import tempfile

        temp_dir = tempfile.gettempdir()

        # Clean the audio_id - remove "audio_" prefix if present
        clean_audio_id = audio_id.replace("audio_", "")
        audio_files = [f for f in os.listdir(temp_dir) if f.startswith(f"audio_{clean_audio_id}")]

        if not audio_files:
            raise HTTPException(status_code=404, detail="Audio file not found")

        audio_path = os.path.join(temp_dir, audio_files[0])

        if not os.path.exists(audio_path):
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Determine content type
        if audio_path.endswith('.mp3'):
            media_type = "audio/mpeg"
        elif audio_path.endswith('.wav'):
            media_type = "audio/wav"
        elif audio_path.endswith('.opus'):
            media_type = "audio/opus"
        else:
            media_type = "audio/mpeg"

        # Stream the file
        return StreamingResponse(
            tts_service.stream_audio(audio_path),
            media_type=media_type,
            headers={"Accept-Ranges": "bytes"}
        )

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