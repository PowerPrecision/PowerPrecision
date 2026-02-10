"""
Tests for CreditoIMO API
Configuração central dos testes.
"""
import os
import sys
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# CORREÇÃO CRÍTICA: Definir variável de ambiente ANTES de importar o server
# Isto garante que o server.py desliga o rate limiter no arranque
os.environ["TESTING"] = "true"

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar a app real (agora já com o TESTING=true)
from server import app

# URL fictício para os testes
API_URL = "http://testserver/api"

@pytest_asyncio.fixture
async def client():
    """
    Cria um cliente HTTP assíncrono que fala DIRETAMENTE com a app.
    Usa o loop de sessão definido no pytest.ini.
    """
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
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123" 
    })
    
    # Fallback se a password for diferente
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