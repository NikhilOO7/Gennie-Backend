from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from typing import Dict, Any
import re

class EmotionService:
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Emotion keywords mapping
        self.emotion_keywords = {
            'happy': ['happy', 'joy', 'excited', 'cheerful', 'glad', 'pleased', 'delighted', 'thrilled'],
            'sad': ['sad', 'depressed', 'down', 'blue', 'melancholy', 'sorrowful', 'dejected'],
            'angry': ['angry', 'mad', 'furious', 'rage', 'irritated', 'annoyed', 'frustrated'],
            'fear': ['afraid', 'scared', 'terrified', 'anxious', 'worried', 'nervous', 'fearful'],
            'surprise': ['surprised', 'shocked', 'amazed', 'astonished', 'startled', 'stunned'],
            'disgust': ['disgusted', 'revolted', 'repulsed', 'sickened', 'appalled'],
            'love': ['love', 'adore', 'cherish', 'affection', 'fond', 'devoted', 'romantic'],
            'trust': ['trust', 'confident', 'reliable', 'faith', 'believe', 'depend'],
            'anticipation': ['anticipate', 'expect', 'looking forward', 'eager', 'hopeful']
        }
    
    async def analyze_emotion(self, text: str) -> Dict[str, Any]:
        """Comprehensive emotion analysis using multiple methods"""
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # VADER sentiment analysis
        vader_scores = self.vader_analyzer.polarity_scores(cleaned_text)
        
        # TextBlob analysis
        blob = TextBlob(cleaned_text)
        textblob_sentiment = blob.sentiment
        
        # Keyword-based emotion detection
        keyword_emotions = self._detect_keyword_emotions(cleaned_text)
        
        # Combine results
        primary_emotion = self._determine_primary_emotion(vader_scores, keyword_emotions)
        intensity = self._calculate_intensity(vader_scores, textblob_sentiment)
        
        return {
            'emotion': primary_emotion,
            'intensity': intensity,
            'sentiment': self._get_sentiment_label(vader_scores['compound']),
            'sentiment_score': vader_scores['compound'],
            'confidence': self._calculate_confidence(vader_scores, keyword_emotions),
            'detailed_scores': {
                'vader': vader_scores,
                'textblob': {
                    'polarity': textblob_sentiment.polarity,
                    'subjectivity': textblob_sentiment.subjectivity
                },
                'keyword_emotions': keyword_emotions
            },
            'analysis_method': 'hybrid'
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for analysis"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep punctuation for sentiment
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        return text.lower()
    
    def _detect_keyword_emotions(self, text: str) -> Dict[str, int]:
        """Detect emotions based on keyword matching"""
        emotion_counts = {}
        words = text.split()
        
        for emotion, keywords in self.emotion_keywords.items():
            count = sum(1 for word in words if any(keyword in word for keyword in keywords))
            if count > 0:
                emotion_counts[emotion] = count
        
        return emotion_counts
    
    def _determine_primary_emotion(self, vader_scores: Dict, keyword_emotions: Dict) -> str:
        """Determine primary emotion from analysis results"""
        # If keyword emotions found, use the most frequent
        if keyword_emotions:
            return max(keyword_emotions, key=keyword_emotions.get)
        
        # Fall back to VADER sentiment mapping
        compound = vader_scores['compound']
        
        if compound >= 0.5:
            return 'happy'
        elif compound <= -0.5:
            if vader_scores['neg'] > 0.3:
                return 'angry'
            else:
                return 'sad'
        elif abs(compound) < 0.1:
            return 'neutral'
        elif compound > 0:
            return 'content'
        else:
            return 'concerned'
    
    def _calculate_intensity(self, vader_scores: Dict, textblob_sentiment) -> float:
        """Calculate emotion intensity"""
        vader_intensity = abs(vader_scores['compound'])
        textblob_intensity = abs(textblob_sentiment.polarity)
        
        # Average the intensities
        combined_intensity = (vader_intensity + textblob_intensity) / 2
        
        # Normalize to 0-1 range
        return min(max(combined_intensity, 0.0), 1.0)
    
    def _get_sentiment_label(self, compound_score: float) -> str:
        """Convert compound score to sentiment label"""
        if compound_score >= 0.05:
            return 'positive'
        elif compound_score <= -0.05:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_confidence(self, vader_scores: Dict, keyword_emotions: Dict) -> float:
        """Calculate confidence in emotion analysis"""
        # Higher confidence if both methods agree
        base_confidence = abs(vader_scores['compound'])
        
        # Boost confidence if keywords were found
        if keyword_emotions:
            base_confidence = min(base_confidence + 0.2, 1.0)
        
        # Reduce confidence for very neutral scores
        if abs(vader_scores['compound']) < 0.1:
            base_confidence *= 0.5
        
        return round(base_confidence, 2)

# Global instance
emotion_service = EmotionService()