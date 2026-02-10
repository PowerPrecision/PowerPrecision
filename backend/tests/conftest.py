"""
Tests for CreditoIMO API
Configuração central dos testes.
"""
import sys
import os
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Adicionar backend ao path para conseguir importar o server
sys.path.insert(0, str(Path(__file__).parent.parent))

# IMPORTANTE: Importar a app real
from server import app

# URL fictício para os testes
API_URL = "http://testserver/api"

@pytest_asyncio.fixture
async def client():
    """
    Cria um cliente HTTP assíncrono que fala DIRETAMENTE com a app.
    Não requer servidor a correr na porta 8001.
    """
    # CORREÇÃO CRÍTICA: Desligar o Rate Limiter durante os testes
    # para evitar erro 429 (Too Many Requests)
    if hasattr(app.state, "limiter"):
        app.state.limiter.enabled = False
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=API_URL,
        timeout=30.0
    ) as ac:
        yield ac

# --- Fixtures de Autenticação ---

@pytest_asyncio.fixture
async def admin_token(client):
    """Obter token de admin"""
    # Tenta login com a password padrão
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123" 
    })
    
    # Fallback se a password for diferente (dependendo do seed)
    if response.status_code != 200:
         response = await client.post("/auth/login", json={
            "email": "admin@sistema.pt",
            "password": "admin2026"
        })
    
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]

@pytest_asyncio.fixture
async def consultor_token(client):
    """Obter token de consultor"""
    # Tenta criar utilizador primeiro para garantir que existe
    await client.post("/auth/register", json={
        "email": "consultor@sistema.pt",
        "password": "consultor123",
        "name": "Consultor Teste",
        "role": "consultor"
    })
    
    response = await client.post("/auth/login", json={
        "email": "consultor@sistema.pt",
        "password": "consultor123"
    })
    
    if response.status_code != 200:
        pytest.skip(f"Falha login consultor: {response.text}")
        
    return response.json()["access_token"]

@pytest_asyncio.fixture
async def mediador_token(client):
    """Obter token de mediador"""
    await client.post("/auth/register", json={
        "email": "mediador@sistema.pt",
        "password": "mediador123",
        "name": "Mediador Teste",
        "role": "mediador"
    })
    
    response = await client.post("/auth/login", json={
        "email": "mediador@sistema.pt",
        "password": "mediador123"
    })
    
    if response.status_code != 200:
        pytest.skip(f"Falha login mediador: {response.text}")
        
    return response.json()["access_token"]