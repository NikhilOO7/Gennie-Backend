from app.services.rag_service import RAGService
from app.services.vector_service import vector_service
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedRAGService(RAGService):
    """Enhanced RAG service with vector similarity search"""
    
    def __init__(self):
        super().__init__()
        self.vector_service = vector_service
        self.vector_weight = 0.7  # Weight for vector similarity
        self.temporal_weight = 0.3  # Weight for temporal relevance
    
    async def get_context_for_query(
        self,
        query: str,
        user_id: int,
        chat_id: Optional[int] = None,
        db: Optional[Any] = None,
        redis_client: Optional[Any] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Enhanced context retrieval with vector search"""
        try:
            start_time = datetime.now()
            
            # 1. Vector similarity search
            similar_messages = await self.vector_service.find_similar_messages(
                query=query,
                top_k=limit * 2,  # Get more candidates for filtering
                similarity_threshold=0.6,
                user_id=user_id,
                chat_id=chat_id
            )
            
            # 2. Fallback to traditional RAG if not enough vector results
            if len(similar_messages) < limit:
                traditional_context = await super().get_context_for_query(
                    query, user_id, chat_id, db, redis_client, limit
                )
                
                # Merge results
                vector_message_ids = {msg['message_id'] for msg in similar_messages}
                for msg in traditional_context.get('context_messages', []):
                    if str(msg.get('id')) not in vector_message_ids:
                        similar_messages.append({
                            'message_id': str(msg['id']),
                            'similarity_score': 0.5,  # Default score for traditional results
                            'text': msg.get('content', ''),
                            'metadata': {
                                'sender_type': msg.get('sender_type'),
                                'created_at': msg.get('created_at'),
                                'user_id': user_id
                            }
                        })
            
            # 3. Apply temporal scoring
            temporal_scored = await self._apply_temporal_scoring(similar_messages)
            
            # 4. Final ranking and selection
            final_context = self._rank_and_select_context(temporal_scored, limit)
            
            # 5. Build context text
            context_text = self._build_context_text(final_context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'context_messages': final_context,
                'context_text': context_text,
                'total_retrieved': len(similar_messages),
                'vector_matches': len([m for m in similar_messages if m['similarity_score'] > 0.6]),
                'processing_time_ms': processing_time * 1000,
                'method': 'vector_enhanced_rag'
            }
            
        except Exception as e:
            logger.error(f"Enhanced RAG context retrieval failed: {str(e)}")
            # Fallback to traditional RAG
            return await super().get_context_for_query(
                query, user_id, chat_id, db, redis_client, limit
            )
    
    async def _apply_temporal_scoring(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply temporal relevance scoring"""
        now = datetime.now()
        
        for msg in messages:
            try:
                created_at = msg['metadata'].get('created_at')
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                elif not isinstance(created_at, datetime):
                    created_at = now  # Default to now if parsing fails
                
                # Calculate time decay (messages lose relevance over time)
                time_diff_hours = (now - created_at).total_seconds() / 3600
                temporal_score = max(0, 1 - (time_diff_hours / (24 * 7)))  # Decay over a week
                
                # Combine vector similarity with temporal relevance
                original_score = msg['similarity_score']
                combined_score = (
                    self.vector_weight * original_score +
                    self.temporal_weight * temporal_score
                )
                
                msg['combined_score'] = combined_score
                msg['temporal_score'] = temporal_score
                
            except Exception as e:
                logger.warning(f"Failed to apply temporal scoring to message: {str(e)}")
                msg['combined_score'] = msg['similarity_score']
                msg['temporal_score'] = 0.5
        
        return messages
    
    def _rank_and_select_context(self, messages: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """Rank messages by combined score and select top candidates"""
        # Sort by combined score
        ranked_messages = sorted(
            messages,
            key=lambda x: x.get('combined_score', x['similarity_score']),
            reverse=True
        )
        
        # Select top messages
        selected = ranked_messages[:limit]
        
        # Format for consistent interface
        formatted_messages = []
        for msg in selected:
            formatted_messages.append({
                'id': msg['message_id'],
                'content': msg['text'],
                'sender_type': msg['metadata'].get('sender_type', 'user'),
                'created_at': msg['metadata'].get('created_at'),
                'similarity_score': msg['similarity_score'],
                'temporal_score': msg.get('temporal_score', 0),
                'combined_score': msg.get('combined_score', msg['similarity_score'])
            })
        
        return formatted_messages
    
    def _build_context_text(self, context_messages: List[Dict[str, Any]]) -> str:
        """Build context text from selected messages"""
        if not context_messages:
            return ""
        
        context_parts = []
        for msg in context_messages:
            sender = msg.get('sender_type', 'user').title()
            content = msg.get('content', '').strip()
            if content:
                context_parts.append(f"{sender}: {content}")
        
        return "\n".join(context_parts)

# Create enhanced instance
enhanced_rag_service = EnhancedRAGService()