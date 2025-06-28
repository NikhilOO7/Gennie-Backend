"""
WebSocket Router - Real-time chat functionality
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Dict, List, Optional, Any
import json
import logging
from datetime import datetime, timezone
import asyncio
import uuid

from app.database import get_db, get_redis
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, MessageType, SenderType
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.rag_service import rag_service
from app.routers.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, List[str]] = {}
        self.chat_connections: Dict[int, List[str]] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_id: int, chat_id: int):
        """Accept and register a new connection"""
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
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc)
        }
        
        logger.info(f"WebSocket connected: {connection_id} (user: {user_id}, chat: {chat_id})")
    
    def disconnect(self, connection_id: str):
        """Remove a connection"""
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
        """Get number of connections in a chat"""
        return len(self.chat_connections.get(chat_id, []))
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get information about all connections"""
        return {
            "total_connections": self.get_connection_count(),
            "user_connections": {
                user_id: len(connections) 
                for user_id, connections in self.user_connections.items()
            },
            "chat_connections": {
                chat_id: len(connections) 
                for chat_id, connections in self.chat_connections.items()
            },
            "connection_details": self.connection_metadata
        }

# Global connection manager
manager = ConnectionManager()

async def get_websocket_user(token: str, db: AsyncSession) -> User:
    """Verify WebSocket token and get user"""
    try:
        payload = verify_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    user_id_str = payload.get("sub")
    
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    # Convert string subject back to integer
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
    """Handle chat message via WebSocket - FIXED VERSION"""
    
    content = message_data.get("content", "").strip()
    
    if not content:
        return {
            "type": "error",
            "error": "Message content cannot be empty"
        }
    
    try:
        start_time = datetime.now(timezone.utc)
        
        # Store chat_id and user_id to avoid lazy loading issues
        chat_id = chat.id
        user_id = user.id
        chat_ai_model = chat.ai_model
        chat_temperature = chat.temperature
        chat_max_tokens = chat.max_tokens
        chat_system_prompt = chat.system_prompt
        
        # Create user message
        user_message = Message(
            chat_id=chat_id,
            content=content,
            message_type=MessageType.TEXT,
            sender_type=SenderType.USER,
            message_metadata={
                "source": "websocket",
                "connection_id": connection_id
            }
        )
        
        db.add(user_message)
        await db.flush()  # Get the ID without committing
        
        # Send immediate acknowledgment
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
            "user_id": user_id,
            "content": content,
            "timestamp": user_message.created_at.isoformat()
        }, chat_id, exclude_connection=connection_id)
        
        # Show AI typing indicator
        await manager.send_to_chat({
            "type": "ai_typing",
            "chat_id": chat_id,
            "is_typing": True
        }, chat_id)
        
        # Analyze emotion
        emotion_data = None
        try:
            emotion_result = await emotion_service.analyze_emotion(
                content, 
                context={"user_id": user_id, "chat_id": chat_id}
            )
            if emotion_result and emotion_result.get("success"):
                emotion_data = emotion_result
                user_message.emotion_detected = emotion_data.get("primary_emotion")
                user_message.sentiment_score = emotion_data.get("sentiment_score", 0.0)
                user_message.confidence_score = emotion_data.get("confidence_score", 0.0)
        except Exception as e:
            logger.warning(f"Emotion analysis failed: {str(e)}")
        
        # Get conversation context using RAG
        context_messages = []
        user_preferences = None
        
        try:
            # Use RAG to get relevant context
            rag_context = await rag_service.get_context_for_chat(
                chat_id=chat_id,
                user_id=user_id,
                current_message=content,
                db=db,
                redis_client=redis_client
            )
            
            if rag_context:
                context_messages = rag_context.get("context_messages", [])
                user_preferences = rag_context.get("user_preferences", {})
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {str(e)}")
        
        # Prepare messages for OpenAI
        messages = []
        
        # Add system prompt if available
        if chat_system_prompt:
            messages.append({"role": "system", "content": chat_system_prompt})
        
        # Add context messages
        for ctx_msg in context_messages[-10:]:  # Limit context
            role = "user" if ctx_msg.get("sender_type") == "USER" else "assistant"
            messages.append({
                "role": role,
                "content": ctx_msg.get("content", "")
            })
        
        # Add current message
        messages.append({"role": "user", "content": content})
        
        # Get AI response
        ai_response_data = await openai_service.generate_chat_response(
            messages=messages,
            model=chat_ai_model,
            temperature=chat_temperature,
            max_tokens=chat_max_tokens,
            user_id=str(user_id)
        )
        
        if not ai_response_data["success"]:
            raise Exception(ai_response_data.get("error", "Failed to get AI response"))
        
        ai_response = ai_response_data["response"]
        token_usage = ai_response_data.get("tokens_used", {})
        
        # Create AI message
        ai_message = Message(
            chat_id=chat_id,
            content=ai_response,
            message_type=MessageType.TEXT,
            sender_type=SenderType.ASSISTANT,
            tokens_used=token_usage.get("total_tokens", 0),
            processing_time=ai_response_data.get("processing_time", 0.0),
            message_metadata={
                "ai_model": chat_ai_model,
                "websocket_response": True,
                "user_preferences_applied": bool(user_preferences)
            }
        )
        
        db.add(ai_message)
        
        # Update chat statistics (avoid lazy loading by updating directly)
        chat.total_messages += 2
        chat.total_user_messages += 1
        chat.total_ai_messages += 1
        chat.total_tokens_used += token_usage.get("total_tokens", 0)
        chat.last_message_at = datetime.now(timezone.utc)
        chat.updated_at = datetime.now(timezone.utc)
        
        # Update user statistics
        user.total_messages += 2
        user.total_tokens_used += token_usage.get("total_tokens", 0)
        
        # Commit all changes
        await db.commit()
        
        # Refresh to get updated values
        await db.refresh(user_message)
        await db.refresh(ai_message)
        
        # Stop typing indicator
        await manager.send_to_chat({
            "type": "ai_typing",
            "chat_id": chat_id,
            "is_typing": False
        }, chat_id)
        
        # Send AI response to all chat participants
        await manager.send_to_chat({
            "type": "ai_message",
            "message_id": ai_message.id,
            "content": ai_response,
            "timestamp": ai_message.created_at.isoformat(),
            "tokens_used": token_usage.get("total_tokens", 0),
            "processing_time": ai_response_data.get("processing_time", 0.0),
            "emotion_detected": emotion_data.get("primary_emotion") if emotion_data else None
        }, chat_id)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(
            f"WebSocket chat message processed in {processing_time:.2f}s",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
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
                "chat_id": chat_id,
                "is_typing": False
            }, chat_id)
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
            "last_activity": chat.updated_at.isoformat() if chat.updated_at else None
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
    FIXED: Proper async session handling
    """
    connection_id = f"{chat_id}_{datetime.now().timestamp()}"
    
    try:
        # Verify authentication
        user = await get_websocket_user(token, db)
        
        # Verify chat access with proper loading
        chat_query = select(Chat).options(
            selectinload(Chat.user)  # Eagerly load relationships
        ).where(
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
        
        # Update activity (within session context)
        user.last_activity = datetime.now(timezone.utc)
        chat.updated_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Refresh objects to ensure they're bound to the session
        await db.refresh(user)
        await db.refresh(chat)
        
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
                
                # Process the message with fresh session
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