import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

@pytest.mark.asyncio
async def test_get_voice_preferences(client: AsyncClient, test_user: User):
    response = await client.get("/api/v1/users/me/voice-preferences")
    assert response.status_code == 200
    assert response.json() == {}

@pytest.mark.asyncio
async def test_update_voice_preferences(client: AsyncClient, test_user: User):
    new_prefs = {
        "voice_name": "en-US-Neural2-F",
        "speaking_rate": 1.2,
        "pitch": 0.5,
        "voice_language": "en-US",
    }
    response = await client.put("/api/v1/users/me/voice-preferences", json=new_prefs)
    assert response.status_code == 200
    assert response.json() == new_prefs

    response = await client.get("/api/v1/users/me/voice-preferences")
    assert response.status_code == 200
    assert response.json() == new_prefs
