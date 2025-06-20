from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, get_redis
from app.services.openai_service import openai_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service
from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from typing import Dict, List, Optional
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Dict[str, WebSocket]] = {}
        self.user_sessions: Dict[int, int] = {}  # websocket_id -> user_id
    
    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        
        connection_id = id(websocket)
        self.active_connections[chat_id][connection_id] = websocket
        self.user_sessions[connection_id] = user_id
        
        logger.info(f"WebSocket connected for chat {chat_id}, user {user_id}")
        
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "chat_id": chat_id,
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    def disconnect(self, websocket: WebSocket, chat_id: int):
        connection_id = id(websocket)
        
        if chat_id in self.active_connections:
            if connection_id in self.active_connections[chat_id]:
                del self.active_connections[chat_id][connection_id]
                
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
        
        if connection_id in self.user_sessions:
            user_id = self.user_sessions[connection_id]
            del self.user_sessions[connection_id]
            logger.info(f"WebSocket disconnected for chat {chat_id}, user {user_id}")
    
    async def send_personal_message(self, message: dict, chat_id: int, exclude_connection: Optional[WebSocket] = None):
        if chat_id in self.active_connections:
            disconnected_connections = []
            
            for connection_id, websocket in self.active_connections[chat_id].items():
                if exclude_connection and websocket == exclude_connection:
                    continue
                    
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending message to connection {connection_id}: {e}")
                    disconnected_connections.append(connection_id)
            
            # Clean up disconnected connections
            for connection_id in disconnected_connections:
                if connection_id in self.active_connections[chat_id]:
                    del self.active_connections[chat_id][connection_id]
                if connection_id in self.user_sessions:
                    del self.user_sessions[connection_id]
    
    async def broadcast_to_chat(self, message: dict, chat_id: int):
        await self.send_personal_message(message, chat_id)
    
    def get_chat_connections_count(self, chat_id: int) -> int:
        return len(self.active_connections.get(chat_id, {}))
    
    def get_total_connections(self) -> int:
        return sum(len(connections) for connections in self.active_connections.values())

manager = ConnectionManager()

async def get_websocket_user(websocket: WebSocket, token: str, db: Session) -> User:
    """Authenticate user from WebSocket token"""
    try:
        import jwt
        from app.config import settings
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if user_id is None:
            await websocket.close(code=1008, reason="Invalid token")
            return None
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            await websocket.close(code=1008, reason="User not found")
            return None
            
        return user
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return None

@router.websocket("/ws/chat/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str,
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    # Authenticate user
    user = await get_websocket_user(websocket, token, db)
    if not user:
        return
    
    # Verify chat belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == user.id
    ).first()
    
    if not chat:
        await websocket.close(code=1008, reason="Chat not found or access denied")
        return
    
    # Connect to chat
    await manager.connect(websocket, chat_id, user.id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message_type = message_data.get("type")
            
            if message_type == "chat_message":
                await handle_chat_message(websocket, chat_id, message_data, user, db, redis)
            elif message_type == "typing_start":
                await handle_typing_status(chat_id, user.id, True)
            elif message_type == "typing_stop":
                await handle_typing_status(chat_id, user.id, False)
            elif message_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, chat_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, chat_id)

async def handle_chat_message(websocket: WebSocket, chat_id: int, message_data: dict, user: User, db: Session, redis):
    """Handle incoming chat message"""
    try:
        user_message = message_data.get("message", "")
        if not user_message.strip():
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Empty message not allowed"
            }))
            return
        
        # Send acknowledgment
        await websocket.send_text(json.dumps({
            "type": "message_received",
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Analyze emotion
        emotion_data = await emotion_service.analyze_emotion(user_message)
        
        # Save user message
        user_msg = Message(
            chat_id=chat_id,
            content=user_message,
            sender_type="user",
            emotion_data=emotion_data
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)
        
        # Broadcast user message to other connections
        await manager.send_personal_message({
            "type": "user_message",
            "message_id": user_msg.id,
            "content": user_message,
            "emotion_data": emotion_data,
            "timestamp": user_msg.timestamp.isoformat(),
            "user_id": user.id
        }, chat_id, exclude_connection=websocket)
        
        # Show AI typing indicator
        await manager.broadcast_to_chat({
            "type": "ai_typing",
            "status": True
        }, chat_id)
        
        # Get conversation context
        context = await get_conversation_context(db, chat_id, 10)
        
        # Get personalization data
        personalization_data = await personalization_service.get_personalized_context(db, user.id)
        
        # Generate AI response
        ai_response = await openai_service.generate_response(
            message=user_message,
            context=context,
            emotion_data=emotion_data,
            personalization=personalization_data
        )
        
        # Save AI response
        ai_msg = Message(
            chat_id=chat_id,
            content=ai_response,
            sender_type="assistant",
            emotion_data={"response_to": emotion_data}
        )
        db.add(ai_msg)
        
        # Update chat timestamp
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        chat.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ai_msg)
        
        # Stop AI typing indicator and send response
        await manager.broadcast_to_chat({
            "type": "ai_typing",
            "status": False
        }, chat_id)
        
        await manager.broadcast_to_chat({
            "type": "ai_response",
            "message_id": ai_msg.id,
            "content": ai_response,
            "timestamp": ai_msg.timestamp.isoformat(),
            "emotion_data": ai_msg.emotion_data
        }, chat_id)
        
        # Learn from conversation (background task)
        asyncio.create_task(
            personalization_service.learn_from_conversation(
                db, user.id, user_message, emotion_data
            )
        )
        
    except Exception as e:
        logger.error(f"Error handling chat message: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process message"
        }))

async def handle_typing_status(chat_id: int, user_id: int, is_typing: bool):
    """Handle typing status updates"""
    await manager.broadcast_to_chat({
        "type": "user_typing",
        "user_id": user_id,
        "is_typing": is_typing,
        "timestamp": datetime.utcnow().isoformat()
    }, chat_id)

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
    for msg in reversed(messages):
        context.append({
            "role": "user" if msg.sender_type == "user" else "assistant",
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        })
    
    return context

# WebSocket status endpoint
@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "total_connections": manager.get_total_connections(),
        "active_chats": len(manager.active_connections),
        "status": "operational"
    }