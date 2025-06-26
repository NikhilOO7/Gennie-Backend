from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from typing import Dict, Any, List
import logging
import re
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class EmotionService:
    """
    Advanced emotion detection and sentiment analysis service
    """
    
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        self.emotion_keywords = {
            "joy": ["happy", "excited", "joyful", "cheerful", "delighted", "pleased", "glad", "thrilled"],
            "sadness": ["sad", "depressed", "disappointed", "upset", "down", "blue", "melancholy"],
            "anger": ["angry", "mad", "furious", "irritated", "annoyed", "frustrated", "livid"],
            "fear": ["scared", "afraid", "anxious", "worried", "nervous", "terrified", "frightened"],
            "surprise": ["surprised", "shocked", "amazed", "astonished", "stunned", "bewildered"],
            "disgust": ["disgusted", "revolted", "repulsed", "sickened", "appalled"],
            "love": ["love", "adore", "cherish", "treasure", "devoted", "affectionate"],
            "gratitude": ["grateful", "thankful", "appreciative", "blessed", "obliged"],
            "excitement": ["excited", "thrilled", "pumped", "enthusiastic", "eager"],
            "confusion": ["confused", "puzzled", "perplexed", "bewildered", "lost"],
            "stress": ["stressed", "overwhelmed", "pressured", "tense", "strained"],
            "hope": ["hopeful", "optimistic", "confident", "positive", "encouraged"]
        }
        
    async def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """
        Comprehensive emotion analysis combining multiple approaches
        """
        try:
            # Clean and prepare text
            clean_text = self._clean_text(text)
            
            # VADER sentiment analysis
            vader_scores = self.vader_analyzer.polarity_scores(clean_text)
            
            # TextBlob sentiment analysis
            blob = TextBlob(clean_text)
            textblob_sentiment = blob.sentiment
            
            # Keyword-based emotion detection
            emotions = self._detect_emotions_by_keywords(clean_text)
            
            # Intensity analysis
            intensity = self._analyze_intensity(clean_text)
            
            # Confidence scoring
            confidence = self._calculate_confidence(vader_scores, textblob_sentiment, emotions)
            
            # Overall classification
            primary_emotion = self._classify_primary_emotion(vader_scores, emotions)
            
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "text_length": len(text),
                
                # VADER scores
                "compound": vader_scores["compound"],
                "positive": vader_scores["pos"],
                "negative": vader_scores["neg"],
                "neutral": vader_scores["neu"],
                
                # TextBlob scores
                "polarity": textblob_sentiment.polarity,
                "subjectivity": textblob_sentiment.subjectivity,
                
                # Emotion categories
                "emotions": emotions,
                "primary_emotion": primary_emotion,
                "intensity": intensity,
                "confidence": confidence,
                
                # Additional metadata
                "sentiment_label": self._get_sentiment_label(vader_scores["compound"]),
                "emotional_state": self._get_emotional_state(vader_scores, emotions),
                "suggestions": self._get_response_suggestions(primary_emotion, intensity)
            }
            
            logger.info(f"Emotion analysis complete: {primary_emotion} (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in emotion analysis: {str(e)}")
            return self._get_default_emotion_data()
    
    async def analyze_conversation_mood(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze the overall mood of a conversation
        """
        try:
            if not messages:
                return {"mood": "neutral", "trend": "stable", "confidence": 0.0}
            
            sentiment_scores = []
            emotions_count = {}
            
            for msg in messages:
                if msg.get("emotion_data"):
                    compound = msg["emotion_data"].get("compound", 0)
                    sentiment_scores.append(compound)
                    
                    primary_emotion = msg["emotion_data"].get("primary_emotion", "neutral")
                    emotions_count[primary_emotion] = emotions_count.get(primary_emotion, 0) + 1
            
            if not sentiment_scores:
                return {"mood": "neutral", "trend": "stable", "confidence": 0.0}
            
            # Calculate trend
            if len(sentiment_scores) >= 3:
                recent_avg = sum(sentiment_scores[-3:]) / 3
                early_avg = sum(sentiment_scores[:3]) / 3
                if recent_avg > early_avg + 0.1:
                    trend = "improving"
                elif recent_avg < early_avg - 0.1:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
            
            # Overall mood
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            if avg_sentiment > 0.2:
                mood = "positive"
            elif avg_sentiment < -0.2:
                mood = "negative"
            else:
                mood = "neutral"
            
            # Dominant emotion
            dominant_emotion = max(emotions_count, key=emotions_count.get) if emotions_count else "neutral"
            
            return {
                "mood": mood,
                "trend": trend,
                "dominant_emotion": dominant_emotion,
                "average_sentiment": round(avg_sentiment, 3),
                "message_count": len(messages),
                "confidence": min(len(sentiment_scores) / 10, 1.0),  # Higher confidence with more messages
                "emotions_distribution": emotions_count
            }
            
        except Exception as e:
            logger.error(f"Error analyzing conversation mood: {str(e)}")
            return {"mood": "neutral", "trend": "stable", "confidence": 0.0}
    
    async def get_emotion_insights(self, emotion_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate insights from emotion history
        """
        try:
            if not emotion_history:
                return {"insights": [], "patterns": [], "recommendations": []}
            
            insights = []
            patterns = []
            recommendations = []
            
            # Analyze patterns
            emotions = [entry.get("primary_emotion", "neutral") for entry in emotion_history]
            sentiment_scores = [entry.get("compound", 0) for entry in emotion_history]
            
            # Most common emotions
            emotion_counts = {}
            for emotion in emotions:
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
            most_common = max(emotion_counts, key=emotion_counts.get)
            insights.append(f"Your most common emotional state is {most_common}")
            
            # Sentiment trend
            if len(sentiment_scores) >= 5:
                recent_trend = sum(sentiment_scores[-5:]) / 5
                overall_avg = sum(sentiment_scores) / len(sentiment_scores)
                
                if recent_trend > overall_avg + 0.1:
                    insights.append("Your recent emotional trend is more positive than usual")
                elif recent_trend < overall_avg - 0.1:
                    insights.append("Your recent emotional trend is more negative than usual")
            
            # Patterns
            if emotion_counts.get("stress", 0) > len(emotions) * 0.3:
                patterns.append("High stress levels detected frequently")
                recommendations.append("Consider stress management techniques or breaks")
            
            if emotion_counts.get("joy", 0) > len(emotions) * 0.4:
                patterns.append("Generally positive emotional state")
                recommendations.append("Keep up the positive energy!")
            
            return {
                "insights": insights,
                "patterns": patterns,
                "recommendations": recommendations,
                "emotion_distribution": emotion_counts,
                "average_sentiment": round(sum(sentiment_scores) / len(sentiment_scores), 3)
            }
            
        except Exception as e:
            logger.error(f"Error generating emotion insights: {str(e)}")
            return {"insights": [], "patterns": [], "recommendations": []}
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for analysis"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _detect_emotions_by_keywords(self, text: str) -> Dict[str, float]:
        """Detect emotions based on keyword matching"""
        text_lower = text.lower()
        emotions = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            emotions[emotion] = count / len(keywords)  # Normalize by number of keywords
        
        return emotions
    
    def _analyze_intensity(self, text: str) -> float:
        """Analyze the intensity of emotions in text"""
        # Count exclamation marks, capital letters, etc.
        exclamations = text.count('!')
        capitals = sum(1 for c in text if c.isupper())
        total_chars = len(text)
        
        intensity = (exclamations * 0.3 + (capitals / total_chars if total_chars > 0 else 0) * 0.7)
        return min(intensity, 1.0)  # Cap at 1.0
    
    def _calculate_confidence(self, vader_scores: Dict, textblob_sentiment, emotions: Dict) -> float:
        """Calculate confidence in emotion analysis"""
        # Base confidence on agreement between methods
        vader_abs = abs(vader_scores["compound"])
        textblob_abs = abs(textblob_sentiment.polarity)
        
        # Agreement between VADER and TextBlob
        agreement = 1 - abs(vader_scores["compound"] - textblob_sentiment.polarity) / 2
        
        # Strength of signal
        signal_strength = (vader_abs + textblob_abs) / 2
        
        # Emotion keyword presence
        emotion_signal = max(emotions.values()) if emotions else 0
        
        confidence = (agreement * 0.4 + signal_strength * 0.4 + emotion_signal * 0.2)
        return min(confidence, 1.0)
    
    def _classify_primary_emotion(self, vader_scores: Dict, emotions: Dict) -> str:
        """Classify the primary emotion"""
        compound = vader_scores["compound"]
        
        # Find strongest keyword-based emotion
        if emotions:
            max_emotion = max(emotions, key=emotions.get)
            if emotions[max_emotion] > 0.1:  # Threshold for keyword detection
                return max_emotion
        
        # Fall back to sentiment-based classification
        if compound >= 0.3:
            return "joy"
        elif compound <= -0.3:
            return "sadness"
        else:
            return "neutral"
    
    def _get_sentiment_label(self, compound: float) -> str:
        """Get human-readable sentiment label"""
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        else:
            return "neutral"
    
    def _get_emotional_state(self, vader_scores: Dict, emotions: Dict) -> str:
        """Get overall emotional state description"""
        compound = vader_scores["compound"]
        
        if compound >= 0.5:
            return "very_positive"
        elif compound >= 0.1:
            return "positive"
        elif compound <= -0.5:
            return "very_negative"
        elif compound <= -0.1:
            return "negative"
        else:
            return "neutral"
    
    def _get_response_suggestions(self, primary_emotion: str, intensity: float) -> List[str]:
        """Get suggestions for how to respond to this emotion"""
        suggestions = []
        
        emotion_responses = {
            "sadness": ["Express empathy", "Offer support", "Ask if they want to talk about it"],
            "anger": ["Acknowledge their feelings", "Remain calm", "Ask what's bothering them"],
            "joy": ["Share in their happiness", "Ask for more details", "Celebrate with them"],
            "fear": ["Provide reassurance", "Offer practical help", "Listen actively"],
            "stress": ["Suggest taking a break", "Offer to help prioritize", "Recommend relaxation"],
            "confusion": ["Ask clarifying questions", "Break down complex topics", "Provide examples"],
            "gratitude": ["Accept graciously", "Share in the positive moment", "Ask what made them grateful"]
        }
        
        if primary_emotion in emotion_responses:
            suggestions = emotion_responses[primary_emotion]
        else:
            suggestions = ["Listen actively", "Respond naturally", "Match their energy level"]
        
        # Adjust for intensity
        if intensity > 0.7:
            suggestions.append("Acknowledge the strong emotions")
        
        return suggestions
    
    def _get_default_emotion_data(self) -> Dict[str, Any]:
        """Return default emotion data when analysis fails"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 1.0,
            "polarity": 0.0,
            "subjectivity": 0.0,
            "emotions": {},
            "primary_emotion": "neutral",
            "intensity": 0.0,
            "confidence": 0.0,
            "sentiment_label": "neutral",
            "emotional_state": "neutral",
            "suggestions": ["Respond naturally"],
            "error": True
        }
    
    async def health_check(self) -> bool:
        """Check if emotion service is working"""
        try:
            test_result = await self.analyze_emotion("I am happy today!")
            return test_result.get("primary_emotion") is not None
        except Exception as e:
            logger.error(f"Emotion service health check failed: {str(e)}")
            return False

# Create singleton instance
emotion_service = EmotionService()