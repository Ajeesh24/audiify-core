from typing import Optional, Literal
from pydantic import BaseModel, HttpUrl, Field


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


class ProcessArticleResponse(BaseModel):
    """Complete article processing response."""
    success: bool = Field(..., description="Processing success status")
    article: Optional[ArticleContent] = Field(None, description="Article content")
    audio: Optional[AudioResponse] = Field(None, description="Audio information")
    error: Optional[str] = Field(None, description="Error message if failed")


class JobStartResponse(BaseModel):
    """Response when starting an async job."""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: str = Field(default="started", description="Job status")
    estimated_time: int = Field(default=60, description="Estimated completion time in seconds")


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str = Field(..., description="Job identifier")
    status: Literal["processing", "completed", "error"] = Field(..., description="Current job status")
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