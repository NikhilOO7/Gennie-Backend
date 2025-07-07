"""
AI Conversation Router - Core AI interaction endpoints
comprehensive AI features, emotion detection, personalization, and RAG visualization
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, update, func
from sqlalchemy.orm import selectinload
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, validator
import logging
from redis.asyncio import Redis
import json
import asyncio

from app.database import get_db, get_redis
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageType, SenderType
from app.models.emotion import Emotion, EmotionType
from app.models.user_preference import UserPreference
from app.routers.auth import get_current_user
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service
from app.services.prompt_service import prompt_service
from app.services.rag_service import rag_service
# from app.services.utils import generate_chat_title

logger = logging.getLogger(__name__)
router = APIRouter()

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

# Add this endpoint after the GET /personalization endpoint
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
            # Create new preference record
            user_pref = UserPreference(
                user_id=current_user.id,
                preferences={},
                interaction_patterns={},
                learning_data={},
                features_enabled=UserPreference.get_default_features()
            )
            db.add(user_pref)
        
        # Update preferences with new values
        update_data = preferences_update.dict(exclude_unset=True)
        
        # Map frontend field names to model field names
        field_mapping = {
            'emotional_support_level': 'emotional_support_level',
            'response_length': 'preferred_response_length',
            'conversation_style': 'conversation_style'
        }
        
        for frontend_key, value in update_data.items():
            if value is not None:
                # Use mapped key if available, otherwise use original
                model_key = field_mapping.get(frontend_key, frontend_key)
                user_pref.set_preference(model_key, value)
        
        # Update last interaction timestamp
        user_pref.last_interaction_at = datetime.now(timezone.utc)
        
        # Commit changes
        await db.commit()
        await db.refresh(user_pref)
        
        # Clear cached preferences
        if redis_client:
            cache_key = f"user_preferences:{current_user.id}"
            await redis_client.delete(cache_key)
            # Note: Removed the cache_user_preferences call since it doesn't exist
            # The preferences are already saved in the database
        
        logger.info(f"Updated preferences for user {current_user.id}")
        
        return {
            "success": True,
            "message": "Preferences updated successfully",
            "preferences": user_pref.preferences,
            "last_updated": user_pref.updated_at.isoformat() if user_pref.updated_at else None
        }
        
    except Exception as e:
        logger.error(f"Failed to update preferences: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )
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
    Main AI chat endpoint with emotion detection and personalization
    """
    
    try:
        # Track processing time
        start_time = datetime.now(timezone.utc)
        
        # 1. Get or create chat session
        if chat_request.chat_id:
            # Verify chat belongs to user
            result = await db.execute(
                select(Chat)
                .where(and_(
                    Chat.id == chat_request.chat_id,
                    Chat.user_id == current_user.id,
                    Chat.is_active == True
                ))
                .options(selectinload(Chat.messages))
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
                # title=await generate_chat_title(chat_request.message),
                title="New Chat",  # Placeholder title, will be updated later
                is_active=True
            )
            db.add(chat)
            await db.flush()
        
        # 2. Create user message
        user_message = Message(
            chat_id=chat.id,
            content=chat_request.message,
            message_type=MessageType.TEXT,
            sender_type=SenderType.USER,
            message_metadata={"request_params": chat_request.dict(exclude={"message"})}
        )
        db.add(user_message)
        await db.flush()
        
        # 3. Emotion detection
        emotion_data = None
        if chat_request.detect_emotion:
            try:
                emotion_result = await emotion_service.analyze_emotion(chat_request.message)
                if emotion_result.get("success"):
                    emotion_data = emotion_result
                    
                    # Save emotion to database
                    emotion_record = Emotion(
                        user_id=current_user.id,
                        chat_id=chat.id,
                        message_id=user_message.id,
                        primary_emotion=EmotionType(emotion_result.get("primary_emotion", "neutral")),
                        emotion_scores=emotion_result.get("all_emotions", {}),
                        confidence_score=emotion_result.get("confidence", 0.5),
                        sentiment_score=emotion_result.get("sentiment_score", 0.0),
                        text_analyzed=chat_request.message[:500],
                        emotion_intensity=emotion_result.get("intensity", 0.5)
                    )
                    db.add(emotion_record)
                    
                    # Update message with emotion data
                    user_message.set_emotion_data(
                        sentiment_score=emotion_result.get("sentiment_score", 0.0),
                        emotion=emotion_result.get("primary_emotion", "neutral"),
                        confidence=emotion_result.get("confidence", 0.5)
                    )
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
        
        # 5. Get user preferences for personalization
        user_preferences = None
        if chat_request.enable_personalization:
            try:
                user_preferences = await personalization_service.get_cached_preferences(
                    current_user.id, redis_client
                )
                
                if not user_preferences:
                    # Get interaction history and analyze preferences
                    result = await db.execute(
                        select(Message)
                        .join(Chat)
                        .where(Chat.user_id == current_user.id)
                        .order_by(desc(Message.created_at))
                        .limit(50)
                    )
                    messages = result.scalars().all()
                    
                    interaction_history = [
                        {
                            "sender_type": msg.sender_type.value,
                            "content": msg.content,
                            "timestamp": msg.created_at.isoformat(),
                            "emotion": msg.emotion_detected
                        }
                        for msg in messages
                    ]
                    
                    if len(interaction_history) >= personalization_service.min_interactions:
                        pref_analysis = await personalization_service.analyze_user_preferences(
                            current_user.id, interaction_history, redis_client
                        )
                        if pref_analysis.get("success"):
                            user_preferences = pref_analysis["preferences"]
                            
            except Exception as e:
                logger.warning(f"Personalization failed: {str(e)}")
        
        # 6. Build conversation context with prompt service
        conversation_messages = await build_conversation_context(
            chat=chat,
            user_preferences=user_preferences,
            emotion_context={"recent_emotion": emotion_data.get("primary_emotion")} if emotion_data else None,
            rag_context=rag_context_data
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
        
        # 9. Update chat statistics
        chat.total_messages += 2
        chat.total_tokens_used += token_usage.get("total_tokens", 0)
        chat.last_activity_at = datetime.now(timezone.utc)
        
        # 10. Update user statistics
        current_user.total_messages += 2
        current_user.total_tokens_used += token_usage.get("total_tokens", 0)
        current_user.last_activity = datetime.now(timezone.utc)
        
        # 11. Update user preferences based on interaction
        await update_user_preferences(
            user_id=current_user.id,
            message=chat_request.message,
            response=ai_response,
            emotion=emotion_data.get("primary_emotion") if emotion_data else None,
            db=db
        )
        
        # Commit all changes
        await db.commit()
        
        # Calculate total processing time
        total_processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Prepare response
        response_data = ChatResponse(
            response=ai_response,
            message_id=ai_message.id,
            chat_id=chat.id,
            emotion_analysis=emotion_data,
            token_usage=token_usage,
            processing_time=total_processing_time,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "ai_model": ai_response_data.get("model_used", chat.ai_model),
                "emotion_detected": emotion_data is not None,
                "personalization_applied": user_preferences is not None,
                "rag_context_used": rag_context_data is not None and len(rag_context_data.get("context_messages", [])) > 0,
                "user_message_id": user_message.id
            }
        )
        
        logger.info(f"Chat response generated for user {current_user.id} in {total_processing_time:.2f}s")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )

async def build_conversation_context(
    chat: Chat,
    user_preferences: Optional[Dict[str, Any]] = None,
    emotion_context: Optional[Dict[str, Any]] = None,
    rag_context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """Build conversation context with prompt service"""
    
    messages = []
    
    # Get conversation history from RAG context if available
    conversation_history = []
    if rag_context and rag_context.get("context_messages"):
        conversation_history = rag_context["context_messages"]
    
    # Use prompt service to get appropriate system prompt
    system_prompt = prompt_service.get_prompt_for_context(
        user_message="",  # Will be added later
        conversation_history=conversation_history,
        user_preferences=user_preferences,
        detected_emotion=emotion_context.get("recent_emotion") if emotion_context else None
    )
    
    # Add system prompt
    messages.append({"role": "system", "content": system_prompt})
    
    # Add RAG context messages if available
    if rag_context and rag_context.get("context_messages"):
        for ctx_msg in rag_context["context_messages"][-5:]:  # Limit context
            role = "user" if ctx_msg.get("sender_type") == "USER" else "assistant"
            messages.append({
                "role": role,
                "content": ctx_msg.get("content", "")
            })
    
    return messages

async def update_user_preferences(
    user_id: int,
    message: str,
    response: str,
    emotion: Optional[str],
    db: AsyncSession
) -> None:
    """Update user preferences based on interaction"""
    
    # Get or create user preference record
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    user_pref = result.scalar_one_or_none()
    
    if not user_pref:
        user_pref = UserPreference(
            user_id=user_id,
            preferences={}
        )
        db.add(user_pref)
    
    # Update interaction patterns
    patterns = user_pref.interaction_patterns or {}
    
    # Track message length preference
    msg_length = len(message)
    if msg_length < 50:
        patterns["message_length"] = "short"
    elif msg_length < 200:
        patterns["message_length"] = "medium"
    else:
        patterns["message_length"] = "long"
    
    # Track time of day preference
    hour = datetime.now().hour
    if 6 <= hour < 12:
        patterns["active_time"] = "morning"
    elif 12 <= hour < 18:
        patterns["active_time"] = "afternoon"
    elif 18 <= hour < 24:
        patterns["active_time"] = "evening"
    else:
        patterns["active_time"] = "night"
    
    # Track topic interests (simple keyword analysis)
    topics = []
    tech_keywords = ["code", "programming", "software", "tech", "computer", "ai", "app", "develop"]
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
    
    if topics:
        current_interests = user_pref.preferences.get("interests", [])
        user_pref.preferences["interests"] = list(set(current_interests + topics))[:10]  # Limit to 10 interests
    
    # Update emotional patterns
    if emotion:
        emotional_patterns = patterns.get("emotional_patterns", {})
        emotional_patterns[datetime.now().date().isoformat()] = emotion
        # Keep only last 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).date().isoformat()
        emotional_patterns = {k: v for k, v in emotional_patterns.items() if k >= cutoff_date}
        patterns["emotional_patterns"] = emotional_patterns
    
    user_pref.interaction_patterns = patterns
    user_pref.last_interaction_at = datetime.now(timezone.utc)

# Get conversation context endpoint
@router.get("/conversation-context/{chat_id}", response_model=ConversationContext)
async def get_conversation_context(
    chat_id: int,
    include_emotions: bool = Query(True, description="Include emotion history"),
    include_preferences: bool = Query(True, description="Include user preferences"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation context for a chat"""
    
    try:
        # Verify chat access
        result = await db.execute(
            select(Chat)
            .where(and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id
            ))
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Get recent messages
        messages_result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(desc(Message.created_at))
            .limit(20)
        )
        messages = messages_result.scalars().all()
        
        # Format messages
        context = [
            {
                "role": "user" if msg.sender_type == SenderType.USER else "assistant",
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "emotion": msg.emotion_detected
            }
            for msg in reversed(messages)
        ]
        
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
    
    # Check permissions
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        since_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        
        # Query emotions
        result = await db.execute(
            select(Emotion)
            .where(and_(
                Emotion.user_id == user_id,
                Emotion.detected_at >= since_time
            ))
            .order_by(desc(Emotion.detected_at))
        )
        emotions = result.scalars().all()
        
        # Analyze patterns
        emotion_counts = {}
        sentiment_scores = []
        
        for emotion in emotions:
            emotion_type = emotion.primary_emotion.value
            emotion_counts[emotion_type] = emotion_counts.get(emotion_type, 0) + 1
            sentiment_scores.append(emotion.sentiment_score)
        
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        return {
            "user_id": user_id,
            "time_window_hours": time_window_hours,
            "total_emotions": len(emotions),
            "emotion_distribution": emotion_counts,
            "average_sentiment": avg_sentiment,
            "dominant_emotion": max(emotion_counts, key=emotion_counts.get) if emotion_counts else None,
            "timeline": [
                {
                    "timestamp": e.detected_at.isoformat(),
                    "emotion": e.primary_emotion.value,
                    "sentiment": e.sentiment_score,
                    "confidence": e.confidence_score
                }
                for e in emotions[:50]  # Limit to recent 50
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get emotion patterns: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emotion patterns"
        )

# User emotions endpoint
@router.get("/user/emotions")
async def get_user_emotions(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's emotional history"""
    
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    result = await db.execute(
        select(Emotion)
        .where(
            and_(
                Emotion.user_id == current_user.id,
                Emotion.detected_at >= since_date
            )
        )
        .order_by(desc(Emotion.detected_at))
        .limit(100)
    )
    
    emotions = result.scalars().all()
    
    # Aggregate emotion data
    emotion_summary = {}
    for emotion in emotions:
        emotion_type = emotion.primary_emotion.value
        emotion_summary[emotion_type] = emotion_summary.get(emotion_type, 0) + 1
    
    return {
        "user_id": current_user.id,
        "period_days": days,
        "total_interactions": len(emotions),
        "emotion_distribution": emotion_summary,
        "recent_emotions": [
            {
                "timestamp": e.detected_at.isoformat(),
                "emotion": e.primary_emotion.value,
                "confidence": e.confidence_score,
                "sentiment": e.sentiment_score
            }
            for e in emotions[:10]
        ]
    }

# RAG context visualization endpoint
@router.get("/rag-context/{message_id}")
async def get_rag_context_for_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get RAG context used for a specific message"""
    
    # Get the message
    result = await db.execute(
        select(Message).where(
            and_(
                Message.id == message_id,
                Message.chat_id.in_(
                    select(Chat.id).where(Chat.user_id == current_user.id)
                )
            )
        )
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Get RAG context from message metadata
    rag_metadata = message.message_metadata.get("rag_context", {})
    
    # Get user preferences
    pref_result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == current_user.id)
    )
    user_pref = pref_result.scalar_one_or_none()
    
    # Get recent emotions
    emotion_result = await db.execute(
        select(Emotion)
        .where(Emotion.user_id == current_user.id)
        .order_by(desc(Emotion.detected_at))
        .limit(5)
    )
    recent_emotions = emotion_result.scalars().all()
    
    # Build emotional pattern
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
            "embeddingDimensions": 1536,
            "similarityThreshold": 0.7,
            "contextsRetrieved": len(rag_metadata.get("context_messages", []))
        }
    }

# Personalization info endpoint
@router.get("/personalization")
async def get_personalization_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
):
    """Get user's personalization data"""
    
    try:
        # Try to get cached preferences
        preferences = await personalization_service.get_cached_preferences(
            current_user.id,
            redis_client
        )
        
        # Get from database if not cached
        if not preferences:
            result = await db.execute(
                select(UserPreference)
                .where(UserPreference.user_id == current_user.id)
            )
            user_pref = result.scalar_one_or_none()
            
            if user_pref:
                preferences = user_pref.preferences
            else:
                preferences = {}
        
        # Get interaction stats
        message_count_result = await db.execute(
            select(func.count(Message.id))
            .join(Chat)
            .where(Chat.user_id == current_user.id)
        )
        message_count = message_count_result.scalar() or 0
        
        return {
            "user_id": current_user.id,
            "preferences": preferences,
            "interaction_count": message_count,
            "personalization_enabled": message_count >= personalization_service.min_interactions,
            "min_interactions_required": personalization_service.min_interactions,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get personalization info: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve personalization information"
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