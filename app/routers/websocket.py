"""
WebSocket Router - Real-time chat communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, List, Optional, Any
import json
import logging
import asyncio
from datetime import datetime, timezone
import jwt

from app.database import get_db, get_redis
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, SenderType
from app.config import settings
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    """
    Manages WebSocket connections for real-time chat
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, List[str]] = {}  # user_id -> [connection_ids]
        self.chat_connections: Dict[int, List[str]] = {}  # chat_id -> [connection_ids] 
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: int, chat_id: int):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(connection_id)
        
        # Track chat connections
        if chat_id not in self.chat_connections:
            self.chat_connections[chat_id] = []
        self.chat_connections[chat_id].append(connection_id)
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "connected_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc)
        }
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id}, chat: {chat_id})")
    
    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id not in self.active_connections:
            return
        
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")
        chat_id = metadata.get("chat_id")
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            if connection_id in self.user_connections[user_id]:
                self.user_connections[user_id].remove(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from chat connections
        if chat_id and chat_id in self.chat_connections:
            if connection_id in self.chat_connections[chat_id]:
                self.chat_connections[chat_id].remove(connection_id)
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]
        
        # Remove metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message, default=str))
                
                # Update activity
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = datetime.now(timezone.utc)
                    
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {str(e)}")
                self.disconnect(connection_id)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: int):
        """Send message to all connections of a user"""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id].copy():
                await self.send_personal_message(message, connection_id)
    
    async def send_to_chat(self, message: Dict[str, Any], chat_id: int, exclude_connection: Optional[str] = None):
        """Send message to all connections in a chat"""
        if chat_id in self.chat_connections:
            for connection_id in self.chat_connections[chat_id].copy():
                if connection_id != exclude_connection:
                    await self.send_personal_message(message, connection_id)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connections"""
        for connection_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, connection_id)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for a user"""
        return len(self.user_connections.get(user_id, []))
    
    def get_chat_connection_count(self, chat_id: int) -> int:
        """Get number of connections for a chat"""
        return len(self.chat_connections.get(chat_id, []))
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "unique_chats": len(self.chat_connections),
            "connections_by_user": {uid: len(conns) for uid, conns in self.user_connections.items()},
            "connections_by_chat": {cid: len(conns) for cid, conns in self.chat_connections.items()}
        }

# Global connection manager
manager = ConnectionManager()

async def verify_websocket_token(token: str) -> Dict[str, Any]:
    """Verify WebSocket authentication token"""
    try:
        payload = jwt.decode(
            token, 
            settings.get_secret_key(), 
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Invalid token type")
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

async def get_websocket_user(token: str, db: AsyncSession) -> User:
    """Get user from WebSocket token"""
    payload = await verify_websocket_token(token)
    user_id_str = payload.get("sub")
    
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # FIXED: Convert string subject back to integer
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid user ID format")
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user

async def process_websocket_message(
    message_data: Dict[str, Any],
    connection_id: str,
    user: User,
    chat: Chat,
    db: AsyncSession,
    redis_client
) -> Optional[Dict[str, Any]]:
    """Process incoming WebSocket message"""
    
    try:
        message_type = message_data.get("type")
        
        if message_type == "chat_message":
            return await handle_chat_message(message_data, connection_id, user, chat, db, redis_client)
        elif message_type == "typing_start":
            return await handle_typing_indicator(message_data, connection_id, user, chat, True)
        elif message_type == "typing_stop":
            return await handle_typing_indicator(message_data, connection_id, user, chat, False)
        elif message_type == "ping":
            return await handle_ping(message_data, connection_id)
        elif message_type == "get_status":
            return await handle_status_request(message_data, connection_id, user, chat)
        else:
            return {
                "type": "error",
                "error": f"Unknown message type: {message_type}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    except Exception as e:
        logger.error(f"Error processing WebSocket message: {str(e)}", exc_info=True)
        return {
            "type": "error",
            "error": "Failed to process message",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

async def handle_chat_message(
    message_data: Dict[str, Any],
    connection_id: str,
    user: User,
    chat: Chat,
    db: AsyncSession,
    redis_client
) -> Dict[str, Any]:
    """Handle chat message via WebSocket"""
    
    content = message_data.get("content", "").strip()
    if not content:
        return {
            "type": "error",
            "error": "Message content cannot be empty"
        }
    
    if len(content) > 4000:
        return {
            "type": "error", 
            "error": "Message too long (max 4000 characters)"
        }
    
    start_time = datetime.now(timezone.utc)
    
    try:
        # Create user message
        user_message = Message.create_user_message(
            chat_id=chat.id,
            content=content
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)
        
        # Send acknowledgment to sender
        await manager.send_personal_message({
            "type": "message_sent",
            "message_id": user_message.id,
            "content": content,
            "timestamp": user_message.created_at.isoformat(),
            "status": "sent"
        }, connection_id)
        
        # Broadcast user message to other chat participants
        await manager.send_to_chat({
            "type": "user_message",
            "message_id": user_message.id,
            "user_id": user.id,
            "username": user.username,
            "content": content,
            "timestamp": user_message.created_at.isoformat()
        }, chat.id, exclude_connection=connection_id)
        
        # Analyze emotion if enabled
        emotion_data = None
        if chat.get_setting("enable_emotion_detection", True):
            try:
                emotion_analysis = await emotion_service.analyze_emotion(
                    content,
                    context={"user_id": user.id, "chat_id": chat.id}
                )
                
                if emotion_analysis.get("success"):
                    emotion_data = emotion_analysis
                    user_message.set_emotion_data(
                        sentiment_score=emotion_data.get("sentiment_score", 0.0),
                        emotion=emotion_data.get("primary_emotion", "neutral"),
                        confidence=emotion_data.get("confidence_score", 0.0)
                    )
            except Exception as e:
                logger.warning(f"Emotion analysis failed: {str(e)}")
        
        # Get user preferences for personalization
        user_preferences = None
        if chat.get_setting("enable_personalization", True):
            try:
                user_preferences = await personalization_service.get_cached_preferences(
                    user.id, redis_client
                )
            except Exception as e:
                logger.warning(f"Failed to get user preferences: {str(e)}")
        
        # Build conversation context
        conversation_messages = []
        
        # Add system prompt
        system_prompt = chat.system_prompt
        if not system_prompt and user_preferences:
            emotion_context = {"recent_emotion": emotion_data.get("primary_emotion")} if emotion_data else None
            system_prompt = await personalization_service.generate_personalized_system_prompt(
                user_preferences, emotion_context
            )
        
        if system_prompt:
            conversation_messages.append({"role": "system", "content": system_prompt})
        
        # Add recent messages for context
        context_messages = chat.get_context_messages()
        for msg in context_messages:
            if msg.sender_type == SenderType.USER:
                conversation_messages.append({"role": "user", "content": msg.content})
            elif msg.sender_type == SenderType.ASSISTANT:
                conversation_messages.append({"role": "assistant", "content": msg.content})
        
        # Add current user message
        conversation_messages.append({"role": "user", "content": content})
        
        # Send typing indicator
        await manager.send_to_chat({
            "type": "ai_typing",
            "chat_id": chat.id,
            "is_typing": True
        }, chat.id)
        
        # Generate AI response
        ai_response_data = await openai_service.generate_chat_response(
            messages=conversation_messages,
            temperature=chat.temperature,
            max_tokens=chat.max_tokens,
            model=chat.ai_model,
            user_id=str(user.id)
        )
        
        if not ai_response_data.get("success"):
            await manager.send_to_chat({
                "type": "ai_typing",
                "chat_id": chat.id,
                "is_typing": False
            }, chat.id)
            
            return {
                "type": "error",
                "error": f"AI response failed: {ai_response_data.get('error', 'Unknown error')}"
            }
        
        ai_response = ai_response_data["response"]
        token_usage = ai_response_data["tokens_used"]
        
        # Create AI message
        ai_message = Message.create_assistant_message(
            chat_id=chat.id,
            content=ai_response,
            tokens_used=token_usage.get("total_tokens", 0),
            processing_time=ai_response_data["processing_time"]
        )
        
        ai_message.set_metadata("ai_model", chat.ai_model)
        ai_message.set_metadata("websocket_response", True)
        if user_preferences:
            ai_message.set_metadata("personalization_applied", True)
        
        db.add(ai_message)
        
        # Update chat and user statistics
        chat.update_message_stats(is_user_message=False, tokens_used=token_usage.get("total_tokens", 0))
        user.increment_usage_stats(messages=2, tokens=token_usage.get("total_tokens", 0))
        
        await db.commit()
        await db.refresh(ai_message)
        
        # Stop typing indicator
        await manager.send_to_chat({
            "type": "ai_typing",
            "chat_id": chat.id,
            "is_typing": False
        }, chat.id)
        
        # Send AI response to all chat participants
        await manager.send_to_chat({
            "type": "ai_message",
            "message_id": ai_message.id,
            "content": ai_response,
            "timestamp": ai_message.created_at.isoformat(),
            "tokens_used": token_usage.get("total_tokens", 0),
            "processing_time": ai_response_data["processing_time"],
            "emotion_detected": emotion_data.get("primary_emotion") if emotion_data else None
        }, chat.id)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(
            f"WebSocket chat message processed in {processing_time:.2f}s",
            extra={
                "user_id": user.id,
                "chat_id": chat.id,
                "connection_id": connection_id,
                "processing_time": processing_time,
                "tokens_used": token_usage.get("total_tokens", 0)
            }
        )
        
        return {
            "type": "message_processed",
            "user_message_id": user_message.id,
            "ai_message_id": ai_message.id,
            "processing_time": processing_time
        }
    
    except Exception as e:
        logger.error(f"Failed to handle chat message: {str(e)}", exc_info=True)
        await db.rollback()
        
        # Stop typing indicator on error
        try:
            await manager.send_to_chat({
                "type": "ai_typing",
                "chat_id": chat.id,
                "is_typing": False
            }, chat.id)
        except:
            pass
        
        return {
            "type": "error",
            "error": "Failed to process chat message"
        }

async def handle_typing_indicator(
    message_data: Dict[str, Any],
    connection_id: str,
    user: User,
    chat: Chat,
    is_typing: bool
) -> Optional[Dict[str, Any]]:
    """Handle typing indicators"""
    
    try:
        # Broadcast typing status to other chat participants
        await manager.send_to_chat({
            "type": "user_typing",
            "user_id": user.id,
            "username": user.username,
            "chat_id": chat.id,
            "is_typing": is_typing,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, chat.id, exclude_connection=connection_id)
        
        return None  # No response needed
    
    except Exception as e:
        logger.error(f"Failed to handle typing indicator: {str(e)}")
        return {
            "type": "error",
            "error": "Failed to process typing indicator"
        }

async def handle_ping(message_data: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
    """Handle ping messages"""
    return {
        "type": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def handle_status_request(
    message_data: Dict[str, Any],
    connection_id: str,
    user: User,
    chat: Chat
) -> Dict[str, Any]:
    """Handle status requests"""
    
    return {
        "type": "status",
        "user_id": user.id,
        "chat_id": chat.id,
        "connection_id": connection_id,
        "chat_info": {
            "title": chat.title,
            "total_messages": chat.total_messages,
            "is_active": chat.is_active,
            "last_activity": chat.last_activity_at.isoformat() if chat.last_activity_at else None
        },
        "connection_info": {
            "connected_at": manager.connection_metadata.get(connection_id, {}).get("connected_at"),
            "total_connections": manager.get_connection_count(),
            "chat_connections": manager.get_chat_connection_count(chat.id)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.websocket("/chat/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """
    WebSocket endpoint for real-time chat
    """
    connection_id = f"{chat_id}_{datetime.now().timestamp()}"
    
    try:
        # Verify authentication
        user = await get_websocket_user(token, db)
        
        # Verify chat access
        chat_query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == user.id,
                Chat.is_deleted == False,
                Chat.is_active == True
            )
        )
        
        chat_result = await db.execute(chat_query)
        chat = chat_result.scalar_one_or_none()
        
        if not chat:
            await websocket.close(code=1008, reason="Chat not found or access denied")
            return
        
        # Connect to WebSocket
        await manager.connect(websocket, connection_id, user.id, chat_id)
        
        # Send connection confirmation
        await manager.send_personal_message({
            "type": "connected",
            "chat_id": chat_id,
            "user_id": user.id,
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, connection_id)
        
        # Update user activity
        user.update_last_activity()
        chat.update_activity()
        await db.commit()
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                
                try:
                    message_data = json.loads(data)
                except json.JSONDecodeError:
                    await manager.send_personal_message({
                        "type": "error",
                        "error": "Invalid JSON format"
                    }, connection_id)
                    continue
                
                # Process the message
                response = await process_websocket_message(
                    message_data, connection_id, user, chat, db, redis_client
                )
                
                # Send response if any
                if response:
                    await manager.send_personal_message(response, connection_id)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected normally: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}", exc_info=True)
            await manager.send_personal_message({
                "type": "error",
                "error": "Connection error occurred"
            }, connection_id)
    
    except Exception as e:
        logger.error(f"WebSocket connection failed: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        manager.disconnect(connection_id)

@router.get("/connections")
async def get_connection_info():
    """Get WebSocket connection information (admin only)"""
    return manager.get_connection_info()

@router.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    # current_user: User = Depends(get_current_admin_user)  # Would need admin check
):
    """Broadcast message to all connections (admin only)"""
    
    broadcast_message = {
        "type": "broadcast",
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await manager.broadcast(broadcast_message)
    
    return {
        "message": "Broadcast sent",
        "recipients": manager.get_connection_count()
    }

# Background task to clean up stale connections
async def cleanup_stale_connections():
    """Clean up stale WebSocket connections"""
    try:
        current_time = datetime.now(timezone.utc)
        stale_threshold = 300  # 5 minutes
        
        stale_connections = []
        for connection_id, metadata in manager.connection_metadata.items():
            last_activity = metadata.get("last_activity")
            if last_activity:
                time_diff = (current_time - last_activity).total_seconds()
                if time_diff > stale_threshold:
                    stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            logger.info(f"Cleaning up stale connection: {connection_id}")
            manager.disconnect(connection_id)
    
    except Exception as e:
        logger.error(f"Error cleaning up stale connections: {str(e)}")

# Export the connection manager for use in other modules
__all__ = ["router", "manager", "cleanup_stale_connections"]