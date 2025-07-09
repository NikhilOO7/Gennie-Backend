from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import io
import logging

from app.database import get_db
from app.models.user import User
from app.models.message import Message
from app.routers.auth import get_current_user
from app.services.speech_service import speech_service
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form("en-US"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Transcribe audio file to text"""
    try:
        # Validate file size
        contents = await audio.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(400, "Audio file too large")
        
        # Get file extension
        file_ext = audio.filename.split('.')[-1].lower()
        
        # Transcribe
        result = await speech_service.transcribe_audio(
            audio_data=contents,
            audio_format=file_ext,
            language_code=language
        )
        
        if "error" in result:
            raise HTTPException(400, f"Transcription failed: {result['error']}")
        
        # Log usage
        logger.info(f"User {current_user.id} transcribed audio: {len(contents)} bytes")
        
        return {
            "success": True,
            "transcript": result["transcript"],
            "confidence": result["confidence"],
            "language": result["language"]
        }
        
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        raise HTTPException(500, str(e))

@router.post("/synthesize")
async def synthesize_speech(
    text: str = Form(...),
    voice: Optional[str] = Form(None),
    language: Optional[str] = Form("en-US"),
    speaking_rate: Optional[float] = Form(1.0),
    current_user: User = Depends(get_current_user)
):
    """Convert text to speech"""
    try:
        # Validate input
        if len(text) > 5000:
            raise HTTPException(400, "Text too long (max 5000 characters)")
        
        # Synthesize
        audio_content = await speech_service.synthesize_speech(
            text=text,
            voice_name=voice,
            language_code=language,
            speaking_rate=speaking_rate
        )
        
        # Return audio file
        return StreamingResponse(
            io.BytesIO(audio_content),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )
        
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        raise HTTPException(500, str(e))

@router.get("/voices")
async def list_voices(
    language: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get available TTS voices"""
    try:
        voices = await speech_service.get_available_voices(language)
        
        # Filter and format for frontend
        formatted_voices = []
        for voice in voices:
            if voice["natural"]:  # Only return high-quality voices
                formatted_voices.append({
                    "id": voice["name"],
                    "name": voice["name"].split("-")[-1],
                    "language": voice["language_codes"][0],
                    "gender": voice["gender"]
                })
        
        return {
            "voices": formatted_voices,
            "default": "en-US-Neural2-F"
        }
        
    except Exception as e:
        logger.error(f"Error listing voices: {str(e)}")
        raise HTTPException(500, str(e))

@router.post("/voice-message")
async def create_voice_message(
    chat_id: int = Form(...),
    audio: UploadFile = File(...),
    language: Optional[str] = Form("en-US"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process voice message: transcribe and generate AI response"""
    try:
        # Read audio
        audio_data = await audio.read()
        
        # Transcribe
        transcription = await speech_service.transcribe_audio(
            audio_data=audio_data,
            audio_format=audio.filename.split('.')[-1].lower(),
            language_code=language
        )
        
        if not transcription["transcript"]:
            raise HTTPException(400, "Could not transcribe audio")
        
        # Save user message
        user_message = Message(
            chat_id=chat_id,
            content=transcription["transcript"],
            role="user",
            metadata={
                "type": "voice",
                "confidence": transcription["confidence"],
                "language": language
            }
        )
        db.add(user_message)
        await db.commit()
        
        # Generate AI response
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": transcription["transcript"]}
        ]
        
        ai_response_text = ""
        async for chunk in gemini_service.generate_response(messages):
            ai_response_text += chunk
        
        # Save AI message
        ai_message = Message(
            chat_id=chat_id,
            content=ai_response_text,
            role="assistant"
        )
        db.add(ai_message)
        await db.commit()
        
        # Generate audio response
        audio_response = await speech_service.synthesize_speech(ai_response_text)
        
        return {
            "user_message": {
                "id": user_message.id,
                "content": user_message.content,
                "confidence": transcription["confidence"]
            },
            "ai_message": {
                "id": ai_message.id,
                "content": ai_message.content
            },
            "audio_response": base64.b64encode(audio_response).decode()
        }
        
    except Exception as e:
        logger.error(f"Voice message error: {str(e)}")
        await db.rollback()
        raise HTTPException(500, str(e))