# test_gemini_config.py - Run this to test your Gemini configuration
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_gemini():
    print("=== Testing Gemini Configuration ===\n")
    
    # Check environment variables
    print("1. Environment Variables:")
    api_key = os.getenv('GEMINI_API_KEY', '')
    print(f"   GEMINI_API_KEY present: {bool(api_key)}")
    print(f"   GEMINI_API_KEY starts with 'AIza': {api_key.startswith('AIza')}")
    print(f"   GEMINI_API_KEY length: {len(api_key)}")
    print(f"   GOOGLE_GENAI_USE_VERTEXAI: {os.getenv('GOOGLE_GENAI_USE_VERTEXAI')}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
    print(f"   GOOGLE_CLOUD_PROJECT_ID: {os.getenv('GOOGLE_CLOUD_PROJECT_ID')}")
    
    # Check if credentials file exists (if using Vertex AI)
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'false').lower() == 'true':
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', './credentials.json')
        print(f"\n2. Vertex AI Mode:")
        print(f"   Credentials file exists: {os.path.exists(creds_path)}")
        if os.path.exists(creds_path):
            print(f"   Credentials file size: {os.path.getsize(creds_path)} bytes")
    
    # Try to import and initialize
    print("\n3. Testing Gemini Service Import:")
    try:
        # Force disable Vertex AI for testing direct API
        os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'false'
        
        from google import genai
        print("   ✓ google.genai imported successfully")
        
        # Try to create client
        if api_key and api_key.startswith('AIza'):
            print(f"\n4. Creating Gemini client...")
            client = genai.Client(api_key=api_key)
            print("   ✓ Gemini client created successfully")
            
            # List available models
            print("\n5. Available models:")
            try:
                models = await client.aio.models.list()
                async for model in models:
                    print(f"   - {model.name}")
            except Exception as e:
                print(f"   Could not list models: {e}")
            
            # Try a simple request
            print("\n6. Testing generation:")
            try:
                response = await client.aio.models.generate_content(
                    model="gemini-2.0-flash-exp",
                    contents="Say 'Hello, I'm working!' in exactly 5 words"
                )
                print("   ✓ Test request successful!")
                print(f"   Response: {response.text}")
            except Exception as e:
                print(f"   ✗ Test request failed: {type(e).__name__}: {e}")
                
                # Try with a different model
                print("\n   Trying with gemini-1.5-flash...")
                try:
                    response = await client.aio.models.generate_content(
                        model="gemini-1.5-flash",
                        contents="Say 'Hello, I'm working!' in exactly 5 words"
                    )
                    print("   ✓ gemini-1.5-flash works!")
                    print(f"   Response: {response.text}")
                except Exception as e2:
                    print(f"   ✗ gemini-1.5-flash also failed: {e2}")
        else:
            print("   ✗ Invalid or missing API key!")
            print("   API key should start with 'AIza' for direct Gemini API")
            
    except Exception as e:
        print(f"   ✗ Import/initialization failed: {type(e).__name__}: {e}")
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
    
    print("\n7. Recommendations:")
    if not api_key:
        print("   ❌ No API key found! Set GEMINI_API_KEY in your .env file")
    elif not api_key.startswith('AIza'):
        print("   ❌ API key doesn't look like a valid Gemini API key")
        print("   Gemini API keys should start with 'AIza'")
    
    if os.getenv('GOOGLE_GENAI_USE_VERTEXAI', 'false').lower() == 'true':
        print("\n   You have Vertex AI mode enabled. For simpler setup:")
        print("   - Set GOOGLE_GENAI_USE_VERTEXAI=false in your .env")
        print("   - Use direct Gemini API with just the API key")

if __name__ == "__main__":
    asyncio.run(test_gemini())