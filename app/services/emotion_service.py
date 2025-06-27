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
import ssl

# Emotion analysis libraries
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
import nltk

from app.config import settings

logger = logging.getLogger(__name__)

# Fix SSL certificate issue for NLTK downloads
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

class EmotionService:
    """
    Comprehensive emotion analysis service with multiple detection methods
    """
    
    def __init__(self):
        """Initialize emotion analysis service"""
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Download required NLTK data with SSL fix
        self._ensure_nltk_data()
        
        # Emotion keywords mapping
        self.emotion_keywords = self._load_emotion_keywords()
        
        # Emotion patterns
        self.emotion_patterns = self._load_emotion_patterns()
        
        # Performance tracking
        self.analysis_count = 0
        self.total_processing_time = 0.0
        
        logger.info("Emotion analysis service initialized")
    
    def _ensure_nltk_data(self):
        """Ensure required NLTK data is downloaded with SSL handling"""
        required_data = ['punkt', 'brown', 'averaged_perceptron_tagger', 'wordnet']
        
        for data_name in required_data:
            try:
                if data_name == 'punkt':
                    nltk.data.find('tokenizers/punkt')
                elif data_name == 'wordnet':
                    nltk.data.find('corpora/wordnet')
                else:
                    nltk.data.find(f'corpora/{data_name}')
                logger.debug(f"NLTK {data_name} data already present")
            except LookupError:
                try:
                    logger.info(f"Downloading NLTK {data_name} data...")
                    nltk.download(data_name, quiet=True)
                    logger.info(f"Successfully downloaded NLTK {data_name} data")
                except Exception as e:
                    logger.warning(f"Failed to download NLTK {data_name} data: {e}")
                    logger.warning(f"Some emotion analysis features may be limited without {data_name}")
    
    def _load_emotion_keywords(self) -> Dict[str, List[str]]:
        """Load emotion keywords for pattern matching"""
        return {
            "joy": [
                "happy", "joy", "joyful", "excited", "thrilled", "delighted", 
                "pleased", "cheerful", "elated", "euphoric", "blissful", "content",
                "satisfied", "glad", "grateful", "amazed", "wonderful", "fantastic",
                "awesome", "brilliant", "excellent", "love", "adore", "celebrate",
                "ecstatic", "overjoyed", "jubilant", "merry", "upbeat", "optimistic"
            ],
            "sadness": [
                "sad", "sorrow", "grief", "melancholy", "depressed", "gloomy",
                "miserable", "unhappy", "dejected", "downcast", "heartbroken",
                "disappointed", "discouraged", "despondent", "blue", "tearful",
                "crying", "weeping", "mourning", "regret", "loss", "lonely",
                "hopeless", "despair", "forlorn", "disheartened", "crestfallen"
            ],
            "anger": [
                "angry", "mad", "furious", "rage", "irate", "livid", "enraged",
                "infuriated", "annoyed", "irritated", "frustrated", "outraged",
                "hostile", "resentful", "bitter", "hate", "disgusted", "revolted",
                "appalled", "incensed", "seething", "fuming", "pissed", "wrathful"
            ],
            "fear": [
                "afraid", "scared", "frightened", "terrified", "anxious", "worried",
                "nervous", "panicked", "alarmed", "concerned", "apprehensive",
                "uneasy", "tense", "stressed", "paranoid", "phobic", "dreading",
                "intimidated", "threatened", "insecure", "vulnerable", "petrified"
            ],
            "surprise": [
                "surprised", "shocked", "astonished", "amazed", "stunned", "bewildered",
                "confused", "perplexed", "baffled", "puzzled", "startled", "unexpected",
                "sudden", "wow", "unbelievable", "incredible", "remarkable", "astounded"
            ],
            "disgust": [
                "disgusted", "revolted", "repulsed", "nauseated", "sickened",
                "appalled", "horrified", "repugnant", "offensive", "gross",
                "yuck", "eww", "terrible", "awful", "horrible", "vile", "nasty"
            ],
            "contempt": [
                "contempt", "disdain", "scorn", "ridicule", "mock", "sneer",
                "despise", "loathe", "detest", "arrogant", "superior", "condescending",
                "dismissive", "sarcastic", "cynical", "haughty"
            ],
            "excitement": [
                "excited", "thrilled", "enthusiastic", "eager", "energetic",
                "pumped", "stoked", "hyped", "fired up", "passionate", "dynamic",
                "animated", "exhilarated", "invigorated", "zealous"
            ],
            "anxiety": [
                "anxious", "worried", "stressed", "overwhelmed", "panicked",
                "restless", "agitated", "troubled", "disturbed", "frantic",
                "jittery", "on edge", "apprehensive", "distressed"
            ],
            "frustration": [
                "frustrated", "annoyed", "irritated", "exasperated", "fed up",
                "aggravated", "vexed", "bothered", "irked", "miffed",
                "disgruntled", "impatient", "ticked off"
            ],
            "contentment": [
                "content", "peaceful", "calm", "serene", "relaxed", "comfortable",
                "satisfied", "pleased", "at ease", "tranquil", "balanced",
                "composed", "untroubled", "mellow", "placid"
            ]
        }
    
    def _load_emotion_patterns(self) -> Dict[str, List[str]]:
        """Load regex patterns for emotion detection"""
        return {
            "joy": [
                r"\b(?:so|very|really|extremely|super)\s+(?:happy|excited|thrilled|glad)\b",
                r"\b(?:love|adore|absolutely love|really like)\s+(?:this|it|that)\b",
                r"(?:!{2,}|\b(?:yay|woohoo|awesome|fantastic|amazing)\b)",
                r"\b(?:can't wait|looking forward|excited about)\b",
                r"😊|😃|😄|😁|🙂|😍|🥰|❤️|💕",  # Emoji patterns
                r"\b(?:best|greatest|wonderful|perfect)\s+(?:day|time|moment)\b"
            ],
            "sadness": [
                r"\b(?:so|very|really|extremely)\s+(?:sad|depressed|down|unhappy)\b",
                r"\b(?:feel|feeling)\s+(?:terrible|awful|horrible|miserable)\b",
                r"\b(?:wish|hope)\s+(?:things|life)\s+(?:were|was)\s+(?:different|better)\b",
                r"\b(?:miss|missing)\s+(?:you|him|her|them|it)\b",
                r"😢|😭|😔|😞|💔|😿",  # Sad emojis
                r"\b(?:cry|crying|tears|tearful)\b"
            ],
            "anger": [
                r"\b(?:so|very|really|extremely|fucking|damn)\s+(?:angry|mad|furious|pissed)\b",
                r"\b(?:hate|can't stand|despise|loathe)\b",
                r"\b(?:this|that)\s+(?:is|makes me)\s+(?:ridiculous|stupid|idiotic)\b",
                r"(?:!{3,}|[A-Z\s]{10,})",  # Multiple exclamation marks or all caps
                r"😠|😡|🤬|😤|💢",  # Angry emojis
                r"\b(?:fuck|shit|damn|hell)\b"  # Profanity (mild)
            ],
            "fear": [
                r"\b(?:so|very|really|extremely)\s+(?:scared|afraid|worried|anxious)\b",
                r"\b(?:what if|i'm afraid|terrified that)\b",
                r"\b(?:nervous|anxious)\s+about\b",
                r"\b(?:terrified|petrified|frightened)\s+(?:of|that)\b",
                r"😨|😱|😰|🙀",  # Fear emojis
                r"\b(?:panic|panicking|freaking out)\b"
            ],
            "surprise": [
                r"\b(?:oh my|wow|whoa|omg|oh)\b",
                r"\b(?:can't believe|unbelievable|incredible)\b",
                r"\b(?:shocked|surprised|astonished)\b",
                r"😮|😲|🤯|😱",  # Surprise emojis
                r"(?:\?{2,}|!{2,}\?)"  # Multiple question marks
            ],
            "excitement": [
                r"\b(?:can't wait|so excited|super pumped)\b",
                r"\b(?:amazing|incredible|awesome)\s+(?:news|opportunity)\b",
                r"(?:!{3,})",  # Multiple exclamation marks
                r"🎉|🎊|🥳|🤩",  # Celebration emojis
                r"\b(?:thrilled|pumped|stoked|hyped)\b"
            ]
        }
    
    async def analyze_emotion(
        self, 
        text: str, 
        context: Optional[Dict[str, Any]] = None,
        methods: Optional[List[str]] = None,
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive emotion analysis using multiple methods
        
        Args:
            text: The text to analyze
            context: Optional context about the conversation
            methods: Specific methods to use (default: all available)
            detailed: Whether to include detailed analysis results
            
        Returns:
            Dictionary with emotion analysis results
        """
        if not text or not text.strip():
            return self._create_neutral_result()
        
        start_time = datetime.now(timezone.utc)
        self.analysis_count += 1
        
        try:
            # Clean and prepare text
            text = text.strip()
            
            # Default to all methods if not specified
            if methods is None:
                methods = ["vader", "textblob", "keywords", "patterns"]
            
            # Run analyses in parallel
            tasks = []
            if "vader" in methods:
                tasks.append(self._analyze_with_vader(text))
            if "textblob" in methods:
                tasks.append(self._analyze_with_textblob(text))
            if "keywords" in methods:
                tasks.append(self._analyze_with_keywords(text))
            if "patterns" in methods:
                tasks.append(self._analyze_with_patterns(text))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            analysis_results = {}
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Analysis method failed: {str(result)}")
                    continue
                if isinstance(result, dict) and "method" in result:
                    analysis_results[result["method"]] = result
            
            # Combine results
            combined_result = await self._combine_analysis_results(
                analysis_results, text, context
            )
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.total_processing_time += processing_time
            
            # Add metadata
            combined_result["processing_time"] = processing_time
            combined_result["analysis_timestamp"] = datetime.now(timezone.utc).isoformat()
            combined_result["analysis_id"] = f"emotion_{self.analysis_count}"
            
            # Add detailed results if requested
            if detailed:
                combined_result["detailed_results"] = analysis_results
            
            # Log analysis completion
            logger.debug(
                f"Emotion analysis completed in {processing_time:.3f}s",
                extra={
                    "text_length": len(text),
                    "primary_emotion": combined_result.get("primary_emotion"),
                    "confidence": combined_result.get("confidence_score"),
                    "methods_used": len(analysis_results)
                }
            )
            
            return combined_result
        
        except Exception as e:
            logger.error(f"Emotion analysis failed: {str(e)}", exc_info=True)
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "success": False,
                "error": str(e),
                "primary_emotion": "neutral",
                "confidence_score": 0.0,
                "processing_time": processing_time,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _analyze_with_vader(self, text: str) -> Dict[str, Any]:
        """Analyze emotion using VADER sentiment analysis"""
        try:
            scores = self.vader_analyzer.polarity_scores(text)
            
            # Enhanced emotion mapping based on compound score and individual scores
            compound = scores['compound']
            pos = scores['pos']
            neg = scores['neg']
            neu = scores['neu']
            
            # Determine primary emotion with more nuanced mapping
            if compound >= 0.5:
                if pos > 0.6:
                    primary_emotion = "excitement" if "!" in text else "joy"
                else:
                    primary_emotion = "joy"
            elif compound >= 0.1:
                primary_emotion = "contentment"
            elif compound <= -0.5:
                if neg > 0.6:
                    primary_emotion = "anger" if any(word in text.lower() for word in ["hate", "angry", "furious"]) else "sadness"
                else:
                    primary_emotion = "sadness"
            elif compound <= -0.1:
                primary_emotion = "frustration"
            else:
                primary_emotion = "neutral"
            
            # Calculate confidence based on the strength of the compound score
            confidence = min(abs(compound) * 1.2, 1.0)  # Scale up slightly as VADER tends to be conservative
            
            return {
                "method": "vader",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": compound,
                "emotion_scores": {
                    "positive": pos,
                    "negative": neg,
                    "neutral": neu,
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
            sentiment = blob.sentiment
            
            # Enhanced emotion mapping
            polarity = sentiment.polarity
            subjectivity = sentiment.subjectivity
            
            # Map polarity to emotions with subjectivity consideration
            if polarity > 0.5:
                primary_emotion = "excitement" if subjectivity > 0.6 else "joy"
            elif polarity > 0.1:
                primary_emotion = "contentment"
            elif polarity < -0.5:
                primary_emotion = "anger" if subjectivity > 0.6 else "sadness"
            elif polarity < -0.1:
                primary_emotion = "frustration"
            else:
                primary_emotion = "neutral"
            
            # Confidence considers both polarity strength and subjectivity
            confidence = abs(polarity) * (0.5 + subjectivity * 0.5)
            
            return {
                "method": "textblob",
                "primary_emotion": primary_emotion,
                "confidence_score": min(confidence, 1.0),
                "sentiment_score": polarity,
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
            matched_keywords = {}
            total_matches = 0
            
            for emotion, keywords in self.emotion_keywords.items():
                score = 0
                matches = []
                
                for keyword in keywords:
                    # Check for whole word matches
                    if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                        score += 1
                        matches.append(keyword)
                        total_matches += 1
                
                if score > 0:
                    # Normalize by the number of keywords to avoid bias
                    emotion_scores[emotion] = score / len(keywords)
                    matched_keywords[emotion] = matches
            
            if not emotion_scores:
                primary_emotion = "neutral"
                confidence = 0.5
            else:
                # Get primary emotion
                primary_emotion = max(emotion_scores, key=emotion_scores.get)
                
                # Calculate confidence based on score and uniqueness
                primary_score = emotion_scores[primary_emotion]
                other_scores = [score for em, score in emotion_scores.items() if em != primary_emotion]
                
                if other_scores:
                    # Higher confidence if primary emotion is clearly dominant
                    score_diff = primary_score - max(other_scores)
                    confidence = min(primary_score + score_diff * 0.5, 1.0)
                else:
                    confidence = min(primary_score * 2, 1.0)
            
            return {
                "method": "keywords",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": self._emotion_to_sentiment(primary_emotion),
                "emotion_scores": emotion_scores,
                "matched_keywords": matched_keywords,
                "total_matches": total_matches
            }
        
        except Exception as e:
            logger.error(f"Keyword analysis failed: {str(e)}")
            return {"method": "keywords", "error": str(e)}
    
    async def _analyze_with_patterns(self, text: str) -> Dict[str, Any]:
        """Analyze emotion using regex patterns"""
        try:
            emotion_scores = {}
            matched_patterns = {}
            total_pattern_matches = 0
            
            for emotion, patterns in self.emotion_patterns.items():
                score = 0
                matches = []
                
                for pattern in patterns:
                    regex_matches = re.findall(pattern, text, re.IGNORECASE)
                    if regex_matches:
                        score += len(regex_matches)
                        matches.extend(regex_matches)
                        total_pattern_matches += len(regex_matches)
                
                if score > 0:
                    # Normalize score
                    emotion_scores[emotion] = min(score / 5.0, 1.0)  # Adjust normalization factor
                    matched_patterns[emotion] = matches
            
            if not emotion_scores:
                primary_emotion = "neutral"
                confidence = 0.5
            else:
                primary_emotion = max(emotion_scores, key=emotion_scores.get)
                confidence = emotion_scores[primary_emotion]
                
                # Boost confidence if multiple patterns match
                if len(matched_patterns.get(primary_emotion, [])) > 2:
                    confidence = min(confidence * 1.2, 1.0)
            
            return {
                "method": "patterns",
                "primary_emotion": primary_emotion,
                "confidence_score": confidence,
                "sentiment_score": self._emotion_to_sentiment(primary_emotion),
                "emotion_scores": emotion_scores,
                "matched_patterns": matched_patterns,
                "total_pattern_matches": total_pattern_matches
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
        if not results:
            return self._create_neutral_result()
        
        # Filter out error results
        valid_results = {k: v for k, v in results.items() if "error" not in v}
        
        if not valid_results:
            return {
                "success": False,
                "error": "All analysis methods failed",
                "primary_emotion": "neutral",
                "confidence_score": 0.0,
                "analysis_methods": list(results.keys())
            }
        
        # Weighted voting system for emotions
        emotion_votes = {}
        confidence_scores = []
        sentiment_scores = []
        
        # Define method weights based on reliability
        method_weights = {
            "vader": 1.2,      # Higher weight for VADER's proven accuracy
            "textblob": 1.0,
            "keywords": 0.9,   # Slightly lower for simple keyword matching
            "patterns": 1.1    # Good for specific patterns
        }
        
        for method, result in valid_results.items():
            primary = result.get("primary_emotion", "neutral")
            confidence = result.get("confidence_score", 0.5)
            weight = method_weights.get(method, 1.0)
            
            # Weighted vote
            emotion_votes[primary] = emotion_votes.get(primary, 0) + (confidence * weight)
            
            confidence_scores.append(confidence)
            
            if "sentiment_score" in result:
                sentiment_scores.append(result["sentiment_score"])
        
        # Determine primary emotion (highest weighted vote)
        primary_emotion = max(emotion_votes, key=emotion_votes.get)
        
        # Calculate combined confidence
        if confidence_scores:
            # Weighted average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            # Boost confidence if methods agree
            agreement_bonus = min(len([v for v in valid_results.values() if v.get("primary_emotion") == primary_emotion]) / len(valid_results) * 0.2, 0.2)
            confidence = min(avg_confidence + agreement_bonus, 1.0)
        else:
            confidence = 0.5
        
        # Calculate average sentiment
        combined_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
        
        # Aggregate all emotion scores
        combined_emotion_scores = {}
        for result in valid_results.values():
            if "emotion_scores" in result:
                for emotion, score in result["emotion_scores"].items():
                    if isinstance(score, (int, float)):
                        if emotion in combined_emotion_scores:
                            combined_emotion_scores[emotion] = (combined_emotion_scores[emotion] + score) / 2
                        else:
                            combined_emotion_scores[emotion] = score
        
        # Apply context adjustments if available
        if context:
            primary_emotion, confidence = self._apply_context_adjustments(
                primary_emotion, confidence, context
            )
        
        # Get secondary emotion
        secondary_emotion = self._get_secondary_emotion(emotion_votes, primary_emotion)
        
        return {
            "success": True,
            "primary_emotion": primary_emotion,
            "secondary_emotion": secondary_emotion,
            "confidence_score": round(confidence, 3),
            "sentiment_score": round(combined_sentiment, 3),
            "emotion_scores": {k: round(v, 3) for k, v in combined_emotion_scores.items()},
            "emotion_intensity": self._calculate_intensity(confidence, combined_sentiment),
            "analysis_methods": list(valid_results.keys()),
            "method_agreement": len([v for v in valid_results.values() if v.get("primary_emotion") == primary_emotion]) / len(valid_results),
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
            # Only return if it has reasonable support
            if remaining_emotions[secondary] > max(emotion_scores.values()) * 0.5:
                return secondary
        
        return None
    
    def _calculate_intensity(self, confidence: float, sentiment: float) -> float:
        """Calculate emotion intensity"""
        # Combine confidence and absolute sentiment
        intensity = (confidence * 0.6 + abs(sentiment) * 0.4)
        return round(min(max(intensity, 0.0), 1.0), 3)
    
    def _emotion_to_sentiment(self, emotion: str) -> float:
        """Convert emotion to sentiment score"""
        emotion_sentiment_map = {
            # Positive emotions
            "joy": 0.8,
            "excitement": 0.9,
            "contentment": 0.5,
            "surprise": 0.3,  # Can be positive or neutral
            
            # Negative emotions
            "sadness": -0.7,
            "anger": -0.8,
            "fear": -0.6,
            "disgust": -0.7,
            "contempt": -0.6,
            "anxiety": -0.5,
            "frustration": -0.4,
            
            # Neutral
            "neutral": 0.0
        }
        
        return emotion_sentiment_map.get(emotion, 0.0)
    
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
                # Count recent occurrences of emotions
                recent_emotion_counts = {}
                for recent_emotion in recent_emotions[-5:]:  # Last 5 emotions
                    if isinstance(recent_emotion, dict):
                        emotion_name = recent_emotion.get("primary_emotion", "neutral")
                    else:
                        emotion_name = recent_emotion
                    recent_emotion_counts[emotion_name] = recent_emotion_counts.get(emotion_name, 0) + 1
                
                # If current emotion matches recent pattern, boost confidence
                if emotion in recent_emotion_counts:
                    pattern_strength = recent_emotion_counts[emotion] / len(recent_emotions[-5:])
                    confidence = min(confidence + pattern_strength * 0.15, 1.0)
        
        # Time-based adjustments
        if "time_context" in context:
            current_hour = context.get("time_context", datetime.now().hour)
            
            # Late night/early morning adjustments
            if isinstance(current_hour, int):
                if 22 <= current_hour or current_hour <= 4:
                    if emotion in {"anxiety", "sadness", "fear"}:
                        confidence = min(confidence * 1.15, 1.0)
                    elif emotion in {"excitement", "joy"}:
                        confidence = confidence * 0.9  # Less likely to be genuinely happy late at night
                
                # Morning adjustments
                elif 6 <= current_hour <= 9:
                    if emotion in {"frustration", "anxiety"}:
                        confidence = min(confidence * 1.1, 1.0)  # Morning stress
        
        # Conversation topic adjustments
        if "conversation_topic" in context:
            topic = str(context["conversation_topic"]).lower()
            
            topic_emotion_boosts = {
                "work": {"frustration": 0.1, "anxiety": 0.1, "anger": 0.05},
                "job": {"anxiety": 0.15, "frustration": 0.1},
                "family": {"joy": 0.1, "sadness": 0.1, "contentment": 0.05},
                "relationship": {"joy": 0.1, "sadness": 0.15, "anxiety": 0.1},
                "health": {"anxiety": 0.2, "fear": 0.15},
                "money": {"anxiety": 0.15, "frustration": 0.1},
                "finance": {"anxiety": 0.15, "frustration": 0.1},
                "success": {"joy": 0.2, "excitement": 0.15},
                "achievement": {"joy": 0.15, "excitement": 0.2}
            }
            
            for topic_keyword, emotion_boosts in topic_emotion_boosts.items():
                if topic_keyword in topic and emotion in emotion_boosts:
                    confidence = min(confidence + emotion_boosts[emotion], 1.0)
        
        # User personality adjustments
        if "user_personality" in context:
            personality = context["user_personality"]
            if isinstance(personality, dict):
                # Adjust based on known personality traits
                if personality.get("generally_positive", False) and emotion in {"joy", "contentment", "excitement"}:
                    confidence = min(confidence * 1.1, 1.0)
                elif personality.get("generally_anxious", False) and emotion in {"anxiety", "fear"}:
                    confidence = min(confidence * 1.15, 1.0)
        
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
            "text_length": 0,
            "context_applied": False
        }
    
    async def analyze_conversation_emotions(
        self, 
        messages: List[Dict[str, Any]],
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """Analyze emotions across a conversation"""
        if not messages:
            return {
                "success": False,
                "error": "No messages to analyze",
                "conversation_emotions": []
            }
        
        try:
            # Analyze each message
            emotion_results = []
            for i, message in enumerate(messages):
                text = message.get("content", "")
                
                # Create context from previous messages
                context = {
                    "recent_emotions": emotion_results[-3:] if i > 0 else [],
                    "message_index": i,
                    "conversation_length": len(messages)
                }
                
                result = await self.analyze_emotion(text, context=context)
                result["message_index"] = i
                emotion_results.append(result)
            
            # Calculate conversation-level metrics
            primary_emotions = [r["primary_emotion"] for r in emotion_results if r.get("success")]
            sentiment_scores = [r["sentiment_score"] for r in emotion_results if "sentiment_score" in r]
            
            # Emotion distribution
            emotion_distribution = {}
            for emotion in primary_emotions:
                emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + 1
            
            # Normalize distribution
            total_emotions = len(primary_emotions)
            if total_emotions > 0:
                emotion_distribution = {k: v/total_emotions for k, v in emotion_distribution.items()}
            
            result = {
                "success": True,
                "conversation_emotions": emotion_results,
                "emotion_distribution": emotion_distribution,
                "dominant_emotion": max(emotion_distribution, key=emotion_distribution.get) if emotion_distribution else "neutral",
                "average_sentiment": sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0,
                "sentiment_range": {
                    "min": min(sentiment_scores) if sentiment_scores else 0.0,
                    "max": max(sentiment_scores) if sentiment_scores else 0.0
                },
                "total_messages": len(messages),
                "emotional_volatility": self._calculate_volatility(sentiment_scores)
            }
            
            # Add emotion trends if requested
            if include_trends and len(emotion_results) > 2:
                result["emotion_trends"] = self._analyze_emotion_trends(emotion_results)
            
            return result
            
        except Exception as e:
            logger.error(f"Conversation emotion analysis failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "conversation_emotions": []
            }
    
    def _calculate_volatility(self, scores: List[float]) -> float:
        """Calculate emotional volatility (variance in sentiment)"""
        if len(scores) < 2:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / len(scores)
        return round(variance ** 0.5, 3)  # Standard deviation
    
    def _analyze_emotion_trends(self, emotion_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in emotions over the conversation"""
        sentiments = [r["sentiment_score"] for r in emotion_results if "sentiment_score" in r]
        
        if len(sentiments) < 3:
            return {"trend": "stable", "direction": 0}
        
        # Simple linear regression for trend
        n = len(sentiments)
        x_values = list(range(n))
        
        x_mean = sum(x_values) / n
        y_mean = sum(sentiments) / n
        
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, sentiments))
        denominator = sum((x - x_mean) ** 2 for x in x_values)
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Interpret trend
        if abs(slope) < 0.05:
            trend = "stable"
        elif slope > 0.05:
            trend = "improving"
        else:
            trend = "declining"
        
        return {
            "trend": trend,
            "direction": round(slope, 3),
            "start_sentiment": round(sentiments[0], 3),
            "end_sentiment": round(sentiments[-1], 3),
            "sentiment_change": round(sentiments[-1] - sentiments[0], 3)
        }
    
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
        avg_processing_time = self.total_processing_time / self.analysis_count if self.analysis_count > 0 else 0
        
        return {
            "service_name": "Emotion Analysis",
            "version": "2.0",
            "available_methods": ["vader", "textblob", "keywords", "patterns"],
            "supported_emotions": list(self.emotion_keywords.keys()),
            "keyword_count": sum(len(keywords) for keywords in self.emotion_keywords.values()),
            "pattern_count": sum(len(patterns) for patterns in self.emotion_patterns.values()),
            "enabled": settings.EMOTION_ANALYSIS_ENABLED,
            "confidence_threshold": settings.EMOTION_CONFIDENCE_THRESHOLD,
            "statistics": {
                "total_analyses": self.analysis_count,
                "average_processing_time": round(avg_processing_time, 3),
                "total_processing_time": round(self.total_processing_time, 3)
            }
        }

# Create global service instance
emotion_service = EmotionService()

# Export the service
__all__ = ["EmotionService", "emotion_service"]