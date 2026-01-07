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
import boto3
from botocore.exceptions import ClientError

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

        # Initialize S3 client for audio file storage
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ.get('AUDIO_BUCKET_NAME')
        if not self.bucket_name:
            logger.warning("AUDIO_BUCKET_NAME not set - falling back to local storage")

    async def generate_and_stream_audio(
        self,
        text: str,
        user_id: str,
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0,
        format: str = "mp3"
    ) -> AsyncGenerator[tuple[bytes, Dict[str, Any]], None]:
        """
        Generate audio from text and stream it while simultaneously saving to S3.

        This method provides real-time streaming to the user while building up the
        complete audio file in S3 for later access via Recent Articles.

        Args:
            text: Text to convert to speech
            user_id: User ID for file organization and access control
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            model: TTS model (tts-1 or tts-1-hd)
            speed: Speech speed (0.25 to 4.0)
            format: Audio format (mp3, opus, aac, flac)

        Yields:
            Tuples of (audio_chunk, metadata) where metadata includes audio_id, progress, etc.
        """
        try:
            # Generate unique ID for this audio
            content_hash = hashlib.md5(f"{text}{voice}{model}{speed}".encode()).hexdigest()
            audio_id = f"audio_{content_hash[:16]}"
            audio_filename = f"{audio_id}.{format}"
            s3_key = f"audio/user-{user_id}/{audio_filename}"

            logger.info(f"Starting streaming audio generation: {audio_id}")

            # Check if audio already exists in S3
            if self.bucket_name:
                try:
                    # Check if file exists in S3
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                    logger.info(f"Audio {audio_id} already exists in S3, streaming existing file")

                    # Stream existing file from S3
                    try:
                        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                        file_size = response['ContentLength']

                        # Stream in chunks
                        chunk_size = 8192
                        bytes_streamed = 0

                        for chunk in iter(lambda: response['Body'].read(chunk_size), b""):
                            if not chunk:
                                break

                            bytes_streamed += len(chunk)
                            progress = int((bytes_streamed / file_size) * 100)

                            metadata = {
                                "audio_id": audio_id,
                                "voice": voice,
                                "model": model,
                                "speed": speed,
                                "format": format,
                                "cached": True,
                                "s3_key": s3_key,
                                "storage": "s3",
                                "progress": progress,
                                "bytes_streamed": bytes_streamed,
                                "total_size": file_size
                            }

                            yield chunk, metadata

                        return

                    except Exception as e:
                        logger.error(f"Error streaming existing S3 file {s3_key}: {str(e)}")
                        # Fall through to generate new audio

                except ClientError as e:
                    if e.response['Error']['Code'] != '404':
                        logger.warning(f"S3 error checking for {audio_id}: {str(e)}")

            # Generate new audio with streaming
            logger.info(f"Generating new streaming audio: {audio_id}")

            # Split text into chunks
            chunks = self._split_text(text, max_length=4000)
            total_chunks = len(chunks)

            # S3 buffer for incremental storage
            s3_buffer = BytesIO()
            total_bytes_generated = 0

            for chunk_idx, text_chunk in enumerate(chunks):
                logger.info(f"Processing chunk {chunk_idx + 1}/{total_chunks}")

                # Generate audio for this chunk
                response = await self.openai_client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=text_chunk,
                    speed=speed,
                    response_format=format
                )

                audio_data = response.content
                total_bytes_generated += len(audio_data)

                # Add to S3 buffer
                s3_buffer.write(audio_data)

                # Stream this chunk to user immediately
                chunk_progress = int(((chunk_idx + 1) / total_chunks) * 100)

                metadata = {
                    "audio_id": audio_id,
                    "voice": voice,
                    "model": model,
                    "speed": speed,
                    "format": format,
                    "cached": False,
                    "s3_key": s3_key,
                    "storage": "s3" if self.bucket_name else "streaming",
                    "progress": chunk_progress,
                    "chunk": chunk_idx + 1,
                    "total_chunks": total_chunks,
                    "bytes_generated": total_bytes_generated
                }

                yield audio_data, metadata

                # Periodically upload buffer to S3 (every few chunks or if buffer gets large)
                if self.bucket_name and (
                    chunk_idx % 3 == 0 or  # Every 3 chunks
                    s3_buffer.tell() > 1024 * 1024 or  # Buffer > 1MB
                    chunk_idx == total_chunks - 1  # Last chunk
                ):
                    try:
                        # Upload accumulated audio to S3
                        buffer_data = s3_buffer.getvalue()
                        if buffer_data:
                            # For MP3, we can append chunks (simple concatenation works)
                            if chunk_idx == 0:
                                # First upload - create new object
                                self.s3_client.put_object(
                                    Bucket=self.bucket_name,
                                    Key=s3_key,
                                    Body=buffer_data,
                                    ContentType=f"audio/{format}",
                                    ContentDisposition=f"inline; filename={audio_filename}"
                                )
                            else:
                                # Subsequent uploads - we need to append
                                # For simplicity, we'll replace the entire object
                                # In production, consider using multipart upload for large files
                                existing_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
                                existing_data = existing_response['Body'].read()
                                combined_data = existing_data + audio_data

                                self.s3_client.put_object(
                                    Bucket=self.bucket_name,
                                    Key=s3_key,
                                    Body=combined_data,
                                    ContentType=f"audio/{format}",
                                    ContentDisposition=f"inline; filename={audio_filename}"
                                )

                            logger.debug(f"Uploaded chunk {chunk_idx + 1} to S3: {s3_key}")

                    except Exception as e:
                        logger.error(f"Failed to upload chunk {chunk_idx + 1} to S3: {str(e)}")
                        # Continue streaming even if S3 upload fails

            # Final metadata
            final_metadata = {
                "audio_id": audio_id,
                "voice": voice,
                "model": model,
                "speed": speed,
                "format": format,
                "size": total_bytes_generated,
                "chunks": total_chunks,
                "cached": False,
                "s3_key": s3_key,
                "storage": "s3" if self.bucket_name else "streaming",
                "progress": 100,
                "completed": True
            }

            logger.info(f"Streaming audio generation completed: {audio_id} ({total_bytes_generated} bytes)")

            # Yield final completion signal
            yield b'', final_metadata

        except Exception as e:
            logger.error(f"Error in streaming audio generation: {str(e)}")
            # Yield error metadata
            error_metadata = {
                "audio_id": audio_id if 'audio_id' in locals() else "unknown",
                "error": str(e),
                "progress": 0,
                "completed": False
            }
            yield b'', error_metadata
            raise Exception(f"Failed to generate streaming audio: {str(e)}")

    async def generate_audio(
        self,
        text: str,
        user_id: str,
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0,
        format: str = "mp3"
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate audio from text using OpenAI TTS.

        Args:
            text: Text to convert to speech
            user_id: User ID for file organization and access control
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

            # S3 key with user-specific path for isolation: audio/user-{user_id}/filename
            s3_key = f"audio/user-{user_id}/{audio_filename}"

            # Check if we already have this audio cached in S3
            if self.bucket_name:
                try:
                    # Check if file exists in S3
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                    logger.info(f"Using cached audio from S3: {audio_id}")

                    metadata = {
                        "audio_id": audio_id,
                        "voice": voice,
                        "model": model,
                        "speed": speed,
                        "format": format,
                        "cached": True,
                        "s3_key": s3_key,
                        "storage": "s3"
                    }

                    # Return S3 key, not presigned URL (URLs generated on-demand)
                    return s3_key, metadata
                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        # File doesn't exist in S3, continue to generate
                        logger.debug(f"Audio {audio_id} not found in S3, generating new")
                    else:
                        # Other S3 error, log but continue to generate
                        logger.warning(f"S3 error checking for {audio_id}: {str(e)}")
            else:
                # Fallback to local storage check
                local_path = os.path.join(self.temp_dir, audio_filename)
                if os.path.exists(local_path):
                    logger.info(f"Using cached audio locally: {audio_id}")
                    metadata = {
                        "audio_id": audio_id,
                        "voice": voice,
                        "model": model,
                        "speed": speed,
                        "format": format,
                        "cached": True,
                        "storage": "local"
                    }
                    return local_path, metadata

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

            # Upload to S3 if bucket is available
            if self.bucket_name:
                try:
                    # Upload directly to S3
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=s3_key,
                        Body=final_audio,
                        ContentType=f"audio/{format}",
                        ContentDisposition=f"inline; filename={audio_filename}"
                    )

                    logger.info(f"Audio uploaded to S3: {s3_key} ({len(final_audio)} bytes)")

                    # Calculate metadata
                    metadata = {
                        "audio_id": audio_id,
                        "voice": voice,
                        "model": model,
                        "speed": speed,
                        "format": format,
                        "size": len(final_audio),
                        "chunks": len(chunks),
                        "cached": False,
                        "s3_key": s3_key,
                        "storage": "s3"
                    }

                    # Return S3 key, not presigned URL (URLs generated on-demand)
                    return s3_key, metadata

                except Exception as s3_error:
                    logger.error(f"Failed to upload to S3: {str(s3_error)}, falling back to local storage")
                    # Continue with local storage fallback

            # Fallback: Save locally (for development or S3 failure)
            local_path = os.path.join(self.temp_dir, audio_filename)
            async with aiofiles.open(local_path, 'wb') as f:
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
                "cached": False,
                "storage": "local"
            }

            logger.info(f"Audio saved locally: {audio_id} ({len(final_audio)} bytes)")
            return local_path, metadata

        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            raise Exception(f"Failed to generate audio: {str(e)}")

    def get_audio_url(self, audio_id: str, user_id: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get a URL to access the audio file (S3 presigned URL or local path).

        Args:
            audio_id: Audio identifier
            user_id: User ID for path construction and access verification
            expires_in: URL expiration time in seconds (for S3 presigned URLs)

        Returns:
            Audio access URL or None if not found
        """
        try:
            # Try S3 first with user-specific path
            if self.bucket_name:
                s3_key = f"audio/user-{user_id}/{audio_id}.mp3"  # Default to mp3, could be improved

                try:
                    # Check if file exists in S3
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)

                    # Generate presigned URL for secure access
                    presigned_url = self.s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket_name, 'Key': s3_key},
                        ExpiresIn=expires_in
                    )

                    logger.info(f"Generated presigned URL for {audio_id} (user {user_id})")
                    return presigned_url

                except ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        logger.info(f"Audio {audio_id} not found in S3 for user {user_id}, checking local storage")
                    else:
                        logger.warning(f"S3 error getting URL for {audio_id}: {str(e)}")

            # Fallback to local file check (less secure, for development)
            audio_files = [f for f in os.listdir(self.temp_dir) if f.startswith(audio_id)]
            if audio_files:
                local_path = os.path.join(self.temp_dir, audio_files[0])
                if os.path.exists(local_path):
                    return local_path

            return None

        except Exception as e:
            logger.error(f"Error getting audio URL for {audio_id} (user {user_id}): {str(e)}")
            return None

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