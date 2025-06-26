from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta  # Fixed: Added proper datetime imports

from app.database import get_db
from app.models.chat import Chat
from app.models.message import Message
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/chats", tags=["chats"])

# Enhanced Pydantic models
class ChatCreate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ai_model: Optional[str] = "gpt-3.5-turbo"
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ai_model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_archived: Optional[bool] = None
    is_favorite: Optional[bool] = None

class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    description: Optional[str]
    ai_model: str
    temperature: float
    max_tokens: int
    is_archived: bool
    is_favorite: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    message_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    sender_type: str = "user"
    metadata: Optional[Dict[str, Any]] = None  # Keep API-friendly name

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    content: str
    sender_type: str
    timestamp: datetime
    emotion_data: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None  # Keep this for API compatibility
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_message(cls, message):
        """Create MessageResponse from Message model"""
        return cls(
            id=message.id,
            chat_id=message.chat_id,
            content=message.content,
            sender_type=message.sender_type,
            timestamp=message.timestamp,
            emotion_data=message.emotion_data,
            metadata=message.message_metadata  # Map the field correctly
        )

class ChatStats(BaseModel):
    total_chats: int
    total_messages: int
    active_chats: int
    average_messages_per_chat: float
    recent_activity: List[Dict[str, Any]]

# Chat management endpoints
@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    current_time = datetime.now(timezone.utc)  # Modern timezone-aware datetime
    
    db_chat = Chat(
        user_id=current_user.id,
        title=chat.title or f"New Conversation - {current_time.strftime('%Y-%m-%d %H:%M')}",
        description=chat.description,
        ai_model=chat.ai_model or "gpt-3.5-turbo",
        system_prompt=chat.system_prompt,
        temperature=str(chat.temperature or 0.7),
        max_tokens=chat.max_tokens or 1000,
        created_at=current_time,
        last_activity_at=current_time
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

@router.get("/", response_model=List[ChatResponse])
async def get_chats(
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for the current user"""
    query = db.query(Chat).filter(Chat.user_id == current_user.id)
    
    if not include_archived:
        query = query.filter(Chat.is_archived == False)
    
    chats = query.order_by(Chat.last_activity_at.desc()).offset(skip).limit(limit).all()
    
    # Add message count to each chat
    for chat in chats:
        chat.message_count = db.query(Message).filter(Message.chat_id == chat.id).count()
    
    return chats

@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat statistics for the current user"""
    total_chats = db.query(Chat).filter(Chat.user_id == current_user.id).count()
    total_messages = db.query(Message).join(Chat).filter(Chat.user_id == current_user.id).count()
    
    # Active chats (with activity in last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_chats = db.query(Chat).filter(
        Chat.user_id == current_user.id,
        Chat.last_activity_at >= week_ago
    ).count()
    
    # Average messages per chat
    avg_messages = total_messages / total_chats if total_chats > 0 else 0
    
    # Recent activity (last 5 chats with recent messages)
    recent_chats = db.query(Chat).filter(
        Chat.user_id == current_user.id
    ).order_by(Chat.last_activity_at.desc()).limit(5).all()
    
    recent_activity = []
    for chat in recent_chats:
        last_message = db.query(Message).filter(
            Message.chat_id == chat.id
        ).order_by(Message.timestamp.desc()).first()
        
        if last_message:
            recent_activity.append({
                "chat_id": chat.id,
                "chat_title": chat.title,
                "last_message": last_message.content[:100] + "..." if len(last_message.content) > 100 else last_message.content,
                "timestamp": last_message.timestamp.isoformat(),
                "sender_type": last_message.sender_type
            })
    
    return ChatStats(
        total_chats=total_chats,
        total_messages=total_messages,
        active_chats=active_chats,
        average_messages_per_chat=round(avg_messages, 2),
        recent_activity=recent_activity
    )

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific chat session"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Update last activity
    chat.last_activity_at = datetime.now(timezone.utc)
    db.commit()
    
    return chat

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a chat session"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Update fields
    update_data = chat_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "temperature":
            setattr(chat, field, str(value))
        else:
            setattr(chat, field, value)
    
    chat.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(chat)
    
    return chat

@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages for a specific chat"""
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.timestamp.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Convert to response format
    return [MessageResponse.from_message(msg) for msg in messages]

@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def create_message(
    chat_id: int,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new message in a chat"""
    # Verify chat exists and belongs to user
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    current_time = datetime.now(timezone.utc)
    
    db_message = Message(
        chat_id=chat_id,
        content=message.content,
        sender_type=message.sender_type,
        message_metadata=message.metadata,  # Map API field to DB field
        timestamp=current_time
    )
    
    db.add(db_message)
    
    # Update chat's last activity
    chat.last_activity_at = current_time
    chat.updated_at = current_time
    
    db.commit()
    db.refresh(db_message)
    
    return db_message

@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat session"""
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    db.delete(chat)
    db.commit()
    
    return {"message": "Chat deleted successfully", "deleted_at": datetime.now(timezone.utc).isoformat()}

@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(
    chat_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific message"""
    # Verify chat belongs to user and message exists
    chat = db.query(Chat).filter(
        Chat.id == chat_id,
        Chat.user_id == current_user.id
    ).first()
    
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.chat_id == chat_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.delete(message)
    db.commit()
    
    return {"message": "Message deleted successfully", "deleted_at": datetime.now(timezone.utc).isoformat()}