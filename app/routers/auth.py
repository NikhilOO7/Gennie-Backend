"""
Authentication Router - User authentication and authorization
with JWT tokens, refresh tokens, and comprehensive security
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
import secrets
import logging
from pydantic import BaseModel, EmailStr, validator
import bcrypt

from app.database import get_db, get_redis
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()

# Pydantic models for request/response
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('username')
    def validate_username(cls, v):
        if not User.validate_username(v):
            raise ValueError('Username must be 3-50 characters, alphanumeric and underscore only')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not User.validate_password(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, digit, and special character')
        return v

class UserLogin(BaseModel):
    email_or_username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PasswordReset(BaseModel):
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if not User.validate_password(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, digit, and special character')
        return v

class PasswordResetRequest(BaseModel):
    email: EmailStr

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if not User.validate_password(v):
            raise ValueError('Password must be at least 8 characters with uppercase, lowercase, digit, and special character')
        return v

class EmailVerification(BaseModel):
    token: str

# JWT token functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.get_secret_key(), 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.get_secret_key(), 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token, 
            settings.get_secret_key(), 
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError("Invalid token type")
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    token = credentials.credentials
    payload = verify_token(token, "access")
    
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get user from database
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )
    
    # Update last activity
    user.update_last_activity()
    await db.commit()
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user (additional validation)"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

async def get_current_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current verified user"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    return current_user

# Utility functions
async def authenticate_user(
    email_or_username: str, 
    password: str, 
    db: AsyncSession
) -> Optional[User]:
    """Authenticate user with email/username and password"""
    
    # Try to find user by email or username
    stmt = select(User).where(
        and_(
            (User.email == email_or_username) | (User.username == email_or_username),
            User.is_active == True
        )
    )
    
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        return None
    
    if not user.verify_password(password):
        return None
    
    return user

async def create_user(user_data: UserRegister, db: AsyncSession) -> User:
    """Create new user account"""
    
    # Check if user already exists
    stmt = select(User).where(
        (User.email == user_data.email) | (User.username == user_data.username)
    )
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        verification_token=secrets.token_urlsafe(32)
    )
    
    user.set_password(user_data.password)
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user

# Authentication endpoints
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Register new user account"""
    
    try:
        # Create user
        user = await create_user(user_data, db)
        
        # Generate tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        # Store refresh token in Redis
        if redis:
            await redis.setex(
                f"refresh_token:{user.id}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
                refresh_token
            )
        
        # Log registration
        logger.info(
            f"New user registered: {user.username} ({user.email})",
            extra={
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        # TODO: Send verification email in background task
        # background_tasks.add_task(send_verification_email, user.email, user.verification_token)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user.to_dict()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """User login"""
    
    try:
        # Authenticate user
        user = await authenticate_user(login_data.email_or_username, login_data.password, db)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email/username or password"
            )
        
        # Generate tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username},
            expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": user.id})
        
        # Store refresh token in Redis
        if redis:
            await redis.setex(
                f"refresh_token:{user.id}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
                refresh_token
            )
        
        # Update login timestamp
        user.update_last_login()
        await db.commit()
        
        # Log successful login
        logger.info(
            f"User logged in: {user.username}",
            extra={
                "user_id": user.id,
                "username": user.username,
                "client_ip": request.client.host if request.client else "unknown"
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user.to_dict()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Refresh access token"""
    
    try:
        # Verify refresh token
        payload = verify_token(refresh_data.refresh_token, "refresh")
        user_id: int = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Check if refresh token exists in Redis
        if redis:
            stored_token = await redis.get(f"refresh_token:{user_id}")
            if not stored_token or stored_token != refresh_data.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
        
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Generate new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.id, "username": user.username},
            expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(data={"sub": user.id})
        
        # Update refresh token in Redis
        if redis:
            await redis.setex(
                f"refresh_token:{user.id}",
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
                new_refresh_token
            )
        
        # Update last activity
        user.update_last_activity()
        await db.commit()
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user.to_dict()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    redis = Depends(get_redis)
):
    """User logout"""
    
    try:
        # Remove refresh token from Redis
        if redis:
            await redis.delete(f"refresh_token:{current_user.id}")
        
        # Log logout
        logger.info(
            f"User logged out: {current_user.username}",
            extra={"user_id": current_user.id, "username": current_user.username}
        )
        
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}", exc_info=True)
        return {"message": "Logged out locally"}

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user.to_dict(include_sensitive=True)

@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    
    try:
        # Verify current password
        if not current_user.verify_password(password_data.current_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Set new password
        current_user.set_password(password_data.new_password)
        await db.commit()
        
        logger.info(
            f"Password changed for user: {current_user.username}",
            extra={"user_id": current_user.id}
        )
        
        return {"message": "Password changed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.post("/request-password-reset")
async def request_password_reset(
    reset_request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset"""
    
    try:
        # Find user by email
        stmt = select(User).where(User.email == reset_request.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            
            await db.commit()
            
            # TODO: Send reset email in background task
            # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
            
            logger.info(
                f"Password reset requested for: {user.email}",
                extra={"user_id": user.id}
            )
        
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}
    
    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}", exc_info=True)
        return {"message": "Password reset request processed"}

@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """Reset password with token"""
    
    try:
        # Find user by reset token
        stmt = select(User).where(User.reset_token == reset_data.token)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.can_reset_password():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Set new password
        user.set_password(reset_data.new_password)
        user.clear_reset_token()
        
        await db.commit()
        
        logger.info(
            f"Password reset completed for: {user.username}",
            extra={"user_id": user.id}
        )
        
        return {"message": "Password reset successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )

@router.post("/verify-email")
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db)
):
    """Verify email address"""
    
    try:
        # Find user by verification token
        stmt = select(User).where(User.verification_token == verification_data.token)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        if user.is_email_verified():
            return {"message": "Email already verified"}
        
        # Verify email
        user.verify_email()
        await db.commit()
        
        logger.info(
            f"Email verified for user: {user.username}",
            extra={"user_id": user.id}
        )
        
        return {"message": "Email verified successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )

# Export commonly used functions
__all__ = [
    "router",
    "get_current_user",
    "get_current_active_user", 
    "get_current_verified_user",
    "verify_token",
    "create_access_token",
    "create_refresh_token"
]