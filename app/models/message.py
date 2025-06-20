from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class SenderType(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageStatus(enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    
    # Message content
    content = Column(Text, nullable=False)
    sender_type = Column(Enum(SenderType), nullable=False)
    
    # Message metadata
    message_type = Column(String(20), default="text")  # "text", "image", "file", "system"
    status = Column(Enum(MessageStatus), default=MessageStatus.SENT)
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)  # For replies
    
    # AI-related data
    emotion_data = Column(JSON, nullable=True)  # Emotion analysis results
    sentiment_score = Column(String(10), nullable=True)  # Positive/Negative/Neutral
    confidence_score = Column(String(10), nullable=True)  # AI confidence in response
    
    # Processing metadata
    processing_time = Column(String(10), nullable=True)  # Time taken to generate response
    model_used = Column(String(50), nullable=True)  # AI model used for response
    tokens_used = Column(Integer, nullable=True)  # Number of tokens used
    
    # Additional metadata
    metadata = Column(JSON, nullable=True)  # Additional flexible metadata
    is_edited = Column(Boolean, default=False)
    edit_history = Column(JSON, nullable=True)  # History of edits
    
    # Flags
    is_favorite = Column(Boolean, default=False)
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(100), nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")
    replies = relationship("Message", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<Message(id={self.id}, chat_id={self.chat_id}, sender_type={self.sender_type})>"

# Emotion detection model (if you want to store emotion analysis separately)
class Emotion(Base):
    __tablename__ = "emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    
    # Primary emotion data
    emotion = Column(String(50), nullable=False)  # happy, sad, angry, etc.
    intensity = Column(String(10), nullable=False)  # 0.0 to 1.0
    confidence = Column(String(10), nullable=False)  # 0.0 to 1.0
    
    # Detailed emotion breakdown
    emotions_detailed = Column(JSON, nullable=True)  # Detailed emotion scores
    sentiment = Column(String(20), nullable=False)  # positive, negative, neutral
    sentiment_score = Column(String(10), nullable=False)  # -1.0 to 1.0
    
    # Analysis metadata
    analysis_method = Column(String(50), nullable=False)  # "vader", "textblob", "openai"
    analysis_version = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Emotion(id={self.id}, message_id={self.message_id}, emotion='{self.emotion}')>"