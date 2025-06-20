from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import asyncio

from app.database import get_db, get_redis
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service
from app.routers.auth import get_current_user
import json

router = APIRouter(prefix="/api/ai", tags=["ai"])

class ChatMessage(BaseModel):
    chat_id: int
    message: str
    context_length: Optional[int] = 10
    use_personalization: bool = True

class ChatResponse(BaseModel):
    response: str
    emotion_data: Dict[str, Any]
    message_id: int
    response_time: float
    personalization_applied: bool = False

class ConversationSummary(BaseModel):
    chat_id: int
    summary: str
    key_topics: List[str]
    emotion_patterns: Dict[str, Any]
    message_count: int

class AIStats(BaseModel):
    total_conversations: int
    total_ai_responses: int
    average_response_time: float
    most_common_emotions: List[str]

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """Main chat endpoint with AI response generation"""
    import time
    start_time = time.time()
    
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_request.chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    try:
        # 1. Analyze user message emotion
        emotion_data = await emotion_service.analyze_emotion(chat_request.message)
        
        # 2. Save user message
        user_message = Message(
            chat_id=chat_request.chat_id,
            content=chat_request.message,
            sender_type="user",
            emotion_data=emotion_data
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 3. Get conversation context
        context = await get_conversation_context(
            db, chat_request.chat_id, chat_request.context_length
        )
        
        # 4. Get personalization data if requested
        personalization_data = {}
        if chat_request.use_personalization:
            personalization_data = await personalization_service.get_personalized_context(
                db, current_user.id
            )
        
        # 5. Generate AI response
        ai_response = await openai_service.generate_response(
            message=chat_request.message,
            context=context,
            emotion_data=emotion_data,
            personalization=personalization_data
        )
        
        # 6. Save AI response
        ai_message = Message(
            chat_id=chat_request.chat_id,
            content=ai_response,
            sender_type="assistant",
            emotion_data={"response_to": emotion_data}
        )
        db.add(ai_message)
        
        # 7. Update chat timestamp
        chat.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ai_message)
        
        # 8. Learn from conversation (background task)
        if chat_request.use_personalization:
            background_tasks.add_task(
                personalization_service.learn_from_conversation,
                db, current_user.id, chat_request.message, emotion_data
            )
        
        response_time = time.time() - start_time
        
        return ChatResponse(
            response=ai_response,
            emotion_data=emotion_data,
            message_id=ai_message.id,
            response_time=response_time,
            personalization_applied=chat_request.use_personalization
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

@router.get("/chat/{chat_id}/summary", response_model=ConversationSummary)
async def get_conversation_summary(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation summary and analysis"""
    # Verify chat belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get all messages
    messages = db.query(Message).filter(Message.chat_id == chat_id).all()
    
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")
    
    # Generate summary using AI
    conversation_text = "\n".join([f"{msg.sender_type}: {msg.content}" for msg in messages])
    
    summary = await openai_service.generate_summary(conversation_text)
    key_topics = await openai_service.extract_topics(conversation_text)
    
    # Analyze emotion patterns
    emotions = [msg.emotion_data for msg in messages if msg.emotion_data]
    emotion_patterns = analyze_emotion_patterns(emotions)
    
    return ConversationSummary(
        chat_id=chat_id,
        summary=summary,
        key_topics=key_topics,
        emotion_patterns=emotion_patterns,
        message_count=len(messages)
    )

@router.get("/stats", response_model=AIStats)
async def get_ai_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI usage statistics"""
    # Get user's chats
    user_chats = db.query(Chat).filter(Chat.user_id == current_user.id).all()
    chat_ids = [chat.id for chat in user_chats]
    
    if not chat_ids:
        return AIStats(
            total_conversations=0,
            total_ai_responses=0,
            average_response_time=0.0,
            most_common_emotions=[]
        )
    
    # Count AI responses
    ai_responses = db.query(Message).filter(
        Message.chat_id.in_(chat_ids),
        Message.sender_type == "assistant"
    ).all()
    
    # Calculate average response time (if stored)
    response_times = [msg.metadata.get('response_time', 0) for msg in ai_responses if msg.metadata]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Get emotion data
    emotions = []
    for msg in ai_responses:
        if msg.emotion_data:
            emotion = msg.emotion_data.get('emotion')
            if emotion:
                emotions.append(emotion)
    
    # Count most common emotions
    emotion_counts = {}
    for emotion in emotions:
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    most_common = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    most_common_emotions = [emotion for emotion, count in most_common]
    
    return AIStats(
        total_conversations=len(user_chats),
        total_ai_responses=len(ai_responses),
        average_response_time=avg_response_time,
        most_common_emotions=most_common_emotions
    )

@router.post("/regenerate")
async def regenerate_response(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate AI response for a specific message"""
    # Verify chat and message belong to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.chat_id == chat_id,
        Message.sender_type == "assistant"
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="AI message not found")
    
    # Get the user message that this was responding to
    user_message = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.sender_type == "user",
        Message.timestamp < message.timestamp
    ).order_by(Message.timestamp.desc()).first()
    
    if not user_message:
        raise HTTPException(status_code=404, detail="Original user message not found")
    
    # Get context and regenerate
    context = await get_conversation_context(db, chat_id, 10)
    emotion_data = user_message.emotion_data or {}
    
    new_response = await openai_service.generate_response(
        message=user_message.content,
        context=context,
        emotion_data=emotion_data,
        personalization={}
    )
    
    # Update the message
    message.content = new_response
    message.metadata = {
        "regenerated": True,
        "regenerated_at": datetime.utcnow().isoformat()
    }
    
    db.commit()
    
    return {"message": "Response regenerated successfully", "new_response": new_response}

# Utility functions
async def get_conversation_context(db: Session, chat_id: int, limit: int = 10) -> List[Dict]:
    """Get recent conversation context"""
    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    context = []
    for msg in reversed(messages):  # Reverse to get chronological order
        context.append({
            "role": "user" if msg.sender_type == "user" else "assistant",
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        })
    
    return context

def analyze_emotion_patterns(emotions: List[Dict]) -> Dict[str, Any]:
    """Analyze emotion patterns from message data"""
    if not emotions:
        return {}
    
    # Extract emotion values
    emotion_values = []
    for emotion_data in emotions:
        if isinstance(emotion_data, dict) and 'emotion' in emotion_data:
            emotion_values.append(emotion_data['emotion'])
    
    if not emotion_values:
        return {}
    
    # Count emotions
    emotion_counts = {}
    for emotion in emotion_values:
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    # Calculate patterns
    total_emotions = len(emotion_values)
    emotion_percentages = {
        emotion: (count / total_emotions) * 100 
        for emotion, count in emotion_counts.items()
    }
    
    dominant_emotion = max(emotion_counts, key=emotion_counts.get)
    
    return {
        "emotion_distribution": emotion_percentages,
        "dominant_emotion": dominant_emotion,
        "total_analyzed": total_emotions,
        "unique_emotions": len(emotion_counts)
    }