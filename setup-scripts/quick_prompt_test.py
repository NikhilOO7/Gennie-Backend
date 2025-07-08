# quick_prompt_test.py - Quick test to see what system prompts are generated

import asyncio
from app.services.personalization import personalization_service

async def test_prompts():
    """Test what system prompts are generated for different preferences"""
    
    print("\n" + "="*60)
    print("SYSTEM PROMPT GENERATION TEST")
    print("="*60 + "\n")
    
    # Test cases with different preference combinations
    test_cases = [
        {
            "name": "DEFAULT (Friendly, Medium, Standard)",
            "preferences": {
                "conversation_style": "friendly",
                "preferred_response_length": "medium",
                "emotional_support_level": "standard"
            }
        },
        {
            "name": "FORMAL & BRIEF",
            "preferences": {
                "conversation_style": "formal",
                "preferred_response_length": "short",
                "emotional_support_level": "minimal",
                "technical_level": "expert"
            }
        },
        {
            "name": "CASUAL & SUPPORTIVE",
            "preferences": {
                "conversation_style": "casual",
                "preferred_response_length": "long",
                "emotional_support_level": "high",
                "humor_level": "high"
            }
        },
        {
            "name": "PROFESSIONAL & TECHNICAL",
            "preferences": {
                "conversation_style": "professional",
                "preferred_response_length": "medium",
                "emotional_support_level": "standard",
                "technical_level": "expert",
                "formality_level": "formal"
            }
        }
    ]
    
    # Test each combination
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        print(f"Preferences: {test['preferences']}")
        
        # Generate prompt without emotion context
        prompt = await personalization_service.generate_personalized_system_prompt(
            test['preferences'],
            context={}
        )
        print(f"\nGenerated System Prompt:")
        print(f'"{prompt}"')
        
        # Also test with emotional context
        prompt_sad = await personalization_service.generate_personalized_system_prompt(
            test['preferences'],
            context={"emotion": "sadness"}
        )
        print(f"\nWith Sad Emotion Context:")
        print(f'"{prompt_sad}"')
    
    # Test edge cases
    print("\n\nEDGE CASES")
    print("="*60)
    
    # Empty preferences
    print("\nEmpty preferences:")
    prompt = await personalization_service.generate_personalized_system_prompt({}, {})
    print(f'"{prompt}"')
    
    # Only one preference
    print("\nOnly conversation style:")
    prompt = await personalization_service.generate_personalized_system_prompt(
        {"conversation_style": "professional"}, 
        {}
    )
    print(f'"{prompt}"')

if __name__ == "__main__":
    asyncio.run(test_prompts())