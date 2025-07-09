import os
import io
import asyncio
from typing import Dict, Any, Optional, List
import logging
from google.cloud import speech_v1
from google.cloud import texttospeech_v1
from pydub import AudioSegment
import base64

logger = logging.getLogger(__name__)

class SpeechService:
    """Service for Google Cloud Speech-to-Text and Text-to-Speech"""
    
    def __init__(self):
        self.stt_client = speech_v1.SpeechClient()
        self.tts_client = texttospeech_v1.TextToSpeechClient()
        
        # Default configurations
        self.default_language = "en-US"
        self.default_voice = "en-US-Neural2-F"
        self.sample_rate = 16000
        
        logger.info("SpeechService initialized")
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str = "webm",
        language_code: str = None,
        enable_punctuation: bool = True
    ) -> Dict[str, Any]:
        """Transcribe audio to text"""
        try:
            # Convert audio format if needed
            if audio_format in ["webm", "mp3", "ogg"]:
                audio_data = await self._convert_audio_format(audio_data, audio_format)
            
            # Configure recognition
            audio = speech_v1.RecognitionAudio(content=audio_data)
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                language_code=language_code or self.default_language,
                enable_automatic_punctuation=enable_punctuation,
                model="latest_long",
                use_enhanced=True
            )
            
            # Perform transcription
            response = await asyncio.to_thread(
                self.stt_client.recognize,
                config=config,
                audio=audio
            )
            
            # Extract results
            if response.results:
                result = response.results[0]
                if result.alternatives:
                    return {
                        "transcript": result.alternatives[0].transcript,
                        "confidence": result.alternatives[0].confidence,
                        "language": language_code or self.default_language,
                        "words": self._extract_word_timings(result)
                    }
            
            return {
                "transcript": "",
                "confidence": 0.0,
                "language": language_code or self.default_language,
                "error": "No transcription results"
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {
                "transcript": "",
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def synthesize_speech(
        self,
        text: str,
        voice_name: str = None,
        language_code: str = None,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        output_format: str = "mp3"
    ) -> bytes:
        """Convert text to speech"""
        try:
            # Configure synthesis input
            synthesis_input = texttospeech_v1.SynthesisInput(text=text)
            
            # Configure voice
            voice = texttospeech_v1.VoiceSelectionParams(
                language_code=language_code or self.default_language,
                name=voice_name or self.default_voice
            )
            
            # Configure audio
            audio_encoding = {
                "mp3": texttospeech_v1.AudioEncoding.MP3,
                "wav": texttospeech_v1.AudioEncoding.LINEAR16,
                "ogg": texttospeech_v1.AudioEncoding.OGG_OPUS
            }.get(output_format, texttospeech_v1.AudioEncoding.MP3)
            
            audio_config = texttospeech_v1.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                sample_rate_hertz=24000
            )
            
            # Perform synthesis
            response = await asyncio.to_thread(
                self.tts_client.synthesize_speech,
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"TTS error: {str(e)}")
            raise
    
    async def get_available_voices(self, language_code: str = None) -> List[Dict[str, Any]]:
        """Get list of available TTS voices"""
        try:
            response = await asyncio.to_thread(
                self.tts_client.list_voices,
                language_code=language_code
            )
            
            voices = []
            for voice in response.voices:
                voices.append({
                    "name": voice.name,
                    "language_codes": voice.language_codes,
                    "gender": voice.ssml_gender.name,
                    "natural": "Neural" in voice.name or "Wavenet" in voice.name
                })
            
            return voices
            
        except Exception as e:
            logger.error(f"Error listing voices: {str(e)}")
            return []
    
    async def _convert_audio_format(self, audio_data: bytes, input_format: str) -> bytes:
        """Convert audio to LINEAR16 format for Google Speech"""
        try:
            # Load audio
            audio = AudioSegment.from_file(
                io.BytesIO(audio_data),
                format=input_format
            )
            
            # Convert to mono, 16kHz, 16-bit PCM
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(self.sample_rate)
            audio = audio.set_sample_width(2)  # 16-bit
            
            # Export as WAV
            buffer = io.BytesIO()
            audio.export(buffer, format="wav")
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Audio conversion error: {str(e)}")
            raise
    
    def _extract_word_timings(self, result) -> List[Dict[str, Any]]:
        """Extract word-level timing information"""
        words = []
        for word_info in result.alternatives[0].words:
            words.append({
                "word": word_info.word,
                "start_time": word_info.start_time.total_seconds(),
                "end_time": word_info.end_time.total_seconds()
            })
        return words

# Create singleton instance
speech_service = SpeechService()