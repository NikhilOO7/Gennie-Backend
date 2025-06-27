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
            
            # Cache preferences if Redis is available
            if redis_client:
                await self._cache_preferences(user_id, preferences, redis_client)
            
            return {
                "success": True,
                "user_id": user_id,
                "preferences": preferences,
                "interaction_count": len(interaction_history),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "next_update_threshold": len(interaction_history) + 10
            }
        
        except Exception as e:
            logger.error(f"Preference analysis failed for user {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id,
                "fallback_preferences": self._get_default_preferences(user_id)
            }
    
    async def _analyze_conversation_style(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's conversation style preferences"""
        
        user_messages = [msg for msg in history if msg.get("sender_type") == "user"]
        
        if not user_messages:
            return {"style": "balanced", "confidence": 0.0}
        
        # Analyze message characteristics
        message_lengths = [len(msg.get("content", "")) for msg in user_messages]
        question_count = sum(1 for msg in user_messages if "?" in msg.get("content", ""))
        exclamation_count = sum(1 for msg in user_messages if "!" in msg.get("content", ""))
        
        avg_length = sum(message_lengths) / len(message_lengths)
        question_ratio = question_count / len(user_messages)
        exclamation_ratio = exclamation_count / len(user_messages)
        
        # Determine style
        if avg_length > 200 and question_ratio > 0.3:
            style = "analytical"
        elif exclamation_ratio > 0.2 and avg_length < 100:
            style = "casual"
        elif question_ratio > 0.4:
            style = "inquisitive"
        elif avg_length > 150:
            style = "detailed"
        else:
            style = "balanced"
        
        confidence = min(len(user_messages) / 20.0, 1.0)  # Higher confidence with more messages
        
        return {
            "style": style,
            "confidence": confidence,
            "avg_message_length": avg_length,
            "question_ratio": question_ratio,
            "exclamation_ratio": exclamation_ratio,
            "characteristics": {
                "verbose": avg_length > 200,
                "concise": avg_length < 50,
                "inquisitive": question_ratio > 0.3,
                "expressive": exclamation_ratio > 0.2
            }
        }
    
    async def _analyze_response_length_preference(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze preferred response length"""
        
        # Look at user feedback patterns and follow-up questions
        ai_messages = [msg for msg in history if msg.get("sender_type") == "assistant"]
        user_messages = [msg for msg in history if msg.get("sender_type") == "user"]
        
        if len(ai_messages) < 2:
            return {"preference": "medium", "confidence": 0.0}
        
        # Analyze AI response lengths and user follow-ups
        response_lengths = [len(msg.get("content", "")) for msg in ai_messages]
        avg_ai_response_length = sum(response_lengths) / len(response_lengths)
        
        # Look for patterns in user follow-ups
        follow_up_patterns = []
        for i in range(len(ai_messages) - 1):
            ai_msg_length = len(ai_messages[i].get("content", ""))
            # Find next user message
            next_user_msgs = [
                msg for msg in user_messages 
                if msg.get("timestamp", 0) > ai_messages[i].get("timestamp", 0)
            ]
            
            if next_user_msgs:
                next_user_msg = next_user_msgs[0]
                content = next_user_msg.get("content", "").lower()
                
                # Check for length-related feedback
                if any(phrase in content for phrase in ["too long", "shorter", "brief", "tl;dr"]):
                    follow_up_patterns.append(("shorter", ai_msg_length))
                elif any(phrase in content for phrase in ["more detail", "elaborate", "explain more"]):
                    follow_up_patterns.append(("longer", ai_msg_length))
                else:
                    follow_up_patterns.append(("neutral", ai_msg_length))
        
        # Determine preference
        if not follow_up_patterns:
            if avg_ai_response_length > 500:
                preference = "long"
            elif avg_ai_response_length < 200:
                preference = "short"
            else:
                preference = "medium"
        else:
            shorter_requests = [p for p in follow_up_patterns if p[0] == "shorter"]
            longer_requests = [p for p in follow_up_patterns if p[0] == "longer"]
            
            if len(shorter_requests) > len(longer_requests):
                preference = "short"
            elif len(longer_requests) > len(shorter_requests):
                preference = "long"
            else:
                preference = "medium"
        
        confidence = min(len(follow_up_patterns) / 10.0, 1.0)
        
        return {
            "preference": preference,
            "confidence": confidence,
            "avg_ai_response_length": avg_ai_response_length,
            "feedback_patterns": len(follow_up_patterns),
            "length_feedback": {
                "shorter_requests": len([p for p in follow_up_patterns if p[0] == "shorter"]),
                "longer_requests": len([p for p in follow_up_patterns if p[0] == "longer"])
            }
        }
    
    async def _analyze_technical_level(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's technical sophistication level"""
        
        user_messages = [msg for msg in history if msg.get("sender_type") == "user"]
        
        if not user_messages:
            return {"level": "beginner", "confidence": 0.0}
        
        technical_indicators = {
            "beginner": [
                "what is", "how do i", "explain", "simple", "basic", "help me understand",
                "i don't know", "confused", "new to this"
            ],
            "intermediate": [
                "configure", "setup", "install", "implement", "optimize", "troubleshoot",
                "best practice", "recommend", "compare", "pros and cons"
            ],
            "advanced": [
                "algorithm", "architecture", "performance", "scalability", "optimization",
                "debug", "refactor", "api", "framework", "deploy", "infrastructure",
                "security", "authentication", "database", "microservices"
            ],
            "expert": [
                "distributed systems", "machine learning", "artificial intelligence",
                "containerization", "kubernetes", "devops", "ci/cd", "monitoring",
                "observability", "load balancing", "caching", "concurrency"
            ]
        }
        
        level_scores = defaultdict(int)
        total_indicators = 0
        
        for message in user_messages:
            content = message.get("content", "").lower()
            
            for level, indicators in technical_indicators.items():
                for indicator in indicators:
                    if indicator in content:
                        level_scores[level] += 1
                        total_indicators += 1
        
        if total_indicators == 0:
            return {"level": "beginner", "confidence": 0.0}
        
        # Calculate weighted scores
        level_weights = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        weighted_score = sum(level_scores[level] * level_weights[level] for level in level_scores)
        avg_score = weighted_score / total_indicators if total_indicators > 0 else 1
        
        if avg_score >= 3.5:
            level = "expert"
        elif avg_score >= 2.5:
            level = "advanced"
        elif avg_score >= 1.5:
            level = "intermediate"
        else:
            level = "beginner"
        
        confidence = min(total_indicators / 20.0, 1.0)
        
        return {
            "level": level,
            "confidence": confidence,
            "weighted_score": avg_score,
            "indicator_counts": dict(level_scores),
            "total_indicators": total_indicators
        }
    
    async def _analyze_formality_preference(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's formality preferences"""
        
        user_messages = [msg for msg in history if msg.get("sender_type") == "user"]
        
        if not user_messages:
            return {"level": "neutral", "confidence": 0.0}
        
        formal_indicators = [
            "please", "thank you", "would you", "could you", "i would appreciate",
            "furthermore", "however", "nevertheless", "therefore", "consequently"
        ]
        
        informal_indicators = [
            "hey", "hi", "yeah", "yep", "nope", "gonna", "wanna", "kinda", "sorta",
            "btw", "fyi", "lol", "omg", "wtf", "awesome", "cool", "sweet"
        ]
        
        formal_count = 0
        informal_count = 0
        total_words = 0
        
        for message in user_messages:
            content = message.get("content", "").lower()
            words = content.split()
            total_words += len(words)
            
            formal_count += sum(1 for indicator in formal_indicators if indicator in content)
            informal_count += sum(1 for indicator in informal_indicators if indicator in content)
        
        if total_words == 0:
            return {"level": "neutral", "confidence": 0.0}
        
        formal_ratio = formal_count / total_words
        informal_ratio = informal_count / total_words
        
        if formal_ratio > informal_ratio * 2:
            level = "formal"
        elif informal_ratio > formal_ratio * 2:
            level = "informal"
        else:
            level = "neutral"
        
        confidence = min((formal_count + informal_count) / 10.0, 1.0)
        
        return {
            "level": level,
            "confidence": confidence,
            "formal_ratio": formal_ratio,
            "informal_ratio": informal_ratio,
            "formal_indicators": formal_count,
            "informal_indicators": informal_count
        }
    
    async def _analyze_creativity_preference(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's creativity and originality preferences"""
        
        user_messages = [msg for msg in history if msg.get("sender_type") == "user"]
        
        if not user_messages:
            return {"level": "moderate", "confidence": 0.0}
        
        creative_indicators = [
            "creative", "innovative", "original", "unique", "imaginative", "artistic",
            "brainstorm", "think outside", "unconventional", "experimental", "novel"
        ]
        
        analytical_indicators = [
            "analyze", "logical", "systematic", "methodical", "structured", "precise",
            "accurate", "factual", "evidence", "data", "statistics", "research"
        ]
        
        creative_count = sum(
            1 for msg in user_messages 
            for indicator in creative_indicators 
            if indicator in msg.get("content", "").lower()
        )
        
        analytical_count = sum(
            1 for msg in user_messages 
            for indicator in analytical_indicators 
            if indicator in msg.get("content", "").lower()
        )
        
        if creative_count > analytical_count:
            level = "high"
        elif analytical_count > creative_count:
            level = "low"
        else:
            level = "moderate"
        
        confidence = min((creative_count + analytical_count) / 15.0, 1.0)
        
        return {
            "level": level,
            "confidence": confidence,
            "creative_indicators": creative_count,
            "analytical_indicators": analytical_count,
            "preference_ratio": creative_count / max(analytical_count, 1)
        }
    
    async def _analyze_topic_interests(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's topic interests"""
        
        user_messages = [msg for msg in history if msg.get("sender_type") == "user"]
        
        topic_keywords = {
            "technology": ["tech", "software", "programming", "computer", "ai", "ml", "data", "api"],
            "business": ["business", "marketing", "strategy", "finance", "startup", "entrepreneur"],
            "science": ["science", "research", "study", "experiment", "theory", "analysis"],
            "health": ["health", "fitness", "wellness", "medical", "nutrition", "exercise"],
            "education": ["learn", "study", "education", "course", "training", "skill"],
            "creativity": ["art", "design", "creative", "music", "writing", "photography"],
            "lifestyle": ["travel", "food", "cooking", "hobby", "entertainment", "movies"]
        }
        
        topic_scores = defaultdict(int)
        total_mentions = 0
        
        for message in user_messages:
            content = message.get("content", "").lower()
            
            for topic, keywords in topic_keywords.items():
                for keyword in keywords:
                    if keyword in content:
                        topic_scores[topic] += 1
                        total_mentions += 1
        
        if total_mentions == 0:
            return {"interests": {}, "confidence": 0.0}
        
        # Normalize scores
        normalized_scores = {
            topic: score / total_mentions 
            for topic, score in topic_scores.items()
        }
        
        # Get top interests
        top_interests = sorted(
            normalized_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        confidence = min(total_mentions / 30.0, 1.0)
        
        return {
            "interests": dict(top_interests),
            "confidence": confidence,
            "total_mentions": total_mentions,
            "topic_distribution": dict(normalized_scores)
        }
    
    async def _analyze_temporal_patterns(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's temporal usage patterns"""
        
        timestamps = []
        for msg in history:
            if msg.get("timestamp"):
                try:
                    if isinstance(msg["timestamp"], str):
                        ts = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
                    else:
                        ts = msg["timestamp"]
                    timestamps.append(ts)
                except:
                    continue
        
        if len(timestamps) < 5:
            return {"patterns": {}, "confidence": 0.0}
        
        # Analyze hourly patterns
        hours = [ts.hour for ts in timestamps]
        hour_counts = Counter(hours)
        
        # Analyze daily patterns
        days = [ts.weekday() for ts in timestamps]  # 0=Monday, 6=Sunday
        day_counts = Counter(days)
        
        # Find peak activity times
        peak_hour = max(hour_counts, key=hour_counts.get)
        peak_day = max(day_counts, key=day_counts.get)
        
        # Classify time preferences
        if peak_hour < 6:
            time_preference = "night_owl"
        elif peak_hour < 12:
            time_preference = "morning_person"
        elif peak_hour < 18:
            time_preference = "afternoon_active"
        else:
            time_preference = "evening_active"
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        confidence = min(len(timestamps) / 50.0, 1.0)
        
        return {
            "patterns": {
                "peak_hour": peak_hour,
                "peak_day": day_names[peak_day],
                "time_preference": time_preference,
                "hourly_distribution": dict(hour_counts),
                "daily_distribution": dict(day_counts)
            },
            "confidence": confidence,
            "total_interactions": len(timestamps)
        }
    
    def _calculate_preference_confidence(
        self, 
        preferences: Dict[str, Any], 
        interaction_count: int
    ) -> Dict[str, float]:
        """Calculate confidence scores for all preferences"""
        
        base_confidence = min(interaction_count / 50.0, 1.0)
        
        confidence_scores = {}
        for pref_type, pref_data in preferences.items():
            if isinstance(pref_data, dict) and "confidence" in pref_data:
                # Combine individual confidence with base confidence
                individual_confidence = pref_data["confidence"]
                combined_confidence = (individual_confidence + base_confidence) / 2
                confidence_scores[pref_type] = combined_confidence
            else:
                confidence_scores[pref_type] = base_confidence * 0.5
        
        return confidence_scores
    
    async def _cache_preferences(
        self, 
        user_id: int, 
        preferences: Dict[str, Any], 
        redis_client
    ) -> None:
        """Cache preferences in Redis"""
        try:
            cache_key = f"user_preferences:{user_id}"
            cache_data = {
                "preferences": preferences,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "ttl": settings.PERSONALIZATION_CACHE_TTL
            }
            
            await redis_client.setex(
                cache_key, 
                settings.PERSONALIZATION_CACHE_TTL, 
                json.dumps(cache_data, default=str)
            )
            
            logger.debug(f"Cached preferences for user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to cache preferences for user {user_id}: {str(e)}")
    
    async def get_cached_preferences(
        self, 
        user_id: int, 
        redis_client
    ) -> Optional[Dict[str, Any]]:
        """Get cached preferences from Redis"""
        try:
            cache_key = f"user_preferences:{user_id}"
            cached_data = await redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                return data.get("preferences")
        
        except Exception as e:
            logger.error(f"Failed to get cached preferences for user {user_id}: {str(e)}")
        
        return None
    
    def _get_default_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get default preferences for new users"""
        return {
            "conversation_style": {"style": "balanced", "confidence": 0.0},
            "response_length": {"preference": "medium", "confidence": 0.0},
            "technical_level": {"level": "beginner", "confidence": 0.0},
            "formality": {"level": "neutral", "confidence": 0.0},
            "creativity": {"level": "moderate", "confidence": 0.0},
            "topics": {"interests": {}, "confidence": 0.0},
            "temporal_patterns": {"patterns": {}, "confidence": 0.0}
        }
    
    async def generate_personalized_system_prompt(
        self, 
        user_preferences: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate personalized system prompt based on user preferences"""
        
        base_prompt = "You are a helpful AI assistant. "
        
        # Add conversation style instructions
        conv_style = user_preferences.get("conversation_style", {})
        style = conv_style.get("style", "balanced")
        
        if style == "casual":
            base_prompt += "Keep your responses conversational and friendly. "
        elif style == "analytical":
            base_prompt += "Provide detailed, analytical responses with logical reasoning. "
        elif style == "inquisitive":
            base_prompt += "Be thorough in your explanations and ask clarifying questions when helpful. "
        elif style == "detailed":
            base_prompt += "Provide comprehensive, detailed responses. "
        
        # Add response length preferences
        length_pref = user_preferences.get("response_length", {})
        preference = length_pref.get("preference", "medium")
        
        if preference == "short":
            base_prompt += "Keep your responses concise and to the point. "
        elif preference == "long":
            base_prompt += "Provide detailed, comprehensive responses with examples. "
        
        # Add technical level adjustments
        tech_level = user_preferences.get("technical_level", {})
        level = tech_level.get("level", "beginner")
        
        if level == "beginner":
            base_prompt += "Explain technical concepts in simple terms with analogies. "
        elif level == "intermediate":
            base_prompt += "You can use technical terminology but explain complex concepts. "
        elif level == "advanced":
            base_prompt += "Feel free to use technical language and advanced concepts. "
        elif level == "expert":
            base_prompt += "Use expert-level technical language and assume deep knowledge. "
        
        # Add formality preferences
        formality = user_preferences.get("formality", {})
        formality_level = formality.get("level", "neutral")
        
        if formality_level == "formal":
            base_prompt += "Maintain a professional, formal tone. "
        elif formality_level == "informal":
            base_prompt += "Use a casual, conversational tone. "
        
        # Add creativity preferences
        creativity = user_preferences.get("creativity", {})
        creativity_level = creativity.get("level", "moderate")
        
        if creativity_level == "high":
            base_prompt += "Be creative and think outside the box in your responses. "
        elif creativity_level == "low":
            base_prompt += "Focus on factual, straightforward information. "
        
        # Add topic-specific adjustments
        topics = user_preferences.get("topics", {})
        interests = topics.get("interests", {})
        
        if interests:
            top_interest = max(interests, key=interests.get)
            base_prompt += f"The user shows particular interest in {top_interest}. "
        
        # Add contextual adjustments
        if context:
            if context.get("recent_emotion") in ["sadness", "anxiety"]:
                base_prompt += "Be empathetic and supportive in your tone. "
            elif context.get("recent_emotion") in ["joy", "excitement"]:
                base_prompt += "Match the user's positive energy. "
        
        return base_prompt.strip()
    
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