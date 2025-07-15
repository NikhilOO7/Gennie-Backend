"""
Topics Service - Handle topic personalization and recommendations
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from collections import Counter

from app.models.user_preference import UserPreference
from app.models.chat import Chat
from app.models.message import Message

logger = logging.getLogger(__name__)

class TopicsService:
    """Service for managing user topic interests and recommendations"""
    
    AVAILABLE_TOPICS = [
        {"id": "tech", "name": "Technology", "icon": "💻", "description": "Latest tech trends, gadgets, and innovations"},
        {"id": "science", "name": "Science", "icon": "🔬", "description": "Scientific discoveries and research"},
        {"id": "health", "name": "Health & Fitness", "icon": "🏃‍♂️", "description": "Wellness, nutrition, and exercise"},
        {"id": "cooking", "name": "Cooking", "icon": "🍳", "description": "Recipes, techniques, and culinary arts"},
        {"id": "travel", "name": "Travel", "icon": "✈️", "description": "Destinations, tips, and adventures"},
        {"id": "music", "name": "Music", "icon": "🎵", "description": "Genres, artists, and music theory"},
        {"id": "art", "name": "Art & Design", "icon": "🎨", "description": "Visual arts, design, and creativity"},
        {"id": "sports", "name": "Sports", "icon": "⚽", "description": "Sports news, analysis, and fitness"},
        {"id": "gaming", "name": "Gaming", "icon": "🎮", "description": "Video games, esports, and gaming culture"},
        {"id": "books", "name": "Books & Literature", "icon": "📚", "description": "Reading recommendations and literary discussions"},
        {"id": "movies", "name": "Movies & TV", "icon": "🎬", "description": "Film, television, and entertainment"},
        {"id": "business", "name": "Business", "icon": "💼", "description": "Entrepreneurship, management, and economics"},
        {"id": "finance", "name": "Finance", "icon": "💰", "description": "Personal finance, investing, and markets"},
        {"id": "history", "name": "History", "icon": "📜", "description": "Historical events and perspectives"},
        {"id": "philosophy", "name": "Philosophy", "icon": "🤔", "description": "Philosophical ideas and ethical discussions"},
        {"id": "nature", "name": "Nature", "icon": "🌿", "description": "Environment, wildlife, and outdoor activities"},
        {"id": "space", "name": "Space", "icon": "🚀", "description": "Astronomy, space exploration, and cosmos"},
        {"id": "fashion", "name": "Fashion", "icon": "👗", "description": "Style, trends, and fashion industry"},
        {"id": "cars", "name": "Cars", "icon": "🚗", "description": "Automotive news, reviews, and technology"},
        {"id": "pets", "name": "Pets", "icon": "🐕", "description": "Pet care, training, and animal welfare"}
    ]
    
    TOPIC_RELATIONSHIPS = {
        "tech": ["science", "gaming", "business"],
        "science": ["tech", "space", "philosophy"],
        "health": ["cooking", "sports", "nature"],
        "cooking": ["health", "travel", "art"],
        "travel": ["cooking", "history", "nature"],
        "music": ["art", "movies", "philosophy"],
        "art": ["music", "fashion", "philosophy"],
        "sports": ["health", "gaming", "nature"],
        "gaming": ["tech", "sports", "movies"],
        "books": ["philosophy", "history", "art"],
        "movies": ["music", "books", "gaming"],
        "business": ["tech", "finance", "philosophy"],
        "finance": ["business", "tech", "history"],
        "history": ["philosophy", "books", "travel"],
        "philosophy": ["science", "books", "art"],
        "nature": ["travel", "health", "space"],
        "space": ["science", "tech", "philosophy"],
        "fashion": ["art", "business", "travel"],
        "cars": ["tech", "sports", "business"],
        "pets": ["nature", "health", "books"]
    }
    
    def __init__(self):
        self.topics_dict = {topic["id"]: topic for topic in self.AVAILABLE_TOPICS}
    
    async def get_user_topics(self, db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """Get user's selected topics and related information"""
        try:
            # Get user preferences
            result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            user_pref = result.scalar_one_or_none()
            
            if not user_pref or not user_pref.preferences:
                selected_topics = ["tech", "health", "cooking"]  # Default topics
            else:
                selected_topics = user_pref.preferences.get("interests", [])
            
            # Get topic statistics
            topic_stats = await self._get_topic_stats(db, user_id, selected_topics)
            
            # Get recommendations
            recommendations = self._get_topic_recommendations(selected_topics)
            
            return {
                "selected_topics": selected_topics,
                "available_topics": self.AVAILABLE_TOPICS,
                "topic_stats": topic_stats,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to get user topics: {str(e)}")
            raise
    
    async def update_user_topics(self, db: AsyncSession, user_id: int, topics: List[str]) -> Dict[str, Any]:
        """Update user's topic interests"""
        try:
            # Validate topics
            valid_topics = [t for t in topics if t in self.topics_dict]
            
            # Get or create user preference
            result = await db.execute(
                select(UserPreference).where(UserPreference.user_id == user_id)
            )
            user_pref = result.scalar_one_or_none()
            
            if not user_pref:
                user_pref = UserPreference(user_id=user_id)
                db.add(user_pref)
            
            # Update topics
            user_pref.update_topic_interests(valid_topics)
            user_pref.last_interaction_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(user_pref)
            
            # Return updated data
            return await self.get_user_topics(db, user_id)
            
        except Exception as e:
            logger.error(f"Failed to update user topics: {str(e)}")
            await db.rollback()
            raise
    
    async def _get_topic_stats(self, db: AsyncSession, user_id: int, topics: List[str]) -> Dict[str, Any]:
        """Get statistics for user's topics"""
        try:
            # Count chats per topic
            chat_counts = {}
            for topic in topics:
                result = await db.execute(
                    select(func.count(Chat.id))
                    .where(Chat.user_id == user_id)
                    .where(Chat.related_topic == topic)
                    .where(Chat.is_deleted == False)
                )
                chat_counts[topic] = result.scalar() or 0
            
            # Get total topic-based chats
            result = await db.execute(
                select(func.count(Chat.id))
                .where(Chat.user_id == user_id)
                .where(Chat.related_topic.in_(topics))
                .where(Chat.is_deleted == False)
            )
            total_topic_chats = result.scalar() or 0
            
            return {
                "chat_counts": chat_counts,
                "total_topic_chats": total_topic_chats,
                "most_active_topic": max(chat_counts, key=chat_counts.get) if chat_counts else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get topic stats: {str(e)}")
            return {}
    
    def _get_topic_recommendations(self, selected_topics: List[str], max_recommendations: int = 3) -> List[Dict[str, Any]]:
        """Get topic recommendations based on current selections"""
        recommendations = Counter()
        
        # Count related topics
        for topic in selected_topics:
            if topic in self.TOPIC_RELATIONSHIPS:
                for related in self.TOPIC_RELATIONSHIPS[topic]:
                    if related not in selected_topics:
                        recommendations[related] += 1
        
        # Get top recommendations
        top_recommendations = recommendations.most_common(max_recommendations)
        
        return [
            self.topics_dict[topic_id]
            for topic_id, _ in top_recommendations
            if topic_id in self.topics_dict
        ]
    
    def get_topic_info(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific topic"""
        return self.topics_dict.get(topic_id)

# Create singleton instance
topics_service = TopicsService()