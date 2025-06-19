from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class EmotionService:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        
    async def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """Analyze emotion in text using VADER sentiment analysis"""
        try:
            # Get VADER scores
            scores = self.analyzer.polarity_scores(text)
            
            # Determine primary emotion
            primary_emotion = self._determine_primary_emotion(scores)
            
            # Enhanced emotion detection
            enhanced_emotion = self._enhance_emotion_detection(text, scores)
            
            # Calculate intensity
            intensity = max(abs(scores['pos']), abs(scores['neg']), abs(scores['neu']))
            
            return {
                "primary_emotion": primary_emotion,
                "enhanced_emotion": enhanced_emotion,
                "intensity": intensity,
                "confidence": abs(scores['compound']),
                "scores": scores,
                "text_length": len(text.split())
            }
            
        except Exception as e:
            logger.error(f"Emotion analysis error: {str(e)}")
            return {
                "primary_emotion": "neutral",
                "enhanced_emotion": "neutral",
                "intensity": 0.5,
                "confidence": 0.5,
                "scores": {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0},
                "text_length": len(text.split()) if text else 0
            }
    
    def _determine_primary_emotion(self, scores: Dict[str, float]) -> str:
        """Determine primary emotion from VADER scores"""
        compound = scores['compound']
        
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        else:
            return "neutral"
    
    def _enhance_emotion_detection(self, text: str, scores: Dict[str, float]) -> str:
        """Enhanced emotion detection with keyword analysis"""
        text_lower = text.lower()
        
        # Positive emotions
        if any(word in text_lower for word in ['excited', 'thrilled', 'amazing', 'fantastic']):
            return "excited"
        elif any(word in text_lower for word in ['happy', 'joy', 'glad', 'cheerful']):
            return "happy"
        elif any(word in text_lower for word in ['love', 'adore', 'wonderful']):
            return "love"
        
        # Negative emotions
        elif any(word in text_lower for word in ['sad', 'depressed', 'down', 'upset']):
            return "sad"
        elif any(word in text_lower for word in ['angry', 'mad', 'furious', 'irritated']):
            return "angry"
        elif any(word in text_lower for word in ['anxious', 'worried', 'nervous', 'stress']):
            return "anxious"
        elif any(word in text_lower for word in ['frustrated', 'annoyed', 'bothered']):
            return "frustrated"
        
        # Neutral emotions
        elif any(word in text_lower for word in ['confused', 'unsure', 'uncertain']):
            return "confused"
        elif any(word in text_lower for word in ['tired', 'exhausted', 'weary']):
            return "tired"
        
        # Fall back to primary emotion
        return self._determine_primary_emotion(scores)

# Create global instance
emotion_service = EmotionService()