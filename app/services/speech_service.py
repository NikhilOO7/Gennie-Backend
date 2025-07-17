import os
import io
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from google.cloud import speech_v1
from google.cloud.speech_v1 import types
from google.api_core import exceptions
import numpy as np
import wave

class SpeechService:
    def __init__(self):
        """Initialize Google Cloud Speech-to-Text client"""
        self.client = speech_v1.SpeechAsyncClient()
        self.streaming_client = speech_v1.SpeechClient()
        
        # Supported audio formats
        self.audio_formats = {
            'wav': speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            'flac': speech_v1.RecognitionConfig.AudioEncoding.FLAC,
            'mp3': speech_v1.RecognitionConfig.AudioEncoding.MP3,
            'webm': speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            'ogg': speech_v1.RecognitionConfig.AudioEncoding.OGG_OPUS,
        }
        
        # Default configuration
        self.default_config = {
            'language_code': 'en-US',
            'enable_automatic_punctuation': True,
            'enable_word_time_offsets': False,
            'model': 'latest_long',
            'use_enhanced': True,
        }
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str = 'wav',
        sample_rate: int = 16000,
        language_code: str = 'en-US',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Transcribe audio data to text
        
        Args:
            audio_data: Audio data in bytes
            audio_format: Audio format (wav, flac, mp3, webm, ogg)
            sample_rate: Sample rate in Hz
            language_code: Language code for transcription
            **kwargs: Additional configuration options
            
        Returns:
            Dict containing transcript and metadata
        """
        try:
            # Get audio encoding
            encoding = self.audio_formats.get(audio_format.lower())
            if not encoding:
                raise ValueError(f"Unsupported audio format: {audio_format}")
            
            # Special handling for WebM - don't specify sample rate
            # Let Google Cloud Speech detect it from the header
            if audio_format.lower() == 'webm':
                # Build recognition config without sample_rate_hertz
                config = speech_v1.RecognitionConfig(
                    encoding=encoding,
                    language_code=language_code,
                    enable_automatic_punctuation=kwargs.get(
                        'enable_automatic_punctuation', 
                        self.default_config['enable_automatic_punctuation']
                    ),
                    enable_word_time_offsets=kwargs.get(
                        'enable_word_time_offsets',
                        self.default_config['enable_word_time_offsets']
                    ),
                    model=kwargs.get('model', self.default_config['model']),
                    use_enhanced=kwargs.get('use_enhanced', self.default_config['use_enhanced']),
                    audio_channel_count=kwargs.get('audio_channel_count', 1),
                    # Don't specify sample_rate_hertz for WebM
                )
            else:
                # For other formats, use the provided sample rate
                config = speech_v1.RecognitionConfig(
                    encoding=encoding,
                    sample_rate_hertz=sample_rate,
                    language_code=language_code,
                    enable_automatic_punctuation=kwargs.get(
                        'enable_automatic_punctuation', 
                        self.default_config['enable_automatic_punctuation']
                    ),
                    enable_word_time_offsets=kwargs.get(
                        'enable_word_time_offsets',
                        self.default_config['enable_word_time_offsets']
                    ),
                    model=kwargs.get('model', self.default_config['model']),
                    use_enhanced=kwargs.get('use_enhanced', self.default_config['use_enhanced']),
                    audio_channel_count=kwargs.get('audio_channel_count', 1),
                )
            
            # Create audio object
            audio = speech_v1.RecognitionAudio(content=audio_data)
            
            # Perform transcription
            response = await self.client.recognize(
                config=config,
                audio=audio
            )
            
            # Process results
            transcripts = []
            words = []
            confidence_scores = []
            
            for result in response.results:
                # Get best alternative
                alternative = result.alternatives[0]
                transcripts.append(alternative.transcript)
                confidence_scores.append(alternative.confidence)
                
                # Extract word timings if enabled
                if kwargs.get('enable_word_time_offsets'):
                    for word_info in alternative.words:
                        words.append({
                            'word': word_info.word,
                            'start_time': word_info.start_time.total_seconds(),
                            'end_time': word_info.end_time.total_seconds(),
                        })
            
            return {
                'transcript': ' '.join(transcripts),
                'confidence': sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                'words': words,
                'language': language_code,
                'duration': self._get_audio_duration(audio_data, audio_format, sample_rate),
            }
            
        except exceptions.GoogleAPIError as e:
            raise Exception(f"Google Speech API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Transcription error: {str(e)}")

    async def streaming_transcribe(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        sample_rate: int = 16000,
        language_code: str = 'en-US',
        interim_results: bool = True,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Perform streaming transcription
        
        Args:
            audio_stream: Async generator yielding audio chunks
            sample_rate: Sample rate in Hz
            language_code: Language code for transcription
            interim_results: Whether to return interim results
            **kwargs: Additional configuration options
            
        Yields:
            Dict containing transcription updates
        """
        # Build streaming config
        config = speech_v1.StreamingRecognitionConfig(
            config=speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model='latest_short',
            ),
            interim_results=interim_results,
            single_utterance=kwargs.get('single_utterance', False),
        )
        
        # Create request generator
        async def request_generator():
            # Send config first
            yield speech_v1.StreamingRecognizeRequest(
                streaming_config=config
            )
            
            # Send audio chunks
            async for chunk in audio_stream:
                yield speech_v1.StreamingRecognizeRequest(
                    audio_content=chunk
                )
        
        # Process streaming responses
        try:
            # Use sync client with asyncio
            responses = await asyncio.to_thread(
                self.streaming_client.streaming_recognize,
                request_generator()
            )
            
            for response in responses:
                for result in response.results:
                    # Get best alternative
                    alternative = result.alternatives[0]
                    
                    yield {
                        'transcript': alternative.transcript,
                        'is_final': result.is_final,
                        'confidence': alternative.confidence if result.is_final else None,
                        'stability': result.stability if hasattr(result, 'stability') else None,
                        'language': language_code,
                    }
                    
        except exceptions.GoogleAPIError as e:
            yield {
                'error': f"Google Speech API error: {str(e)}",
                'is_final': True,
            }
        except Exception as e:
            yield {
                'error': f"Streaming error: {str(e)}",
                'is_final': True,
            }
    
    def _get_audio_duration(self, audio_data: bytes, format: str, sample_rate: int) -> float:
        """Calculate audio duration in seconds"""
        try:
            if format == 'wav':
                with io.BytesIO(audio_data) as audio_io:
                    with wave.open(audio_io, 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        return frames / float(rate)
            else:
                # Estimate based on data size for other formats
                # This is approximate and format-dependent
                bytes_per_second = sample_rate * 2  # 16-bit audio
                return len(audio_data) / bytes_per_second
        except:
            return 0.0
    
    async def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        # This is a subset of supported languages
        # Full list: https://cloud.google.com/speech-to-text/docs/languages
        return [
            {'code': 'en-US', 'name': 'English (US)'},
            {'code': 'en-GB', 'name': 'English (UK)'},
            {'code': 'es-ES', 'name': 'Spanish (Spain)'},
            {'code': 'es-MX', 'name': 'Spanish (Mexico)'},
            {'code': 'fr-FR', 'name': 'French'},
            {'code': 'de-DE', 'name': 'German'},
            {'code': 'it-IT', 'name': 'Italian'},
            {'code': 'pt-BR', 'name': 'Portuguese (Brazil)'},
            {'code': 'ru-RU', 'name': 'Russian'},
            {'code': 'ja-JP', 'name': 'Japanese'},
            {'code': 'ko-KR', 'name': 'Korean'},
            {'code': 'zh-CN', 'name': 'Chinese (Simplified)'},
            {'code': 'hi-IN', 'name': 'Hindi'},
            {'code': 'ar-SA', 'name': 'Arabic'},
        ]
    
    async def validate_audio(self, audio_data: bytes, format: str) -> Dict[str, Any]:
        """Validate audio data before transcription"""
        try:
            # Check file size (max 10MB for non-streaming)
            max_size = 10 * 1024 * 1024
            if len(audio_data) > max_size:
                return {
                    'valid': False,
                    'error': f'Audio file too large. Maximum size: {max_size/1024/1024}MB'
                }
            
            # Check format support
            if format.lower() not in self.audio_formats:
                return {
                    'valid': False,
                    'error': f'Unsupported format: {format}. Supported: {list(self.audio_formats.keys())}'
                }
            
            # For WAV files, validate header
            if format.lower() == 'wav':
                try:
                    with io.BytesIO(audio_data) as audio_io:
                        with wave.open(audio_io, 'rb') as wav_file:
                            channels = wav_file.getnchannels()
                            sample_width = wav_file.getsampwidth()
                            framerate = wav_file.getframerate()
                            
                            return {
                                'valid': True,
                                'channels': channels,
                                'sample_width': sample_width,
                                'sample_rate': framerate,
                                'duration': wav_file.getnframes() / float(framerate)
                            }
                except Exception as e:
                    return {
                        'valid': False,
                        'error': f'Invalid WAV file: {str(e)}'
                    }
            
            return {'valid': True}
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Audio validation error: {str(e)}'
            }

# Create singleton instance
speech_service = SpeechService()