import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import logging
import asyncio
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        # Use a lightweight model for development/testing
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2
        
        # In-memory storage for development (replace with Pinecone/Weaviate in production)
        self.vectors = {}  # message_id -> embedding
        self.metadata = {}  # message_id -> metadata
        
        logger.info("Vector service initialized with in-memory storage")
    
    async def store_message_embedding(
        self,
        message_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Store message embedding in vector database"""
        try:
            # Generate embedding
            embedding = await self._generate_embedding(text)
            
            # Store in memory (replace with actual vector DB in production)
            self.vectors[message_id] = embedding
            self.metadata[message_id] = {
                **metadata,
                'text': text,
                'stored_at': datetime.utcnow().isoformat(),
                'text_hash': hashlib.md5(text.encode()).hexdigest()
            }
            
            logger.debug(f"Stored embedding for message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store embedding for message {message_id}: {str(e)}")
            return False
    
    async def find_similar_messages(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Find similar messages using vector search"""
        try:
            if not self.vectors:
                return []
            
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Calculate similarities
            similarities = []
            for msg_id, stored_embedding in self.vectors.items():
                similarity = cosine_similarity(
                    query_embedding.reshape(1, -1),
                    stored_embedding.reshape(1, -1)
                )[0][0]
                
                if similarity >= similarity_threshold:
                    metadata = self.metadata.get(msg_id, {})
                    
                    # Apply filters
                    if user_id and metadata.get('user_id') != user_id:
                        continue
                    if chat_id and metadata.get('chat_id') != chat_id:
                        continue
                    
                    similarities.append({
                        'message_id': msg_id,
                        'similarity_score': float(similarity),
                        'metadata': metadata,
                        'text': metadata.get('text', '')
                    })
            
            # Sort by similarity and return top_k
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar messages: {str(e)}")
            return []
    
    async def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            lambda: self.model.encode(text)
        )
        return embedding
    
    async def delete_message_embedding(self, message_id: str) -> bool:
        """Delete message embedding"""
        try:
            if message_id in self.vectors:
                del self.vectors[message_id]
            if message_id in self.metadata:
                del self.metadata[message_id]
            logger.debug(f"Deleted embedding for message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete embedding for message {message_id}: {str(e)}")
            return False
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get vector storage statistics"""
        return {
            'total_vectors': len(self.vectors),
            'embedding_dimension': self.embedding_dimension,
            'model_name': 'all-MiniLM-L6-v2',
            'storage_type': 'in_memory'
        }

# Create singleton instance
vector_service = VectorService()