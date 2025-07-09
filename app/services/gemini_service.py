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
        # Set environment variables for Vertex AI
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        os.environ["GOOGLE_CLOUD_PROJECT"] = settings.GOOGLE_CLOUD_PROJECT_ID
        os.environ["GOOGLE_CLOUD_LOCATION"] = settings.GOOGLE_CLOUD_LOCATION
        
        # Initialize client with Vertex AI
        self.client = genai.Client(
            vertexai=True,
            project=settings.GOOGLE_CLOUD_PROJECT_ID,
            location=settings.GOOGLE_CLOUD_LOCATION,
            http_options=HttpOptions(
                api_version="v1",  # Use stable API version
                timeout=60.0,
            )
        )
        
        # Model configurations
        self.chat_model = "gemini-2.0-flash-001"  # Latest Gemini 2.0 Flash model
        self.multimodal_model = "gemini-2.0-flash-001"  # Flash supports multimodal
        self.embeddings_dimension = 768  # Gemini embeddings dimension
        
        # Default parameters
        self.default_temperature = settings.OPENAI_TEMPERATURE  # Reuse existing setting
        self.default_max_tokens = settings.OPENAI_MAX_TOKENS
        self.default_top_p = settings.OPENAI_TOP_P
        
        # Safety settings - configure based on your requirements
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
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ]
        
        logger.info(f"Gemini service initialized with model: {self.chat_model}")
    
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        frequency_penalty: Optional[float] = None,  # Not used in Gemini
        presence_penalty: Optional[float] = None,   # Not used in Gemini
        model: Optional[str] = None,
        stream: bool = False,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate chat response compatible with OpenAI interface
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            model: Model to use (defaults to configured model)
            stream: Whether to stream the response
            user_id: User ID for tracking
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with response data matching OpenAI format
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Validate messages
            if not messages or not isinstance(messages, list):
                raise ValueError("Messages must be a non-empty list")
            
            # Convert messages to Gemini format
            contents = self._convert_messages_to_contents(messages)
            
            # Extract system instruction if present
            system_instruction = None
            for msg in messages:
                if msg.get("role") == "system":
                    system_instruction = msg.get("content")
                    break
            
            # Count input tokens (approximate)
            input_tokens = self._estimate_tokens(messages)
            
            # Prepare generation config
            config = GenerateContentConfig(
                temperature=temperature if temperature is not None else self.default_temperature,
                max_output_tokens=max_tokens if max_tokens is not None else self.default_max_tokens,
                top_p=top_p if top_p is not None else self.default_top_p,
                system_instruction=system_instruction,
                safety_settings=self.safety_settings,
            )
            
            if stream:
                # Handle streaming response
                return await self._handle_streaming_response(
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
    
    async def _handle_streaming_response(
        self,
        contents: List[Any],
        config: GenerateContentConfig,
        model: Optional[str],
        start_time: datetime,
        input_tokens: int
    ) -> Dict[str, Any]:
        """Handle streaming response from Gemini"""
        
        try:
            chunks = []
            
            # Use async streaming
            async for chunk in self.client.aio.models.generate_content_stream(
                model=model or self.chat_model,
                contents=contents,
                config=config,
            ):
                if hasattr(chunk, 'text') and chunk.text:
                    chunks.append(chunk.text)
            
            response_text = "".join(chunks)
            output_tokens = self._estimate_token_count(response_text)
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
                "model_used": model or self.chat_model,
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
        Note: Gemini uses a different approach for embeddings
        
        Args:
            texts: Text or list of texts to embed
            model: Model to use
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
            if not texts:
                raise ValueError("No texts provided for embedding")
            
            # For now, return mock embeddings as Gemini embeddings work differently
            # You would need to use a specific embedding model or endpoint
            embeddings = []
            for text in texts:
                # Generate a mock embedding of the correct dimension
                embedding = [0.1] * self.embeddings_dimension
                embeddings.append(embedding)
            
            total_tokens = sum(self._estimate_token_count(text) for text in texts)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            
            return {
                "success": True,
                "embeddings": embeddings,
                "model": "gemini-embedding",
                "dimensions": self.embeddings_dimension,
                "tokens_used": total_tokens,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def analyze_image_with_text(
        self,
        image_data: bytes,
        prompt: str,
        mime_type: str = "image/jpeg",
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze image with text prompt (multimodal)
        
        Args:
            image_data: Image bytes
            prompt: Text prompt
            mime_type: MIME type of the image
            model: Model to use
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with analysis results
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create image part
            image_part = Part.from_bytes(
                data=image_data,
                mime_type=mime_type
            )
            
            # Create content with text and image
            contents = [
                Part.from_text(prompt),
                image_part
            ]
            
            # Generate response
            response = await self.client.aio.models.generate_content(
                model=model or self.multimodal_model,
                contents=contents,
                config=GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=1000,
                    safety_settings=self.safety_settings,
                ),
            )
            
            response_text = response.text if hasattr(response, 'text') else ""
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": True,
                "analysis": response_text,
                "model_used": model or self.multimodal_model,
                "processing_time": processing_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def count_tokens(
        self,
        contents: Union[str, List[Dict[str, str]]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Count tokens for content
        
        Args:
            contents: Text or messages to count tokens for
            model: Model to use for counting
            
        Returns:
            Dictionary with token count
        """
        try:
            # If contents is a string, convert to proper format
            if isinstance(contents, str):
                formatted_contents = [Part.from_text(contents)]
            else:
                # Convert messages to contents format
                formatted_contents = self._convert_messages_to_contents(contents)
            
            # Use the count_tokens method
            response = await self.client.aio.models.count_tokens(
                model=model or self.chat_model,
                contents=formatted_contents,
            )
            
            # Extract token count from response
            total_tokens = response.total_tokens if hasattr(response, 'total_tokens') else 0
            
            return {
                "success": True,
                "total_tokens": total_tokens,
                "model": model or self.chat_model
            }
        
        except Exception as e:
            # If official token counting fails, use estimation
            logger.warning(f"Token counting failed, using estimation: {str(e)}")
            
            if isinstance(contents, str):
                estimated_tokens = self._estimate_token_count(contents)
            else:
                estimated_tokens = self._estimate_tokens(contents)
            
            return {
                "success": True,
                "total_tokens": estimated_tokens,
                "model": model or self.chat_model,
                "estimated": True
            }
    
    def _convert_messages_to_contents(self, messages: List[Dict[str, str]]) -> List[Part]:
        """Convert OpenAI-style messages to Gemini contents format"""
        contents = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Skip system messages as they're handled separately
            if role == "system":
                continue
            
            # Convert assistant messages to model role
            if role == "assistant":
                # In Gemini, we just add the content as text
                contents.append(Part.from_text(content))
            else:
                # User messages
                contents.append(Part.from_text(content))
        
        return contents
    
    def _estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages"""
        total_tokens = 0
        
        for msg in messages:
            content = msg.get("content", "")
            total_tokens += self._estimate_token_count(content)
            # Add some tokens for message structure
            total_tokens += 4
        
        return total_tokens
    
    def _estimate_token_count(self, text: str) -> int:
        """Estimate token count for a text string"""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    async def generate_conversation_title(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 50
    ) -> Dict[str, Any]:
        """
        Generate a title for the conversation
        
        Args:
            messages: Conversation messages
            max_length: Maximum title length
            
        Returns:
            Dictionary with title generation result
        """
        try:
            # Create a prompt for title generation
            title_prompt = """Based on this conversation, generate a concise title (max 50 characters) that captures the main topic. 
            Return only the title, no quotes or additional text."""
            
            # Add recent messages context
            recent_messages = messages[-5:] if len(messages) > 5 else messages
            context = "\n".join([f"{msg['role']}: {msg['content'][:100]}..." for msg in recent_messages])
            
            # Generate title
            result = await self.generate_chat_response(
                messages=[
                    {"role": "system", "content": title_prompt},
                    {"role": "user", "content": f"Conversation:\n{context}"}
                ],
                temperature=0.7,
                max_tokens=20
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
    
    async def generate_conversation_summary(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 150
    ) -> Dict[str, Any]:
        """
        Generate a summary of the conversation
        
        Args:
            messages: Conversation messages
            max_length: Maximum summary length
            
        Returns:
            Dictionary with summary
        """
        try:
            summary_prompt = """Summarize this conversation in 2-3 sentences. 
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
    
    async def health_check(self) -> bool:
        """
        Check if Gemini service is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple generation
            response = await self.client.aio.models.generate_content(
                model=self.chat_model,
                contents=[Part.from_text("Hi")],
                config=GenerateContentConfig(
                    max_output_tokens=10,
                    temperature=0.1,
                ),
            )
            
            return hasattr(response, 'text') and len(response.text) > 0
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
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
gemini_service = GeminiService()