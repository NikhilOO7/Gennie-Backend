from app import logger
from app.config import settings
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Request, status, Body
from typing import Optional, List, Dict, Any
import io
import base64
import json
from datetime import datetime

from app.services.speech_service import speech_service
from app.services.tts_service import tts_service
from app.routers.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    enable_punctuation: bool = Form(True),
    enable_word_timing: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe audio file to text
    
    Args:
        audio: Audio file to transcribe
        language_code: Language code for transcription
        enable_punctuation: Add automatic punctuation
        enable_word_timing: Include word-level timestamps
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Get file extension
        file_ext = audio.filename.split('.')[-1].lower()
        if file_ext not in ['wav', 'mp3', 'ogg', 'webm', 'flac']:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {file_ext}"
            )
        
        # Validate audio
        validation = await speech_service.validate_audio(audio_data, file_ext)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=validation['error']
            )
        
        # Perform transcription
        result = await speech_service.transcribe_audio(
            audio_data=audio_data,
            audio_format=file_ext,
            language_code=language_code,
            enable_automatic_punctuation=enable_punctuation,
            enable_word_time_offsets=enable_word_timing,
            sample_rate=validation.get('sample_rate', 16000)
        )
        
        return {
            "success": True,
            "transcript": result['transcript'],
            "confidence": result['confidence'],
            "language": result['language'],
            "duration": result['duration'],
            "words": result.get('words', []) if enable_word_timing else None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

@router.post("/transcribe/base64")
async def transcribe_base64_audio(
    audio_data: str,
    audio_format: str = "wav",
    language_code: str = "en-US",
    sample_rate: int = 16000,
    current_user: User = Depends(get_current_user)
):
    """Transcribe base64-encoded audio data"""
    try:
        # Decode base64
        audio_bytes = base64.b64decode(audio_data)
        
        # Validate audio
        validation = await speech_service.validate_audio(audio_bytes, audio_format)
        if not validation['valid']:
            raise HTTPException(
                status_code=400,
                detail=validation['error']
            )
        
        # Perform transcription
        result = await speech_service.transcribe_audio(
            audio_data=audio_bytes,
            audio_format=audio_format,
            language_code=language_code,
            sample_rate=sample_rate,
            enable_automatic_punctuation=True,
        )
        
        return {
            "success": True,
            "transcript": result['transcript'],
            "confidence": result['confidence'],
            "language": result['language'],
            "duration": result['duration'],
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

# In app/routers/voice.py, update the synthesize endpoint:

@router.post("/synthesize")
async def synthesize_speech(
    request: Request,
    text: str = Body(...),
    voice_name: Optional[str] = Body(None),
    language_code: Optional[str] = Body("en-US"),
    audio_format: str = Body("mp3"),
    speaking_rate: float = Body(1.0),
    pitch: float = Body(0.0),
    return_base64: bool = Body(True),
    current_user: User = Depends(get_current_user)
):
    """
    Convert text to speech
    """
    try:
        # Check if we should use mock
        use_mock = request.headers.get("X-Use-Mock", "false").lower() == "true"
        use_mock = use_mock or getattr(settings, 'USE_MOCK_VOICE', False)
        
        if use_mock:
            # Use mock TTS
            logger.info("Using mock TTS service")
            
            # Generate mock audio (silent audio or beep)
            import base64
            
            # Create a simple beep sound or use pre-recorded audio
            # For now, return a base64 encoded string of silence
            mock_audio_data = b'\x00' * 1000  # Simple silence
            
            if return_base64:
                return {
                    "success": True,
                    "audio_data": base64.b64encode(mock_audio_data).decode(),
                    "audio_format": audio_format,
                    "voice_name": voice_name or "mock-voice",
                    "text_hash": str(hash(text)),
                    "_mock": True
                }
            else:
                audio_io = io.BytesIO(mock_audio_data)
                return StreamingResponse(
                    audio_io,
                    media_type=f'audio/{audio_format}',
                    headers={
                        'Content-Disposition': f'inline; filename="speech.{audio_format}"',
                        'X-Mock': 'true'
                    }
                )
        
        # Use real TTS service
        result = await tts_service.synthesize_speech(
            text=text,
            voice_name=voice_name,
            language_code=language_code,
            audio_format=audio_format,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )
        
        if return_base64:
            # Return base64-encoded audio
            audio_base64 = base64.b64encode(result['audio_content']).decode()
            return {
                "success": True,
                "audio_data": audio_base64,
                "audio_format": result.get('audio_format', audio_format),
                "voice_name": result.get('voice_name', voice_name),
                "text_hash": result.get('text_hash', str(hash(text))),
            }
        else:
            # Return audio stream
            audio_io = io.BytesIO(result['audio_content'])
            
            # Set appropriate content type
            content_types = {
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'ogg': 'audio/ogg',
            }
            content_type = content_types.get(audio_format, 'audio/mpeg')
            
            return StreamingResponse(
                audio_io,
                media_type=content_type,
                headers={
                    'Content-Disposition': f'inline; filename="speech.{audio_format}"',
                    'X-Voice-Name': result.get('voice_name', ''),
                    'X-Text-Hash': result.get('text_hash', ''),
                }
            )
            
    except Exception as e:
        logger.error(f"Speech synthesis failed: {str(e)}", exc_info=True)
        
        # Try fallback to mock if real TTS fails
        if not use_mock and settings.ENVIRONMENT == "development":
            logger.warning("Falling back to mock TTS due to error")
            
            # Simple mock response
            import base64
            mock_audio_data = b'\x00' * 1000
            
            return {
                "success": True,
                "audio_data": base64.b64encode(mock_audio_data).decode(),
                "audio_format": audio_format,
                "voice_name": "mock-voice-fallback",
                "text_hash": str(hash(text)),
                "_mock": True,
                "_error": str(e)
            }
        
        raise HTTPException(
            status_code=500,
            detail=f"Speech synthesis failed: {str(e)}"
        )

@router.post("/synthesize/ssml")
async def synthesize_ssml(
    ssml_text: str,
    voice_name: Optional[str] = None,
    audio_format: str = "mp3",
    current_user: User = Depends(get_current_user)
):
    """Synthesize speech from SSML markup"""
    try:
        result = await tts_service.synthesize_ssml(
            ssml_text=ssml_text,
            voice_name=voice_name,
            audio_format=audio_format,
        )
        
        audio_io = io.BytesIO(result['audio_content'])
        content_types = {
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg',
        }
        
        return StreamingResponse(
            audio_io,
            media_type=content_types.get(audio_format, 'audio/mpeg'),
            headers={
                'Content-Disposition': f'inline; filename="speech.{audio_format}"',
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SSML synthesis failed: {str(e)}"
        )

@router.get("/voices")
async def get_available_voices(
    language_code: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of available TTS voices"""
    try:
        voices = await tts_service.get_voices(language_code)
        return {
            "success": True,
            "voices": voices,
            "total": len(voices),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch voices: {str(e)}"
        )

@router.post("/voices/preview")
async def preview_voice(
    voice_name: str,
    preview_text: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Generate a preview of a specific voice"""
    try:
        audio_content = await tts_service.get_voice_preview(
            voice_name=voice_name,
            preview_text=preview_text
        )
        
        audio_io = io.BytesIO(audio_content)
        return StreamingResponse(
            audio_io,
            media_type="audio/mpeg",
            headers={
                'Content-Disposition': 'inline; filename="preview.mp3"',
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice preview failed: {str(e)}"
        )

@router.get("/languages")
async def get_supported_languages(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported languages for speech recognition"""
    try:
        languages = await speech_service.get_supported_languages()
        return {
            "success": True,
            "languages": languages,
            "total": len(languages),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch languages: {str(e)}"
        )

@router.post("/stream/start")
async def start_streaming_session(
    language_code: str = "en-US",
    interim_results: bool = True,
    single_utterance: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Start a streaming transcription session
    Returns session configuration for WebSocket connection
    """
    try:
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Return session configuration
        return {
            "success": True,
            "session_id": session_id,
            "config": {
                "language_code": language_code,
                "interim_results": interim_results,
                "single_utterance": single_utterance,
                "websocket_url": f"/ws/voice/{session_id}",
            },
            "instructions": {
                "connect": "Connect to the WebSocket URL",
                "send": "Send audio chunks as binary frames",
                "receive": "Receive transcription updates as JSON",
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start streaming session: {str(e)}"
        )

@router.post("/batch/synthesize")
async def batch_synthesize(
    texts: List[str],
    voice_name: Optional[str] = None,
    audio_format: str = "mp3",
    current_user: User = Depends(get_current_user)
):
    """Synthesize multiple texts in batch"""
    try:
        if len(texts) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 texts allowed per batch"
            )
        
        results = await tts_service.batch_synthesize(
            texts=texts,
            voice_name=voice_name,
            audio_format=audio_format,
        )
        
        # Convert audio to base64
        processed_results = []
        for i, result in enumerate(results):
            if 'error' in result:
                processed_results.append({
                    "index": i,
                    "success": False,
                    "error": result['error'],
                })
            else:
                processed_results.append({
                    "index": i,
                    "success": True,
                    "audio_data": base64.b64encode(result['audio_content']).decode(),
                    "audio_format": result['audio_format'],
                    "text_hash": result['text_hash'],
                })
        
        return {
            "success": True,
            "results": processed_results,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch synthesis failed: {str(e)}"
        )