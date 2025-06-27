from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Index, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import enum

from app.database import Base

# user_preference.py content
class PreferenceType(enum.Enum):
    """Preference type enumeration"""
    CONVERSATION_STYLE = "conversation_style"
    RESPONSE_LENGTH = "response_length"
    LANGUAGE = "language"
    TOPIC_INTEREST = "topic_interest"
    FORMALITY_LEVEL = "formality_level"
    CREATIVITY_LEVEL = "creativity_level"
    TECHNICAL_LEVEL = "technical_level"

class UserPreference(Base):
    """
    User preference model for personalization
    """
    __tablename__ = "user_preferences"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Preference details
    preference_type = Column(Enum(PreferenceType), nullable=False)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(JSON, nullable=False)
    
    # Preference metadata
    confidence_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    interaction_count = Column(Integer, default=0, nullable=False)
    last_reinforced = Column(DateTime(timezone=True), nullable=True)
    
    # Source of preference (learned vs explicit)
    is_explicit = Column(Boolean, default=False, nullable=False)  # User explicitly set
    source = Column(String(50), default="learned", nullable=False)  # learned, explicit, imported
    
    # Preference context
    context_tags = Column(JSON, default=list, nullable=False)
    
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
    user = relationship("User", back_populates="user_preferences")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_pref_user_type', 'user_id', 'preference_type'),
        Index('idx_user_pref_key', 'preference_key'),
        Index('idx_user_pref_confidence', 'confidence_score'),
        Index('idx_user_pref_explicit', 'is_explicit'),
    )
    
    def __init__(self, **kwargs):
        """Initialize user preference"""
        if 'context_tags' not in kwargs:
            kwargs['context_tags'] = []
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id}, type='{self.preference_type.value}', key='{self.preference_key}')>"
    
    def reinforce(self, weight: float = 1.0) -> None:
        """Reinforce this preference (increase confidence)"""
        self.interaction_count += 1
        self.last_reinforced = datetime.now(timezone.utc)
        
        # Increase confidence with diminishing returns
        current_confidence = self.confidence_score
        confidence_increase = weight * (1.0 - current_confidence) * 0.1
        self.confidence_score = min(1.0, current_confidence + confidence_increase)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def weaken(self, weight: float = 1.0) -> None:
        """Weaken this preference (decrease confidence)"""
        confidence_decrease = weight * self.confidence_score * 0.1
        self.confidence_score = max(0.0, self.confidence_score - confidence_decrease)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_context_tag(self, tag: str) -> None:
        """Add a context tag"""
        if tag not in self.context_tags:
            tags = self.context_tags.copy()
            tags.append(tag)
            self.context_tags = tags
    
    def remove_context_tag(self, tag: str) -> None:
        """Remove a context tag"""
        if tag in self.context_tags:
            tags = self.context_tags.copy()
            tags.remove(tag)
            self.context_tags = tags
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preference to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "preference_type": self.preference_type.value,
            "preference_key": self.preference_key,
            "preference_value": self.preference_value,
            "confidence_score": self.confidence_score,
            "interaction_count": self.interaction_count,
            "is_explicit": self.is_explicit,
            "source": self.source,
            "context_tags": self.context_tags,
            "last_reinforced": self.last_reinforced.isoformat() if self.last_reinforced else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }