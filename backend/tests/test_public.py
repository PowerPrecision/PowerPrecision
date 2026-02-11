import pytest


@pytest.mark.asyncio
async def test_public_client_registration(client):
    """Test public client registration creates user and process"""
    import uuid
    unique_email = f"test_{uuid.uuid4().hex[:8]}@email.pt"
    
    response = await client.post("/public/client-registration", json={
        "name": "Test Cliente Pytest",
        "email": unique_email,
        "phone": "+351 999 000 111",
        "process_type": "credito"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "process_id" in data
    # A mensagem pode variar se email foi enviado ou não
    assert "Registo criado com sucesso" in data["message"]


@pytest.mark.asyncio
async def test_public_registration_missing_fields(client):
    """Test public registration with missing required fields"""
    response = await client.post("/public/client-registration", json={
        "name": "Test User"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_public_registration_invalid_email(client):
    """Test public registration with invalid email format"""
    response = await client.post("/public/client-registration", json={
        "name": "Test User",
        "email": "not-an-email",
        "phone": "+351 999 000 111",
        "process_type": "credito"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_public_registration_with_personal_data(client):
    """Test public registration with optional personal data"""
    import uuid
    import random
    unique_email = f"test_full_{uuid.uuid4().hex[:8]}@email.pt"
    # Gerar NIF único que não começa com 5 (empresas)
    unique_nif = f"{random.choice([1,2,3,4])}{random.randint(10000000, 99999999)}"
    
    response = await client.post("/public/client-registration", json={
        "name": "Test Cliente Full",
        "email": unique_email,
        "phone": "+351 888 777 666",
        "process_type": "ambos",
        "personal_data": {
            "nif": unique_nif,
            "address": "Rua de Teste, 123",
            "nationality": "Portuguesa"
        },
        "financial_data": {
            "monthly_income": 2500.00,
            "employment_type": "Conta de outrem"
        }
    })
    assert response.status_code == 200
    data = response.json()
    # success deve ser True para registo bem sucedido
    assert data.get("success") is True or "process_id" in data


@pytest.mark.asyncio
async def test_public_registration_all_process_types(client):
    """Test all process types are accepted"""
    import uuid
    
    for process_type in ["credito", "imobiliaria", "ambos"]:
        unique_email = f"test_tipo_{process_type}_{uuid.uuid4().hex[:8]}@email.pt"
        response = await client.post("/public/client-registration", json={
            "name": f"Test Tipo {process_type}",
            "email": unique_email,
            "phone": "+351 111 222 333",
            "process_type": process_type
        })
        assert response.status_code == 200, f"Failed for type: {process_type}"
