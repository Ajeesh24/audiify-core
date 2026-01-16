from typing import Optional, Literal, Dict, List, Any
from pydantic import BaseModel, HttpUrl, Field


class ProgressiveAudioMetadata(BaseModel):
    """Progressive audio metadata for frontend use."""
    is_progressive: bool = Field(..., description="Whether this audio is being generated progressively")
    total_chunks: int = Field(..., description="Total number of chunks")
    completed_chunks: int = Field(..., description="Number of completed chunks")
    expected_durations: List[int] = Field(..., description="Expected duration for each chunk in seconds")


class ArticleProcessRequest(BaseModel):
    """Request model for article processing."""
    url: HttpUrl = Field(..., description="Article URL to process")
    mode: Literal["full", "summary"] = Field(..., description="Processing mode")


class ProcessingStatus(BaseModel):
    """Processing status response."""
    status: Literal["processing", "completed", "error"] = Field(..., description="Processing status")
    step: Optional[str] = Field(None, description="Current processing step")
    progress: int = Field(0, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")


class ArticleContent(BaseModel):
    """Article content response."""
    title: Optional[str] = Field(None, description="Article title")
    content: str = Field(..., description="Cleaned article content")
    summary: Optional[str] = Field(None, description="Article summary (if summary mode)")
    word_count: int = Field(..., description="Word count of processed content")
    estimated_reading_time: int = Field(..., description="Estimated reading time in minutes")


class AudioResponse(BaseModel):
    """Audio generation response."""
    audio_id: str = Field(..., description="Unique audio identifier")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    size: Optional[int] = Field(None, description="Audio file size in bytes")
    url: Optional[str] = Field(None, description="Audio file URL (S3 presigned or API endpoint)")
    s3_key: Optional[str] = Field(None, description="S3 object key if stored in S3")
    storage: Optional[str] = Field(None, description="Storage type: 's3' or 'local'")
    expires_at: Optional[str] = Field(None, description="URL expiration time (for presigned URLs)")


class ProcessArticleResponse(BaseModel):
    """Complete article processing response."""
    success: bool = Field(..., description="Processing success status")
    article: Optional[ArticleContent] = Field(None, description="Article content")
    audio: Optional[AudioResponse] = Field(None, description="Audio information")
    error: Optional[str] = Field(None, description="Error message if failed")
    progressive_audio: Optional[ProgressiveAudioMetadata] = Field(None, description="Progressive audio metadata for frontend")


class JobStartResponse(BaseModel):
    """Response when starting an async job."""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: str = Field(default="started", description="Job status")
    estimated_time: int = Field(default=60, description="Estimated completion time in seconds")


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str = Field(..., description="Job identifier")
    status: Literal["started", "processing", "completed", "error"] = Field(..., description="Current job status")
    progress: int = Field(0, description="Progress percentage (0-100)")
    step: Optional[str] = Field(None, description="Current processing step")
    result: Optional[ProcessArticleResponse] = Field(None, description="Final result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: Optional[str] = Field(None, description="Job creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[dict] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")


class DailyBriefResponse(BaseModel):
    """Daily brief response model."""
    brief_id: str = Field(..., description="Unique brief identifier")
    category: str = Field(..., description="Brief category (general-tech, ai-ml, devops-platform)")
    date: str = Field(..., description="Brief date in YYYY-MM-DD format")
    title: str = Field(..., description="Brief title")
    content: Optional[str] = Field(None, description="Brief text content")
    word_count: int = Field(..., description="Word count")
    estimated_duration: Optional[int] = Field(None, description="Estimated audio duration in seconds")
    actual_duration: Optional[int] = Field(None, description="Actual audio duration in seconds")
    status: str = Field(..., description="Brief status (generated, ready)")
    audio_url: Optional[str] = Field(None, description="S3 presigned URL for audio file")
    audio_size: Optional[int] = Field(None, description="Audio file size in bytes")
    articles_used: List[str] = Field(default_factory=list, description="List of article URLs used in this brief")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class DailyBriefsSummaryResponse(BaseModel):
    """Summary of all daily briefs for a specific date."""
    date: str = Field(..., description="Brief date in YYYY-MM-DD format")
    total_briefs: int = Field(..., description="Total number of briefs")
    ready_briefs: int = Field(..., description="Number of ready briefs")
    categories: Dict[str, Any] = Field(..., description="Brief details by category")
    total_duration: int = Field(0, description="Total audio duration in seconds")
    total_articles_used: int = Field(0, description="Total articles used across all briefs")