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
from app.services.audio_metadata_storage import AudioMetadataStorage
from app.services.progressive_audio_coordinator import ProgressiveAudioCoordinator

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

        # Initialize DynamoDB storage for audio metadata
        try:
            self.audio_metadata_storage = AudioMetadataStorage()
        except Exception as e:
            logger.warning(f"Failed to initialize AudioMetadataStorage: {str(e)} - metadata tracking disabled")

        # Initialize progressive audio coordinator
        try:
            self.progressive_coordinator = ProgressiveAudioCoordinator()
        except Exception as e:
            logger.warning(f"Failed to initialize ProgressiveAudioCoordinator: {str(e)} - coordination disabled")

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

                # Create initial audio metadata in DynamoDB
                if hasattr(self, 'audio_metadata_storage'):
                    try:
                        initial_file_size = os.path.getsize(growing_file_path)
                        self.audio_metadata_storage.create_audio_metadata(
                            audio_id=audio_id,
                            user_id=user_id,
                            total_chunks=len(chunks),
                            s3_key=s3_key,
                            initial_file_size=initial_file_size
                        )
                        logger.info(f"Created audio metadata in DynamoDB for {audio_id}: {initial_file_size} bytes")
                    except Exception as e:
                        logger.error(f"Failed to create audio metadata for {audio_id}: {str(e)}")

                # Initialize progressive coordination for sequential processing
                if hasattr(self, 'progressive_coordinator') and len(chunks) > 1:
                    try:
                        self.progressive_coordinator.initialize_audio_coordination(
                            audio_id=audio_id,
                            user_id=user_id,
                            total_chunks=len(chunks),
                            s3_key=s3_key
                        )
                        logger.info(f"Initialized progressive coordination for {audio_id}: {len(chunks)} total chunks")
                    except Exception as e:
                        logger.error(f"Failed to initialize coordination for {audio_id}: {str(e)}")

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
                "expected_durations": [max(1, int(len(chunk.split()) / 2.5)) for chunk in chunks]  # Convert to integers, minimum 1 second
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
        Create optimal 3-chunk strategy for fake streaming experience.

        Strategy:
        - Chunk 1: 50-60s (immediate start - user gets audio quickly)
        - Chunk 2: 2-3 minutes (substantial content - minimal interruptions)
        - Chunk 3: Everything remaining (completion)

        This gives us 3-4 minutes total processing time while user enjoys uninterrupted listening.
        """
        words = text.split()
        if len(words) == 0:
            return [text]

        total_words = len(words)
        words_per_second = 2.5
        total_duration = total_words / words_per_second

        logger.info(f"Optimal chunking: {total_words} words (~{total_duration:.1f}s total)")

        # For very short articles (< 2 minutes), don't chunk
        if total_duration < 120:
            logger.info(f"Short article ({total_duration:.1f}s) - single chunk optimal")
            return [text.strip()]

        chunks = []
        start_idx = 0

        # Chunk 1: 50-60 seconds (immediate playback)
        chunk1_seconds = 55  # Sweet spot for immediate start
        chunk1_words = min(int(chunk1_seconds * words_per_second), total_words - 100)  # Leave at least 100 words
        chunk1_words = max(chunk1_words, 80)  # Minimum 80 words (~32s)

        chunk1_text = self._extract_chunk_at_sentence_boundary(words, start_idx, chunk1_words)
        chunks.append(chunk1_text)
        start_idx = len(chunk1_text.split())

        remaining_words = total_words - start_idx
        remaining_duration = remaining_words / words_per_second

        logger.info(f"Chunk 1: {len(chunk1_text.split())} words (~{len(chunk1_text.split()) / words_per_second:.1f}s)")
        logger.info(f"Remaining: {remaining_words} words (~{remaining_duration:.1f}s)")

        # Smart decision for remaining content
        if remaining_duration <= 180:  # <= 3 minutes remaining
            # Put all remaining in Chunk 2 (user will have 3+ minutes to process any future content)
            remaining_text = ' '.join(words[start_idx:])
            if remaining_text.strip():
                chunks.append(remaining_text.strip())
                logger.info(f"Chunk 2 (final): {len(remaining_text.split())} words (~{remaining_duration:.1f}s)")

        else:
            # Large content: Chunk 2 = 2-3 minutes, Chunk 3 = rest
            chunk2_seconds = 150  # 2.5 minutes sweet spot
            chunk2_words = min(int(chunk2_seconds * words_per_second), remaining_words - 50)  # Leave 50 for chunk 3

            chunk2_text = self._extract_chunk_at_sentence_boundary(words, start_idx, start_idx + chunk2_words)
            chunks.append(chunk2_text)
            start_idx += len(chunk2_text.split())

            # Chunk 3: Everything remaining
            final_text = ' '.join(words[start_idx:])
            if final_text.strip():
                chunks.append(final_text.strip())

            logger.info(f"Chunk 2: {len(chunk2_text.split())} words (~{len(chunk2_text.split()) / words_per_second:.1f}s)")
            logger.info(f"Chunk 3: {len(final_text.split())} words (~{len(final_text.split()) / words_per_second:.1f}s)")

        # Log final summary
        total_chunks = len(chunks)
        chunk_sizes = [len(chunk.split()) for chunk in chunks]
        estimated_durations = [size / words_per_second for size in chunk_sizes]

        logger.info(f"Optimal result: {total_chunks} chunks, durations: {[f'{d:.1f}s' for d in estimated_durations]}")
        logger.info(f"Processing window: ~{sum(estimated_durations[1:]) if len(estimated_durations) > 1 else 0:.1f}s to complete remaining chunks")

        # Content validation
        total_chunked_words = sum(len(chunk.split()) for chunk in chunks)
        if total_chunked_words != total_words:
            logger.error(f"❌ CONTENT LOSS! Original: {total_words}, Chunked: {total_chunked_words}")
            return [text.strip()]

        empty_chunks = [i for i, chunk in enumerate(chunks) if not chunk.strip()]
        if empty_chunks:
            logger.error(f"❌ EMPTY CHUNKS at indices: {empty_chunks}")
            return [text.strip()]

        logger.info(f"✅ Content validation passed: {total_chunked_words}/{total_words} words preserved")
        return chunks

    def _extract_chunk_at_sentence_boundary(self, words: list[str], start_idx: int, target_end_idx: int) -> str:
        """Extract a chunk of text, preferring to break at sentence boundaries."""
        if start_idx >= len(words):
            return ""

        if target_end_idx >= len(words):
            return ' '.join(words[start_idx:])

        # Get the target chunk
        target_text = ' '.join(words[start_idx:target_end_idx])

        # Look for sentence endings near the target end (within ±20 words)
        search_start = max(int(target_end_idx * 0.8), start_idx + 10)  # Don't go below 80% of target
        search_end = min(target_end_idx + 20, len(words))

        best_end = target_end_idx

        # Search for sentence boundaries in the extended range
        for i in range(search_start, search_end):
            if i < len(words):
                word = words[i]
                # Look for sentence endings
                if word.endswith(('.', '!', '?')) or word.endswith(('."', '!"', '?"')):
                    # Found a sentence boundary
                    best_end = i + 1
                    break
                elif i < len(words) - 1 and words[i + 1].startswith(('However,', 'But,', 'Meanwhile,', 'Furthermore,')):
                    # Found a paragraph/section transition
                    best_end = i + 1
                    break

        return ' '.join(words[start_idx:best_end]).strip()

    async def _generate_chunk_audio(self, text: str, voice: str, model: str, speed: float, format: str) -> bytes:
        """Generate audio for a single text chunk, handling TTS API character limits."""
        try:
            # OpenAI TTS API has 4096 character limit - need to sub-chunk if necessary
            max_chars = 4000  # Leave some buffer below 4096

            if len(text) <= max_chars:
                # Single API call
                response = await self.openai_client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=text,
                    speed=speed,
                    response_format=format
                )
                return response.content

            else:
                # Need to sub-chunk and concatenate audio
                logger.info(f"Large chunk ({len(text)} chars) - sub-chunking for TTS API limits")

                sub_chunks = self._split_text(text, max_chars)
                logger.info(f"Split into {len(sub_chunks)} TTS sub-chunks")

                audio_segments = []
                for i, sub_chunk in enumerate(sub_chunks):
                    logger.info(f"Processing TTS sub-chunk {i+1}/{len(sub_chunks)} ({len(sub_chunk)} chars)")

                    response = await self.openai_client.audio.speech.create(
                        model=model,
                        voice=voice,
                        input=sub_chunk,
                        speed=speed,
                        response_format=format
                    )
                    audio_segments.append(response.content)

                # Concatenate audio segments
                combined_audio = b''.join(audio_segments)
                logger.info(f"Combined {len(audio_segments)} TTS sub-chunks into single audio file")

                return combined_audio

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