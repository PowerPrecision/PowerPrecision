import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from server import app, startup


_initialized = False

async def ensure_initialized():
    """Ensure the app is initialized"""
    global _initialized
    if not _initialized:
        await startup()
        _initialized = True


@pytest_asyncio.fixture
async def client():
    """Create async test client"""
    await ensure_initialized()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_token(client):
    """Get admin authentication token"""
    response = await client.post("/api/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def consultor_token(client):
    """Get consultor authentication token"""
    response = await client.post("/api/auth/login", json={
        "email": "consultor@sistema.pt",
        "password": "consultor123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def mediador_token(client):
    """Get mediador authentication token"""
    response = await client.post("/api/auth/login", json={
        "email": "mediador@sistema.pt",
        "password": "mediador123"
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]
