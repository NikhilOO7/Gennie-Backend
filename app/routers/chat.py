from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

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

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class ChatResponse(BaseModel):
    id: int
    user_id: int
    title: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    message_count: Optional[int] = 0
    last_message_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MessageCreate(BaseModel):
    content: str
    sender_type: str = "user"
    metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    content: str
    sender_type: str
    timestamp: datetime
    emotion_data: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True

class ChatStats(BaseModel):
    total_chats: int
    total_messages: int
    active_chats: int
    average_messages_per_chat: float

# Chat management endpoints
@router.post("/", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    db_chat = Chat(
        user_id=current_user.id,
        title=chat.title or "New Conversation",
        description=chat.description
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

@router.get("/", response_model=List[ChatResponse])
async def get_user_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all chat sessions for current user"""
    query = db.query(Chat).filter(Chat.user_id == current_user.id)
    
    if search:
        query = query.filter(Chat.title.ilike(f"%{search}%"))
    
    chats = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit).all()
    
    # Add message count and last message time
    for chat in chats:
        message_count = db.query(Message).filter(Message.chat_id == chat.id).count()
        last_message = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.timestamp.desc()).first()
        
        chat.message_count = message_count
        chat.last_message_at = last_message.timestamp if last_message else None
    
    return chats

@router.get("/stats", response_model=ChatStats)
async def get_chat_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat statistics for current user"""
    total_chats = db.query(Chat).filter(Chat.user_id == current_user.id).count()
    total_messages = db.query(Message).join(Chat).filter(Chat.user_id == current_user.id).count()
    
    # Active chats (chats with messages in last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    active_chats = db.query(Chat).filter(
        Chat.user_id == current_user.id,
        Chat.updated_at >= week_ago
    ).count()
    
    avg_messages = total_messages / total_chats if total_chats > 0 else 0
    
    return ChatStats(
        total_chats=total_chats,
        total_messages=total_messages,
        active_chats=active_chats,
        average_messages_per_chat=avg_messages
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
    
    # Add message count
    message_count = db.query(Message).filter(Message.chat_id == chat.id).count()
    chat.message_count = message_count
    
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
    
    for field, value in chat_update.dict(exclude_unset=True).items():
        setattr(chat, field, value)
    
    chat.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(chat)
    
    return chat

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
    return {"message": "Chat deleted successfully"}

# Message endpoints
@router.get("/{chat_id}/messages", response_model=List[MessageResponse])
async def get_chat_messages(
    chat_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
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
    
    return messages

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
    
    db_message = Message(
        chat_id=chat_id,
        content=message.content,
        sender_type=message.sender_type,
        metadata=message.metadata
    )
    
    db.add(db_message)
    
    # Update chat's last activity
    chat.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_message)
    
    return db_message

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
    
    return {"message": "Message deleted successfully"}