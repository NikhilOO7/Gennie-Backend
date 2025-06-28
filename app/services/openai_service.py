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
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Prepare request parameters
            request_params = {
                "model": model or self.chat_model,
                "messages": messages,
                "temperature": temperature or self.default_temperature,
                "max_tokens": max_tokens or self.default_max_tokens,
                "top_p": top_p or self.default_top_p,
                "frequency_penalty": frequency_penalty or self.default_frequency_penalty,
                "presence_penalty": presence_penalty or self.default_presence_penalty,
                "stream": stream,
                "user": user_id,
                **kwargs
            }
            
            # Count input tokens
            input_tokens = self.count_tokens_from_messages(messages)
            
            # Log request details
            logger.info(
                f"OpenAI request started",
                extra={
                    "model": request_params["model"],
                    "input_tokens": input_tokens,
                    "max_tokens": request_params["max_tokens"],
                    "temperature": request_params["temperature"],
                    "user_id": user_id
                }
            )
            
            # Make API call
            if stream:
                return await self._handle_streaming_response(request_params, start_time, input_tokens)
            else:
                return await self._handle_standard_response(request_params, start_time, input_tokens)
        
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(
                f"OpenAI request failed after {processing_time:.2f}s: {str(e)}",
                extra={
                    "error_type": type(e).__name__,
                    "user_id": user_id,
                    "model": model or self.chat_model
                },
                exc_info=True
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _handle_standard_response(
        self, 
        request_params: Dict[str, Any], 
        start_time: datetime, 
        input_tokens: int
    ) -> Dict[str, Any]:
        """Handle standard (non-streaming) response"""
        
        response: ChatCompletion = await self.client.chat.completions.create(**request_params)
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Extract response data
        choice = response.choices[0]
        message_content = choice.message.content
        finish_reason = choice.finish_reason
        
        # Token usage
        usage = response.usage
        output_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else input_tokens + output_tokens
        
        # Log successful response
        logger.info(
            f"OpenAI request completed in {processing_time:.2f}s",
            extra={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "finish_reason": finish_reason,
                "processing_time": processing_time
            }
        )
        
        return {
            "success": True,
            "response": message_content,
            "finish_reason": finish_reason,
            "tokens_used": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens
            },
            "processing_time": processing_time,
            "model": response.model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "raw_response": response.model_dump() if hasattr(response, 'model_dump') else None
        }

    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """Create embeddings for text using OpenAI"""
        try:
            response = await self.client.embeddings.create(
                model=self.embeddings_model,  # or "text-embedding-ada-002"
                input=text
            )
            
            return {
                "success": True,
                "embedding": response.data[0].embedding,
                "model": response.model,
                "usage": response.usage.dict() if response.usage else {}
            }
        except Exception as e:
            logger.error(f"Failed to create embedding: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "embedding": None
            }
    
    async def _handle_streaming_response(
        self, 
        request_params: Dict[str, Any], 
        start_time: datetime, 
        input_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming response"""
        
        accumulated_content = ""
        chunk_count = 0
        
        try:
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                chunk_count += 1
                
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    accumulated_content += content
                    
                    yield {
                        "success": True,
                        "chunk": content,
                        "accumulated_content": accumulated_content,
                        "chunk_number": chunk_count,
                        "is_final": False,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                
                # Check for finish
                if chunk.choices and chunk.choices[0].finish_reason:
                    processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    output_tokens = self.count_tokens(accumulated_content)
                    
                    yield {
                        "success": True,
                        "response": accumulated_content,
                        "finish_reason": chunk.choices[0].finish_reason,
                        "tokens_used": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens
                        },
                        "processing_time": processing_time,
                        "chunk_count": chunk_count,
                        "is_final": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    break
        
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Streaming error after {processing_time:.2f}s: {str(e)}")
            
            yield {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
                "accumulated_content": accumulated_content,
                "chunk_count": chunk_count,
                "is_final": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
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
                    total_tokens += len(self.encoding.encode(message["role"]))
                if "content" in message:
                    total_tokens += len(self.encoding.encode(message["content"]))
            
            # Add 2 tokens for assistant reply priming
            total_tokens += 2
            
            return total_tokens
        
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            # Fallback estimation
            total_text = " ".join([msg.get("content", "") for msg in messages])
            return len(total_text) // 4  # Rough approximation
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            return len(text) // 4  # Rough approximation
    
    async def generate_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate embeddings for text(s)"""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            # Count input tokens
            input_tokens = sum(self.count_tokens(text) for text in texts)
            
            # Make API call
            response: CreateEmbeddingResponse = await self.client.embeddings.create(
                model=model or self.embeddings_model,
                input=texts,
                user=user_id
            )
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Extract embeddings
            embeddings = [data.embedding for data in response.data]
            
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
                "processing_time": processing_time,
                "model": response.model,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Embeddings generation failed: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def moderate_content(
        self, 
        text: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check content for policy violations"""
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
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Content moderation failed: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
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
            
            # Use first few messages to generate title
            context_messages = conversation_messages[:3] if len(conversation_messages) > 3 else conversation_messages
            
            # Build messages for title generation
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation context
            for msg in context_messages:
                messages.append(msg)
            
            messages.append({
                "role": "user", 
                "content": "Based on this conversation, generate a concise title."
            })
            
            # Generate title
            result = await self.generate_chat_response(
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent titles
                max_tokens=20,    # Short response
                model="gpt-3.5-turbo"  # Use faster model for titles
            )
            
            if result["success"]:
                title = result["response"].strip().strip('"\'')
                # Ensure title is within length limit
                if len(title) > max_length:
                    title = title[:max_length-3] + "..."
                
                return {
                    "success": True,
                    "title": title,
                    "processing_time": result["processing_time"],
                    "tokens_used": result["tokens_used"]["total_tokens"]
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
        """Generate a summary of a conversation"""
        
        try:
            system_prompt = f"""Summarize this conversation in {max_length} characters or less. 
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
        """Check if OpenAI service is healthy"""
        try:
            # Simple API call to test connectivity
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0
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

# Create global service instance
openai_service = OpenAIService()

# Export the service
__all__ = ["OpenAIService", "openai_service"]