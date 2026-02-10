import sys
import os
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import app
# IMPORTANTE: Importar o limiter do sítio original
from middleware.rate_limit import limiter

# URL fictício para os testes
API_URL = "http://testserver/api"

@pytest_asyncio.fixture
async def client():
    """
    Cliente de teste. Desliga o Rate Limit globalmente.
    """
    # CORREÇÃO DEFINITIVA: Desligar o limiter na fonte
    limiter.enabled = False
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=API_URL,
        timeout=30.0
    ) as ac:
        yield ac

# --- Fixtures de Autenticação ---

@pytest_asyncio.fixture
async def admin_token(client):
    # Tenta login com a password padrão
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123" 
    })
    
    # Fallback
    if response.status_code != 200:
         response = await client.post("/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "admin2026"
        })
    
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]

@pytest_asyncio.fixture
async def consultor_token(client):
    await client.post("/auth/register", json={
        "email": "consultor@sistema.pt", "password": "consultor123",
        "name": "Consultor Teste", "role": "consultor"
    })
    response = await client.post("/auth/login", json={
        "email": "consultor@sistema.pt", "password": "consultor123"
    })
    return response.json().get("access_token")

@pytest_asyncio.fixture
async def mediador_token(client):
    await client.post("/auth/register", json={
        "email": "mediador@sistema.pt", "password": "mediador123",
        "name": "Mediador Teste", "role": "mediador"
    })
    response = await client.post("/auth/login", json={
        "email": "mediador@sistema.pt", "password": "mediador123"
    })
    return response.json().get("access_token")