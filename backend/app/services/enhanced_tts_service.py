# app/services/enhanced_tts_service.py
"""
Enhanced Text-to-Speech Service with quality improvements and real-time streaming
COMPLETE VERSION maintaining ALL existing functionality while adding enhancements
"""

import asyncio
import io
import base64
import hashlib
import json
import logging
import time
import re
from typing import Optional, Dict, Any, List, AsyncGenerator
from google.cloud import texttospeech_v1 as texttospeech
from google.api_core import exceptions

# Optional dependencies - graceful fallback if not available
try:
    from pydub import AudioSegment
    from pydub.effects import normalize, compress_dynamic_range
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("pydub not available - audio enhancement features disabled")

logger = logging.getLogger(__name__)

class EnhancedTTSService:
    """Enhanced Text-to-Speech Service with quality improvements"""
    
    def __init__(self):
        """Initialize Enhanced TTS service"""
        self.client = texttospeech.TextToSpeechAsyncClient()
        self.voices_client = texttospeech.TextToSpeechClient()
        
        # Cache for voices and audio
        self._voices_cache = None
        self._audio_cache = {}
        self.cache_ttl = 3600  # 1 hour
        
        # Default voice settings (backward compatibility)
        self.default_voice = {
            'language_code': 'en-US',
            'name': 'en-US-Neural2-F',  # Female neural voice
            'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
        }
        
        # Audio format mappings (backward compatibility)
        self.audio_formats = {
            'mp3': texttospeech.AudioEncoding.MP3,
            'wav': texttospeech.AudioEncoding.LINEAR16,
            'ogg': texttospeech.AudioEncoding.OGG_OPUS,
        }
        
        # Enhanced voice settings
        self.premium_voices = {
            'en-US': {
                'female': ['en-US-Neural2-F', 'en-US-Neural2-H', 'en-US-Studio-O'],
                'male': ['en-US-Neural2-D', 'en-US-Neural2-J', 'en-US-Studio-Q']
            },
            'en-GB': {
                'female': ['en-GB-Neural2-F', 'en-GB-Studio-F'],
                'male': ['en-GB-Neural2-D', 'en-GB-Studio-B']
            }
        }
        
        # Quality enhancement settings
        self.audio_enhancement = {
            'normalize_volume': True,
            'dynamic_range_compression': True,
            'optimal_sample_rate': 24000,
            'optimal_bitrate': 128000
        }
        
        # SSML enhancement patterns
        self.ssml_patterns = {
            'emphasis_words': ['important', 'crucial', 'attention', 'warning', 'note'],
            'pause_patterns': [
                (r'\.{3}', '<break time="800ms"/>'),  # Ellipsis
                (r'[\.\!\?]\s+', '<break time="500ms"/>'),  # Sentence end
                (r'[,;]\s+', '<break time="300ms"/>'),  # Comma, semicolon
                (r':\s+', '<break time="400ms"/>'),  # Colon
            ],
            'prosody_patterns': [
                (r'\b(very|extremely|really)\s+(\w+)', r'<prosody rate="slow" pitch="+2st">\1 \2</prosody>'),
                (r'\b(quickly|fast|rapid)\b', r'<prosody rate="fast">\1</prosody>'),
                (r'\b(slowly|careful|deliberate)\b', r'<prosody rate="slow">\1</prosody>'),
            ]
        }
        
        logger.info("Enhanced TTS service initialized")
    
    async def warm_up_model(self):
        """Pre-warm the model to reduce first-call latency"""
        try:
            await self.synthesize_speech("Hello", voice_name=self.default_voice['name'])
        except:
            pass
    
    async def synthesize_speech(
        self,
        text: str,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
        audio_format: str = 'mp3',
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0,
        enable_ssml: bool = False,
        use_human_ssml: bool = True,
        enhance_quality: bool = True,
        use_smart_ssml: bool = True,
        emotion: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Enhanced speech synthesis with quality improvements (backward compatible)
        
        Args:
            text: Text to synthesize
            voice_name: Specific voice to use
            language_code: Language code
            audio_format: Output format (mp3, wav, ogg)
            speaking_rate: Speech rate (0.25-4.0)
            pitch: Voice pitch (-20 to 20 semitones)
            volume_gain_db: Volume adjustment (-96 to 16 dB)
            enable_ssml: Whether text contains SSML markup
            use_human_ssml: Add natural breaks for better speech
            enhance_quality: Apply audio enhancement
            use_smart_ssml: Apply intelligent SSML markup
            emotion: Emotional tone ('happy', 'sad', 'excited', 'calm')
            
        Returns:
            Enhanced synthesis result
        """
        try:
            start_time = time.time()
            
            # Check cache first
            cache_key = self._generate_cache_key(text, voice_name, audio_format, speaking_rate, pitch)
            cached_result = self._get_cached_audio(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for audio synthesis: {cache_key[:16]}...")
                return cached_result
            
            # Optimize voice selection
            optimized_voice = await self._optimize_voice_selection(
                voice_name, language_code, emotion
            )
            
            # Use defaults if not provided (backward compatibility)
            if not voice_name:
                voice_name = optimized_voice['name']
            if not language_code:
                language_code = optimized_voice['language_code']
            
            # Enhance text with smart SSML
            enhanced_text = text
            if use_smart_ssml and not enable_ssml:
                enhanced_text = self._apply_smart_ssml(text, emotion)
                enable_ssml = True
            elif use_human_ssml and not enable_ssml:
                # Backward compatibility: create SSML with breaks
                enhanced_text = self.create_ssml_with_breaks(text, break_time="400ms")
                enable_ssml = True
            
            # Build synthesis configuration
            synthesis_config = await self._build_synthesis_config(
                enhanced_text, {'name': voice_name, 'language_code': language_code}, 
                audio_format, speaking_rate, pitch, volume_gain_db, enable_ssml, **kwargs
            )
            
            # Perform synthesis
            response = await self.client.synthesize_speech(request=synthesis_config)
            
            # Enhance audio quality if requested and pydub is available
            if enhance_quality and PYDUB_AVAILABLE:
                enhanced_audio = await self._enhance_audio_quality(
                    response.audio_content, audio_format
                )
            else:
                enhanced_audio = response.audio_content
            
            # Build result (backward compatible format)
            result = {
                "success": True,
                "audio_content": enhanced_audio,
                "audio_data": base64.b64encode(enhanced_audio).decode(),
                "audio_format": audio_format,
                "voice_name": voice_name,
                "language_code": language_code,
                "text_hash": hashlib.md5(text.encode()).hexdigest(),
                "synthesis_time_ms": round((time.time() - start_time) * 1000, 2),
                "enhanced": True,
                "emotion": emotion,
                "cache_hit": False
            }
            
            # Cache the result
            self._cache_audio(cache_key, result)
            
            logger.info(f"Synthesized {len(text)} characters in {result['synthesis_time_ms']}ms")
            return result
            
        except exceptions.GoogleAPIError as e:
            logger.error(f"Google TTS API error: {str(e)}")
            return {
                'success': False,
                'error': f'TTS synthesis failed: {str(e)}',
                'error_type': 'api_error'
            }
        except Exception as e:
            logger.error(f"TTS synthesis error: {str(e)}")
            return {
                'success': False,
                'error': f'TTS synthesis failed: {str(e)}',
                'error_type': 'processing_error'
            }
    
    async def synthesize_streaming(
        self,
        text: str,
        voice_name: Optional[str] = None,
        audio_format: str = 'mp3',
        chunk_size: int = 200,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream synthesis for long text with real-time chunks
        
        Args:
            text: Text to synthesize
            voice_name: Voice to use
            audio_format: Output format
            chunk_size: Characters per chunk
            **kwargs: Additional synthesis options
            
        Yields:
            Dictionary with chunk data and metadata
        """
        try:
            # Split text into chunks for streaming
            chunks = self._split_text_for_streaming(text, chunk_size)
            
            chunk_index = 0
            text_buffer = ""
            
            for chunk in chunks:
                chunk_index += 1
                text_buffer += " " + chunk if text_buffer else chunk
                
                # Synthesize chunk
                result = await self.synthesize_speech(
                    chunk, voice_name=voice_name, audio_format=audio_format, **kwargs
                )
                
                if result.get('success'):
                    yield {
                        "type": "audio_chunk",
                        "chunk_index": chunk_index,
                        "audio_data": result["audio_data"],
                        "audio_content": result["audio_content"],
                        "text": chunk,
                        "text_buffer": text_buffer.strip(),
                        "is_final": chunk_index == len(chunks),
                        "total_chunks": len(chunks),
                        "audio_format": audio_format,
                        "synthesis_time_ms": result.get("synthesis_time_ms", 0)
                    }
                else:
                    yield {
                        "type": "error",
                        "chunk_index": chunk_index,
                        "error": result.get("error", "Chunk synthesis failed"),
                        "text": chunk,
                        "is_final": False
                    }
            
            # Send final confirmation
            if chunk_index > 0:
                final_result = await self.synthesize_speech(
                    text_buffer.strip(), voice_name=voice_name, 
                    audio_format=audio_format, **kwargs
                )
                
                if final_result.get('success'):
                    yield {
                        "type": "synthesis_complete",
                        "total_chunks": chunk_index,
                        "total_text": text_buffer.strip(),
                        "final_audio_data": final_result["audio_data"],
                        "audio_format": audio_format,
                        "is_final": True,
                        "synthesis_time_ms": final_result.get("synthesis_time_ms", 0)
                    }
                else:
                    yield {
                        "type": "error",
                        "chunk_index": chunk_index,
                        "error": final_result.get("error", "Final synthesis failed"),
                        "text": text_buffer.strip(),
                        "is_final": True
                    }
                    
        except Exception as e:
            logger.error(f"Streaming synthesis error: {str(e)}")
            yield {
                "type": "error",
                "error": str(e),
                "is_final": True
            }
    
    async def _enhance_audio_quality(self, audio_data: bytes, audio_format: str) -> bytes:
        """
        Enhance audio quality using pydub
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format
            
        Returns:
            Enhanced audio bytes
        """
        if not PYDUB_AVAILABLE:
            return audio_data
        
        try:
            # Convert to AudioSegment
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data), 
                format=audio_format
            )
            
            # Apply enhancements
            if self.audio_enhancement['normalize_volume']:
                audio = normalize(audio)
            
            if self.audio_enhancement['dynamic_range_compression']:
                # Apply mild compression for better quality
                audio = compress_dynamic_range(audio, threshold=-10.0, ratio=2.0)
            
            # Export enhanced audio
            output_buffer = io.BytesIO()
            audio.export(output_buffer, format=audio_format)
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.warning(f"Audio enhancement failed: {str(e)}, using original")
            return audio_data
    
    def _clean_ssml(self, ssml_text: str) -> str:
        """Clean and validate SSML markup"""
        # Remove nested emphasis tags
        ssml_text = re.sub(r'<emphasis[^>]*>([^<]*)<emphasis[^>]*>([^<]*)</emphasis>([^<]*)</emphasis>', 
                          r'<emphasis level="moderate">\1\2\3</emphasis>', ssml_text)
        
        # Ensure proper nesting of prosody tags
        ssml_text = re.sub(r'<prosody[^>]*>([^<]*)<prosody[^>]*>', r'<prosody>\1<prosody>', ssml_text)
        
        # Remove empty tags
        ssml_text = re.sub(r'<[^>]+></[^>]+>', '', ssml_text)
        
        return ssml_text
    
    async def _build_synthesis_config(
        self, text: str, voice_config: Dict[str, Any], audio_format: str,
        speaking_rate: float, pitch: float, volume_gain_db: float, enable_ssml: bool, **kwargs
    ):
        """Build synthesis configuration"""
        
        # Input configuration
        if enable_ssml:
            synthesis_input = texttospeech.SynthesisInput(ssml=text)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Voice configuration
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config['language_code'],
            name=voice_config['name'],
        )
        
        # Audio configuration with enhancement
        audio_encoding = self.audio_formats.get(audio_format.lower(), texttospeech.AudioEncoding.MP3)
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=audio_encoding,
            speaking_rate=max(0.25, min(4.0, speaking_rate)),
            pitch=max(-20.0, min(20.0, pitch)),
            volume_gain_db=max(-96.0, min(16.0, volume_gain_db)),
            sample_rate_hertz=kwargs.get('sample_rate', self.audio_enhancement['optimal_sample_rate']),
            effects_profile_id=['telephony-class-application'] if audio_format == 'mp3' else None
        )
        
        return texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
    
    def _find_natural_break_point(self, text: str) -> int:
        """Find a natural break point in text for chunking"""
        # Look for sentence endings
        for i in range(len(text) - 1, max(0, len(text) - 200), -1):
            if text[i] in '.!?':
                return i + 1
        
        # Look for comma or other punctuation
        for i in range(len(text) - 1, max(0, len(text) - 100), -1):
            if text[i] in ',;:':
                return i + 1
        
        # Look for word boundary
        for i in range(len(text) - 1, max(0, len(text) - 50), -1):
            if text[i] == ' ':
                return i
        
        # Fallback to middle of text
        return len(text) // 2
    
    def _generate_cache_key(self, text: str, voice_name: str, audio_format: str, 
                          speaking_rate: float, pitch: float) -> str:
        """Generate cache key for audio"""
        key_data = f"{text}:{voice_name}:{audio_format}:{speaking_rate}:{pitch}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cached_audio(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached audio if available and not expired"""
        if cache_key in self._audio_cache:
            cached_data, timestamp = self._audio_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_data
            else:
                # Remove expired cache
                del self._audio_cache[cache_key]
        return None
    
    def _cache_audio(self, cache_key: str, result: Dict[str, Any]):
        """Cache audio result"""
        # Don't cache if audio data is too large (>1MB)
        if len(result.get("audio_data", "")) < 1024 * 1024:
            self._audio_cache[cache_key] = (result, time.time())
            
            # Clean old cache entries if cache is getting too large
            if len(self._audio_cache) > 100:
                self._cleanup_cache()
    
    def _cleanup_cache(self):
        """Remove old cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._audio_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self._audio_cache[key]
    
    def _extract_language_from_voice(self, voice_name: str) -> str:
        """Extract language code from voice name"""
        parts = voice_name.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}-{parts[1]}"
        return "en-US"
    
    # New enhanced methods
    async def _optimize_voice_selection(
        self,
        voice_name: Optional[str],
        language_code: Optional[str],
        emotion: Optional[str]
    ) -> Dict[str, Any]:
        """Intelligently select optimal voice"""
        
        # If specific voice provided, validate and use it
        if voice_name:
            return {
                'name': voice_name,
                'language_code': language_code or self._extract_language_from_voice(voice_name)
            }
        
        # Auto-select based on language and emotion
        lang_code = language_code or 'en-US'
        
        # Get premium voices for language
        if lang_code in self.premium_voices:
            voices = self.premium_voices[lang_code]
            
            # Select based on emotion
            if emotion in ['calm', 'professional', 'gentle']:
                selected_voice = voices['female'][0]  # Calm female voice
            elif emotion in ['authoritative', 'confident', 'serious']:
                selected_voice = voices['male'][0]   # Authoritative male voice
            elif emotion in ['friendly', 'warm', 'happy']:
                selected_voice = voices['female'][1] if len(voices['female']) > 1 else voices['female'][0]
            else:
                # Default to best quality voice
                selected_voice = voices['female'][0]
        else:
            # Fallback for unsupported languages
            selected_voice = f"{lang_code}-Standard-A"
        
        return {
            'name': selected_voice,
            'language_code': lang_code
        }
    
    def _apply_smart_ssml(self, text: str, emotion: Optional[str] = None) -> str:
        """Apply intelligent SSML markup for better speech"""
        
        # Start with SSML wrapper
        ssml_text = f'<speak>{text}</speak>'
        
        # Apply emotion-based prosody
        if emotion:
            prosody_attrs = self._get_emotion_prosody(emotion)
            ssml_text = f'<speak><prosody {prosody_attrs}>{text}</prosody></speak>'
        
        # Apply pause patterns
        for pattern, replacement in self.ssml_patterns['pause_patterns']:
            ssml_text = re.sub(pattern, replacement, ssml_text)
        
        # Apply prosody patterns
        for pattern, replacement in self.ssml_patterns['prosody_patterns']:
            ssml_text = re.sub(pattern, replacement, ssml_text, flags=re.IGNORECASE)
        
        # Add emphasis to important words
        for word in self.ssml_patterns['emphasis_words']:
            pattern = rf'\b{word}\b'
            replacement = f'<emphasis level="moderate">{word}</emphasis>'
            ssml_text = re.sub(pattern, replacement, ssml_text, flags=re.IGNORECASE)
        
        # Clean up any malformed SSML
        ssml_text = self._clean_ssml(ssml_text)
        
        return ssml_text
    
    def _get_emotion_prosody(self, emotion: str) -> str:
        """Get prosody attributes for emotion"""
        emotion_mappings = {
            'happy': 'rate="1.1" pitch="+2st" volume="+2dB"',
            'excited': 'rate="1.2" pitch="+4st" volume="+3dB"',
            'sad': 'rate="0.9" pitch="-2st" volume="-1dB"',
            'calm': 'rate="0.95" pitch="-1st" volume="0dB"',
            'professional': 'rate="1.0" pitch="0st" volume="0dB"',
            'urgent': 'rate="1.15" pitch="+1st" volume="+2dB"',
            'gentle': 'rate="0.9" pitch="-1st" volume="-1dB"'
        }
        return emotion_mappings.get(emotion.lower(), 'rate="1.0" pitch="0st" volume="0dB"')
    
    # Backward compatibility methods from original TTS service
    async def synthesize_speech_streaming(self, text: str, voice_name: str = None):
        """Stream TTS output for lower latency (backward compatibility)"""
        # Split text into smaller chunks
        chunks = self._split_text_for_streaming(text)
        
        for chunk in chunks:
            # Process each chunk immediately
            result = await self.synthesize_speech(chunk, voice_name)
            if result.get('success'):
                yield result['audio_content']
    
    def _split_text_for_streaming(self, text: str, chunk_size: int = 200) -> List[str]:
        """Split text into smaller chunks for streaming (backward compatibility)"""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            # Calculate end position
            end_pos = min(current_pos + chunk_size, len(text))
            
            # If we're not at the end, find a natural break point
            if end_pos < len(text):
                chunk_text = text[current_pos:end_pos]
                break_point = self._find_natural_break_point(chunk_text)
                if break_point > 0:
                    end_pos = current_pos + break_point
            
            # Extract chunk
            chunk = text[current_pos:end_pos].strip()
            if chunk:
                chunks.append(chunk)
            
            current_pos = end_pos
        
        return chunks
    
    def create_ssml_with_breaks(
        self,
        text: str,
        break_time: str = "400ms",
        emphasis_words: Optional[List[str]] = None
    ) -> str:
        """Create SSML with natural breaks (backward compatibility)"""
        ssml_parts = ['<speak>']
        
        # Split into sentences
        sentences = re.split(r'([.!?]+)', text)
        
        for i, sentence in enumerate(sentences):
            # Add emphasis to specific words
            if emphasis_words:
                for word in emphasis_words:
                    sentence = sentence.replace(
                        word,
                        f'<emphasis level="strong">{word}</emphasis>'
                    )
            
            ssml_parts.append(sentence)
            
            # Add break between sentences
            if i < len(sentences) - 1:
                ssml_parts.append(f'<break time="{break_time}"/>')
        
        ssml_parts.append('</speak>')
        return ''.join(ssml_parts)
    
    # Additional backward compatibility methods
    async def get_voices(self, language_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available voices (backward compatibility)"""
        # Implementation would fetch from Google Cloud TTS API
        # For now, return a basic list
        return [
            {"name": "en-US-Neural2-F", "language_code": "en-US", "ssml_gender": "FEMALE"},
            {"name": "en-US-Neural2-D", "language_code": "en-US", "ssml_gender": "MALE"},
            {"name": "en-US-Neural2-H", "language_code": "en-US", "ssml_gender": "FEMALE"},
            {"name": "en-US-Neural2-J", "language_code": "en-US", "ssml_gender": "MALE"},
        ]
    
    async def get_voice_preview(
        self,
        voice_name: str,
        preview_text: Optional[str] = None
    ) -> bytes:
        """Generate a voice preview (backward compatibility)"""
        if not preview_text:
            preview_text = "Hello! This is a preview of the selected voice."
        
        result = await self.synthesize_speech(
            text=preview_text,
            voice_name=voice_name,
            audio_format="mp3"
        )
        
        if result.get("success"):
            return result["audio_content"]
        else:
            raise Exception(result.get("error", "Voice preview failed"))
    
    def estimate_audio_duration(
        self,
        text: str,
        speaking_rate: float = 1.0
    ) -> float:
        """Estimate audio duration based on text length (backward compatibility)"""
        # Average speaking rate is ~150 words per minute
        words = len(text.split())
        words_per_second = 2.5 * speaking_rate
        return words / words_per_second
    
    async def batch_synthesize(
        self,
        texts: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Synthesize multiple texts in batch (backward compatibility)"""
        results = []
        
        for text in texts:
            try:
                result = await self.synthesize_speech(text, **kwargs)
                results.append(result)
            except Exception as e:
                results.append({
                    'error': str(e),
                    'text': text[:50] + '...' if len(text) > 50 else text
                })
        
        return results


# Create enhanced singleton instance
enhanced_tts_service = EnhancedTTSService()

# Backward compatibility alias
tts_service = enhanced_tts_service