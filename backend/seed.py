#!/usr/bin/env python3
"""
==============================================
SEED DATABASE - CreditoIMO
==============================================
Script para criar utilizadores iniciais.
Executar apenas UMA VEZ na configuração inicial.

Uso:
    cd /app/backend
    python seed.py

ATENÇÃO: Não executar em produção se os utilizadores já existirem!
==============================================
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# User roles
class UserRole:
    CLIENTE = "cliente"
    CONSULTOR = "consultor"
    INTERMEDIARIO = "intermediario"
    MEDIADOR = "mediador"
    ADMINISTRATIVO = "administrativo"
    DIRETOR = "diretor"
    CEO = "ceo"
    ADMIN = "admin"


async def seed_users():
    """Criar utilizadores iniciais no sistema."""
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("=" * 50)
    print("CreditoIMO - Seed de Utilizadores")
    print("=" * 50)
    print(f"MongoDB: {mongo_url}")
    print(f"Database: {db_name}")
    print()
    
    # Lista de utilizadores a criar
    # NOTA: Altere as passwords antes de usar em produção!
    default_users = [
        {
            "email": "admin@sistema.pt",
            "password": "admin2026",  # ALTERAR EM PRODUÇÃO
            "name": "Admin",
            "role": UserRole.ADMIN,
            "phone": None,
            "company": "Sistema"
        },
        {
            "email": "pedro@powerealestate.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Pedro Borges",
            "role": UserRole.CEO,
            "phone": "+351 912 000 001",
            "company": "Power Real Estate"
        },
        {
            "email": "tiago@powerealestate.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Tiago Borges",
            "role": UserRole.CONSULTOR,
            "phone": "+351 912 000 002",
            "company": "Power Real Estate"
        },
        {
            "email": "flavio@powerealestate.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Flávio da Silva",
            "role": UserRole.CONSULTOR,
            "phone": "+351 912 000 003",
            "company": "Power Real Estate"
        },
        {
            "email": "estacio@precisioncredito.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Estácio Miranda",
            "role": UserRole.INTERMEDIARIO,
            "phone": "+351 912 000 004",
            "company": "Precision Crédito"
        },
        {
            "email": "fernando@precisioncredito.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Fernando Andrade",
            "role": UserRole.INTERMEDIARIO,
            "phone": "+351 912 000 005",
            "company": "Precision Crédito"
        },
        {
            "email": "carina@powerealestate.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Carina Amuedo",
            "role": UserRole.DIRETOR,
            "phone": "+351 912 000 006",
            "company": "Power Real Estate"
        },
        {
            "email": "marisa@powerealestate.pt",
            "password": "power2026",  # ALTERAR EM PRODUÇÃO
            "name": "Marisa Rodrigues",
            "role": UserRole.ADMINISTRATIVO,
            "phone": "+351 912 000 007",
            "company": "Power Real Estate"
        },
    ]
    
    created_count = 0
    skipped_count = 0
    
    for user_data in default_users:
        existing = await db.users.find_one({"email": user_data["email"]})
        
        if existing:
            print(f"  [SKIP] {user_data['name']} ({user_data['email']}) - já existe")
            skipped_count += 1
            continue
        
        user_doc = {
            "id": str(uuid.uuid4()),
            "email": user_data["email"],
            "password": hash_password(user_data["password"]),
            "name": user_data["name"],
            "phone": user_data.get("phone"),
            "role": user_data["role"],
            "company": user_data.get("company"),
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.users.insert_one(user_doc)
        print(f"  [OK] {user_data['name']} ({user_data['role']}) - {user_data['email']}")
        created_count += 1
    
    print()
    print("-" * 50)
    print(f"Utilizadores criados: {created_count}")
    print(f"Utilizadores ignorados (já existiam): {skipped_count}")
    print("-" * 50)
    
    # Mostrar total de utilizadores
    total = await db.users.count_documents({})
    print(f"\nTotal de utilizadores na base de dados: {total}")
    
    client.close()
    
    print()
    print("IMPORTANTE: Altere as passwords padrão em produção!")
    print("=" * 50)


async def seed_workflow_statuses():
    """Criar estados de workflow se não existirem."""
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    existing = await db.workflow_statuses.count_documents({})
    if existing > 0:
        print(f"\nWorkflow statuses já existem ({existing} estados). Ignorando...")
        client.close()
        return
    
    print("\nA criar estados de workflow...")
    
    default_statuses = [
        {"id": str(uuid.uuid4()), "name": "clientes_espera", "label": "Clientes em Espera", "order": 1, "color": "yellow", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "fase_documental", "label": "Fase Documental", "order": 2, "color": "blue", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "fase_documental_ii", "label": "Fase Documental II", "order": 3, "color": "blue", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "enviado_bruno", "label": "Enviado ao Bruno", "order": 4, "color": "purple", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "enviado_luis", "label": "Enviado ao Luís", "order": 5, "color": "purple", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "enviado_bcp_rui", "label": "Enviado BCP Rui", "order": 6, "color": "purple", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "entradas_precision", "label": "Entradas Precision", "order": 7, "color": "orange", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "fase_bancaria", "label": "Fase Bancária - Pré Aprovação", "order": 8, "color": "orange", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "fase_visitas", "label": "Fase de Visitas", "order": 9, "color": "blue", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "ch_aprovado", "label": "CH Aprovado - Avaliação", "order": 10, "color": "green", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "fase_escritura", "label": "Fase de Escritura", "order": 11, "color": "green", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "escritura_agendada", "label": "Escritura Agendada", "order": 12, "color": "green", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "concluidos", "label": "Concluídos", "order": 13, "color": "green", "is_default": True},
        {"id": str(uuid.uuid4()), "name": "desistencias", "label": "Desistências", "order": 14, "color": "red", "is_default": True},
    ]
    
    await db.workflow_statuses.insert_many(default_statuses)
    print(f"  [OK] {len(default_statuses)} estados de workflow criados")
    
    client.close()


async def main():
    """Função principal do seed."""
    await seed_users()
    await seed_workflow_statuses()


if __name__ == "__main__":
    asyncio.run(main())
