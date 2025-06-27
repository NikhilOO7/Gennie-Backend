"""
AI Conversation Router - Core AI interaction endpoints
comprehensive AI features, emotion detection, and personalization
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import json
from pydantic import BaseModel, validator

from app.database import get_db, get_redis
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, SenderType, MessageType
from app.models.emotion import Emotion
from app.routers.auth import get_current_user
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[int] = None
    use_context: bool = True
    detect_emotion: bool = True
    enable_personalization: bool = True
    stream: bool = False
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 4000:
            raise ValueError('Message too long (max 4000 characters)')
        return v.strip()

class ChatResponse(BaseModel):
    response: str
    chat_id: int
    user_message_id: int
    ai_message_id: int
    timestamp: datetime
    processing_time: float
    token_usage: Dict[str, int]
    emotion_data: Optional[Dict[str, Any]] = None
    personalization_applied: bool = False
    
    class Config:
        from_attributes = True

class ConversationContext(BaseModel):
    messages: List[Dict[str, str]]
    emotion_history: Optional[List[Dict[str, Any]]] = None
    user_preferences: Optional[Dict[str, Any]] = None

class PromptTemplate(BaseModel):
    name: str
    template: str
    variables: List[str]
    category: str

class PromptRequest(BaseModel):
    template_name: str
    variables: Dict[str, str]
    message: str

# Utility functions
async def get_or_create_chat(
    chat_id: Optional[int], 
    user: User, 
    db: AsyncSession
) -> Chat:
    """Get existing chat or create new one"""
    
    if chat_id:
        # Get existing chat
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == user.id,
                Chat.is_deleted == False,
                Chat.is_active == True
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found or inaccessible"
            )
        
        return chat
    else:
        # Create new chat
        if not user.can_create_chat():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat creation limit reached"
            )
        
        chat = Chat(
            user_id=user.id,
            title="New Chat"
        )
        
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        
        # Update user chat count
        user.total_chats += 1
        await db.commit()
        
        return chat

async def build_conversation_context(
    chat: Chat, 
    user_preferences: Optional[Dict[str, Any]] = None,
    emotion_context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """Build conversation context from chat history"""
    
    messages = []
    
    # Add system prompt
    system_prompt = chat.system_prompt
    if not system_prompt and user_preferences:
        system_prompt = await personalization_service.generate_personalized_system_prompt(
            user_preferences, emotion_context
        )
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Get recent messages for context
    context_messages = chat.get_context_messages()
    
    for msg in context_messages:
        if msg.sender_type == SenderType.USER:
            messages.append({"role": "user", "content": msg.content})
        elif msg.sender_type == SenderType.ASSISTANT:
            messages.append({"role": "assistant", "content": msg.content})
    
    return messages

async def update_conversation_context_cache(
    chat_id: int,
    user_message: Dict[str, Any],
    ai_message: Dict[str, Any],
    redis_client
):
    """Update conversation context in Redis cache"""
    try:
        if not redis_client:
            return
        
        cache_key = f"conversation_context:{chat_id}"
        
        # Get existing context
        existing_context = await redis_client.get(cache_key)
        if existing_context:
            context = json.loads(existing_context)
        else:
            context = []
        
        # Add new messages
        context.extend([user_message, ai_message])
        
        # Keep only last 20 messages
        if len(context) > 20:
            context = context[-20:]
        
        # Update cache with 1 hour expiration
        await redis_client.setex(cache_key, 3600, json.dumps(context, default=str))
        
        logger.debug(f"Updated conversation context cache for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to update conversation context cache: {str(e)}")

# Main chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """
    Main AI chat endpoint with comprehensive features
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # 1. Get or create chat
        chat = await get_or_create_chat(chat_request.chat_id, current_user, db)
        
        # 2. Check if chat can accept new messages
        if not chat.can_add_message():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot add message to this chat"
            )
        
        # 3. Create user message
        user_message = Message.create_user_message(
            chat_id=chat.id,
            content=chat_request.message
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        
        # 4. Analyze emotion if enabled
        emotion_data = None
        if chat_request.detect_emotion:
            try:
                emotion_analysis = await emotion_service.analyze_emotion(
                    chat_request.message,
                    context={"user_id": current_user.id, "chat_id": chat.id}
                )
                
                if emotion_analysis.get("success"):
                    emotion_data = emotion_analysis
                    
                    # Update message with emotion data
                    user_message.set_emotion_data(
                        sentiment_score=emotion_data.get("sentiment_score", 0.0),
                        emotion=emotion_data.get("primary_emotion", "neutral"),
                        confidence=emotion_data.get("confidence_score", 0.0)
                    )
                    
                    # Create emotion record
                    emotion_record = Emotion.create_from_analysis(
                        user_id=current_user.id,
                        analysis_result=emotion_data,
                        chat_id=chat.id,
                        message_id=user_message.id
                    )
                    db.add(emotion_record)
                    
            except Exception as e:
                logger.warning(f"Emotion analysis failed: {str(e)}")
        
        # 5. Get user preferences for personalization
        user_preferences = None
        if chat_request.enable_personalization:
            try:
                user_preferences = await personalization_service.get_cached_preferences(
                    current_user.id, redis_client
                )
                
                if not user_preferences:
                    # Get interaction history and analyze preferences
                    # This would typically fetch from database
                    interaction_history = []  # Placeholder
                    if len(interaction_history) >= personalization_service.min_interactions:
                        pref_analysis = await personalization_service.analyze_user_preferences(
                            current_user.id, interaction_history, redis_client
                        )
                        if pref_analysis.get("success"):
                            user_preferences = pref_analysis["preferences"]
                            
            except Exception as e:
                logger.warning(f"Personalization failed: {str(e)}")
        
        # 6. Build conversation context
        emotion_context = {"recent_emotion": emotion_data.get("primary_emotion")} if emotion_data else None
        conversation_messages = await build_conversation_context(
            chat, user_preferences, emotion_context
        )
        
        # Add current user message
        conversation_messages.append({"role": "user", "content": chat_request.message})
        
        # 7. Generate AI response
        ai_response_data = await openai_service.generate_chat_response(
            messages=conversation_messages,
            temperature=chat.temperature,
            max_tokens=chat.max_tokens,
            model=chat.ai_model,
            stream=chat_request.stream,
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
        
        # 8. Create AI message
        ai_message = Message.create_assistant_message(
            chat_id=chat.id,
            content=ai_response,
            tokens_used=token_usage.get("total_tokens", 0),
            processing_time=processing_time_ai
        )
        
        # Add AI model and other metadata
        ai_message.set_metadata("ai_model", chat.ai_model)
        ai_message.set_metadata("temperature", chat.temperature)
        ai_message.set_metadata("max_tokens", chat.max_tokens)
        if user_preferences:
            ai_message.set_metadata("personalization_applied", True)
            ai_message.set_metadata("user_preferences_version", user_preferences.get("version"))
        
        db.add(ai_message)
        
        # 9. Update chat statistics
        chat.update_message_stats(is_user_message=False, tokens_used=token_usage.get("total_tokens", 0))
        chat.auto_generate_title()  # Generate title if it's still "New Chat"
        
        # 10. Update user statistics
        current_user.increment_usage_stats(
            messages=2,  # user message + AI message
            tokens=token_usage.get("total_tokens", 0)
        )
        
        await db.commit()
        await db.refresh(ai_message)
        
        # 11. Background tasks
        # Update conversation context cache
        background_tasks.add_task(
            update_conversation_context_cache,
            chat.id,
            user_message.to_dict(),
            ai_message.to_dict(),
            redis_client
        )
        
        # Update personalization data
        if chat_request.enable_personalization:
            background_tasks.add_task(
                personalization_service.update_user_interaction,
                current_user.id,
                chat.id,
                chat_request.message,
                ai_response,
                emotion_data,
                redis_client
            )
        
        # Calculate total processing time
        total_processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(
            f"Chat response generated for user {current_user.id} in {total_processing_time:.2f}s",
            extra={
                "user_id": current_user.id,
                "chat_id": chat.id,
                "processing_time": total_processing_time,
                "tokens_used": token_usage.get("total_tokens", 0),
                "emotion_detected": emotion_data.get("primary_emotion") if emotion_data else None
            }
        )
        
        return ChatResponse(
            response=ai_response,
            chat_id=chat.id,
            user_message_id=user_message.id,
            ai_message_id=ai_message.id,
            timestamp=ai_message.created_at,
            processing_time=total_processing_time,
            token_usage=token_usage,
            emotion_data=emotion_data,
            personalization_applied=user_preferences is not None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat request failed: {str(e)}", exc_info=True)
        await db.rollback()
        
        # Save error message to chat if chat was created
        try:
            if 'chat' in locals():
                error_message = Message.create_assistant_message(
                    chat_id=chat.id,
                    content="I apologize, but I encountered an error processing your message. Please try again."
                )
                error_message.set_metadata("error", str(e))
                error_message.set_metadata("error_type", type(e).__name__)
                db.add(error_message)
                await db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request"
        )

# Context management endpoints
@router.get("/context/{chat_id}")
async def get_conversation_context(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Get current conversation context"""
    
    try:
        # Verify chat access
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Get cached context from Redis
        context = []
        if redis_client:
            cache_key = f"conversation_context:{chat_id}"
            cached_context = await redis_client.get(cache_key)
            if cached_context:
                context = json.loads(cached_context)
        
        # Fallback to database if no cache
        if not context:
            context_messages = chat.get_context_messages()
            context = [msg.get_context_for_ai() for msg in context_messages]
        
        return ConversationContext(
            messages=context,
            emotion_history=None,  # Would be populated from database
            user_preferences=None  # Would be populated from personalization service
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation context: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation context"
        )

# Emotion analysis endpoints
@router.post("/analyze-sentiment")
async def analyze_text_sentiment(
    text: str = Query(..., description="Text to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Analyze sentiment of arbitrary text"""
    
    try:
        emotion_data = await emotion_service.analyze_emotion(text)
        
        return {
            "text": text,
            "sentiment": emotion_data,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "user_id": current_user.id
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze sentiment"
        )

@router.get("/emotion-patterns/{user_id}")
async def get_emotion_patterns(
    user_id: int,
    time_window_hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's emotion patterns (admin only or own data)"""
    
    # Check authorization
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        # Get emotion history from database
        emotion_query = select(Emotion).where(
            and_(
                Emotion.user_id == user_id,
                Emotion.detected_at >= datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
            )
        ).order_by(Emotion.detected_at)
        
        emotion_result = await db.execute(emotion_query)
        emotions = emotion_result.scalars().all()
        
        emotion_history = [emotion.to_dict() for emotion in emotions]
        
        # Analyze patterns
        pattern_analysis = await emotion_service.analyze_emotion_patterns(
            emotion_history, time_window_hours
        )
        
        return pattern_analysis
    
    except Exception as e:
        logger.error(f"Failed to get emotion patterns: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emotion patterns"
        )

# Prompt template endpoints
@router.get("/prompts")
async def get_prompt_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user)
):
    """Get available prompt templates"""
    
    # This would typically come from a database or service
    # For now, return some example templates
    templates = [
        PromptTemplate(
            name="Creative Writing",
            template="You are a creative writing assistant. Help the user with {task} by providing {style} suggestions.",
            variables=["task", "style"],
            category="creative"
        ),
        PromptTemplate(
            name="Code Review",
            template="You are a senior software engineer. Review this {language} code and provide feedback on {aspect}.",
            variables=["language", "aspect"],
            category="technical"
        ),
        PromptTemplate(
            name="Learning Tutor",
            template="You are an expert tutor in {subject}. Explain {concept} in a way suitable for {level} students.",
            variables=["subject", "concept", "level"],
            category="educational"
        )
    ]
    
    if category:
        templates = [t for t in templates if t.category == category]
    
    return {"templates": templates}

@router.post("/chat-with-prompt", response_model=ChatResponse)
async def chat_with_prompt_template(
    prompt_request: PromptRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Chat using a prompt template"""
    
    try:
        # Get prompt template (this would come from database)
        # For now, use a simple example
        if prompt_request.template_name == "Creative Writing":
            template = "You are a creative writing assistant. Help the user with {task} by providing {style} suggestions."
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )
        
        # Fill template variables
        try:
            filled_prompt = template.format(**prompt_request.variables)
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing template variable: {str(e)}"
            )
        
        # Create chat request with filled prompt
        chat_request = ChatRequest(
            message=f"{filled_prompt}\n\n{prompt_request.message}",
            use_context=False,  # Don't use context for template-based requests
            detect_emotion=True,
            enable_personalization=True
        )
        
        # Process using main chat endpoint
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
        # Test OpenAI service
        openai_healthy = await openai_service.health_check()
        
        # Test emotion service
        emotion_healthy = await emotion_service.health_check()
        
        # Test personalization service
        personalization_healthy = await personalization_service.health_check()
        
        overall_status = "healthy" if all([
            openai_healthy, emotion_healthy, personalization_healthy
        ]) else "degraded"
        
        return {
            "status": overall_status,
            "services": {
                "openai": "healthy" if openai_healthy else "unhealthy",
                "emotion_analysis": "healthy" if emotion_healthy else "unhealthy",
                "personalization": "healthy" if personalization_healthy else "unhealthy"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI service health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }