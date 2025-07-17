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
from app.services.gemini_service import gemini_service
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
        
        # Get metadata
        metadata = self.connection_metadata.get(connection_id, {})
        user_id = metadata.get("user_id")
        chat_id = metadata.get("chat_id")
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id] = [
                cid for cid in self.user_connections[user_id] if cid != connection_id
            ]
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from chat connections
        if chat_id and chat_id in self.chat_connections:
            self.chat_connections[chat_id] = [
                cid for cid in self.chat_connections[chat_id] if cid != connection_id
            ]
            if not self.chat_connections[chat_id]:
                del self.chat_connections[chat_id]
        
        # Remove metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
                # Update last activity
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]["last_activity"] = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {str(e)}")
                self.disconnect(connection_id)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: int):
        """Send message to all connections of a user"""
        if user_id in self.user_connections:
            tasks = []
            for connection_id in self.user_connections[user_id]:
                tasks.append(self.send_personal_message(message, connection_id))
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def send_to_chat(self, message: Dict[str, Any], chat_id: int):
        """Send message to all participants in a chat"""
        if chat_id in self.chat_connections:
            tasks = []
            for connection_id in self.chat_connections[chat_id]:
                tasks.append(self.send_personal_message(message, connection_id))
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connections"""
        tasks = []
        for connection_id in self.active_connections:
            tasks.append(self.send_personal_message(message, connection_id))
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_user_count(self) -> int:
        """Get number of unique connected users"""
        return len(self.user_connections)
    
    def get_chat_participants(self, chat_id: int) -> List[int]:
        """Get list of user IDs in a chat"""
        participants = set()
        if chat_id in self.chat_connections:
            for connection_id in self.chat_connections[chat_id]:
                metadata = self.connection_metadata.get(connection_id, {})
                user_id = metadata.get("user_id")
                if user_id:
                    participants.add(user_id)
        return list(participants)
    
    async def cleanup_stale_connections(self, timeout_seconds: int = 300):
        """Remove connections that haven't been active"""
        now = datetime.now(timezone.utc)
        stale_connections = []
        
        for connection_id, metadata in self.connection_metadata.items():
            last_activity = metadata.get("last_activity")
            if last_activity and (now - last_activity).total_seconds() > timeout_seconds:
                stale_connections.append(connection_id)
        
        for connection_id in stale_connections:
            logger.info(f"Cleaning up stale connection: {connection_id}")
            self.disconnect(connection_id)


# Create global connection manager
manager = ConnectionManager()


@router.websocket("/chat/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """WebSocket endpoint for real-time chat"""
    
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # Log the connection attempt
        logger.info(f"WebSocket connection attempt for chat {chat_id}")
        
        # Verify token and get user
        try:
            user = await get_user_from_token(token, db)
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return
        
        # Verify chat access
        result = await db.execute(
            select(Chat).where(and_(
                Chat.id == chat_id,
                Chat.user_id == user.id,
                Chat.is_active == True
            ))
        )
        chat = result.scalar_one_or_none()
        
        if not chat:
            logger.error(f"Chat {chat_id} not found or access denied for user {user.id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Chat not found")
            return
        
        # Connect websocket
        await manager.connect(websocket, connection_id, user.id, chat_id)
        logger.info(f"WebSocket connected successfully: {connection_id}")
        
        # Send connection confirmation
        await manager.send_personal_message({
            "type": "connection_established",
            "connection_id": connection_id,
            "user_id": user.id,
            "chat_id": chat_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, connection_id)
        
        # Notify other participants
        await manager.send_to_chat({
            "type": "user_joined",
            "user_id": user.id,
            "username": user.username,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, chat_id)
        
        # Main message loop
        while True:
            # Receive message
            message_data = await websocket.receive_json()
            
            # Process message
            response = await process_websocket_message(
                message_data,
                connection_id,
                user,
                chat,
                db,
                redis_client
            )
            
            # Send response if any
            if response:
                await manager.send_personal_message(response, connection_id)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for connection {connection_id}: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=str(e)[:120])
        except:
            pass
    finally:
        # Clean up connection
        if connection_id:
            manager.disconnect(connection_id)
        
        # Notify other participants if user was authenticated
        if user and chat_id:
            try:
                await manager.send_to_chat({
                    "type": "user_left",
                    "user_id": user.id,
                    "username": user.username,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, chat_id)
            except:
                pass

async def get_user_from_token(token: str, db: AsyncSession) -> User:
    """Get user from JWT token"""
    payload = verify_token(token)
    
    # Get user ID from payload
    user_id_str = payload.get("sub")
    
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    # Convert string ID to integer
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token: invalid user ID format")
    
    # Query with integer user_id
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    
    return user

async def handle_voice_stream_start(message_data, connection_id, user, chat, db):
    """Handle voice stream start"""
    websocket = manager.active_connections.get(connection_id)
    if not websocket:
        return {
            "type": "error",
            "error": "WebSocket connection not found",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    # Create voice session
    user_id = str(user.id)
    session_id = str(uuid.uuid4())
    
    # Store in manager (add voice_sessions dict if not exists)
    if not hasattr(manager, 'voice_sessions'):
        manager.voice_sessions = {}
    
    manager.voice_sessions[user_id] = {
        "session_id": session_id,
        "connection_id": connection_id,
        "language_code": message_data.get("language_code", "en-US"),
        "interim_results": message_data.get("interim_results", True),
        "sample_rate": message_data.get("sample_rate", 16000),
        "started_at": datetime.now(timezone.utc)
    }
    
    return {
        "type": "voice_stream_started",
        "session_id": session_id,
        "config": {
            "language_code": message_data.get("language_code", "en-US"),
            "sample_rate": message_data.get("sample_rate", 16000),
            "interim_results": message_data.get("interim_results", True)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

async def handle_voice_stream_end(message_data, connection_id, user, chat, db):
    """Handle voice stream end"""
    user_id = str(user.id)
    
    if hasattr(manager, 'voice_sessions') and user_id in manager.voice_sessions:
        session = manager.voice_sessions.pop(user_id, None)
        return {
            "type": "voice_stream_ended",
            "session_id": session.get("session_id") if session else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    return {
        "type": "error",
        "error": "No active voice session found",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


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
        elif message_type == "voice_stream_start":  # ADD THIS
            return await handle_voice_stream_start(message_data, connection_id, user, chat, db)
        elif message_type == "voice_stream_end":    # ADD THIS
            return await handle_voice_stream_end(message_data, connection_id, user, chat, db)
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
    
    try:
        # Detect if this is a voice message
        is_voice_message = message_data.get("metadata", {}).get("source") == "voice"
        request_voice_response = message_data.get("request_voice_response", is_voice_message)
        
        start_time = datetime.now(timezone.utc)
        
        # Store chat_id and user_id to avoid lazy loading issues
        chat_id = chat.id
        user_id = user.id
        chat_ai_model = chat.ai_model
        chat_temperature = chat.temperature
        chat_max_tokens = chat.max_tokens
        chat_system_prompt = chat.system_prompt
        
        # If chat has a topic, include it in the AI context (FIXED)
        system_context = ""
        if chat.related_topic:
            # Check if topics_service is imported, if not, skip this part
            try:
                from app.services.topics_service import topics_service
                topic_info = topics_service.get_topic_info(chat.related_topic)
                if topic_info:
                    system_context = f"This conversation is related to {topic_info['name']}. "
            except ImportError:
                # Topics service not available, skip
                pass

        # Send typing indicator
        await manager.send_to_chat({
            "type": "ai_typing",
            "chat_id": chat_id,
            "is_typing": True
        }, chat_id)
        
        # Create user message
        user_message = Message(
            chat_id=chat_id,
            content=content,
            message_type=MessageType.TEXT,
            sender_type=SenderType.USER
        )
        db.add(user_message)
        await db.flush()  # Get the ID without committing
        
        # Broadcast user message to all chat participants
        await manager.send_to_chat({
            "type": "user_message",
            "message_id": user_message.id,
            "user_id": user_id,
            "content": content,
            "timestamp": user_message.created_at.isoformat()
        }, chat_id)
        
        # Emotion detection
        emotion_data = None
        if message_data.get("detect_emotion", True):
            emotion_result = await emotion_service.analyze_emotion(content)
            if emotion_result["success"]:
                emotion_data = emotion_result
        
        # Get RAG context
        context_messages = []
        user_preferences = {}
        try:
            rag_context = await rag_service.get_context_for_query(
                query=content,
                user_id=user_id,
                chat_id=chat_id,
                db=db,
                redis_client=redis_client
            )
            
            if rag_context:
                context_messages = rag_context.get("context_messages", [])
                user_preferences = rag_context.get("user_preferences", {})
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {str(e)}")
        
        # Prepare messages for Gemini
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
        
        # Get AI response using Gemini
        ai_response_data = await gemini_service.generate_chat_response(
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
                "user_preferences_applied": bool(user_preferences),
                "voice_requested": request_voice_response
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
        
        # After getting AI response, determine if we need TTS
        needs_voice_response = request_voice_response or is_voice_message
        
        # Prepare response data
        response_data = {
            "type": "ai_message",
            "message_id": ai_message.id,
            "content": ai_response,
            "timestamp": ai_message.created_at.isoformat(),
            "emotion_detected": emotion_data.get("primary_emotion") if emotion_data else None,
            "confidence_score": emotion_data.get("confidence_score") if emotion_data else None,
            "tokens_used": token_usage.get("total_tokens", 0),
            "processing_time": ai_response_data.get("processing_time", 0.0),
            "message_metadata": {
                "model": chat_ai_model,
                "context_used": bool(context_messages),
                "personalization_applied": bool(user_preferences)
            },
            "has_voice": needs_voice_response,
            "voice_requested": needs_voice_response
        }
        
        # Generate voice response if needed
        if needs_voice_response:
            try:
                # Import TTS handler from websocket_tts
                from app.routers.websocket_tts import generate_and_send_audio
                
                # Generate audio asynchronously
                asyncio.create_task(
                    generate_and_send_audio(
                        text=ai_response,
                        message_id=ai_message.id,
                        chat_id=chat_id,
                        connection_id=connection_id,
                        manager=manager,
                        redis_client=redis_client,
                        voice_settings = chat.get_voice_settings()
                    )
                )
                
                # Add voice generation status
                response_data["voice_status"] = "generating"
                
            except Exception as e:
                logger.error(f"Failed to initiate TTS: {str(e)}")
                response_data["voice_error"] = str(e)
        
        # Send the text response immediately
        await manager.send_to_chat(response_data, chat_id)
        
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(
            f"WebSocket chat message processed in {processing_time:.2f}s",
            extra={
                "user_id": user_id,
                "chat_id": chat_id,
                "connection_id": connection_id,
                "processing_time": processing_time,
                "tokens_used": token_usage.get("total_tokens", 0),
                "is_voice_message": is_voice_message,
                "voice_response_requested": needs_voice_response
            }
        )
        
        return {
            "type": "message_processed",
            "user_message_id": user_message.id,
            "ai_message_id": ai_message.id,
            "processing_time": processing_time,
            "voice_requested": needs_voice_response
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
) -> None:
    """Handle typing indicator"""
    
    # Broadcast to other participants
    await manager.send_to_chat({
        "type": "typing_indicator",
        "user_id": user.id,
        "username": user.username,
        "is_typing": is_typing,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, chat.id)
    
    return None


async def handle_ping(message_data: Dict[str, Any], connection_id: str) -> Dict[str, Any]:
    """Handle ping message"""
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
    """Handle status request"""
    
    participants = manager.get_chat_participants(chat.id)
    
    return {
        "type": "status",
        "chat_id": chat.id,
        "participants": participants,
        "connection_count": len(manager.chat_connections.get(chat.id, [])),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Background task to clean up stale connections
async def cleanup_task():
    """Periodic cleanup of stale connections"""
    while True:
        try:
            await asyncio.sleep(60)  # Run every minute
            await manager.cleanup_stale_connections()
        except Exception as e:
            logger.error(f"Cleanup task error: {str(e)}")


# Start cleanup task when module loads
asyncio.create_task(cleanup_task())

# Export router and manager
__all__ = ["router", "manager"]