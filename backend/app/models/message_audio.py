# Update to app/models.py - Add these fields to the Message model

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # New fields for voice support
    audio_url = Column(String(500), nullable=True)  # URL to stored audio file
    voice_metadata = Column(JSON, nullable=True)    # Voice-related metadata
    
    # Relationships
    user = relationship("User", back_populates="messages")

# Migration script - alembic/versions/add_voice_support.py
"""Add voice support to messages

Revision ID: add_voice_support_001
Revises: 
Create Date: 2024-01-XX

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_voice_support_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add audio_url column
    op.add_column('messages', 
        sa.Column('audio_url', sa.String(500), nullable=True)
    )
    
    # Add voice_metadata column
    op.add_column('messages',
        sa.Column('voice_metadata', sa.JSON(), nullable=True)
    )
    
    # Create index on audio_url for faster lookups
    op.create_index(
        'ix_messages_audio_url',
        'messages',
        ['audio_url'],
        unique=False
    )

def downgrade():
    # Drop index
    op.drop_index('ix_messages_audio_url', table_name='messages')
    
    # Drop columns
    op.drop_column('messages', 'voice_metadata')
    op.drop_column('messages', 'audio_url')

# Update to message creation logic in app/routers/messages.py
from typing import Optional, Dict, Any
import uuid
import boto3
from botocore.exceptions import ClientError

class MessageService:
    def __init__(self):
        # Initialize S3 client for audio storage (optional)
        self.s3_client = boto3.client('s3')
        self.audio_bucket = os.environ.get('AUDIO_BUCKET_NAME', 'chatbot-audio')
        
    async def create_message(
        self,
        user_id: int,
        content: str,
        is_user: bool,
        audio_data: Optional[bytes] = None,
        voice_metadata: Optional[Dict[str, Any]] = None,
        db = None
    ) -> Message:
        """
        Create a new message with optional audio
        
        Args:
            user_id: User ID
            content: Message content
            is_user: Whether this is a user message
            audio_data: Optional audio data bytes
            voice_metadata: Optional voice-related metadata
            db: Database session
            
        Returns:
            Created message
        """
        audio_url = None
        
        # Store audio if provided
        if audio_data:
            audio_url = await self.store_audio(user_id, audio_data)
            
        # Create message
        message = Message(
            user_id=user_id,
            content=content,
            is_user=is_user,
            audio_url=audio_url,
            voice_metadata=voice_metadata or {},
            timestamp=datetime.utcnow()
        )
        
        db.add(message)
        db.commit()
        db.refresh(message)
        
        return message
    
    async def store_audio(self, user_id: int, audio_data: bytes) -> str:
        """
        Store audio data and return URL
        
        Args:
            user_id: User ID
            audio_data: Audio data bytes
            
        Returns:
            Audio URL
        """
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        key = f"audio/{user_id}/{audio_id}.mp3"
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.audio_bucket,
                Key=key,
                Body=audio_data,
                ContentType='audio/mpeg'
            )
            
            # Generate URL
            url = f"https://{self.audio_bucket}.s3.amazonaws.com/{key}"
            return url
            
        except ClientError as e:
            # Fallback to local storage
            local_path = f"./audio_storage/{user_id}/{audio_id}.mp3"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(audio_data)
                
            return f"/static/audio/{user_id}/{audio_id}.mp3"
    
    async def get_message_audio(self, message_id: int, db) -> Optional[bytes]:
        """
        Retrieve audio data for a message
        
        Args:
            message_id: Message ID
            db: Database session
            
        Returns:
            Audio data bytes or None
        """
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message or not message.audio_url:
            return None
            
        # Check if S3 URL
        if message.audio_url.startswith('https://'):
            # Extract key from URL
            key = message.audio_url.split('.com/')[-1]
            
            try:
                response = self.s3_client.get_object(
                    Bucket=self.audio_bucket,
                    Key=key
                )
                return response['Body'].read()
            except ClientError:
                return None
        else:
            # Local file
            local_path = message.audio_url.replace('/static/', './')
            if os.path.exists(local_path):
                with open(local_path, 'rb') as f:
                    return f.read()
                    
        return None

# Create singleton instance
message_service = MessageService()