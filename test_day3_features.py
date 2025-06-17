#!/usr/bin/env python3
"""
Test Day 3 Features - OpenAI Integration and Conversation API
Run this script to test the implemented features
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1/ai"

def test_health_check():
    """Test basic health check"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_ai_health():
    """Test AI service health"""
    print("🔍 Testing AI service health...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI service health: {data}")
            return True
        else:
            print(f"❌ AI health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ AI health check error: {e}")
        return False

def test_ai_connection():
    """Test OpenAI API connection"""
    print("🔍 Testing OpenAI connection...")
    try:
        response = requests.post(f"{API_URL}/test-connection")
        if response.status_code == 200:
            data = response.json()
            if data.get("connected"):
                print("✅ OpenAI connection successful")
                return True
            else:
                print(f"❌ OpenAI connection failed: {data.get('error')}")
                return False
        else:
            print(f"❌ Connection test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection test error: {e}")
        return False

def test_prompt_templates():
    """Test prompt templates"""
    print("🔍 Testing prompt templates...")
    try:
        response = requests.get(f"{API_URL}/prompts/templates")
        if response.status_code == 200:
            data = response.json()
            templates = data.get("templates", {})
            print(f"✅ Found {len(templates)} prompt templates:")
            for name in templates.keys():
                print(f"   - {name}")
            return True
        else:
            print(f"❌ Prompt templates test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Prompt templates error: {e}")
        return False

def test_conversation():
    """Test basic conversation"""
    print("🔍 Testing conversation API...")
    
    # Check if OpenAI API key is configured
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not configured - skipping conversation test")
        print("   Please set OPENAI_API_KEY in your .env file")
        return False
    
    try:
        conversation_data = {
            "message": "Hello! Can you tell me a short joke?",
            "use_context": False,
            "detect_emotion": False
        }
        
        response = requests.post(
            f"{API_URL}/chat",
            json=conversation_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Conversation test successful!")
            print(f"   Chat ID: {data.get('chat_id')}")
            print(f"   Response: {data.get('response')[:100]}...")
            print(f"   Tokens used: {data.get('tokens_used')}")
            print(f"   Processing time: {data.get('processing_time'):.2f}s")
            return True
        else:
            print(f"❌ Conversation test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Conversation test error: {e}")
        return False

def test_title_generation():
    """Test chat title generation"""
    print("🔍 Testing title generation...")
    
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not configured - skipping title generation test")
        return False
    
    try:
        title_data = ["Hello, I need help with Python programming", "Can you explain loops?"]
        
        response = requests.post(
            f"{API_URL}/generate-title",
            json=title_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Title generation successful: '{data.get('title')}'")
            return True
        else:
            print(f"❌ Title generation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Title generation error: {e}")
        return False

def test_emotion_analysis():
    """Test emotion analysis"""
    print("🔍 Testing emotion analysis...")
    
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not configured - skipping emotion analysis test")
        return False
    
    try:
        # Test with emotion data as query parameter
        test_text = "I'm feeling really excited about this new project!"
        
        response = requests.post(
            f"{API_URL}/analyze-emotion",
            params={"text": test_text}
        )
        
        if response.status_code == 200:
            data = response.json()
            analysis = data.get("analysis", {})
            print(f"✅ Emotion analysis successful!")
            print(f"   Text: {test_text}")
            print(f"   Emotion: {analysis.get('emotion')}")
            print(f"   Sentiment: {analysis.get('sentiment')}")
            print(f"   Confidence: {analysis.get('confidence')}")
            return True
        else:
            print(f"❌ Emotion analysis failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Emotion analysis error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Day 3 Features - OpenAI Integration")
    print("=" * 50)
    
    # Check if server is running
    try:
        requests.get(BASE_URL, timeout=5)
    except requests.ConnectionError:
        print("❌ Server is not running!")
        print("Please start the server with: uvicorn app.main:app --reload")
        return
    
    tests = [
        test_health_check,
        test_ai_health,
        test_ai_connection,
        test_prompt_templates,
        test_conversation,
        test_title_generation,
        test_emotion_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Day 3 implementation is working correctly.")
    elif passed > total // 2:
        print("⚠️  Most tests passed. Check the failed tests above.")
    else:
        print("❌ Many tests failed. Please check your implementation.")
    
    print("\n💡 Next Steps:")
    print("1. Make sure your .env file has a valid OPENAI_API_KEY")
    print("2. Test the API endpoints manually at http://localhost:8000/docs")
    print("3. Ready to move to Day 4 - Multi-turn conversation memory!")

if __name__ == "__main__":
    main()