#!/usr/bin/env python3
"""
====================================================================
SCRIPT DE SEED PARA O SISTEMA CREDITOIMO
====================================================================
Este script popula a base de dados com dados de demonstração realistas
para o Sistema de Gestão de Processos Imobiliários e Crédito.

Autor: CreditoIMO Development Team
Versão: 2.0
Data: Janeiro 2026

Utilização:
    python scripts/seed_database.py

Este script cria:
- 8 utilizadores (Admin, CEO, Consultores, Intermediários)
- 155 processos com dados completos de clientes
- 43 eventos/prazos no calendário
- 847 documentos com validades
- 14 estados de workflow

ATENÇÃO: Este script limpa dados existentes antes de inserir novos!
====================================================================
"""

import asyncio
import uuid
import random
import os
import sys
from datetime import datetime, timedelta, timezone

# Adicionar o diretório backend ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

# ====================================================================
# CONFIGURAÇÃO DE SEGURANÇA
# ====================================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Gera hash seguro para a password usando bcrypt."""
    return pwd_context.hash(password)

# ====================================================================
# DADOS DE UTILIZADORES
# ====================================================================
# Utilizadores do sistema conforme especificação do PRD
# Incluem colaboradores da Power Real Estate e Precision Crédito

USERS_DATA = [
    {
        "email": "admin@sistema.pt",
        "password": "admin2026",
        "name": "Administrador",
        "role": "admin",
        "phone": None,
        "company": "Sistema"
    },
    {
        "email": "pedro@powerealestate.pt",
        "password": "power2026",
        "name": "Pedro Borges",
        "role": "ceo",
        "phone": "+351 912 000 001",
        "company": "Power Real Estate"
    },
    {
        "email": "tiago@powerealestate.pt",
        "password": "power2026",
        "name": "Tiago Borges",
        "role": "consultor",
        "phone": "+351 912 000 002",
        "company": "Power Real Estate"
    },
    {
        "email": "flavio@powerealestate.pt",
        "password": "power2026",
        "name": "Flávio da Silva",
        "role": "consultor",
        "phone": "+351 912 000 003",
        "company": "Power Real Estate"
    },
    {
        "email": "estacio@precisioncredito.pt",
        "password": "power2026",
        "name": "Estácio Miranda",
        "role": "intermediario",
        "phone": "+351 912 000 004",
        "company": "Precision Crédito"
    },
    {
        "email": "fernando@precisioncredito.pt",
        "password": "power2026",
        "name": "Fernando Andrade",
        "role": "intermediario",
        "phone": "+351 912 000 005",
        "company": "Precision Crédito"
    },
    {
        "email": "carina@powerealestate.pt",
        "password": "power2026",
        "name": "Carina Amuedo",
        "role": "consultor_intermediario",
        "phone": "+351 912 000 006",
        "company": "Power Real Estate"
    },
    {
        "email": "marisa@powerealestate.pt",
        "password": "power2026",
        "name": "Marisa Rodrigues",
        "role": "consultor_intermediario",
        "phone": "+351 912 000 007",
        "company": "Power Real Estate"
    }
]

# ====================================================================
# DADOS DE WORKFLOW
# ====================================================================
# 14 fases do processo conforme Trello original
WORKFLOW_STATUSES = [
    {"name": "clientes_espera", "label": "Clientes em Espera", "order": 1, "color": "#EAB308"},
    {"name": "fase_documental", "label": "Fase Documental", "order": 2, "color": "#3B82F6"},
    {"name": "fase_documental_ii", "label": "Fase Documental II", "order": 3, "color": "#3B82F6"},
    {"name": "enviado_bruno", "label": "Enviado ao Bruno", "order": 4, "color": "#8B5CF6"},
    {"name": "enviado_luis", "label": "Enviado ao Luís", "order": 5, "color": "#8B5CF6"},
    {"name": "enviado_bcp_rui", "label": "Enviado BCP Rui", "order": 6, "color": "#8B5CF6"},
    {"name": "entradas_precision", "label": "Entradas Precision", "order": 7, "color": "#F97316"},
    {"name": "fase_bancaria", "label": "Fase Bancária - Pré Aprovação", "order": 8, "color": "#F97316"},
    {"name": "fase_visitas", "label": "Fase de Visitas", "order": 9, "color": "#3B82F6"},
    {"name": "ch_aprovado", "label": "CH Aprovado - Avaliação", "order": 10, "color": "#22C55E"},
    {"name": "fase_escritura", "label": "Fase de Escritura", "order": 11, "color": "#22C55E"},
    {"name": "escritura_agendada", "label": "Escritura Agendada", "order": 12, "color": "#22C55E"},
    {"name": "concluidos", "label": "Concluídos", "order": 13, "color": "#22C55E"},
    {"name": "desistencias", "label": "Desistências", "order": 14, "color": "#EF4444"},
]

# ====================================================================
# DADOS AUXILIARES PARA GERAÇÃO DE PROCESSOS
# ====================================================================

# Nomes portugueses realistas
FIRST_NAMES = [
    "Maria", "João", "Ana", "Pedro", "Mariana", "Miguel", "Sofia", "André",
    "Beatriz", "Tiago", "Inês", "Rui", "Catarina", "Diogo", "Marta", "Francisco",
    "Carolina", "Ricardo", "Teresa", "Daniel", "Helena", "Luís", "Patrícia", "Bruno",
    "Sara", "Nuno", "Joana", "Carlos", "Rita", "José", "Filipa", "Paulo",
    "Raquel", "Hugo", "Cláudia", "Marco", "Susana", "Gonçalo", "Sandra", "Rafael",
    "Mónica", "Vasco", "Liliana", "Eduardo", "Alexandra", "David", "Fernanda", "Sérgio"
]

LAST_NAMES = [
    "Silva", "Santos", "Ferreira", "Pereira", "Oliveira", "Costa", "Rodrigues", "Martins",
    "Sousa", "Fernandes", "Gonçalves", "Gomes", "Lopes", "Marques", "Alves", "Almeida",
    "Ribeiro", "Pinto", "Carvalho", "Teixeira", "Moreira", "Correia", "Mendes", "Nunes",
    "Vieira", "Monteiro", "Cardoso", "Rocha", "Ramos", "Coelho", "Cruz", "Cunha",
    "Reis", "Simões", "Pires", "Araújo", "Fonseca", "Azevedo", "Barbosa", "Matos"
]

# Cidades e distritos portugueses
CITIES = [
    ("Lisboa", "Lisboa"), ("Porto", "Porto"), ("Braga", "Braga"),
    ("Setúbal", "Setúbal"), ("Aveiro", "Aveiro"), ("Leiria", "Leiria"),
    ("Coimbra", "Coimbra"), ("Faro", "Faro"), ("Viseu", "Viseu"),
    ("Santarém", "Santarém"), ("Viana do Castelo", "Viana do Castelo"),
    ("Vila Real", "Vila Real"), ("Bragança", "Bragança"), ("Évora", "Évora"),
    ("Almada", "Setúbal"), ("Cascais", "Lisboa"), ("Sintra", "Lisboa"),
    ("Oeiras", "Lisboa"), ("Matosinhos", "Porto"), ("Vila Nova de Gaia", "Porto"),
    ("Guimarães", "Braga"), ("Funchal", "Madeira"), ("Ponta Delgada", "Açores")
]

# Ruas portuguesas
STREETS = [
    "Rua da Liberdade", "Avenida da República", "Rua do Comércio", "Praça do Município",
    "Rua das Flores", "Avenida dos Aliados", "Rua Augusta", "Largo do Carmo",
    "Rua de Santa Catarina", "Avenida Almirante Reis", "Rua da Conceição", "Travessa do Forno",
    "Rua dos Clérigos", "Avenida da Boavista", "Rua Garrett", "Largo do Rato",
    "Rua do Ouro", "Avenida da Liberdade", "Rua Formosa", "Praça D. João I"
]

# Profissões
PROFESSIONS = [
    "Engenheiro/a", "Professor/a", "Médico/a", "Advogado/a", "Arquitecto/a",
    "Enfermeiro/a", "Contabilista", "Empresário/a", "Gestor/a", "Técnico/a de Informática",
    "Comercial", "Funcionário/a Público/a", "Bancário/a", "Farmacêutico/a", "Dentista",
    "Designer", "Jornalista", "Economista", "Psicólogo/a", "Assistente Administrativo/a"
]

# Estados civis
MARITAL_STATUS = ["Solteiro/a", "Casado/a", "União de Facto", "Divorciado/a", "Viúvo/a"]

# Bancos portugueses
BANKS = [
    "Millennium BCP", "Caixa Geral de Depósitos", "Santander Totta", "Novo Banco",
    "BPI", "Bankinter", "Crédito Agrícola", "Montepio", "Eurobic", "Activo Bank"
]

# Tipos de imóvel
PROPERTY_TYPES = ["Apartamento T1", "Apartamento T2", "Apartamento T3", "Apartamento T4",
                  "Moradia V2", "Moradia V3", "Moradia V4", "Moradia V5", "Terreno", "Loja"]

# Tipos de documento
DOCUMENT_TYPES = [
    ("cc", "Cartão de Cidadão"),
    ("passaporte", "Passaporte"),
    ("carta_conducao", "Carta de Condução"),
    ("contrato_trabalho", "Contrato de Trabalho"),
    ("recibos_vencimento", "Recibos de Vencimento"),
    ("irs", "Declaração IRS"),
    ("certidao_predial", "Certidão Predial"),
    ("caderneta_predial", "Caderneta Predial"),
    ("licenca_utilizacao", "Licença de Utilização"),
    ("ficha_tecnica", "Ficha Técnica Habitação")
]


# ====================================================================
# FUNÇÕES AUXILIARES
# ====================================================================

def generate_nif():
    """Gera um NIF português válido (formato simplificado)."""
    return f"{''.join([str(random.randint(0, 9)) for _ in range(9)])}"

def generate_phone():
    """Gera um número de telefone português."""
    prefixes = ["91", "92", "93", "96"]
    return f"+351 {random.choice(prefixes)}{random.randint(1000000, 9999999)}"

def generate_email(first_name, last_name):
    """Gera um endereço de email realista."""
    domains = ["gmail.com", "hotmail.com", "outlook.pt", "sapo.pt", "mail.pt"]
    return f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"

def generate_address(city_district):
    """Gera uma morada portuguesa."""
    city, district = city_district
    return f"{random.choice(STREETS)}, nº {random.randint(1, 200)}, {random.randint(1000, 9999)}-{random.randint(100, 999)} {city}"

def generate_birth_date(min_age=25, max_age=65):
    """Gera uma data de nascimento."""
    today = datetime.now()
    age = random.randint(min_age, max_age)
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return f"{birth_year}-{birth_month:02d}-{birth_day:02d}"

def generate_document_expiry(base_date=None, min_days=30, max_days=1825):
    """
    Gera uma data de validade para documento.
    Por defeito, entre 30 dias e 5 anos no futuro.
    Para documentos próximos a expirar, usar min_days e max_days apropriados.
    """
    if base_date is None:
        base_date = datetime.now()
    days_ahead = random.randint(min_days, max_days)
    expiry = base_date + timedelta(days=days_ahead)
    return expiry.strftime("%Y-%m-%d")


# ====================================================================
# FUNÇÃO PRINCIPAL DE SEED
# ====================================================================

async def seed_database():
    """
    Função principal que popula toda a base de dados.
    """
    print("=" * 70)
    print("  CREDITOIMO - SCRIPT DE SEED DA BASE DE DADOS")
    print("=" * 70)
    print()
    
    # Conectar à base de dados
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')  # Usar a mesma DB do backend
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print(f"📡 Conectado a: {mongo_url}")
    print(f"📁 Base de dados: {db_name}")
    print()
    
    # ----------------------------------------------------------------
    # LIMPAR DADOS EXISTENTES
    # ----------------------------------------------------------------
    print("🗑️  A limpar dados existentes...")
    await db.users.delete_many({})
    await db.processes.delete_many({})
    await db.deadlines.delete_many({})
    await db.documents.delete_many({})
    await db.workflow_statuses.delete_many({})
    await db.activities.delete_many({})
    await db.history.delete_many({})
    print("   ✅ Dados limpos com sucesso")
    print()
    
    # ----------------------------------------------------------------
    # CRIAR UTILIZADORES
    # ----------------------------------------------------------------
    print("👥 A criar utilizadores...")
    user_ids = {}
    
    for user_data in USERS_DATA:
        user_id = str(uuid.uuid4())
        user_ids[user_data["email"]] = user_id
        
        user_doc = {
            "id": user_id,
            "email": user_data["email"],
            "password": hash_password(user_data["password"]),
            "name": user_data["name"],
            "phone": user_data["phone"],
            "role": user_data["role"],
            "company": user_data.get("company"),
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
        print(f"   ✅ {user_data['name']} ({user_data['role']}) - {user_data['email']}")
    
    print(f"   📊 Total: {len(USERS_DATA)} utilizadores criados")
    print()
    
    # ----------------------------------------------------------------
    # CRIAR WORKFLOW STATUSES
    # ----------------------------------------------------------------
    print("📋 A criar estados de workflow...")
    
    for status in WORKFLOW_STATUSES:
        status_doc = {
            "id": str(uuid.uuid4()),
            "name": status["name"],
            "label": status["label"],
            "order": status["order"],
            "color": status["color"],
            "is_default": True
        }
        await db.workflow_statuses.insert_one(status_doc)
    
    print(f"   ✅ {len(WORKFLOW_STATUSES)} estados de workflow criados")
    print()
    
    # ----------------------------------------------------------------
    # CRIAR PROCESSOS
    # ----------------------------------------------------------------
    print("📁 A criar processos...")
    
    # IDs dos utilizadores para atribuição
    flavio_id = user_ids["flavio@powerealestate.pt"]
    tiago_id = user_ids["tiago@powerealestate.pt"]
    estacio_id = user_ids["estacio@precisioncredito.pt"]
    fernando_id = user_ids["fernando@precisioncredito.pt"]
    carina_id = user_ids["carina@powerealestate.pt"]
    marisa_id = user_ids["marisa@powerealestate.pt"]
    
    consultors = [flavio_id, tiago_id, carina_id, marisa_id]
    intermediarios = [estacio_id, fernando_id, carina_id, marisa_id]
    
    # Distribuição dos processos por fase
    status_distribution = {
        "clientes_espera": 15,
        "fase_documental": 20,
        "fase_documental_ii": 15,
        "enviado_bruno": 8,
        "enviado_luis": 8,
        "enviado_bcp_rui": 6,
        "entradas_precision": 12,
        "fase_bancaria": 18,
        "fase_visitas": 10,
        "ch_aprovado": 12,
        "fase_escritura": 8,
        "escritura_agendada": 5,
        "concluidos": 10,
        "desistencias": 8
    }
    
    processes = []
    process_ids = []
    process_count = 0
    
    # Distribuição específica para Flávio e Estácio
    # Flávio: 40 processos como consultor
    # Estácio: 35 processos como intermediário
    
    for status_name, count in status_distribution.items():
        for i in range(count):
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(LAST_NAMES)
            city_district = random.choice(CITIES)
            
            process_id = str(uuid.uuid4())
            process_ids.append(process_id)
            
            # Atribuição específica para garantir Flávio e Estácio têm processos
            if process_count < 40:
                # Primeiros 40 para Flávio como consultor
                consultor_id = flavio_id
            elif process_count < 80:
                # Próximos 40 para Tiago
                consultor_id = tiago_id
            else:
                # Restantes distribuídos
                consultor_id = random.choice(consultors)
            
            if process_count < 35:
                # Primeiros 35 para Estácio como intermediário
                intermediario_id = estacio_id
            elif process_count < 70:
                # Próximos 35 para Fernando
                intermediario_id = fernando_id
            else:
                # Restantes distribuídos
                intermediario_id = random.choice(intermediarios)
            
            monthly_income = random.randint(1200, 8000)
            property_value = random.randint(100000, 600000)
            
            process = {
                "id": process_id,
                "client_id": str(uuid.uuid4()),
                "client_name": f"{first_name} {last_name}",
                "client_email": generate_email(first_name, last_name),
                "client_phone": generate_phone(),
                "process_type": random.choice(["credito", "imobiliaria", "ambos"]),
                "status": status_name,
                "personal_data": {
                    "nif": generate_nif(),
                    "documento_id": f"{random.randint(10000000, 99999999)}",
                    "naturalidade": city_district[0],
                    "nacionalidade": "Portuguesa",
                    "morada_fiscal": generate_address(city_district),
                    "birth_date": generate_birth_date(),
                    "estado_civil": random.choice(MARITAL_STATUS),
                    "profissao": random.choice(PROFESSIONS),
                    "compra_tipo": random.choice(["Habitação Própria", "Investimento", "Segunda Habitação"])
                },
                "financial_data": {
                    "monthly_income": monthly_income,
                    "other_income": random.randint(0, 1500) if random.random() > 0.7 else 0,
                    "monthly_expenses": random.randint(400, 2000),
                    "employment_type": random.choice(["Efetivo", "Contrato a Termo", "Independente"]),
                    "employer_name": f"Empresa {random.choice(LAST_NAMES)}, Lda" if random.random() > 0.3 else None,
                    "employment_duration": f"{random.randint(1, 20)} anos",
                    "has_debts": random.random() > 0.7,
                    "debt_amount": random.randint(5000, 50000) if random.random() > 0.7 else 0,
                    "capital_proprio": random.randint(10000, 100000),
                    "valor_financiado": f"{property_value - random.randint(10000, 50000)}€",
                    "acesso_portal_financas": random.choice(["Sim", "Não"]),
                    "chave_movel_digital": random.choice(["Sim", "Não"]),
                    "renda_habitacao_atual": random.randint(400, 1200) if random.random() > 0.5 else 0,
                    "precisa_vender_casa": random.choice(["Sim", "Não"]),
                    "efetivo": random.choice(["Sim", "Não"]),
                    "fiador": random.choice(["Sim", "Não", "Não necessário"]),
                    "bancos_creditos": random.sample(BANKS, k=random.randint(0, 3))
                },
                "real_estate_data": {
                    "tipo_imovel": random.choice(PROPERTY_TYPES),
                    "num_quartos": random.choice(["T1", "T2", "T3", "T4", "T5+"]),
                    "localizacao": f"{city_district[0]}, {city_district[1]}",
                    "caracteristicas": random.sample(["Garagem", "Varanda", "Terraço", "Jardim", "Piscina", "Elevador", "Arrecadação"], k=random.randint(1, 4)),
                    "property_type": random.choice(PROPERTY_TYPES),
                    "property_zone": city_district[0],
                    "max_budget": property_value
                },
                "credit_data": {
                    "requested_amount": property_value,
                    "loan_term_years": random.choice([20, 25, 30, 35, 40]),
                    "interest_rate": round(random.uniform(2.5, 4.5), 2),
                    "bank_name": random.choice(BANKS) if status_name in ["ch_aprovado", "fase_escritura", "escritura_agendada", "concluidos"] else None,
                    "bank_approval_date": (datetime.now() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d") if status_name in ["ch_aprovado", "fase_escritura", "escritura_agendada", "concluidos"] else None
                },
                "assigned_consultor_id": consultor_id,
                "consultor_id": consultor_id,
                "assigned_mediador_id": intermediario_id,
                "intermediario_id": intermediario_id,
                "valor_financiado": f"{property_value}€",
                "idade_menos_35": random.random() > 0.6,
                "prioridade": random.random() > 0.8,
                "labels": random.sample(["Urgente", "VIP", "Primeira Casa", "Investidor", "Jovem"], k=random.randint(0, 2)),
                "notes": f"Processo criado para demonstração. Cliente interessado em {random.choice(PROPERTY_TYPES)} na zona de {city_district[0]}." if random.random() > 0.5 else None,
                "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 180))).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            processes.append(process)
            process_count += 1
    
    await db.processes.insert_many(processes)
    print(f"   ✅ {len(processes)} processos criados")
    
    # Contar atribuições
    flavio_count = sum(1 for p in processes if p["consultor_id"] == flavio_id)
    estacio_count = sum(1 for p in processes if p["intermediario_id"] == estacio_id)
    print(f"   📊 Flávio da Silva: {flavio_count} processos como consultor")
    print(f"   📊 Estácio Miranda: {estacio_count} processos como intermediário")
    print()
    
    # ----------------------------------------------------------------
    # CRIAR DOCUMENTOS COM VALIDADES
    # ----------------------------------------------------------------
    print("📄 A criar documentos com validades...")
    
    documents = []
    docs_expiring_soon = 0  # Documentos a expirar em 60 dias
    
    for process_id in process_ids:
        # Cada processo tem entre 3 a 8 documentos
        num_docs = random.randint(3, 8)
        selected_doc_types = random.sample(DOCUMENT_TYPES, k=min(num_docs, len(DOCUMENT_TYPES)))
        
        for doc_type, doc_name in selected_doc_types:
            # 15% dos documentos expiram nos próximos 60 dias (para alertas)
            if random.random() < 0.15:
                expiry_date = generate_document_expiry(min_days=1, max_days=60)
                docs_expiring_soon += 1
            else:
                expiry_date = generate_document_expiry(min_days=61, max_days=1825)
            
            doc = {
                "id": str(uuid.uuid4()),
                "process_id": process_id,
                "document_type": doc_type,
                "document_name": doc_name,
                "expiry_date": expiry_date,
                "notes": f"Documento {doc_name} do cliente" if random.random() > 0.7 else None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": random.choice(list(user_ids.values()))
            }
            documents.append(doc)
    
    await db.documents.insert_many(documents)
    
    # Copiar também para document_expiries (usado pela API)
    await db.document_expiries.delete_many({})
    await db.document_expiries.insert_many(documents)
    
    print(f"   ✅ {len(documents)} documentos criados")
    print(f"   ⚠️  {docs_expiring_soon} documentos a expirar nos próximos 60 dias")
    print()
    
    # ----------------------------------------------------------------
    # CRIAR PRAZOS/EVENTOS NO CALENDÁRIO
    # ----------------------------------------------------------------
    print("📅 A criar eventos no calendário...")
    
    deadlines = []
    deadline_titles = [
        "Reunião com cliente",
        "Entregar documentação",
        "Visita ao imóvel",
        "Contactar banco",
        "Preparar proposta",
        "Revisão de contrato",
        "Assinatura de CPCV",
        "Avaliação do imóvel",
        "Escritura",
        "Follow-up cliente",
        "Verificar aprovação crédito",
        "Enviar documentos ao banco"
    ]
    
    all_user_ids = list(user_ids.values())
    
    for i in range(43):
        process_id = random.choice(process_ids) if random.random() > 0.2 else None
        assigned_user = random.choice(all_user_ids)
        
        # Datas: 30% no passado, 70% no futuro (próximos 90 dias)
        if random.random() < 0.3:
            due_date = datetime.now() - timedelta(days=random.randint(1, 30))
        else:
            due_date = datetime.now() + timedelta(days=random.randint(1, 90))
        
        deadline = {
            "id": str(uuid.uuid4()),
            "process_id": process_id,
            "title": random.choice(deadline_titles),
            "description": f"Prazo importante para o processo." if random.random() > 0.5 else None,
            "due_date": due_date.strftime("%Y-%m-%d"),
            "priority": random.choice(["low", "medium", "high"]),
            "completed": due_date < datetime.now() and random.random() > 0.3,
            "status": "completed" if due_date < datetime.now() and random.random() > 0.3 else "pending",
            "assigned_user_id": assigned_user,
            "assigned_consultor_id": random.choice(consultors),
            "assigned_mediador_id": random.choice(intermediarios),
            "created_by": random.choice(all_user_ids),
            "created_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))).isoformat()
        }
        deadlines.append(deadline)
    
    await db.deadlines.insert_many(deadlines)
    print(f"   ✅ {len(deadlines)} eventos criados no calendário")
    print()
    
    # ----------------------------------------------------------------
    # CRIAR ÍNDICES
    # ----------------------------------------------------------------
    print("🔧 A criar índices...")
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.processes.create_index("id", unique=True)
    await db.processes.create_index("client_id")
    await db.processes.create_index("consultor_id")
    await db.processes.create_index("intermediario_id")
    await db.deadlines.create_index("id", unique=True)
    await db.deadlines.create_index("process_id")
    await db.documents.create_index("id", unique=True)
    await db.documents.create_index("process_id")
    await db.documents.create_index("expiry_date")
    await db.workflow_statuses.create_index("name", unique=True)
    print("   ✅ Índices criados")
    print()
    
    # ----------------------------------------------------------------
    # SUMÁRIO FINAL
    # ----------------------------------------------------------------
    print("=" * 70)
    print("  SEED COMPLETO!")
    print("=" * 70)
    print()
    print("  📊 RESUMO DOS DADOS CRIADOS:")
    print(f"     • Utilizadores: {len(USERS_DATA)}")
    print(f"     • Processos: {len(processes)}")
    print(f"     • Documentos: {len(documents)}")
    print(f"     • Eventos/Prazos: {len(deadlines)}")
    print(f"     • Estados de Workflow: {len(WORKFLOW_STATUSES)}")
    print()
    print("  👥 ATRIBUIÇÕES:")
    print(f"     • Flávio da Silva (Consultor): {flavio_count} processos")
    print(f"     • Estácio Miranda (Intermediário): {estacio_count} processos")
    print()
    print("  🔐 CREDENCIAIS DE ACESSO:")
    for user in USERS_DATA:
        print(f"     • {user['email']} / {user['password']} ({user['role']})")
    print()
    print("=" * 70)
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
