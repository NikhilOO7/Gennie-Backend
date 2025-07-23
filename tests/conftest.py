import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import SessionLocal
from app.models.user import User
from main import app  # Replace with your actual FastAPI app import

@pytest.fixture
def anyio_backend():
    return "asyncio"  # Configures the async backend for pytest to handle event loops properly

@pytest.fixture
async def db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

@pytest.fixture(scope="module")  # Use "module" scope for efficiency; adjust to "function" if needed for isolation
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(db: AsyncSession):
    user = User(id="test_user", email="test@example.com", hashed_password="password", voice_preference="default")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
