"""
OpenAI Service - Comprehensive AI Integration
with async support, error handling, and modern patterns
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime, timezone
import tiktoken
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types import CreateEmbeddingResponse

from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Comprehensive OpenAI service with modern async patterns and error handling
    """
    
    def __init__(self):
        """Initialize OpenAI service with configuration"""
        self.client = AsyncOpenAI(
            api_key=settings.get_openai_api_key(),
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES
        )
        
        # Model configurations
        self.chat_model = settings.OPENAI_MODEL
        self.embeddings_model = settings.EMBEDDINGS_MODEL
        
        # Default parameters
        self.default_temperature = settings.OPENAI_TEMPERATURE
        self.default_max_tokens = settings.OPENAI_MAX_TOKENS
        self.default_top_p = settings.OPENAI_TOP_P
        self.default_frequency_penalty = settings.OPENAI_FREQUENCY_PENALTY
        self.default_presence_penalty = settings.OPENAI_PRESENCE_PENALTY
        
        # Token encoding for counting
        try:
            self.encoding = tiktoken.encoding_for_model(self.chat_model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        logger.info(f"OpenAI service initialized with model: {self.chat_model}")
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None,
        model: Optional[str] = None,
        stream: bool = False,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate chat response with comprehensive error handling and token counting
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2 to 2)
            presence_penalty: Presence penalty (-2 to 2)
            model: Model to use (defaults to configured model)
            stream: Whether to stream the response
            user_id: User ID for tracking
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with response data
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate messages
            if not messages or not isinstance(messages, list):
                raise ValueError("Messages must be a non-empty list")
            
            # Count input tokens
            input_tokens = self.count_tokens_from_messages(messages)
            
            # Prepare parameters
            params = {
                "model": model or self.chat_model,
                "messages": messages,
                "temperature": temperature if temperature is not None else self.default_temperature,
                "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
                "top_p": top_p if top_p is not None else self.default_top_p,
                "frequency_penalty": frequency_penalty if frequency_penalty is not None else self.default_frequency_penalty,
                "presence_penalty": presence_penalty if presence_penalty is not None else self.default_presence_penalty,
                "stream": stream,
            }
            
            # Add optional parameters
            if user_id:
                params["user"] = str(user_id)
            
            # Add any additional kwargs
            params.update(kwargs)
            
            logger.info(f"Generating chat response for user {user_id} with {len(messages)} messages")
            
            if stream:
                # Handle streaming response
                return await self._handle_streaming_response(params, start_time, input_tokens)
            else:
                # Handle regular response
                response = await self.client.chat.completions.create(**params)
                
                # Extract response data
                response_text = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason
                
                # Calculate tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens
                
                # Calculate processing time
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                logger.info(f"Chat response generated successfully: {total_tokens} tokens in {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "response": response_text,
                    "finish_reason": finish_reason,
                    "tokens_used": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens
                    },
                    "model_used": response.model,
                    "processing_time": processing_time,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        except Exception as e:
            error_message = f"Chat generation failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _handle_streaming_response(
        self,
        params: Dict[str, Any],
        start_time: datetime,
        input_tokens: int
    ) -> Dict[str, Any]:
        """Handle streaming response from OpenAI"""
        
        try:
            stream = await self.client.chat.completions.create(**params)
            
            chunks = []
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    chunks.append(chunk.choices[0].delta.content)
            
            response_text = "".join(chunks)
            output_tokens = self.count_tokens(response_text)
            total_tokens = input_tokens + output_tokens
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "response": response_text,
                "tokens_used": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                },
                "model_used": params["model"],
                "processing_time": processing_time,
                "stream": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Streaming response failed: {str(e)}", exc_info=True)
            raise
    
    async def generate_embeddings(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text(s)
        
        Args:
            texts: Text or list of texts to embed
            model: Model to use (defaults to configured embeddings model)
            user_id: User ID for tracking
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with embedding data
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            # Validate input
            if not texts or not all(isinstance(t, str) for t in texts):
                raise ValueError("Text must be a string or list of strings")
            
            # Count input tokens
            input_tokens = sum(self.count_tokens(text) for text in texts)
            
            # Generate embeddings
            response = await self.client.embeddings.create(
                input=texts,
                model=model or self.embeddings_model,
                user=user_id if user_id else None,
                **kwargs
            )
            
            # Extract embeddings
            embeddings = [data.embedding for data in response.data]
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"Generated embeddings for {len(texts)} texts in {processing_time:.2f}s",
                extra={
                    "text_count": len(texts),
                    "input_tokens": input_tokens,
                    "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                    "processing_time": processing_time
                }
            )
            
            return {
                "success": True,
                "embeddings": embeddings,
                "input_tokens": input_tokens,
                "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                "model_used": response.model,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            error_message = f"Embedding generation failed: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """Create embeddings for text using OpenAI (backward compatibility)"""
        result = await self.generate_embeddings(text)
        
        if result["success"]:
            return {
                "success": True,
                "embedding": result["embeddings"][0] if result["embeddings"] else None,
                "model": result["model_used"],
                "usage": {"total_tokens": result["input_tokens"]}
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "embedding": None
            }
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            if not text:
                return 0
            
            if self.encoding:
                return len(self.encoding.encode(text))
            else:
                # Fallback estimation (roughly 4 characters per token)
                return len(text) // 4
        
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}, using estimation")
            return len(text) // 4
    
    def count_tokens_from_messages(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a list of messages"""
        try:
            # This is an approximation - actual token counting for chat models is more complex
            total_tokens = 0
            
            for message in messages:
                # 4 tokens per message for metadata
                total_tokens += 4
                
                # Add tokens for role and content
                if "role" in message:
                    total_tokens += self.count_tokens(message["role"])
                if "content" in message:
                    total_tokens += self.count_tokens(message["content"])
            
            # Add 2 tokens for assistant reply priming
            total_tokens += 2
            
            return total_tokens
        
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            # Fallback estimation
            total_text = " ".join([msg.get("content", "") for msg in messages])
            return len(total_text) // 4
    
    async def moderate_content(
        self,
        text: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check content for policy violations
        
        Args:
            text: Text to moderate
            user_id: User ID for tracking
            
        Returns:
            Dictionary with moderation results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            response = await self.client.moderations.create(
                input=text,
                user=user_id
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            moderation = response.results[0]
            
            return {
                "success": True,
                "flagged": moderation.flagged,
                "categories": moderation.categories.model_dump() if hasattr(moderation.categories, 'model_dump') else dict(moderation.categories),
                "category_scores": moderation.category_scores.model_dump() if hasattr(moderation.category_scores, 'model_dump') else dict(moderation.category_scores),
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Content moderation failed: {str(e)}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def generate_title(
        self,
        conversation_messages: List[Dict[str, str]],
        max_length: int = 50
    ) -> Dict[str, Any]:
        """Generate a title for a conversation"""
        
        try:
            # Create a prompt for title generation
            system_prompt = f"""Generate a concise, descriptive title for this conversation. 
            The title should be {max_length} characters or less and capture the main topic or theme.
            Respond with only the title, no quotes or additional text."""
            
            # Build messages for title generation
            title_messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add a summary of the conversation
            if len(conversation_messages) > 0:
                conversation_summary = "\n".join([
                    f"{msg['role']}: {msg['content'][:100]}..."
                    for msg in conversation_messages[:5]
                ])
                title_messages.append({
                    "role": "user",
                    "content": f"Generate a title for this conversation:\n{conversation_summary}"
                })
            
            # Generate title
            result = await self.generate_chat_response(
                messages=title_messages,
                temperature=0.7,
                max_tokens=20,
                model="gpt-3.5-turbo"
            )
            
            if result["success"]:
                title = result["response"].strip()
                if len(title) > max_length:
                    title = title[:max_length-3] + "..."
                
                return {
                    "success": True,
                    "title": title,
                    "processing_time": result["processing_time"]
                }
            else:
                return result
        
        except Exception as e:
            logger.error(f"Title generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 200
    ) -> Dict[str, Any]:
        """Summarize a conversation"""
        
        try:
            # Create prompt for summarization
            system_prompt = """You are a helpful assistant that creates concise summaries.
            Focus on the main topics discussed and key points. Be concise but comprehensive."""
            
            # Build messages for summarization
            summary_messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation messages
            summary_messages.extend(messages)
            
            summary_messages.append({
                "role": "user",
                "content": "Provide a summary of this conversation."
            })
            
            # Generate summary
            result = await self.generate_chat_response(
                messages=summary_messages,
                temperature=0.3,
                max_tokens=100,
                model="gpt-3.5-turbo"
            )
            
            if result["success"]:
                summary = result["response"].strip()
                if len(summary) > max_length:
                    summary = summary[:max_length-3] + "..."
                
                return {
                    "success": True,
                    "summary": summary,
                    "processing_time": result["processing_time"],
                    "tokens_used": result["tokens_used"]["total_tokens"]
                }
            else:
                return result
        
        except Exception as e:
            logger.error(f"Conversation summarization failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple completion
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            
            return response.choices[0].message.content is not None
        
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models"""
        try:
            # Note: This would require the models endpoint which might not be available
            # For now, return configured model info
            return {
                "chat_model": self.chat_model,
                "embeddings_model": self.embeddings_model,
                "default_temperature": self.default_temperature,
                "default_max_tokens": self.default_max_tokens,
                "encoding": self.encoding.name if self.encoding else "unknown"
            }
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {"error": str(e)}
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            "service_name": "OpenAI",
            "chat_model": self.chat_model,
            "embeddings_model": self.embeddings_model,
            "timeout": settings.OPENAI_TIMEOUT,
            "max_retries": settings.OPENAI_MAX_RETRIES,
            "default_parameters": {
                "temperature": self.default_temperature,
                "max_tokens": self.default_max_tokens,
                "top_p": self.default_top_p,
                "frequency_penalty": self.default_frequency_penalty,
                "presence_penalty": self.default_presence_penalty
            }
        }
    
    async def cleanup(self) -> None:
        """
        Cleanup OpenAI service resources
        Called during application shutdown
        """
        try:
            logger.info("Starting OpenAI service cleanup...")
            
            # Close any pending async operations
            if hasattr(self.client, '_client'):
                await self.client._client.aclose()
            
            # Clear any caches or temporary data
            self.encoding = None
            
            logger.info("OpenAI service cleanup completed")
        except Exception as e:
            logger.error(f"Error during OpenAI service cleanup: {str(e)}")
            # Don't raise - we want shutdown to continue
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.cleanup()

# Create global service instance
openai_service = OpenAIService()

# Export the service
__all__ = ["OpenAIService", "openai_service"]