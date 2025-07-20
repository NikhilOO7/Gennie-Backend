"""
Message Model - Individual chat messages
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import enum
import hashlib

from app.database import Base

class MessageType(enum.Enum):
    """Message type enumeration"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"
    ERROR = "error"

class SenderType(enum.Enum):
    """Sender type enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(Base):
    """
    Message model representing individual chat messages
    Fixed: Updated field names to match existing code (message_metadata instead of metadata)
    """
    __tablename__ = "messages"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to chat
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    
    # Message content
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT, nullable=False)
    sender_type = Column(Enum(SenderType), nullable=False)
    
    # Message metadata - FIXED: Using message_metadata to match existing code
    message_metadata = Column(JSON, default=dict, nullable=False)
    
    # Processing information
    tokens_used = Column(Integer, default=0, nullable=False)
    processing_time = Column(Float, nullable=True)  # in seconds
    
    # Emotion analysis results
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    emotion_detected = Column(String(50), nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Message status
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_flagged = Column(Boolean, default=False, nullable=False)
    
    # Content hash for deduplication
    content_hash = Column(String(64), nullable=True, index=True)
    
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
    timestamp = Column(DateTime(timezone=True), nullable=True)  # For compatibility with existing code
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    
    # Indexes for better performance
    __table_args__ = (
        Index('idx_message_chat_created', 'chat_id', 'created_at'),
        Index('idx_message_sender_type', 'sender_type'),
        Index('idx_message_type', 'message_type'),
        Index('idx_message_hash', 'content_hash'),
        Index('idx_message_emotion', 'emotion_detected'),
        Index('idx_message_flagged', 'is_flagged'),
        Index('idx_message_deleted', 'is_deleted'),
    )
    
    def __init__(self, **kwargs):
        """Initialize message with content hash and metadata"""
        # Set timestamp for compatibility
        if 'timestamp' not in kwargs:
            kwargs['timestamp'] = datetime.now(timezone.utc)
        
        # Initialize metadata if not provided
        if 'message_metadata' not in kwargs:
            kwargs['message_metadata'] = {}
        
        super().__init__(**kwargs)
        
        # Generate content hash
        if self.content:
            self.generate_content_hash()
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, sender='{self.sender_type.value}', type='{self.message_type.value}')>"
    
    def __str__(self):
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"{self.sender_type.value}: {content_preview}"
    
    def generate_content_hash(self) -> None:
        """Generate hash of message content for deduplication"""
        if self.content:
            self.content_hash = hashlib.sha256(self.content.encode('utf-8')).hexdigest()
    
    def set_emotion_data(self, sentiment_score: float, emotion: str, confidence: float) -> None:
        """Set emotion analysis results"""
        self.sentiment_score = max(-1.0, min(1.0, sentiment_score))  # Clamp to [-1, 1]
        self.emotion_detected = emotion
        self.confidence_score = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.message_metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        if self.message_metadata is None:
            self.message_metadata = {}
        self.message_metadata[key] = value
    
    def mark_as_edited(self) -> None:
        """Mark message as edited"""
        self.is_edited = True
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_deleted(self) -> None:
        """Mark message as deleted (soft delete)"""
        self.is_deleted = True
        self.updated_at = datetime.now(timezone.utc)
    
    def flag(self, reason: str = None) -> None:
        """Flag message for review"""
        self.is_flagged = True
        if reason:
            self.set_metadata("flag_reason", reason)
    
    def unflag(self) -> None:
        """Remove flag from message"""
        self.is_flagged = False
        if "flag_reason" in self.message_metadata:
            del self.message_metadata["flag_reason"]
    
    @classmethod
    def create_user_message(cls, chat_id: int, content: str, **kwargs) -> "Message":
        """Factory method to create a user message"""
        return cls(
            chat_id=chat_id,
            content=content,
            sender_type=SenderType.USER,
            message_type=kwargs.get("message_type", MessageType.TEXT),
            **{k: v for k, v in kwargs.items() if k not in ["message_type"]}
        )
    
    @classmethod
    def create_assistant_message(cls, chat_id: int, content: str, **kwargs) -> "Message":
        """Factory method to create an assistant message"""
        return cls(
            chat_id=chat_id,
            content=content,
            sender_type=SenderType.ASSISTANT,
            message_type=kwargs.get("message_type", MessageType.TEXT),
            **{k: v for k, v in kwargs.items() if k not in ["message_type"]}
        )
    
    @classmethod
    def create_system_message(cls, chat_id: int, content: str, **kwargs) -> "Message":
        """Factory method to create a system message"""
        return cls(
            chat_id=chat_id,
            content=content,
            sender_type=SenderType.SYSTEM,
            message_type=MessageType.SYSTEM,
            **kwargs
        )
    
    def get_emotion_summary(self) -> Dict[str, Any]:
        """Get emotion analysis summary"""
        return {
            "sentiment_score": self.sentiment_score,
            "emotion_detected": self.emotion_detected,
            "confidence_score": self.confidence_score,
            "sentiment_label": self.get_sentiment_label(),
            "emotion_strength": self.get_emotion_strength()
        }
    
    def get_sentiment_label(self) -> str:
        """Get human-readable sentiment label"""
        if self.sentiment_score is None:
            return "unknown"
        elif self.sentiment_score > 0.1:
            return "positive"
        elif self.sentiment_score < -0.1:
            return "negative"
        else:
            return "neutral"
    
    def get_emotion_strength(self) -> str:
        """Get emotion strength label"""
        if self.confidence_score is None:
            return "unknown"
        elif self.confidence_score > 0.8:
            return "strong"
        elif self.confidence_score > 0.6:
            return "moderate"
        elif self.confidence_score > 0.4:
            return "weak"
        else:
            return "very_weak"
    
    def get_processing_info(self) -> Dict[str, Any]:
        """Get message processing information"""
        return {
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "content_hash": self.content_hash,
            "is_edited": self.is_edited,
            "edit_count": len(self.get_metadata("edit_history", [])),
            "character_count": len(self.content),
            "word_count": len(self.content.split()),
        }
    
    def to_dict(self, include_metadata: bool = False, include_emotion: bool = True) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = {
            "id": self.id,
            "chat_id": self.chat_id,
            "content": self.content,
            "message_type": self.message_type.value,
            "sender_type": self.sender_type.value,
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "is_edited": self.is_edited,
            "is_deleted": self.is_deleted,
            "is_flagged": self.is_flagged,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
        
        if include_emotion:
            data.update({
                "sentiment_score": self.sentiment_score,
                "emotion_detected": self.emotion_detected,
                "confidence_score": self.confidence_score,
                "emotion_summary": self.get_emotion_summary(),
            })
        
        if include_metadata:
            data.update({
                "message_metadata": self.message_metadata,
                "content_hash": self.content_hash,
                "processing_info": self.get_processing_info(),
            })
        
        return data
    
    def get_context_for_ai(self) -> Dict[str, Any]:
        """Get message data formatted for AI context"""
        return {
            "role": "user" if self.sender_type == SenderType.USER else "assistant",
            "content": self.content,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
            "emotion": self.emotion_detected,
            "sentiment": self.get_sentiment_label(),
        }
    
    def is_similar_to(self, other_message: "Message", threshold: float = 0.8) -> bool:
        """Check if this message is similar to another message"""
        if not other_message or not other_message.content:
            return False
        
        # Simple similarity check based on content hash
        if self.content_hash and other_message.content_hash:
            return self.content_hash == other_message.content_hash
        
        # More sophisticated similarity checking could be implemented here
        # using NLP techniques like cosine similarity of embeddings
        return False
    
    def get_word_count(self) -> int:
        """Get word count of message content"""
        return len(self.content.split()) if self.content else 0
    
    def get_character_count(self) -> int:
        """Get character count of message content"""
        return len(self.content) if self.content else 0
    
    def contains_keywords(self, keywords: List[str], case_sensitive: bool = False) -> bool:
        """Check if message contains specific keywords"""
        if not self.content or not keywords:
            return False
        
        content = self.content if case_sensitive else self.content.lower()
        keywords = keywords if case_sensitive else [kw.lower() for kw in keywords]
        
        return any(keyword in content for keyword in keywords)
    
    def extract_urls(self) -> List[str]:
        """Extract URLs from message content"""
        import re
        if not self.content:
            return []
        
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        return re.findall(url_pattern, self.content)
    
    def extract_mentions(self) -> List[str]:
        """Extract @mentions from message content"""
        import re
        if not self.content:
            return []
        
        mention_pattern = r'@(\w+)'
        return re.findall(mention_pattern, self.content)
    
    def extract_hashtags(self) -> List[str]:
        """Extract #hashtags from message content"""
        import re
        if not self.content:
            return []
        
        hashtag_pattern = r'#(\w+)'
        return re.findall(hashtag_pattern, self.content)