"""
Engine 5: Audio Generation Engine

Converts text briefs to audio using ElevenLabs or AWS Polly
Includes fallback mechanism and cost optimization
"""

import os
import time
import boto3
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import tempfile

from models import Brief, Job, EngineStatus
from config import AUDIO_SETTINGS, S3_SETTINGS, COST_OPTIMIZATION, get_s3_key
from utils.logger import get_logger, log_engine_start, log_engine_complete, log_engine_error
from utils.metrics import cost_tracker, time_operation

logger = get_logger(__name__)


class AudioGenerationEngine:
    """
    Audio Generation Engine

    Responsible for:
    1. Converting text briefs to high-quality audio
    2. Supporting ElevenLabs and AWS Polly providers
    3. Uploading audio files to S3
    4. Managing cost optimization with fallback
    """

    def __init__(self):
        self.brief_model = Brief()
        self.job_model = Job()

        # Initialize AWS clients
        self.s3_client = boto3.client('s3')
        self.polly_client = boto3.client('polly')

        # Audio generation settings
        self.provider = AUDIO_SETTINGS['provider']
        self.elevenlabs_api_key = AUDIO_SETTINGS['elevenlabs_api_key']
        self.voice_id = AUDIO_SETTINGS['voice_id']
        self.s3_bucket = S3_SETTINGS['bucket_name']

    def generate_daily_audio(self, date: str = None) -> Dict[str, any]:
        """
        Main entry point for daily audio generation

        Args:
            date: Date in YYYY-MM-DD format (defaults to today)

        Returns:
            Audio generation results summary
        """
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')

        logger.info(f"Starting audio generation for {date}")
        log_engine_start('audio_engine', date, logger)

        # Start) in job tracking
        job = self.job_model.get_job(date)
        if not job:
            raise ValueError(f"No job found for date {date}. Previous engines must run first.")

        self.job_model.start_engine(date, 'audio_engine')

        try:
            results = {
                'date': date,
                'audio_files_generated': 0,
                'total_audio_duration': 0,
                'processing_time': 0,
                'cost_usd': 0.0,
                'provider_used': self.provider,
                'categories': {}
            }

            start_time = time.time()

            # Get all briefs for the date
            briefs = self.brief_model.get_briefs_by_date(date)
            if not briefs:
                logger.warning(f"No briefs found for date {date}")
                self.job_model.complete_engine(date, 'audio_engine', results)
                return results

            # Process each brief
            for brief in briefs:
                if brief.get('status') != 'generated':
                    continue

                category = brief['category']
                logger.info(f"Generating audio for {category} brief")

                try:
                    audio_result = self._generate_brief_audio(brief, date)
                    results['categories'][category] = audio_result

                    if audio_result['success']:
                        results['audio_files_generated'] += 1
                        results['total_audio_duration'] += audio_result['duration']
                        results['cost_usd'] += audio_result['cost_usd']

                except Exception as e:
                    logger.error(f"Error generating audio for {category}: {str(e)}")
                    results['categories'][category] = {
                        'success': False,
                        'error': str(e),
                        'duration': 0,
                        'cost_usd': 0.0
                    }

            results['processing_time'] = time.time() - start_time

            # Complete engine tracking
            self.job_model.complete_engine(date, 'audio_engine', {
                'audio_files_generated': results['audio_files_generated'],
                'total_audio_duration': results['total_audio_duration']
            })

            log_engine_complete('audio_engine', date, results, logger)

            logger.info(f"Audio generation completed. Generated {results['audio_files_generated']} files, "
                       f"total duration: {results['total_audio_duration']}s, "
                       f"cost: ${results['cost_usd']:.4f}")

            return results

        except Exception as e:
            logger.error(f"Audio generation failed: {str(e)}")
            log_engine_error('audio_engine', date, str(e), logger)
            self.job_model.fail_engine(date, 'audio_engine', str(e))
            raise

    def _generate_brief_audio(self, brief: Dict, date: str) -> Dict[str, any]:
        """
        Generate audio for a single brief

        Args:
            brief: Brief data from database
            date: Processing date

        Returns:
            Audio generation results
        """
        category = brief['category']
        content = brief['content']
        brief_id = brief['brief_id']

        # Estimate cost and check budget
        estimated_cost = self._estimate_audio_cost(content)
        if cost_tracker.get_daily_cost() + estimated_cost > COST_OPTIMIZATION['target_daily_cost']:
            return {
                'success': False,
                'error': 'Would exceed daily budget',
                'duration': 0,
                'cost_usd': 0.0
            }

        try:
            # Generate audio using primary provider
            audio_data, duration, cost = self._generate_audio_with_provider(
                content, self.provider, category
            )

            if not audio_data:
                # Fallback to AWS Polly if primary provider fails
                logger.warning(f"Primary provider failed, falling back to AWS Polly for {category}")
                audio_data, duration, cost = self._generate_audio_with_provider(
                    content, 'aws_polly', category
                )

                if not audio_data:
                    return {
                        'success': False,
                        'error': 'Both audio providers failed',
                        'duration': 0,
                        'cost_usd': 0.0
                    }

            # Upload to S3
            s3_key = self._upload_audio_to_s3(audio_data, category, date)
            if not s3_key:
                return {
                    'success': False,
                    'error': 'Failed to upload audio to S3',
                    'duration': 0,
                    'cost_usd': cost
                }

            # Generate public URL
            audio_url = f"https://{self.s3_bucket}.s3.{S3_SETTINGS['region']}.amazonaws.com/{s3_key}"

            # Update brief with audio information
            self.brief_model.update_audio_info(
                category=category,
                date=date,
                audio_url=audio_url,
                actual_duration=duration,
                audio_size=len(audio_data)
            )

            # Track audio generation cost
            if self.provider == 'elevenlabs':
                cost_tracker.track_audio_usage('audio_generation', len(content))

            return {
                'success': True,
                'audio_url': audio_url,
                's3_key': s3_key,
                'duration': duration,
                'file_size': len(audio_data),
                'cost_usd': cost
            }

        except Exception as e:
            logger.error(f"Error generating audio for {category}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'duration': 0,
                'cost_usd': 0.0
            }

    def _generate_audio_with_provider(self, text: str, provider: str, category: str) -> Tuple[Optional[bytes], int, float]:
        """
        Generate audio using specified provider

        Args:
            text: Text content to convert
            provider: Provider name ('elevenlabs' or 'aws_polly')
            category: Content category

        Returns:
            Tuple of (audio_data, duration_seconds, cost_usd)
        """
        try:
            if provider == 'elevenlabs':
                return self._generate_with_elevenlabs(text)
            elif provider == 'aws_polly':
                return self._generate_with_polly(text)
            else:
                logger.error(f"Unknown audio provider: {provider}")
                return None, 0, 0.0

        except Exception as e:
            logger.error(f"Error with {provider} provider: {str(e)}")
            return None, 0, 0.0

    def _generate_with_elevenlabs(self, text: str) -> Tuple[Optional[bytes], int, float]:
        """
        Generate audio using ElevenLabs API

        Args:
            text: Text to convert

        Returns:
            Tuple of (audio_data, duration_seconds, cost_usd)
        """
        if not self.elevenlabs_api_key:
            logger.error("ElevenLabs API key not configured")
            return None, 0, 0.0

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key
        }

        data = {
            "text": text,
            "model_id": AUDIO_SETTINGS['model'],
            "voice_settings": {
                "stability": AUDIO_SETTINGS['stability'],
                "similarity_boost": AUDIO_SETTINGS['similarity_boost'],
                "style": 0.0,
                "use_speaker_boost": True
            }
        }

        try:
            logger.info("Generating audio with ElevenLabs...")
            response = requests.post(url, json=data, headers=headers, timeout=300)  # 5 minute timeout

            if response.status_code != 200:
                logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None, 0, 0.0

            audio_data = response.content

            # Estimate duration (rough calculation: 150 words per minute)
            words = len(text.split())
            duration = int((words / 150) * 60)

            # Calculate cost (approximate)
            characters = len(text)
            cost = characters * 0.00003  # ~$0.03 per 1000 characters

            logger.info(f"ElevenLabs audio generated: {len(audio_data)} bytes, ~{duration}s duration")
            return audio_data, duration, cost

        except requests.exceptions.RequestException as e:
            logger.error(f"ElevenLabs request error: {str(e)}")
            return None, 0, 0.0

    def _generate_with_polly(self, text: str) -> Tuple[Optional[bytes], int, float]:
        """
        Generate audio using AWS Polly

        Args:
            text: Text to convert

        Returns:
            Tuple of (audio_data, duration_seconds, cost_usd)
        """
        try:
            logger.info("Generating audio with AWS Polly...")

            # Use SSML for better pronunciation and pacing
            ssml_text = f"""
            <speak>
                <prosody rate="medium" pitch="medium">
                    {text}
                </prosody>
            </speak>
            """

            response = self.polly_client.synthesize_speech(
                Text=ssml_text,
                TextType='ssml',
                OutputFormat='mp3',
                VoiceId='Matthew',  # High-quality English voice
                Engine='neural'     # Better quality than standard
            )

            audio_data = response['AudioStream'].read()

            # Estimate duration
            words = len(text.split())
            duration = int((words / 150) * 60)

            # AWS Polly cost (approximate: $4 per 1M characters for Neural voices)
            characters = len(text)
            cost = (characters / 1000000) * 4.0

            logger.info(f"AWS Polly audio generated: {len(audio_data)} bytes, ~{duration}s duration")
            return audio_data, duration, cost

        except Exception as e:
            logger.error(f"AWS Polly error: {str(e)}")
            return None, 0, 0.0

    def _upload_audio_to_s3(self, audio_data: bytes, category: str, date: str) -> Optional[str]:
        """
        Upload audio file to S3

        Args:
            audio_data: Audio file bytes
            category: Content category
            date: Processing date

        Returns:
            S3 key or None if failed
        """
        try:
            # Generate S3 key with organized structure
            filename = f"daily-brief-{category}-{date}.mp3"
            s3_key = get_s3_key('audio', f"news-briefs/{date}/{filename}")

            # Upload with metadata
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=audio_data,
                ContentType='audio/mpeg',
                Metadata={
                    'category': category,
                    'date': date,
                    'type': 'news-brief',
                    'generated_at': datetime.utcnow().isoformat()
                },
                # Make publicly accessible
                ACL='public-read'
            )

            logger.info(f"Audio uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return None

    def _estimate_audio_cost(self, text: str) -> float:
        """
        Estimate cost for audio generation

        Args:
            text: Text content

        Returns:
            Estimated cost in USD
        """
        characters = len(text)

        if self.provider == 'elevenlabs':
            return characters * 0.00003  # ~$0.03 per 1000 characters
        else:  # aws_polly
            return (characters / 1000000) * 4.0  # $4 per 1M characters

    def regenerate_audio(self, category: str, date: str) -> Dict[str, any]:
        """
        Regenerate audio for a specific brief

        Args:
            category: Category name
            date: Processing date

        Returns:
            Regeneration results
        """
        logger.info(f"Regenerating audio for {category} on {date}")

        # Get the brief
        brief = self.brief_model.get_brief(category, date)
        if not brief:
            return {'error': 'Brief not found'}

        if brief.get('status') != 'generated':
            return {'error': 'Brief is not ready for audio generation'}

        # Check budget
        estimated_cost = self._estimate_audio_cost(brief['content'])
        if cost_tracker.get_daily_cost() + estimated_cost > COST_OPTIMIZATION['target_daily_cost']:
            return {'error': 'Daily budget exceeded'}

        try:
            result = self._generate_brief_audio(brief, date)

            if result['success']:
                logger.info(f"Successfully regenerated audio for {category}")
            else:
                logger.warning(f"Failed to regenerate audio for {category}: {result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error regenerating audio for {category}: {str(e)}")
            return {'error': str(e)}

    def get_audio_generation_stats(self, date: str) -> Dict[str, any]:
        """
        Get audio generation statistics for a specific date

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            Audio generation statistics
        """
        job = self.job_model.get_job(date)
        if not job:
            return {'error': 'No audio generation job found for date'}

        engine_data = job.get('engines', {}).get('audio_engine', {})

        return {
            'date': date,
            'status': engine_data.get('status'),
            'audio_files_generated': engine_data.get('audio_files_generated', 0),
            'total_audio_duration': engine_data.get('total_audio_duration', 0),
            'duration': engine_data.get('duration'),
            'started_at': engine_data.get('started_at'),
            'completed_at': engine_data.get('completed_at'),
            'error_message': engine_data.get('error_message')
        }


def lambda_handler(event, context):
    """
    AWS Lambda handler for audio generation

    Expected event format:
    {
        "date": "2024-01-15",  # optional, defaults to today
        "category": "general-tech"  # optional, if provided only generates for this category
    }
    """
    try:
        date = event.get('date')
        category = event.get('category')

        engine = AudioGenerationEngine()

        if category:
            # Generate audio for specific category only
            brief = engine.brief_model.get_brief(category, date or datetime.utcnow().strftime('%Y-%m-%d'))
            if not brief:
                return {
                    'statusCode': 404,
                    'body': {'error': 'Brief not found'}
                }

            result = engine._generate_brief_audio(brief, date or datetime.utcnow().strftime('%Y-%m-%d'))
            return {
                'statusCode': 200,
                'body': {
                    'category': category,
                    'result': result
                }
            }
        else:
            # Generate all daily audio
            results = engine.generate_daily_audio(date)
            return {
                'statusCode': 200,
                'body': results
            }

    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


if __name__ == '__main__':
    # For local testing
    engine = AudioGenerationEngine()
    results = engine.generate_daily_audio()
    print(f"Audio generation completed: {results}")