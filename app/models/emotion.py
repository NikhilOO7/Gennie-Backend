"""Emotion model for emotion analysis."""

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base

class Emotion(Base):
    __tablename__ = "emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False, index=True)
    
    # Primary emotion data
    emotion_type = Column(String(50), nullable=False)  # happy, sad, angry, etc.
    confidence = Column(Float, nullable=False)  # Confidence score 0-1
    
    # VADER sentiment scores
    compound = Column(Float, nullable=True)  # Overall sentiment (-1 to 1)
    positive = Column(Float, nullable=True)  # Positive sentiment score
    negative = Column(Float, nullable=True)  # Negative sentiment score
    neutral = Column(Float, nullable=True)   # Neutral sentiment score
    
    # TextBlob scores
    polarity = Column(Float, nullable=True)      # Polarity score (-1 to 1)
    subjectivity = Column(Float, nullable=True)  # Subjectivity score (0 to 1)
    
    # Additional analysis
    intensity = Column(Float, nullable=True)     # Emotion intensity (0 to 1)
    emotion_label = Column(String(20), nullable=True)  # positive/negative/neutral
    
    # Raw analysis data
    analysis_data = Column(JSON, nullable=True)  # Complete analysis results
    
    # Processing metadata
    analyzer_version = Column(String(20), nullable=True)  # Version of emotion analyzer
    processing_time = Column(Float, nullable=True)       # Time taken for analysis
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    # Note: Don't create back_populates for Chat as it might cause circular imports
    # message = relationship("Message")  # Commented out to avoid circular imports
    
    def __repr__(self):
        return f"<Emotion(id={self.id}, emotion_type='{self.emotion_type}', confidence={self.confidence})>"
    
    def to_dict(self) -> dict:
        """Convert emotion to dictionary"""
        return {
            "id": self.id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "emotion_type": self.emotion_type,
            "confidence": self.confidence,
            "compound": self.compound,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "polarity": self.polarity,
            "subjectivity": self.subjectivity,
            "intensity": self.intensity,
            "emotion_label": self.emotion_label,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def create_from_analysis(cls, chat_id: int, message_id: int, analysis_data: dict):
        """Create Emotion record from emotion analysis data"""
        return cls(
            chat_id=chat_id,
            message_id=message_id,
            emotion_type=analysis_data.get("primary_emotion", "neutral"),
            confidence=analysis_data.get("confidence", 0.0),
            compound=analysis_data.get("compound", 0.0),
            positive=analysis_data.get("positive", 0.0),
            negative=analysis_data.get("negative", 0.0),
            neutral=analysis_data.get("neutral", 0.0),
            polarity=analysis_data.get("polarity", 0.0),
            subjectivity=analysis_data.get("subjectivity", 0.0),
            intensity=analysis_data.get("intensity", 0.0),
            emotion_label=analysis_data.get("sentiment_label", "neutral"),
            analysis_data=analysis_data,
            analyzer_version="1.0",
            processing_time=analysis_data.get("processing_time", 0.0)
        )