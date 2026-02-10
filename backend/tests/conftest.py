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

# CORREÇÃO: Definir modo de teste ANTES de importar a app
os.environ["TESTING"] = "true"

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import app
from database import db
from services.auth import hash_password
# Importar limiter para garantir que está desligado
from middleware.rate_limit import limiter

# URL fictício para os testes
API_URL = "http://testserver/api"

@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Cria uma instância do event loop para toda a sessão de testes."""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="function")
async def client():
    """
    Cria um cliente HTTP assíncrono que fala DIRETAMENTE com a app.
    """
    # Garantia extra de que o rate limit está off
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
    """Obter token de admin. Cria o user se não existir."""
    email = "admin@sistema.pt"
    password = "admin123"
    
    # 1. Garantir que o user existe na DB (Seed automático)
    hashed = hash_password(password)
    await db.users.update_one(
        {"email": email},
        {"$set": {
            "email": email,
            "password": hashed,
            "name": "Admin Teste",
            "role": "admin",
            "is_active": True
        }},
        upsert=True
    )
    
    # 2. Fazer Login
    response = await client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]

@pytest_asyncio.fixture
async def consultor_token(client):
    """Obter token de consultor. Cria o user se não existir."""
    email = "consultor@sistema.pt"
    password = "consultor123"
    
    hashed = hash_password(password)
    await db.users.update_one(
        {"email": email},
        {"$set": {
            "email": email,
            "password": hashed,
            "name": "Consultor Teste",
            "role": "consultor",
            "is_active": True
        }},
        upsert=True
    )
    
    response = await client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]

@pytest_asyncio.fixture
async def mediador_token(client):
    """Obter token de mediador. Cria o user se não existir."""
    email = "mediador@sistema.pt"
    password = "mediador123"
    
    hashed = hash_password(password)
    await db.users.update_one(
        {"email": email},
        {"$set": {
            "email": email,
            "password": hashed,
            "name": "Mediador Teste",
            "role": "mediador",
            "is_active": True
        }},
        upsert=True
    )
    
    response = await client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]