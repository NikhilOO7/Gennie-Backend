"""
Chat Model - Conversation session management
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

from app.database import Base

class Chat(Base):
    """
    Chat model representing conversation sessions
    FIXED: Renamed 'metadata' to 'chat_metadata' to avoid SQLAlchemy conflict
    """
    __tablename__ = "chats"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Chat metadata - FIXED: renamed from metadata to chat_metadata
    title = Column(String(200), nullable=False, default="New Chat")
    description = Column(Text, nullable=True)
    
    # Chat configuration
    ai_model = Column(String(50), default="gpt-3.5-turbo", nullable=False)
    system_prompt = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7, nullable=False)
    max_tokens = Column(Integer, default=1000, nullable=False)
    
    # Chat status
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)
    
    # Chat statistics
    total_messages = Column(Integer, default=0, nullable=False)
    total_tokens_used = Column(Integer, default=0, nullable=False)
    total_user_messages = Column(Integer, default=0, nullable=False)
    total_ai_messages = Column(Integer, default=0, nullable=False)
    
    # Chat settings - FIXED: renamed from metadata to chat_metadata
    chat_chat_metadata = Column(JSON, default=dict, nullable=False)
    
    # Chat context and preferences
    context_window_size = Column(Integer, default=10, nullable=False)
    auto_title_generation = Column(Boolean, default=True, nullable=False)
    
    # Session tracking
    session_id = Column(String(36), default=lambda: str(uuid.uuid4()), nullable=False, unique=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), 
        onupdate=func.now(),
        nullable=True
    )
    
    # Relationships
    user = relationship("User", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
    
    # Indexes for better performance
    __table_args__ = (
        Index('idx_chat_user_created', 'user_id', 'created_at'),
        Index('idx_chat_user_active', 'user_id', 'is_active'),
        Index('idx_chat_session', 'session_id'),
        Index('idx_chat_archived', 'is_archived'),
        Index('idx_chat_deleted', 'is_deleted'),
        Index('idx_chat_favorite', 'is_favorite'),
        Index('idx_chat_last_message', 'last_message_at'),
    )
    
    def __init__(self, **kwargs):
        """Initialize chat with default metadata"""
        if 'chat_metadata' not in kwargs:
            kwargs['chat_metadata'] = {}
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<Chat(id={self.id}, user_id={self.user_id}, title='{self.title}', messages={self.total_messages})>"
    
    def __str__(self):
        return f"{self.title} ({self.total_messages} messages)"
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get chat metadata value"""
        return self.chat_metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set chat metadata value"""
        if self.chat_metadata is None:
            self.chat_metadata = {}
        
        # Create a new dict to trigger SQLAlchemy change detection
        updated_metadata = self.chat_metadata.copy()
        updated_metadata[key] = value
        self.chat_metadata = updated_metadata
    
    def update_message_count(self, sender_type: str) -> None:
        """Update message counters"""
        self.total_messages += 1
        if sender_type == "user":
            self.total_user_messages += 1
        elif sender_type == "assistant":
            self.total_ai_messages += 1
        
        self.last_message_at = datetime.now(timezone.utc)
    
    def add_tokens_used(self, tokens: int) -> None:
        """Add to total tokens used"""
        self.total_tokens_used += tokens
    
    def archive(self) -> None:
        """Archive this chat"""
        self.is_archived = True
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def unarchive(self) -> None:
        """Unarchive this chat"""
        self.is_archived = False
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self) -> None:
        """Soft delete this chat"""
        self.is_deleted = True
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def restore(self) -> None:
        """Restore soft deleted chat"""
        self.is_deleted = False
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def toggle_favorite(self) -> None:
        """Toggle favorite status"""
        self.is_favorite = not self.is_favorite
        self.updated_at = datetime.now(timezone.utc)
    
    def update_title(self, new_title: str) -> None:
        """Update chat title"""
        self.title = new_title[:200]  # Ensure max length
        self.updated_at = datetime.now(timezone.utc)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get chat summary"""
        return {
            "id": self.id,
            "title": self.title,
            "total_messages": self.total_messages,
            "total_tokens_used": self.total_tokens_used,
            "last_activity": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "is_favorite": self.is_favorite
        }
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert chat to dictionary"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "ai_model": self.ai_model,
            "system_prompt": self.system_prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "is_deleted": self.is_deleted,
            "is_favorite": self.is_favorite,
            "total_messages": self.total_messages,
            "total_tokens_used": self.total_tokens_used,
            "total_user_messages": self.total_user_messages,
            "total_ai_messages": self.total_ai_messages,
            "context_window_size": self.context_window_size,
            "auto_title_generation": self.auto_title_generation,
            "session_id": self.session_id,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_metadata:
            data["chat_metadata"] = self.chat_metadata
        
        return data
