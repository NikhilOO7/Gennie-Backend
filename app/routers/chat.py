"""
Chat Management Router - CRUD operations for chats and messages
with comprehensive chat management and pagination
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, validator

from app.database import get_db, get_redis
from app.models.user import User
from app.models.chat import Chat
from app.models.message import Message, SenderType, MessageType
from app.routers.auth import get_current_user
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Request/Response models
class ChatCreate(BaseModel):
    title: Optional[str] = "New Chat"
    description: Optional[str] = None
    ai_model: Optional[str] = "gpt-3.5-turbo"
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v
    
    @validator('max_tokens')
    def validate_max_tokens(cls, v):
        if v is not None and not 1 <= v <= 4000:
            raise ValueError('Max tokens must be between 1 and 4000')
        return v

class ChatUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ai_model: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_favorite: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and not 0.0 <= v <= 2.0:
            raise ValueError('Temperature must be between 0.0 and 2.0')
        return v

class ChatResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    ai_model: str
    is_active: bool
    is_archived: bool
    is_favorite: bool
    total_messages: int
    total_tokens_used: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    last_message_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    id: int
    chat_id: int
    content: str
    message_type: str
    sender_type: str
    tokens_used: int
    processing_time: Optional[float]
    sentiment_score: Optional[float]
    emotion_detected: Optional[str]
    confidence_score: Optional[float]
    is_edited: bool
    is_deleted: bool
    is_flagged: bool
    created_at: datetime
    timestamp: Optional[datetime]
    
    class Config:
        from_attributes = True

class ChatListResponse(BaseModel):
    chats: List[ChatResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class BulkAction(BaseModel):
    action: str
    chat_ids: List[int]
    
    @validator('action')
    def validate_action(cls, v):
        allowed_actions = ['archive', 'unarchive', 'delete', 'favorite', 'unfavorite']
        if v not in allowed_actions:
            raise ValueError(f'Action must be one of: {allowed_actions}')
        return v

# Chat CRUD endpoints
@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat"""
    
    try:
        # Check if user can create more chats
        if not current_user.can_create_chat():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chat creation limit reached"
            )
        
        # Create chat
        chat = Chat(
            user_id=current_user.id,
            title=chat_data.title,
            description=chat_data.description,
            ai_model=chat_data.ai_model,
            system_prompt=chat_data.system_prompt,
            temperature=chat_data.temperature or 0.7,
            max_tokens=chat_data.max_tokens or 1000
        )
        
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        
        # Update user chat count
        current_user.total_chats += 1
        await db.commit()
        
        logger.info(
            f"Chat created: {chat.id} by user {current_user.id}",
            extra={
                "chat_id": chat.id,
                "user_id": current_user.id,
                "title": chat.title
            }
        )
        
        return ChatResponse.from_orm(chat)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat creation failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat"
        )

@router.get("/", response_model=ChatListResponse)
async def get_user_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    include_archived: bool = Query(False, description="Include archived chats"),
    include_deleted: bool = Query(False, description="Include soft-deleted chats"),
    search: Optional[str] = Query(None, description="Search in chat titles and descriptions"),
    sort_by: str = Query("last_activity_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """Get user's chats with pagination and filtering"""
    
    try:
        # Build query
        query = select(Chat).where(Chat.user_id == current_user.id)
        
        # Apply filters
        if not include_archived:
            query = query.where(Chat.is_archived == False)
        
        if not include_deleted:
            query = query.where(Chat.is_deleted == False)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Chat.title.ilike(search_term),
                    Chat.description.ilike(search_term)
                )
            )
        
        # Count total results
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply sorting
        if sort_order.lower() == "desc":
            sort_column = desc(getattr(Chat, sort_by, Chat.last_activity_at))
        else:
            sort_column = getattr(Chat, sort_by, Chat.last_activity_at)
        
        query = query.order_by(sort_column)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        chats = result.scalars().all()
        
        # Calculate pagination info
        has_next = offset + page_size < total_count
        has_previous = page > 1
        
        chat_responses = [ChatResponse.from_orm(chat) for chat in chats]
        
        return ChatListResponse(
            chats=chat_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous
        )
    
    except Exception as e:
        logger.error(f"Failed to get user chats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chats"
        )

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get specific chat"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Update last activity
        chat.update_activity()
        await db.commit()
        
        return ChatResponse.from_orm(chat)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chat {chat_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat"
        )

@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update chat"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Update fields
        update_data = chat_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(chat, field):
                setattr(chat, field, value)
        
        chat.update_activity()
        await db.commit()
        await db.refresh(chat)
        
        logger.info(
            f"Chat updated: {chat.id}",
            extra={"chat_id": chat.id, "user_id": current_user.id}
        )
        
        return ChatResponse.from_orm(chat)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update chat {chat_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update chat"
        )

@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: int,
    hard_delete: bool = Query(False, description="Permanently delete chat"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete chat (soft delete by default)"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        if hard_delete:
            # Permanently delete chat and all messages
            await db.delete(chat)
            current_user.total_chats = max(0, current_user.total_chats - 1)
            message = "Chat permanently deleted"
        else:
            # Soft delete
            chat.soft_delete()
            message = "Chat moved to trash"
        
        await db.commit()
        
        logger.info(
            f"Chat {'permanently ' if hard_delete else ''}deleted: {chat.id}",
            extra={"chat_id": chat.id, "user_id": current_user.id, "hard_delete": hard_delete}
        )
        
        return {"message": message}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chat {chat_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete chat"
        )

@router.post("/{chat_id}/restore")
async def restore_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore soft-deleted chat"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == True
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deleted chat not found"
            )
        
        chat.restore()
        await db.commit()
        
        logger.info(
            f"Chat restored: {chat.id}",
            extra={"chat_id": chat.id, "user_id": current_user.id}
        )
        
        return {"message": "Chat restored successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore chat {chat_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore chat"
        )

@router.post("/{chat_id}/archive")
async def archive_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Archive chat"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        chat.archive()
        await db.commit()
        
        return {"message": "Chat archived successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive chat {chat_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive chat"
        )

@router.post("/{chat_id}/unarchive")
async def unarchive_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unarchive chat"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_archived == True
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archived chat not found"
            )
        
        chat.unarchive()
        await db.commit()
        
        return {"message": "Chat unarchived successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unarchive chat {chat_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unarchive chat"
        )

@router.post("/{chat_id}/favorite")
async def toggle_favorite(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle chat favorite status"""
    
    try:
        query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        chat = result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        chat.toggle_favorite()
        await db.commit()
        
        action = "added to" if chat.is_favorite else "removed from"
        return {"message": f"Chat {action} favorites"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle favorite for chat {chat_id}: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update favorite status"
        )

# Message endpoints
@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_chat_messages(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    include_deleted: bool = Query(False, description="Include deleted messages")
):
    """Get chat messages with pagination"""
    
    try:
        # Verify chat access
        chat_query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        chat_result = await db.execute(chat_query)
        chat = chat_result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Build message query
        query = select(Message).where(Message.chat_id == chat_id)
        
        if not include_deleted:
            query = query.where(Message.is_deleted == False)
        
        # Count total messages
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total_count = count_result.scalar()
        
        # Apply pagination and ordering
        offset = (page - 1) * page_size
        query = query.order_by(Message.created_at).offset(offset).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Calculate pagination info
        has_next = offset + page_size < total_count
        has_previous = page > 1
        
        message_responses = [MessageResponse.from_orm(message) for message in messages]
        
        return MessageListResponse(
            messages=message_responses,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages for chat {chat_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )

# Bulk operations
@router.post("/bulk-action")
async def bulk_chat_action(
    bulk_action: BulkAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk action on multiple chats"""
    
    try:
        # Get chats
        query = select(Chat).where(
            and_(
                Chat.id.in_(bulk_action.chat_ids),
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        result = await db.execute(query)
        chats = result.scalars().all()
        
        if not chats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No chats found"
            )
        
        # Perform action
        updated_count = 0
        for chat in chats:
            if bulk_action.action == "archive":
                if not chat.is_archived:
                    chat.archive()
                    updated_count += 1
            elif bulk_action.action == "unarchive":
                if chat.is_archived:
                    chat.unarchive()
                    updated_count += 1
            elif bulk_action.action == "delete":
                if not chat.is_deleted:
                    chat.soft_delete()
                    updated_count += 1
            elif bulk_action.action == "favorite":
                if not chat.is_favorite:
                    chat.toggle_favorite()
                    updated_count += 1
            elif bulk_action.action == "unfavorite":
                if chat.is_favorite:
                    chat.toggle_favorite()
                    updated_count += 1
        
        await db.commit()
        
        logger.info(
            f"Bulk action performed: {bulk_action.action} on {updated_count} chats",
            extra={
                "user_id": current_user.id,
                "action": bulk_action.action,
                "chat_count": updated_count
            }
        )
        
        return {
            "message": f"Action '{bulk_action.action}' performed on {updated_count} chats",
            "updated_count": updated_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk action failed: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk action failed"
        )

# Chat statistics and analytics
@router.get("/{chat_id}/stats")
async def get_chat_stats(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chat statistics"""
    
    try:
        # Verify chat access
        chat_query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        )
        
        chat_result = await db.execute(chat_query)
        chat = chat_result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Get basic stats
        stats = chat.get_conversation_summary()
        
        # Add more detailed statistics
        message_query = select(Message).where(
            and_(
                Message.chat_id == chat_id,
                Message.is_deleted == False
            )
        )
        
        message_result = await db.execute(message_query)
        messages = message_result.scalars().all()
        
        if messages:
            user_messages = [m for m in messages if m.sender_type == SenderType.USER]
            ai_messages = [m for m in messages if m.sender_type == SenderType.ASSISTANT]
            
            # Calculate additional stats
            stats.update({
                "avg_user_message_length": sum(len(m.content) for m in user_messages) / len(user_messages) if user_messages else 0,
                "avg_ai_message_length": sum(len(m.content) for m in ai_messages) / len(ai_messages) if ai_messages else 0,
                "avg_response_time": sum(m.processing_time for m in ai_messages if m.processing_time) / len([m for m in ai_messages if m.processing_time]) if ai_messages else 0,
                "emotion_distribution": {},  # Would be calculated from emotion data
                "most_active_hour": None,  # Would be calculated from message timestamps
            })
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get stats for chat {chat_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat statistics"
        )

# Chat export
@router.get("/{chat_id}/export")
async def export_chat(
    chat_id: int,
    format: str = Query("json", description="Export format (json, markdown, txt)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export chat conversation"""
    
    try:
        # Verify chat access
        chat_query = select(Chat).where(
            and_(
                Chat.id == chat_id,
                Chat.user_id == current_user.id,
                Chat.is_deleted == False
            )
        ).options(selectinload(Chat.messages))
        
        chat_result = await db.execute(chat_query)
        chat = chat_result.scalar_one_or_none()
        
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        
        # Export conversation
        export_data = chat.export_conversation(format)
        
        if "error" in export_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=export_data["error"]
            )
        
        logger.info(
            f"Chat exported: {chat_id} in {format} format",
            extra={"chat_id": chat_id, "user_id": current_user.id, "format": format}
        )
        
        return export_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export chat {chat_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export chat"
        )