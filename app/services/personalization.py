from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.models.message import Message
from app.models.user_preferences import UserPreferences
import logging
import json

logger = logging.getLogger(__name__)

class PersonalizationService:
    def __init__(self):
        pass
    
    async def learn_from_conversation(
        self,
        db: Session,
        chat_id: int,
        message: str,
        emotion_data: Dict[str, Any]
    ):
        """Learn from user's conversation patterns"""
        try:
            # Get or create user preferences
            preferences = db.query(UserPreferences).filter(
                UserPreferences.chat_id == chat_id
            ).first()
            
            if not preferences:
                preferences = UserPreferences(
                    chat_id=chat_id,
                    personality_traits={},
                    response_style="friendly",
                    interaction_history={"message_count": 0, "emotions": []}
                )
                db.add(preferences)
            
            # Update interaction history
            if not preferences.interaction_history:
                preferences.interaction_history = {"message_count": 0, "emotions": []}
            
            # Update message count
            preferences.interaction_history["message_count"] = preferences.interaction_history.get("message_count", 0) + 1
            
            # Track emotions
            if "emotions" not in preferences.interaction_history:
                preferences.interaction_history["emotions"] = []
            
            preferences.interaction_history["emotions"].append({
                "emotion": emotion_data.get("enhanced_emotion", "neutral"),
                "intensity": emotion_data.get("intensity", 0.5),
                "message_length": len(message.split())
            })
            
            # Keep only last 50 emotions
            if len(preferences.interaction_history["emotions"]) > 50:
                preferences.interaction_history["emotions"] = preferences.interaction_history["emotions"][-50:]
            
            # Update personality traits based on patterns
            await self._update_personality_traits(preferences)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error learning from conversation: {str(e)}")
            db.rollback()
    
    async def get_personalized_context(
        self,
        db: Session,
        chat_id: int
    ) -> Dict[str, Any]:
        """Get personalized context for AI responses"""
        try:
            preferences = db.query(UserPreferences).filter(
                UserPreferences.chat_id == chat_id
            ).first()
            
            if not preferences:
                return {}
            
            # Build context
            context = {
                "response_style": preferences.response_style,
                "personality_traits": preferences.personality_traits or {},
                "interaction_summary": self._generate_interaction_summary(preferences.interaction_history or {})
            }
            
            # Add recent emotions
            if preferences.interaction_history and "emotions" in preferences.interaction_history:
                recent_emotions = preferences.interaction_history["emotions"][-10:]
                context["recent_emotions"] = [e["emotion"] for e in recent_emotions]
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting personalized context: {str(e)}")
            return {}
    
    async def _update_personality_traits(self, preferences: UserPreferences):
        """Update personality traits based on interaction patterns"""
        try:
            if not preferences.interaction_history or "emotions" not in preferences.interaction_history:
                return
            
            emotions = preferences.interaction_history["emotions"]
            if len(emotions) < 5:  # Need at least 5 interactions
                return
            
            # Calculate emotional patterns
            emotion_counts = {}
            total_intensity = 0
            
            for emotion_data in emotions:
                emotion = emotion_data["emotion"]
                intensity = emotion_data["intensity"]
                
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                total_intensity += intensity
            
            # Determine dominant emotion
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
            avg_intensity = total_intensity / len(emotions)
            
            # Update personality traits
            if not preferences.personality_traits:
                preferences.personality_traits = {}
            
            preferences.personality_traits.update({
                "dominant_emotion": dominant_emotion,
                "emotional_intensity": avg_intensity,
                "interaction_count": len(emotions),
                "last_updated": "2025-01-18"  # You might want to use datetime here
            })
            
            # Adjust response style based on patterns
            if dominant_emotion in ["sad", "anxious", "frustrated"]:
                preferences.response_style = "supportive"
            elif dominant_emotion in ["excited", "happy", "love"]:
                preferences.response_style = "enthusiastic"
            else:
                preferences.response_style = "friendly"
                
        except Exception as e:
            logger.error(f"Error updating personality traits: {str(e)}")
    
    def _generate_interaction_summary(self, history: Dict[str, Any]) -> str:
        """Generate a summary of user interaction patterns"""
        try:
            if not history or "emotions" not in history:
                return "New user with no interaction history."
            
            emotions = history["emotions"]
            message_count = history.get("message_count", 0)
            
            if len(emotions) == 0:
                return f"User has sent {message_count} messages but no emotion data available."
            
            # Calculate averages
            avg_message_length = sum(e.get("message_length", 0) for e in emotions) / len(emotions)
            avg_intensity = sum(e.get("intensity", 0.5) for e in emotions) / len(emotions)
            
            # Most common emotions
            emotion_counts = {}
            for emotion_data in emotions:
                emotion = emotion_data["emotion"]
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            most_common_emotion = max(emotion_counts, key=emotion_counts.get)
            
            return f"User typically sends {avg_message_length:.1f} word messages with {avg_intensity:.1f} emotional intensity. Most common emotion: {most_common_emotion}."
            
        except Exception as e:
            logger.error(f"Error generating interaction summary: {str(e)}")
            return "Unable to generate interaction summary."

# Create global instance
personalization_service = PersonalizationService()