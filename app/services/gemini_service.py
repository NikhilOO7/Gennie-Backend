"""
Gemini Service - Google AI Integration with Vertex AI
Using the latest google-genai SDK with async support, streaming, and multimodal capabilities
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime, timezone
import os
from google import genai
from google.genai.types import (
    Part,
    GenerateContentConfig,
    HttpOptions,
    Tool,
    FunctionDeclaration,
    Content,
    HarmCategory,
    HarmBlockThreshold,
    SafetySetting,
)

from app.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    """
    Comprehensive Gemini service using the latest google-genai SDK
    with async patterns, streaming support, and multimodal capabilities
    """
    
    def __init__(self):
        """Initialize Gemini service with configuration"""
        try:
            # Set timeout environment variables for Google libraries
            os.environ["DEFAULT_SOCKET_TIMEOUT"] = "60"
            os.environ["DEFAULT_TIMEOUT"] = "60"
            
            # First, try to use API key if available (simpler, no OAuth2 issues)
            if settings.GEMINI_API_KEY:
                logger.info("Initializing Gemini with API key (Developer API)...")
                
                # Use Gemini Developer API with API key
                os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
                
                api_key = settings.GEMINI_API_KEY.get_secret_value() if hasattr(settings.GEMINI_API_KEY, 'get_secret_value') else settings.GEMINI_API_KEY
                
                self.client = genai.Client(
                    api_key=api_key,
                    http_options=HttpOptions(
                        api_version="v1",
                        timeout=60.0,  # Increased timeout to 60 seconds
                    )
                )
                
                # Set model names for Developer API
                self.chat_model = "gemini-1.5-flash"  # Use 1.5 for Developer API
                self.multimodal_model = "gemini-1.5-flash"
                self.embeddings_model = "text-embedding-004"
                
                logger.info("Successfully initialized Gemini with API key")
                
            elif settings.GOOGLE_CLOUD_PROJECT_ID and os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS or ""):
                logger.info("Initializing Gemini with Vertex AI...")
                
                # Configure environment for Vertex AI authentication
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
                os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
                os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GOOGLE_CLOUD_PROJECT_ID
                os.environ["GOOGLE_CLOUD_LOCATION"] = settings.GOOGLE_CLOUD_LOCATION
                
                # Initialize client with Vertex AI
                self.client = genai.Client(
                    vertexai=True,
                    project=settings.GOOGLE_CLOUD_PROJECT_ID,
                    location=settings.GOOGLE_CLOUD_LOCATION,
                    http_options=HttpOptions(
                        api_version="v1",
                        timeout=60.0,  # Increased timeout to 60 seconds
                    )
                )
                
                # Set model names for Vertex AI
                self.chat_model = "gemini-2.5-flash"
                self.multimodal_model = "gemini-2.5-flash"
                self.embeddings_model = "text-embedding-004"
                
                logger.info(f"Successfully initialized Gemini with Vertex AI in {settings.GOOGLE_CLOUD_LOCATION}")
                
            else:
                # Fallback error message
                error_msg = (
                    "Gemini service requires either:\n"
                    "1. GEMINI_API_KEY for Developer API (recommended), or\n"
                    "2. GOOGLE_CLOUD_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS for Vertex AI\n"
                    "Please set one of these in your .env file."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Common configuration
            self.embeddings_dimension = 768
            self.default_temperature = settings.GEMINI_TEMPERATURE
            self.default_max_tokens = settings.GEMINI_MAX_TOKENS
            self.default_top_p = settings.GEMINI_TOP_P
            
            # Safety settings
            self.safety_settings = [
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
                SafetySetting(
                    category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                ),
            ]
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini service: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources when shutting down"""
        try:
            logger.info("Gemini service cleanup completed")
        except Exception as e:
            logger.error(f"Error during Gemini service cleanup: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Gemini service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # For API key mode, skip health check if not properly initialized
            if not hasattr(self, 'client') or self.client is None:
                logger.warning("Gemini client not initialized, skipping health check")
                return False
            
            # Simple health check with minimal content
            test_content = "Hi"
            
            # Try to generate a simple response with a short timeout
            try:
                # Create a task for the API call
                api_task = asyncio.create_task(
                    self.client.aio.models.generate_content(
                        model=self.chat_model,
                        contents=[test_content],
                        config=GenerateContentConfig(
                            max_output_tokens=5,
                            temperature=0.0,
                            top_p=0.1,
                            top_k=1,
                        ),
                    )
                )
                
                # Wait for the task with timeout
                response = await asyncio.wait_for(api_task, timeout=30.0)
                
                # Check if we got a valid response
                if hasattr(response, 'text'):
                    logger.info("Gemini health check passed")
                    return True
                else:
                    logger.warning("Gemini health check failed: No response text")
                    return False
                    
            except asyncio.TimeoutError:
                logger.error("Gemini health check timed out after 30 seconds")
                # Cancel the task if it's still running
                if not api_task.done():
                    api_task.cancel()
                return False
                
        except Exception as e:
            logger.error(f"Gemini health check failed: {type(e).__name__}: {str(e)}")
            # Don't fail the entire startup for health check failures
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model
        
        Returns:
            Model information dictionary
        """
        return {
            "chat_model": self.chat_model,
            "multimodal_model": self.multimodal_model,
            "embeddings_model": self.embeddings_model,
            "embeddings_dimension": self.embeddings_dimension,
            "location": settings.GOOGLE_CLOUD_LOCATION,
            "project": settings.GOOGLE_CLOUD_PROJECT_ID,
            "api_version": "v1",
            "timeout": 60.0,
            "using_vertex_ai": os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
        }
    
    def _convert_messages_to_contents(self, messages: List[Dict[str, str]]) -> List[Content]:
        """
        Convert OpenAI-style messages to Gemini contents
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            List of Gemini Content objects
        """
        contents = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Map roles
            if role == "system":
                # System messages handled separately in Gemini
                continue
            elif role == "assistant":
                role = "model"
            else:
                role = "user"
            
            # Create content
            contents.append(Content(parts=[Part.from_text(content)], role=role))
        
        return contents
    
    def _extract_system_instruction(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """
        Extract system instruction from messages
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            System instruction if found, None otherwise
        """
        for message in messages:
            if message.get("role") == "system":
                return message.get("content")
        return None
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate total tokens from messages
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Estimated total token count
        """
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return total_chars // 4
    
    async def _handle_streaming_response(
        self,
        contents: List[Content],
        config: GenerateContentConfig,
        model: Optional[str],
        start_time: datetime,
        input_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle streaming response from Gemini
        
        Args:
            contents: Content to generate from
            config: Generation configuration
            model: Model to use
            start_time: Request start time
            input_tokens: Number of input tokens
            
        Yields:
            Response chunks
        """
        try:
            response_text = ""
            chunk_count = 0
            
            async for chunk in self.client.aio.models.generate_content_stream(
                model=model or self.chat_model,
                contents=contents,
                config=config,
            ):
                chunk_count += 1
                chunk_text = chunk.text if hasattr(chunk, 'text') else ""
                response_text += chunk_text
                
                yield {
                    "success": True,
                    "content": chunk_text,
                    "chunk_index": chunk_count,
                    "finish_reason": None,
                    "model_used": model or self.chat_model
                }
            
            # Final chunk with token usage
            output_tokens = self._estimate_token_count(response_text)
            total_tokens = input_tokens + output_tokens
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            yield {
                "success": True,
                "content": "",
                "chunk_index": chunk_count + 1,
                "finish_reason": "stop",
                "tokens_used": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens
                },
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {str(e)}")
            yield {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
        model: Optional[str] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Generate a chat response using Gemini
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            stream: Whether to stream the response
            model: Model to use (optional)
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary or async generator for streaming
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Convert messages to Gemini format
            contents = self._convert_messages_to_contents(messages)
            system_instruction = self._extract_system_instruction(messages)
            
            # Estimate input tokens
            input_tokens = self._estimate_tokens(messages)
            
            # Create generation config
            config = GenerateContentConfig(
                temperature=temperature if temperature is not None else self.default_temperature,
                max_output_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
                top_p=top_p if top_p is not None else self.default_top_p,
                system_instruction=system_instruction,
                safety_settings=self.safety_settings,
            )
            
            # Add thinking configuration for Gemini 2.5 models if enabled
            if settings.GEMINI_ENABLE_THINKING and "2.5" in (model or self.chat_model):
                from google.genai.types import ThinkingConfig
                config.thinking_config = ThinkingConfig(
                    thinking_budget=settings.GEMINI_THINKING_BUDGET,
                    include_thoughts=False  # Don't include thoughts in response
                )
            
            if stream:
                # Handle streaming response
                return self._handle_streaming_response(
                    contents, config, model, start_time, input_tokens
                )
            else:
                # Handle regular response
                response = await self.client.aio.models.generate_content(
                    model=model or self.chat_model,
                    contents=contents,
                    config=config,
                )
                
                # Extract response data
                response_text = response.text if hasattr(response, 'text') else ""
                
                # Calculate tokens (approximate)
                output_tokens = self._estimate_token_count(response_text)
                total_tokens = input_tokens + output_tokens
                
                # Calculate processing time
                processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                logger.info(f"Chat response generated successfully: {total_tokens} tokens in {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "response": response_text,
                    "finish_reason": "stop",  # Gemini doesn't provide finish reasons
                    "tokens_used": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens
                    },
                    "model_used": model or self.chat_model,
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
    
    async def generate_embeddings(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text
        
        Args:
            text: Text or list of texts to embed
            model: Model to use (optional)
            
        Returns:
            Dictionary with embeddings
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Ensure text is a list
            texts = [text] if isinstance(text, str) else text
            
            # Generate embeddings
            response = await self.client.aio.models.embed_content(
                model=model or self.embeddings_model,
                contents=texts,
            )
            
            # Extract embeddings
            embeddings = []
            if hasattr(response, 'embeddings'):
                for embedding in response.embeddings:
                    embeddings.append(embedding.values)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "embeddings": embeddings,
                "model_used": model or self.embeddings_model,
                "dimension": self.embeddings_dimension,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def analyze_multimodal_content(
        self,
        text: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze multimodal content (text + image/video/audio)
        
        Args:
            text: Text prompt
            media_url: URL to media file (GCS URL preferred)
            media_type: MIME type of media
            **kwargs: Additional parameters
            
        Returns:
            Analysis response
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create parts
            parts = [Part.from_text(text)]
            
            if media_url and media_type:
                # Add media part
                parts.append(Part.from_uri(uri=media_url, mime_type=media_type))
            
            # Create content
            contents = [Content(parts=parts, role="user")]
            
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=self.multimodal_model,
                contents=contents,
                config=GenerateContentConfig(
                    temperature=kwargs.get("temperature", 0.7),
                    max_output_tokens=kwargs.get("max_tokens", 1000),
                    safety_settings=self.safety_settings,
                ),
            )
            
            # Extract response
            response_text = response.text if hasattr(response, 'text') else ""
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "analysis": response_text,
                "model_used": self.multimodal_model,
                "media_analyzed": media_url is not None,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Multimodal analysis failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Tool],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response with function calling/tools
        
        Args:
            messages: List of message dictionaries
            tools: List of Tool objects
            **kwargs: Additional parameters
            
        Returns:
            Response with potential tool calls
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Convert messages
            contents = self._convert_messages_to_contents(messages)
            system_instruction = self._extract_system_instruction(messages)
            
            # Create config with tools
            config = GenerateContentConfig(
                temperature=kwargs.get("temperature", self.default_temperature),
                max_output_tokens=kwargs.get("max_tokens", self.default_max_tokens),
                system_instruction=system_instruction,
                tools=tools,
                safety_settings=self.safety_settings,
            )
            
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=kwargs.get("model", self.chat_model),
                contents=contents,
                config=config,
            )
            
            # Extract response and tool calls
            response_text = response.text if hasattr(response, 'text') else ""
            tool_calls = []
            
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call'):
                            tool_calls.append({
                                "name": part.function_call.name,
                                "arguments": dict(part.function_call.args)
                            })
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "response": response_text,
                "tool_calls": tool_calls,
                "model_used": kwargs.get("model", self.chat_model),
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Tool generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def summarize_conversation(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 200
    ) -> Dict[str, Any]:
        """
        Summarize a conversation
        
        Args:
            messages: List of message dictionaries
            max_length: Maximum length of summary
            
        Returns:
            Summary response
        """
        try:
            # Create summarization prompt
            summary_prompt = f"""Summarize this conversation in {max_length} characters or less.
Focus on the main topics discussed and key points. Be concise but comprehensive."""
            
            # Generate summary
            result = await self.generate_chat_response(
                messages=[
                    {"role": "system", "content": summary_prompt},
                    *messages,
                    {"role": "user", "content": "Provide a summary of this conversation."}
                ],
                temperature=0.3,
                max_tokens=100
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
    
    def count_tokens_from_messages(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens from a list of messages (for compatibility)
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Estimated token count
        """
        return self._estimate_tokens(messages)
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text (for compatibility)
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        return self._estimate_token_count(text)

# Create a singleton instance
try:
    gemini_service = GeminiService()
except Exception as e:
    logger.error(f"Failed to create Gemini service instance: {str(e)}")
    # Create a dummy service that will fail health checks but won't crash the app
    class DummyGeminiService:
        async def health_check(self):
            return False
        async def cleanup(self):
            pass
        async def get_model_info(self):
            return {"error": "Service not initialized"}
        async def generate_chat_response(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        async def generate_embeddings(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        async def analyze_multimodal_content(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        async def generate_with_tools(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        async def summarize_conversation(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        def count_tokens_from_messages(self, messages):
            return 0
        def count_tokens(self, text):
            return 0
    
    gemini_service = DummyGeminiService()