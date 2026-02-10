"""
Tests for CreditoIMO API
Configuração central dos testes.

NOTA: Os utilizadores de teste devem existir na DB:
- admin@sistema.pt / admin123
- consultor@sistema.pt / consultor123  
- mediador@sistema.pt / mediador123
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
    Reset da conexão DB antes de cada teste para evitar problemas de event loop.
    """
    from database import reset_db_connection
    from server import app
    from middleware.rate_limit import limiter
    
    # Reset conexão DB para forçar nova conexão com o event loop actual
    reset_db_connection()
    
    # Garantia extra de que o rate limit está off
    limiter.enabled = False
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=API_URL,
        timeout=30.0
    ) as ac:
        yield ac
    
    # Cleanup após teste
    reset_db_connection()


# --- Fixtures de Autenticação ---
# NOTA: Os utilizadores devem já existir na DB (criados via seed)

@pytest_asyncio.fixture
async def admin_token(client):
    """Obter token de admin (user deve existir na DB)."""
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123"
    })
    
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def consultor_token(client):
    """Obter token de consultor (user deve existir na DB)."""
    response = await client.post("/auth/login", json={
        "email": "consultor@sistema.pt",
        "password": "consultor123"
    })
    assert response.status_code == 200, f"Consultor login failed: {response.text}"
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def mediador_token(client):
    """Obter token de mediador (user deve existir na DB)."""
    response = await client.post("/auth/login", json={
        "email": "mediador@sistema.pt",
        "password": "mediador123"
    })
    assert response.status_code == 200, f"Mediador login failed: {response.text}"
    return response.json()["access_token"]