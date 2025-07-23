import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

@pytest.mark.anyio
async def test_get_user_voice_preference(client: AsyncClient, test_user: User):
    response = await client.get(f"/users/{test_user.id}/voice-preference")
    assert response.status_code == 200
    assert response.json() == {"voice_preference": "default"}

@pytest.mark.anyio
async def test_update_user_voice_preference(client: AsyncClient, test_user: User):
    response = await client.put(
        f"/users/{test_user.id}/voice-preference",
        json={"voice_preference": "new-voice"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Voice preference updated successfully"}

    # Verify the change in the database
    response = await client.get(f"/users/{test_user.id}/voice-preference")
    assert response.status_code == 200
    assert response.json() == {"voice_preference": "new-voice"}
