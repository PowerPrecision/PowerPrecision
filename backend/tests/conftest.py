"""
Tests for CreditoIMO API
These tests run against the actual running server.
Make sure the backend is running before executing tests.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pytest
import pytest_asyncio
from httpx import AsyncClient


# Get the API URL from environment or use default
API_URL = os.environ.get('TEST_API_URL', 'http://localhost:8001/api')


@pytest_asyncio.fixture
async def client():
    """Create async HTTP client for testing"""
    async with AsyncClient(base_url=API_URL, timeout=30.0) as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_token(client):
    """Get admin authentication token"""
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123"
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def consultor_token(client):
    """Get consultor authentication token"""
    response = await client.post("/auth/login", json={
        "email": "consultor@sistema.pt",
        "password": "consultor123"
    })
    assert response.status_code == 200, f"Consultor login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def mediador_token(client):
    """Get mediador authentication token"""
    response = await client.post("/auth/login", json={
        "email": "mediador@sistema.pt",
        "password": "mediador123"
    })
    assert response.status_code == 200, f"Mediador login failed: {response.text}"
    return response.json()["access_token"]
