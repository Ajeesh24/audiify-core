"""
OpenAI TTS Service for News Agency Audio Generation

Simplified version of backend TTS service for brief-to-audio conversion
"""

import hashlib
import boto3
from openai import OpenAI
import logging
from typing import Dict, Any, List

from config import OPENAI_SETTINGS, S3_SETTINGS

logger = logging.getLogger(__name__)


class TTSService:
    """Service for text-to-speech conversion using OpenAI TTS."""

    def __init__(self):
        """Initialize TTS service."""
        if not OPENAI_SETTINGS['api_key']:
            raise ValueError("OpenAI API key not configured")

        self.client = OpenAI(api_key=OPENAI_SETTINGS['api_key'])

        # Initialize S3 client for audio storage
        self.s3_client = boto3.client('s3')
        self.s3_bucket = S3_SETTINGS.get('bucket_name', '')

    def generate_brief_audio(
        self,
        text: str,
        category: str,
        date: str,
        voice: str = "alloy",
        model: str = "tts-1"
    ) -> Dict[str, Any]:
        """
        Generate audio from brief text using OpenAI TTS.

        Args:
            text: Brief text to convert to speech
            category: Brief category (for S3 key organization)
            date: Date for organization
            voice: OpenAI voice (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 or tts-1-hd)

        Returns:
            Dict with audio_url, duration, size, and metadata
        """
        try:
            # Generate unique audio ID
            content_hash = hashlib.md5(f"{text}{voice}{model}".encode()).hexdigest()
            audio_id = f"brief_{category}_{date}_{content_hash[:8]}"
            audio_filename = f"{audio_id}.mp3"

            # S3 key: audio/briefs/{date}/{category}/filename
            s3_key = f"audio/briefs/{date}/{category}/{audio_filename}"

            logger.info(f"Generating audio for {category} brief: {audio_id}")

            # Check if already exists in S3 (caching)
            if self._audio_exists_in_s3(s3_key):
                logger.info(f"Using cached audio: {audio_id}")
                audio_url = self._get_s3_url(s3_key)
                return {
                    'audio_url': audio_url,
                    'audio_id': audio_id,
                    's3_key': s3_key,
                    'cached': True,
                    'duration': self._estimate_duration(text),
                    'size': 0  # Unknown for cached
                }

            # Generate audio with OpenAI TTS
            audio_data = self._generate_audio_with_openai(text, voice, model)

            # Upload to S3
            audio_url = self._upload_to_s3(audio_data, s3_key)

            # Calculate metadata
            duration = self._estimate_duration(text)
            size = len(audio_data)

            logger.info(f"Generated audio: {audio_id} ({size} bytes, ~{duration}s)")

            return {
                'audio_url': audio_url,
                'audio_id': audio_id,
                's3_key': s3_key,
                'cached': False,
                'duration': duration,
                'size': size
            }

        except Exception as e:
            logger.error(f"Error generating brief audio: {str(e)}")
            raise Exception(f"Failed to generate audio: {str(e)}")

    def _generate_audio_with_openai(self, text: str, voice: str, model: str) -> bytes:
        """Generate audio using OpenAI TTS API."""
        try:
            # Split text if too long (OpenAI limit: 4096 characters)
            chunks = self._split_text(text, max_length=4000)

            if len(chunks) == 1:
                # Single chunk
                response = self.client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=text
                )
                return response.content
            else:
                # Multiple chunks - combine audio
                logger.info(f"Splitting into {len(chunks)} chunks for TTS")
                audio_chunks = []

                for i, chunk in enumerate(chunks):
                    logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                    response = self.client.audio.speech.create(
                        model=model,
                        voice=voice,
                        input=chunk
                    )
                    audio_chunks.append(response.content)

                # Simple concatenation (works for MP3)
                return b''.join(audio_chunks)

        except Exception as e:
            logger.error(f"OpenAI TTS error: {str(e)}")
            raise

    def _split_text(self, text: str, max_length: int = 4000) -> List[str]:
        """Split long text into chunks suitable for TTS."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_pos = 0

        while current_pos < len(text):
            end_pos = min(current_pos + max_length, len(text))

            if end_pos == len(text):
                chunks.append(text[current_pos:end_pos])
                break

            # Find sentence boundary
            chunk_text = text[current_pos:end_pos]
            for delimiter in ['. ', '! ', '? ', '\n\n']:
                last_delimiter = chunk_text.rfind(delimiter)
                if last_delimiter > len(chunk_text) * 0.7:
                    end_pos = current_pos + last_delimiter + len(delimiter.strip())
                    break

            chunks.append(text[current_pos:end_pos].strip())
            current_pos = end_pos

        return [chunk for chunk in chunks if chunk.strip()]

    def _upload_to_s3(self, audio_data: bytes, s3_key: str) -> str:
        """Upload audio data to S3 and return URL."""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=audio_data,
                ContentType='audio/mpeg',
                ContentDisposition=f'inline; filename={s3_key.split("/")[-1]}'
            )

            return self._get_s3_url(s3_key)

        except Exception as e:
            logger.error(f"S3 upload error: {str(e)}")
            raise

    def _get_s3_url(self, s3_key: str) -> str:
        """Get S3 URL for audio file."""
        region = S3_SETTINGS.get('region', 'us-east-1')
        return f"https://{self.s3_bucket}.s3.{region}.amazonaws.com/{s3_key}"

    def _audio_exists_in_s3(self, s3_key: str) -> bool:
        """Check if audio file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            return True
        except Exception:
            return False

    def _estimate_duration(self, text: str) -> int:
        """Estimate audio duration in seconds (150 words per minute)."""
        word_count = len(text.split())
        return max(1, int((word_count / 150) * 60))

    def get_available_voices(self) -> Dict[str, str]:
        """Get available OpenAI TTS voices."""
        return {
            "alloy": "Balanced, neutral voice suitable for news",
            "echo": "Clear, friendly voice",
            "fable": "Warm, expressive voice great for storytelling",
            "onyx": "Deep, authoritative voice",
            "nova": "Bright, energetic voice",
            "shimmer": "Soft, gentle voice"
        }

    def estimate_cost(self, text: str, model: str = "tts-1") -> float:
        """Estimate TTS cost in USD."""
        char_count = len(text)

        # OpenAI TTS pricing (per 1K characters)
        if model == "tts-1":
            cost_per_1k = 0.015
        else:  # tts-1-hd
            cost_per_1k = 0.030

        return (char_count / 1000) * cost_per_1k


# Global TTS service instance
tts_service = TTSService()