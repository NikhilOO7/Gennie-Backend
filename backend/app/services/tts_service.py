import os
import io
import base64
from typing import Optional, Dict, Any, List
from google.cloud import texttospeech_v1 as texttospeech
from google.api_core import exceptions
import hashlib
import json

class TTSService:
    def __init__(self):
        """Initialize Google Cloud Text-to-Speech client"""
        self.client = texttospeech.TextToSpeechAsyncClient()
        self.voices_client = texttospeech.TextToSpeechClient()
        
        # Cache for voices list
        self._voices_cache = None
        
        # Default voice settings
        self.default_voice = {
            'language_code': 'en-US',
            'name': 'en-US-Neural2-F',  # Female neural voice
            'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE
        }
        
        # Audio format mappings
        self.audio_formats = {
            'mp3': texttospeech.AudioEncoding.MP3,
            'wav': texttospeech.AudioEncoding.LINEAR16,
            'ogg': texttospeech.AudioEncoding.OGG_OPUS,
        }

        self.warm_up_model()

    async def warm_up_model(self):
        """Pre-warm the model to reduce first-call latency"""
        try:
            await self.synthesize_speech("Hello", voice_name=self.default_voice['name'])
        except:
            pass
    
    async def synthesize_speech_streaming(self, text: str, voice_name: str = None):
        """Stream TTS output for lower latency"""
        # Split text into smaller chunks
        chunks = self._split_text_for_streaming(text)
        
        for chunk in chunks:
            # Process each chunk immediately
            result = await self.synthesize_speech(chunk, voice_name)
            yield result['audio_content']
    
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
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convert text to speech
        
        Args:
            text: Text to synthesize
            voice_name: Voice name (e.g., 'en-US-Neural2-F')
            language_code: Language code (e.g., 'en-US')
            audio_format: Output format (mp3, wav, ogg)
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            volume_gain_db: Volume gain (-96.0 to 16.0)
            enable_ssml: Whether text contains SSML markup
            
        Returns:
            Dict containing audio data and metadata
        """
        try:
            # Use defaults if not provided
            if not voice_name:
                voice_name = self.default_voice['name']
            if not language_code:
                language_code = voice_name.split('-')[0] + '-' + voice_name.split('-')[1]
            
            # Build synthesis input
            if enable_ssml:
                synthesis_input = texttospeech.SynthesisInput(ssml=text)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build voice selection
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                name=voice_name,
            )
            
            # Build audio config
            audio_encoding = self.audio_formats.get(audio_format.lower())
            if not audio_encoding:
                raise ValueError(f"Unsupported audio format: {audio_format}")
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=max(0.25, min(4.0, speaking_rate)),
                pitch=max(-20.0, min(20.0, pitch)),
                volume_gain_db=max(-96.0, min(16.0, volume_gain_db)),
                sample_rate_hertz=kwargs.get('sample_rate', 24000),
            )
            
            # Perform synthesis
            response = await self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            
            # Calculate text hash for caching
            text_hash = hashlib.md5(
                f"{text}{voice_name}{audio_format}{speaking_rate}{pitch}".encode()
            ).hexdigest()
            
            return {
                'audio_content': response.audio_content,
                'audio_format': audio_format,
                'text_hash': text_hash,
                'voice_name': voice_name,
                'language_code': language_code,
                'char_count': len(text),
                'settings': {
                    'speaking_rate': speaking_rate,
                    'pitch': pitch,
                    'volume_gain_db': volume_gain_db,
                }
            }
            
        except exceptions.GoogleAPIError as e:
            raise Exception(f"Google TTS API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Speech synthesis error: {str(e)}")
    
    async def synthesize_ssml(self, ssml_text: str, **kwargs) -> Dict[str, Any]:
        """
        Synthesize speech from SSML markup
        
        Args:
            ssml_text: SSML-formatted text
            **kwargs: Additional synthesis parameters
            
        Returns:
            Dict containing audio data and metadata
        """
        # Wrap in speak tags if not already present
        if not ssml_text.strip().startswith('<speak>'):
            ssml_text = f'<speak>{ssml_text}</speak>'
        
        return await self.synthesize_speech(
            text=ssml_text,
            enable_ssml=True,
            **kwargs
        )
    
    async def get_voices(self, language_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available voices
        
        Args:
            language_code: Filter by language code
            
        Returns:
            List of available voices
        """
        try:
            # Use cache if available
            if self._voices_cache is None:
                response = await self.client.list_voices()
                self._voices_cache = response.voices
            
            voices = []
            for voice in self._voices_cache:
                # Filter by language if specified
                if language_code and not any(
                    lc == language_code for lc in voice.language_codes
                ):
                    continue
                
                # Determine voice type
                voice_type = 'Standard'
                if 'Neural2' in voice.name:
                    voice_type = 'Neural2'
                elif 'Studio' in voice.name:
                    voice_type = 'Studio'
                elif 'Wavenet' in voice.name:
                    voice_type = 'WaveNet'
                elif 'News' in voice.name:
                    voice_type = 'News'
                elif 'Journey' in voice.name:
                    voice_type = 'Journey'
                
                voices.append({
                    'name': voice.name,
                    'language_codes': list(voice.language_codes),
                    'ssml_gender': self._gender_to_string(voice.ssml_gender),
                    'type': voice_type,
                    'natural_sample_rate_hertz': voice.natural_sample_rate_hertz,
                })
            
            # Sort by type priority and name
            type_priority = {
                'Neural2': 0,
                'Studio': 1,
                'Journey': 2,
                'WaveNet': 3,
                'News': 4,
                'Standard': 5
            }
            
            voices.sort(key=lambda v: (
                type_priority.get(v['type'], 999),
                v['name']
            ))
            
            return voices
            
        except exceptions.GoogleAPIError as e:
            raise Exception(f"Error fetching voices: {str(e)}")
    
    async def get_voice_preview(
        self,
        voice_name: str,
        preview_text: Optional[str] = None
    ) -> bytes:
        """
        Generate a voice preview
        
        Args:
            voice_name: Voice to preview
            preview_text: Custom preview text
            
        Returns:
            Audio data for preview
        """
        if not preview_text:
            preview_text = "Hello! This is a preview of the selected voice."
        
        result = await self.synthesize_speech(
            text=preview_text,
            voice_name=voice_name,
            audio_format='mp3',
        )
        
        return result['audio_content']
    
    def _gender_to_string(self, gender: texttospeech.SsmlVoiceGender) -> str:
        """Convert gender enum to string"""
        if gender == texttospeech.SsmlVoiceGender.MALE:
            return 'Male'
        elif gender == texttospeech.SsmlVoiceGender.FEMALE:
            return 'Female'
        elif gender == texttospeech.SsmlVoiceGender.NEUTRAL:
            return 'Neutral'
        else:
            return 'Unspecified'
    
    def create_ssml_with_breaks(
        self,
        text: str,
        break_time: str = "500ms",
        emphasis_words: Optional[List[str]] = None
    ) -> str:
        """
        Create SSML markup with breaks and emphasis
        
        Args:
            text: Plain text
            break_time: Break duration
            emphasis_words: Words to emphasize
            
        Returns:
            SSML-formatted text
        """
        ssml_parts = ['<speak>']
        
        # Split into sentences
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
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
    
    def estimate_audio_duration(
        self,
        text: str,
        speaking_rate: float = 1.0
    ) -> float:
        """
        Estimate audio duration based on text length
        
        Args:
            text: Text to synthesize
            speaking_rate: Speaking rate multiplier
            
        Returns:
            Estimated duration in seconds
        """
        # Average speaking rate is ~150 words per minute
        words = len(text.split())
        words_per_second = 2.5 * speaking_rate
        return words / words_per_second
    
    async def batch_synthesize(
        self,
        texts: List[str],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Synthesize multiple texts in batch
        
        Args:
            texts: List of texts to synthesize
            **kwargs: Synthesis parameters
            
        Returns:
            List of synthesis results
        """
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

# Create singleton instance
tts_service = TTSService()