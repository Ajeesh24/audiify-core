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

    async def generate_audio_progressive(
        self,
        text: str,
        user_id: str,
        voice: str = "alloy",
        model: str = "tts-1",
        speed: float = 1.0,
        format: str = "mp3"
    ) -> tuple[str, Dict[str, Any]]:
        """
        Generate audio progressively with exponential chunk sizes.
        Returns first chunk immediately, continues processing in background.

        Chunk strategy: 15s → 40s → 80s → 160s → 320s
        Creates single growing S3 file for seamless user experience.
        """
        try:
            # Generate chunks with exponential sizes for fake streaming
            chunks = self._create_exponential_chunks(text)
            logger.info(f"Created {len(chunks)} exponential chunks for progressive generation")

            # Generate unique ID for this audio
            content_hash = hashlib.md5(f"{text}{voice}{model}{speed}".encode()).hexdigest()
            audio_id = f"audio_{content_hash[:16]}"
            audio_filename = f"{audio_id}.{format}"
            s3_key = f"audio/user-{user_id}/{audio_filename}"

            # Check if complete version already exists in S3
            if self.bucket_name:
                try:
                    self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
                    logger.info(f"Complete audio already exists: {audio_id}")

                    metadata = {
                        "audio_id": audio_id,
                        "voice": voice,
                        "model": model,
                        "speed": speed,
                        "format": format,
                        "cached": True,
                        "s3_key": s3_key,
                        "storage": "s3",
                        "progressive": False,
                        "total_chunks": len(chunks),
                        "completed_chunks": len(chunks)
                    }
                    return s3_key, metadata
                except ClientError as e:
                    if e.response['Error']['Code'] != '404':
                        logger.warning(f"S3 error checking for {audio_id}: {str(e)}")

            # Generate first chunk immediately
            logger.info(f"Generating first chunk immediately: {len(chunks[0])} characters")
            first_chunk_audio = await self._generate_chunk_audio(chunks[0], voice, model, speed, format)

            # Save first chunk to growing file path in /tmp
            growing_file_path = os.path.join(self.temp_dir, audio_filename)
            await self._save_audio_to_growing_file(growing_file_path, first_chunk_audio, is_first=True)

            # Upload first chunk to S3 immediately
            if self.bucket_name:
                await self._upload_growing_file_to_s3(growing_file_path, s3_key)

            # Prepare metadata for first chunk response
            metadata = {
                "audio_id": audio_id,
                "voice": voice,
                "model": model,
                "speed": speed,
                "format": format,
                "cached": False,
                "s3_key": s3_key,
                "storage": "s3" if self.bucket_name else "local",
                "progressive": len(chunks) > 1,
                "total_chunks": len(chunks),
                "completed_chunks": 1,
                "expected_durations": [20, 40, 80, 160, 320][:len(chunks)]
            }

            # Start background processing for remaining chunks if any
            if len(chunks) > 1:
                logger.info(f"Queueing {len(chunks) - 1} remaining chunks for background processing")
                await self._queue_remaining_chunks_for_processing(
                    chunks[1:], s3_key, voice, model, speed, format, audio_id, user_id
                )

            return s3_key if self.bucket_name else growing_file_path, metadata

        except Exception as e:
            logger.error(f"Error in progressive audio generation: {str(e)}")
            raise Exception(f"Failed to generate progressive audio: {str(e)}")

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

    def _create_exponential_chunks(self, text: str) -> list[str]:
        """
        Create exponential chunks for progressive audio generation.

        Chunk durations: 15s → 40s → 80s → 160s → 320s
        Approximate words per second: 2.5 (conversational speed)
        """
        words = text.split()
        if len(words) == 0:
            return [text]

        # Target durations in seconds with exponential growth
        target_durations = [15, 40, 80, 160, 320]
        words_per_second = 2.5

        chunks = []
        start_idx = 0

        for target_seconds in target_durations:
            if start_idx >= len(words):
                break

            target_words = int(target_seconds * words_per_second)
            end_idx = min(start_idx + target_words, len(words))

            # Find good breaking point (sentence boundary)
            chunk_text = ' '.join(words[start_idx:end_idx])

            # Look for sentence ending near the end to avoid cutting mid-sentence
            if end_idx < len(words):
                remaining_text = ' '.join(words[start_idx:min(end_idx + 20, len(words))])
                for delimiter in ['. ', '! ', '? ', '\n']:
                    delimiter_pos = remaining_text.find(delimiter, len(chunk_text) - 50)
                    if delimiter_pos != -1 and delimiter_pos > len(chunk_text) * 0.8:
                        chunk_text = remaining_text[:delimiter_pos + len(delimiter.strip())]
                        end_idx = start_idx + len(chunk_text.split())
                        break

            if chunk_text.strip():
                chunks.append(chunk_text.strip())
                start_idx = end_idx
            else:
                break

        # Add remaining text as final chunk if any
        if start_idx < len(words):
            remaining_chunk = ' '.join(words[start_idx:])
            if remaining_chunk.strip():
                chunks.append(remaining_chunk.strip())

        logger.info(f"Split text into {len(chunks)} exponential chunks: {[len(c.split()) for c in chunks]} words")
        return chunks

    async def _generate_chunk_audio(self, text: str, voice: str, model: str, speed: float, format: str) -> bytes:
        """Generate audio for a single text chunk."""
        try:
            response = await self.openai_client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                speed=speed,
                response_format=format
            )
            return response.content
        except Exception as e:
            logger.error(f"Error generating chunk audio: {str(e)}")
            raise

    async def _save_audio_to_growing_file(self, file_path: str, audio_data: bytes, is_first: bool = False):
        """Save audio data to growing file, appending if not first chunk."""
        try:
            if is_first:
                # First chunk: create new file
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(audio_data)
                logger.info(f"Created new growing file: {file_path} ({len(audio_data)} bytes)")
            else:
                # Subsequent chunks: append to existing file
                # Note: For MP3, we should use proper audio concatenation
                # For now, we'll use simple byte concatenation (works for many cases)
                async with aiofiles.open(file_path, 'ab') as f:
                    await f.write(audio_data)
                logger.info(f"Appended to growing file: {file_path} (+{len(audio_data)} bytes)")
        except Exception as e:
            logger.error(f"Error saving audio to growing file: {str(e)}")
            raise

    async def _upload_growing_file_to_s3(self, local_path: str, s3_key: str):
        """Upload the current state of growing file to S3."""
        try:
            async with aiofiles.open(local_path, 'rb') as f:
                file_data = await f.read()

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ContentType="audio/mp3",
                ContentDisposition=f"inline; filename={os.path.basename(s3_key)}"
            )

            logger.info(f"Uploaded growing file to S3: {s3_key} ({len(file_data)} bytes)")
        except Exception as e:
            logger.error(f"Error uploading growing file to S3: {str(e)}")
            raise

    async def _process_remaining_chunks_progressive(
        self,
        remaining_chunks: list[str],
        growing_file_path: str,
        s3_key: str,
        voice: str,
        model: str,
        speed: float,
        format: str,
        audio_id: str
    ):
        """Process remaining chunks in background, growing the file progressively."""
        try:
            for i, chunk_text in enumerate(remaining_chunks, start=2):  # Start from chunk 2
                logger.info(f"Processing background chunk {i} for {audio_id}")

                # Generate audio for this chunk
                chunk_audio = await self._generate_chunk_audio(chunk_text, voice, model, speed, format)

                # Append to growing file
                await self._save_audio_to_growing_file(growing_file_path, chunk_audio, is_first=False)

                # Upload updated file to S3 (overwrites previous)
                if self.bucket_name:
                    await self._upload_growing_file_to_s3(growing_file_path, s3_key)

                logger.info(f"Completed chunk {i}/{len(remaining_chunks) + 1} for {audio_id}")

                # Small delay to prevent overwhelming OpenAI API
                await asyncio.sleep(0.5)

            logger.info(f"Completed all progressive chunks for {audio_id}")

        except Exception as e:
            logger.error(f"Error in background chunk processing for {audio_id}: {str(e)}")
            # Don't raise - this is background processing

    async def _queue_remaining_chunks_for_processing(
        self,
        remaining_chunks: list[str],
        s3_key: str,
        voice: str,
        model: str,
        speed: float,
        format: str,
        audio_id: str,
        user_id: str
    ):
        """Queue remaining chunks for processing via SQS (separate Lambda invocations)."""
        try:
            import boto3
            import json
            import os

            # Get SQS queue URL from environment
            queue_url = os.environ.get('SQS_QUEUE_URL')
            if not queue_url:
                logger.error("SQS_QUEUE_URL not configured - cannot queue background chunks")
                return

            sqs_client = boto3.client('sqs')

            # Queue each remaining chunk as a separate job
            for i, chunk_text in enumerate(remaining_chunks, start=2):  # Start from chunk 2
                chunk_job = {
                    "type": "progressive_chunk",
                    "audio_id": audio_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "total_chunks": len(remaining_chunks) + 1,  # +1 for the first chunk
                    "chunk_text": chunk_text,
                    "s3_key": s3_key,
                    "voice": voice,
                    "model": model,
                    "speed": speed,
                    "format": format
                }

                # Send to SQS
                response = sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(chunk_job),
                    MessageAttributes={
                        'JobType': {
                            'StringValue': 'progressive_chunk',
                            'DataType': 'String'
                        },
                        'AudioId': {
                            'StringValue': audio_id,
                            'DataType': 'String'
                        }
                    }
                )

                logger.info(f"Queued progressive chunk {i}/{len(remaining_chunks) + 1} for {audio_id}: {response['MessageId']}")

        except Exception as e:
            logger.error(f"Error queuing remaining chunks for {audio_id}: {str(e)}")
            # Don't raise - this is best-effort background processing