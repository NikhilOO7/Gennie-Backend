"""
RAG (Retrieval-Augmented Generation) Service
Provides context retrieval and conversation memory for the chatbot
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
import json
import numpy as np
from redis.asyncio import Redis

from app.models.message import Message, SenderType
from app.models.user_preference import UserPreference
from app.services.openai_service import openai_service

logger = logging.getLogger(__name__)


class RAGService:
    """Service for managing conversation context and retrieval"""
    
    def __init__(self):
        self.embedding_cache_ttl = 3600  # 1 hour
        self.context_window_size = 10
        self.similarity_threshold = 0.7
    
    async def get_context_for_chat(
        self,
        chat_id: int,
        user_id: int,
        current_message: str,
        db: AsyncSession,
        redis_client: Optional[Redis] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for the current chat message
        
        Returns:
            Dictionary containing:
            - context_messages: List of relevant previous messages
            - user_preferences: User's preferences and patterns
            - similarity_scores: Relevance scores for context messages
        """
        try:
            # Get recent messages from the chat
            recent_messages = await self._get_recent_messages(
                chat_id=chat_id,
                db=db,
                limit=20
            )
            
            # Get user preferences
            user_preferences = await self._get_user_preferences(
                user_id=user_id,
                db=db
            )
            
            # Generate embedding for current message
            current_embedding = await self._get_message_embedding(
                message=current_message,
                redis_client=redis_client
            )
            
            # Find similar messages if we have embeddings
            similar_messages = []
            if current_embedding is not None:
                similar_messages = await self._find_similar_messages(
                    current_embedding=current_embedding,
                    recent_messages=recent_messages,
                    redis_client=redis_client
                )
            
            # Combine recent and similar messages
            context_messages = self._merge_context_messages(
                recent_messages=recent_messages[:self.context_window_size],
                similar_messages=similar_messages
            )
            
            return {
                "context_messages": context_messages,
                "user_preferences": user_preferences,
                "has_embeddings": current_embedding is not None
            }
            
        except Exception as e:
            logger.error(f"Failed to get context for chat: {str(e)}")
            return {
                "context_messages": [],
                "user_preferences": {},
                "error": str(e)
            }
    
    async def _get_recent_messages(
        self,
        chat_id: int,
        db: AsyncSession,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent messages from the chat"""
        try:
            query = select(Message).where(
                Message.chat_id == chat_id
            ).order_by(
                desc(Message.created_at)
            ).limit(limit)
            
            result = await db.execute(query)
            messages = result.scalars().all()
            
            # Convert to dictionaries and reverse to chronological order
            message_dicts = []
            for msg in reversed(messages):
                message_dicts.append({
                    "id": msg.id,
                    "content": msg.content,
                    "sender_type": msg.sender_type.value,
                    "created_at": msg.created_at.isoformat(),
                    "emotion_detected": msg.emotion_detected,
                    "sentiment_score": msg.sentiment_score
                })
            
            return message_dicts
            
        except Exception as e:
            logger.error(f"Failed to get recent messages: {str(e)}")
            return []
    
    async def _get_user_preferences(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get user preferences and patterns"""
        try:
            # For now, return empty preferences since the UserPreference model
            # stores individual preferences, not aggregated ones
            # In a real implementation, you would aggregate these preferences
            return {
                "communication_style": "balanced",
                "topics_of_interest": [],
                "response_length_preference": "medium",
                "humor_level": "moderate",
                "formality_level": "neutral",
                "emotional_support_level": "standard",
                "learning_preferences": {}
            }
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {str(e)}")
            return {}
    
    async def _get_message_embedding(
        self,
        message: str,
        redis_client: Optional[Redis] = None
    ) -> Optional[np.ndarray]:
        """Generate or retrieve embedding for a message"""
        try:
            # Check cache first
            if redis_client:
                cache_key = f"embedding:{hash(message)}"
                cached = await redis_client.get(cache_key)
                if cached:
                    return np.frombuffer(cached, dtype=np.float32)
            
            # Generate new embedding using the OpenAI service
            embedding_result = await openai_service.generate_embeddings(
                texts=message,  # generate_embeddings expects texts parameter
                model=self.embeddings_model if hasattr(self, 'embeddings_model') else None
            )
            
            if not embedding_result["success"]:
                logger.error(f"Failed to generate embedding: {embedding_result.get('error')}")
                return None
            
            # Extract the first (and only) embedding from the list
            embeddings = embedding_result.get("embeddings", [])
            if not embeddings:
                logger.error("No embeddings returned")
                return None
                
            embedding = np.array(embeddings[0], dtype=np.float32)
            
            # Cache the embedding
            if redis_client:
                await redis_client.setex(
                    cache_key,
                    self.embedding_cache_ttl,
                    embedding.tobytes()
                )
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get message embedding: {str(e)}")
            return None
    async def _find_similar_messages(
        self,
        current_embedding: np.ndarray,
        recent_messages: List[Dict[str, Any]],
        redis_client: Optional[Redis] = None
    ) -> List[Dict[str, Any]]:
        """Find messages similar to the current one"""
        similar_messages = []
        
        try:
            for message in recent_messages:
                # Skip if it's the same message
                if message["content"] == "":
                    continue
                
                # Get embedding for the message
                msg_embedding = await self._get_message_embedding(
                    message["content"],
                    redis_client
                )
                
                if msg_embedding is None:
                    continue
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(current_embedding, msg_embedding)
                
                if similarity >= self.similarity_threshold:
                    message["similarity_score"] = float(similarity)
                    similar_messages.append(message)
            
            # Sort by similarity score
            similar_messages.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return similar_messages[:5]  # Return top 5 similar messages
            
        except Exception as e:
            logger.error(f"Failed to find similar messages: {str(e)}")
            return []
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
            
        except Exception as e:
            logger.error(f"Failed to calculate cosine similarity: {str(e)}")
            return 0.0
    
    def _merge_context_messages(
        self,
        recent_messages: List[Dict[str, Any]],
        similar_messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge recent and similar messages, removing duplicates"""
        # Use a set to track message IDs
        seen_ids = set()
        merged = []
        
        # Add similar messages first (they're more relevant)
        for msg in similar_messages:
            if msg["id"] not in seen_ids:
                seen_ids.add(msg["id"])
                merged.append(msg)
        
        # Add recent messages
        for msg in recent_messages:
            if msg["id"] not in seen_ids:
                seen_ids.add(msg["id"])
                merged.append(msg)
        
        # Sort by created_at to maintain chronological order
        merged.sort(key=lambda x: x["created_at"])
        
        return merged[:self.context_window_size]
    
    async def store_conversation_feedback(
        self,
        message_id: int,
        user_id: int,
        feedback: str,
        db: AsyncSession
    ) -> bool:
        """Store user feedback for improving context retrieval"""
        try:
            # This would be used to improve the RAG system over time
            # For now, we just log it
            logger.info(f"Feedback received for message {message_id}: {feedback}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store feedback: {str(e)}")
            return False


# Create a singleton instance
rag_service = RAGService()

# Export
__all__ = ["rag_service", "RAGService"]