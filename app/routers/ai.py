from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone  # Fixed: Added proper datetime imports
import logging
import json

from app.database import get_db, get_redis
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])

# Pydantic models
class ChatMessage(BaseModel):
    chat_id: int
    message: str
    stream: bool = False
    context_window: int = Field(default=10, ge=1, le=50)

class ChatResponse(BaseModel):
    response: str
    emotion_data: Dict[str, Any]
    user_message_id: int
    ai_message_id: int
    timestamp: datetime
    processing_time: float
    token_usage: Optional[Dict[str, int]] = None

class ConversationSummary(BaseModel):
    chat_id: int
    summary: str
    key_topics: List[str]
    sentiment_trend: str
    total_messages: int
    generated_at: datetime

class PromptTemplate(BaseModel):
    name: str
    template: str
    variables: List[str]
    category: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Main chat endpoint with AI response generation
    Enhanced with modern error handling and performance monitoring
    """
    start_time = datetime.now(timezone.utc)
    
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_request.chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    try:
        logger.info(f"Processing chat request for user {current_user.id}, chat {chat_request.chat_id}")
        
        # 1. Analyze user message emotion
        emotion_data = await emotion_service.analyze_emotion(chat_request.message)
        logger.info(f"Emotion analysis complete: {emotion_data.get('compound', 0)}")
        
        # 2. Save user message with modern timestamp
        user_message = Message(
            chat_id=chat_request.chat_id,
            content=chat_request.message,
            sender_type="user",
            emotion_data=emotion_data,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 3. Get conversation context with specified window
        context_messages = (
            db.query(Message)
            .filter(Message.chat_id == chat_request.chat_id)
            .order_by(Message.timestamp.desc())
            .limit(chat_request.context_window)
            .all()
        )
        context_messages.reverse()  # Reverse to chronological order
        
        # 4. Get user personalization data
        personalization_data = await personalization_service.get_user_context(
            current_user.id, 
            chat_request.chat_id,
            redis
        )
        
        # 5. Prepare context for AI
        conversation_context = []
        for msg in context_messages[:-1]:  # Exclude the current message
            conversation_context.append({
                "role": "user" if msg.sender_type == "user" else "assistant",
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "emotion": msg.emotion_data
            })
        
        # 6. Generate AI response
        ai_response_data = await openai_service.generate_response(
            message=chat_request.message,
            context=conversation_context,
            chat_settings={
                "model": chat.ai_model,
                "temperature": float(chat.temperature),
                "max_tokens": chat.max_tokens,
                "system_prompt": chat.system_prompt
            },
            emotion_data=emotion_data,
            personalization_data=personalization_data
        )
        
        ai_response = ai_response_data.get("response", "I'm sorry, I couldn't generate a response.")
        token_usage = ai_response_data.get("usage", {})
        
        # 7. Save AI response
        ai_message = Message(
            chat_id=chat_request.chat_id,
            content=ai_response,
            sender_type="assistant",
            message_metadata={"token_usage": token_usage, "model": chat.ai_model},  # Using correct field
            timestamp=datetime.now(timezone.utc)
        )
        db.add(ai_message)
        
        # 8. Update chat activity
        chat.last_activity_at = datetime.now(timezone.utc)
        chat.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(ai_message)
        
        # 9. Update conversation context in Redis (background task)
        background_tasks.add_task(
            update_conversation_context,
            chat_request.chat_id,
            user_message.dict() if hasattr(user_message, 'dict') else {
                "id": user_message.id,
                "content": user_message.content,
                "sender_type": user_message.sender_type,
                "timestamp": user_message.timestamp.isoformat()
            },
            {
                "id": ai_message.id,
                "content": ai_message.content,
                "sender_type": ai_message.sender_type,
                "timestamp": ai_message.timestamp.isoformat()
            },
            redis
        )
        
        # 10. Update personalization data (background task)
        background_tasks.add_task(
            personalization_service.update_user_interaction,
            current_user.id,
            chat_request.chat_id,
            chat_request.message,
            ai_response,
            emotion_data,
            redis
        )
        
        # Calculate processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(f"Chat response generated successfully in {processing_time:.2f}s")
        
        return ChatResponse(
            response=ai_response,
            emotion_data=emotion_data,
            user_message_id=user_message.id,
            ai_message_id=ai_message.id,
            timestamp=ai_message.timestamp,
            processing_time=processing_time,
            token_usage=token_usage
        )
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        db.rollback()
        
        # Save error message
        error_message = Message(
            chat_id=chat_request.chat_id,
            content="I apologize, but I encountered an error processing your message. Please try again.",
            sender_type="assistant",
            message_metadata={"error": str(e), "error_type": type(e).__name__},  # Using correct field
            timestamp=datetime.now(timezone.utc)
        )
        db.add(error_message)
        db.commit()
        db.refresh(error_message)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        return ChatResponse(
            response="I apologize, but I encountered an error processing your message. Please try again.",
            emotion_data={"error": True, "compound": 0.0},
            user_message_id=user_message.id if 'user_message' in locals() else 0,
            ai_message_id=error_message.id,
            timestamp=error_message.timestamp,
            processing_time=processing_time
        )

@router.get("/chat/{chat_id}/summary", response_model=ConversationSummary)
async def get_conversation_summary(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a summary of the conversation"""
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get all messages for the chat
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.timestamp.asc()).all()
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages found in chat")
    
    # Generate summary using AI service
    summary_data = await openai_service.generate_conversation_summary(
        messages=[{
            "role": "user" if msg.sender_type == "user" else "assistant",
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        } for msg in messages]
    )
    
    # Analyze sentiment trend
    sentiment_scores = [msg.emotion_data.get('compound', 0) for msg in messages if msg.emotion_data]
    if sentiment_scores:
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        if avg_sentiment > 0.1:
            sentiment_trend = "positive"
        elif avg_sentiment < -0.1:
            sentiment_trend = "negative"
        else:
            sentiment_trend = "neutral"
    else:
        sentiment_trend = "neutral"
    
    return ConversationSummary(
        chat_id=chat_id,
        summary=summary_data.get("summary", "No summary available"),
        key_topics=summary_data.get("key_topics", []),
        sentiment_trend=sentiment_trend,
        total_messages=len(messages),
        generated_at=datetime.now(timezone.utc)
    )

@router.get("/prompts", response_model=List[PromptTemplate])
async def get_prompt_templates():
    """Get available prompt templates"""
    return [
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
        ),
        PromptTemplate(
            name="Business Analyst",
            template="You are a business analyst. Analyze {data_type} and provide insights on {business_area}.",
            variables=["data_type", "business_area"],
            category="business"
        )
    ]

@router.post("/analyze-sentiment")
async def analyze_text_sentiment(
    text: str,
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
        logger.error(f"Error analyzing sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to analyze sentiment")

async def update_conversation_context(
    chat_id: int,
    user_message: Dict[str, Any],
    ai_message: Dict[str, Any],
    redis
):
    """Background task to update conversation context in Redis"""
    try:
        cache_key = f"conversation_context:{chat_id}"
        
        # Get existing context
        existing_context = await redis.get(cache_key)
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
        await redis.setex(cache_key, 3600, json.dumps(context, default=str))
        
        logger.info(f"Updated conversation context for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Failed to update conversation context: {str(e)}")

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
        
        return {
            "status": "healthy" if all([openai_healthy, emotion_healthy, personalization_healthy]) else "degraded",
            "services": {
                "openai": "healthy" if openai_healthy else "unhealthy",
                "emotion_analysis": "healthy" if emotion_healthy else "unhealthy",
                "personalization": "healthy" if personalization_healthy else "unhealthy"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI service health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }