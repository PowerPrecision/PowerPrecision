#!/usr/bin/env python3
"""
==============================================
SEED PROCESSES - Dados de Teste
==============================================
Script para criar processos de exemplo.
Executar DEPOIS do seed.py (utilizadores precisam existir).

Uso:
    python seed_processes.py

==============================================
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import random

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


async def seed_processes():
    """Criar processos de exemplo."""
    
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("=" * 50)
    print("CreditoIMO - Seed de Processos")
    print("=" * 50)
    print(f"MongoDB: {mongo_url[:50]}...")
    print(f"Database: {db_name}")
    print()
    
    # Verificar se já existem processos
    existing = await db.processes.count_documents({})
    if existing > 0:
        print(f"⚠️  Já existem {existing} processos na base de dados.")
        print("   Para adicionar mais, apague os existentes primeiro.")
        client.close()
        return
    
    # Obter utilizadores existentes
    consultores = await db.users.find({"role": "consultor"}).to_list(100)
    intermediarios = await db.users.find({"role": {"$in": ["intermediario", "mediador"]}}).to_list(100)
    
    if not consultores:
        print("❌ Erro: Não existem consultores. Execute seed.py primeiro!")
        client.close()
        return
    
    # Obter estados de workflow
    statuses = await db.workflow_statuses.find({}).sort("order", 1).to_list(100)
    if not statuses:
        print("❌ Erro: Não existem estados de workflow. Execute seed.py primeiro!")
        client.close()
        return
    
    status_names = [s["name"] for s in statuses]
    
    # Lista de processos de exemplo
    sample_processes = [
        {
            "client_name": "João Silva",
            "client_email": "joao.silva@email.com",
            "client_phone": "+351 912 345 678",
            "process_type": "credito_habitacao",
            "status": "fase_documental",
            "personal_data": {
                "nome_completo": "João Manuel Silva",
                "nif": "123456789",
                "data_nascimento": "1985-03-15",
                "estado_civil": "casado",
                "morada": "Rua das Flores 123, Lisboa"
            },
            "financial_data": {
                "rendimento_mensal": "2500",
                "entidade_patronal": "Empresa ABC Lda",
                "tipo_contrato": "efetivo"
            }
        },
        {
            "client_name": "Maria Santos",
            "client_email": "maria.santos@email.com",
            "client_phone": "+351 913 456 789",
            "process_type": "credito_habitacao",
            "status": "fase_bancaria",
            "personal_data": {
                "nome_completo": "Maria Fernanda Santos",
                "nif": "987654321",
                "data_nascimento": "1990-07-22",
                "estado_civil": "solteiro",
                "morada": "Av. da Liberdade 456, Porto"
            },
            "financial_data": {
                "rendimento_mensal": "1800",
                "entidade_patronal": "Hospital Central",
                "tipo_contrato": "efetivo"
            }
        },
        {
            "client_name": "Pedro Costa",
            "client_email": "pedro.costa@email.com",
            "client_phone": "+351 914 567 890",
            "process_type": "credito_habitacao",
            "status": "clientes_espera",
            "personal_data": {
                "nome_completo": "Pedro Miguel Costa",
                "nif": "456789123",
                "data_nascimento": "1988-11-30",
                "estado_civil": "casado"
            }
        },
        {
            "client_name": "Ana Ferreira",
            "client_email": "ana.ferreira@email.com",
            "client_phone": "+351 915 678 901",
            "process_type": "credito_habitacao",
            "status": "ch_aprovado",
            "personal_data": {
                "nome_completo": "Ana Cristina Ferreira",
                "nif": "789123456",
                "data_nascimento": "1992-05-10",
                "estado_civil": "solteiro"
            },
            "real_estate_data": {
                "tipo_imovel": "apartamento",
                "localizacao": "Cascais",
                "valor_aquisicao": "350000"
            }
        },
        {
            "client_name": "Carlos Rodrigues",
            "client_email": "carlos.rodrigues@email.com",
            "client_phone": "+351 916 789 012",
            "process_type": "credito_habitacao",
            "status": "fase_escritura",
            "personal_data": {
                "nome_completo": "Carlos Alberto Rodrigues",
                "nif": "321654987"
            }
        },
        {
            "client_name": "Sofia Martins",
            "client_email": "sofia.martins@email.com",
            "client_phone": "+351 917 890 123",
            "process_type": "credito_habitacao",
            "status": "enviado_bruno",
            "personal_data": {
                "nome_completo": "Sofia Alexandra Martins",
                "nif": "654987321"
            }
        },
        {
            "client_name": "Ricardo Almeida",
            "client_email": "ricardo.almeida@email.com",
            "client_phone": "+351 918 901 234",
            "process_type": "credito_habitacao",
            "status": "fase_visitas",
            "personal_data": {
                "nome_completo": "Ricardo José Almeida",
                "nif": "147258369"
            }
        },
        {
            "client_name": "Teresa Oliveira",
            "client_email": "teresa.oliveira@email.com",
            "client_phone": "+351 919 012 345",
            "process_type": "credito_habitacao",
            "status": "entradas_precision",
            "personal_data": {
                "nome_completo": "Teresa Maria Oliveira",
                "nif": "369258147"
            }
        },
        {
            "client_name": "Bruno Sousa",
            "client_email": "bruno.sousa@email.com",
            "client_phone": "+351 920 123 456",
            "process_type": "credito_habitacao",
            "status": "concluidos"
        },
        {
            "client_name": "Inês Pereira",
            "client_email": "ines.pereira@email.com",
            "client_phone": "+351 921 234 567",
            "process_type": "credito_habitacao",
            "status": "fase_documental_ii"
        }
    ]
    
    created_count = 0
    process_number = 1
    now = datetime.now(timezone.utc)
    
    for proc_data in sample_processes:
        # Atribuir consultor e intermediário aleatoriamente
        consultor = random.choice(consultores) if consultores else None
        intermediario = random.choice(intermediarios) if intermediarios else None
        
        # Criar documento do processo
        process_doc = {
            "id": str(uuid.uuid4()),
            "process_number": process_number,
            "client_name": proc_data["client_name"],
            "client_email": proc_data.get("client_email", ""),
            "client_phone": proc_data.get("client_phone", ""),
            "client_id": None,
            "process_type": proc_data.get("process_type", "credito_habitacao"),
            "status": proc_data.get("status", "clientes_espera"),
            "personal_data": proc_data.get("personal_data", {}),
            "financial_data": proc_data.get("financial_data", {}),
            "real_estate_data": proc_data.get("real_estate_data", {}),
            "credit_data": {},
            "assigned_consultor_id": consultor["id"] if consultor else None,
            "consultor_name": consultor["name"] if consultor else None,
            "assigned_mediador_id": intermediario["id"] if intermediario else None,
            "mediador_name": intermediario["name"] if intermediario else None,
            "source": "seed_data",
            "created_at": (now - timedelta(days=random.randint(1, 60))).isoformat(),
            "updated_at": now.isoformat()
        }
        
        await db.processes.insert_one(process_doc)
        print(f"  [OK] #{process_number} {proc_data['client_name']} - {proc_data.get('status', 'clientes_espera')}")
        
        process_number += 1
        created_count += 1
    
    print()
    print("-" * 50)
    print(f"Processos criados: {created_count}")
    print("-" * 50)
    
    # Mostrar resumo por estado
    print("\nResumo por estado:")
    for status in statuses[:8]:  # Primeiros 8 estados
        count = await db.processes.count_documents({"status": status["name"]})
        if count > 0:
            print(f"  {status['label']}: {count}")
    
    client.close()
    print()
    print("=" * 50)
    print("✅ Seed de processos concluído!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(seed_processes())
