from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Base schemas
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]

class UserLogin(BaseSchema):
    username: str
    password: str

# Token Schemas
class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseSchema):
    username: Optional[str] = None

# Chat Schemas
class ChatBase(BaseSchema):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)

class ChatCreate(ChatBase):
    pass

class ChatUpdate(BaseSchema):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_archived: Optional[bool] = None

class ChatResponse(ChatBase):
    id: int
    user_id: int
    is_active: bool
    is_archived: bool
    total_messages: int
    last_message_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

# Message Schemas
class MessageBase(BaseSchema):
    content: str = Field(..., min_length=1)
    message_type: str = Field(default="text")

class MessageCreate(MessageBase):
    chat_id: int

class MessageResponse(MessageBase):
    id: int
    chat_id: int
    is_from_user: bool
    tokens_used: Optional[int]
    processing_time: Optional[float]
    sentiment_score: Optional[float]
    emotion_detected: Optional[str]
    confidence_score: Optional[float]
    created_at: datetime

# AI Conversation Schemas
class ConversationRequest(BaseSchema):
    message: str = Field(..., min_length=1, max_length=4000)
    chat_id: Optional[int] = None
    use_context: bool = True
    detect_emotion: bool = True

class ConversationResponse(BaseSchema):
    response: str
    chat_id: int
    message_id: int
    tokens_used: int
    processing_time: float
    emotion_detected: Optional[str] = None
    sentiment_score: Optional[float] = None

# User Preferences Schemas
class UserPreferencesBase(BaseSchema):
    preferred_response_length: str = Field(default="medium")
    conversation_style: str = Field(default="friendly")
    language: str = Field(default="en")
    timezone: str = Field(default="UTC")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=100, le=4000)

class UserPreferencesCreate(UserPreferencesBase):
    pass

class UserPreferencesUpdate(BaseSchema):
    preferred_response_length: Optional[str] = None
    conversation_style: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=4000)
    enable_emotion_detection: Optional[bool] = None
    enable_context_memory: Optional[bool] = None
    enable_learning: Optional[bool] = None

class UserPreferencesResponse(UserPreferencesBase):
    id: int
    user_id: int
    enable_emotion_detection: bool
    enable_context_memory: bool
    enable_learning: bool
    interests: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime]

# Health Check Schema
class HealthResponse(BaseSchema):
    status: str
    message: str
    timestamp: datetime
    version: str
    environment: str

# Error Schemas
class ErrorResponse(BaseSchema):
    error: str
    detail: Optional[str] = None
    code: Optional[int] = None