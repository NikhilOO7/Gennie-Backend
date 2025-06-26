from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Any
import json
import logging
import asyncio
from datetime import datetime, timezone

from app.database import get_db, get_redis
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.routers.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat
    """
    
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_connections: Dict[int, List[int]] = {}  # user_id -> [chat_ids]
        self.chat_participants: Dict[int, List[int]] = {}  # chat_id -> [user_ids]
        
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Store connection
        connection_key = f"{user_id}_{chat_id}"
        self.active_connections[connection_key] = websocket
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        if chat_id not in self.user_connections[user_id]:
            self.user_connections[user_id].append(chat_id)
        
        # Track chat participants
        if chat_id not in self.chat_participants:
            self.chat_participants[chat_id] = []
        if user_id not in self.chat_participants[chat_id]:
            self.chat_participants[chat_id].append(user_id)
        
        logger.info(f"WebSocket connected: user {user_id}, chat {chat_id}")
        
        # Send connection confirmation
        await self.send_personal_message({
            "type": "connection_established",
            "chat_id": chat_id,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "Connected to chat successfully"
        }, chat_id, user_id)
    
    def disconnect(self, chat_id: int, user_id: int):
        """Remove a WebSocket connection"""
        connection_key = f"{user_id}_{chat_id}"
        
        if connection_key in self.active_connections:
            del self.active_connections[connection_key]
        
        # Clean up tracking
        if user_id in self.user_connections:
            if chat_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(chat_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        if chat_id in self.chat_participants:
            if user_id in self.chat_participants[chat_id]:
                self.chat_participants[chat_id].remove(user_id)
            if not self.chat_participants[chat_id]:
                del self.chat_participants[chat_id]
        
        logger.info(f"WebSocket disconnected: user {user_id}, chat {chat_id}")
    
    async def send_personal_message(self, message: dict, chat_id: int, user_id: int):
        """Send message to a specific user in a specific chat"""
        connection_key = f"{user_id}_{chat_id}"
        if connection_key in self.active_connections:
            websocket = self.active_connections[connection_key]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to {connection_key}: {str(e)}")
                # Remove broken connection
                self.disconnect(chat_id, user_id)
    
    async def broadcast_to_chat(self, message: dict, chat_id: int, exclude_user: Optional[int] = None):
        """Broadcast message to all users in a chat"""
        if chat_id in self.chat_participants:
            for user_id in self.chat_participants[chat_id]:
                if exclude_user and user_id == exclude_user:
                    continue
                await self.send_personal_message(message, chat_id, user_id)
    
    async def send_typing_indicator(self, chat_id: int, user_id: int, is_typing: bool):
        """Send typing indicator to other users in the chat"""
        message = {
            "type": "typing_indicator",
            "chat_id": chat_id,
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.broadcast_to_chat(message, chat_id, exclude_user=user_id)
    
    def get_active_users(self, chat_id: int) -> List[int]:
        """Get list of active users in a chat"""
        return self.chat_participants.get(chat_id, [])
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)

# Global connection manager
manager = ConnectionManager()

@router.websocket("/chat/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    WebSocket endpoint for real-time chat
    """
    try:
        # Verify token and get user
        from app.routers.auth import TokenData
        import jwt
        from app.config import settings
        
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("user_id")
            if not user_id:
                await websocket.close(code=1008, reason="Invalid token")
                return
        except jwt.JWTError:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        # Verify user exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            await websocket.close(code=1008, reason="User not found or inactive")
            return
        
        # Verify chat exists and user has access
        chat = db.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == user_id
        ).first()
        
        if not chat:
            await websocket.close(code=1008, reason="Chat not found or access denied")
            return
        
        # Connect to WebSocket
        await manager.connect(websocket, chat_id, user_id)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Process the message based on type
                response = await process_websocket_message(
                    message_data, chat_id, user_id, user, db, redis
                )
                
                # Send response back to client
                if response:
                    await manager.send_personal_message(response, chat_id, user_id)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally: user {user_id}, chat {chat_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
            await manager.send_personal_message({
                "type": "error",
                "message": "An error occurred. Please refresh the page.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, chat_id, user_id)
        finally:
            manager.disconnect(chat_id, user_id)
            
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass

async def process_websocket_message(
    message_data: dict,
    chat_id: int,
    user_id: int,
    user: User,
    db: Session,
    redis
) -> Optional[dict]:
    """
    Process different types of WebSocket messages
    """
    message_type = message_data.get("type", "chat_message")
    
    try:
        if message_type == "chat_message":
            return await handle_chat_message(message_data, chat_id, user_id, user, db, redis)
        
        elif message_type == "typing_start":
            await manager.send_typing_indicator(chat_id, user_id, True)
            return None
        
        elif message_type == "typing_stop":
            await manager.send_typing_indicator(chat_id, user_id, False)
            return None
        
        elif message_type == "get_chat_history":
            return await handle_get_chat_history(message_data, chat_id, user_id, db)
        
        elif message_type == "regenerate_response":
            return await handle_regenerate_response(message_data, chat_id, user_id, user, db, redis)
        
        elif message_type == "ping":
            return {"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()}
        
        else:
            return {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {str(e)}")
        return {
            "type": "error",
            "message": "Failed to process message. Please try again.",
            "error_details": str(e) if user.get_setting("debug_mode", False) else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

async def handle_chat_message(
    message_data: dict,
    chat_id: int,
    user_id: int,
    user: User,
    db: Session,
    redis
) -> dict:
    """
    Handle chat message and generate AI response
    """
    user_message = message_data.get("message", "").strip()
    
    if not user_message:
        return {
            "type": "error",
            "message": "Message cannot be empty",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    try:
        # Send "AI is thinking" indicator
        await manager.send_personal_message({
            "type": "ai_thinking",
            "message": "AI is thinking...",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, chat_id, user_id)
        
        # 1. Analyze emotion
        emotion_data = await emotion_service.analyze_emotion(user_message)
        
        # 2. Save user message
        user_msg = Message(
            chat_id=chat_id,
            content=user_message,
            sender_type="user",
            emotion_data=emotion_data,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        
        # 3. Get conversation context
        context_messages = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.timestamp.desc())
            .limit(10)
            .all()
        )
        context_messages.reverse()
        
        # 4. Get personalization data
        personalization_data = await personalization_service.get_user_context(
            user_id, chat_id, redis
        )
        
        # 5. Prepare context for AI
        conversation_context = []
        for msg in context_messages[:-1]:  # Exclude current message
            conversation_context.append({
                "role": "user" if msg.sender_type == "user" else "assistant",
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            })
        
        # 6. Get chat settings
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        chat_settings = {
            "model": chat.ai_model,
            "temperature": float(chat.temperature),
            "max_tokens": chat.max_tokens,
            "system_prompt": chat.system_prompt
        }
        
        # 7. Generate AI response
        ai_response_data = await openai_service.generate_response(
            message=user_message,
            context=conversation_context,
            chat_settings=chat_settings,
            emotion_data=emotion_data,
            personalization_data=personalization_data
        )
        
        ai_response = ai_response_data.get("response", "I'm sorry, I couldn't generate a response.")
        token_usage = ai_response_data.get("usage", {})
        
        # 8. Save AI response
        ai_msg = Message(
            chat_id=chat_id,
            content=ai_response,
            sender_type="assistant",
            message_metadata={"token_usage": token_usage, "model": chat.ai_model},  # Using correct field
            timestamp=datetime.now(timezone.utc)
        )
        db.add(ai_msg)
        
        # 9. Update chat and user stats
        chat.last_activity_at = datetime.now(timezone.utc)
        chat.updated_at = datetime.now(timezone.utc)
        
        user.increment_usage_stats(
            messages=2,  # User message + AI response
            tokens=token_usage.get("total_tokens", 0)
        )
        user.update_activity()
        
        db.commit()
        db.refresh(ai_msg)
        
        # 10. Update personalization data (background task)
        asyncio.create_task(
            personalization_service.update_user_interaction(
                user_id, chat_id, user_message, ai_response, emotion_data, redis
            )
        )
        
        # 11. Return response
        return {
            "type": "chat_response",
            "user_message": {
                "id": user_msg.id,
                "content": user_message,
                "timestamp": user_msg.timestamp.isoformat(),
                "emotion_data": emotion_data
            },
            "ai_response": {
                "id": ai_msg.id,
                "content": ai_response,
                "timestamp": ai_msg.timestamp.isoformat(),
                "token_usage": token_usage
            },
            "chat_id": chat_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error handling chat message: {str(e)}")
        db.rollback()
        
        # Save error message
        error_msg = Message(
            chat_id=chat_id,
            content="I apologize, but I encountered an error processing your message. Please try again.",
            sender_type="assistant",
            message_metadata={"error": str(e), "error_type": type(e).__name__},  # Using correct field
            timestamp=datetime.now(timezone.utc)
        )
        db.add(error_msg)
        db.commit()
        db.refresh(error_msg)
        
        return {
            "type": "error_response",
            "user_message": {
                "content": user_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "error_message": {
                "id": error_msg.id,
                "content": error_msg.content,
                "timestamp": error_msg.timestamp.isoformat()
            },
            "error": "Failed to generate AI response",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

async def handle_get_chat_history(
    message_data: dict,
    chat_id: int,
    user_id: int,
    db: Session
) -> dict:
    """
    Get chat history for the WebSocket client
    """
    try:
        limit = message_data.get("limit", 50)
        offset = message_data.get("offset", 0)
        
        messages = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        messages.reverse()  # Show in chronological order
        
        message_list = []
        for msg in messages:
            message_list.append({
                "id": msg.id,
                "content": msg.content,
                "sender_type": msg.sender_type,
                "timestamp": msg.timestamp.isoformat(),
                "emotion_data": msg.emotion_data,
                "metadata": msg.message_metadata  # Using correct field
            })
        
        return {
            "type": "chat_history",
            "messages": message_list,
            "chat_id": chat_id,
            "total_count": db.query(Message).filter(Message.chat_id == chat_id).count(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting chat history: {str(e)}")
        return {
            "type": "error",
            "message": "Failed to retrieve chat history",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

async def handle_regenerate_response(
    message_data: dict,
    chat_id: int,
    user_id: int,
    user: User,
    db: Session,
    redis
) -> dict:
    """
    Regenerate the last AI response
    """
    try:
        message_id = message_data.get("message_id")
        
        if not message_id:
            return {
                "type": "error",
                "message": "Message ID is required for regeneration",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get the message to regenerate
        original_message = db.query(Message).filter(
            Message.id == message_id,
            Message.chat_id == chat_id,
            Message.sender_type == "assistant"
        ).first()
        
        if not original_message:
            return {
                "type": "error",
                "message": "Message not found or cannot be regenerated",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Get the user message that prompted this response
        user_message = db.query(Message).filter(
            Message.chat_id == chat_id,
            Message.sender_type == "user",
            Message.timestamp < original_message.timestamp
        ).order_by(Message.timestamp.desc()).first()
        
        if not user_message:
            return {
                "type": "error",
                "message": "Cannot find original user message",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Send "AI is thinking" indicator
        await manager.send_personal_message({
            "type": "ai_thinking",
            "message": "Regenerating response...",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, chat_id, user_id)
        
        # Follow similar process as handle_chat_message but for regeneration
        # ... (similar AI generation logic)
        
        # For brevity, this is a simplified version
        return {
            "type": "response_regenerated",
            "original_message_id": message_id,
            "new_response": "This is a regenerated response (implementation simplified)",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error regenerating response: {str(e)}")
        return {
            "type": "error",
            "message": "Failed to regenerate response",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@router.get("/stats")
async def websocket_stats():
    """
    Get WebSocket connection statistics
    """
    return {
        "active_connections": manager.get_connection_count(),
        "active_chats": len(manager.chat_participants),
        "active_users": len(manager.user_connections),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }