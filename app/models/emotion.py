from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import enum

from app.database import Base

class EmotionType(enum.Enum):
    """Emotion type enumeration"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    CONTEMPT = "contempt"
    NEUTRAL = "neutral"
    EXCITEMENT = "excitement"
    ANXIETY = "anxiety"
    FRUSTRATION = "frustration"
    CONTENTMENT = "contentment"

class Emotion(Base):
    """
    Emotion analysis model for tracking emotional patterns
    """
    __tablename__ = "emotions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    
    # Emotion data
    primary_emotion = Column(Enum(EmotionType), nullable=False)
    secondary_emotion = Column(Enum(EmotionType), nullable=True)
    
    # Scores and confidence
    emotion_scores = Column(JSON, default=dict, nullable=False)  # All emotion scores
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0
    sentiment_score = Column(Float, nullable=False)   # -1.0 to 1.0
    
    # Analysis metadata
    analysis_method = Column(String(50), default="vader", nullable=False)
    text_analyzed = Column(Text, nullable=True)
    context_used = Column(JSON, default=dict, nullable=False)
    
    # Temporal information
    emotion_intensity = Column(Float, default=0.5, nullable=False)  # 0.0 to 1.0
    emotion_duration = Column(Integer, nullable=True)  # in seconds
    
    # Timestamps
    detected_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    
    # Relationships
    user = relationship("User")
    chat = relationship("Chat")
    message = relationship("Message")
    
    # Indexes
    __table_args__ = (
        Index('idx_emotion_user_detected', 'user_id', 'detected_at'),
        Index('idx_emotion_chat', 'chat_id'),
        Index('idx_emotion_primary', 'primary_emotion'),
        Index('idx_emotion_sentiment', 'sentiment_score'),
        Index('idx_emotion_confidence', 'confidence_score'),
    )
    
    def __init__(self, **kwargs):
        """Initialize emotion record"""
        if 'emotion_scores' not in kwargs:
            kwargs['emotion_scores'] = {}
        if 'context_used' not in kwargs:
            kwargs['context_used'] = {}
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<Emotion(id={self.id}, user_id={self.user_id}, primary='{self.primary_emotion.value}', confidence={self.confidence_score:.2f})>"
    
    def get_emotion_label(self) -> str:
        """Get human-readable emotion label"""
        return self.primary_emotion.value.replace('_', ' ').title()
    
    def get_sentiment_label(self) -> str:
        """Get human-readable sentiment label"""
        if self.sentiment_score > 0.1:
            return "Positive"
        elif self.sentiment_score < -0.1:
            return "Negative"
        else:
            return "Neutral"
    
    def get_intensity_label(self) -> str:
        """Get emotion intensity label"""
        if self.emotion_intensity > 0.8:
            return "Very Strong"
        elif self.emotion_intensity > 0.6:
            return "Strong"
        elif self.emotion_intensity > 0.4:
            return "Moderate"
        elif self.emotion_intensity > 0.2:
            return "Weak"
        else:
            return "Very Weak"
    
    def get_confidence_label(self) -> str:
        """Get confidence level label"""
        if self.confidence_score > 0.8:
            return "High"
        elif self.confidence_score > 0.6:
            return "Medium"
        elif self.confidence_score > 0.4:
            return "Low"
        else:
            return "Very Low"
    
    def is_positive(self) -> bool:
        """Check if emotion is generally positive"""
        positive_emotions = {EmotionType.JOY, EmotionType.EXCITEMENT, EmotionType.CONTENTMENT, EmotionType.SURPRISE}
        return self.primary_emotion in positive_emotions
    
    def is_negative(self) -> bool:
        """Check if emotion is generally negative"""
        negative_emotions = {EmotionType.SADNESS, EmotionType.ANGER, EmotionType.FEAR, 
                           EmotionType.DISGUST, EmotionType.ANXIETY, EmotionType.FRUSTRATION}
        return self.primary_emotion in negative_emotions
    
    def is_neutral(self) -> bool:
        """Check if emotion is neutral"""
        return self.primary_emotion == EmotionType.NEUTRAL
    
    def get_all_emotions(self) -> List[Dict[str, Any]]:
        """Get all detected emotions with scores"""
        emotions = []
        
        # Add primary emotion
        emotions.append({
            "emotion": self.primary_emotion.value,
            "score": self.emotion_scores.get(self.primary_emotion.value, self.confidence_score),
            "is_primary": True
        })
        
        # Add secondary emotion if exists
        if self.secondary_emotion:
            emotions.append({
                "emotion": self.secondary_emotion.value,
                "score": self.emotion_scores.get(self.secondary_emotion.value, 0.0),
                "is_primary": False
            })
        
        # Add other emotions from scores
        for emotion, score in self.emotion_scores.items():
            if emotion not in [e["emotion"] for e in emotions]:
                emotions.append({
                    "emotion": emotion,
                    "score": score,
                    "is_primary": False
                })
        
        # Sort by score
        return sorted(emotions, key=lambda x: x["score"], reverse=True)
    
    def to_dict(self, include_context: bool = False) -> Dict[str, Any]:
        """Convert emotion to dictionary"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "primary_emotion": self.primary_emotion.value,
            "secondary_emotion": self.secondary_emotion.value if self.secondary_emotion else None,
            "emotion_label": self.get_emotion_label(),
            "confidence_score": self.confidence_score,
            "confidence_label": self.get_confidence_label(),
            "sentiment_score": self.sentiment_score,
            "sentiment_label": self.get_sentiment_label(),
            "emotion_intensity": self.emotion_intensity,
            "intensity_label": self.get_intensity_label(),
            "analysis_method": self.analysis_method,
            "is_positive": self.is_positive(),
            "is_negative": self.is_negative(),
            "is_neutral": self.is_neutral(),
            "all_emotions": self.get_all_emotions(),
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        
        if include_context:
            data.update({
                "emotion_scores": self.emotion_scores,
                "context_used": self.context_used,
                "text_analyzed": self.text_analyzed,
                "emotion_duration": self.emotion_duration,
            })
        
        return data
    
    @classmethod
    def create_from_analysis(cls, user_id: int, analysis_result: Dict[str, Any], 
                           chat_id: int = None, message_id: int = None) -> "Emotion":
        """Create emotion record from analysis result"""
        return cls(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            primary_emotion=EmotionType(analysis_result.get("primary_emotion", "neutral")),
            secondary_emotion=EmotionType(analysis_result["secondary_emotion"]) if analysis_result.get("secondary_emotion") else None,
            emotion_scores=analysis_result.get("emotion_scores", {}),
            confidence_score=analysis_result.get("confidence_score", 0.0),
            sentiment_score=analysis_result.get("sentiment_score", 0.0),
            emotion_intensity=analysis_result.get("emotion_intensity", 0.5),
            analysis_method=analysis_result.get("analysis_method", "vader"),
            text_analyzed=analysis_result.get("text_analyzed"),
            context_used=analysis_result.get("context_used", {}),
        )
    
    def get_emotion_pattern_summary(self) -> Dict[str, Any]:
        """Get summary for emotion pattern analysis"""
        return {
            "primary_emotion": self.primary_emotion.value,
            "sentiment_score": self.sentiment_score,
            "emotion_intensity": self.emotion_intensity,
            "confidence_score": self.confidence_score,
            "detected_at": self.detected_at,
            "is_positive": self.is_positive(),
            "is_negative": self.is_negative(),
        }