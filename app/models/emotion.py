"""
Emotion Model - Emotion analysis records
"""

import numpy as np
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
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
            return "Mild"
        else:
            return "Very Mild"
    
    def is_positive_emotion(self) -> bool:
        """Check if emotion is positive"""
        positive_emotions = [
            EmotionType.JOY,
            EmotionType.EXCITEMENT,
            EmotionType.CONTENTMENT,
            EmotionType.SURPRISE  # Can be positive or negative
        ]
        return self.primary_emotion in positive_emotions
    
    def is_negative_emotion(self) -> bool:
        """Check if emotion is negative"""
        negative_emotions = [
            EmotionType.SADNESS,
            EmotionType.ANGER,
            EmotionType.FEAR,
            EmotionType.DISGUST,
            EmotionType.CONTEMPT,
            EmotionType.ANXIETY,
            EmotionType.FRUSTRATION
        ]
        return self.primary_emotion in negative_emotions
    
    def get_all_emotions_sorted(self) -> List[Tuple[str, float]]:
        """Get all emotions sorted by score"""
        if not self.emotion_scores:
            return []
        
        sorted_emotions = sorted(
            self.emotion_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_emotions
    
    def to_dict(self, include_analysis: bool = True) -> Dict[str, Any]:
        """Convert emotion record to dictionary"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "primary_emotion": self.primary_emotion.value,
            "secondary_emotion": self.secondary_emotion.value if self.secondary_emotion else None,
            "confidence_score": self.confidence_score,
            "sentiment_score": self.sentiment_score,
            "emotion_intensity": self.emotion_intensity,
            "emotion_label": self.get_emotion_label(),
            "sentiment_label": self.get_sentiment_label(),
            "intensity_label": self.get_intensity_label(),
            "is_positive": self.is_positive_emotion(),
            "is_negative": self.is_negative_emotion(),
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }
        
        if include_analysis:
            data.update({
                "emotion_scores": self.emotion_scores,
                "analysis_method": self.analysis_method,
                "text_analyzed": self.text_analyzed,
                "context_used": self.context_used,
                "emotion_duration": self.emotion_duration,
                "all_emotions": self.get_all_emotions_sorted()
            })
        
        return data
    
    @classmethod
    def create_from_analysis(
        cls,
        user_id: int,
        analysis_result: Dict[str, Any],
        chat_id: Optional[int] = None,
        message_id: Optional[int] = None
    ) -> "Emotion":
        """Create emotion record from analysis result"""
        # Extract primary emotion
        primary_emotion = analysis_result.get("primary_emotion", "neutral")
        if isinstance(primary_emotion, str):
            try:
                primary_emotion = EmotionType(primary_emotion.lower())
            except ValueError:
                primary_emotion = EmotionType.NEUTRAL
        
        # Extract secondary emotion if present
        secondary_emotion = analysis_result.get("secondary_emotion")
        if secondary_emotion and isinstance(secondary_emotion, str):
            try:
                secondary_emotion = EmotionType(secondary_emotion.lower())
            except ValueError:
                secondary_emotion = None
        
        return cls(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            primary_emotion=primary_emotion,
            secondary_emotion=secondary_emotion,
            emotion_scores=analysis_result.get("emotion_scores", {}),
            confidence_score=analysis_result.get("confidence_score", 0.5),
            sentiment_score=analysis_result.get("sentiment_score", 0.0),
            emotion_intensity=analysis_result.get("emotion_intensity", 0.5),
            analysis_method=analysis_result.get("analysis_method", "vader"),
            text_analyzed=analysis_result.get("text_analyzed", "")[:500],  # Limit text length
            context_used=analysis_result.get("context_used", {})
        )
    
    def update_from_analysis(self, analysis_result: Dict[str, Any]) -> None:
        """Update emotion record with new analysis results"""
        # Update primary emotion
        primary_emotion = analysis_result.get("primary_emotion")
        if primary_emotion:
            try:
                self.primary_emotion = EmotionType(primary_emotion.lower())
            except ValueError:
                pass
        
        # Update scores
        if "confidence_score" in analysis_result:
            self.confidence_score = analysis_result["confidence_score"]
        if "sentiment_score" in analysis_result:
            self.sentiment_score = analysis_result["sentiment_score"]
        if "emotion_intensity" in analysis_result:
            self.emotion_intensity = analysis_result["emotion_intensity"]
        if "emotion_scores" in analysis_result:
            self.emotion_scores = analysis_result["emotion_scores"]
        
        # Update metadata
        if "analysis_method" in analysis_result:
            self.analysis_method = analysis_result["analysis_method"]
        if "context_used" in analysis_result:
            self.context_used = analysis_result["context_used"]
    
    def get_emotion_trajectory(self, other_emotions: List["Emotion"]) -> Dict[str, Any]:
        """Analyze emotion trajectory given a list of emotions"""
        if not other_emotions:
            return {
                "trend": "stable",
                "changes": [],
                "volatility": 0.0
            }
        
        # Sort by detection time
        all_emotions = [self] + other_emotions
        all_emotions.sort(key=lambda e: e.detected_at)
        
        # Calculate changes
        changes = []
        for i in range(1, len(all_emotions)):
            prev_emotion = all_emotions[i-1]
            curr_emotion = all_emotions[i]
            
            if prev_emotion.primary_emotion != curr_emotion.primary_emotion:
                changes.append({
                    "from": prev_emotion.primary_emotion.value,
                    "to": curr_emotion.primary_emotion.value,
                    "timestamp": curr_emotion.detected_at.isoformat(),
                    "sentiment_change": curr_emotion.sentiment_score - prev_emotion.sentiment_score
                })
        
        # Calculate volatility (how much emotions change)
        sentiment_scores = [e.sentiment_score for e in all_emotions]
        if len(sentiment_scores) > 1:
            volatility = np.std(sentiment_scores)
        else:
            volatility = 0.0
        
        # Determine trend
        if len(sentiment_scores) >= 2:
            recent_avg = np.mean(sentiment_scores[-3:])
            early_avg = np.mean(sentiment_scores[:3])
            if recent_avg > early_avg + 0.1:
                trend = "improving"
            elif recent_avg < early_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "changes": changes,
            "volatility": float(volatility),
            "emotion_sequence": [e.primary_emotion.value for e in all_emotions]
        }