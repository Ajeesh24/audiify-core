from datetime import datetime
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Import Mangum for Lambda compatibility
try:
    from mangum import Mangum
except ImportError:
    Mangum = None

from app.core.config import get_settings
from app.api.routes import router

# Configure logging with environment variable support
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Override any existing logging configuration
)

# Set up root logger for Lambda
root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, log_level, logging.INFO))

# Ensure handlers are properly configured for CloudWatch
if not root_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(handler)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured at level: {log_level}")

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Audifyy API server...")

    # Verify required API keys
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured - TTS functionality will be disabled")

    # Install Playwright browsers if needed
    try:
        import playwright
        logger.info("Playwright available for web scraping")
    except ImportError:
        logger.warning("Playwright not available - some article extraction may fail")

    yield

    # Shutdown
    logger.info("Shutting down Audifyy API server...")


# Create FastAPI app
app = FastAPI(
    title="Audifyy API",
    description="Convert articles to audio with AI-powered summarization",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "audifyy.com", "*.audifyy.com"]
    )

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests."""
    start_time = datetime.now()

    response = await call_next(request)

    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"{response.status_code} - {process_time:.3f}s"
    )

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return HTTPException(
        status_code=500,
        detail="Internal server error"
    )


# Apply rate limiting to routes
@app.get("/")
@limiter.limit(f"{settings.rate_limit_requests}/hour")
async def root(request: Request):
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Audifyy API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Documentation disabled in production",
        "endpoints": {
            "health": "/api/health",
            "process_article": "/api/process-article",
            "stream_audio": "/api/audio/{audio_id}",
            "validate_url": "/api/validate-url",
            "voices": "/api/voices",
            "estimate_cost": "/api/estimate-cost"
        }
    }


# Apply rate limiting to all API routes
@app.middleware("http")
async def apply_rate_limiting(request: Request, call_next):
    """Apply rate limiting to API routes."""
    if request.url.path.startswith("/api/"):
        # Check rate limit
        try:
            # This is handled by the SlowAPIMiddleware, but we can add custom logic here
            pass
        except RateLimitExceeded:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_requests} requests per hour"
            )

    response = await call_next(request)
    return response


# Include API routes
app.include_router(router, prefix="/api", tags=["api"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )

# Lambda handler for AWS Lambda deployment
# Check if running in Lambda environment
if Mangum and os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    # Disable lifespan events for Lambda (they don't work well with cold starts)
    app_for_lambda = FastAPI(
        title="Audifyy API",
        description="Convert articles to audio with AI-powered summarization",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        # No lifespan for Lambda
    )

    # Add the same middleware and routes
    app_for_lambda.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # Simplified rate limiting for Lambda
    limiter_lambda = Limiter(key_func=get_remote_address)
    app_for_lambda.state.limiter = limiter_lambda

    # Add routes
    app_for_lambda.include_router(router, prefix="/api", tags=["api"])

    # Root endpoint
    @app_for_lambda.get("/")
    async def lambda_root():
        """Root endpoint with API information."""
        return {
            "message": "Welcome to Audifyy API (Lambda)",
            "version": "1.0.0",
            "runtime": "AWS Lambda",
            "endpoints": {
                "health": "/api/health",
                "process_article": "/api/process-article",
                "stream_audio": "/api/audio/{audio_id}",
                "validate_url": "/api/validate-url",
                "voices": "/api/voices",
                "estimate_cost": "/api/estimate-cost"
            }
        }

    # Create hybrid Lambda handler for both HTTP and SQS events
    mangum_handler = Mangum(app_for_lambda, lifespan="off")

    def lambda_handler(event, context):
        """
        Hybrid Lambda handler that routes HTTP and SQS events appropriately.
        """
        import json
        import asyncio

        # Check if this is an SQS event
        if 'Records' in event and len(event['Records']) > 0:
            # This is an SQS event - process background job
            logger.info(f"Processing SQS event with {len(event['Records'])} records")

            async def process_sqs_records():
                for record in event['Records']:
                    if record.get('eventSource') == 'aws:sqs':
                        try:
                            # Parse SQS message
                            message_body = json.loads(record['body'])
                            job_id = message_body['job_id']
                            user_id = message_body['user_id']  # Extract user_id
                            request_data = message_body['request_data']

                            logger.info(f"Processing background job {job_id} for user {user_id}")

                            # Import here to avoid circular imports
                            from app.services.job_storage import JobStorage
                            from app.models import ArticleProcessRequest

                            # Process the job
                            job_storage = JobStorage()
                            request = ArticleProcessRequest(**request_data)

                            # Import background processing function
                            from app.api.routes import process_article_background

                            # Process in background with user_id
                            await process_article_background(job_id, request, user_id, job_storage)

                        except Exception as e:
                            logger.error(f"Failed to process SQS record: {str(e)}")
                            raise

            # Create new event loop for SQS processing only
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run SQS processing
            loop.run_until_complete(process_sqs_records())
            return {"statusCode": 200, "body": "SQS events processed"}

        else:
            # This is an HTTP event - use Mangum (handles its own event loop)
            return mangum_handler(event, context)
else:
    # Create a dummy handler for non-Lambda environments
    def lambda_handler(event, context):
        return {
            "statusCode": 500,
            "body": "Not running in Lambda environment"
        }