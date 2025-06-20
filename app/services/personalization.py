from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.models.user_preferences import UserPreferences
from app.models.message import Message
from app.models.chat import Chat
import json

class PersonalizationService:
    def __init__(self):
        self.learning_rate = 0.1  # How fast to adapt to user patterns
        self.memory_window = 30  # Days to consider for learning
    
    async def learn_from_conversation(
        self,
        db: Session,
        user_id: int,
        user_message: str,
        emotion_data: Dict[str, Any]
    ) -> None:
        """Learn user preferences from conversation patterns"""
        try:
            # Get or create user preferences
            preferences = db.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).first()
            
            if not preferences:
                preferences = UserPreferences(
                    user_id=user_id,
                    personality_traits={},
                    interaction_history=[]
                )
                db.add(preferences)
            
            # Update personality traits
            await self._update_personality_traits(preferences, user_message, emotion_data)
            
            # Update interaction history
            self._update_interaction_history(preferences, user_message, emotion_data)
            
            # Determine response style preferences
            preferences.response_style = self._determine_response_style(preferences)
            
            # Update preferences
            preferences.updated_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            print(f"Learning error: {e}")
    
    async def get_personalized_context(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """Get personalized context for AI response generation"""
        preferences = db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).first()
        
        if not preferences:
            return self._get_default_context()
        
        return {
            'response_style': preferences.response_style or 'balanced',
            'preferred_length': preferences.preferred_response_length or 'medium',
            'personality_traits': preferences.personality_traits or {},
            'interests': preferences.interests or [],
            'ai_personality': preferences.ai_personality or 'helpful',
            'interaction_summary': self._get_interaction_summary(preferences),
            'language': preferences.language or 'en',
            'context_memory_enabled': preferences.context_memory
        }
    
    async def _update_personality_traits(
        self,
        preferences: UserPreferences,
        message: str,
        emotion_data: Dict[str, Any]
    ) -> None:
        """Update personality traits based on conversation patterns"""
        current_traits = preferences.personality_traits or {}
        
        # Analyze message characteristics
        message_length = len(message.split())
        emotion = emotion_data.get('emotion', 'neutral')
        intensity = float(emotion_data.get('intensity', 0.5))
        
        # Update traits with exponential moving average
        traits_to_update = {
            'average_message_length': message_length,
            'emotional_expressiveness': intensity,
            'dominant_emotions': emotion,
            'communication_style': self._analyze_communication_style(message),
            'formality_level': self._analyze_formality(message),
            'question_frequency': message.count('?') / max(len(message.split()), 1)
        }
        
        for trait, value in traits_to_update.items():
            if trait in current_traits:
                if trait == 'dominant_emotions':
                    # Handle emotion frequency tracking
                    if 'emotion_frequency' not in current_traits:
                        current_traits['emotion_frequency'] = {}
                    emotion_freq = current_traits['emotion_frequency']
                    emotion_freq[emotion] = emotion_freq.get(emotion, 0) + 1
                else:
                    # Exponential moving average for numeric traits
                    current_traits[trait] = (
                        (1 - self.learning_rate) * current_traits[trait] +
                        self.learning_rate * value
                    )
            else:
                current_traits[trait] = value
        
        preferences.personality_traits = current_traits
    
    def _update_interaction_history(
        self,
        preferences: UserPreferences,
        message: str,
        emotion_data: Dict[str, Any]
    ) -> None:
        """Update interaction history with recent conversation data"""
        history = preferences.interaction_history or []
        
        # Add new interaction
        interaction = {
            'timestamp': datetime.utcnow().isoformat(),
            'message_length': len(message.split()),
            'emotion': emotion_data.get('emotion'),
            'intensity': emotion_data.get('intensity'),
            'sentiment': emotion_data.get('sentiment')
        }
        
        history.append(interaction)
        
        # Keep only recent interactions (memory_window days)
        cutoff_date = datetime.utcnow() - timedelta(days=self.memory_window)
        history = [
            h for h in history 
            if datetime.fromisoformat(h['timestamp']) > cutoff_date
        ]
        
        # Limit to max 100 interactions for performance
        if len(history) > 100:
            history = history[-100:]
        
        preferences.interaction_history = history
    
    def _determine_response_style(self, preferences: UserPreferences) -> str:
        """Determine preferred response style based on personality traits"""
        traits = preferences.personality_traits or {}
        
        formality = traits.get('formality_level', 0.5)
        message_length = traits.get('average_message_length', 10)
        
        if formality > 0.7:
            return 'formal'
        elif formality < 0.3 and message_length < 15:
            return 'casual'
        else:
            return 'balanced'
    
    def _analyze_communication_style(self, message: str) -> str:
        """Analyze user's communication style"""
        # Simple heuristics for communication style
        exclamation_ratio = message.count('!') / max(len(message), 1)
        caps_ratio = sum(1 for c in message if c.isupper()) / max(len(message), 1)
        
        if exclamation_ratio > 0.05 or caps_ratio > 0.3:
            return 'expressive'
        elif '?' in message:
            return 'inquisitive'
        else:
            return 'conversational'
    
    def _analyze_formality(self, message: str) -> float:
        """Analyze formality level of message (0-1 scale)"""
        formal_indicators = [
            'please', 'thank you', 'could you', 'would you',
            'i would like', 'i am writing', 'sincerely'
        ]
        informal_indicators = [
            'hey', 'hi', 'yeah', 'nah', 'gonna', 'wanna',
            'lol', 'haha', 'omg', 'btw'
        ]
        
        message_lower = message.lower()
        formal_count = sum(1 for indicator in formal_indicators if indicator in message_lower)
        informal_count = sum(1 for indicator in informal_indicators if indicator in message_lower)
        
        if formal_count + informal_count == 0:
            return 0.5  # Neutral
        
        return formal_count / (formal_count + informal_count)
    
    def _get_interaction_summary(self, preferences: UserPreferences) -> str:
        """Generate summary of user interaction patterns"""
        history = preferences.interaction_history or []
        
        if not history:
            return "New user - building interaction profile."
        
        # Calculate averages
        avg_message_length = sum(h.get('message_length', 0) for h in history) / len(history)
        avg_intensity = sum(h.get('intensity', 0.5) for h in history) / len(history)
        
        # Most common emotions
        emotions = [h.get('emotion', 'neutral') for h in history]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        most_common_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else 'neutral'
        
        return (
            f"User typically sends {avg_message_length:.1f} word messages "
            f"with {avg_intensity:.1f} emotional intensity. "
            f"Most common emotion: {most_common_emotion}. "
            f"Based on {len(history)} recent interactions."
        )
    
    def _get_default_context(self) -> Dict[str, Any]:
        """Get default context for new users"""
        return {
            'response_style': 'balanced',
            'preferred_length': 'medium',
            'personality_traits': {},
            'interests': [],
            'ai_personality': 'helpful',
            'interaction_summary': 'New user - no interaction history yet.',
            'language': 'en',
            'context_memory_enabled': True
        }

# Global instance
personalization_service = PersonalizationService()