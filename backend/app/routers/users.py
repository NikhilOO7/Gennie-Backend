from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, EmailStr, validator

from app.database import get_db
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message
from app.routers.auth import get_current_user, get_current_verified_user, get_current_user
from app.routers.health import health_router

logger = logging.getLogger(__name__)
users_router = APIRouter()

# Request/Response models
class UserProfile(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None

class UserSettings(BaseModel):
    settings: Dict[str, Any]

class VoicePreferences(BaseModel):
    voice_name: Optional[str] = None
    voice_language: Optional[str] = None
    speaking_rate: Optional[float] = None
    pitch: Optional[float] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    display_name: str
    avatar_url: Optional[str]
    bio: Optional[str]
    is_verified: bool
    is_premium: bool
    timezone: str
    language: str
    theme: str
    total_chats: int
    total_messages: int
    created_at: datetime
    last_activity: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserStats(BaseModel):
    total_chats: int
    total_messages: int
    total_tokens_used: int
    account_age_days: int
    average_messages_per_chat: float
    most_active_day: Optional[str]
    most_active_hour: Optional[int]
    favorite_ai_model: Optional[str]

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

@users_router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    
    user_dict = current_user.to_dict(include_sensitive=True)
    user_dict["display_name"] = current_user.get_display_name()
    return UserResponse(**user_dict)

@users_router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_update: UserProfile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile"""
    
    try:
        # Update fields
        update_data = profile_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        # Update full name if first/last name changed
        if 'first_name' in update_data or 'last_name' in update_data:
            first_name = current_user.first_name or ""
            last_name = current_user.last_name or ""
            current_user.full_name = f"{first_name} {last_name}".strip()
        
        current_user.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"User profile updated: {current_user.id}")
        
        user_dict = current_user.to_dict(include_sensitive=True)
        user_dict["display_name"] = current_user.get_display_name()
        return UserResponse(**user_dict)
    
    except Exception as e:
        logger.error(f"Failed to update user profile: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )

@users_router.get("/me/settings")
async def get_user_settings(current_user: User = Depends(get_current_user)):
    """Get user settings"""
    return {"settings": current_user.settings}

@users_router.put("/me/settings")
async def update_user_settings(
    settings_update: UserSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user settings"""
    
    try:
        # Validate settings structure
        if not isinstance(settings_update.settings, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Settings must be a valid JSON object"
            )
        
        # Update settings
        current_user.settings = settings_update.settings
        current_user.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"User settings updated: {current_user.id}")
        
        return {"settings": current_user.settings, "message": "Settings updated successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user settings: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings"
        )

@users_router.get("/me/voice-preferences", response_model=VoicePreferences)
async def get_voice_preferences(current_user: User = Depends(get_current_user)):
    """Get user's voice preferences."""
    return current_user.voice_preferences or {}

@users_router.put("/me/voice-preferences", response_model=VoicePreferences)
async def update_voice_preferences(
    voice_prefs: VoicePreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's voice preferences."""
    try:
        current_user.voice_preferences = voice_prefs.dict(exclude_unset=True)
        await db.commit()
        return current_user.voice_preferences
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update voice preferences for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Could not update voice preferences.")

@users_router.get("/me/stats", response_model=UserStats)
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user statistics"""
    
    try:
        # Basic stats from user model
        basic_stats = current_user.get_chat_summary()
        
        # Additional statistics from database
        chat_query = select(Chat).where(
            and_(
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        chat_result = await db.execute(chat_query)
        chats = chat_result.scalars().all()
        
        # Calculate additional metrics
        ai_models = {}
        for chat in chats:
            model = chat.ai_model
            ai_models[model] = ai_models.get(model, 0) + 1
        
        favorite_ai_model = max(ai_models, key=ai_models.get) if ai_models else None
        
        return UserStats(
            total_chats=basic_stats["total_chats"],
            total_messages=basic_stats["total_messages"],
            total_tokens_used=basic_stats["total_tokens_used"],
            account_age_days=basic_stats["account_age_days"],
            average_messages_per_chat=basic_stats["average_messages_per_chat"],
            most_active_day=None,  # Would calculate from message timestamps
            most_active_hour=None,  # Would calculate from message timestamps
            favorite_ai_model=favorite_ai_model
        )
    
    except Exception as e:
        logger.error(f"Failed to get user statistics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )

@users_router.delete("/me")
async def delete_user_account(
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user account (requires email verification)"""
    
    try:
        # Soft delete user
        current_user.is_active = False
        current_user.is_deleted = True
        current_user.updated_at = datetime.now(timezone.utc)
        
        # Soft delete all user chats
        chat_query = select(Chat).where(Chat.user_id == current_user.id)
        chat_result = await db.execute(chat_query)
        chats = chat_result.scalars().all()
        
        for chat in chats:
            chat.soft_delete()
        
        await db.commit()
        
        logger.info(f"User account deleted: {current_user.id}")
        
        return {"message": "Account deleted successfully"}
    
    except Exception as e:
        logger.error(f"Failed to delete user account: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )

@users_router.get("/me/export")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export all user data (GDPR compliance)"""
    
    try:
        # Get user profile
        user_data = current_user.to_dict(include_sensitive=True)
        
        # Get all chats
        chat_query = select(Chat).where(Chat.user_id == current_user.id)
        chat_result = await db.execute(chat_query)
        chats = chat_result.scalars().all()
        
        chat_data = []
        for chat in chats:
            chat_export = chat.export_conversation("json")
            chat_data.append(chat_export)
        
        export_data = {
            "user_profile": user_data,
            "chats": chat_data,
            "export_date": datetime.now(timezone.utc).isoformat(),
            "data_format": "json",
            "total_chats": len(chat_data),
            "total_messages": sum(len(chat.get("messages", [])) for chat in chat_data)
        }
        
        logger.info(f"User data exported: {current_user.id}")
        
        return export_data
    
    except Exception as e:
        logger.error(f"Failed to export user data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export user data"
        )

# Admin endpoints (would require admin authentication)
@users_router.get("/", response_model=UserListResponse)
async def get_users(
    # current_admin: User = Depends(get_current_admin_user),  # Would need admin check
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search users"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verified status"),
    db: AsyncSession = Depends(get_db)
):
    """Get users list (admin only)"""
    
    try:
        # Build query
        query = select(User)
        
        # Apply filters
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        if is_verified is not None:
            query = query.where(User.is_verified == is_verified)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_term),
                    User.email.ilike(search_term),
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term)
                )
            )
        
        # Count total results
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(desc(User.created_at)).offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Calculate pagination info
        has_next = offset + page_size < total_count
        has_previous = page > 1
        
        user_responses = []
        for user in users:
            user_dict = user.to_dict()
            user_dict["display_name"] = user.get_display_name()
            user_responses.append(UserResponse(**user_dict))
        
        return UserListResponse(
            users=user_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous
        )
    
    except Exception as e:
        logger.error(f"Failed to get users list: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@users_router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    # current_admin: User = Depends(get_current_admin_user),  # Would need admin check
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID (admin only)"""
    
    try:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_dict = user.to_dict()
        user_dict["display_name"] = user.get_display_name()
        return UserResponse(**user_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )

# Create the main router and include sub-routers
router = APIRouter()
router.include_router(health_router, tags=["Health"])
router.include_router(users_router, prefix="/users", tags=["Users"])

# Export both routers
__all__ = ["router", "health_router", "users_router"]