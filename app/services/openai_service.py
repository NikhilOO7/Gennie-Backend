import openai
import asyncio
from typing import List, Dict, Optional, Any
import json
import time
from datetime import datetime
import logging

from app.core.config import settings
from app.core.database import get_redis

logger = logging.getLogger(__name__)

class OpenAIService:
    """Service for handling OpenAI API interactions"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.openai_temperature
        self.max_tokens = settings.openai_max_tokens
        
    async def test_connection(self) -> bool:
        """Test OpenAI API connection"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate AI response using OpenAI"""
        try:
            start_time = time.time()
            
            # Use custom or default settings
            temp = temperature or self.temperature
            tokens = max_tokens or self.max_tokens
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
                user=str(user_id) if user_id else None
            )
            
            processing_time = time.time() - start_time
            
            # Extract response data
            choice = response.choices[0]
            content = choice.message.content
            
            return {
                "response": content,
                "model": self.model,
                "tokens_used": response.usage.total_tokens,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "processing_time": processing_time,
                "finish_reason": choice.finish_reason,
                "temperature": temp,
                "max_tokens": tokens
            }
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"AI service error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI service: {e}")
            raise Exception(f"AI service unavailable: {str(e)}")
    
    async def generate_conversation_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        system_prompt: str = None,
        user_preferences: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate response for conversation with context"""
        
        # Build message history
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            # Default system prompt
            messages.append({
                "role": "system", 
                "content": "You are a helpful, friendly AI assistant. Provide thoughtful and engaging responses."
            })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Keep last 10 messages for context
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Apply user preferences
        temperature = self.temperature
        max_tokens = self.max_tokens
        
        if user_preferences:
            if user_preferences.get("temperature"):
                temperature = user_preferences["temperature"]
            if user_preferences.get("max_tokens"):
                max_tokens = user_preferences["max_tokens"]
        
        # Generate response
        return await self.generate_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def generate_chat_title(self, messages: List[str]) -> str:
        """Generate a title for a chat based on messages"""
        try:
            # Take first few messages to generate title
            conversation_sample = " ".join(messages[:3])
            
            prompt = f"""Generate a short, descriptive title (max 6 words) for this conversation:

{conversation_sample}

Title:"""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=20
            )
            
            title = response.choices[0].message.content.strip()
            return title[:50]  # Limit title length
            
        except Exception as e:
            logger.error(f"Error generating chat title: {e}")
            return "New Chat"
    
    async def analyze_sentiment_with_ai(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI (backup to VADER)"""
        try:
            prompt = f"""Analyze the sentiment and emotion of this text. Respond with JSON only:

Text: "{text}"

Provide response in this exact format:
{{
    "sentiment": "positive/negative/neutral",
    "emotion": "joy/sadness/anger/fear/surprise/disgust/neutral",
    "confidence": 0.95,
    "intensity": 0.8
}}"""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=100
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error in AI sentiment analysis: {e}")
            return {
                "sentiment": "neutral",
                "emotion": "neutral", 
                "confidence": 0.5,
                "intensity": 0.5
            }
    
    async def enhance_prompt_with_context(
        self,
        base_prompt: str,
        user_context: Dict[str, Any] = None,
        conversation_context: List[str] = None
    ) -> str:
        """Enhance prompt with user and conversation context"""
        
        enhanced_prompt = base_prompt
        
        # Add user context
        if user_context:
            context_info = []
            if user_context.get("conversation_style"):
                context_info.append(f"Conversation style: {user_context['conversation_style']}")
            if user_context.get("interests"):
                context_info.append(f"User interests: {', '.join(user_context['interests'])}")
            if user_context.get("preferred_response_length"):
                context_info.append(f"Preferred response length: {user_context['preferred_response_length']}")
            
            if context_info:
                enhanced_prompt += f"\n\nUser context: {'; '.join(context_info)}"
        
        # Add conversation context
        if conversation_context:
            recent_context = conversation_context[-3:]  # Last 3 exchanges
            if recent_context:
                enhanced_prompt += f"\n\nRecent conversation context: {'; '.join(recent_context)}"
        
        return enhanced_prompt

# Global service instance
openai_service = OpenAIService()