# Create a test script: test_gcp.py
import os
from dotenv import load_dotenv

load_dotenv()

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './credentials.json'

from google.cloud import speech
from google.cloud import texttospeech
from google import genai
from google.genai import types

# Test Speech client
try:
    speech_client = speech.SpeechClient()
    print("✓ Speech-to-Text client initialized")
except Exception as e:
    print(f"✗ Speech-to-Text error: {e}")

# Test TTS client
try:
    tts_client = texttospeech.TextToSpeechClient()
    print("✓ Text-to-Speech client initialized")
except Exception as e:
    print(f"✗ Text-to-Speech error: {e}")


try:
    # Ensure GEMINI_API_KEY is set in your environment
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")

    # Initialize client with api_key
    client = genai.Client(api_key=gemini_api_key) # Pass the API key here
    # model = genai.GenerativeModel('gemini-2.0-flash-exp') # No, use client.get_model or specify in generate_content

    response = client.models.generate_content( # This method is for client-based model interaction
        model="gemini-2.0-flash-exp", # Use the correct model name
        contents="Explain how AI works in a few words"
    )
    print(response.text)
    print("✓ Gemini client initialized")
except Exception as e:
    print(f"✗ Gemini error: {e}")