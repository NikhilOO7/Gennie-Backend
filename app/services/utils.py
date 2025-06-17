import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)

class UtilsService:
    """Utility functions for the AI chatbot"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text input"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove potentially harmful characters
        text = re.sub(r'[<>{}]', '', text)
        
        return text
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 4000) -> str:
        """Truncate text to maximum length"""
        if not text or len(text) <= max_length:
            return text
        
        # Try to truncate at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        # Find the latest sentence ending
        sentence_end = max(last_period, last_exclamation, last_question)
        
        if sentence_end > max_length * 0.7:  # If we can preserve at least 70% of content
            return truncated[:sentence_end + 1]
        else:
            return truncated + "..."
    
    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text (simple implementation)"""
        if not text:
            return []
        
        # Simple keyword extraction - remove common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'throughout',
            'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'can',
            'may', 'might', 'must', 'shall', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Extract words, convert to lowercase, filter out common words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in common_words]
        
        # Count frequency and return most common
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_keywords]]
    
    @staticmethod
    def generate_chat_summary(messages: List[Dict[str, Any]]) -> str:
        """Generate a summary of chat messages"""
        if not messages:
            return "No messages in chat"
        
        total_messages = len(messages)
        user_messages = [msg for msg in messages if msg.get('is_from_user', False)]
        ai_messages = [msg for msg in messages if not msg.get('is_from_user', True)]
        
        # Extract keywords from user messages
        all_user_text = " ".join([msg.get('content', '') for msg in user_messages])
        keywords = UtilsService.extract_keywords(all_user_text, 5)
        
        summary = f"Chat with {total_messages} messages ({len(user_messages)} from user, {len(ai_messages)} from AI)"
        if keywords:
            summary += f". Main topics: {', '.join(keywords)}"
        
        return summary
    
    @staticmethod
    def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
        """Calculate estimated reading time in seconds"""
        if not text:
            return 0
        
        word_count = len(text.split())
        reading_time_minutes = word_count / words_per_minute
        return max(1, int(reading_time_minutes * 60))  # At least 1 second
    
    @staticmethod
    def format_response_for_mobile(response: str, max_length: int = 2000) -> Dict[str, Any]:
        """Format AI response for mobile display"""
        # Truncate if too long
        formatted_response = UtilsService.truncate_text(response, max_length)
        
        # Calculate metrics
        word_count = len(formatted_response.split())
        char_count = len(formatted_response)
        reading_time = UtilsService.calculate_reading_time(formatted_response)
        
        # Check if response was truncated
        was_truncated = len(response) != len(formatted_response)
        
        return {
            "text": formatted_response,
            "metadata": {
                "word_count": word_count,
                "character_count": char_count,
                "reading_time_seconds": reading_time,
                "was_truncated": was_truncated,
                "original_length": len(response) if was_truncated else char_count
            }
        }
    
    @staticmethod
    def sanitize_json_string(data: str) -> Optional[Dict]:
        """Safely parse JSON string with error handling"""
        if not data:
            return None
        
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return None
    
    @staticmethod
    def generate_conversation_hash(messages: List[str]) -> str:
        """Generate a hash for conversation messages (for caching/deduplication)"""
        if not messages:
            return ""
        
        # Create a string from all messages
        conversation_string = "|".join(messages)
        
        # Generate SHA256 hash
        return hashlib.sha256(conversation_string.encode()).hexdigest()[:16]
    
    @staticmethod
    def time_ago(timestamp: datetime) -> str:
        """Convert timestamp to human-readable 'time ago' format"""
        now = datetime.utcnow()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    @staticmethod
    def validate_message_content(content: str) -> Dict[str, Any]:
        """Validate message content and return validation result"""
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not content or not content.strip():
            result["is_valid"] = False
            result["errors"].append("Message content cannot be empty")
            return result
        
        # Check length
        if len(content) > 4000:
            result["warnings"].append("Message is very long and may be truncated")
        
        # Check for potential spam patterns
        if len(set(content.split())) < len(content.split()) * 0.3:  # Too much repetition
            result["warnings"].append("Message contains repetitive content")
        
        # Check for excessive special characters
        special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', content)) / len(content)
        if special_char_ratio > 0.3:
            result["warnings"].append("Message contains many special characters")
        
        return result

# Global service instance
utils_service = UtilsService()