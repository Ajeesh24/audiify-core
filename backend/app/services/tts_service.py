import asyncio
import hashlib
import tempfile
import os
from typing import Optional, Dict, Any, AsyncGenerator
from io import BytesIO
import aiofiles
from openai import AsyncOpenAI
import httpx
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TTSService:
    """Service for text-to-speech conversion using OpenAI and other providers."""

    def __init__(self):
        """Initialize TTS service."""
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")

        # Create httpx client with SSL verification disabled for corporate environments
        http_client = httpx.AsyncClient(verify=False)

        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=http_client
        )
        self.temp_dir = tempfile.gettempdir()

    async def generate_audio(
        self,
        text: str,
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0,
        format: str = "mp3"
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate audio from text using OpenAI TTS.

        Args:
            text: Text to convert to speech
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 or tts-1-hd)
            speed: Speech speed (0.25 to 4.0)
            format: Audio format (mp3, opus, aac, flac)

        Returns:
            Tuple of (audio_file_path, metadata)
        """
        try:
            # Generate a unique ID for this audio
            content_hash = hashlib.md5(f"{text}{voice}{model}{speed}".encode()).hexdigest()
            audio_id = f"audio_{content_hash[:16]}"
            audio_filename = f"{audio_id}.{format}"
            audio_path = os.path.join(self.temp_dir, audio_filename)

            # Check if we already have this audio cached
            if os.path.exists(audio_path):
                logger.info(f"Using cached audio: {audio_id}")
                metadata = {
                    "audio_id": audio_id,
                    "voice": voice,
                    "model": model,
                    "speed": speed,
                    "format": format,
                    "cached": True
                }
                return audio_path, metadata

            logger.info(f"Generating new audio with OpenAI TTS: {audio_id}")

            # Split text if it's too long (OpenAI has a 4096 character limit)
            chunks = self._split_text(text, max_length=4000)
            audio_chunks = []

            for i, chunk in enumerate(chunks):
                logger.info(f"Generating audio chunk {i+1}/{len(chunks)}")

                response = await self.openai_client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=chunk,
                    speed=speed,
                    response_format=format
                )

                # Read the audio data
                audio_data = response.content

                audio_chunks.append(audio_data)

            # Combine chunks if multiple
            if len(audio_chunks) == 1:
                final_audio = audio_chunks[0]
            else:
                final_audio = await self._combine_audio_chunks(audio_chunks, format)

            # Save to file
            async with aiofiles.open(audio_path, 'wb') as f:
                await f.write(final_audio)

            # Calculate metadata
            metadata = {
                "audio_id": audio_id,
                "voice": voice,
                "model": model,
                "speed": speed,
                "format": format,
                "size": len(final_audio),
                "chunks": len(chunks),
                "cached": False
            }

            logger.info(f"Audio generated successfully: {audio_id} ({len(final_audio)} bytes)")
            return audio_path, metadata

        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            raise Exception(f"Failed to generate audio: {str(e)}")

    def _split_text(self, text: str, max_length: int = 4000) -> list[str]:
        """
        Split long text into chunks suitable for TTS.

        Args:
            text: Text to split
            max_length: Maximum length per chunk

        Returns:
            List of text chunks
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current_pos = 0

        while current_pos < len(text):
            # Find a good breaking point (end of sentence)
            end_pos = min(current_pos + max_length, len(text))

            if end_pos == len(text):
                # Last chunk
                chunks.append(text[current_pos:end_pos])
                break

            # Look for sentence endings near the limit
            chunk_text = text[current_pos:end_pos]

            # Find the last sentence ending
            for delimiter in ['. ', '! ', '? ', '\n\n']:
                last_delimiter = chunk_text.rfind(delimiter)
                if last_delimiter > len(chunk_text) * 0.7:  # At least 70% of max length
                    end_pos = current_pos + last_delimiter + len(delimiter.strip())
                    break

            chunks.append(text[current_pos:end_pos].strip())
            current_pos = end_pos

        return [chunk for chunk in chunks if chunk.strip()]

    async def _combine_audio_chunks(self, chunks: list[bytes], format: str) -> bytes:
        """
        Combine multiple audio chunks into a single audio file.

        Note: This is a simple concatenation. For production, you might want
        to use proper audio processing libraries like pydub for seamless joining.
        """
        # For MP3 and other formats, simple concatenation works in many cases
        # In production, consider using pydub or ffmpeg for proper audio joining
        return b''.join(chunks)

    async def stream_audio(self, audio_path: str) -> AsyncGenerator[bytes, None]:
        """
        Stream audio file in chunks.

        Args:
            audio_path: Path to the audio file

        Yields:
            Audio data chunks
        """
        chunk_size = 8192  # 8KB chunks

        try:
            async with aiofiles.open(audio_path, 'rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error(f"Error streaming audio {audio_path}: {str(e)}")
            raise

    def get_available_voices(self) -> Dict[str, str]:
        """Get available TTS voices."""
        return {
            "alloy": "A balanced, neutral voice suitable for most content",
            "echo": "A clear, friendly voice with slight warmth",
            "fable": "A warm, expressive voice great for storytelling",
            "onyx": "A deep, authoritative voice",
            "nova": "A bright, energetic voice",
            "shimmer": "A soft, gentle voice with clarity"
        }

    def estimate_cost(self, text: str, model: str = "tts-1") -> float:
        """
        Estimate the cost of TTS conversion.

        Args:
            text: Text to convert
            model: TTS model

        Returns:
            Estimated cost in USD
        """
        char_count = len(text)

        # OpenAI TTS pricing (as of 2024)
        if model == "tts-1":
            cost_per_1k_chars = 0.015
        else:  # tts-1-hd
            cost_per_1k_chars = 0.030

        return (char_count / 1000) * cost_per_1k_chars

    def cleanup_old_files(self, max_age_hours: int = 24):
        """Clean up old temporary audio files."""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (max_age_hours * 3600)

            for filename in os.listdir(self.temp_dir):
                if filename.startswith("audio_") and filename.endswith((".mp3", ".wav", ".opus")):
                    filepath = os.path.join(self.temp_dir, filename)
                    try:
                        file_mtime = os.path.getmtime(filepath)

                        if file_mtime < cutoff_time:
                            os.unlink(filepath)
                            logger.info(f"Cleaned up old audio file: {filename}")
                    except OSError:
                        # File might have been deleted already, ignore
                        continue

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get information about an audio file."""
        try:
            stat = os.stat(audio_path)
            return {
                "exists": True,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            }
        except OSError:
            return {"exists": False}