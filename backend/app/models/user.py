"""
User Model - schema with comprehensive user management
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from passlib.context import CryptContext
import re
from typing import Optional, Dict, Any, List

from app.database import Base

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    """
    User model with comprehensive user management features
    Fixed: Added password_hash field that was missing in server logs
    """
    __tablename__ = "users"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Authentication fields - FIXED: Added password_hash field
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # FIXED: This was missing
    
    # Profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_premium = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # User preferences
    timezone = Column(String(50), default="UTC", nullable=False)
    language = Column(String(10), default="en", nullable=False)
    theme = Column(String(20), default="light", nullable=False)
    
    # Usage statistics
    total_chats = Column(Integer, default=0, nullable=False)
    total_messages = Column(Integer, default=0, nullable=False)
    total_tokens_used = Column(Integer, default=0, nullable=False)
    
    # User settings (JSON field for flexible settings)
    settings = Column(JSON, default=dict, nullable=False)
    voice_preferences = Column(JSON, default=dict, nullable=False)
    
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
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Email verification
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_token = Column(String(255), nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    user_preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes for better performance
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_username_active', 'username', 'is_active'),
        Index('idx_user_created_at', 'created_at'),
        Index('idx_user_last_activity', 'last_activity'),
        Index('idx_user_verification', 'verification_token'),
        Index('idx_user_reset_token', 'reset_token'),
    )
    
    def __init__(self, **kwargs):
        """Initialize user with default settings"""
        # Set default settings if not provided
        if 'settings' not in kwargs:
            kwargs['settings'] = self.get_default_settings()
        
        # Generate full name if first_name and last_name provided
        if 'first_name' in kwargs and 'last_name' in kwargs:
            kwargs['full_name'] = f"{kwargs['first_name']} {kwargs['last_name']}".strip()
        
        super().__init__(**kwargs)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    def __str__(self):
        return f"{self.username} ({self.email})"
    
    @staticmethod
    def get_default_settings() -> Dict[str, Any]:
        """Get default user settings"""
        return {
            "notifications": {
                "email_enabled": True,
                "push_enabled": True,
                "chat_notifications": True
            },
            "privacy": {
                "profile_public": False,
                "show_online_status": True,
                "data_collection_consent": False
            },
            "chat_preferences": {
                "ai_model": "gemini-2.0-flash-001",
                "response_style": "balanced",
                "max_context_length": 10,
                "enable_emotion_detection": True,
                "enable_personalization": True
            },
            "ui_preferences": {
                "compact_mode": False,
                "show_timestamps": True,
                "typing_indicators": True,
                "sound_enabled": True
            }
        }
    
    def set_password(self, password: str) -> None:
        """
        Hash and set user password
        """
        if not self.validate_password(password):
            raise ValueError("Password does not meet requirements")
        
        self.password_hash = pwd_context.hash(password)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password
        """
        return pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """
        Verify user password against hash
        """
        if not self.password_hash:
            return False
        return pwd_context.verify(password, self.password_hash)
    
    @staticmethod
    def validate_password(password: str) -> bool:
        """
        Validate password strength
        """
        if len(password) < 8:
            return False
        
        # Check for at least one uppercase, lowercase, digit, and special character
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'[0-9]', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
            return False
        
        return True
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """
        Validate username format
        """
        # Username: 3-50 chars, alphanumeric + underscore, no spaces
        pattern = r'^[a-zA-Z0-9_]{3,50}$'
        return re.match(pattern, username) is not None
    
    def update_last_activity(self) -> None:
        """
        Update last activity timestamp
        """
        self.last_activity = datetime.now(timezone.utc)
    
    def update_last_login(self) -> None:
        """
        Update last login timestamp
        """
        self.last_login = datetime.now(timezone.utc)
        self.update_last_activity()
    
    def increment_usage_stats(self, messages: int = 0, tokens: int = 0) -> None:
        """
        Increment usage statistics
        """
        if messages > 0:
            self.total_messages += messages
        if tokens > 0:
            self.total_tokens_used += tokens
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific setting value
        """
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set_setting(self, key: str, value: Any) -> None:
        """
        Set a specific setting value
        """
        keys = key.split('.')
        settings = self.settings.copy()
        current = settings
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        self.settings = settings
    
    def is_email_verified(self) -> bool:
        """
        Check if email is verified
        """
        return self.email_verified_at is not None
    
    def verify_email(self) -> None:
        """
        Mark email as verified
        """
        self.email_verified_at = datetime.now(timezone.utc)
        self.verification_token = None
        self.is_verified = True
    
    def can_reset_password(self) -> bool:
        """
        Check if user can reset password (token exists and not expired)
        """
        if not self.reset_token or not self.reset_token_expires:
            return False
        
        return datetime.now(timezone.utc) < self.reset_token_expires
    
    def clear_reset_token(self) -> None:
        """
        Clear password reset token
        """
        self.reset_token = None
        self.reset_token_expires = None
    
    def get_display_name(self) -> str:
        """
        Get user's display name
        """
        if self.full_name:
            return self.full_name
        elif self.first_name:
            return self.first_name
        else:
            return self.username
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        Convert user to dictionary
        """
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email if include_sensitive else None,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "display_name": self.get_display_name(),
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium,
            "timezone": self.timezone,
            "language": self.language,
            "theme": self.theme,
            "total_chats": self.total_chats,
            "total_messages": self.total_messages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }
        
        if include_sensitive:
            data.update({
                "settings": self.settings,
                "total_tokens_used": self.total_tokens_used,
                "last_login": self.last_login.isoformat() if self.last_login else None,
                "email_verified_at": self.email_verified_at.isoformat() if self.email_verified_at else None,
            })
        
        return data
    
    def get_public_profile(self) -> Dict[str, Any]:
        """
        Get public profile information
        """
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.get_display_name(),
            "avatar_url": self.avatar_url,
            "bio": self.bio if self.get_setting("privacy.profile_public", False) else None,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def search(cls, query: str, limit: int = 10) -> List["User"]:
        """
        Search users by username, email, or full name
        Note: This would typically be implemented in a service layer
        """
        # This is a placeholder - actual implementation would be in a service
        pass
    
    def get_chat_summary(self) -> Dict[str, Any]:
        """
        Get user's chat activity summary
        """
        return {
            "total_chats": self.total_chats,
            "total_messages": self.total_messages,
            "average_messages_per_chat": self.total_messages / max(self.total_chats, 1),
            "total_tokens_used": self.total_tokens_used,
            "account_age_days": (datetime.now(timezone.utc) - self.created_at).days if self.created_at else 0,
        }
    
    def can_create_chat(self) -> bool:
        """
        Check if user can create new chat (rate limiting, quotas, etc.)
        """
        # Basic implementation - can be extended with more complex logic
        if not self.is_active:
            return False
        
        # Premium users have no limits
        if self.is_premium:
            return True
        
        # Free users have daily limits
        daily_chat_limit = 50
        return self.total_chats < daily_chat_limit
    
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Get user's current rate limits
        """
        if self.is_premium:
            return {
                "messages_per_hour": 1000,
                "chats_per_day": 100,
                "tokens_per_day": 100000,
                "file_uploads_per_day": 50
            }
        else:
            return {
                "messages_per_hour": 100,
                "chats_per_day": 10,
                "tokens_per_day": 10000,
                "file_uploads_per_day": 5
            }