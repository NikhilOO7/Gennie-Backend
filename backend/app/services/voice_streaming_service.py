import asyncio
import io
import base64
from typing import AsyncGenerator, Dict, Any, Optional
from app.services.tts_service import tts_service
from app.services.gemini_service import gemini_service
import logging

logger = logging.getLogger(__name__)

class VoiceStreamingService:
    def __init__(self):
        self.chunk_size = 1024  # Audio chunk size in bytes
        self.min_text_length = 20  # Minimum text length before synthesis
        self.max_buffer_size = 200  # Maximum text buffer size
    
    async def stream_voice_response(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_settings: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream TTS audio in real-time as text is generated
        
        Args:
            text_stream: Async generator of text chunks
            voice_settings: Voice configuration
            user_preferences: User preferences for voice
            
        Yields:
            Dict containing audio chunks and metadata
        """
        text_buffer = ""
        sentence_endings = {'.', '!', '?', '\n'}
        
        try:
            async for text_chunk in text_stream:
                text_buffer += text_chunk
                
                # Check if we have a complete sentence or buffer is full
                should_synthesize = (
                    any(ending in text_chunk for ending in sentence_endings) or
                    len(text_buffer) >= self.max_buffer_size
                )
                
                if should_synthesize and len(text_buffer.strip()) >= self.min_text_length:
                    # Synthesize accumulated text
                    audio_chunk = await self._synthesize_chunk(
                        text_buffer.strip(),
                        voice_settings,
                        user_preferences
                    )
                    
                    if audio_chunk:
                        yield {
                            "type": "audio_chunk",
                            "text": text_buffer.strip(),
                            "audio_data": audio_chunk["audio_data"],
                            "audio_format": audio_chunk.get("audio_format", "mp3"),
                            "chunk_index": audio_chunk.get("chunk_index", 0),
                            "is_final": False
                        }
                    
                    text_buffer = ""
            
            # Handle remaining text in buffer
            if text_buffer.strip():
                audio_chunk = await self._synthesize_chunk(
                    text_buffer.strip(),
                    voice_settings,
                    user_preferences
                )
                
                if audio_chunk:
                    yield {
                        "type": "audio_chunk",
                        "text": text_buffer.strip(),
                        "audio_data": audio_chunk["audio_data"],
                        "audio_format": audio_chunk.get("audio_format", "mp3"),
                        "chunk_index": audio_chunk.get("chunk_index", 0),
                        "is_final": True
                    }
                    
        except Exception as e:
            logger.error(f"Voice streaming error: {str(e)}")
            yield {
                "type": "error",
                "error": str(e),
                "is_final": True
            }
    
    async def _synthesize_chunk(
        self,
        text: str,
        voice_settings: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Synthesize a single text chunk to audio"""
        try:
            # Apply voice optimizations
            optimized_text = await self._optimize_text_for_voice(text, user_preferences)
            
            # Get voice configuration
            voice_config = self._get_voice_config(voice_settings, user_preferences)
            
            # Synthesize speech
            result = await tts_service.synthesize_speech(
                text=optimized_text,
                voice_name=voice_config.get("voice_name"),
                audio_format=voice_config.get("audio_format", "mp3"),
                speaking_rate=voice_config.get("speaking_rate", 1.0),
                pitch=voice_config.get("pitch", 0.0),
            )
            
            if result.get("success"):
                return {
                    "audio_data": base64.b64encode(result["audio_content"]).decode(),
                    "audio_format": result.get("audio_format", "mp3"),
                    "text_hash": str(hash(optimized_text)),
                    "chunk_index": 0  # Could be incremented for multiple chunks
                }
                
        except Exception as e:
            logger.error(f"Chunk synthesis failed: {str(e)}")
            return None
    
    async def _optimize_text_for_voice(
        self,
        text: str,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> str:
        """Optimize text for better voice synthesis"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Add natural pauses for better speech rhythm
        text = text.replace(', ', ', ')  # Ensure space after commas
        text = text.replace('. ', '. ')  # Ensure space after periods
        
        # Handle abbreviations and numbers if needed
        # This could be expanded based on user preferences
        
        return text
    
    def _get_voice_config(
        self,
        voice_settings: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get consolidated voice configuration"""
        config = {
            "voice_name": "en-US-Neural2-C",  # Default female voice
            "audio_format": "mp3",
            "speaking_rate": 1.0,
            "pitch": 0.0,
        }
        
        # Apply user preferences
        if user_preferences and "voice_settings" in user_preferences:
            config.update(user_preferences["voice_settings"])
        
        # Apply session-specific settings
        if voice_settings:
            config.update(voice_settings)
        
        return config

# Create singleton instance
voice_streaming_service = VoiceStreamingService()