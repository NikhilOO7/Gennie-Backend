from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import time
import logging

from app.core.database import get_db, get_redis
from app.core.config import settings
from app.schemas import ConversationRequest, ConversationResponse
from app.services.openai_service import openai_service
from app.services.prompt_service import prompt_service
from app.models.chat import Chat, Message
from app.models.user_preference import UserPreference

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ConversationResponse)
async def chat_with_ai(
    request: ConversationRequest, 
    db: Session = Depends(get_db)
):
    """Send a message to the AI and get a response"""
    try:
        start_time = time.time()
        
        # For now, we'll use a temporary user_id since auth isn't implemented yet
        temp_user_id = 1
        
        # Get or create chat
        chat = None
        if request.chat_id:
            chat = db.query(Chat).filter(Chat.id == request.chat_id).first()
            if not chat:
                raise HTTPException(
                    status_code=404,
                    detail="Chat not found"
                )
        else:
            # Create new chat
            chat = Chat(
                user_id=temp_user_id,
                title="New Chat",
                is_active=True
            )
            db.add(chat)
            db.commit()
            db.refresh(chat)
        
        # Get conversation history if requested
        conversation_history = []
        if request.use_context and chat:
            recent_messages = db.query(Message).filter(
                Message.chat_id == chat.id
            ).order_by(Message.created_at.desc()).limit(10).all()
            
            # Convert to conversation format (reverse to get chronological order)
            for msg in reversed(recent_messages):
                role = "user" if msg.is_from_user else "assistant"
                conversation_history.append({
                    "role": role,
                    "content": msg.content
                })
        
        # Get user preferences (default for now)
        user_preferences = {
            "conversation_style": "friendly",
            "preferred_response_length": "medium",
            "language": "en",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Build system prompt using prompt service
        system_prompt = prompt_service.get_prompt_for_context(
            user_message=request.message,
            conversation_history=conversation_history,
            user_preferences=user_preferences,
            detected_emotion=None  # Will be implemented later
        )
        
        # Generate AI response
        ai_response = await openai_service.generate_conversation_response(
            user_message=request.message,
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            user_preferences=user_preferences
        )
        
        # Save user message to database
        user_message = Message(
            chat_id=chat.id,
            content=request.message,
            is_from_user=True,
            message_type="text",
            created_at=datetime.utcnow()
        )
        db.add(user_message)
        
        # Save AI response to database
        ai_message = Message(
            chat_id=chat.id,
            content=ai_response["response"],
            is_from_user=False,
            message_type="text",
            tokens_used=ai_response["tokens_used"],
            processing_time=ai_response["processing_time"],
            created_at=datetime.utcnow()
        )
        db.add(ai_message)
        
        # Update chat statistics
        chat.total_messages += 2  # User message + AI response
        chat.last_message_at = datetime.utcnow()
        
        # Generate chat title if it's the first exchange
        if chat.total_messages == 2 and chat.title == "New Chat":
            try:
                new_title = await openai_service.generate_chat_title([request.message])
                chat.title = new_title
            except Exception as e:
                logger.warning(f"Failed to generate chat title: {e}")
        
        db.commit()
        db.refresh(ai_message)
        
        total_time = time.time() - start_time
        
        return ConversationResponse(
            response=ai_response["response"],
            chat_id=chat.id,
            message_id=ai_message.id,
            tokens_used=ai_response["tokens_used"],
            processing_time=total_time,
            emotion_detected=None,  # Will be implemented later
            sentiment_score=None    # Will be implemented later
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat service error: {str(e)}"
        )

@router.get("/chat/{chat_id}/context")
async def get_conversation_context(chat_id: int, db: Session = Depends(get_db)):
    """Get conversation context for a chat"""
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Get recent messages
        messages = db.query(Message).filter(
            Message.chat_id == chat_id
        ).order_by(Message.created_at.desc()).limit(20).all()
        
        context = {
            "chat_id": chat_id,
            "title": chat.title,
            "total_messages": chat.total_messages,
            "recent_messages": [
                {
                    "id": msg.id,
                    "content": msg.content,
                    "is_from_user": msg.is_from_user,
                    "created_at": msg.created_at.isoformat(),
                    "tokens_used": msg.tokens_used
                }
                for msg in reversed(messages)
            ]
        }
        
        return context
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve conversation context"
        )

@router.post("/generate-title")
async def generate_chat_title(messages: List[str]):
    """Generate a title for a chat based on messages"""
    try:
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        title = await openai_service.generate_chat_title(messages)
        return {"title": title}
        
    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate chat title"
        )

@router.post("/analyze-emotion")
async def analyze_emotion(text: str):
    """Analyze emotion in text using AI"""
    try:
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        # Use OpenAI for emotion analysis (we'll add VADER later)
        analysis = await openai_service.analyze_sentiment_with_ai(text)
        
        return {
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing emotion: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze emotion"
        )

@router.get("/prompts/templates")
async def get_prompt_templates():
    """Get available prompt templates"""
    try:
        templates = {
            name: {
                "name": template.name,
                "variables": template.variables
            }
            for name, template in prompt_service.templates.items()
        }
        
        return {
            "templates": templates,
            "total_count": len(templates)
        }
        
    except Exception as e:
        logger.error(f"Error getting prompt templates: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve prompt templates"
        )

@router.post("/test-connection")
async def test_ai_connection():
    """Test AI service connection"""
    try:
        is_connected = await openai_service.test_connection()
        
        return {
            "connected": is_connected,
            "service": "OpenAI",
            "model": settings.openai_model,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error testing AI connection: {e}")
        return {
            "connected": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Health check for AI system
@router.get("/health")
async def ai_health_check():
    """Health check for AI system"""
    # Check OpenAI API key is configured
    openai_configured = bool(settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here")
    
    return {
        "status": "healthy" if openai_configured else "warning",
        "message": "AI system is ready" if openai_configured else "OpenAI API key not configured",
        "timestamp": datetime.utcnow().isoformat(),
        "configuration": {
            "openai_api_key_configured": openai_configured,
            "openai_model": settings.openai_model,
            "temperature": settings.openai_temperature,
            "max_tokens": settings.openai_max_tokens
        },
        "features": {
            "ai_chat": "not_implemented",
            "emotion_analysis": "not_implemented",
            "conversation_context": "not_implemented",
            "title_generation": "not_implemented"
        }
    }