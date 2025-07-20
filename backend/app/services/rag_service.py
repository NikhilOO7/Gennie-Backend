"""
RAG (Retrieval-Augmented Generation) Service
Provides context-aware responses by retrieving relevant past conversations
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
import json

from app.models.message import Message, MessageType, SenderType
from app.models.chat import Chat
from app.models.user_preference import UserPreference
from app.services.gemini_service import gemini_service
from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service for context-aware conversation retrieval and generation
    """
    
    def __init__(self):
        """Initialize RAG service"""
        self.embeddings_model = "text-embedding-004"  # Gemini embeddings model
        self.embeddings_dimension = 768  # Gemini embeddings dimension
        self.max_context_messages = 20
        self.relevance_threshold = 0.7
        self.time_decay_factor = 0.95
        self.embedding_cache_ttl = 3600  # 1 hour
        
        logger.info("RAG service initialized")
    
    async def get_context_for_query(
        self,
        query: str,
        user_id: int,
        chat_id: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        redis_client: Optional[Redis] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get relevant context for a query from past conversations
        
        Args:
            query: The user's query
            user_id: User ID
            chat_id: Optional specific chat ID
            db: Database session
            redis_client: Redis client for caching
            limit: Maximum number of context messages
            
        Returns:
            Dictionary with context messages and metadata
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Get query embedding
            query_embedding = await self._get_message_embedding(query, redis_client)
            if query_embedding is None:
                logger.warning("Failed to get query embedding")
                return {"context_messages": [], "user_preferences": {}}
            
            # Retrieve relevant messages
            relevant_messages = await self._retrieve_relevant_messages(
                query_embedding,
                user_id,
                chat_id,
                db,
                limit
            )
            
            # Get user preferences
            user_preferences = await self._get_user_preferences(user_id, db)
            
            # Format context
            context_messages = []
            for msg, score in relevant_messages:
                context_messages.append({
                    "content": msg.content,
                    "sender_type": msg.sender_type.value,
                    "created_at": msg.created_at.isoformat(),
                    "relevance_score": float(score),
                    "chat_id": msg.chat_id,
                    "tokens": msg.tokens_used or 0
                })
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "context_messages": context_messages,
                "user_preferences": user_preferences,
                "query_embedding_cached": False,  # Would track if cached
                "processing_time": processing_time,
                "messages_retrieved": len(context_messages)
            }
            
        except Exception as e:
            logger.error(f"Failed to get context for query: {str(e)}", exc_info=True)
            return {"context_messages": [], "user_preferences": {}}
    
    async def _retrieve_relevant_messages(
        self,
        query_embedding: np.ndarray,
        user_id: int,
        chat_id: Optional[int],
        db: AsyncSession,
        limit: int
    ) -> List[Tuple[Message, float]]:
        """Retrieve relevant messages based on embedding similarity"""
        try:
            # Build query
            query = select(Message).join(Chat).where(
                and_(
                    Chat.user_id == user_id,
                    Message.content.isnot(None),
                    Message.content != ""
                )
            )
            
            # Filter by chat if specified
            if chat_id:
                query = query.where(Chat.id == chat_id)
            
            # Order by recency and limit
            query = query.order_by(desc(Message.created_at)).limit(100)
            
            # Execute query
            result = await db.execute(query)
            messages = result.scalars().all()
            
            if not messages:
                return []
            
            # Calculate similarities
            relevant_messages = []
            for msg in messages:
                # Get message embedding
                msg_embedding = await self._get_message_embedding(
                    msg.content,
                    None  # Redis client could be passed here
                )
                
                if msg_embedding is None:
                    continue
                
                # Calculate cosine similarity
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    msg_embedding.reshape(1, -1)
                )[0][0]
                
                # Apply time decay
                time_diff = (datetime.now(timezone.utc) - msg.created_at).days
                time_weight = self.time_decay_factor ** time_diff
                weighted_score = similarity * time_weight
                
                # Filter by threshold
                if weighted_score >= self.relevance_threshold:
                    relevant_messages.append((msg, weighted_score))
            
            # Sort by score and limit
            relevant_messages.sort(key=lambda x: x[1], reverse=True)
            return relevant_messages[:limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve relevant messages: {str(e)}")
            return []
    
    async def _get_user_preferences(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Get user preferences for personalization"""
        try:
            result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            user_pref = result.scalar_one_or_none()
            
            if user_pref and user_pref.preferences:
                return user_pref.preferences
            
            # Return default preferences
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
                cache_key = f"embedding:{hashlib.md5(message.encode()).hexdigest()}"
                cached = await redis_client.get(cache_key)
                if cached:
                    return np.frombuffer(cached, dtype=np.float32)
            
            # Generate new embedding using the Gemini service
            # Fix: Changed 'texts' parameter to 'text' (singular)
            embedding_result = await gemini_service.generate_embeddings(
                text=message,  # Changed from texts=message
                model=self.embeddings_model
            )
            
            if not embedding_result["success"]:
                logger.error(f"Failed to generate embedding: {embedding_result.get('error')}")
                return None
            
            # Extract the first (and only) embedding from the list
            embeddings = embedding_result.get("embeddings", [])
            if not embeddings:
                logger.error("No embeddings returned")
                return None
            
            embedding_array = np.array(embeddings[0], dtype=np.float32)
            
            # Cache the embedding
            if redis_client:
                await redis_client.set(
                    cache_key,
                    embedding_array.tobytes(),
                    ex=self.cache_ttl
                )
            
            return embedding_array
            
        except Exception as e:
            logger.error(f"Failed to get message embedding: {str(e)}")
            return None

    async def find_similar_conversations(
        self,
        query: str,
        user_id: int,
        db: AsyncSession,
        redis_client: Optional[Redis] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past conversations
        
        Args:
            query: Search query
            user_id: User ID
            db: Database session
            redis_client: Redis client
            limit: Maximum number of conversations
            
        Returns:
            List of similar conversations with metadata
        """
        try:
            # Get query embedding
            query_embedding = await self._get_message_embedding(query, redis_client)
            if query_embedding is None:
                return []
            
            # Get user's chats
            result = await db.execute(
                select(Chat)
                .where(and_(
                    Chat.user_id == user_id,
                    Chat.is_active == True
                ))
                .options(selectinload(Chat.messages))
                .order_by(desc(Chat.updated_at))
                .limit(50)
            )
            chats = result.scalars().all()
            
            # Calculate chat similarities
            similar_chats = []
            for chat in chats:
                if not chat.messages:
                    continue
                
                # Calculate average embedding for chat
                chat_embeddings = []
                for msg in chat.messages[-10:]:  # Last 10 messages
                    if msg.content:
                        embedding = await self._get_message_embedding(msg.content, redis_client)
                        if embedding is not None:
                            chat_embeddings.append(embedding)
                
                if not chat_embeddings:
                    continue
                
                # Average embedding
                avg_embedding = np.mean(chat_embeddings, axis=0)
                
                # Calculate similarity
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    avg_embedding.reshape(1, -1)
                )[0][0]
                
                similar_chats.append({
                    "chat_id": chat.id,
                    "title": chat.title,
                    "similarity_score": float(similarity),
                    "message_count": len(chat.messages),
                    "last_message_at": chat.last_message_at.isoformat() if chat.last_message_at else None,
                    "created_at": chat.created_at.isoformat()
                })
            
            # Sort by similarity and limit
            similar_chats.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similar_chats[:limit]
            
        except Exception as e:
            logger.error(f"Failed to find similar conversations: {str(e)}")
            return []
    
    async def generate_contextual_response(
        self,
        query: str,
        context_messages: List[Dict[str, Any]],
        user_preferences: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate response with context using Gemini
        
        Args:
            query: User's query
            context_messages: Retrieved context messages
            user_preferences: User preferences
            system_prompt: Optional system prompt
            
        Returns:
            Generated response with metadata
        """
        try:
            # Build messages
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Default RAG-aware system prompt
                messages.append({
                    "role": "system",
                    "content": "You are a helpful AI assistant with access to conversation history. "
                              "Use the provided context to give more personalized and relevant responses."
                })
            
            # Add user preferences as context
            if user_preferences:
                pref_prompt = f"User preferences: {json.dumps(user_preferences, indent=2)}"
                messages.append({"role": "system", "content": pref_prompt})
            
            # Add context messages
            if context_messages:
                context_prompt = "Relevant conversation history:\n"
                for ctx in context_messages[:5]:  # Limit to 5 most relevant
                    sender = "User" if ctx["sender_type"] == "USER" else "Assistant"
                    context_prompt += f"{sender}: {ctx['content'][:200]}...\n"
                messages.append({"role": "system", "content": context_prompt})
            
            # Add user query
            messages.append({"role": "user", "content": query})
            
            # Generate response using Gemini
            response = await gemini_service.generate_chat_response(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate contextual response: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def update_embeddings_batch(
        self,
        message_ids: List[int],
        db: AsyncSession,
        redis_client: Optional[Redis] = None
    ) -> Dict[str, Any]:
        """
        Update embeddings for a batch of messages
        
        Args:
            message_ids: List of message IDs
            db: Database session
            redis_client: Redis client
            
        Returns:
            Update statistics
        """
        try:
            # Get messages
            result = await db.execute(
                select(Message).where(Message.id.in_(message_ids))
            )
            messages = result.scalars().all()
            
            success_count = 0
            error_count = 0
            
            for msg in messages:
                if not msg.content:
                    continue
                
                # Generate embedding
                embedding = await self._get_message_embedding(msg.content, redis_client)
                if embedding is not None:
                    success_count += 1
                else:
                    error_count += 1
            
            return {
                "total_messages": len(messages),
                "success_count": success_count,
                "error_count": error_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to update embeddings batch: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def health_check(self) -> bool:
        """Check if RAG service is healthy"""
        try:
            # Test embedding generation using Gemini
            test_embedding = await self._get_message_embedding("Hello, world!")
            return test_embedding is not None
        except Exception as e:
            logger.error(f"RAG health check failed: {str(e)}")
            return False


# Create singleton instance
rag_service = RAGService()

# Export the service
__all__ = ["RAGService", "rag_service"]