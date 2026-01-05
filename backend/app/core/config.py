import os
import json
from typing import Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


def load_openai_key() -> Optional[str]:
    """Load OpenAI API key from environment or SSM Parameter Store."""
    # First try direct environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # If running in Lambda, try to load from SSM Parameter Store
    parameter_name = os.getenv("OPENAI_API_KEY_PARAMETER")
    if parameter_name and os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        try:
            import boto3
            ssm = boto3.client('ssm')
            response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
            return response['Parameter']['Value']
        except Exception as e:
            print(f"Failed to load API key from SSM: {e}")
            return None

    return None


class Settings(BaseSettings):
    """Application settings and configuration."""

    # App settings
    app_name: str = Field(default="Audifyy API", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host address")
    port: int = Field(default=8000, description="Port number")

    # API Keys - loaded dynamically
    openai_api_key: Optional[str] = Field(default_factory=load_openai_key, description="OpenAI API key")
    elevenlabs_api_key: Optional[str] = Field(default=None, description="ElevenLabs API key")

    # Redis settings (not used in Lambda)
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    redis_ttl: int = Field(default=86400, description="Redis TTL in seconds (24h)")

    # Rate limiting
    rate_limit_requests: int = Field(default=10, description="Requests per hour per IP")
    rate_limit_window: int = Field(default=3600, description="Rate limit window in seconds")

    # Processing settings
    max_article_length: int = Field(default=50000, description="Maximum article length in characters")
    max_summary_length: int = Field(default=2000, description="Maximum summary length in characters")

    # CORS settings - handle both string and list for Lambda environment
    cors_origins: Union[str, list] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "https://audifyy.com"],
        description="Allowed CORS origins"
    )

    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string if needed."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return [v]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings