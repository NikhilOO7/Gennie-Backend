"""
Prompt Service - Dynamic prompt management and engineering
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class PromptTemplate:
    """Class for managing prompt templates"""
    
    def __init__(self, name: str, template: str, variables: List[str] = None):
        self.name = name
        self.template = template
        self.variables = variables or []
    
    def render(self, **kwargs) -> str:
        """Render template with provided variables"""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing variable {e} in template {self.name}")
            return self.template

class PromptService:
    """Service for managing AI prompts and prompt engineering"""
    
    def __init__(self):
        self.templates = {}
        self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates"""
        
        # Base conversation prompt
        self.templates["conversation"] = PromptTemplate(
            name="conversation",
            template="""You are a helpful, empathetic AI assistant. Your goal is to provide thoughtful, engaging, and personalized responses.

Conversation Guidelines:
- Be friendly and conversational
- Show empathy and understanding
- Provide helpful and accurate information
- Ask follow-up questions when appropriate
- Adapt your tone to match the user's mood and style

{context_info}

{personality_info}

{conversation_style}

Current conversation:""",
            variables=["context_info", "personality_info", "conversation_style"]
        )
        
        # Emotional support prompt
        self.templates["emotional_support"] = PromptTemplate(
            name="emotional_support",
            template="""You are a compassionate AI assistant focused on providing emotional support. 

Guidelines for emotional support:
- Listen actively and validate feelings
- Offer comfort and encouragement
- Suggest coping strategies when appropriate
- Be gentle and non-judgmental
- Recognize when professional help might be needed

User's current emotional state: {emotion}
Context: {context}

Respond with empathy and care:""",
            variables=["emotion", "context"]
        )
        
        # Professional prompt
        self.templates["professional"] = PromptTemplate(
            name="professional",
            template="""You are a professional AI assistant providing expert guidance and information.

Professional Guidelines:
- Maintain a formal, respectful tone
- Provide accurate, well-researched information
- Structure responses clearly and logically
- Include relevant examples when helpful
- Acknowledge limitations of your knowledge

Topic: {topic}
User's level: {user_level}
Specific request: {request}

Professional response:""",
            variables=["topic", "user_level", "request"]
        )
        
        # Creative prompt
        self.templates["creative"] = PromptTemplate(
            name="creative",
            template="""You are a creative AI assistant helping with imaginative and artistic tasks.

Creative Guidelines:
- Think outside the box
- Encourage creativity and exploration
- Provide vivid, engaging descriptions
- Offer multiple creative options
- Build upon the user's ideas

Creative task: {task}
Style preference: {style}
Constraints: {constraints}

Let your creativity flow:""",
            variables=["task", "style", "constraints"]
        )
        
        # Problem-solving prompt
        self.templates["problem_solving"] = PromptTemplate(
            name="problem_solving",
            template="""You are a logical AI assistant specializing in problem-solving and analysis.

Problem-Solving Approach:
- Break down complex problems into steps
- Consider multiple perspectives and solutions
- Provide pros and cons for different approaches
- Ask clarifying questions when needed
- Suggest practical next steps

Problem: {problem}
Context: {context}
Constraints: {constraints}

Analytical response:""",
            variables=["problem", "context", "constraints"]
        )
    
    def add_template(self, name: str, template: str, variables: List[str] = None):
        """Add a new prompt template"""
        self.templates[name] = PromptTemplate(name, template, variables)
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a prompt template by name"""
        return self.templates.get(name)
    
    def build_system_prompt(
        self,
        base_template: str = "conversation",
        user_preferences: Dict[str, Any] = None,
        conversation_context: List[str] = None,
        detected_emotion: str = None
    ) -> str:
        """Build a system prompt based on context and preferences"""
        
        template = self.get_template(base_template)
        if not template:
            template = self.get_template("conversation")
        
        # Build context information
        context_info = ""
        if conversation_context:
            context_info = f"Recent conversation topics: {', '.join(conversation_context[-3:])}"
        
        # Build personality information
        personality_info = ""
        if user_preferences:
            traits = []
            if user_preferences.get("conversation_style"):
                traits.append(f"preferred style: {user_preferences['conversation_style']}")
            if user_preferences.get("interests"):
                traits.append(f"interests: {', '.join(user_preferences['interests'][:3])}")
            if user_preferences.get("preferred_response_length"):
                traits.append(f"response length: {user_preferences['preferred_response_length']}")
            
            if traits:
                personality_info = f"User preferences - {', '.join(traits)}"
        
        # Build conversation style
        conversation_style = ""
        if detected_emotion and detected_emotion != "neutral":
            if detected_emotion in ["sadness", "fear", "anger"]:
                conversation_style = "The user seems to be experiencing some difficult emotions. Respond with extra empathy and care."
            elif detected_emotion in ["joy", "excitement"]:
                conversation_style = "The user seems to be in a positive mood. Match their energy appropriately."
        
        # Render template
        return template.render(
            context_info=context_info,
            personality_info=personality_info,
            conversation_style=conversation_style
        )
    
    def build_specialized_prompt(
        self,
        prompt_type: str,
        user_message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Build specialized prompts for specific use cases"""
        
        if prompt_type == "title_generation":
            return f"""Generate a concise, descriptive title (3-6 words) for this conversation:

Message: "{user_message}"

Title:"""
        
        elif prompt_type == "emotion_analysis":
            return f"""Analyze the emotion and sentiment in this message. Respond with JSON only:

Message: "{user_message}"

Format:
{{
    "emotion": "joy/sadness/anger/fear/surprise/disgust/neutral",
    "sentiment": "positive/negative/neutral",
    "intensity": 0.8,
    "confidence": 0.9
}}"""
        
        elif prompt_type == "context_summary":
            messages = context.get("messages", [])
            return f"""Summarize the key points and context from this conversation:

Messages: {json.dumps(messages[-10:])}

Provide a brief summary focusing on:
1. Main topics discussed
2. User's current needs/questions
3. Important context to remember

Summary:"""
        
        elif prompt_type == "personalization":
            return f"""Based on this user interaction, identify preferences and interests:

User message: "{user_message}"
Previous interactions: {context.get('history', 'None')}

Identify:
1. Communication style preferences
2. Topics of interest
3. Preferred response length/style
4. Any patterns in behavior

Analysis:"""
        
        else:
            return user_message
    
    def adapt_prompt_for_user(
        self,
        base_prompt: str,
        user_preferences: Dict[str, Any]
    ) -> str:
        """Adapt prompt based on user preferences"""
        
        adaptations = []
        
        # Response length preference
        length_pref = user_preferences.get("preferred_response_length", "medium")
        if length_pref == "short":
            adaptations.append("Keep responses concise and to the point.")
        elif length_pref == "long":
            adaptations.append("Provide detailed, comprehensive responses with examples.")
        
        # Conversation style
        style = user_preferences.get("conversation_style", "friendly")
        if style == "formal":
            adaptations.append("Maintain a professional, formal tone.")
        elif style == "casual":
            adaptations.append("Use a relaxed, conversational tone.")
        elif style == "professional":
            adaptations.append("Provide expert-level, professional guidance.")
        
        # Add language preference
        language = user_preferences.get("language", "en")
        if language != "en":
            adaptations.append(f"Respond in {language} language.")
        
        # Combine adaptations
        if adaptations:
            adaptation_text = "\n\nAdditional instructions:\n- " + "\n- ".join(adaptations)
            return base_prompt + adaptation_text
        
        return base_prompt
    
    def get_prompt_for_context(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        user_preferences: Dict[str, Any] = None,
        detected_emotion: str = None
    ) -> str:
        """Get the most appropriate prompt for the given context"""
        
        # Determine prompt type based on message content and emotion
        prompt_type = "conversation"  # default
        
        # Check for emotional content
        emotional_keywords = ["sad", "angry", "frustrated", "worried", "anxious", "depressed", "upset"]
        if any(keyword in user_message.lower() for keyword in emotional_keywords):
            prompt_type = "emotional_support"
        
        # Check for professional/technical content
        professional_keywords = ["work", "business", "project", "analysis", "strategy", "technical"]
        if any(keyword in user_message.lower() for keyword in professional_keywords):
            prompt_type = "professional"
        
        # Check for creative content
        creative_keywords = ["creative", "story", "write", "imagine", "design", "art", "idea"]
        if any(keyword in user_message.lower() for keyword in creative_keywords):
            prompt_type = "creative"
        
        # Check for problem-solving content
        problem_keywords = ["problem", "issue", "solve", "help", "how to", "what should"]
        if any(keyword in user_message.lower() for keyword in problem_keywords):
            prompt_type = "problem_solving"
        
        # Build context from conversation history
        conversation_context = []
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages
                if msg.get("role") == "user":
                    conversation_context.append(msg["content"][:100])  # First 100 chars
        
        # Build the system prompt
        return self.build_system_prompt(
            base_template=prompt_type,
            user_preferences=user_preferences,
            conversation_context=conversation_context,
            detected_emotion=detected_emotion
        )

# Global service instance
prompt_service = PromptService()

# Export
__all__ = ["PromptService", "prompt_service", "PromptTemplate"]