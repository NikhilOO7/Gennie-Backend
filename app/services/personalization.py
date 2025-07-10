"""
Personalization Service - Advanced user personalization and preference learning
with machine learning patterns and adaptive responses
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import re
import math

from app.config import settings

logger = logging.getLogger(__name__)

class PersonalizationService:
    """
    Advanced personalization service for learning user preferences and adapting responses
    """
    
    def __init__(self):
        """Initialize personalization service"""
        self.preference_weights = {
            "conversation_style": 0.3,
            "response_length": 0.2,
            "technical_level": 0.2,
            "formality": 0.15,
            "creativity": 0.1,
            "topics": 0.05
        }
        
        # Learning parameters
        self.min_interactions = settings.MIN_INTERACTIONS_FOR_PERSONALIZATION
        self.learning_rate = 0.1
        self.decay_factor = 0.95
        
        logger.info("Personalization service initialized")
    
    async def analyze_user_preferences(
        self, 
        user_id: int, 
        interaction_history: List[Dict[str, Any]],
        redis_client = None
    ) -> Dict[str, Any]:
        """
        Analyze user preferences from interaction history
        """
        if len(interaction_history) < self.min_interactions:
            return self._get_default_preferences(user_id)
        
        try:
            preferences = {}
            
            # Analyze conversation style
            preferences["conversation_style"] = await self._analyze_conversation_style(interaction_history)
            
            # Analyze response length preferences
            preferences["response_length"] = await self._analyze_response_length_preference(interaction_history)
            
            # Analyze technical level
            preferences["technical_level"] = await self._analyze_technical_level(interaction_history)
            
            # Analyze formality preferences
            preferences["formality"] = await self._analyze_formality_preference(interaction_history)
            
            # Analyze creativity preferences
            preferences["creativity"] = await self._analyze_creativity_preference(interaction_history)
            
            # Analyze topic interests
            preferences["topics"] = await self._analyze_topic_interests(interaction_history)
            
            # Analyze temporal patterns
            preferences["temporal_patterns"] = await self._analyze_temporal_patterns(interaction_history)
            
            # Calculate confidence scores
            preferences["confidence_scores"] = self._calculate_preference_confidence(
                preferences, len(interaction_history)
            )
            
            # Cache preferences if Redis available
            if redis_client:
                await self._cache_preferences(user_id, preferences, redis_client)
            
            return {
                "success": True,
                "preferences": preferences,
                "interaction_count": len(interaction_history),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze user preferences: {str(e)}", exc_info=True)
            return self._get_default_preferences(user_id)
    
    def _get_default_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get default preferences for a user"""
        return {
            "success": True,
            "preferences": {
                "conversation_style": "balanced",
                "response_length": "medium",
                "technical_level": "intermediate",
                "formality": "casual_professional",
                "creativity": "moderate",
                "topics": {},
                "temporal_patterns": {},
                "confidence_scores": {
                    "overall": 0.0
                }
            },
            "interaction_count": 0,
            "using_defaults": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def _analyze_conversation_style(self, history: List[Dict[str, Any]]) -> str:
        """Analyze user's preferred conversation style"""
        try:
            styles = {
                "analytical": 0,
                "emotional": 0,
                "practical": 0,
                "creative": 0,
                "balanced": 0
            }
            
            for interaction in history:
                user_content = interaction.get("content", "").lower()
                
                # Analytical keywords
                if any(word in user_content for word in ["analyze", "explain", "why", "how", "data", "evidence"]):
                    styles["analytical"] += 1
                
                # Emotional keywords
                if any(word in user_content for word in ["feel", "emotion", "happy", "sad", "worry", "love"]):
                    styles["emotional"] += 1
                
                # Practical keywords
                if any(word in user_content for word in ["do", "make", "build", "fix", "solve", "implement"]):
                    styles["practical"] += 1
                
                # Creative keywords
                if any(word in user_content for word in ["imagine", "create", "design", "idea", "innovate"]):
                    styles["creative"] += 1
            
            # If no clear preference, default to balanced
            max_style = max(styles, key=styles.get)
            if styles[max_style] < len(history) * 0.2:
                return "balanced"
            
            return max_style
            
        except Exception as e:
            logger.error(f"Error analyzing conversation style: {str(e)}")
            return "balanced"
    
    async def _analyze_response_length_preference(self, history: List[Dict[str, Any]]) -> str:
        """Analyze user's preference for response length"""
        try:
            user_lengths = []
            
            for interaction in history:
                if interaction.get("sender_type") == "user":
                    content = interaction.get("content", "")
                    user_lengths.append(len(content.split()))
            
            if not user_lengths:
                return "medium"
            
            avg_length = sum(user_lengths) / len(user_lengths)
            
            if avg_length < 20:
                return "short"
            elif avg_length < 50:
                return "medium"
            else:
                return "long"
                
        except Exception as e:
            logger.error(f"Error analyzing response length: {str(e)}")
            return "medium"
    
    async def _analyze_technical_level(self, history: List[Dict[str, Any]]) -> str:
        """Analyze user's technical level based on vocabulary"""
        try:
            technical_terms = 0
            total_messages = 0
            
            technical_keywords = {
                "basic": ["app", "click", "button", "screen", "email"],
                "intermediate": ["api", "database", "function", "variable", "server"],
                "advanced": ["algorithm", "optimization", "architecture", "framework", "microservice"]
            }
            
            for interaction in history:
                if interaction.get("sender_type") == "user":
                    content = interaction.get("content", "").lower()
                    total_messages += 1
                    
                    for level, keywords in technical_keywords.items():
                        if any(keyword in content for keyword in keywords):
                            technical_terms += list(technical_keywords.keys()).index(level) + 1
            
            if total_messages == 0:
                return "intermediate"
            
            avg_technical = technical_terms / total_messages
            
            if avg_technical < 1.5:
                return "basic"
            elif avg_technical < 2.5:
                return "intermediate"
            else:
                return "advanced"
                
        except Exception as e:
            logger.error(f"Error analyzing technical level: {str(e)}")
            return "intermediate"
    
    async def _analyze_formality_preference(self, history: List[Dict[str, Any]]) -> str:
        """Analyze user's formality preference"""
        try:
            formality_indicators = {
                "casual": 0,
                "casual_professional": 0,
                "formal": 0
            }
            
            for interaction in history:
                if interaction.get("sender_type") == "user":
                    content = interaction.get("content", "")
                    
                    # Casual indicators
                    if any(indicator in content.lower() for indicator in ["hey", "yeah", "lol", "btw", "gonna"]):
                        formality_indicators["casual"] += 1
                    
                    # Formal indicators
                    elif any(indicator in content for indicator in ["Dear", "Sincerely", "Regards", "Please", "Thank you"]):
                        formality_indicators["formal"] += 1
                    
                    # Default to casual professional
                    else:
                        formality_indicators["casual_professional"] += 1
            
            return max(formality_indicators, key=formality_indicators.get)
            
        except Exception as e:
            logger.error(f"Error analyzing formality: {str(e)}")
            return "casual_professional"
    
    async def _analyze_creativity_preference(self, history: List[Dict[str, Any]]) -> str:
        """Analyze user's preference for creative responses"""
        try:
            creative_requests = 0
            total_messages = 0
            
            creative_keywords = ["imagine", "create", "story", "poem", "idea", "brainstorm", "creative", "unique"]
            
            for interaction in history:
                if interaction.get("sender_type") == "user":
                    content = interaction.get("content", "").lower()
                    total_messages += 1
                    
                    if any(keyword in content for keyword in creative_keywords):
                        creative_requests += 1
            
            if total_messages == 0:
                return "moderate"
            
            creative_ratio = creative_requests / total_messages
            
            if creative_ratio < 0.1:
                return "low"
            elif creative_ratio < 0.3:
                return "moderate"
            else:
                return "high"
                
        except Exception as e:
            logger.error(f"Error analyzing creativity preference: {str(e)}")
            return "moderate"
    
    async def _analyze_topic_interests(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze user's topic interests"""
        try:
            topic_counter = Counter()
            
            topic_keywords = {
                "technology": ["tech", "software", "hardware", "computer", "ai", "code"],
                "business": ["business", "market", "finance", "startup", "company", "strategy"],
                "health": ["health", "wellness", "fitness", "medical", "doctor", "exercise"],
                "education": ["learn", "study", "course", "education", "teach", "school"],
                "entertainment": ["movie", "music", "game", "book", "show", "entertainment"],
                "science": ["science", "research", "experiment", "theory", "discovery", "study"],
                "travel": ["travel", "trip", "vacation", "destination", "flight", "hotel"],
                "food": ["food", "recipe", "cook", "restaurant", "meal", "cuisine"]
            }
            
            for interaction in history:
                if interaction.get("sender_type") == "user":
                    content = interaction.get("content", "").lower()
                    
                    for topic, keywords in topic_keywords.items():
                        if any(keyword in content for keyword in keywords):
                            topic_counter[topic] += 1
            
            # Normalize scores
            total = sum(topic_counter.values())
            if total > 0:
                return {topic: count/total for topic, count in topic_counter.items()}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error analyzing topics: {str(e)}")
            return {}
    
    async def _analyze_temporal_patterns(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in user interactions"""
        try:
            hour_counter = defaultdict(int)
            day_counter = defaultdict(int)
            
            for interaction in history:
                if interaction.get("sender_type") == "user":
                    timestamp_str = interaction.get("timestamp", "")
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            hour_counter[timestamp.hour] += 1
                            day_counter[timestamp.weekday()] += 1
                        except:
                            continue
            
            return {
                "preferred_hours": dict(hour_counter),
                "preferred_days": dict(day_counter),
                "most_active_hour": max(hour_counter, key=hour_counter.get) if hour_counter else None,
                "most_active_day": max(day_counter, key=day_counter.get) if day_counter else None
            }
            
        except Exception as e:
            logger.error(f"Error analyzing temporal patterns: {str(e)}")
            return {}
    
    def _calculate_preference_confidence(self, preferences: Dict[str, Any], interaction_count: int) -> Dict[str, float]:
        """Calculate confidence scores for preferences"""
        try:
            # Base confidence on interaction count
            base_confidence = min(interaction_count / 50, 1.0)  # Max confidence at 50 interactions
            
            confidence_scores = {}
            
            for key, weight in self.preference_weights.items():
                if key in preferences and preferences[key]:
                    confidence_scores[key] = base_confidence * weight
                else:
                    confidence_scores[key] = 0.0
            
            confidence_scores["overall"] = sum(confidence_scores.values())
            
            return confidence_scores
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return {"overall": 0.0}
    
    async def _cache_preferences(self, user_id: int, preferences: Dict[str, Any], redis_client) -> None:
        """Cache user preferences in Redis"""
        try:
            cache_key = f"user_preferences:{user_id}"
            await redis_client.setex(
                cache_key,
                settings.PERSONALIZATION_CACHE_TTL,
                json.dumps(preferences, default=str)
            )
        except Exception as e:
            logger.error(f"Failed to cache preferences: {str(e)}")
    
    async def get_cached_preferences(self, user_id: int, redis_client) -> Optional[Dict[str, Any]]:
        """Get cached preferences from Redis"""
        try:
            cache_key = f"user_preferences:{user_id}"
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached preferences: {str(e)}")
            return None
    
    async def generate_personalized_prompt(
        self,
        user_id: int,
        base_prompt: str,
        preferences: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate personalized system prompt based on user preferences"""
        try:
            if not preferences or preferences.get("using_defaults"):
                return base_prompt
            
            personalized_prompt = base_prompt
            prefs = preferences.get("preferences", {})
            
            # Adjust for conversation style
            style = prefs.get("conversation_style", "balanced")
            if style == "analytical":
                personalized_prompt += " Provide detailed analysis and logical explanations."
            elif style == "emotional":
                personalized_prompt += " Be empathetic and acknowledge feelings."
            elif style == "practical":
                personalized_prompt += " Focus on actionable advice and practical solutions."
            elif style == "creative":
                personalized_prompt += " Be creative and imaginative in your responses."
            
            # Adjust for response length
            length = prefs.get("response_length", "medium")
            if length == "short":
                personalized_prompt += " Keep responses concise and to the point."
            elif length == "long":
                personalized_prompt += " Provide comprehensive and detailed responses."
            
            # Adjust for technical level
            tech_level = prefs.get("technical_level", "intermediate")
            if tech_level == "basic":
                personalized_prompt += " Use simple language and avoid technical jargon."
            elif tech_level == "advanced":
                personalized_prompt += " Feel free to use technical terminology and advanced concepts."
            
            # Adjust for formality
            formality = prefs.get("formality", "casual_professional")
            if formality == "casual":
                personalized_prompt += " Use a casual, friendly tone."
            elif formality == "formal":
                personalized_prompt += " Maintain a formal, professional tone."
            
            # Adjust for creativity
            creativity = prefs.get("creativity", "moderate")
            if creativity == "high":
                personalized_prompt += " Be creative and think outside the box."
            elif creativity == "low":
                personalized_prompt += " Stick to conventional approaches."
            
            # Add topic interests if significant
            topics = prefs.get("topics", {})
            if topics:
                top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:3]
                if top_topics and top_topics[0][1] > 0.2:  # If top topic > 20%
                    topic_names = [t[0] for t in top_topics]
                    personalized_prompt += f" The user is particularly interested in: {', '.join(topic_names)}."
            
            return personalized_prompt
            
        except Exception as e:
            logger.error(f"Error generating personalized prompt: {str(e)}")
            return base_prompt
    
    def adapt_system_prompt(
        self,
        base_prompt: str,
        user_preferences: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        emotion: Optional[str] = None
    ) -> str:
        """
        Adapt system prompt based on user preferences and context
        
        Args:
            base_prompt: Base system prompt
            user_preferences: User preference data
            context: Additional context (like RAG results)
            emotion: Current detected emotion
            
        Returns:
            Adapted system prompt
        """
        # If personalization is disabled, return base prompt
        if not settings.PERSONALIZATION_ENABLED:
            return base_prompt
        
        # Start with base prompt
        adapted_prompt = base_prompt
        
        # Add preference-based adaptations
        if user_preferences and not user_preferences.get("using_defaults"):
            prefs = user_preferences.get("preferences", {})
            
            # Response style adaptations
            style = prefs.get("conversation_style", "balanced")
            length = prefs.get("response_length", "medium")
            
            style_adaptations = {
                "analytical": "Focus on data, logic, and detailed analysis. ",
                "emotional": "Be empathetic and emotionally aware. ",
                "practical": "Provide actionable, practical advice. ",
                "creative": "Be creative and imaginative. ",
                "balanced": ""
            }
            
            length_adaptations = {
                "short": "Keep responses brief and concise. ",
                "medium": "",
                "long": "Provide comprehensive, detailed responses. "
            }
            
            adapted_prompt += style_adaptations.get(style, "")
            adapted_prompt += length_adaptations.get(length, "")
        
        # Add emotion-based adaptations
        if emotion:
            if emotion in ["sadness", "fear", "anger"]:
                adapted_prompt += "The user appears to be experiencing negative emotions. Be extra empathetic and supportive. "
            elif emotion in ["joy", "excitement"]:
                adapted_prompt += "The user seems to be in a positive mood. Match their energy appropriately. "
        
        # Add RAG context awareness (works for both formats)
        if context and context.get("rag_context"):
            adapted_prompt += "You have access to relevant context from previous conversations. Use this context to provide more personalized and informed responses. "
        
        return adapted_prompt
    
    async def update_user_interaction(
        self, 
        user_id: int, 
        chat_id: int, 
        user_message: str, 
        ai_response: str, 
        emotion_data: Optional[Dict[str, Any]] = None,
        redis_client = None
    ) -> None:
        """Update user interaction data for learning"""
        try:
            interaction_data = {
                "user_id": user_id,
                "chat_id": chat_id,
                "user_message": user_message,
                "ai_response": ai_response,
                "emotion_data": emotion_data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if redis_client:
                # Store recent interaction for real-time learning
                interaction_key = f"user_interaction:{user_id}:{datetime.now().timestamp()}"
                await redis_client.setex(
                    interaction_key, 
                    86400,  # 24 hours
                    json.dumps(interaction_data, default=str)
                )
                
                # Update interaction counter
                counter_key = f"user_interaction_count:{user_id}"
                await redis_client.incr(counter_key)
                await redis_client.expire(counter_key, 86400 * 30)  # 30 days
        
        except Exception as e:
            logger.error(f"Failed to update user interaction for user {user_id}: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if personalization service is healthy"""
        # If personalization is disabled, it's considered "healthy" but inactive
        if not settings.PERSONALIZATION_ENABLED:
            logger.info("Personalization service is disabled by settings, health check returning True.")
            return True

        try:
            # Test basic functionality
            test_history = [
                {"sender_type": "user", "content": "Hello, how are you?", "timestamp": datetime.now().isoformat()},
                {"sender_type": "assistant", "content": "I'm doing well, thank you!", "timestamp": datetime.now().isoformat()}
            ]
            
            result = await self.analyze_user_preferences(999999, test_history)
            return result.get("success", False)
        
        except Exception as e:
            logger.error(f"Personalization service health check failed: {str(e)}")
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get personalization service information"""
        return {
            "service_name": "Personalization",
            "min_interactions": self.min_interactions,
            "learning_rate": self.learning_rate,
            "decay_factor": self.decay_factor,
            "preference_types": list(self.preference_weights.keys()),
            "preference_weights": self.preference_weights,
            "enabled": settings.PERSONALIZATION_ENABLED,
            "cache_ttl": settings.PERSONALIZATION_CACHE_TTL
        }

# Create global service instance
personalization_service = PersonalizationService()

# Export the service
__all__ = ["PersonalizationService", "personalization_service"]