#!/usr/bin/env python3
"""
Test configuration loading
"""

try:
    print("🧪 Testing configuration loading...")
    
    # Test settings import
    from app.core.config import settings
    print("✅ Settings imported successfully")
    
    # Test key settings
    print(f"✅ Database URL: {settings.database_url}")
    print(f"✅ Redis URL: {settings.redis_url}")
    print(f"✅ OpenAI Model: {settings.openai_model}")
    print(f"✅ Environment: {settings.environment}")
    print(f"✅ Debug: {settings.debug}")
    print(f"✅ CORS Origins: {settings.cors_origins}")
    
    # Test OpenAI API key
    if settings.openai_api_key == "your_openai_api_key_here":
        print("⚠️  OpenAI API key not set in .env file")
    else:
        print("✅ OpenAI API key is configured")
    
    print("🎉 Configuration test passed!")
    
except Exception as e:
    print(f"❌ Configuration test failed: {e}")
    import traceback
    traceback.print_exc()