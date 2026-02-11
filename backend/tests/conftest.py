"""
Tests for CreditoIMO API
Configuração central dos testes.

Os utilizadores de teste são criados automaticamente:
- admin@sistema.pt / admin123
- consultor@sistema.pt / consultor123  
- mediador@sistema.pt / mediador123
"""
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# CORREÇÃO: Definir modo de teste ANTES de importar a app
os.environ["TESTING"] = "true"

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# URL fictício para os testes
API_URL = "http://testserver/api"

# Utilizadores de teste
TEST_USERS = [
    {
        "email": "admin@sistema.pt",
        "password": "admin123",
        "name": "Admin Teste",
        "role": "admin"
    },
    {
        "email": "consultor@sistema.pt",
        "password": "consultor123",
        "name": "Consultor Teste",
        "role": "consultor"
    },
    {
        "email": "mediador@sistema.pt",
        "password": "mediador123",
        "name": "Mediador Teste",
        "role": "mediador"
    }
]


async def ensure_test_users_exist():
    """
    Garantir que os utilizadores de teste existem na base de dados.
    Cria-os se não existirem, actualiza a password se existirem.
    """
    try:
        import bcrypt
        from database import get_db
        
        db = get_db()
        
        for user_data in TEST_USERS:
            existing = await db.users.find_one({"email": user_data["email"]})
            hashed_password = bcrypt.hashpw(
                user_data["password"].encode("utf-8"),
                bcrypt.gensalt()
            ).decode("utf-8")
            
            if existing:
                # Actualizar password para garantir que está correcta
                await db.users.update_one(
                    {"email": user_data["email"]},
                    {"$set": {"password": hashed_password}}
                )
            else:
                # Criar utilizador
                await db.users.insert_one({
                    "id": str(uuid.uuid4()),
                    "email": user_data["email"],
                    "password": hashed_password,
                    "name": user_data["name"],
                    "role": user_data["role"],
                    "phone": "+351 900000000",
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    except Exception as e:
        print(f"Warning: Could not ensure test users exist: {e}")


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """
    Cria um cliente HTTP assíncrono que fala DIRETAMENTE com a app.
    Reset da conexão DB antes de cada teste para evitar problemas de event loop.
    """
    from database import reset_db_connection
    from server import app
    from middleware.rate_limit import limiter
    
    # Reset conexão DB para forçar nova conexão com o event loop actual
    reset_db_connection()
    
    # Garantir que os utilizadores de teste existem
    await ensure_test_users_exist()
    
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
    """Obter token de admin."""
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123"
    })
    
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def consultor_token(client):
    """Obter token de consultor."""
    response = await client.post("/auth/login", json={
        "email": "consultor@sistema.pt",
        "password": "consultor123"
    })
    assert response.status_code == 200, f"Consultor login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def mediador_token(client):
    """Obter token de mediador."""
    response = await client.post("/auth/login", json={
        "email": "mediador@sistema.pt",
        "password": "mediador123"
    })
    assert response.status_code == 200, f"Mediador login failed: {response.text}"
    return response.json()["access_token"]
