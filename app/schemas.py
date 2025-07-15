from pydantic import BaseModel, Field, validator, EmailStr
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from enum import Enum
import re

# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        # Enable ORM mode for SQLAlchemy integration
        from_attributes = True
        # FIXED: Changed from allow_population_by_field_name to validate_by_name for Pydantic V2
        populate_by_name = True
        # Validate assignment
        validate_assignment = True
        # Use enum values
        use_enum_values = True

# Common field validators
class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class TopicInfo(BaseSchema):
    """Topic information schema"""
    id: str
    name: str
    icon: str
    description: Optional[str] = None

class UserTopicsUpdate(BaseSchema):
    """Schema for updating user topics"""
    topics: List[str] = Field(..., min_length=0, max_length=20)

class UserTopicsResponse(BaseSchema):
    """Response for user topics"""
    selected_topics: List[str]
    available_topics: List[TopicInfo]
    topic_stats: Dict[str, Any]
    recommendations: List[TopicInfo]

# User schemas
class UserBase(BaseSchema):
    """Base user schema"""
    # FIXED: Changed regex to pattern for Pydantic V2
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    timezone: str = Field(default="UTC", max_length=50)
    language: str = Field(default="en", max_length=10)
    theme: str = Field(default="light", max_length=20)

class UserCreate(UserBase):
    """Schema for user creation"""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        
        checks = [
            (r'[A-Z]', 'uppercase letter'),
            (r'[a-z]', 'lowercase letter'), 
            (r'[0-9]', 'digit'),
            (r'[!@#$%^&*(),.?\":{}|<>]', 'special character')
        ]
        
        for pattern, desc in checks:
            if not re.search(pattern, v):
                raise ValueError(f'Password must contain at least one {desc}')
        
        return v

class UserUpdate(BaseSchema):
    """Schema for user updates"""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    timezone: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    theme: Optional[str] = Field(None, max_length=20)

class UserResponse(UserBase, TimestampMixin):
    """Schema for user responses"""
    id: int
    full_name: Optional[str]
    display_name: str
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    is_premium: bool
    total_chats: int
    total_messages: int
    last_activity: Optional[datetime]

# Chat schemas
class ChatBase(BaseSchema):
    """Base chat schema"""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    ai_model: str = Field(default="gemini-2.0-flash-001", max_length=50)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1, le=4000)
    chat_mode: str = Field('text', pattern="^(text|voice)$")
    related_topic: Optional[str] = None

class ChatCreate(ChatBase):
    """Schema for chat creation"""
    system_prompt: Optional[str] = Field(None, max_length=2000)
    

class ChatUpdate(BaseSchema):
    """Schema for chat updates"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    ai_model: Optional[str] = Field(None, max_length=50)
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4000)
    system_prompt: Optional[str] = Field(None, max_length=2000)
    is_favorite: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None

class ChatResponse(ChatBase, TimestampMixin):
    """Schema for chat responses"""
    id: int
    user_id: int
    is_active: bool
    is_archived: bool
    is_favorite: bool
    total_messages: int
    total_tokens_used: int
    last_activity_at: Optional[datetime]
    last_message_at: Optional[datetime]

# Message schemas
class MessageType(str, Enum):
    """Message type enumeration"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"

class SenderType(str, Enum):
    """Sender type enumeration"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class MessageBase(BaseSchema):
    """Base message schema"""
    content: str = Field(..., min_length=1, max_length=4000)
    message_type: MessageType = MessageType.TEXT
    sender_type: SenderType

class MessageCreate(MessageBase):
    """Schema for message creation"""
    chat_id: int

class MessageResponse(MessageBase, TimestampMixin):
    """Schema for message responses"""
    id: int
    chat_id: int
    tokens_used: int = 0
    processing_time: Optional[float] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    emotion_detected: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_edited: bool = False
    is_deleted: bool = False
    is_flagged: bool = False

# AI conversation schemas
class ConversationRequest(BaseSchema):
    """Schema for AI conversation requests"""
    message: str = Field(..., min_length=1, max_length=4000)
    chat_id: Optional[int] = None
    use_context: bool = True
    detect_emotion: bool = True
    enable_personalization: bool = True
    stream: bool = False
    
    @validator('message')
    def validate_message_content(cls, v):
        """Validate message content"""
        if not v.strip():
            raise ValueError('Message cannot be empty or only whitespace')
        return v.strip()

class ConversationResponse(BaseSchema):
    """Schema for AI conversation responses"""
    response: str
    chat_id: int
    user_message_id: int
    ai_message_id: int
    timestamp: datetime
    processing_time: float
    token_usage: Dict[str, int]
    emotion_data: Optional[Dict[str, Any]] = None
    personalization_applied: bool = False

# Emotion schemas
class EmotionType(str, Enum):
    """Emotion type enumeration"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    EXCITEMENT = "excitement"
    ANXIETY = "anxiety"
    FRUSTRATION = "frustration"
    CONTENTMENT = "contentment"

class EmotionAnalysis(BaseSchema):
    """Schema for emotion analysis results"""
    primary_emotion: EmotionType
    secondary_emotion: Optional[EmotionType] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    emotion_intensity: float = Field(..., ge=0.0, le=1.0)
    analysis_method: str
    processing_time: float

# Pagination schemas
class PaginationParams(BaseSchema):
    """Schema for pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

class PaginatedResponse(BaseSchema):
    """Base schema for paginated responses"""
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

# Error schemas
class ErrorResponse(BaseSchema):
    """Schema for error responses"""
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None

class ValidationErrorResponse(ErrorResponse):
    """Schema for validation error responses"""
    validation_errors: List[Dict[str, Any]]

# Health check schemas
class HealthStatus(str, Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ServiceHealth(BaseSchema):
    """Schema for individual service health"""
    status: HealthStatus
    response_time_ms: Optional[float] = None
    last_check: datetime
    error: Optional[str] = None

class HealthCheckResponse(BaseSchema):
    """Schema for health check responses"""
    status: HealthStatus
    timestamp: datetime
    version: str
    environment: str
    checks: Dict[str, ServiceHealth]
    response_time_seconds: float

# WebSocket schemas
class WebSocketMessageType(str, Enum):
    """WebSocket message type enumeration"""
    CHAT_MESSAGE = "chat_message"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    PING = "ping"
    PONG = "pong"
    ERROR = "error"

class WebSocketMessage(BaseSchema):
    """Schema for WebSocket messages"""
    type: WebSocketMessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Export all schemas
__all__ = [
    "BaseSchema",
    "TimestampMixin",
    "TopicInfo",
    "UserTopicsUpdate",
    "UserTopicsResponse",
    "UserBase",
    "UserCreate", 
    "UserUpdate",
    "UserResponse",
    "ChatBase",
    "ChatCreate",
    "ChatUpdate", 
    "ChatResponse",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "MessageType",
    "SenderType",
    "ConversationRequest",
    "ConversationResponse",
    "EmotionType",
    "EmotionAnalysis",
    "PaginationParams",
    "PaginatedResponse",
    "ErrorResponse",
    "ValidationErrorResponse",
    "HealthStatus",
    "ServiceHealth",
    "HealthCheckResponse",
    "WebSocketMessageType",
    "WebSocketMessage"
]