# app/routers/voice_mock.py
"""
Mock voice endpoints for testing without Google Cloud setup
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
import logging
import random

from app.routers.auth import get_current_user
from app.models import User

logger = logging.getLogger(__name__)
router = APIRouter()

# Mock transcriptions for testing
MOCK_TRANSCRIPTIONS = [
    "Hello, how are you today?",
    "What's the weather like?",
    "Can you help me with something?",
    "Tell me a joke",
    "What time is it?",
    "I need assistance with a problem",
    "Thank you for your help",
    "That's interesting, tell me more",
    "How does this work?",
    "What do you recommend?"
]

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    enable_punctuation: bool = Form(True),
    enable_word_timing: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """
    Mock transcribe audio file to text
    Returns a random transcription for testing
    """
    try:
        # Read audio data (just to consume it)
        audio_data = await audio.read()
        
        # Log the request
        logger.info(f"Mock transcription requested by user {current_user.id}")
        logger.info(f"Audio file: {audio.filename}, size: {len(audio_data)} bytes")
        
        # Get a random transcription
        transcript = random.choice(MOCK_TRANSCRIPTIONS)
        
        # Simulate some processing time
        import asyncio
        await asyncio.sleep(0.5)
        
        return {
            "success": True,
            "transcript": transcript,
            "confidence": 0.95,
            "language": language_code,
            "duration": 2.5,
            "words": None,
            "_mock": True  # Indicator that this is mock data
        }
        
    except Exception as e:
        logger.error(f"Mock transcription error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Mock transcription failed: {str(e)}"
        )

@router.post("/synthesize")
async def synthesize_speech(
    text: str,
    voice_name: Optional[str] = None,
    language_code: Optional[str] = None,
    audio_format: str = "mp3",
    speaking_rate: float = 1.0,
    pitch: float = 0.0,
    return_base64: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Mock text-to-speech synthesis
    Returns a dummy audio response
    """
    try:
        logger.info(f"Mock TTS requested by user {current_user.id}")
        logger.info(f"Text: {text[:50]}...")
        
        # For mock, just return a success response with dummy data
        if return_base64:
            # Return a tiny valid MP3 file (silence) as base64
            # This is a minimal valid MP3 file (about 200 bytes)
            dummy_mp3 = b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            import base64
            audio_base64 = base64.b64encode(dummy_mp3).decode('utf-8')
            
            return {
                "success": True,
                "audio_data": audio_base64,
                "duration": 1.0,
                "text_length": len(text),
                "_mock": True
            }
        else:
            return {
                "success": True,
                "message": "Mock audio synthesis completed",
                "duration": 1.0,
                "_mock": True
            }
            
    except Exception as e:
        logger.error(f"Mock TTS error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Mock synthesis failed: {str(e)}"
        )

@router.get("/voices")
async def get_available_voices(
    language_code: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of mock TTS voices"""
    return {
        "success": True,
        "voices": [
            {
                "name": "en-US-Standard-A",
                "language_codes": ["en-US"],
                "ssml_gender": "FEMALE",
                "natural_sample_rate_hertz": 24000,
                "type": "Standard"
            },
            {
                "name": "en-US-Standard-B", 
                "language_codes": ["en-US"],
                "ssml_gender": "MALE",
                "natural_sample_rate_hertz": 24000,
                "type": "Standard"
            },
            {
                "name": "en-US-Neural2-C",
                "language_codes": ["en-US"],
                "ssml_gender": "FEMALE", 
                "natural_sample_rate_hertz": 24000,
                "type": "Neural2"
            }
        ],
        "total": 3,
        "_mock": True
    }

@router.get("/languages")
async def get_supported_languages(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported languages for speech recognition"""
    return {
        "success": True,
        "languages": [
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-GB", "name": "English (UK)"},
            {"code": "es-ES", "name": "Spanish (Spain)"},
            {"code": "fr-FR", "name": "French (France)"},
            {"code": "de-DE", "name": "German (Germany)"},
            {"code": "it-IT", "name": "Italian (Italy)"},
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
            {"code": "ja-JP", "name": "Japanese (Japan)"},
            {"code": "ko-KR", "name": "Korean (Korea)"},
            {"code": "zh-CN", "name": "Chinese (Simplified)"}
        ],
        "total": 10,
        "_mock": True
    }