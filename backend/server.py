import logging
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from database import db, client
from models.auth import UserRole
from services.auth import hash_password
from routes import (
    auth_router, processes_router, admin_router, 
    deadlines_router, activities_router, onedrive_router,
    public_router, stats_router, ai_router, documents_router
)


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


app = FastAPI(title="Sistema de Gestão de Processos")


# Include all routers under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(processes_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(deadlines_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(onedrive_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(documents_router, prefix="/api")


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.processes.create_index("id", unique=True)
    await db.processes.create_index("client_id")
    await db.deadlines.create_index("id", unique=True)
    await db.deadlines.create_index("process_id")
    await db.activities.create_index("process_id")
    await db.history.create_index("process_id")
    await db.workflow_statuses.create_index("name", unique=True)
    
    # Create default workflow statuses if none exist - 14 fases do Trello
    status_count = await db.workflow_statuses.count_documents({})
    if status_count == 0:
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
        logger.info("14 workflow statuses created (conforme Trello)")
    
    # Create default admin if not exists
    admin_exists = await db.users.find_one({"role": UserRole.ADMIN})
    if not admin_exists:
        admin_doc = {
            "id": str(uuid.uuid4()),
            "email": "admin@sistema.pt",
            "password": hash_password("admin123"),
            "name": "Administrador",
            "phone": None,
            "role": UserRole.ADMIN,
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        logger.info("Admin user created: admin@sistema.pt / admin123")
    
    # Create test clients if none exist
    client_count = await db.users.count_documents({"role": UserRole.CLIENTE})
    if client_count == 0:
        test_clients = [
            {"name": "João Silva", "email": "joao.silva@email.pt", "phone": "+351 912 345 678", "onedrive_folder": "João Silva"},
            {"name": "Maria Santos", "email": "maria.santos@email.pt", "phone": "+351 923 456 789", "onedrive_folder": "Maria Santos"},
            {"name": "Pedro Costa", "email": "pedro.costa@email.pt", "phone": "+351 934 567 890", "onedrive_folder": "Pedro Costa"},
        ]
        for test_client in test_clients:
            client_doc = {
                "id": str(uuid.uuid4()),
                "email": test_client["email"],
                "password": hash_password("cliente123"),
                "name": test_client["name"],
                "phone": test_client["phone"],
                "role": UserRole.CLIENTE,
                "is_active": True,
                "onedrive_folder": test_client["onedrive_folder"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(client_doc)
        logger.info("Test clients created (password: cliente123)")
    
    # Create test consultor and mediador if none exist
    consultor_exists = await db.users.find_one({"role": UserRole.CONSULTOR})
    if not consultor_exists:
        consultor_doc = {
            "id": str(uuid.uuid4()),
            "email": "consultor@sistema.pt",
            "password": hash_password("consultor123"),
            "name": "Carlos Consultor",
            "phone": "+351 961 234 567",
            "role": UserRole.CONSULTOR,
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(consultor_doc)
        logger.info("Test consultor created: consultor@sistema.pt / consultor123")
    
    mediador_exists = await db.users.find_one({"role": UserRole.MEDIADOR})
    if not mediador_exists:
        mediador_doc = {
            "id": str(uuid.uuid4()),
            "email": "mediador@sistema.pt",
            "password": hash_password("mediador123"),
            "name": "Ana Mediadora",
            "phone": "+351 962 345 678",
            "role": UserRole.MEDIADOR,
            "is_active": True,
            "onedrive_folder": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(mediador_doc)
        logger.info("Test mediador created: mediador@sistema.pt / mediador123")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
