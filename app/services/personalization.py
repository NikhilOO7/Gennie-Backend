import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
import asyncio
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class PersonalizationService:
    """
    Advanced personalization service for AI chatbot responses
    """
    
    def __init__(self):
        self.interaction_patterns = {}
        self.user_preferences = {}
        self.conversation_history = {}
        
    async def get_user_context(
        self, 
        user_id: int, 
        chat_id: int, 
        redis
    ) -> Dict[str, Any]:
        """
        Get comprehensive user context for personalization
        """
        try:
            # Get user preferences from Redis
            pref_key = f"user_preferences:{user_id}"
            preferences = await redis.get(pref_key)
            if preferences:
                preferences = json.loads(preferences)
            else:
                preferences = {}
            
            # Get interaction patterns
            pattern_key = f"interaction_patterns:{user_id}"
            patterns = await redis.get(pattern_key)
            if patterns:
                patterns = json.loads(patterns)
            else:
                patterns = {}
            
            # Get recent conversation topics
            topics_key = f"conversation_topics:{user_id}"
            topics = await redis.get(topics_key)
            if topics:
                topics = json.loads(topics)
            else:
                topics = []
            
            # Get user's typical conversation style
            style_key = f"conversation_style:{user_id}"
            style = await redis.get(style_key)
            if style:
                style = json.loads(style)
            else:
                style = {}
            
            context = {
                "user_id": user_id,
                "chat_id": chat_id,
                "preferences": preferences,
                "interaction_patterns": patterns,
                "recent_topics": topics,
                "conversation_style": style,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Retrieved user context for user {user_id}")
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return {"user_id": user_id, "chat_id": chat_id, "preferences": {}}
    
    async def update_user_interaction(
        self,
        user_id: int,
        chat_id: int,
        user_message: str,
        ai_response: str,
        emotion_data: Dict[str, Any],
        redis
    ):
        """
        Update user interaction patterns and preferences
        """
        try:
            timestamp = datetime.now(timezone.utc)
            
            # Update interaction patterns
            await self._update_interaction_patterns(user_id, user_message, ai_response, emotion_data, redis)
            
            # Update conversation topics
            await self._update_conversation_topics(user_id, user_message, redis)
            
            # Update conversation style
            await self._update_conversation_style(user_id, user_message, ai_response, redis)
            
            # Update response effectiveness
            await self._track_response_effectiveness(user_id, chat_id, emotion_data, redis)
            
            # Update user preferences based on behavior
            await self._infer_preferences(user_id, user_message, emotion_data, redis)
            
            logger.info(f"Updated personalization data for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error updating user interaction: {str(e)}")
    
    async def get_response_recommendations(
        self,
        user_id: int,
        message: str,
        emotion_data: Dict[str, Any],
        redis
    ) -> Dict[str, Any]:
        """
        Get personalized response recommendations
        """
        try:
            context = await self.get_user_context(user_id, 0, redis)
            
            recommendations = {
                "tone": self._recommend_tone(context, emotion_data),
                "length": self._recommend_length(context),
                "style": self._recommend_style(context),
                "topics_to_explore": self._recommend_topics(context, message),
                "avoid_topics": self._get_topics_to_avoid(context),
                "personalization_triggers": self._get_personalization_triggers(context)
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting response recommendations: {str(e)}")
            return {}
    
    async def analyze_user_patterns(
        self,
        user_id: int,
        redis,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze user patterns over time
        """
        try:
            # Get all user data
            context = await self.get_user_context(user_id, 0, redis)
            patterns = context.get("interaction_patterns", {})
            
            analysis = {
                "most_active_times": self._analyze_activity_times(patterns),
                "preferred_topics": self._analyze_preferred_topics(context),
                "communication_style": self._analyze_communication_style(context),
                "emotion_patterns": self._analyze_emotion_patterns(patterns),
                "engagement_metrics": self._calculate_engagement_metrics(patterns),
                "learning_preferences": self._infer_learning_preferences(context),
                "response_preferences": self._analyze_response_preferences(patterns)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing user patterns: {str(e)}")
            return {}
    
    async def get_personalized_prompts(
        self,
        user_id: int,
        category: str,
        redis
    ) -> List[str]:
        """
        Get personalized conversation prompts
        """
        try:
            context = await self.get_user_context(user_id, 0, redis)
            interests = context.get("preferences", {}).get("interests", [])
            topics = context.get("recent_topics", [])
            
            prompts = []
            
            # Category-specific prompts
            if category == "creative":
                prompts = [
                    "What's a creative project you've been thinking about?",
                    "If you could design anything, what would it be?",
                    "What inspires your creativity?"
                ]
            elif category == "learning":
                prompts = [
                    "What's something new you'd like to learn?",
                    "What topic have you always been curious about?",
                    "What skill would make the biggest difference in your life?"
                ]
            elif category == "personal":
                prompts = [
                    "What made you smile today?",
                    "What's been on your mind lately?",
                    "What are you looking forward to?"
                ]
            
            # Personalize based on interests
            if interests:
                for interest in interests[:3]:  # Top 3 interests
                    prompts.append(f"Tell me about your experience with {interest}")
                    prompts.append(f"What's new in the world of {interest}?")
            
            return prompts[:5]  # Return top 5 prompts
            
        except Exception as e:
            logger.error(f"Error getting personalized prompts: {str(e)}")
            return ["How can I help you today?"]
    
    async def _update_interaction_patterns(
        self,
        user_id: int,
        user_message: str,
        ai_response: str,
        emotion_data: Dict[str, Any],
        redis
    ):
        """Update interaction patterns in Redis"""
        pattern_key = f"interaction_patterns:{user_id}"
        
        # Get existing patterns
        existing = await redis.get(pattern_key)
        if existing:
            patterns = json.loads(existing)
        else:
            patterns = {
                "message_count": 0,
                "avg_message_length": 0,
                "emotion_history": [],
                "topic_frequency": {},
                "time_patterns": [],
                "response_ratings": []
            }
        
        # Update patterns
        patterns["message_count"] += 1
        
        # Update average message length
        current_length = len(user_message)
        patterns["avg_message_length"] = (
            (patterns["avg_message_length"] * (patterns["message_count"] - 1) + current_length) 
            / patterns["message_count"]
        )
        
        # Add emotion data
        patterns["emotion_history"].append({
            "emotion": emotion_data.get("primary_emotion", "neutral"),
            "compound": emotion_data.get("compound", 0),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only last 50 emotion entries
        patterns["emotion_history"] = patterns["emotion_history"][-50:]
        
        # Add time pattern
        patterns["time_patterns"].append({
            "hour": datetime.now(timezone.utc).hour,
            "day_of_week": datetime.now(timezone.utc).weekday(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only last 100 time entries
        patterns["time_patterns"] = patterns["time_patterns"][-100:]
        
        # Save back to Redis
        await redis.setex(pattern_key, 86400 * 30, json.dumps(patterns))  # 30 days expiry
    
    async def _update_conversation_topics(self, user_id: int, message: str, redis):
        """Extract and update conversation topics"""
        topics_key = f"conversation_topics:{user_id}"
        
        # Simple topic extraction (in production, you might use NLP libraries)
        potential_topics = self._extract_topics(message)
        
        if potential_topics:
            existing = await redis.get(topics_key)
            if existing:
                topics = json.loads(existing)
            else:
                topics = []
            
            # Add new topics with timestamp
            for topic in potential_topics:
                topics.append({
                    "topic": topic,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "count": 1
                })
            
            # Consolidate duplicate topics
            topic_counts = Counter([t["topic"] for t in topics])
            unique_topics = []
            for topic, count in topic_counts.most_common(20):  # Keep top 20 topics
                unique_topics.append({
                    "topic": topic,
                    "count": count,
                    "last_mentioned": max([t["timestamp"] for t in topics if t["topic"] == topic])
                })
            
            await redis.setex(topics_key, 86400 * 30, json.dumps(unique_topics))
    
    async def _update_conversation_style(self, user_id: int, user_message: str, ai_response: str, redis):
        """Analyze and update conversation style preferences"""
        style_key = f"conversation_style:{user_id}"
        
        # Analyze message characteristics
        message_analysis = {
            "length": len(user_message),
            "question_count": user_message.count("?"),
            "exclamation_count": user_message.count("!"),
            "formal_indicators": self._count_formal_indicators(user_message),
            "casual_indicators": self._count_casual_indicators(user_message),
            "technical_terms": self._count_technical_terms(user_message)
        }
        
        existing = await redis.get(style_key)
        if existing:
            style = json.loads(existing)
        else:
            style = {
                "avg_message_length": 0,
                "formality_score": 0,
                "technical_level": 0,
                "interaction_count": 0
            }
        
        # Update style metrics
        style["interaction_count"] += 1
        count = style["interaction_count"]
        
        # Update averages
        style["avg_message_length"] = (
            (style["avg_message_length"] * (count - 1) + message_analysis["length"]) / count
        )
        
        # Calculate formality score
        formality = (message_analysis["formal_indicators"] - message_analysis["casual_indicators"])
        style["formality_score"] = (
            (style["formality_score"] * (count - 1) + formality) / count
        )
        
        # Update technical level
        style["technical_level"] = (
            (style["technical_level"] * (count - 1) + message_analysis["technical_terms"]) / count
        )
        
        await redis.setex(style_key, 86400 * 30, json.dumps(style))
    
    async def _track_response_effectiveness(self, user_id: int, chat_id: int, emotion_data: Dict, redis):
        """Track how effective responses are based on emotional feedback"""
        effectiveness_key = f"response_effectiveness:{user_id}"
        
        # Simple effectiveness metric based on emotion improvement
        current_sentiment = emotion_data.get("compound", 0)
        
        existing = await redis.get(effectiveness_key)
        if existing:
            effectiveness = json.loads(existing)
        else:
            effectiveness = {"responses": [], "avg_effectiveness": 0}
        
        effectiveness["responses"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sentiment": current_sentiment,
            "chat_id": chat_id
        })
        
        # Keep only last 50 responses
        effectiveness["responses"] = effectiveness["responses"][-50:]
        
        # Calculate average effectiveness
        if len(effectiveness["responses"]) > 1:
            sentiments = [r["sentiment"] for r in effectiveness["responses"]]
            effectiveness["avg_effectiveness"] = sum(sentiments) / len(sentiments)
        
        await redis.setex(effectiveness_key, 86400 * 30, json.dumps(effectiveness))
    
    async def _infer_preferences(self, user_id: int, message: str, emotion_data: Dict, redis):
        """Infer user preferences from behavior"""
        pref_key = f"user_preferences:{user_id}"
        
        existing = await redis.get(pref_key)
        if existing:
            preferences = json.loads(existing)
        else:
            preferences = {
                "interests": [],
                "response_style": "balanced",
                "communication_preference": "casual",
                "help_topics": [],
                "learning_style": "mixed"
            }
        
        # Infer interests from message content
        new_interests = self._extract_interests(message)
        for interest in new_interests:
            if interest not in preferences["interests"]:
                preferences["interests"].append(interest)
        
        # Keep only top 10 interests
        preferences["interests"] = preferences["interests"][:10]
        
        # Infer response style preference from message length and emotion
        if len(message) > 100 and emotion_data.get("compound", 0) > 0:
            preferences["response_style"] = "detailed"
        elif len(message) < 50:
            preferences["response_style"] = "concise"
        
        await redis.setex(pref_key, 86400 * 30, json.dumps(preferences))
    
    def _extract_topics(self, message: str) -> List[str]:
        """Simple topic extraction"""
        # This is a simplified version - in production, use proper NLP
        topics = []
        topic_keywords = {
            "technology": ["tech", "computer", "software", "AI", "programming"],
            "health": ["health", "exercise", "diet", "wellness", "medical"],
            "business": ["business", "work", "career", "job", "company"],
            "entertainment": ["movie", "music", "game", "TV", "book"],
            "science": ["science", "research", "study", "experiment"],
            "travel": ["travel", "trip", "vacation", "visit", "explore"]
        }
        
        message_lower = message.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def _extract_interests(self, message: str) -> List[str]:
        """Extract potential interests from message"""
        interests = []
        interest_patterns = [
            "I love", "I enjoy", "I'm interested in", "I like", "passionate about",
            "hobby", "favorite", "into", "fan of"
        ]
        
        message_lower = message.lower()
        for pattern in interest_patterns:
            if pattern in message_lower:
                # Extract words after the pattern (simplified)
                parts = message_lower.split(pattern)
                if len(parts) > 1:
                    following_words = parts[1].split()[:3]  # Get next 3 words
                    interests.extend(following_words)
        
        return [word.strip(".,!?") for word in interests if len(word) > 2]
    
    def _count_formal_indicators(self, message: str) -> int:
        """Count formal language indicators"""
        formal_words = ["however", "therefore", "furthermore", "consequently", "nevertheless"]
        return sum(1 for word in formal_words if word in message.lower())
    
    def _count_casual_indicators(self, message: str) -> int:
        """Count casual language indicators"""
        casual_words = ["hey", "yeah", "gonna", "wanna", "kinda", "sorta", "lol", "haha"]
        return sum(1 for word in casual_words if word in message.lower())
    
    def _count_technical_terms(self, message: str) -> int:
        """Count technical terms (simplified)"""
        tech_terms = ["API", "database", "algorithm", "function", "variable", "server", "client"]
        return sum(1 for term in tech_terms if term in message)
    
    def _recommend_tone(self, context: Dict, emotion_data: Dict) -> str:
        """Recommend response tone"""
        user_emotion = emotion_data.get("primary_emotion", "neutral")
        
        if user_emotion in ["sadness", "fear", "stress"]:
            return "supportive"
        elif user_emotion in ["joy", "excitement"]:
            return "enthusiastic"
        elif user_emotion == "anger":
            return "calm"
        else:
            return "friendly"
    
    def _recommend_length(self, context: Dict) -> str:
        """Recommend response length"""
        style = context.get("conversation_style", {})
        avg_length = style.get("avg_message_length", 50)
        
        if avg_length > 150:
            return "detailed"
        elif avg_length < 50:
            return "brief"
        else:
            return "moderate"
    
    def _recommend_style(self, context: Dict) -> str:
        """Recommend response style"""
        style = context.get("conversation_style", {})
        formality = style.get("formality_score", 0)
        
        if formality > 2:
            return "formal"
        elif formality < -2:
            return "casual"
        else:
            return "balanced"
    
    def _recommend_topics(self, context: Dict, message: str) -> List[str]:
        """Recommend topics to explore"""
        recent_topics = context.get("recent_topics", [])
        interests = context.get("preferences", {}).get("interests", [])
        
        # Combine recent topics and interests
        recommendations = []
        
        # Add related topics
        for topic_info in recent_topics[:3]:
            if isinstance(topic_info, dict):
                recommendations.append(topic_info.get("topic", ""))
            else:
                recommendations.append(topic_info)
        
        # Add interests
        recommendations.extend(interests[:2])
        
        return [topic for topic in recommendations if topic]
    
    def _get_topics_to_avoid(self, context: Dict) -> List[str]:
        """Get topics that might be sensitive for this user"""
        # This would be based on negative emotional responses to certain topics
        # For now, return empty list
        return []
    
    def _get_personalization_triggers(self, context: Dict) -> List[str]:
        """Get triggers for personalization"""
        triggers = []
        
        preferences = context.get("preferences", {})
        if preferences.get("interests"):
            triggers.append("mention_interests")
        
        style = context.get("conversation_style", {})
        if style.get("technical_level", 0) > 0.5:
            triggers.append("use_technical_language")
        
        if style.get("formality_score", 0) > 1:
            triggers.append("use_formal_tone")
        
        return triggers
    
    def _analyze_activity_times(self, patterns: Dict) -> Dict[str, Any]:
        """Analyze when user is most active"""
        time_patterns = patterns.get("time_patterns", [])
        
        if not time_patterns:
            return {"most_active_hour": None, "most_active_day": None}
        
        hours = [t["hour"] for t in time_patterns]
        days = [t["day_of_week"] for t in time_patterns]
        
        most_active_hour = Counter(hours).most_common(1)[0][0] if hours else None
        most_active_day = Counter(days).most_common(1)[0][0] if days else None
        
        return {
            "most_active_hour": most_active_hour,
            "most_active_day": most_active_day,
            "activity_distribution": dict(Counter(hours))
        }
    
    def _analyze_preferred_topics(self, context: Dict) -> List[str]:
        """Analyze user's preferred topics"""
        topics = context.get("recent_topics", [])
        if not topics:
            return []
        
        # Sort by count if available
        if topics and isinstance(topics[0], dict):
            sorted_topics = sorted(topics, key=lambda x: x.get("count", 0), reverse=True)
            return [t["topic"] for t in sorted_topics[:5]]
        
        return topics[:5]
    
    def _analyze_communication_style(self, context: Dict) -> Dict[str, Any]:
        """Analyze user's communication style"""
        style = context.get("conversation_style", {})
        
        return {
            "formality": "formal" if style.get("formality_score", 0) > 1 else "casual",
            "technical_level": "high" if style.get("technical_level", 0) > 0.5 else "low",
            "verbosity": "verbose" if style.get("avg_message_length", 50) > 100 else "concise"
        }
    
    def _analyze_emotion_patterns(self, patterns: Dict) -> Dict[str, Any]:
        """Analyze user's emotional patterns"""
        emotions = patterns.get("emotion_history", [])
        
        if not emotions:
            return {"dominant_emotion": "neutral", "average_sentiment": 0}
        
        emotion_counts = Counter([e["emotion"] for e in emotions])
        sentiments = [e["compound"] for e in emotions]
        
        return {
            "dominant_emotion": emotion_counts.most_common(1)[0][0],
            "average_sentiment": sum(sentiments) / len(sentiments),
            "emotion_distribution": dict(emotion_counts)
        }
    
    def _calculate_engagement_metrics(self, patterns: Dict) -> Dict[str, Any]:
        """Calculate user engagement metrics"""
        return {
            "total_messages": patterns.get("message_count", 0),
            "avg_message_length": patterns.get("avg_message_length", 0),
            "engagement_score": min(patterns.get("message_count", 0) / 10, 1.0)  # Simple scoring
        }
    
    def _infer_learning_preferences(self, context: Dict) -> Dict[str, str]:
        """Infer how user prefers to learn"""
        style = context.get("conversation_style", {})
        
        preferences = {}
        
        if style.get("avg_message_length", 50) > 100:
            preferences["detail_level"] = "comprehensive"
        else:
            preferences["detail_level"] = "concise"
        
        if style.get("technical_level", 0) > 0.5:
            preferences["complexity"] = "advanced"
        else:
            preferences["complexity"] = "beginner"
        
        return preferences
    
    def _analyze_response_preferences(self, patterns: Dict) -> Dict[str, Any]:
        """Analyze what type of responses user prefers"""
        # This would analyze response effectiveness data
        # For now, return basic preferences
        return {
            "preferred_length": "moderate",
            "preferred_tone": "friendly",
            "include_examples": True,
            "include_questions": False
        }
    
    async def health_check(self) -> bool:
        """Check if personalization service is working"""
        try:
            # Simple health check
            test_context = await self.get_user_context(999999, 999999, type('MockRedis', (), {'get': lambda self, key: None})())
            return isinstance(test_context, dict)
        except Exception as e:
            logger.error(f"Personalization service health check failed: {str(e)}")
            return False

# Create singleton instance
personalization_service = PersonalizationService()