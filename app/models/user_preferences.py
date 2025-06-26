"""User preferences model for storing user customization settings."""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Dict, List, Any

from app.database import Base

class UserPreferences(Base):
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Personal Information
    age = Column(Integer, nullable=True)
    location = Column(String(100), nullable=True)
    occupation = Column(String(100), nullable=True)
    
    # Interests and Topics
    interests = Column(JSON, nullable=True)  # List of interests
    preferred_topics = Column(JSON, nullable=True)  # List of preferred conversation topics
    avoided_topics = Column(JSON, nullable=True)   # List of topics to avoid
    
    # Communication Preferences
    language = Column(String(10), default="en", nullable=False)
    personality_type = Column(String(20), nullable=True)  # MBTI, Big5, etc.
    communication_style = Column(String(20), default="casual", nullable=False)  # casual, formal, professional
    response_style = Column(String(20), default="balanced", nullable=False)  # concise, detailed, balanced
    
    # AI Behavior Preferences
    ai_personality = Column(String(50), default="helpful", nullable=False)  # helpful, friendly, professional, witty
    preferred_response_length = Column(String(20), default="medium", nullable=False)  # short, medium, long
    use_emojis = Column(Boolean, default=True, nullable=False)
    include_examples = Column(Boolean, default=True, nullable=False)
    ask_clarifying_questions = Column(Boolean, default=True, nullable=False)
    
    # Learning and Adaptation
    learning_style = Column(String(20), nullable=True)  # visual, auditory, kinesthetic, reading
    expertise_level = Column(JSON, nullable=True)  # {"programming": "expert", "cooking": "beginner"}
    adaptation_speed = Column(String(20), default="medium", nullable=False)  # slow, medium, fast
    
    # UI/UX Preferences
    theme = Column(String(20), default="light", nullable=False)  # light, dark, auto
    font_size = Column(String(10), default="medium", nullable=False)  # small, medium, large
    compact_mode = Column(Boolean, default=False, nullable=False)
    animations_enabled = Column(Boolean, default=True, nullable=False)
    
    # Notification Preferences
    notification_settings = Column(JSON, nullable=True)  # Flexible notification settings
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    
    # Privacy Settings
    data_collection_consent = Column(Boolean, default=True, nullable=False)
    analytics_consent = Column(Boolean, default=True, nullable=False)
    personalization_consent = Column(Boolean, default=True, nullable=False)
    
    # Advanced Settings
    custom_prompts = Column(JSON, nullable=True)  # User-defined custom prompts
    api_preferences = Column(JSON, nullable=True)  # API-specific preferences
    experimental_features = Column(Boolean, default=False, nullable=False)
    
    # Usage Patterns (automatically updated)
    most_active_hours = Column(JSON, nullable=True)  # Hours when user is most active
    preferred_conversation_length = Column(Integer, nullable=True)  # Average messages per conversation
    typical_session_duration = Column(Integer, nullable=True)  # Minutes per session
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_sync = Column(DateTime(timezone=True), nullable=True)  # Last time preferences were synced
    
    # Relationships
    user = relationship("User", back_populates="user_preferences")
    
    def __repr__(self):
        return f"<UserPreferences(id={self.id}, user_id={self.user_id}, language='{self.language}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "age": self.age,
            "location": self.location,
            "occupation": self.occupation,
            "interests": self.interests or [],
            "preferred_topics": self.preferred_topics or [],
            "avoided_topics": self.avoided_topics or [],
            "language": self.language,
            "personality_type": self.personality_type,
            "communication_style": self.communication_style,
            "response_style": self.response_style,
            "ai_personality": self.ai_personality,
            "preferred_response_length": self.preferred_response_length,
            "use_emojis": self.use_emojis,
            "include_examples": self.include_examples,
            "ask_clarifying_questions": self.ask_clarifying_questions,
            "learning_style": self.learning_style,
            "expertise_level": self.expertise_level or {},
            "theme": self.theme,
            "notification_settings": self.notification_settings or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def update_interests(self, new_interests: List[str]):
        """Add new interests while keeping existing ones"""
        current_interests = self.interests or []
        for interest in new_interests:
            if interest not in current_interests:
                current_interests.append(interest)
        # Keep only the most recent 20 interests
        self.interests = current_interests[-20:]
    
    def add_preferred_topic(self, topic: str):
        """Add a preferred topic"""
        if not self.preferred_topics:
            self.preferred_topics = []
        if topic not in self.preferred_topics:
            self.preferred_topics.append(topic)
            # Keep only top 15 topics
            self.preferred_topics = self.preferred_topics[-15:]
    
    def add_avoided_topic(self, topic: str):
        """Add a topic to avoid"""
        if not self.avoided_topics:
            self.avoided_topics = []
        if topic not in self.avoided_topics:
            self.avoided_topics.append(topic)
    
    def set_expertise(self, domain: str, level: str):
        """Set expertise level for a domain"""
        if not self.expertise_level:
            self.expertise_level = {}
        self.expertise_level[domain] = level
    
    def get_expertise(self, domain: str) -> str:
        """Get expertise level for a domain"""
        if not self.expertise_level:
            return "beginner"
        return self.expertise_level.get(domain, "beginner")
    
    def update_usage_pattern(self, hour: int, conversation_length: int, session_duration: int):
        """Update usage patterns based on current session"""
        # Update most active hours
        if not self.most_active_hours:
            self.most_active_hours = {}
        
        hour_str = str(hour)
        if hour_str in self.most_active_hours:
            self.most_active_hours[hour_str] += 1
        else:
            self.most_active_hours[hour_str] = 1
        
        # Update conversation length (running average)
        if self.preferred_conversation_length:
            self.preferred_conversation_length = (self.preferred_conversation_length + conversation_length) // 2
        else:
            self.preferred_conversation_length = conversation_length
        
        # Update session duration (running average)
        if self.typical_session_duration:
            self.typical_session_duration = (self.typical_session_duration + session_duration) // 2
        else:
            self.typical_session_duration = session_duration
    
    def get_most_active_hour(self) -> int:
        """Get the hour when user is most active"""
        if not self.most_active_hours:
            return 12  # Default to noon
        
        most_active = max(self.most_active_hours.items(), key=lambda x: x[1])
        return int(most_active[0])
    
    @classmethod
    def create_default(cls, user_id: int):
        """Create default preferences for a new user"""
        return cls(
            user_id=user_id,
            interests=[],
            preferred_topics=[],
            avoided_topics=[],
            language="en",
            communication_style="casual",
            response_style="balanced",
            ai_personality="helpful",
            preferred_response_length="medium",
            theme="light",
            notification_settings={
                "new_features": True,
                "tips": True,
                "reminders": False
            },
            expertise_level={}
        )