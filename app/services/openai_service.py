import openai
from typing import Dict, List, Optional, Any
import logging
import asyncio
from datetime import datetime, timezone
import json

from app.config import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Modern OpenAI service with comprehensive chat functionality
    """
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = settings.OPENAI_MODEL
        self.default_temperature = settings.OPENAI_TEMPERATURE
        self.default_max_tokens = settings.OPENAI_MAX_TOKENS
        self.embeddings_model = settings.EMBEDDINGS_MODEL
        
    async def generate_response(
        self,
        message: str,
        context: List[Dict[str, Any]] = None,
        chat_settings: Dict[str, Any] = None,
        emotion_data: Dict[str, Any] = None,
        personalization_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate AI response with context and personalization
        """
        try:
            # Prepare settings
            model = chat_settings.get("model", self.default_model) if chat_settings else self.default_model
            temperature = chat_settings.get("temperature", self.default_temperature) if chat_settings else self.default_temperature
            max_tokens = chat_settings.get("max_tokens", self.default_max_tokens) if chat_settings else self.default_max_tokens
            system_prompt = chat_settings.get("system_prompt") if chat_settings else None
            
            # Build messages array
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                # Default system prompt with personalization
                system_content = self._build_system_prompt(emotion_data, personalization_data)
                messages.append({"role": "system", "content": system_content})
            
            # Add conversation context
            if context:
                for ctx_msg in context[-10:]:  # Limit context to last 10 messages
                    role = "user" if ctx_msg.get("role") == "user" else "assistant"
                    messages.append({
                        "role": role,
                        "content": ctx_msg.get("content", "")
                    })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            # Extract response
            ai_response = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            logger.info(f"OpenAI response generated successfully. Tokens used: {usage['total_tokens']}")
            
            return {
                "response": ai_response,
                "usage": usage,
                "model": model,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except openai.RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {str(e)}")
            return {
                "response": "I'm experiencing high demand right now. Please try again in a moment.",
                "error": "rate_limit",
                "usage": {}
            }
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return {
                "response": "I'm having trouble connecting to my AI service. Please try again.",
                "error": "api_error",
                "usage": {}
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI service: {str(e)}")
            return {
                "response": "I encountered an unexpected error. Please try again.",
                "error": "unexpected_error",
                "usage": {}
            }
    
    async def generate_conversation_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of the conversation
        """
        try:
            # Prepare conversation text
            conversation_text = ""
            for msg in messages:
                role = "User" if msg.get("role") == "user" else "Assistant"
                conversation_text += f"{role}: {msg.get('content', '')}\n"
            
            if len(conversation_text) > 8000:  # Truncate if too long
                conversation_text = conversation_text[-8000:]
            
            # Create summary prompt
            summary_prompt = f"""
            Please analyze this conversation and provide:
            1. A concise summary (2-3 sentences)
            2. Key topics discussed (as a list)
            3. Overall tone/sentiment

            Conversation:
            {conversation_text}
            
            Please respond in JSON format with keys: summary, key_topics, tone
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse response
            summary_text = response.choices[0].message.content
            try:
                summary_data = json.loads(summary_text)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                summary_data = {
                    "summary": summary_text,
                    "key_topics": [],
                    "tone": "neutral"
                }
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {str(e)}")
            return {
                "summary": "Unable to generate summary",
                "key_topics": [],
                "tone": "neutral"
            }
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embeddings_model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return []
    
    async def moderate_content(self, text: str) -> Dict[str, Any]:
        """
        Check content for policy violations
        """
        try:
            response = await self.client.moderations.create(input=text)
            moderation = response.results[0]
            
            return {
                "flagged": moderation.flagged,
                "categories": moderation.categories,
                "category_scores": moderation.category_scores
            }
            
        except Exception as e:
            logger.error(f"Error in content moderation: {str(e)}")
            return {"flagged": False, "categories": {}, "category_scores": {}}
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI service is healthy
        """
        try:
            # Simple API call to test connectivity
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            return True
            
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return False
    
    def _build_system_prompt(
        self, 
        emotion_data: Optional[Dict[str, Any]] = None, 
        personalization_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build dynamic system prompt based on context
        """
        base_prompt = """You are an intelligent and helpful AI assistant. You provide thoughtful, accurate, and engaging responses while maintaining a conversational tone."""
        
        # Add emotion-aware instructions
        if emotion_data:
            compound_score = emotion_data.get("compound", 0)
            if compound_score < -0.3:
                base_prompt += " The user seems to be feeling negative or upset. Please respond with empathy and try to be supportive."
            elif compound_score > 0.3:
                base_prompt += " The user seems to be in a positive mood. Feel free to match their energy and enthusiasm."
        
        # Add personalization
        if personalization_data:
            interests = personalization_data.get("interests", [])
            if interests:
                base_prompt += f" The user has expressed interest in: {', '.join(interests)}. You can reference these topics when relevant."
            
            response_style = personalization_data.get("response_style")
            if response_style == "detailed":
                base_prompt += " Provide detailed, comprehensive responses."
            elif response_style == "concise":
                base_prompt += " Keep responses concise and to the point."
        
        return base_prompt
    
    async def generate_title_suggestion(self, first_message: str) -> str:
        """
        Generate a title for a chat based on the first message
        """
        try:
            prompt = f"Generate a short, descriptive title (max 5 words) for a conversation that starts with: '{first_message}'"
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=20
            )
            
            title = response.choices[0].message.content.strip().replace('"', '')
            return title if len(title) <= 50 else title[:47] + "..."
            
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            return "New Conversation"

# Create singleton instance
openai_service = OpenAIService()