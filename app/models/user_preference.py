"""
User Preference Model - User personalization and preferences
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import enum

from app.database import Base

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
    User preferences and personalization data
    """
    __tablename__ = "user_preferences"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Preferences (stored as JSON for flexibility)
    preferences = Column(JSON, default=dict, nullable=False)
    
    # Interaction patterns
    interaction_patterns = Column(JSON, default=dict, nullable=False)
    
    # Learning data
    learning_data = Column(JSON, default=dict, nullable=False)
    
    # Feature flags
    features_enabled = Column(JSON, default=dict, nullable=False)
    
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
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="user_preferences")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_preference_updated', 'updated_at'),
        Index('idx_user_preference_interaction', 'last_interaction_at'),
    )
    
    def __init__(self, **kwargs):
        """Initialize user preference with defaults"""
        if 'preferences' not in kwargs:
            kwargs['preferences'] = self.get_default_preferences()
        if 'interaction_patterns' not in kwargs:
            kwargs['interaction_patterns'] = {}
        if 'learning_data' not in kwargs:
            kwargs['learning_data'] = {}
        if 'features_enabled' not in kwargs:
            kwargs['features_enabled'] = self.get_default_features()
        
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id})>"
    
    @staticmethod
    def get_default_preferences() -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            # Communication preferences
            "conversation_style": "friendly",  # friendly, formal, casual, professional
            "preferred_response_length": "medium",  # short, medium, long
            "humor_level": "moderate",  # none, light, moderate, high
            "formality_level": "neutral",  # very_casual, casual, neutral, formal, very_formal
            
            # Content preferences
            "interests": [],  # List of topics the user is interested in
            "avoid_topics": [],  # Topics to avoid
            "language": "en",  # Language preference
            "technical_level": "intermediate",  # beginner, intermediate, advanced, expert
            
            # Interaction preferences
            "emotional_support_level": "standard",  # minimal, standard, high
            "proactivity": "moderate",  # low, moderate, high
            "question_asking": "moderate",  # low, moderate, high
            "context_awareness": "high",  # low, medium, high
            
            # UI/UX preferences
            "theme": "light",  # light, dark, auto
            "notification_preferences": {
                "email": True,
                "push": False,
                "in_app": True
            },
            "timezone": "UTC",
            
            # Privacy preferences
            "data_retention": "standard",  # minimal, standard, extended
            "analytics_opt_in": True,
            "personalization_level": "full"  # basic, standard, full
        }
    
    @staticmethod
    def get_default_features() -> Dict[str, bool]:
        """Get default feature flags"""
        return {
            "emotion_detection": True,
            "personalization": True,
            "context_awareness": True,
            "voice_input": False,
            "voice_output": False,
            "advanced_analytics": False,
            "beta_features": False
        }
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a specific preference value"""
        keys = key.split('.')
        value = self.preferences
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a specific preference value"""
        keys = key.split('.')
        
        # Navigate to the nested key
        current = self.preferences
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        current[keys[-1]] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def get_pattern(self, pattern_type: str) -> Any:
        """Get interaction pattern data"""
        return self.interaction_patterns.get(pattern_type)
    
    def update_pattern(self, pattern_type: str, data: Any) -> None:
        """Update interaction pattern data"""
        if self.interaction_patterns is None:
            self.interaction_patterns = {}
        
        self.interaction_patterns[pattern_type] = data
        self.last_interaction_at = datetime.now(timezone.utc)
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.features_enabled.get(feature, False)
    
    def toggle_feature(self, feature: str, enabled: bool) -> None:
        """Toggle a feature on/off"""
        if self.features_enabled is None:
            self.features_enabled = {}
        
        self.features_enabled[feature] = enabled
        self.updated_at = datetime.now(timezone.utc)
    
    def record_interaction(self, interaction_type: str, data: Dict[str, Any]) -> None:
        """Record an interaction for learning purposes"""
        if self.learning_data is None:
            self.learning_data = {}
        
        if "interactions" not in self.learning_data:
            self.learning_data["interactions"] = []
        
        self.learning_data["interactions"].append({
            "type": interaction_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        })
        
        # Keep only recent interactions (last 100)
        self.learning_data["interactions"] = self.learning_data["interactions"][-100:]
        
        self.last_interaction_at = datetime.now(timezone.utc)
    
    def get_personalization_summary(self) -> Dict[str, Any]:
        """Get a summary of personalization data"""
        total_interactions = len(self.learning_data.get("interactions", []))
        
        # Calculate engagement metrics
        if total_interactions > 0:
            recent_interactions = self.learning_data["interactions"][-10:]
            avg_sentiment = sum(
                i.get("data", {}).get("sentiment", 0) 
                for i in recent_interactions
            ) / len(recent_interactions)
        else:
            avg_sentiment = 0
        
        return {
            "user_id": self.user_id,
            "total_interactions": total_interactions,
            "conversation_style": self.get_preference("conversation_style"),
            "interests": self.get_preference("interests", []),
            "preferred_response_length": self.get_preference("preferred_response_length"),
            "personalization_level": self.get_preference("personalization_level"),
            "last_interaction": self.last_interaction_at.isoformat() if self.last_interaction_at else None,
            "engagement_level": self._calculate_engagement_level(),
            "average_recent_sentiment": avg_sentiment,
            "features_enabled": sum(1 for v in self.features_enabled.values() if v),
            "active_patterns": list(self.interaction_patterns.keys())
        }
    
    def _calculate_engagement_level(self) -> str:
        """Calculate user engagement level based on interactions"""
        if not self.last_interaction_at:
            return "new"
        
        days_since_last = (datetime.now(timezone.utc) - self.last_interaction_at).days
        total_interactions = len(self.learning_data.get("interactions", []))
        
        if days_since_last > 30:
            return "inactive"
        elif days_since_last > 7:
            return "low"
        elif total_interactions < 10:
            return "moderate"
        else:
            return "high"
    
    def to_dict(self, include_learning_data: bool = False) -> Dict[str, Any]:
        """Convert user preference to dictionary"""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "preferences": self.preferences,
            "interaction_patterns": self.interaction_patterns,
            "features_enabled": self.features_enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_interaction_at": self.last_interaction_at.isoformat() if self.last_interaction_at else None,
            "personalization_summary": self.get_personalization_summary()
        }
        
        if include_learning_data:
            data["learning_data"] = self.learning_data
        
        return data
    
    def merge_preferences(self, new_preferences: Dict[str, Any]) -> None:
        """Merge new preferences with existing ones"""
        def deep_merge(base: dict, update: dict) -> dict:
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base
        
        self.preferences = deep_merge(self.preferences, new_preferences)
        self.updated_at = datetime.now(timezone.utc)
    
    def reset_to_defaults(self) -> None:
        """Reset preferences to defaults"""
        self.preferences = self.get_default_preferences()
        self.features_enabled = self.get_default_features()
        self.interaction_patterns = {}
        self.learning_data = {}
        self.updated_at = datetime.now(timezone.utc)