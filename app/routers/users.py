from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.database import get_db
from app.models.user import User
from app.models.user_preferences import UserPreferences
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])

# Pydantic models
class UserPreferencesUpdate(BaseModel):
    age: Optional[int] = None
    interests: Optional[List[str]] = None
    language: Optional[str] = None
    personality_type: Optional[str] = None
    response_style: Optional[str] = None
    theme: Optional[str] = None
    notification_settings: Optional[Dict[str, Any]] = None

class UserPreferencesResponse(BaseModel):
    id: int
    user_id: int
    age: Optional[int]
    interests: Optional[List[str]]
    language: Optional[str]
    personality_type: Optional[str]
    response_style: Optional[str]
    theme: Optional[str]
    notification_settings: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

@router.get("/profile")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get user profile (same as auth profile but different endpoint)"""
    return current_user

@router.put("/profile")
async def update_user_profile(
    profile_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    for field, value in profile_data.items():
        if hasattr(current_user, field) and field not in ['id', 'email', 'password_hash']:
            setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        # Create default preferences
        preferences = UserPreferences(
            user_id=current_user.id,
            language="en",
            response_style="balanced",
            theme="light"
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    return preferences

@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_update: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    if not preferences:
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
    
    # Update preferences
    for field, value in preferences_update.dict(exclude_unset=True).items():
        setattr(preferences, field, value)
    
    preferences.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(preferences)
    
    return preferences