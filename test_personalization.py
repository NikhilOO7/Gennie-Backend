# test_personalization_requests.py - Test personalization via API requests

import requests
import json
import time

# Configuration
API_BASE = "http://localhost:8000/api/v1"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwidXNlcm5hbWUiOiJOaWtoaWwwMDciLCJleHAiOjE3NTE5NjM1MzgsInR5cGUiOiJhY2Nlc3MifQ.FLCDUCllLEoF35kvZC86QXzoqnvtZxvrggibMfKY2dQ"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def test_personalization_differences():
    """Test if different preferences produce different responses"""
    
    print("\n" + "="*60)
    print("TESTING PERSONALIZATION DIFFERENCES")
    print("="*60 + "\n")
    
    # Test message
    test_message = "Can you help me understand machine learning?"
    
    # Test 1: Professional & Short & Minimal Support
    print("1. Setting PROFESSIONAL & SHORT & MINIMAL...")
    response = requests.put(
        f"{API_BASE}/ai/personalization",
        headers=headers,
        json={
            "conversation_style": "professional",
            "response_length": "short",
            "emotional_support_level": "minimal",
            "technical_level": "expert"
        }
    )
    
    if response.ok:
        print("   ✓ Preferences updated")
        time.sleep(1)  # Give it a moment
        
        # Test chat
        response = requests.post(
            f"{API_BASE}/ai/chat",
            headers=headers,
            json={
                "message": test_message,
                "enable_personalization": True,
                "detect_emotion": True
            }
        )
        
        if response.ok:
            data = response.json()
            print(f"   ✓ Response received ({len(data['response'].split())} words)")
            print(f"   ✓ Personalized: {data['metadata'].get('personalization_applied', False)}")
            print(f"\n   Response preview:")
            print(f"   '{data['response'][:200]}...'\n")
            professional_response = data['response']
        else:
            print(f"   ✗ Chat failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return
    
    # Wait before next test
    time.sleep(2)
    
    # Test 2: Casual & Long & High Support
    print("\n2. Setting CASUAL & LONG & HIGH...")
    response = requests.put(
        f"{API_BASE}/ai/personalization",
        headers=headers,
        json={
            "conversation_style": "casual",
            "response_length": "long",
            "emotional_support_level": "high",
            "technical_level": "beginner"
        }
    )
    
    if response.ok:
        print("   ✓ Preferences updated")
        time.sleep(1)
        
        # Test chat
        response = requests.post(
            f"{API_BASE}/ai/chat",
            headers=headers,
            json={
                "message": test_message,
                "enable_personalization": True,
                "detect_emotion": True
            }
        )
        
        if response.ok:
            data = response.json()
            print(f"   ✓ Response received ({len(data['response'].split())} words)")
            print(f"   ✓ Personalized: {data['metadata'].get('personalization_applied', False)}")
            print(f"\n   Response preview:")
            print(f"   '{data['response'][:200]}...'\n")
            casual_response = data['response']
        else:
            print(f"   ✗ Chat failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return
    
    # Compare responses
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    
    print(f"\nProfessional response: {len(professional_response.split())} words")
    print(f"Casual response: {len(casual_response.split())} words")
    print(f"\nLength difference: {abs(len(casual_response.split()) - len(professional_response.split()))} words")
    
    # Check for style differences
    casual_indicators = ["hey", "you know", "basically", "gonna", "kinda", "!", "😊"]
    professional_indicators = ["therefore", "furthermore", "consequently", "specifically"]
    
    casual_score = sum(1 for indicator in casual_indicators if indicator.lower() in casual_response.lower())
    professional_score = sum(1 for indicator in professional_indicators if indicator.lower() in professional_response.lower())
    
    print(f"\nCasual indicators in casual response: {casual_score}")
    print(f"Professional indicators in professional response: {professional_score}")
    
    if len(casual_response.split()) > len(professional_response.split()) * 1.5:
        print("\n✅ SUCCESS: Casual response is significantly longer!")
    else:
        print("\n⚠️  WARNING: Response lengths are too similar")
    
    # Test emotional support
    print("\n" + "="*60)
    print("TESTING EMOTIONAL SUPPORT")
    print("="*60)
    
    emotional_message = "I'm really stressed about learning programming"
    
    # Test with high emotional support
    response = requests.post(
        f"{API_BASE}/ai/chat",
        headers=headers,
        json={
            "message": emotional_message,
            "enable_personalization": True,
            "detect_emotion": True
        }
    )
    
    if response.ok:
        data = response.json()
        print(f"\nWith HIGH emotional support:")
        print(f"Response: '{data['response'][:300]}...'\n")
        
        # Check for supportive language
        support_words = ["understand", "feel", "stress", "help", "support", "worry", "together", "okay"]
        support_count = sum(1 for word in support_words if word in data['response'].lower())
        print(f"Supportive words found: {support_count}")

if __name__ == "__main__":
    test_personalization_differences()