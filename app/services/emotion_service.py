"""
Emotion Analysis Service - Comprehensive emotion detection and analysis
with multiple analysis methods and advanced pattern recognition
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import json
import re

# Emotion analysis libraries
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import nltk

from app.config import settings

logger = logging.getLogger(__name__)

class EmotionService:
    """
    Comprehensive emotion analysis service with multiple detection methods
    """
    
    def __init__(self):
        """Initialize emotion analysis service"""
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Download required NLTK data
        self._ensure_nltk_data()
        
        # Emotion keywords mapping
        self.emotion_keywords = self._load_emotion_keywords()
        
        # Emotion patterns
        self.emotion_patterns = self._load_emotion_patterns()
        
        logger.info("Emotion analysis service initialized")
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded"""
        try:
            nltk.data.find('corpora/punkt')
        except LookupError:
            try:
                nltk.download('punkt', quiet=True)
            except Exception as e:
                logger.warning(f"Failed to download NLTK punkt data: {e}")
        
        try:
            nltk.data.find('corpora/brown')
        except LookupError:
            try:
                nltk.download('brown', quiet=True)
            except Exception as e:
                logger.warning(f"Failed to download NLTK brown corpus: {e}")
    
    def _load_emotion_keywords(self) -> Dict[str, List[str]]:
        """Load emotion keywords for pattern matching"""
        return {
            "joy": [
                "happy", "joy", "joyful", "excited", "thrilled", "delighted", 
                "pleased", "cheerful", "elated", "euphoric", "blissful", "content",
                "satisfied", "glad", "grateful", "amazed", "wonderful", "fantastic",
                "awesome", "brilliant", "excellent", "love", "adore", "celebrate"
            ],
            "sadness": [
                "sad", "sorrow", "grief", "melancholy", "depressed", "gloomy",
                "miserable", "unhappy", "dejected", "downcast", "heartbroken",
                "disappointed", "discouraged", "despondent", "blue", "tearful",
                "crying", "weeping", "mourning", "regret", "loss", "lonely"
            ],
            "anger": [
                "angry", "mad", "furious", "rage", "irate", "livid", "enraged",
                "infuriated", "annoyed", "irritated", "frustrated", "outraged",
                "hostile", "resentful", "bitter", "hate", "disgusted", "revolted",
                "appalled", "incensed", "seething", "fuming", "pissed"
            ],
            "fear": [
                "afraid", "scared", "frightened", "terrified", "anxious", "worried",
                "nervous", "panicked", "alarmed", "concerned", "apprehensive",
                "uneasy", "tense", "stressed", "paranoid", "phobic", "dreading",
                "intimidated", "threatened", "insecure", "vulnerable"
            ],
            "surprise": [
                "surprised", "shocked", "astonished", "amazed", "stunned", "bewildered",
                "confused", "perplexed", "baffled", "puzzled", "startled", "unexpected",
                "sudden", "wow", "unbelievable", "incredible", "remarkable"
            ],
            "disgust": [
                "disgusted", "revolted", "repulsed", "nauseated", "sickened",
                "appalled", "horrified", "repugnant", "offensive", "gross",
                "yuck", "eww", "terrible", "awful", "horrible"
            ],
            "contempt": [
                "contempt", "disdain", "scorn", "ridicule", "mock", "sneer",
                "despise", "loathe", "detest", "arrogant", "superior", "condescending"
            ],
            "excitement": [
                "excited", "thrilled", "enthusiastic", "eager", "energetic",
                "pumped", "stoked", "hyped", "fired up", "passionate", "dynamic"
            ],
            "anxiety": [
                "anxious", "worried", "stressed", "overwhelmed", "panicked",
                "restless", "agitated", "troubled", "disturbed", "frantic"
            ],
            "frustration": [
                "frustrated", "annoyed", "irritated", "exasperated", "fed up",
                "aggravated", "vexed", "bothered", "irked", "miffed"
            ],
            "contentment": [
                "content", "peaceful", "calm", "serene", "relaxed", "comfortable",
                "satisfied", "pleased", "at ease", "tranquil", "balanced"
            ]
        }
    
    def _load_emotion_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for emotion detection"""
        return {
            "joy": [
                r"\b(?:so|very|really|extremely)\s+(?:happy|excited|thrilled)\b",
                r"\b(?:love|adore|absolutely)\s+(?:this|it|that)\b",
                r"(?:!{2,}|\b(?:yay|woohoo|awesome|fantastic)\b)",
                r"\b(?:can't wait|looking forward)\b"
            ],
            "sadness": [
                r"\b(?:so|very|really|extremely)\s+(?:sad|depressed|down)\b",
                r"\b(?:feel|feeling)\s+(?:terrible|awful|horrible)\b",
                r"\b(?:wish|hope)\s+(?:things|life)\s+(?:were|was)\s+different\b",
                r"\b(?:miss|missing)\s+(?:you|him|her|them)\b"
            ],
            "anger": [
                r"\b(?:so|very|really|extremely)\s+(?:angry|mad|furious)\b",
                r"\b(?:hate|can't stand|despise)\b",
                r"\b(?:this|that)\s+(?:is|makes me)\s+(?:ridiculous|stupid)\b",
                r"(?:!{3,}|CAPS\s+WORDS)"
            ],
            "fear": [
                r"\b(?:so|very|really|extremely)\s+(?:scared|afraid|worried)\b",
                r"\b(?:what if|i'm afraid)\b",
                r"\b(?:nervous|anxious)\s+about\b",
                r"\b(?:terrified|petrified)\s+of\b"
            ]
        }
    
    async def analyze_emotion(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None,
        methods: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive emotion analysis using multiple methods
        """
        if not text or not text.strip():
            return self._create_neutral_result()
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Default methods if not specified
            if methods is None:
                methods = ["vader", "textblob", "keywords", "patterns"]
            
            results = {}
            
            # VADER sentiment analysis
            if "vader" in methods:
                results["vader"] = await self._analyze_with_vader(text)
            
            # TextBlob analysis
            if "textblob" in methods:
                results["textblob"] = await self._analyze_with_textblob(text)
            
            # Keyword-based analysis
            if "keywords" in methods:
                results["keywords"] = await self._analyze_with_keywords(text)
            
            # Pattern-based analysis
            if "patterns" in methods:
                results["patterns"] = await self._analyze_with_patterns(text)
            
            # Combine results
            combined_result = await self._combine_analysis_results(results, text, context)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            combined_result["processing_time"] = processing_time
            combined_result["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            logger.debug(
                f"Emotion analysis completed in {processing_time:.3f}s",
                extra={
                    "text_length": len(text),
                    "primary_emotion": combined_result.get("primary_emotion"),
                    "confidence": combined_result.get("confidence_score")
                }
            )
            
            return combined_result
        
        except Exception as e:
            logger.error(f"Emotion analysis failed: {str(e)}", exc_info=True)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time": processing_time,
                "primary_emotion": "neutral",
                "confidence_score": 0.0,
                "sentiment_score": 0.0
            }
    
    async def _analyze_with_vader(self, text: str) -> Dict[str, Any]:
        """Analyze emotion using VADER sentiment analysis"""
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            
            # Map compound score to emotions
            compound = scores["compound"]
            
            if compound >= 0.5:
                primary_emotion = "joy"
                confidence = min(compound, 1.0)
            elif compound <= -0.5:
                if scores["neg"] > 0.6:
                    primary_emotion = "anger" if "hate" in text.lower() or "angry" in text.lower() else "sadness"
                else:
                    primary_emotion = "sadness"
                confidence = min(abs(compound), 1.0)
            elif compound >= 0.1:
                primary_emotion = "contentment"
                confidence = compound
            elif compound <= -0.1:
                primary_emotion = "sadness"
                confidence = abs(compound)
            else:
                primary_emotion = "neutral"
                confidence = 1.0 - abs(compound)
            
            return {
                "method": "vader",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": compound,
                "emotion_scores": {
                    "positive": scores["pos"],
                    "negative": scores["neg"],
                    "neutral": scores["neu"],
                    "compound": compound
                },
                "raw_scores": scores
            }
        
        except Exception as e:
            logger.error(f"VADER analysis failed: {str(e)}")
            return {"method": "vader", "error": str(e)}
    
    async def _analyze_with_textblob(self, text: str) -> Dict[str, Any]:
        """Analyze emotion using TextBlob"""
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # Map polarity to emotions
            if polarity > 0.3:
                primary_emotion = "joy"
                confidence = min(polarity, 1.0)
            elif polarity < -0.3:
                primary_emotion = "sadness"
                confidence = min(abs(polarity), 1.0)
            elif polarity > 0.1:
                primary_emotion = "contentment"
                confidence = polarity
            elif polarity < -0.1:
                primary_emotion = "sadness"
                confidence = abs(polarity)
            else:
                primary_emotion = "neutral"
                confidence = 1.0 - abs(polarity)
            
            return {
                "method": "textblob",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": polarity,
                "subjectivity": subjectivity,
                "emotion_scores": {
                    "polarity": polarity,
                    "subjectivity": subjectivity
                }
            }
        
        except Exception as e:
            logger.error(f"TextBlob analysis failed: {str(e)}")
            return {"method": "textblob", "error": str(e)}
    
    async def _analyze_with_keywords(self, text: str) -> Dict[str, Any]:
        """Analyze emotion using keyword matching"""
        try:
            text_lower = text.lower()
            emotion_scores = {}
            
            for emotion, keywords in self.emotion_keywords.items():
                score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    if keyword in text_lower:
                        # Weight longer keywords more heavily
                        weight = len(keyword) / 10.0
                        score += weight
                        matched_keywords.append(keyword)
                
                if score > 0:
                    # Normalize score
                    emotion_scores[emotion] = min(score / len(keywords), 1.0)
            
            if not emotion_scores:
                primary_emotion = "neutral"
                confidence = 0.5
            else:
                primary_emotion = max(emotion_scores, key=emotion_scores.get)
                confidence = emotion_scores[primary_emotion]
            
            return {
                "method": "keywords",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": self._emotion_to_sentiment(primary_emotion),
                "emotion_scores": emotion_scores,
                "matched_keywords": matched_keywords if 'matched_keywords' in locals() else []
            }
        
        except Exception as e:
            logger.error(f"Keyword analysis failed: {str(e)}")
            return {"method": "keywords", "error": str(e)}
    
    async def _analyze_with_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze emotion using regex patterns"""
        try:
            emotion_scores = {}
            matched_patterns = {}
            
            for emotion, patterns in self.emotion_patterns.items():
                score = 0
                matches = []
                
                for pattern in patterns:
                    regex_matches = re.findall(pattern, text, re.IGNORECASE)
                    if regex_matches:
                        score += len(regex_matches)
                        matches.extend(regex_matches)
                
                if score > 0:
                    emotion_scores[emotion] = min(score / 10.0, 1.0)  # Normalize
                    matched_patterns[emotion] = matches
            
            if not emotion_scores:
                primary_emotion = "neutral"
                confidence = 0.5
            else:
                primary_emotion = max(emotion_scores, key=emotion_scores.get)
                confidence = emotion_scores[primary_emotion]
            
            return {
                "method": "patterns",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": self._emotion_to_sentiment(primary_emotion),
                "emotion_scores": emotion_scores,
                "matched_patterns": matched_patterns
            }
        
        except Exception as e:
            logger.error(f"Pattern analysis failed: {str(e)}")
            return {"method": "patterns", "error": str(e)}
    
    async def _combine_analysis_results(
        self, 
        results: Dict[str, Dict[str, Any]], 
        text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Combine results from multiple analysis methods"""
        
        valid_results = {k: v for k, v in results.items() if "error" not in v}
        
        if not valid_results:
            return self._create_neutral_result()
        
        # Weight different methods
        method_weights = {
            "vader": 0.4,
            "textblob": 0.3,
            "keywords": 0.2,
            "patterns": 0.1
        }
        
        # Aggregate emotion scores
        combined_emotion_scores = {}
        combined_sentiment = 0.0
        total_weight = 0.0
        
        for method, result in valid_results.items():
            weight = method_weights.get(method, 0.1)
            total_weight += weight
            
            # Add sentiment score
            if "sentiment_score" in result:
                combined_sentiment += result["sentiment_score"] * weight
            
            # Add emotion scores
            if "emotion_scores" in result and isinstance(result["emotion_scores"], dict):
                for emotion, score in result["emotion_scores"].items():
                    if isinstance(score, (int, float)):
                        if emotion not in combined_emotion_scores:
                            combined_emotion_scores[emotion] = 0.0
                        combined_emotion_scores[emotion] += score * weight
        
        # Normalize
        if total_weight > 0:
            combined_sentiment /= total_weight
            for emotion in combined_emotion_scores:
                combined_emotion_scores[emotion] /= total_weight
        
        # Determine primary emotion
        primary_emotion = "neutral"
        confidence = 0.5
        
        if combined_emotion_scores:
            # Find emotion with highest score
            emotion_candidates = {}
            for emotion, score in combined_emotion_scores.items():
                if emotion in self.emotion_keywords:  # Valid emotion
                    emotion_candidates[emotion] = score
            
            if emotion_candidates:
                primary_emotion = max(emotion_candidates, key=emotion_candidates.get)
                confidence = min(emotion_candidates[primary_emotion], 1.0)
        
        # Apply context adjustments if provided
        if context:
            primary_emotion, confidence = self._apply_context_adjustments(
                primary_emotion, confidence, context
            )
        
        return {
            "success": True,
            "primary_emotion": primary_emotion,
            "secondary_emotion": self._get_secondary_emotion(combined_emotion_scores, primary_emotion),
            "confidence_score": confidence,
            "sentiment_score": combined_sentiment,
            "emotion_scores": combined_emotion_scores,
            "emotion_intensity": self._calculate_intensity(confidence, combined_sentiment),
            "analysis_methods": list(valid_results.keys()),
            "detailed_results": results,
            "text_length": len(text),
            "context_applied": context is not None
        }
    
    def _get_secondary_emotion(self, emotion_scores: Dict[str, float], primary_emotion: str) -> Optional[str]:
        """Get secondary emotion from scores"""
        if not emotion_scores or len(emotion_scores) < 2:
            return None
        
        # Remove primary emotion and find next highest
        remaining_emotions = {k: v for k, v in emotion_scores.items() if k != primary_emotion}
        
        if remaining_emotions:
            secondary = max(remaining_emotions, key=remaining_emotions.get)
            # Only return if confidence is reasonable
            if remaining_emotions[secondary] > 0.3:
                return secondary
        
        return None
    
    def _calculate_intensity(self, confidence: float, sentiment: float) -> float:
        """Calculate emotion intensity"""
        # Combine confidence and absolute sentiment
        intensity = (confidence + abs(sentiment)) / 2.0
        return min(max(intensity, 0.0), 1.0)
    
    def _emotion_to_sentiment(self, emotion: str) -> float:
        """Convert emotion to sentiment score"""
        positive_emotions = {"joy", "excitement", "contentment", "surprise"}
        negative_emotions = {"sadness", "anger", "fear", "disgust", "contempt", "anxiety", "frustration"}
        
        if emotion in positive_emotions:
            return 0.5 if emotion == "contentment" else 0.7
        elif emotion in negative_emotions:
            return -0.5 if emotion in {"sadness", "anxiety"} else -0.7
        else:
            return 0.0
    
    def _apply_context_adjustments(
        self, 
        emotion: str, 
        confidence: float, 
        context: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Apply context-based adjustments to emotion detection"""
        
        # Historical emotion patterns
        if "recent_emotions" in context:
            recent_emotions = context["recent_emotions"]
            if recent_emotions and len(recent_emotions) > 0:
                # If user has been consistently sad, boost sadness detection
                recent_emotion_counts = {}
                for recent_emotion in recent_emotions[-5:]:  # Last 5 emotions
                    emotion_name = recent_emotion.get("primary_emotion", "neutral")
                    recent_emotion_counts[emotion_name] = recent_emotion_counts.get(emotion_name, 0) + 1
                
                if emotion in recent_emotion_counts:
                    # Boost confidence if emotion is consistent with recent pattern
                    boost = min(recent_emotion_counts[emotion] * 0.1, 0.3)
                    confidence = min(confidence + boost, 1.0)
        
        # Time-based adjustments
        if "time_context" in context:
            current_hour = datetime.now().hour
            if current_hour < 6 or current_hour > 22:  # Late night/early morning
                if emotion in {"anxiety", "sadness"}:
                    confidence = min(confidence * 1.2, 1.0)  # People often feel more anxious at night
        
        # Conversation context
        if "conversation_topic" in context:
            topic = context["conversation_topic"].lower()
            if "work" in topic or "job" in topic:
                if emotion in {"frustration", "anxiety"}:
                    confidence = min(confidence * 1.1, 1.0)
            elif "family" in topic or "relationship" in topic:
                if emotion in {"joy", "sadness"}:
                    confidence = min(confidence * 1.1, 1.0)
        
        return emotion, confidence
    
    def _create_neutral_result(self) -> Dict[str, Any]:
        """Create a neutral emotion result"""
        return {
            "success": True,
            "primary_emotion": "neutral",
            "secondary_emotion": None,
            "confidence_score": 0.5,
            "sentiment_score": 0.0,
            "emotion_scores": {"neutral": 0.5},
            "emotion_intensity": 0.0,
            "analysis_methods": [],
            "text_length": 0
        }
    
    async def analyze_emotion_patterns(
        self, 
        emotion_history: List[Dict[str, Any]], 
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Analyze emotion patterns over time"""
        
        if not emotion_history:
            return {"error": "No emotion history provided"}
        
        try:
            # Filter by time window
            cutoff_time = datetime.now(timezone.utc).timestamp() - (time_window_hours * 3600)
            recent_emotions = [
                e for e in emotion_history 
                if e.get("detected_at") and 
                datetime.fromisoformat(e["detected_at"].replace("Z", "+00:00")).timestamp() > cutoff_time
            ]
            
            if not recent_emotions:
                return {"error": "No recent emotions in time window"}
            
            # Calculate patterns
            emotion_counts = {}
            sentiment_scores = []
            intensity_scores = []
            
            for emotion_data in recent_emotions:
                primary_emotion = emotion_data.get("primary_emotion", "neutral")
                emotion_counts[primary_emotion] = emotion_counts.get(primary_emotion, 0) + 1
                
                if "sentiment_score" in emotion_data:
                    sentiment_scores.append(emotion_data["sentiment_score"])
                
                if "emotion_intensity" in emotion_data:
                    intensity_scores.append(emotion_data["emotion_intensity"])
            
            # Calculate statistics
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
            avg_intensity = sum(intensity_scores) / len(intensity_scores) if intensity_scores else 0.0
            
            # Determine dominant emotion
            dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"
            
            # Calculate emotional stability (variance in sentiment)
            if len(sentiment_scores) > 1:
                sentiment_variance = sum((s - avg_sentiment) ** 2 for s in sentiment_scores) / len(sentiment_scores)
                emotional_stability = max(0.0, 1.0 - sentiment_variance)
            else:
                emotional_stability = 1.0
            
            return {
                "success": True,
                "time_window_hours": time_window_hours,
                "emotion_count": len(recent_emotions),
                "dominant_emotion": dominant_emotion,
                "emotion_distribution": emotion_counts,
                "average_sentiment": avg_sentiment,
                "average_intensity": avg_intensity,
                "emotional_stability": emotional_stability,
                "sentiment_trend": self._calculate_sentiment_trend(sentiment_scores),
                "pattern_summary": self._generate_pattern_summary(
                    dominant_emotion, avg_sentiment, avg_intensity, emotional_stability
                )
            }
        
        except Exception as e:
            logger.error(f"Emotion pattern analysis failed: {str(e)}")
            return {"error": str(e), "error_type": type(e).__name__}
    
    def _calculate_sentiment_trend(self, sentiment_scores: List[float]) -> str:
        """Calculate sentiment trend (improving, declining, stable)"""
        if len(sentiment_scores) < 3:
            return "insufficient_data"
        
        # Compare first and last thirds
        first_third = sentiment_scores[:len(sentiment_scores)//3]
        last_third = sentiment_scores[-len(sentiment_scores)//3:]
        
        avg_first = sum(first_third) / len(first_third)
        avg_last = sum(last_third) / len(last_third)
        
        difference = avg_last - avg_first
        
        if difference > 0.1:
            return "improving"
        elif difference < -0.1:
            return "declining"
        else:
            return "stable"
    
    def _generate_pattern_summary(
        self, 
        dominant_emotion: str, 
        avg_sentiment: float, 
        avg_intensity: float, 
        stability: float
    ) -> str:
        """Generate human-readable pattern summary"""
        
        sentiment_desc = "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral"
        intensity_desc = "high" if avg_intensity > 0.7 else "moderate" if avg_intensity > 0.4 else "low"
        stability_desc = "stable" if stability > 0.7 else "variable" if stability > 0.4 else "volatile"
        
        return f"Predominantly {dominant_emotion} with {sentiment_desc} sentiment, " \
               f"{intensity_desc} intensity, and {stability_desc} emotional patterns."
    
    async def health_check(self) -> bool:
        """Check if emotion service is healthy"""
        try:
            # Test basic functionality
            test_result = await self.analyze_emotion("I am happy today")
            return test_result.get("success", False) and test_result.get("primary_emotion") == "joy"
        except Exception as e:
            logger.error(f"Emotion service health check failed: {str(e)}")
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get emotion service information"""
        return {
            "service_name": "Emotion Analysis",
            "available_methods": ["vader", "textblob", "keywords", "patterns"],
            "supported_emotions": list(self.emotion_keywords.keys()),
            "keyword_count": sum(len(keywords) for keywords in self.emotion_keywords.values()),
            "pattern_count": sum(len(patterns) for patterns in self.emotion_patterns.values()),
            "enabled": settings.EMOTION_ANALYSIS_ENABLED,
            "confidence_threshold": settings.EMOTION_CONFIDENCE_THRESHOLD
        }

# Create global service instance
emotion_service = EmotionService()

# Export the service
__all__ = ["EmotionService", "emotion_service"]