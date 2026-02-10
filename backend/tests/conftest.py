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
from motor.motor_asyncio import AsyncIOMotorClient

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import app
from database import db
# IMPORTANTE: Importar o limiter diretamente para o conseguir desligar
from middleware.rate_limit import limiter

# URL fictício para os testes
API_URL = "http://testserver/api"

@pytest_asyncio.fixture(scope="function")
async def client():
    """
    Cria um cliente HTTP assíncrono que fala DIRETAMENTE com a app.
    Resolve o problema do Rate Limit e do Event Loop.
    """
    # 1. DESLIGAR RATE LIMITER (Solução Definitiva)
    limiter.enabled = False
    
    # 2. RESOLVER "Event loop is closed"
    # O cliente Mongo global fica preso ao loop anterior. Criamos um novo.
    from database import mongo_url, db as global_db
    # Recriar cliente para o loop atual
    test_mongo_client = AsyncIOMotorClient(mongo_url)
    app.state.mongo_client = test_mongo_client
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=API_URL,
        timeout=30.0
    ) as ac:
        yield ac
    
    # Limpeza
    test_mongo_client.close()

# --- Fixtures de Autenticação ---

@pytest_asyncio.fixture
async def admin_token(client):
    """Obter token de admin"""
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123" 
    })
    
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