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

# URL fictício para os testes (interceptado pelo ASGITransport)
API_URL = "http://testserver/api"

@pytest_asyncio.fixture
async def client():
    """
    Cria um cliente HTTP assíncrono que fala DIRETAMENTE com a app.
    Não requer servidor a correr na porta 8001.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=API_URL,
        timeout=30.0
    ) as ac:
        yield ac

# --- Fixtures de Autenticação (Mantidas e Atualizadas) ---

@pytest_asyncio.fixture
async def admin_token(client):
    """Obter token de admin"""
    response = await client.post("/auth/login", json={
        "email": "admin@sistema.pt",
        "password": "admin123" # A password definida no seed.py
    })
    # Se falhar, tenta a password alternativa que tinhas nos outros testes
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
    assert response.status_code == 200, f"Consultor login failed: {response.text}"
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
    assert response.status_code == 200, f"Mediador login failed: {response.text}"
    return response.json()["access_token"]