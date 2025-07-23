# app/services/enhanced_speech_service.py
"""
Enhanced Speech-to-Text Service with quality improvements and real-time streaming
COMPLETE VERSION preserving ALL existing functionality while adding enhancements
"""

import asyncio
import io
import base64
import logging
import time
import json
from typing import Optional, Dict, Any, List, Tuple, AsyncGenerator
from google.cloud import speech_v1 as speech
from google.api_core import exceptions
import numpy as np

# Optional dependencies with graceful fallback
try:
    from pydub import AudioSegment
    from pydub.effects import normalize, low_pass_filter, high_pass_filter
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

try:
    import webrtcvad
    WEBRTC_VAD_AVAILABLE = True
except ImportError:
    WEBRTC_VAD_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class EnhancedSpeechService:
    """Enhanced Speech-to-Text Service with quality improvements"""
    
    def __init__(self):
        """Initialize Enhanced Speech service"""
        self.client = speech.SpeechAsyncClient()
        self.streaming_client = speech.SpeechClient()
        
        # Audio preprocessing settings
        self.target_sample_rate = 16000
        self.target_channels = 1
        self.auto_gain_control = True
        self.noise_reduction_enabled = True
        self.echo_cancellation = True
        
        # Voice Activity Detection
        self.vad_enabled = WEBRTC_VAD_AVAILABLE
        self.vad_mode = 3  # Most aggressive
        self.vad_frame_duration = 30  # milliseconds
        
        # Enhanced recognition settings
        self.enhanced_models = {
            'default': 'latest_long',
            'phone_call': 'phone_call',
            'video': 'video',
            'command_and_search': 'command_and_search'
        }
        
        # Language support
        self.supported_languages = [
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-GB", "name": "English (UK)"},
            {"code": "es-ES", "name": "Spanish (Spain)"},
            {"code": "es-US", "name": "Spanish (US)"},
            {"code": "fr-FR", "name": "French"},
            {"code": "de-DE", "name": "German"},
            {"code": "it-IT", "name": "Italian"},
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
            {"code": "ru-RU", "name": "Russian"},
            {"code": "ja-JP", "name": "Japanese"},
            {"code": "ko-KR", "name": "Korean"},
            {"code": "zh-CN", "name": "Chinese (Simplified)"},
            {"code": "zh-TW", "name": "Chinese (Traditional)"},
            {"code": "hi-IN", "name": "Hindi"},
            {"code": "ar-SA", "name": "Arabic"},
        ]
        
        # Initialize VAD if available
        self.vad = None
        if self.vad_enabled:
            try:
                self.vad = webrtcvad.Vad(self.vad_mode)
                logger.info("✅ WebRTC VAD initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize VAD: {str(e)}")
                self.vad_enabled = False
        
        logger.info("🎙️ Enhanced Speech Service initialized")
        logger.info(f"   Audio preprocessing: {'✅' if PYDUB_AVAILABLE else '❌'}")
        logger.info(f"   Voice Activity Detection: {'✅' if self.vad_enabled else '❌'}")
        logger.info(f"   NumPy processing: {'✅' if NUMPY_AVAILABLE else '❌'}")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        language_code: str = "en-US",
        model: str = "default",
        enable_automatic_punctuation: bool = True,
        enable_word_time_offsets: bool = False,
        enable_word_confidence: bool = True,
        audio_format: str = "wav",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced audio transcription with preprocessing
        
        Args:
            audio_data: Raw audio bytes
            language_code: Language code (e.g., 'en-US')
            model: Recognition model to use
            enable_automatic_punctuation: Add punctuation automatically
            enable_word_time_offsets: Include word-level timestamps
            enable_word_confidence: Include confidence scores
            audio_format: Input audio format
            **kwargs: Additional options
            
        Returns:
            Dictionary with transcription results and metadata
        """
        try:
            # Preprocess audio for better quality
            processed_audio = await self._preprocess_audio(audio_data, audio_format)
            
            # Build recognition config
            config = self._build_recognition_config(
                language_code=language_code,
                model=model,
                enable_automatic_punctuation=enable_automatic_punctuation,
                enable_word_time_offsets=enable_word_time_offsets,
                enable_word_confidence=enable_word_confidence,
                **kwargs
            )
            
            # Create recognition request
            audio = speech.RecognitionAudio(content=processed_audio)
            request = speech.RecognizeRequest(config=config, audio=audio)
            
            # Perform recognition
            start_time = time.time()
            response = await self.client.recognize(request=request)
            processing_time = time.time() - start_time
            
            # Process results
            results = self._process_recognition_results(response, processing_time)
            
            logger.info(f"Transcription completed in {processing_time:.2f}s")
            return results
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"Google Speech API error: {str(e)}")
            return {
                'success': False,
                'error': f'Speech recognition failed: {str(e)}',
                'error_type': 'api_error'
            }
        except Exception as e:
            logger.error(f"Speech recognition error: {str(e)}")
            return {
                'success': False,
                'error': f'Speech recognition failed: {str(e)}',
                'error_type': 'processing_error'
            }
    
    async def transcribe_streaming(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language_code: str = "en-US",
        model: str = "default",
        enable_interim_results: bool = True,
        single_utterance: bool = False,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Enhanced streaming transcription with real-time processing
        
        Args:
            audio_stream: Async generator yielding audio chunks
            language_code: Language code
            model: Recognition model
            enable_interim_results: Return partial results
            single_utterance: Stop after first utterance
            **kwargs: Additional options
            
        Yields:
            Dictionary with partial/final transcription results
        """
        try:
            # Build streaming config
            config = self._build_recognition_config(
                language_code=language_code,
                model=model,
                enable_automatic_punctuation=True,
                enable_word_confidence=True,
                **kwargs
            )
            
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=enable_interim_results,
                single_utterance=single_utterance
            )
            
            # Create audio chunks generator
            async def audio_generator():
                # Send initial config
                yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
                
                # Process audio chunks
                async for chunk in audio_stream:
                    try:
                        # Preprocess chunk
                        processed_chunk = await self._preprocess_audio_chunk(chunk)
                        
                        # Apply VAD if enabled
                        if self.vad_enabled and self.vad:
                            if not self._is_speech(processed_chunk):
                                continue  # Skip non-speech frames
                        
                        # Yield audio chunk
                        yield speech.StreamingRecognizeRequest(audio_content=processed_chunk)
                        
                    except Exception as e:
                        logger.warning(f"Error processing audio chunk: {str(e)}")
                        continue
            
            # Perform streaming recognition
            responses = self.streaming_client.streaming_recognize(audio_generator())
            
            for response in responses:
                result = self._process_streaming_result(response)
                if result:
                    yield result
                    
        except exceptions.GoogleAPIError as e:
            logger.error(f"Streaming recognition API error: {str(e)}")
            yield {
                'success': False,
                'error': f'Streaming recognition failed: {str(e)}',
                'error_type': 'api_error'
            }
        except Exception as e:
            logger.error(f"Streaming recognition error: {str(e)}")
            yield {
                'success': False,
                'error': f'Streaming recognition failed: {str(e)}',
                'error_type': 'processing_error'
            }
    
    async def _preprocess_audio(self, audio_data: bytes, audio_format: str = "wav") -> bytes:
        """
        Preprocess audio for better recognition quality
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format
            
        Returns:
            Processed audio bytes
        """
        if not PYDUB_AVAILABLE:
            logger.warning("pydub not available, skipping audio preprocessing")
            return audio_data
        
        try:
            # Convert to AudioSegment for processing
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format=audio_format)
            
            # Normalize audio
            if self.auto_gain_control:
                # Normalize volume to optimal level
                target_dBFS = -20.0
                change_in_dBFS = target_dBFS - audio.dBFS
                audio = audio.apply_gain(change_in_dBFS)
            
            # Convert to target format
            audio = audio.set_frame_rate(self.target_sample_rate)
            audio = audio.set_channels(self.target_channels)
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Apply noise reduction if enabled
            if self.noise_reduction_enabled:
                audio = self._apply_noise_reduction(audio)
            
            # Apply echo cancellation
            if self.echo_cancellation:
                audio = self._apply_echo_cancellation(audio)
            
            # Export as WAV bytes
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="wav")
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.warning(f"Audio preprocessing failed: {str(e)}, using original audio")
            return audio_data
    
    async def _preprocess_audio_chunk(self, chunk: bytes) -> bytes:
        """Preprocess audio chunk for streaming"""
        if not PYDUB_AVAILABLE:
            return chunk
        
        try:
            # Basic preprocessing for real-time chunks
            audio = AudioSegment.from_file(io.BytesIO(chunk), format="wav")
            
            # Quick normalization
            if self.auto_gain_control:
                target_dBFS = -20.0
                if audio.dBFS < target_dBFS - 10:  # Only boost if very quiet
                    change_in_dBFS = min(10, target_dBFS - audio.dBFS)
                    audio = audio.apply_gain(change_in_dBFS)
            
            # Ensure correct format
            audio = audio.set_frame_rate(self.target_sample_rate)
            audio = audio.set_channels(self.target_channels)
            
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format="wav")
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.warning(f"Chunk preprocessing failed: {str(e)}")
            return chunk
    
    def _apply_noise_reduction(self, audio: AudioSegment) -> AudioSegment:
        """Apply basic noise reduction to audio"""
        try:
            # Apply frequency filtering
            # High-pass filter to remove low-frequency noise
            audio = high_pass_filter(audio, 80)
            
            # Low-pass filter to remove high-frequency noise
            audio = low_pass_filter(audio, 8000)
            
            # Apply normalization
            audio = normalize(audio)
            
            return audio
        except Exception as e:
            logger.warning(f"Noise reduction failed: {str(e)}")
            return audio
    
    def _apply_echo_cancellation(self, audio: AudioSegment) -> AudioSegment:
        """Apply basic echo cancellation"""
        try:
            # Simple echo reduction using audio processing
            # This is a basic implementation - real echo cancellation is complex
            
            # Reduce reverb by applying dynamic range compression
            if hasattr(audio, 'compress_dynamic_range'):
                audio = audio.compress_dynamic_range(threshold=-20.0, ratio=4.0)
            
            return audio
        except Exception as e:
            logger.warning(f"Echo cancellation failed: {str(e)}")
            return audio
    
    def _is_speech(self, audio_data: bytes) -> bool:
        """Use VAD to determine if audio contains speech"""
        if not self.vad_enabled or not self.vad:
            return True
        
        try:
            # Convert audio to format expected by VAD
            audio = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Get raw audio data
            raw_data = audio.raw_data
            
            # VAD expects frames of specific duration
            frame_size = int(16000 * self.vad_frame_duration / 1000) * 2  # 16-bit samples
            
            # Check multiple frames
            speech_frames = 0
            total_frames = 0
            
            for i in range(0, len(raw_data) - frame_size, frame_size):
                frame = raw_data[i:i + frame_size]
                if len(frame) == frame_size:
                    if self.vad.is_speech(frame, 16000):
                        speech_frames += 1
                    total_frames += 1
            
            # Return True if majority of frames contain speech
            if total_frames == 0:
                return True
            
            speech_ratio = speech_frames / total_frames
            return speech_ratio > 0.3  # 30% threshold
            
        except Exception as e:
            logger.warning(f"VAD processing failed: {str(e)}")
            return True  # Assume speech if VAD fails
    
    def _build_recognition_config(
        self,
        language_code: str,
        model: str,
        enable_automatic_punctuation: bool,
        enable_word_time_offsets: bool,
        enable_word_confidence: bool,
        **kwargs
    ) -> speech.RecognitionConfig:
        """Build recognition configuration"""
        
        # Map model names
        model_name = self.enhanced_models.get(model, model)
        
        # Alternative language codes if needed
        alternative_language_codes = kwargs.get('alternative_language_codes', [])
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.target_sample_rate,
            language_code=language_code,
            alternative_language_codes=alternative_language_codes,
            model=model_name,
            enable_automatic_punctuation=enable_automatic_punctuation,
            enable_word_time_offsets=enable_word_time_offsets,
            enable_word_confidence=enable_word_confidence,
            max_alternatives=kwargs.get('max_alternatives', 1),
            profanity_filter=kwargs.get('profanity_filter', False),
            use_enhanced=kwargs.get('use_enhanced', True),
            speech_contexts=kwargs.get('speech_contexts', []),
            adaptation=kwargs.get('adaptation', None)
        )
        
        return config
    
    def _process_recognition_results(self, response, processing_time: float) -> Dict[str, Any]:
        """Process recognition results"""
        if not response.results:
            return {
                'success': True,
                'transcript': '',
                'confidence': 0.0,
                'alternatives': [],
                'processing_time': processing_time,
                'word_details': []
            }
        
        # Get best result
        result = response.results[0]
        alternative = result.alternatives[0]
        
        # Extract word details if available
        word_details = []
        if hasattr(alternative, 'words') and alternative.words:
            for word in alternative.words:
                word_info = {
                    'word': word.word,
                    'confidence': getattr(word, 'confidence', 0.0)
                }
                
                # Add timing information if available
                if hasattr(word, 'start_time') and word.start_time:
                    word_info['start_time'] = word.start_time.total_seconds()
                if hasattr(word, 'end_time') and word.end_time:
                    word_info['end_time'] = word.end_time.total_seconds()
                
                word_details.append(word_info)
        
        # Build alternatives list
        alternatives = []
        for alt in result.alternatives:
            alternatives.append({
                'transcript': alt.transcript,
                'confidence': getattr(alt, 'confidence', 0.0)
            })
        
        return {
            'success': True,
            'transcript': alternative.transcript,
            'confidence': getattr(alternative, 'confidence', 0.0),
            'alternatives': alternatives,
            'processing_time': processing_time,
            'word_details': word_details,
            'language_code': response.results[0].language_code if hasattr(response.results[0], 'language_code') else None
        }
    
    def _process_streaming_result(self, response) -> Optional[Dict[str, Any]]:
        """Process streaming recognition result"""
        if not response.results:
            return None
        
        result = response.results[0]
        if not result.alternatives:
            return None
        
        alternative = result.alternatives[0]
        
        return {
            'success': True,
            'transcript': alternative.transcript,
            'confidence': getattr(alternative, 'confidence', 0.0),
            'is_final': result.is_final,
            'stability': getattr(result, 'stability', 0.0),
            'result_end_time': result.result_end_time.total_seconds() if hasattr(result, 'result_end_time') and result.result_end_time else None,
            'channel_tag': getattr(result, 'channel_tag', 0),
            'language_code': getattr(result, 'language_code', None)
        }
    
    # Backward compatibility methods
    async def validate_audio(self, audio_data: bytes, audio_format: str) -> bool:
        """Validate audio data format and content (backward compatibility)"""
        try:
            if not audio_data:
                return False
            
            if PYDUB_AVAILABLE:
                # Try to load the audio
                audio = AudioSegment.from_file(io.BytesIO(audio_data), format=audio_format)
                
                # Check basic properties
                if audio.duration_seconds < 0.1:  # Too short
                    return False
                if audio.duration_seconds > 300:  # Too long (5 minutes)
                    return False
                
                return True
            else:
                # Basic validation without pydub
                return len(audio_data) > 1000  # At least 1KB
                
        except Exception as e:
            logger.warning(f"Audio validation failed: {str(e)}")
            return False
    
    async def transcribe_file(
        self,
        file_path: str,
        language_code: str = "en-US",
        model: str = "default"
    ) -> Dict[str, Any]:
        """Transcribe audio file (backward compatibility)"""
        try:
            with open(file_path, 'rb') as f:
                audio_data = f.read()
            
            # Detect format from file extension
            file_ext = file_path.split('.')[-1].lower()
            
            return await self.transcribe_audio(
                audio_data=audio_data,
                language_code=language_code,
                model=model,
                audio_format=file_ext
            )
            
        except Exception as e:
            logger.error(f"File transcription failed: {str(e)}")
            return {
                'success': False,
                'error': f'File transcription failed: {str(e)}',
                'error_type': 'file_error'
            }
    
    async def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages"""
        return self.supported_languages
    
    async def get_available_models(self) -> Dict[str, str]:
        """Get available recognition models"""
        return {
            'default': 'Latest general model with best accuracy',
            'phone_call': 'Optimized for phone call audio quality',
            'video': 'Optimized for video content',
            'command_and_search': 'Optimized for short commands and search queries'
        }
    
    async def check_service_health(self) -> Dict[str, Any]:
        """Check service health and capabilities"""
        try:
            # Test basic recognition with a small audio sample
            test_audio = b'\x00' * 1024  # Silent audio
            
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="en-US"
            )
            
            audio = speech.RecognitionAudio(content=test_audio)
            request = speech.RecognizeRequest(config=config, audio=audio)
            
            # This should succeed even with silent audio
            await self.client.recognize(request=request)
            
            return {
                'status': 'healthy',
                'features': {
                    'basic_recognition': True,
                    'streaming_recognition': True,
                    'audio_preprocessing': PYDUB_AVAILABLE,
                    'voice_activity_detection': self.vad_enabled,
                    'noise_reduction': PYDUB_AVAILABLE,
                    'echo_cancellation': PYDUB_AVAILABLE
                },
                'supported_languages': len(self.supported_languages),
                'available_models': list(self.enhanced_models.keys())
            }
            
        except Exception as e:
            logger.error(f"Speech service health check failed: {str(e)}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'features': {
                    'basic_recognition': False,
                    'streaming_recognition': False,
                    'audio_preprocessing': PYDUB_AVAILABLE,
                    'voice_activity_detection': self.vad_enabled,
                    'noise_reduction': PYDUB_AVAILABLE,
                    'echo_cancellation': PYDUB_AVAILABLE
                }
            }

# Create service instance
enhanced_speech_service = EnhancedSpeechService()

# Backward compatibility alias
speech_service = enhanced_speech_service