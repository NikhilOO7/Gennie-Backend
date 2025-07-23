# app/routers/voice.py
"""
Voice API Router with enhanced features
COMPLETE VERSION maintaining ALL existing functionality while adding new enhanced capabilities
"""

from app.logger import logger
from app.config import settings
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Body
from fastapi.responses import StreamingResponse
from fastapi import Request, status
from typing import Optional, List, Dict, Any
import io
import base64
import json
from datetime import datetime

# Import both original and enhanced services
try:
    from app.services.enhanced_speech_service import enhanced_speech_service
    from app.services.enhanced_tts_service import enhanced_tts_service
    ENHANCED_SERVICES_AVAILABLE = True
except ImportError:
    logger.warning("Enhanced services not available, falling back to original services")
    ENHANCED_SERVICES_AVAILABLE = False

# Fallback to original services if enhanced ones are not available
if ENHANCED_SERVICES_AVAILABLE:
    speech_service = enhanced_speech_service
    tts_service = enhanced_tts_service
else:
    try:
        from app.services.speech_service import speech_service
        from app.services.tts_service import tts_service
    except ImportError:
        # Create mock services if none available
        speech_service = None
        tts_service = None

from app.routers.auth import get_current_user
from app.models import User

router = APIRouter(tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    enable_punctuation: bool = Form(True),
    enable_word_timing: bool = Form(False),
    model_type: str = Form("conversation"),
    enable_enhancement: bool = Form(True),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe audio file to text with enhanced features
    
    Args:
        audio: Audio file to transcribe
        language_code: Language code for transcription
        enable_punctuation: Add automatic punctuation
        enable_word_timing: Include word-level timestamps
        model_type: Model type (conversation, command, dictation)
        enable_enhancement: Use enhanced processing
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Get file extension
        file_ext = audio.filename.split('.')[-1].lower() if audio.filename and '.' in audio.filename else 'webm'
        
        logger.info(f"Received audio file: {audio.filename}, size: {len(audio_data)} bytes")
        
        # Validate audio
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        if speech_service is None:
            raise HTTPException(status_code=503, detail="Speech service not available")
        
        # Validate audio format
        if hasattr(speech_service, 'validate_audio'):
            is_valid = await speech_service.validate_audio(audio_data, file_ext)
            if not is_valid:
                raise HTTPException(status_code=400, detail="Invalid audio format or content")
        
        # Map model type to enhanced model
        model_mapping = {
            'conversation': 'default',
            'command': 'command_and_search',
            'dictation': 'default',
            'phone': 'phone_call',
            'video': 'video'
        }
        model = model_mapping.get(model_type, 'default')
        
        # Transcribe audio
        if ENHANCED_SERVICES_AVAILABLE and enable_enhancement:
            result = await speech_service.transcribe_audio(
                audio_data=audio_data,
                language_code=language_code,
                model=model,
                enable_automatic_punctuation=enable_punctuation,
                enable_word_time_offsets=enable_word_timing,
                enable_word_confidence=True,
                audio_format=file_ext
            )
        else:
            # Fallback to basic transcription
            result = await speech_service.transcribe_audio(
                audio_data=audio_data,
                language_code=language_code,
                audio_format=file_ext
            )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Transcription failed'))
        
        return {
            "transcript": result.get('transcript', ''),
            "confidence": result.get('confidence', 0.0),
            "language_code": result.get('language_code', language_code),
            "processing_time": result.get('processing_time', 0.0),
            "word_details": result.get('word_details', []) if enable_word_timing else [],
            "alternatives": result.get('alternatives', []),
            "enhanced": ENHANCED_SERVICES_AVAILABLE and enable_enhancement
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice_name: Optional[str] = Form(None),
    language_code: Optional[str] = Form("en-US"),
    audio_format: str = Form("mp3"),
    speaking_rate: float = Form(1.0),
    pitch: float = Form(0.0),
    volume_gain: float = Form(0.0),
    enable_ssml: bool = Form(False),
    enhance_quality: bool = Form(True),
    emotion: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Synthesize text to speech with enhanced features
    
    Args:
        text: Text to synthesize
        voice_name: Specific voice to use
        language_code: Language code
        audio_format: Output format (mp3, wav, ogg)
        speaking_rate: Speech rate (0.25-4.0)
        pitch: Voice pitch (-20 to 20 semitones)
        volume_gain: Volume adjustment (-96 to 16 dB)
        enable_ssml: Whether text contains SSML markup
        enhance_quality: Apply audio enhancement
        emotion: Emotional tone ('happy', 'sad', 'excited', 'calm')
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if len(text) > 5000:
            raise HTTPException(status_code=400, detail="Text too long (max 5000 characters)")
        
        if tts_service is None:
            raise HTTPException(status_code=503, detail="TTS service not available")
        
        # Validate parameters
        if speaking_rate < 0.25 or speaking_rate > 4.0:
            raise HTTPException(status_code=400, detail="Speaking rate must be between 0.25 and 4.0")
        
        if pitch < -20.0 or pitch > 20.0:
            raise HTTPException(status_code=400, detail="Pitch must be between -20 and 20 semitones")
        
        if volume_gain < -96.0 or volume_gain > 16.0:
            raise HTTPException(status_code=400, detail="Volume gain must be between -96 and 16 dB")
        
        # Synthesize speech
        if ENHANCED_SERVICES_AVAILABLE and enhance_quality:
            result = await tts_service.synthesize_speech(
                text=text,
                voice_name=voice_name,
                language_code=language_code,
                audio_format=audio_format,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain,
                enable_ssml=enable_ssml,
                enhance_quality=enhance_quality,
                emotion=emotion
            )
        else:
            # Fallback to basic synthesis
            result = await tts_service.synthesize_speech(
                text=text,
                voice_name=voice_name,
                audio_format=audio_format
            )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Synthesis failed'))
        
        return {
            "audio_data": result.get('audio_data', ''),
            "audio_format": result.get('audio_format', audio_format),
            "voice_name": result.get('voice_name', voice_name),
            "language_code": result.get('language_code', language_code),
            "synthesis_time": result.get('synthesis_time_ms', 0),
            "text_hash": result.get('text_hash', ''),
            "enhanced": result.get('enhanced', False),
            "emotion": result.get('emotion', emotion)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@router.post("/synthesize-stream")
async def synthesize_speech_streaming(
    text: str = Form(...),
    voice_name: Optional[str] = Form(None),
    audio_format: str = Form("mp3"),
    chunk_size: int = Form(200),
    current_user: User = Depends(get_current_user)
):
    """
    Stream synthesis for long text with real-time chunks
    
    Args:
        text: Text to synthesize
        voice_name: Voice to use
        audio_format: Output format
        chunk_size: Characters per chunk
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if tts_service is None:
            raise HTTPException(status_code=503, detail="TTS service not available")
        
        # Stream synthesis
        async def generate_audio_chunks():
            if ENHANCED_SERVICES_AVAILABLE and hasattr(tts_service, 'synthesize_streaming'):
                async for chunk in tts_service.synthesize_streaming(
                    text=text,
                    voice_name=voice_name,
                    audio_format=audio_format,
                    chunk_size=chunk_size
                ):
                    yield f"data: {json.dumps(chunk)}\n\n"
            else:
                # Fallback to basic streaming
                async for audio_content in tts_service.synthesize_speech_streaming(text, voice_name):
                    chunk_data = {
                        "type": "audio_chunk",
                        "audio_data": base64.b64encode(audio_content).decode(),
                        "audio_format": audio_format
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
        
        return StreamingResponse(
            generate_audio_chunks(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Streaming synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Streaming synthesis failed: {str(e)}")

@router.get("/voices")
async def get_available_voices(
    language_code: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available voices
    
    Args:
        language_code: Filter by language code
    """
    try:
        if tts_service is None:
            raise HTTPException(status_code=503, detail="TTS service not available")
        
        if hasattr(tts_service, 'get_voices'):
            voices = await tts_service.get_voices(language_code)
        else:
            # Fallback voice list
            voices = [
                {"name": "en-US-Neural2-F", "language_code": "en-US", "ssml_gender": "FEMALE"},
                {"name": "en-US-Neural2-D", "language_code": "en-US", "ssml_gender": "MALE"},
                {"name": "en-US-Neural2-H", "language_code": "en-US", "ssml_gender": "FEMALE"},
                {"name": "en-US-Neural2-J", "language_code": "en-US", "ssml_gender": "MALE"},
            ]
        
        return {
            "voices": voices,
            "total": len(voices),
            "language_filter": language_code,
            "enhanced": ENHANCED_SERVICES_AVAILABLE
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get voices error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")

@router.post("/voice-preview")
async def generate_voice_preview(
    voice_name: str = Form(...),
    preview_text: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a voice preview
    
    Args:
        voice_name: Voice to preview
        preview_text: Custom preview text
    """
    try:
        if tts_service is None:
            raise HTTPException(status_code=503, detail="TTS service not available")
        
        if not preview_text:
            preview_text = "Hello! This is a preview of the selected voice. How does it sound?"
        
        if hasattr(tts_service, 'get_voice_preview'):
            audio_content = await tts_service.get_voice_preview(voice_name, preview_text)
        else:
            # Fallback to regular synthesis
            result = await tts_service.synthesize_speech(preview_text, voice_name=voice_name)
            if not result.get('success'):
                raise HTTPException(status_code=500, detail=result.get('error', 'Preview failed'))
            audio_content = result['audio_content']
        
        return {
            "audio_data": base64.b64encode(audio_content).decode(),
            "voice_name": voice_name,
            "preview_text": preview_text,
            "audio_format": "mp3"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice preview error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Voice preview failed: {str(e)}")

@router.get("/languages")
async def get_supported_languages(current_user: User = Depends(get_current_user)):
    """Get list of supported languages"""
    try:
        if speech_service and hasattr(speech_service, 'get_supported_languages'):
            languages = await speech_service.get_supported_languages()
        else:
            # Fallback language list
            languages = [
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
                {"code": "hi-IN", "name": "Hindi"},
                {"code": "ar-SA", "name": "Arabic"},
            ]
        
        return {
            "languages": languages,
            "total": len(languages),
            "enhanced": ENHANCED_SERVICES_AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"Get languages error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@router.get("/models")
async def get_available_models(current_user: User = Depends(get_current_user)):
    """Get available speech recognition models"""
    try:
        if speech_service and hasattr(speech_service, 'get_available_models'):
            models = await speech_service.get_available_models()
        else:
            # Fallback model list
            models = {
                'default': 'General purpose model',
                'phone_call': 'Optimized for phone call audio',
                'video': 'Optimized for video content',
                'command_and_search': 'Optimized for commands and search'
            }
        
        return {
            "models": models,
            "enhanced": ENHANCED_SERVICES_AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"Get models error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {str(e)}")

@router.get("/features")
async def get_voice_features():
    """Get available voice features and capabilities"""
    
    features = {
        "transcription": {
            "basic": speech_service is not None,
            "enhanced": ENHANCED_SERVICES_AVAILABLE,
            "streaming": ENHANCED_SERVICES_AVAILABLE,
            "word_timing": ENHANCED_SERVICES_AVAILABLE,
            "confidence_scores": True,
            "multiple_languages": True,
            "noise_reduction": ENHANCED_SERVICES_AVAILABLE,
            "voice_activity_detection": ENHANCED_SERVICES_AVAILABLE
        },
        "synthesis": {
            "basic": tts_service is not None,
            "enhanced": ENHANCED_SERVICES_AVAILABLE,
            "streaming": ENHANCED_SERVICES_AVAILABLE,
            "ssml_support": True,
            "emotion_based": ENHANCED_SERVICES_AVAILABLE,
            "voice_cloning": False,  # Not implemented yet
            "audio_enhancement": ENHANCED_SERVICES_AVAILABLE,
            "smart_ssml": ENHANCED_SERVICES_AVAILABLE
        },
        "audio_processing": {
            "format_conversion": ENHANCED_SERVICES_AVAILABLE,
            "noise_reduction": ENHANCED_SERVICES_AVAILABLE,
            "echo_cancellation": ENHANCED_SERVICES_AVAILABLE,
            "auto_gain_control": ENHANCED_SERVICES_AVAILABLE,
            "quality_enhancement": ENHANCED_SERVICES_AVAILABLE
        },
        "real_time": {
            "streaming_transcription": ENHANCED_SERVICES_AVAILABLE,
            "streaming_synthesis": ENHANCED_SERVICES_AVAILABLE,
            "low_latency": ENHANCED_SERVICES_AVAILABLE,
            "websocket_support": True
        },
        "supported_formats": {
            "input": ["wav", "mp3", "webm", "ogg", "m4a"],
            "output": ["mp3", "wav", "ogg"]
        },
        "dependencies": {
            "pydub": "Available" if ENHANCED_SERVICES_AVAILABLE else "Not available",
            "webrtc_vad": "Available" if ENHANCED_SERVICES_AVAILABLE else "Not available", 
            "numpy": "Available" if ENHANCED_SERVICES_AVAILABLE else "Not available",
            "ffmpeg": "Optional (for additional audio formats)"
        }
    }
    
    return {
        "features": features,
        "enhanced_services": ENHANCED_SERVICES_AVAILABLE,
        "version": "2.0.0" if ENHANCED_SERVICES_AVAILABLE else "1.0.0",
        "status": "ready"
    }

@router.get("/health")
async def voice_health_check():
    """Health check for voice services"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "speech_to_text": {"status": "healthy", "enhanced": ENHANCED_SERVICES_AVAILABLE},
            "text_to_speech": {"status": "healthy", "enhanced": ENHANCED_SERVICES_AVAILABLE}
        }
    }
    
    # Test basic services
    try:
        # Test speech service
        if speech_service and hasattr(speech_service, 'validate_audio'):
            test_audio = b'\x00' * 1000  # Dummy audio data
            await speech_service.validate_audio(test_audio, "wav")
        
        # Test TTS service
        if tts_service and hasattr(tts_service, 'estimate_audio_duration'):
            tts_service.estimate_audio_duration("test")
        
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["services"]["speech_to_text"]["status"] = "error"
        health_status["services"]["speech_to_text"]["error"] = str(e)
    
    return health_status

# Backward compatibility endpoints
@router.post("/transcribe-audio")
async def transcribe_audio_simple(
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    return_confidence: bool = Form(True),
    return_alternatives: bool = Form(False),
    current_user: User = Depends(get_current_user)
):
    """
    Simple audio transcription endpoint (backward compatibility)
    """
    try:
        # Read the audio file
        audio_data = await audio.read()
        logger.info(f"Received audio file: {audio.filename}, size: {len(audio_data)} bytes")
        
        # Get file extension from content type if filename doesn't have one
        file_ext = 'webm'  # Default for browser recordings
        if audio.filename and '.' in audio.filename:
            file_ext = audio.filename.split('.')[-1].lower()
        
        # Validate audio
        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data received")
        
        if speech_service is None:
            raise HTTPException(status_code=503, detail="Speech recognition service unavailable")
        
        # Perform transcription
        result = await speech_service.transcribe_audio(
            audio_data=audio_data,
            language_code=language_code,
            audio_format=file_ext,
            enable_word_confidence=return_confidence
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Transcription failed'))
        
        response = {
            "transcript": result.get('transcript', ''),
            "success": True
        }
        
        if return_confidence:
            response["confidence"] = result.get('confidence', 0.0)
        
        if return_alternatives:
            response["alternatives"] = result.get('alternatives', [])
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simple transcription error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/synthesize-simple")
async def synthesize_speech_simple(
    text: str = Form(...),
    voice: Optional[str] = Form(None),
    language: str = Form("en-US"),
    current_user: User = Depends(get_current_user)
):
    """
    Simple speech synthesis endpoint (backward compatibility)
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if tts_service is None:
            raise HTTPException(status_code=503, detail="Text-to-speech service unavailable")
        
        # Perform synthesis
        result = await tts_service.synthesize_speech(
            text=text,
            voice_name=voice,
            language_code=language,
            audio_format="mp3"
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=500, detail=result.get('error', 'Synthesis failed'))
        
        return {
            "audio_data": result.get('audio_data', ''),
            "success": True,
            "audio_format": "mp3"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Simple synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@router.post("/estimate-duration")
async def estimate_speech_duration(
    text: str = Form(...),
    speaking_rate: float = Form(1.0),
    current_user: User = Depends(get_current_user)
):
    """
    Estimate speech duration for given text (backward compatibility)
    """
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        if tts_service and hasattr(tts_service, 'estimate_audio_duration'):
            duration = tts_service.estimate_audio_duration(text, speaking_rate)
        else:
            # Simple estimation: ~150 words per minute
            words = len(text.split())
            duration = (words / 150) * 60 / speaking_rate
        
        return {
            "estimated_duration_seconds": duration,
            "text_length": len(text),
            "word_count": len(text.split()),
            "speaking_rate": speaking_rate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Duration estimation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Duration estimation failed: {str(e)}")

@router.post("/batch-synthesize")
async def batch_synthesize_speech(
    texts: List[str] = Body(...),
    voice_name: Optional[str] = Body(None),
    audio_format: str = Body("mp3"),
    current_user: User = Depends(get_current_user)
):
    """
    Batch synthesis for multiple texts (backward compatibility)
    """
    try:
        if not texts:
            raise HTTPException(status_code=400, detail="No texts provided")
        
        if len(texts) > 50:
            raise HTTPException(status_code=400, detail="Too many texts (max 50)")
        
        if tts_service is None:
            raise HTTPException(status_code=503, detail="TTS service not available")
        
        results = []
        
        if hasattr(tts_service, 'batch_synthesize'):
            results = await tts_service.batch_synthesize(
                texts, voice_name=voice_name, audio_format=audio_format
            )
        else:
            # Fallback to individual synthesis
            for i, text in enumerate(texts):
                try:
                    result = await tts_service.synthesize_speech(
                        text=text,
                        voice_name=voice_name,
                        audio_format=audio_format
                    )
                    results.append({
                        "index": i,
                        "success": result.get('success', False),
                        "audio_data": result.get('audio_data', ''),
                        "text": text[:50] + '...' if len(text) > 50 else text
                    })
                except Exception as e:
                    results.append({
                        "index": i,
                        "success": False,
                        "error": str(e),
                        "text": text[:50] + '...' if len(text) > 50 else text
                    })
        
        success_count = sum(1 for r in results if r.get('success'))
        
        return {
            "results": results,
            "total": len(texts),
            "successful": success_count,
            "failed": len(texts) - success_count,
            "audio_format": audio_format
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch synthesis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch synthesis failed: {str(e)}")