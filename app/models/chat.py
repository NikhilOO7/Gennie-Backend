"""
Chat Model - Conversation session management
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
import json

from app.database import Base
from app.models.message import Message, SenderType

class Chat(Base):
    """
    Chat model representing conversation sessions
    FIXED: Renamed column to 'chat_metadata' to match code expectations
    """
    __tablename__ = "chats"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Chat metadata
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
    
    # Chat settings - FIXED: Changed from chat_chat_metadata to chat_metadata
    chat_metadata = Column(JSON, default=dict, nullable=False)
    
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
    
    def update_activity(self) -> None:
        """Update last activity timestamp"""
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
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get detailed conversation summary and statistics"""
        return {
            "chat_id": self.id,
            "title": self.title,
            "total_messages": self.total_messages,
            "user_messages": self.total_user_messages,
            "ai_messages": self.total_ai_messages,
            "total_tokens_used": self.total_tokens_used,
            "ai_model": self.ai_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "session_duration": self._calculate_session_duration(),
            "is_active": self.is_active,
            "is_archived": self.is_archived,
            "is_favorite": self.is_favorite,
            "context_window_size": self.context_window_size,
            "auto_title_generation": self.auto_title_generation
        }
    
    def _calculate_session_duration(self) -> Optional[float]:
        """Calculate session duration in minutes"""
        if not self.created_at or not self.last_message_at:
            return None
        
        duration = self.last_message_at - self.created_at
        return duration.total_seconds() / 60  # Return in minutes
    
    def export_conversation(self, format: str = "json") -> Dict[str, Any]:
        """Export conversation in various formats"""
        try:
            if format.lower() not in ["json", "markdown", "txt"]:
                return {"error": "Unsupported export format. Use 'json', 'markdown', or 'txt'"}
            
            # Get basic chat info
            export_data = {
                "chat_info": {
                    "id": self.id,
                    "title": self.title,
                    "description": self.description,
                    "ai_model": self.ai_model,
                    "total_messages": self.total_messages,
                    "total_tokens_used": self.total_tokens_used,
                    "created_at": self.created_at.isoformat() if self.created_at else None,
                    "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None
                },
                "messages": []
            }
            
            # Add messages if available
            if hasattr(self, 'messages') and self.messages:
                for message in self.messages:
                    if not message.is_deleted:
                        message_data = {
                            "id": message.id,
                            "content": message.content,
                            "sender_type": message.sender_type.value if hasattr(message.sender_type, 'value') else str(message.sender_type),
                            "message_type": message.message_type.value if hasattr(message.message_type, 'value') else str(message.message_type),
                            "timestamp": message.created_at.isoformat() if message.created_at else None,
                            "tokens_used": message.tokens_used,
                            "processing_time": message.processing_time,
                            "emotion_detected": message.emotion_detected,
                            "sentiment_score": message.sentiment_score
                        }
                        export_data["messages"].append(message_data)
            
            if format.lower() == "json":
                return {
                    "success": True,
                    "format": "json",
                    "data": export_data,
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }
            
            elif format.lower() == "markdown":
                markdown_content = self._format_as_markdown(export_data)
                return {
                    "success": True,
                    "format": "markdown",
                    "content": markdown_content,
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }
            
            elif format.lower() == "txt":
                txt_content = self._format_as_text(export_data)
                return {
                    "success": True,
                    "format": "txt",
                    "content": txt_content,
                    "exported_at": datetime.now(timezone.utc).isoformat()
                }
        
        except Exception as e:
            return {"error": f"Export failed: {str(e)}"}
    
    def _format_as_markdown(self, data: Dict[str, Any]) -> str:
        """Format conversation as Markdown"""
        markdown = f"# {data['chat_info']['title']}\n\n"
        markdown += f"**Chat ID:** {data['chat_info']['id']}\n"
        markdown += f"**AI Model:** {data['chat_info']['ai_model']}\n"
        markdown += f"**Created:** {data['chat_info']['created_at']}\n"
        markdown += f"**Total Messages:** {data['chat_info']['total_messages']}\n"
        markdown += f"**Total Tokens:** {data['chat_info']['total_tokens_used']}\n\n"
        
        if data['chat_info']['description']:
            markdown += f"**Description:** {data['chat_info']['description']}\n\n"
        
        markdown += "## Conversation\n\n"
        
        for message in data['messages']:
            sender = "🤖 **Assistant**" if message['sender_type'] == "assistant" else "👤 **User**"
            markdown += f"### {sender}\n"
            markdown += f"*{message['timestamp']}*\n\n"
            markdown += f"{message['content']}\n\n"
            
            if message['emotion_detected']:
                markdown += f"*Emotion: {message['emotion_detected']}*\n\n"
            
            markdown += "---\n\n"
        
        return markdown
    
    def _format_as_text(self, data: Dict[str, Any]) -> str:
        """Format conversation as plain text"""
        text = f"Chat: {data['chat_info']['title']}\n"
        text += f"=" * len(f"Chat: {data['chat_info']['title']}") + "\n\n"
        text += f"Chat ID: {data['chat_info']['id']}\n"
        text += f"AI Model: {data['chat_info']['ai_model']}\n"
        text += f"Created: {data['chat_info']['created_at']}\n"
        text += f"Total Messages: {data['chat_info']['total_messages']}\n"
        text += f"Total Tokens: {data['chat_info']['total_tokens_used']}\n\n"
        
        if data['chat_info']['description']:
            text += f"Description: {data['chat_info']['description']}\n\n"
        
        text += "CONVERSATION:\n"
        text += "-" * 50 + "\n\n"
        
        for message in data['messages']:
            sender = "ASSISTANT" if message['sender_type'] == "assistant" else "USER"
            text += f"[{sender}] {message['timestamp']}\n"
            text += f"{message['content']}\n"
            
            if message['emotion_detected']:
                text += f"(Emotion: {message['emotion_detected']})\n"
            
            text += "\n" + "-" * 30 + "\n\n"
        
        return text
    
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
    
    def get_context_messages(self, limit: int = None) -> List["Message"]:
        """Get messages for context (most recent messages)"""
        if not hasattr(self, 'messages') or not self.messages:
            return []
        
        # Filter out deleted messages
        valid_messages = [msg for msg in self.messages if not msg.is_deleted]
        
        # Sort by creation time (oldest first)
        valid_messages.sort(key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc))
        
        # Apply limit if specified
        if limit and limit > 0:
            return valid_messages[-limit:]
        
        # Default to context_window_size
        return valid_messages[-self.context_window_size:]

    def can_add_message(self) -> bool:
        """Check if chat can accept new messages"""
        return self.is_active and not self.is_deleted and not self.is_archived

    def update_message_stats(self, is_user_message: bool, tokens_used: int = 0):
        """Update message statistics"""
        self.total_messages += 1
        if is_user_message:
            self.total_user_messages += 1
        else:
            self.total_ai_messages += 1
        
        if tokens_used > 0:
            self.total_tokens_used += tokens_used
        
        self.last_message_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def auto_generate_title(self):
        """Auto-generate title if it's still the default"""
        if self.title == "New Chat" and self.auto_title_generation:
            # This would typically call a service to generate a title
            # For now, we'll just use a simple approach
            if hasattr(self, 'messages') and self.messages:
                first_user_message = next(
                    (msg for msg in self.messages if msg.sender_type == SenderType.USER), 
                    None
                )
                if first_user_message and first_user_message.content:
                    # Take first 50 chars of first message as title
                    self.title = first_user_message.content[:50]
                    if len(first_user_message.content) > 50:
                        self.title += "..."

    @property
    def last_activity_at(self):
        """Get last activity timestamp (returns updated_at or created_at)"""
        return self.updated_at or self.created_at
    
    def update_activity(self):
        """Update the last activity timestamp"""
        from datetime import datetime, timezone
        self.updated_at = datetime.now(timezone.utc)
