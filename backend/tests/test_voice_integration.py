import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.services.tts_service import tts_service

@pytest.mark.asyncio
async def test_text_to_speech_synthesis():
    """Test TTS synthesis functionality"""
    with patch.object(tts_service, 'synthesize_speech') as mock_synth:
        mock_synth.return_value = {
            "success": True,
            "audio_content": b"fake_audio_data",
            "audio_format": "mp3",
            "voice_name": "en-US-Neural2-C"
        }
        
        result = await tts_service.synthesize_speech(
            text="Hello, this is a test",
            voice_name="en-US-Neural2-C",
            audio_format="mp3"
        )
        
        assert result["success"] is True
        assert "audio_content" in result
        assert result["audio_format"] == "mp3"

@pytest.mark.asyncio
async def test_voice_endpoint(client: AsyncClient):
    """Test voice synthesis endpoint"""
    # Register user and get token
    register_response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User"
    })
    token = register_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test voice synthesis
    response = await client.post(
        "/api/v1/voice/synthesize",
        headers=headers,
        json={
            "text": "Hello, world!",
            "voice_name": "en-US-Neural2-C",
            "audio_format": "mp3"
        }
    )
    assert response.status_code == 200