from datetime import datetime
from typing import Optional
import asyncio
import logging
import uuid
import os
import boto3
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.models import (
    ArticleProcessRequest,
    ProcessArticleResponse,
    ArticleContent,
    AudioResponse,
    ProcessingStatus,
    ErrorResponse,
    HealthResponse,
    JobStartResponse,
    JobStatusResponse,
    DailyBriefResponse,
    DailyBriefsSummaryResponse
)
from app.services.extractor import ArticleExtractor
from app.services.llm_service import LLMService
from app.services.tts_service import TTSService
from app.services.job_storage import JobStorage
from app.services.audio_metadata_storage import AudioMetadataStorage
from app.core.config import get_settings
from app.auth.dependencies import get_current_user, get_user_id, get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# Initialize services
article_extractor = ArticleExtractor()
llm_service = LLMService()
tts_service = TTSService()
job_storage = JobStorage()  # DynamoDB-based job storage
audio_metadata_storage = AudioMetadataStorage()  # DynamoDB-based audio metadata storage

# Initialize DynamoDB client for news briefs
dynamodb = boto3.resource('dynamodb')
briefs_table_name = os.getenv('BRIEFS_TABLE', 'audifyy-briefs-dev')
briefs_table = dynamodb.Table(briefs_table_name)

# Initialize S3 client for generating presigned URLs
s3_client = boto3.client('s3')
audio_bucket_name = os.getenv('AUDIO_BUCKET', 'audifyy-news-audio-dev')

async def process_article_background(job_id: str, request: ArticleProcessRequest, user_id: str, job_storage: JobStorage):
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

        # Step 4: Enhance text for audio (only for summaries - full articles don't need enhancement)
        if request.mode == "summary":
            job_storage.update_job_status(job_id, "processing", 70, "Enhancing summary for audio...")
            try:
                enhanced_text = await llm_service.enhance_content_for_audio(final_text)
                final_text = enhanced_text
            except Exception as e:
                logger.warning(f"Audio enhancement failed, using original: {str(e)}")
                # Continue with non-enhanced text
        else:
            # Skip enhancement for full articles - OpenAI TTS handles natural speech well
            logger.info("Skipping LLM enhancement for full article - using original content")

        job_storage.update_job_status(job_id, "processing", 80, "Generating audio progressively...")

        # Step 5: Generate audio progressively (fast first chunk, background processing)
        try:
            audio_s3_key_or_path, audio_metadata = await tts_service.generate_audio_progressive(final_text, user_id)
        except Exception as e:
            logger.error(f"Progressive TTS generation failed: {str(e)}")
            job_storage.update_job_status(job_id, "error", 0, error=f"Failed to generate audio: {str(e)}")
            return

        # If progressive, update job with partial audio info
        if audio_metadata.get("progressive", False):
            job_storage.update_job_status(job_id, "processing", 90, "Audio available, continuing background processing...")
        else:
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

        # Create audio response with progressive metadata
        audio_response = AudioResponse(
            audio_id=audio_metadata["audio_id"],
            duration=None,  # Could calculate with audio analysis
            size=audio_metadata.get("size"),
            url=None,  # Will be generated on-demand via get_audio_url()
            s3_key=audio_metadata.get("s3_key"),
            storage=audio_metadata.get("storage", "unknown")
        )

        # Debug progressive metadata
        is_progressive = audio_metadata.get("progressive", False)
        logger.info(f"Audio metadata progressive flag: {is_progressive}")
        logger.info(f"Audio metadata keys: {list(audio_metadata.keys())}")

        progressive_audio_data = None
        if is_progressive:
            progressive_audio_data = {
                "is_progressive": True,
                "total_chunks": audio_metadata.get("total_chunks", 1),
                "completed_chunks": audio_metadata.get("completed_chunks", 1),
                "expected_durations": audio_metadata.get("expected_durations", [])
            }

        result = ProcessArticleResponse(
            success=True,
            article=article_content,
            audio=audio_response,
            error=None,
            # Add progressive audio metadata to result for frontend use
            progressive_audio=progressive_audio_data
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
async def process_article(
    request: ArticleProcessRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Start processing an article URL asynchronously.
    Returns a job_id immediately for status tracking.
    Requires authentication.
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job in DynamoDB and send to SQS with user_id
        request_data = {
            "url": str(request.url),
            "mode": request.mode
        }

        job_storage.create_job(job_id, request_data, user_id)

        logger.info(f"Started async processing for job {job_id} (user {user_id}): {request.url} (mode: {request.mode})")

        return JobStartResponse(
            job_id=job_id,
            status="started",
            estimated_time=60  # ~1 minute estimate
        )

    except Exception as e:
        logger.error(f"Failed to start article processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.get("/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_user_id)
):
    """Get the current status of a processing job. Requires authentication."""
    job_data = job_storage.get_job(job_id, user_id)

    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found or access denied")

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


@router.get("/audio/{audio_id}/url")
async def get_audio_url(
    audio_id: str,
    user_id: str = Depends(get_user_id)
):
    """Get presigned URL for audio file. Returns JSON with URL."""
    try:
        # Use TTS service to get the audio URL with user verification
        audio_url = tts_service.get_audio_url(audio_id, user_id)

        if not audio_url:
            raise HTTPException(status_code=404, detail="Audio file not found or access denied")

        return {"url": audio_url, "expires_in": 3600}

    except Exception as e:
        logger.error(f"Error getting audio URL {audio_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audio URL")


@router.get("/audio/{audio_id}")
async def stream_audio(
    audio_id: str,
    user_id: str = Depends(get_user_id)
):
    """Stream audio file by ID. Requires authentication and verifies user access."""
    try:
        # Use TTS service to get the audio URL with user verification
        audio_url = tts_service.get_audio_url(audio_id, user_id)

        if not audio_url:
            raise HTTPException(status_code=404, detail="Audio file not found or access denied")

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
        logger.error(f"Error streaming audio {audio_id} for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to stream audio")


@router.get("/audio/{audio_id}/progress")
async def get_audio_progress(
    audio_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get progressive audio generation status from DynamoDB.
    Returns file size and chunk completion info for seamless frontend transitions.
    """
    try:
        # Get audio metadata from DynamoDB
        metadata = audio_metadata_storage.get_audio_metadata(audio_id, user_id)

        if not metadata:
            raise HTTPException(status_code=404, detail="Audio metadata not found or access denied")

        # Get fresh audio URL for frontend
        audio_url = tts_service.get_audio_url(audio_id, user_id)
        if not audio_url:
            raise HTTPException(status_code=404, detail="Audio file not found or access denied")

        # Determine status based on completion
        status = "complete" if metadata['chunks_completed'] >= metadata['total_chunks'] else "growing"

        return {
            "audio_id": audio_id,
            "url": audio_url,
            "file_size": metadata['file_size'],
            "last_modified": metadata.get('updated_at'),
            "chunks_completed": metadata['chunks_completed'],
            "total_chunks": metadata['total_chunks'],
            "status": status,
            "message": f"Audio progress: {metadata['chunks_completed']}/{metadata['total_chunks']} chunks complete"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio progress for {audio_id} (user {user_id}): {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get audio progress")


@router.get("/my-articles")
async def get_my_articles(
    user_id: str = Depends(get_user_id),
    limit: int = 20,
    last_key: Optional[str] = None
):
    """
    Get all articles processed by the current user.
    Returns paginated results ordered by creation date (newest first).
    Requires authentication.
    """
    try:
        # Get user's jobs with pagination
        user_jobs_result = job_storage.get_user_jobs(user_id, limit, last_key)

        articles = []
        for job in user_jobs_result['jobs']:
            # Only include completed jobs with results
            if job.get('status') == 'completed' and job.get('result'):
                result = job['result']

                # Generate fresh presigned URL for audio if it exists
                audio_data = None
                if result.get('audio'):
                    audio_id = result.get('audio', {}).get('audio_id')
                    if audio_id:
                        # Generate presigned URL for this audio file
                        audio_url = tts_service.get_audio_url(audio_id, user_id)
                        audio_data = {
                            'audio_id': audio_id,
                            'size': result.get('audio', {}).get('size'),
                            'storage': result.get('audio', {}).get('storage'),
                            'url': audio_url  # Fresh presigned URL
                        }

                article_data = {
                    'job_id': job['job_id'],
                    'created_at': job['created_at'],
                    'updated_at': job['updated_at'],
                    'url': result.get('article', {}).get('url'),
                    'title': result.get('article', {}).get('title'),
                    'word_count': result.get('article', {}).get('word_count', 0),
                    'estimated_reading_time': result.get('article', {}).get('estimated_reading_time', 0),
                    'mode': 'summary' if result.get('article', {}).get('summary') else 'full',
                    'audio': audio_data
                }
                articles.append(article_data)

        return {
            'articles': articles,
            'pagination': {
                'limit': limit,
                'last_key': user_jobs_result.get('last_evaluated_key'),
                'has_more': bool(user_jobs_result.get('last_evaluated_key')),
                'total_returned': len(articles)
            }
        }

    except Exception as e:
        logger.error(f"Failed to get articles for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve articles")


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


@router.get("/briefs/latest")
async def get_latest_briefs(limit: int = 10):
    """
    Get the latest daily briefs for all categories.
    Returns 'limit' briefs per category, grouped by category.
    Public endpoint - no authentication required.
    """
    try:
        from boto3.dynamodb.conditions import Key

        categories = ["general-tech", "ai-ml", "devops-platform"]
        result = {}

        for category in categories:
            # Query briefs for this category, sorted by date DESC
            response = briefs_table.query(
                IndexName='category-date-index',
                KeyConditionExpression=Key('category').eq(category),
                ScanIndexForward=False,  # Descending order (newest first)
                Limit=limit
            )

            briefs_data = response.get('Items', [])
            briefs = []

            for brief in briefs_data:
                # Only include briefs with ready status
                if brief.get('status') != 'ready':
                    continue

                # Generate presigned URL if audio exists
                audio_url = None
                if brief.get('audio_url'):
                    s3_key = brief.get('audio_url').replace(f"s3://{audio_bucket_name}/", "") if brief.get('audio_url', '').startswith('s3://') else f"audio/{brief.get('category')}-{brief.get('date')}.mp3"

                    try:
                        audio_url = s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': audio_bucket_name, 'Key': s3_key},
                            ExpiresIn=3600
                        )
                    except Exception as e:
                        logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")

                # Format the brief title as "Brief - DD-MM-YY"
                date_obj = datetime.strptime(brief['date'], '%Y-%m-%d')
                title = f"Brief - {date_obj.strftime('%d-%m-%y')}"

                briefs.append({
                    'brief_id': brief['brief_id'],
                    'category': brief['category'],
                    'date': brief['date'],
                    'title': title,
                    'word_count': brief.get('word_count', 0),
                    'estimated_duration': brief.get('estimated_duration'),
                    'actual_duration': brief.get('actual_duration'),
                    'status': brief.get('status', 'generated'),
                    'audio_url': audio_url,
                    'audio_size': brief.get('audio_size'),
                    'articles_used': brief.get('articles_used', []),
                    'created_at': brief.get('created_at', ''),
                    'updated_at': brief.get('updated_at', '')
                })

            result[category] = briefs

        return result

    except Exception as e:
        logger.error(f"Failed to fetch latest briefs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch briefs")


@router.get("/briefs/category/{category}")
async def get_category_briefs(category: str, limit: int = 10, offset: int = 0):
    """
    Get paginated briefs for a specific category.
    Public endpoint - no authentication required.
    """
    try:
        from boto3.dynamodb.conditions import Key

        # Validate category
        valid_categories = ["general-tech", "ai-ml", "devops-platform"]
        if category not in valid_categories:
            raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")

        # Query briefs for this category, sorted by date DESC
        # Note: DynamoDB doesn't support offset directly, so we'll fetch offset + limit and slice
        fetch_limit = offset + limit + 1  # +1 to check if there are more

        response = briefs_table.query(
            IndexName='category-date-index',
            KeyConditionExpression=Key('category').eq(category),
            ScanIndexForward=False,  # Descending order (newest first)
            Limit=fetch_limit
        )

        all_items = response.get('Items', [])

        # Filter only ready briefs
        ready_items = [item for item in all_items if item.get('status') == 'ready']

        # Slice to get the requested page
        briefs_data = ready_items[offset:offset + limit]
        has_more = len(ready_items) > offset + limit

        briefs = []
        for brief in briefs_data:
            # Generate presigned URL if audio exists
            audio_url = None
            if brief.get('audio_url'):
                s3_key = brief.get('audio_url').replace(f"s3://{audio_bucket_name}/", "") if brief.get('audio_url', '').startswith('s3://') else f"audio/{brief.get('category')}-{brief.get('date')}.mp3"

                try:
                    audio_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': audio_bucket_name, 'Key': s3_key},
                        ExpiresIn=3600
                    )
                except Exception as e:
                    logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")

            # Format the brief title as "Brief - DD-MM-YY"
            date_obj = datetime.strptime(brief['date'], '%Y-%m-%d')
            title = f"Brief - {date_obj.strftime('%d-%m-%y')}"

            briefs.append({
                'brief_id': brief['brief_id'],
                'category': brief['category'],
                'date': brief['date'],
                'title': title,
                'word_count': brief.get('word_count', 0),
                'estimated_duration': brief.get('estimated_duration'),
                'actual_duration': brief.get('actual_duration'),
                'status': brief.get('status', 'generated'),
                'audio_url': audio_url,
                'audio_size': brief.get('audio_size'),
                'articles_used': brief.get('articles_used', []),
                'created_at': brief.get('created_at', ''),
                'updated_at': brief.get('updated_at', '')
            })

        return {
            'briefs': briefs,
            'has_more': has_more,
            'next_offset': offset + limit,
            'category': category,
            'count': len(briefs)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch briefs for category {category}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch briefs")


@router.get("/briefs/{date}")
async def get_briefs_by_date(date: str):
    """
    Get all briefs for a specific date (format: YYYY-MM-DD).
    Public endpoint - no authentication required.
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Query briefs for the specified date
        from boto3.dynamodb.conditions import Key
        response = briefs_table.query(
            IndexName='date-index',
            KeyConditionExpression=Key('date').eq(date)
        )

        briefs_data = response.get('Items', [])

        # Process and return briefs
        briefs = []
        for brief in briefs_data:
            # Generate presigned URL if audio exists
            audio_url = None
            if brief.get('audio_url') and brief.get('status') == 'ready':
                s3_key = brief.get('audio_url').replace(f"s3://{audio_bucket_name}/", "") if brief.get('audio_url', '').startswith('s3://') else f"audio/{brief.get('category')}-{brief.get('date')}.mp3"

                try:
                    audio_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': audio_bucket_name, 'Key': s3_key},
                        ExpiresIn=3600
                    )
                except Exception as e:
                    logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")

            # Format the brief title as "Brief - DD-MM-YY"
            date_obj = datetime.strptime(brief['date'], '%Y-%m-%d')
            title = f"Brief - {date_obj.strftime('%d-%m-%y')}"

            briefs.append(DailyBriefResponse(
                brief_id=brief['brief_id'],
                category=brief['category'],
                date=brief['date'],
                title=title,
                content=brief.get('content'),
                word_count=brief.get('word_count', 0),
                estimated_duration=brief.get('estimated_duration'),
                actual_duration=brief.get('actual_duration'),
                status=brief.get('status', 'generated'),
                audio_url=audio_url,
                audio_size=brief.get('audio_size'),
                articles_used=brief.get('articles_used', []),
                created_at=brief.get('created_at', ''),
                updated_at=brief.get('updated_at', '')
            ))

        return {"briefs": briefs, "date": date, "count": len(briefs)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch briefs for date {date}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch briefs")


@router.get("/briefs/{category}/{date}")
async def get_brief_by_category_and_date(category: str, date: str):
    """
    Get a specific brief by category and date.
    Public endpoint - no authentication required.
    """
    try:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        # Query the brief
        composite_key = f"{category}#{date}"
        response = briefs_table.get_item(Key={'composite_key': composite_key})

        brief = response.get('Item')
        if not brief:
            raise HTTPException(status_code=404, detail=f"No brief found for category '{category}' on {date}")

        # Generate presigned URL if audio exists
        audio_url = None
        if brief.get('audio_url') and brief.get('status') == 'ready':
            s3_key = brief.get('audio_url').replace(f"s3://{audio_bucket_name}/", "") if brief.get('audio_url', '').startswith('s3://') else f"audio/{brief.get('category')}-{brief.get('date')}.mp3"

            try:
                audio_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': audio_bucket_name, 'Key': s3_key},
                    ExpiresIn=3600
                )
            except Exception as e:
                logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")

        # Format the brief title as "Brief - DD-MM-YY"
        date_obj = datetime.strptime(brief['date'], '%Y-%m-%d')
        title = f"Brief - {date_obj.strftime('%d-%m-%y')}"

        return DailyBriefResponse(
            brief_id=brief['brief_id'],
            category=brief['category'],
            date=brief['date'],
            title=title,
            content=brief.get('content'),
            word_count=brief.get('word_count', 0),
            estimated_duration=brief.get('estimated_duration'),
            actual_duration=brief.get('actual_duration'),
            status=brief.get('status', 'generated'),
            audio_url=audio_url,
            audio_size=brief.get('audio_size'),
            articles_used=brief.get('articles_used', []),
            created_at=brief.get('created_at', ''),
            updated_at=brief.get('updated_at', '')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch brief for {category} on {date}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch brief")