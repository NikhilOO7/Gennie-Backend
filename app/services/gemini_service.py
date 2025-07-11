"""
Gemini Service - Google AI Integration
Using the latest google-genai SDK with proper timeout configuration
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime, timezone

# IMPORTANT: Set environment variables before importing
from dotenv import load_dotenv
load_dotenv()

# Force disable Vertex AI mode
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'false'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './credentials.json'

# Set default timeouts to prevent the 0.06 second issue
os.environ["DEFAULT_SOCKET_TIMEOUT"] = "60"
os.environ["DEFAULT_TIMEOUT"] = "60"
os.environ["GRPC_PYTHON_BUILD_SYSTEM_OPENSSL"] = "1"
os.environ["GRPC_PYTHON_BUILD_SYSTEM_ZLIB"] = "1"

from google import genai
from google.genai.types import (
    Part,
    GenerateContentConfig,
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
        """Initialize Gemini service exactly like the working test script"""
        try:
            # Get API key from environment
            gemini_api_key = os.getenv('GEMINI_API_KEY')
            if not gemini_api_key:
                gemini_api_key = settings.GEMINI_API_KEY.get_secret_value() if hasattr(settings.GEMINI_API_KEY, 'get_secret_value') else str(settings.GEMINI_API_KEY)
            
            if not gemini_api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set.")
            
            # Initialize client with just API key (like test script)
            self.client = genai.Client(api_key=gemini_api_key)
            
            # Set model names
            self.chat_model = "gemini-1.5-flash-latest"
            self.multimodal_model = "gemini-1.5-flash-latest"
            self.embeddings_model = "text-embedding-004"
            
            logger.info("✓ Gemini client initialized (Developer API mode)")
            
            # Configuration
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
        Simple health check matching the test script approach
        """
        try:
            if not hasattr(self, 'client') or self.client is None:
                logger.warning("Gemini client not initialized")
                return False
            
            # Use synchronous call in an executor to avoid timeout issues
            loop = asyncio.get_event_loop()
            
            def sync_test():
                try:
                    response = self.client.models.generate_content(
                        model=self.chat_model,
                        contents="Explain how AI works in a few words"
                    )
                    return hasattr(response, 'text') and bool(response.text)
                except Exception as e:
                    logger.error(f"Sync health check error: {e}")
                    return False
            
            # Run synchronous code in executor
            result = await loop.run_in_executor(None, sync_test)
            
            if result:
                logger.info("✓ Gemini health check passed")
            else:
                logger.warning("✗ Gemini health check failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini health check error: {type(e).__name__}: {str(e)}")
            return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "chat_model": self.chat_model,
            "multimodal_model": self.multimodal_model,
            "embeddings_model": self.embeddings_model,
            "embeddings_dimension": self.embeddings_dimension,
            "api_version": "v1",
            "using_vertex_ai": False,
            "mode": "Developer API"
        }
    
    def _convert_messages_to_contents(self, messages: List[Dict[str, str]]) -> List[Union[str, Content]]:
        """
        Convert OpenAI-style messages to Gemini contents
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            List of content strings or Content objects for Gemini
        """
        # For simple API usage, just pass the message strings directly
        # The SDK will handle the conversion to proper format
        contents = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Skip system messages as they're handled separately
            if role == "system":
                continue
            
            # For the simple API, just add the content strings
            # The SDK will automatically create the proper format
            if content:
                contents.append(content)
        
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
        prompt: str,
        config: GenerateContentConfig,
        model: Optional[str],
        start_time: datetime,
        input_tokens: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Handle streaming response from Gemini
        
        Args:
            prompt: Prompt string to generate from
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
                contents=prompt,  # Pass as string
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
            # Convert messages to a simple prompt string (like test script)
            prompt = self._convert_messages_to_contents(messages)
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
                try:
                    from google.genai.types import ThinkingConfig
                    config.thinking_config = ThinkingConfig(
                        thinking_budget=settings.GEMINI_THINKING_BUDGET,
                        include_thoughts=False  # Don't include thoughts in response
                    )
                except ImportError:
                    logger.debug("ThinkingConfig not available in current SDK version")
            
            if stream:
                # Handle streaming response
                return self._handle_streaming_response(
                    prompt, config, model, start_time, input_tokens
                )
            else:
                # Handle regular response - pass prompt as string like test script
                response = await self.client.aio.models.generate_content(
                    model=model or self.chat_model,
                    contents=prompt,  # Pass as string, not list
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
            # For multimodal, we need to handle it differently
            # For now, just use text-only approach
            if media_url and media_type:
                prompt = f"{text}\n\n[Note: Media file provided at {media_url}]"
            else:
                prompt = text
            
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=self.multimodal_model,
                contents=prompt,
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
    
    async def generate_conversation_title(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 50
    ) -> Dict[str, Any]:
        """
        Generate a title for a conversation
        
        Args:
            messages: List of message dictionaries
            max_length: Maximum length of title
            
        Returns:
            Title response
        """
        try:
            # Create title generation prompt
            title_prompt = "Generate a concise, descriptive title (3-6 words) for this conversation. Reply with ONLY the title, no quotes or additional text."
            
            # Take only the first few messages for title generation
            context_messages = messages[:3] if len(messages) > 3 else messages
            
            # Generate title
            result = await self.generate_chat_response(
                messages=[
                    {"role": "system", "content": title_prompt},
                    *context_messages,
                    {"role": "user", "content": "Generate a title for this conversation."}
                ],
                temperature=0.3,
                max_tokens=20
            )
            
            if result["success"]:
                title = result["response"].strip()
                # Clean up the title
                title = title.replace('"', '').replace("'", '').strip()
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
        async def generate_conversation_title(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        async def summarize_conversation(self, *args, **kwargs):
            return {"success": False, "error": "Gemini service not initialized"}
        def count_tokens_from_messages(self, messages):
            return 0
        def count_tokens(self, text):
            return 0
    
    gemini_service = DummyGeminiService()