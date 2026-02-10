"""
Tests for CreditoIMO API
Configuração central dos testes.
"""
import os
import sys
from pathlib import Path
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# CORREÇÃO: Definir modo de teste ANTES de importar a app
os.environ["TESTING"] = "true"

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import app
from middleware.rate_limit import limiter

# URL fictício para os testes
API_URL = "http://testserver/api"

# Configurar pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Cria uma instância do event loop para toda a sessão de testes."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
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


@pytest_asyncio.fixture(scope="function")
async def db_client():
    """
    Fixture que fornece acesso à DB dentro do mesmo event loop.
    """
    from database import db
    yield db


async def _ensure_test_user_via_db(db, email: str, password: str, name: str, role: str):
    """Helper para criar/atualizar utilizador de teste diretamente na DB."""
    import uuid
    from datetime import datetime, timezone
    from services.auth import hash_password
    
    hashed = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()
    
    # Verificar se já existe
    existing = await db.users.find_one({"email": email})
    
    if existing:
        # Atualizar password e garantir que está ativo
        await db.users.update_one(
            {"email": email},
            {"$set": {
                "password": hashed,
                "is_active": True
            }}
        )
    else:
        # Criar novo utilizador
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": email,
            "password": hashed,
            "name": name,
            "role": role,
            "is_active": True,
            "created_at": now
        })


# --- Fixtures de Autenticação ---

@pytest_asyncio.fixture
async def admin_token(client, db_client):
    """Obter token de admin. Cria o user se não existir."""
    email = "admin@sistema.pt"
    password = "admin123"
    
    # 1. Garantir que o user existe na DB
    await _ensure_test_user_via_db(db_client, email, password, "Admin Teste", "admin")
    
    # 2. Fazer Login
    response = await client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def consultor_token(client, db_client):
    """Obter token de consultor. Cria o user se não existir."""
    email = "consultor@sistema.pt"
    password = "consultor123"
    
    await _ensure_test_user_via_db(db_client, email, password, "Consultor Teste", "consultor")
    
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Consultor login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def mediador_token(client, db_client):
    """Obter token de mediador. Cria o user se não existir."""
    email = "mediador@sistema.pt"
    password = "mediador123"
    
    await _ensure_test_user_via_db(db_client, email, password, "Mediador Teste", "mediador")
    
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, f"Mediador login failed: {response.text}"
    return response.json()["access_token"]