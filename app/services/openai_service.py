import openai
from typing import List, Dict, Any, Optional
import json
import asyncio
from app.config import settings

class OpenAIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL or "gpt-3.5-turbo"
    
    async def generate_response(
        self,
        message: str,
        context: List[Dict] = None,
        emotion_data: Dict[str, Any] = None,
        personalization: Dict[str, Any] = None,
        system_prompt: str = None
    ) -> str:
        """Generate AI response with context and personalization"""
        try:
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": self._get_default_system_prompt(emotion_data, personalization)})
            
            # Add conversation context
            if context:
                messages.extend(context)
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return "I'm having trouble generating a response right now. Please try again."
    
    async def generate_summary(self, conversation_text: str) -> str:
        """Generate conversation summary"""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Summarize the following conversation in 2-3 sentences, capturing the main topics and tone."},
                    {"role": "user", "content": conversation_text}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Summary generation error: {e}")
            return "Unable to generate summary at this time."
    
    async def extract_topics(self, conversation_text: str) -> List[str]:
        """Extract key topics from conversation"""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract 3-5 key topics from this conversation. Return as a JSON array of strings."},
                    {"role": "user", "content": conversation_text}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            topics_json = response.choices[0].message.content.strip()
            topics = json.loads(topics_json)
            return topics if isinstance(topics, list) else []
            
        except Exception as e:
            print(f"Topic extraction error: {e}")
            return ["general conversation"]
    
    async def analyze_emotion_with_ai(self, text: str) -> Dict[str, Any]:
        """Use AI to analyze emotion (as backup/enhancement)"""
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Analyze the emotion in this text. Return JSON with 'emotion' (primary emotion), 'intensity' (0-1), and 'sentiment' (positive/negative/neutral)."},
                    {"role": "user", "content": text}
                ],
                max_tokens=50,
                temperature=0.1
            )
            
            emotion_json = response.choices[0].message.content.strip()
            return json.loads(emotion_json)
            
        except Exception as e:
            print(f"AI emotion analysis error: {e}")
            return {"emotion": "neutral", "intensity": 0.5, "sentiment": "neutral"}
    
    def _get_default_system_prompt(self, emotion_data: Dict = None, personalization: Dict = None) -> str:
        """Generate dynamic system prompt based on context"""
        prompt = "You are a helpful, empathetic AI assistant. "
        
        if emotion_data:
            emotion = emotion_data.get('emotion', 'neutral')
            if emotion in ['sad', 'angry', 'frustrated']:
                prompt += "The user seems to be experiencing some difficult emotions. Be extra supportive and understanding. "
            elif emotion in ['happy', 'excited', 'joyful']:
                prompt += "The user seems to be in a positive mood. Match their energy while being helpful. "
        
        if personalization:
            response_style = personalization.get('response_style', 'balanced')
            if response_style == 'formal':
                prompt += "Maintain a formal, professional tone. "
            elif response_style == 'casual':
                prompt += "Use a casual, friendly tone. "
            
            personality_traits = personalization.get('personality_traits', {})
            if personality_traits.get('prefers_detailed_responses'):
                prompt += "Provide detailed, comprehensive responses. "
            elif personality_traits.get('prefers_concise_responses'):
                prompt += "Keep responses concise and to the point. "
        
        prompt += "Always be helpful, accurate, and respectful."
        return prompt

# Global instance
openai_service = OpenAIService()