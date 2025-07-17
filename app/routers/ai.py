"""
AI Conversation Router - Core AI interaction endpoints
comprehensive AI features using Gemini, emotion detection, personalization, and RAG visualization
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, update, func
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, validator
import logging
from redis.asyncio import Redis
import json
import asyncio
from fastapi import UploadFile, File, Form
import random
import logging
import base64

from app.config import settings
from app.database import get_db, get_redis
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageType, SenderType
from app.models.emotion import Emotion, EmotionType
from app.models.user_preference import UserPreference
from app.routers.auth import get_current_user
from app.services.gemini_service import gemini_service  # Using Gemini as primary AI service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service
from app.services.prompt_service import prompt_service
from app.services.rag_service import rag_service
from app.schemas import UserTopicsResponse, UserTopicsUpdate
from app.services.topics_service import topics_service

logger = logging.getLogger(__name__)
router = APIRouter()

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

# Request/Response Models
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., min_length=1, max_length=4000)
    chat_id: Optional[int] = None
    detect_emotion: bool = True
    use_context: bool = True
    enable_personalization: bool = True
    stream: bool = False
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    message_id: int
    chat_id: int
    emotion_analysis: Optional[Dict[str, Any]] = None
    token_usage: Dict[str, int]
    processing_time: float
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationContext(BaseModel):
    """Conversation context model"""
    messages: List[Dict[str, str]]
    emotion_history: Optional[List[Dict[str, Any]]] = None
    user_preferences: Optional[Dict[str, Any]] = None

class TemplateRequest(BaseModel):
    """Template-based chat request"""
    message: str = Field(..., min_length=1, max_length=4000)
    template: str = Field(..., description="Template name")
    variables: Dict[str, Any] = Field(default_factory=dict)
    chat_id: Optional[int] = None

class PreferencesUpdate(BaseModel):
    """Model for updating user preferences"""
    conversation_style: Optional[str] = Field(None, pattern="^(friendly|formal|casual|professional)$")
    response_length: Optional[str] = Field(None, pattern="^(short|medium|long)$") 
    emotional_support_level: Optional[str] = Field(None, pattern="^(minimal|standard|high)$")
    humor_level: Optional[str] = Field(None, pattern="^(none|light|moderate|high)$")
    formality_level: Optional[str] = Field(None, pattern="^(very_casual|casual|neutral|formal|very_formal)$")
    technical_level: Optional[str] = Field(None, pattern="^(beginner|intermediate|advanced|expert)$")
    language: Optional[str] = None
    timezone: Optional[str] = None
    interests: Optional[List[str]] = None
    avoid_topics: Optional[List[str]] = None
    topics: Optional[List[str]] = Field(None, max_length=20)

class TTSRequest(BaseModel):
    """Text-to-speech request model"""
    text: str = Field(..., min_length=1, max_length=2000)
    voice_name: Optional[str] = None
    language_code: Optional[str] = "en-US"
    audio_format: str = "mp3"
    speaking_rate: float = Field(1.0, ge=0.5, le=2.0)
    pitch: float = Field(0.0, ge=-10.0, le=10.0)
    return_base64: bool = True


@router.post("/transcribe-audio")
async def transcribe_audio_simple(
    audio: UploadFile = File(...),
    language_code: str = Form("en-US"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Audio transcription endpoint for voice chat with real transcription
    """
    try:
        # Check if we should use mock or real service
        use_mock = getattr(settings, 'USE_MOCK_VOICE', False)
        
        if use_mock:
            # Import and use mock service
            from app.routers.voice_mock import transcribe_audio as mock_transcribe
            return await mock_transcribe(audio, language_code, True, False, current_user)
        
        # Use real transcription service
        from app.services.speech_service import speech_service
        
        # Read the audio file
        audio_data = await audio.read()
        logger.info(f"Received audio file: {audio.filename}, size: {len(audio_data)} bytes")
        
        # Get file extension from content type if filename doesn't have one
        file_ext = 'webm'  # Default for browser recordings
        if audio.filename and '.' in audio.filename:
            file_ext = audio.filename.split('.')[-1].lower()
        elif audio.content_type:
            type_map = {
                'audio/webm': 'webm',
                'audio/wav': 'wav',
                'audio/mp3': 'mp3',
                'audio/mpeg': 'mp3',
                'audio/ogg': 'ogg'
            }
            file_ext = type_map.get(audio.content_type, 'webm')
        
        # Validate audio
        validation = await speech_service.validate_audio(audio_data, file_ext)
        if not validation['valid']:
            logger.error(f"Audio validation failed: {validation.get('error')}")
            raise HTTPException(
                status_code=400,
                detail=validation.get('error', 'Invalid audio format')
            )
        
        # Use the correct sample rate for WebM audio
        # WebM from browsers typically uses 48000 Hz
        sample_rate = 48000 if file_ext == 'webm' else validation.get('sample_rate', 16000)
        
        logger.info(f"Using sample rate: {sample_rate} Hz for {file_ext} audio")
        
        # Perform transcription
        result = await speech_service.transcribe_audio(
            audio_data=audio_data,
            audio_format=file_ext,
            language_code=language_code,
            enable_automatic_punctuation=True,
            sample_rate=sample_rate  # Use the correct sample rate
        )
        
        return {
            "success": True,
            "transcript": result['transcript'],
            "confidence": result.get('confidence', 0.95),
            "language": result.get('language', language_code),
            "duration": result.get('duration', 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}", exc_info=True)
        
        # Fallback to mock if real service fails in development
        if settings.ENVIRONMENT == "development":
            logger.warning("Falling back to mock transcription due to error")
            from app.routers.voice_mock import MOCK_TRANSCRIPTIONS
            import random
            
            return {
                "success": True,
                "transcript": random.choice(MOCK_TRANSCRIPTIONS),
                "confidence": 0.95,
                "language": language_code,
                "duration": 2.5,
                "_mock": True,
                "_error": str(e)
            }
        
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )

@router.post("/voice/synthesize")
async def synthesize_speech(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Mock text-to-speech synthesis
    Returns a dummy audio response
    """
    try:
        logger.info(f"Mock TTS requested by user {current_user.id}")
        logger.info(f"Text: {request.text[:50]}...")
        
        # For mock, return a tiny valid MP3 as base64
        dummy_mp3 = b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        import base64
        audio_base64 = base64.b64encode(dummy_mp3).decode('utf-8')
        
        return {
            "success": True,
            "audio_data": audio_base64,
            "duration": 1.0,
            "text_length": len(request.text),
            "_mock": True
        }
            
    except Exception as e:
        logger.error(f"Mock TTS error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mock synthesis failed: {str(e)}"
        )

@router.get("/message-audio/{message_id}")
async def get_message_audio(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Get audio for a specific message"""
    try:
        # Verify message belongs to user
        result = await db.execute(
            select(Message)
            .join(Chat)
            .where(
                and_(
                    Message.id == message_id,
                    Chat.user_id == current_user.id
                )
            )
        )
        message = result.scalar_one_or_none()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Check Redis cache first
        audio_data = None
        if redis_client:
            audio_key = f"audio:message:{message_id}"
            audio_data = await redis_client.get(audio_key)
        
        if audio_data:
            return {
                "success": True,
                "audio_data": audio_data,
                "format": "mp3",
                "cached": True
            }
        
        # Generate on demand if not cached
        from app.services.tts_service import tts_service
        
        result = await tts_service.synthesize_speech(
            text=message.content,
            audio_format="mp3"
        )
        
        audio_base64 = base64.b64encode(result['audio_content']).decode()
        
        # Cache for next time
        if redis_client:
            await redis_client.set(
                f"audio:message:{message_id}",
                audio_base64,
                ex=3600
            )
        
        return {
            "success": True,
            "audio_data": audio_base64,
            "format": "mp3",
            "cached": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve audio"
        )

def transform_simple_preferences_to_personalization_format(simple_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Transform simple database preferences to personalization service format"""
    
    # Default confidence for manually set preferences
    DEFAULT_CONFIDENCE = 0.8
    
    transformed = {
        "conversation_style": {
            "style": simple_prefs.get("conversation_style", "friendly"),
            "confidence": DEFAULT_CONFIDENCE
        },
        "response_length": {
            "preference": simple_prefs.get("preferred_response_length", "medium"),
            "confidence": DEFAULT_CONFIDENCE
        },
        "technical_level": {
            "level": simple_prefs.get("technical_level", "intermediate"),
            "confidence": DEFAULT_CONFIDENCE
        },
        "formality": {
            "level": simple_prefs.get("formality_level", "neutral"),
            "confidence": DEFAULT_CONFIDENCE
        },
        "creativity": {
            "level": simple_prefs.get("creativity_level", "moderate"),
            "confidence": DEFAULT_CONFIDENCE
        },
        "topics": {
            "interests": {},  # Will be populated from interaction history
            "confidence": 0.0
        },
        "temporal_patterns": {
            "patterns": {},
            "confidence": 0.0
        }
    }
    
    # Handle emotional support level mapping
    emotional_support = simple_prefs.get("emotional_support_level", "standard")
    if emotional_support == "minimal":
        transformed["emotional_support"] = {"level": "low", "confidence": DEFAULT_CONFIDENCE}
    elif emotional_support == "high":
        transformed["emotional_support"] = {"level": "high", "confidence": DEFAULT_CONFIDENCE}
    else:
        transformed["emotional_support"] = {"level": "moderate", "confidence": DEFAULT_CONFIDENCE}
    
    # Add any additional preferences from the database
    for key, value in simple_prefs.items():
        if key not in ["conversation_style", "preferred_response_length", "emotional_support_level", 
                      "technical_level", "formality_level", "creativity_level"]:
            # Pass through other preferences as-is
            transformed[key] = value
    
    return transformed


async def build_conversation_context(
    chat: Chat,
    user_preferences: Optional[Dict[str, Any]] = None,
    emotion_context: Optional[Dict[str, Any]] = None,
    rag_context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None
) -> List[Dict[str, str]]:
    """Build conversation context with personalization, emotion detection, and RAG"""
    
    messages = []
    
    # Get conversation history
    conversation_history = []
    
    # Handle messages properly to avoid lazy loading issues
    try:
        if hasattr(chat, 'messages') and chat.messages is not None:
            # Messages are already loaded via selectinload
            sorted_messages = sorted(chat.messages, key=lambda x: x.created_at)
            recent_messages = sorted_messages[-(settings.CONVERSATION_CONTEXT_WINDOW * 2):]
        elif chat.id and db:
            # Existing chat but messages not loaded - fetch them
            result = await db.execute(
                select(Message)
                .where(Message.chat_id == chat.id)
                .order_by(Message.created_at)
                .limit(settings.CONVERSATION_CONTEXT_WINDOW * 2)
            )
            recent_messages = result.scalars().all()
        else:
            # New chat - no messages yet
            recent_messages = []
            
        for msg in recent_messages:
            role = "user" if msg.sender_type == SenderType.USER else "assistant"
            conversation_history.append({
                "role": role,
                "content": msg.content
            })
    except Exception as e:
        logger.warning(f"Failed to load conversation history: {str(e)}")
        conversation_history = []
    
    # Check if user has short response preference
    has_short_preference = (user_preferences and 
                          user_preferences.get("preferred_response_length") == "short")
    
    # Generate personalized system prompt if preferences are available
    if user_preferences:
        # Use the personalization service to generate a truly personalized prompt
        personalized_prompt = await personalization_service.generate_personalized_system_prompt(
            user_preferences=user_preferences,
            context={
                "emotion": emotion_context.get("recent_emotion") if emotion_context else None,
                "conversation_history": conversation_history,
                "rag_context": rag_context is not None
            }
        )
        
        # Log the personalized prompt for debugging
        logger.info(f"Generated personalized system prompt: {personalized_prompt[:200]}...")
        
        # For short responses, use a simplified system prompt
        if has_short_preference:
            # Use ONLY the personalized prompt with strong brevity instructions
            system_prompt = personalized_prompt
        else:
            # Get additional context-based adjustments from prompt service
            context_prompt = prompt_service.get_prompt_for_context(
                user_message="",  # Will be added later
                conversation_history=conversation_history,
                user_preferences=user_preferences,
                detected_emotion=emotion_context.get("recent_emotion") if emotion_context else None
            )
            
            # Combine both prompts for maximum personalization
            system_prompt = f"{personalized_prompt}\n\n{context_prompt}"
    else:
        # Fall back to standard prompt service if no personalization data
        system_prompt = prompt_service.get_prompt_for_context(
            user_message="",
            conversation_history=conversation_history,
            user_preferences=user_preferences,
            detected_emotion=emotion_context.get("recent_emotion") if emotion_context else None
        )
    
    # Add STRONG brevity instruction at the END for short responses
    if has_short_preference:
        system_prompt += "\n\n[CRITICAL INSTRUCTION: You MUST keep your response to 2-3 sentences maximum. No lists, no multiple paragraphs, no detailed explanations. Be direct and concise. This is the most important instruction.]"
    
    # Add system prompt
    messages.append({"role": "system", "content": system_prompt})
    
    # Add conversation history
    messages.extend(conversation_history)
    
    # Add RAG context if available
    if rag_context and rag_context.get("context_messages"):
        rag_prompt = "Relevant context from previous conversations:\n"
        for ctx in rag_context["context_messages"][:3]:  # Limit to 3 most relevant
            rag_prompt += f"- {ctx['content'][:100]}...\n"
        messages.append({"role": "system", "content": rag_prompt})
    
    return messages


# Main chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    """
    Main AI chat endpoint with emotion detection and personalization using Gemini
    """
    
    try:
        # Track processing time
        start_time = datetime.now(timezone.utc)
        
        # 1. Get or create chat session
        if chat_request.chat_id:
            # Verify chat belongs to user - with eager loading of messages
            result = await db.execute(
                select(Chat)
                .where(and_(
                    Chat.id == chat_request.chat_id,
                    Chat.user_id == current_user.id,
                    Chat.is_active == True
                ))
                .options(selectinload(Chat.messages))  # Eagerly load messages
            )
            chat = result.scalar_one_or_none()
            
            if not chat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Chat not found or access denied"
                )
        else:
            # Create new chat
            chat = Chat(
                user_id=current_user.id,
                title="New Chat",
                ai_model="gemini-2.0-flash-001",  # Using Gemini model
                temperature=0.7,
                max_tokens=1000,
                is_active=True
            )
            db.add(chat)
            await db.flush()
            # DON'T set chat.messages = [] - this causes the SQLAlchemy error
        
        # 2. Create user message
        user_message = Message(
            chat_id=chat.id,
            content=chat_request.message,
            message_type=MessageType.TEXT,
            sender_type=SenderType.USER,
            message_metadata={
                "request_params": {
                    "chat_id": chat_request.chat_id,
                    "detect_emotion": chat_request.detect_emotion,
                    "use_context": chat_request.use_context,
                    "enable_personalization": chat_request.enable_personalization,
                    "stream": chat_request.stream
                }
            }
        )
        db.add(user_message)
        await db.flush()
        
        # 3. Emotion detection
        emotion_data = None
        if chat_request.detect_emotion:
            try:
                emotion_data = await emotion_service.analyze_emotion(chat_request.message)
                if emotion_data and emotion_data.get("primary_emotion"):
                    user_message.emotion_detected = emotion_data["primary_emotion"]
                    user_message.sentiment_score = emotion_data.get("sentiment_score")
                    user_message.confidence_score = emotion_data.get("confidence")
            except Exception as e:
                logger.warning(f"Emotion detection failed: {str(e)}")
        
        # 4. Get RAG context
        rag_context_data = None
        if chat_request.use_context:
            try:
                rag_context_data = await rag_service.get_context_for_chat(
                    chat_id=chat.id,
                    user_id=current_user.id,
                    current_message=chat_request.message,
                    db=db,
                    redis_client=redis_client
                )
            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {str(e)}")
                # Continue without RAG if it fails
                rag_context_data = None
        
        # 5. Get user preferences for personalization
        user_preferences = None
        response_length_pref = "medium"  # default
        if chat_request.enable_personalization:
            try:
                # First, try to get preferences from database
                result = await db.execute(
                    select(UserPreference).where(UserPreference.user_id == current_user.id)
                )
                user_pref = result.scalar_one_or_none()
                
                if user_pref and user_pref.preferences:
                    # Transform database preferences to personalization format
                    user_preferences = transform_simple_preferences_to_personalization_format(
                        user_pref.preferences
                    )
                    # Store the response length preference
                    response_length_pref = user_pref.preferences.get("preferred_response_length", "medium")
                    logger.info(f"Loaded and transformed preferences for user {current_user.id}, response length: {response_length_pref}")

                    # DEBUG: Log all preferences to ensure they're loaded correctly
                    logger.info(f"All preferences for user {current_user.id}: {user_pref.preferences}")
                else:
                    # Use default preferences if none exist
                    user_preferences = personalization_service._get_default_preferences(current_user.id)
                    logger.info(f"Using default preferences for user {current_user.id}")
                            
            except Exception as e:
                logger.warning(f"Personalization failed: {str(e)}")
                user_preferences = None
        
        # Log personalization status
        logger.info(f"Personalization status for user {current_user.id}: {'enabled' if user_preferences else 'disabled'}")
        
        # 6. Build conversation context with prompt service
        conversation_messages = await build_conversation_context(
            chat=chat,
            user_preferences=user_preferences,
            emotion_context={"recent_emotion": emotion_data.get("primary_emotion")} if emotion_data else None,
            rag_context=rag_context_data,
            db=db  # Pass db session
        )
        
        # Add current user message
        conversation_messages.append({"role": "user", "content": chat_request.message})
        
        # 7. Determine max tokens based on response length preference
        max_tokens = chat.max_tokens  # default from chat settings
        if response_length_pref == "short":
            max_tokens = 60  # HARD LIMIT: ~2-3 sentences is typically 40-60 tokens
            logger.info(f"Setting max_tokens to {max_tokens} for SHORT response preference")
        elif response_length_pref == "medium":
            max_tokens = min(300, max_tokens)  # Medium responses
        elif response_length_pref == "long":
            max_tokens = min(2000, max_tokens)  # Allow up to 2000 tokens for long responses

        logger.info(f"Max tokens set to {max_tokens} based on preference: {response_length_pref}")
        
        # 8. Generate AI response
        if chat_request.stream:
            # Return streaming response
            return StreamingResponse(
                _stream_chat_response(
                    messages=conversation_messages,
                    chat=chat,
                    user_message=user_message,
                    db=db,
                    redis_client=redis_client,
                    current_user=current_user,
                    emotion_data=emotion_data,
                    rag_context_data=rag_context_data,
                    start_time=start_time,
                    max_tokens=max_tokens
                ),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming response
            ai_response_data = await gemini_service.generate_chat_response(
                messages=conversation_messages,
                temperature=chat.temperature,
                max_tokens=max_tokens,
                model=chat.ai_model,
                stream=False,
                user_id=str(current_user.id)
            )
        
        if not ai_response_data.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI response generation failed: {ai_response_data.get('error', 'Unknown error')}"
            )
        
        ai_response = ai_response_data["response"]
        token_usage = ai_response_data["tokens_used"]
        processing_time_ai = ai_response_data["processing_time"]
        
        # 9. Create AI message
        ai_message = Message(
            chat_id=chat.id,
            content=ai_response,
            message_type=MessageType.TEXT,
            sender_type=SenderType.ASSISTANT,
            tokens_used=token_usage.get("total_tokens", 0),
            processing_time=processing_time_ai,
            message_metadata={
                "model_used": ai_response_data.get("model_used", chat.ai_model),
                "emotion_context": emotion_data is not None,
                "personalization_applied": user_preferences is not None,
                "rag_context_used": rag_context_data is not None and len(rag_context_data.get("context_messages", [])) > 0,
                "rag_context": rag_context_data if rag_context_data else None
            }
        )
        db.add(ai_message)
        
        # 10. Analyze AI response emotion
        ai_emotion_data = None
        if chat_request.detect_emotion:
            try:
                ai_emotion_data = await emotion_service.analyze_emotion(ai_response)
                if ai_emotion_data:
                    # Store emotion analysis for AI message
                    emotion_record = Emotion(
                        user_id=current_user.id,
                        chat_id=chat.id,
                        message_id=ai_message.id,
                        primary_emotion=EmotionType(ai_emotion_data["primary_emotion"]),
                        confidence_score=ai_emotion_data.get("confidence", 0.5),
                        sentiment_score=ai_emotion_data.get("sentiment_score", 0.0),
                        detected_at=datetime.now(timezone.utc)
                    )
                    db.add(emotion_record)
            except Exception as e:
                logger.warning(f"AI response emotion analysis failed: {str(e)}")
        
        # 11. Update chat metadata
        chat.total_messages += 2
        chat.total_tokens_used += user_message.tokens_used + ai_message.tokens_used
        chat.last_message_at = datetime.now(timezone.utc)
        chat.updated_at = datetime.now(timezone.utc)
        
        # Update title if it's still default
        if chat.title == "New Chat" and chat.auto_title_generation:
            # Generate title in background
            background_tasks.add_task(
                generate_and_update_chat_title,
                chat.id,
                conversation_messages,
                db
            )
        
        # 12. Update user statistics and preferences
        background_tasks.add_task(
            update_user_statistics_and_preferences,
            current_user.id,
            chat_request.message,
            emotion_data.get("primary_emotion") if emotion_data else None,
            db
        )
        
        # Commit all changes
        await db.commit()
        
        # Calculate total processing time
        total_processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # 13. Return response
        return ChatResponse(
            response=ai_response,
            message_id=ai_message.id,
            chat_id=chat.id,
            emotion_analysis=ai_emotion_data,
            token_usage={
                "user_tokens": user_message.tokens_used,
                "ai_tokens": ai_message.tokens_used,
                "total_tokens": user_message.tokens_used + ai_message.tokens_used
            },
            processing_time=total_processing_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "personalization_applied": user_preferences is not None,
                "rag_sources_used": len(rag_context_data.get("context_messages", [])) if rag_context_data else 0,
                "emotion_detected": emotion_data is not None,
                "response_length_preference": response_length_pref
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )

# Helper functions
async def _stream_chat_response(
    messages: List[Dict[str, str]],
    chat: Chat,
    user_message: Message,
    db: AsyncSession,
    redis_client: Redis,
    current_user: User,
    emotion_data: Optional[Dict[str, Any]],
    rag_context_data: Optional[Dict[str, Any]],
    start_time: datetime,
    max_tokens: int
):
    """Stream chat response from Gemini"""
    try:
        # Generate streaming response from Gemini
        ai_response_data = await gemini_service.generate_chat_response(
            messages=messages,
            temperature=chat.temperature,
            max_tokens=max_tokens,
            model=chat.ai_model,
            stream=True,
            user_id=str(current_user.id)
        )
        
        if not ai_response_data.get("success"):
            yield f"data: {json.dumps({'error': ai_response_data.get('error', 'Unknown error')})}\n\n"
            return
        
        # Stream the response text
        response_text = ai_response_data["response"]
        chunks = response_text.split()  # Simple word-based chunking
        
        full_response = ""
        for i, chunk in enumerate(chunks):
            full_response += chunk + " "
            yield f"data: {json.dumps({'content': chunk + ' '})}\n\n"
            await asyncio.sleep(0.05)  # Small delay for smooth streaming
        
        # Save AI message after streaming completes
        ai_message = Message(
            chat_id=chat.id,
            content=full_response.strip(),
            message_type=MessageType.TEXT,
            sender_type=SenderType.ASSISTANT,
            tokens_used=ai_response_data.get("tokens_used", {}).get("total_tokens", 0),
            processing_time=ai_response_data.get("processing_time", 0),
            message_metadata={
                "model_used": ai_response_data.get("model_used", chat.ai_model),
                "emotion_context": emotion_data is not None,
                "personalization_applied": True,
                "rag_context_used": rag_context_data is not None,
                "streamed": True
            }
        )
        db.add(ai_message)
        
        # Update chat statistics
        chat.total_messages += 1
        chat.total_tokens_used += ai_message.tokens_used
        chat.last_message_at = datetime.now(timezone.utc)
        chat.last_activity_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Send final metadata
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        yield f"data: {json.dumps({'type': 'metadata','message_id': ai_message.id,'emotion': emotion_data,'tokens_used': ai_message.tokens_used,'processing_time': processing_time})}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming failed: {str(e)}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


async def generate_and_update_chat_title(chat_id: int, messages: List[Dict[str, str]], db: AsyncSession):
    """Generate and update chat title in background"""
    try:
        async with db.begin():
            chat = await db.get(Chat, chat_id)
            if chat and chat.title == "New Chat":
                # Generate title using Gemini
                title_result = await gemini_service.generate_conversation_title(messages)
                if title_result.get("success"):
                    chat.title = title_result["title"]
                    await db.commit()
    except Exception as e:
        logger.error(f"Failed to generate chat title: {str(e)}")


async def update_user_statistics_and_preferences(
    user_id: int,
    message: str,
    emotion: Optional[str],
    db: AsyncSession
):
    """Update user statistics and learn from interaction"""
    try:
        async with db.begin():
            # Get user preference record
            result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            user_pref = result.scalar_one_or_none()
            
            if not user_pref:
                # Create new preference record
                user_pref = UserPreference(
                    user_id=user_id,
                    preferences={},
                    interaction_patterns={}
                )
                db.add(user_pref)
            
            # Update interaction patterns
            patterns = user_pref.interaction_patterns or {}
            
            # Track time of day preference
            hour = datetime.now(timezone.utc).hour
            time_slots = patterns.get("time_slots", {})
            time_slots[str(hour)] = time_slots.get(str(hour), 0) + 1
            patterns["time_slots"] = time_slots
            
            # Track topic interests based on keywords
            topics = []
            tech_keywords = ["code", "programming", "software", "computer", "technology", "AI", "machine learning"]
            if any(keyword in message.lower() for keyword in tech_keywords):
                topics.append("technology")
            
            health_keywords = ["health", "wellness", "exercise", "mental", "feeling", "stress", "fitness", "diet"]
            if any(keyword in message.lower() for keyword in health_keywords):
                topics.append("health_wellness")
            
            business_keywords = ["work", "business", "job", "career", "project", "company", "meeting"]
            if any(keyword in message.lower() for keyword in business_keywords):
                topics.append("business")
            
            creative_keywords = ["art", "music", "creative", "design", "write", "story", "paint"]
            if any(keyword in message.lower() for keyword in creative_keywords):
                topics.append("creative")
            
            # Update preferences with topics
            if topics:
                preferences_copy = user_pref.preferences.copy()
                current_interests = preferences_copy.get("interests", [])
                preferences_copy["interests"] = list(set(current_interests + topics))[:10]  # Limit to 10 interests
                user_pref.preferences = preferences_copy
                flag_modified(user_pref, 'preferences')
            
            # Update emotional patterns
            if emotion:
                emotional_patterns = patterns.get("emotional_patterns", {})
                emotional_patterns[datetime.now().date().isoformat()] = emotion
                # Keep only last 30 days
                cutoff_date = (datetime.now() - timedelta(days=30)).date().isoformat()
                emotional_patterns = {k: v for k, v in emotional_patterns.items() if k >= cutoff_date}
                patterns["emotional_patterns"] = emotional_patterns
            
            # Update interaction patterns
            user_pref.interaction_patterns = patterns
            flag_modified(user_pref, 'interaction_patterns')
            
            user_pref.last_interaction_at = datetime.now(timezone.utc)
            
            await db.commit()
            
    except Exception as e:
        logger.error(f"Failed to update user preferences: {str(e)}")


# Update personalization preferences endpoint
@router.put("/personalization", response_model=Dict[str, Any])
async def update_personalization_preferences(
    preferences_update: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    """Update user personalization preferences"""
    
    try:
        # Get or create user preference record
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        )
        user_pref = result.scalar_one_or_none()
        
        if not user_pref:
            user_pref = UserPreference(
                user_id=current_user.id,
                preferences={},
                interaction_patterns={}
            )
            db.add(user_pref)
        
        # Update preferences
        current_prefs = user_pref.preferences.copy() if user_pref.preferences else {}
        
        # Update each field if provided
        update_dict = preferences_update.dict(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                # Map the field names correctly
                if key == "response_length":
                    current_prefs["preferred_response_length"] = value
                elif key == "conversation_style":
                    current_prefs["conversation_style"] = value
                elif key == "emotional_support_level":
                    current_prefs["emotional_support_level"] = value
                else:
                    current_prefs[key] = value
        
        user_pref.preferences = current_prefs
        flag_modified(user_pref, 'preferences')
        
        user_pref.last_interaction_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(user_pref)
        
        # Clear any cached preferences
        cache_key = f"user_preferences:{current_user.id}"
        await redis_client.delete(cache_key)
        
        # Transform to personalization format for response
        transformed_prefs = transform_simple_preferences_to_personalization_format(current_prefs)
        
        return {
            "success": True,
            "preferences": current_prefs,
            "personalization_format": transformed_prefs,
            "updated_at": user_pref.last_interaction_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update preferences: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )

@router.get("/topics", response_model=UserTopicsResponse)
async def get_user_topics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's topic interests and recommendations"""
    try:
        topics_data = await topics_service.get_user_topics(db, current_user.id)
        return UserTopicsResponse(**topics_data)
    except Exception as e:
        logger.error(f"Failed to get user topics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve topics"
        )

@router.put("/topics", response_model=UserTopicsResponse)
async def update_user_topics(
    topics_update: UserTopicsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's topic interests"""
    try:
        topics_data = await topics_service.update_user_topics(
            db, current_user.id, topics_update.topics
        )
        return UserTopicsResponse(**topics_data)
    except Exception as e:
        logger.error(f"Failed to update topics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update topics"
        )

# Get personalization preferences endpoint
@router.get("/personalization", response_model=Dict[str, Any])
async def get_personalization_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user personalization preferences and insights"""
    
    try:
        # Get user preference record
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        )
        user_pref = result.scalar_one_or_none()
        
        if not user_pref:
            # Return default preferences
            return {
                "preferences": {
                    "conversation_style": "friendly",
                    "preferred_response_length": "medium",
                    "emotional_support_level": "standard",
                    "technical_level": "intermediate",
                    "formality_level": "neutral"
                },
                "insights": {
                    "total_interactions": 0,
                    "primary_interests": [],
                    "active_times": [],
                    "emotional_patterns": {}
                },
                "last_updated": None
            }
        
        # Extract insights from interaction patterns
        patterns = user_pref.interaction_patterns or {}
        
        # Get most active times
        time_slots = patterns.get("time_slots", {})
        sorted_times = sorted(time_slots.items(), key=lambda x: x[1], reverse=True)
        active_times = [int(hour) for hour, _ in sorted_times[:3]]  # Top 3 active hours
        
        # Get emotional patterns
        emotional_patterns = patterns.get("emotional_patterns", {})
        
        # Count total interactions
        total_interactions = sum(time_slots.values())
        
        return {
            "preferences": user_pref.preferences,
            "insights": {
                "total_interactions": total_interactions,
                "primary_interests": user_pref.preferences.get("interests", []),
                "active_times": active_times,
                "emotional_patterns": emotional_patterns,
                "most_common_emotion": max(emotional_patterns.values(), key=emotional_patterns.values().count) if emotional_patterns else None
            },
            "last_updated": user_pref.last_interaction_at.isoformat() if user_pref.last_interaction_at else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get preferences: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve preferences"
        )


# Emotion analysis endpoint
@router.post("/analyze-emotion", response_model=Dict[str, Any])
async def analyze_emotion(
    text: str = Body(..., min_length=1, max_length=2000),
    include_history: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Analyze emotion in text with optional history"""
    
    try:
        # Analyze current text
        emotion_data = await emotion_service.analyze_emotion(text)
        
        if not emotion_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not analyze emotion in the provided text"
            )
        
        response = {
            "emotion": emotion_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Include emotion history if requested
        if include_history:
            # Get recent emotions for user
            result = await db.execute(
                select(Emotion)
                .where(Emotion.user_id == current_user.id)
                .order_by(desc(Emotion.detected_at))
                .limit(10)
            )
            recent_emotions = result.scalars().all()
            
            history = [
                {
                    "emotion": e.primary_emotion.value,
                    "confidence": e.confidence_score,
                    "sentiment": e.sentiment_score,
                    "detected_at": e.detected_at.isoformat()
                }
                for e in recent_emotions
            ]
            
            response["history"] = history
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Emotion analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze emotion"
        )


# Emotion history endpoint
@router.get("/emotions/history", response_model=Dict[str, Any])
async def get_emotion_history(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's emotion history and trends"""
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get emotions within date range
        result = await db.execute(
            select(Emotion)
            .where(
                and_(
                    Emotion.user_id == current_user.id,
                    Emotion.detected_at >= cutoff_date
                )
            )
            .order_by(Emotion.detected_at)
        )
        emotions = result.scalars().all()
        
        if not emotions:
            return {
                "emotions": [],
                "summary": {
                    "total_emotions": 0,
                    "dominant_emotion": None,
                    "average_sentiment": 0.0,
                    "emotion_distribution": {}
                },
                "trend": "stable"
            }
        
        # Calculate statistics
        emotion_counts = {}
        sentiment_sum = 0
        
        for emotion in emotions:
            emotion_type = emotion.primary_emotion.value
            emotion_counts[emotion_type] = emotion_counts.get(emotion_type, 0) + 1
            sentiment_sum += emotion.sentiment_score
        
        dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else None
        average_sentiment = sentiment_sum / len(emotions)
        
        # Calculate trend
        if len(emotions) >= 2:
            recent_emotions = emotions[-len(emotions)//3:]  # Last third
            older_emotions = emotions[:len(emotions)//3]   # First third
            
            recent_sentiment = sum(e.sentiment_score for e in recent_emotions) / len(recent_emotions)
            older_sentiment = sum(e.sentiment_score for e in older_emotions) / len(older_emotions)
            
            if recent_sentiment > older_sentiment + 0.1:
                trend = "improving"
            elif recent_sentiment < older_sentiment - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "emotions": [
                {
                    "emotion": e.primary_emotion.value,
                    "confidence": e.confidence_score,
                    "sentiment": e.sentiment_score,
                    "detected_at": e.detected_at.isoformat(),
                    "chat_id": e.chat_id
                }
                for e in emotions
            ],
            "summary": {
                "total_emotions": len(emotions),
                "dominant_emotion": dominant_emotion,
                "average_sentiment": average_sentiment,
                "emotion_distribution": emotion_counts
            },
            "trend": trend,
            "period": {
                "start": cutoff_date.isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
                "days": days
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get emotion history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emotion history"
        )


# RAG visualization endpoint
@router.get("/rag/visualization/{message_id}", response_model=Dict[str, Any])
async def get_rag_visualization(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get RAG visualization data for a specific message"""
    
    try:
        # Get message and verify ownership
        result = await db.execute(
            select(Message)
            .join(Chat)
            .where(
                and_(
                    Message.id == message_id,
                    Chat.user_id == current_user.id
                )
            )
        )
        message = result.scalar_one_or_none()
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Extract RAG metadata
        rag_metadata = message.message_metadata.get("rag_context", {})
        
        # Get user preferences for visualization
        result = await db.execute(
            select(UserPreference).where(UserPreference.user_id == current_user.id)
        )
        user_pref = result.scalar_one_or_none()
        
        # Get recent emotions for pattern
        result = await db.execute(
            select(Emotion)
            .where(Emotion.user_id == current_user.id)
            .order_by(desc(Emotion.detected_at))
            .limit(7)
        )
        recent_emotions = result.scalars().all()
        
        # Build emotional history
        emotional_history = []
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            day_emotions = [e for e in recent_emotions 
                           if e.detected_at.date() == date.date()]
            
            if day_emotions:
                avg_sentiment = sum(e.sentiment_score for e in day_emotions) / len(day_emotions)
            else:
                avg_sentiment = 0.5
                
            emotional_history.append({
                "date": date.strftime("%a"),
                "score": (avg_sentiment + 1) / 2  # Normalize to 0-1
            })
        
        emotional_history.reverse()
        
        # Determine trend
        if len(emotional_history) >= 2:
            recent_avg = sum(d["score"] for d in emotional_history[-3:]) / 3
            older_avg = sum(d["score"] for d in emotional_history[:3]) / 3
            trend = "improving" if recent_avg > older_avg else "declining" if recent_avg < older_avg else "stable"
        else:
            trend = "stable"
        
        return {
            "message_id": message_id,
            "currentMessage": message.content,
            "contextMessages": rag_metadata.get("context_messages", []),
            "userPreferences": {
                "conversationStyle": user_pref.preferences.get("conversation_style", "friendly") if user_pref else "friendly",
                "responseLength": user_pref.preferences.get("preferred_response_length", "medium") if user_pref else "medium",
                "interests": user_pref.preferences.get("interests", []) if user_pref else [],
                "preferredTime": user_pref.interaction_patterns.get("active_time", "day") if user_pref and user_pref.interaction_patterns else "day"
            },
            "emotionalPattern": {
                "recent": recent_emotions[0].primary_emotion.value if recent_emotions else "neutral",
                "trend": trend,
                "history": emotional_history
            },
            "ragStats": {
                "contextWindowSize": 10,
                "embeddingDimensions": 768,  # Gemini embeddings
                "similarityThreshold": 0.7,
                "contextsRetrieved": len(rag_metadata.get("context_messages", []))
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get RAG visualization: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve RAG visualization data"
        )


# Template-based chat endpoint
@router.post("/chat/template", response_model=ChatResponse)
async def chat_with_template(
    template_request: TemplateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    """Use a specific prompt template for the conversation"""
    
    try:
        # Get template
        template = prompt_service.get_template(template_request.template)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_request.template}' not found"
            )
        
        # Validate variables
        missing_vars = set(template.variables) - set(template_request.variables.keys())
        if missing_vars:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing template variables: {', '.join(missing_vars)}"
            )
        
        # Render template
        system_prompt = template.render(**template_request.variables)
        
        # Create modified chat request
        chat_request = ChatRequest(
            message=template_request.message,
            chat_id=template_request.chat_id
        )
        
        # Process with custom system prompt
        # This would require modifying the chat_with_ai function to accept custom prompts
        # For now, we'll call the regular endpoint
        return await chat_with_ai(
            chat_request, background_tasks, current_user, db, redis_client
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template chat failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process template chat"
        )


# Service health check
@router.get("/health")
async def ai_service_health():
    """Health check for AI service components"""
    
    try:
        # Test Gemini service
        gemini_healthy = await gemini_service.health_check()
        
        # Test emotion service
        emotion_healthy = await emotion_service.health_check()
        
        # Test personalization service
        personalization_healthy = await personalization_service.health_check()
        
        overall_status = "healthy" if all([
            gemini_healthy, emotion_healthy, personalization_healthy
        ]) else "degraded"
        
        model_info = await gemini_service.get_model_info()
        
        return {
            "status": overall_status,
            "services": {
                "gemini": "healthy" if gemini_healthy else "unhealthy",
                "emotion_analysis": "healthy" if emotion_healthy else "unhealthy",
                "personalization": "healthy" if personalization_healthy else "unhealthy"
            },
            "model_info": model_info,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI service health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }