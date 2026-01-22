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
from routes.alerts import router as alerts_router


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
app.include_router(alerts_router, prefix="/api")


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
    
    # Create default users if they don't exist (conforme PRD)
    default_users = [
        {"email": "admin@sistema.pt", "password": "admin2026", "name": "Admin", "role": UserRole.ADMIN, "phone": None},
        {"email": "pedro@powerealestate.pt", "password": "power2026", "name": "Pedro Borges", "role": UserRole.CEO, "phone": "+351 912 000 001"},
        {"email": "tiago@powerealestate.pt", "password": "power2026", "name": "Tiago Borges", "role": UserRole.CONSULTOR, "phone": "+351 912 000 002"},
        {"email": "flavio@powerealestate.pt", "password": "power2026", "name": "Flávio da Silva", "role": UserRole.CONSULTOR, "phone": "+351 912 000 003"},
        {"email": "estacio@precisioncredito.pt", "password": "power2026", "name": "Estácio Miranda", "role": UserRole.INTERMEDIARIO, "phone": "+351 912 000 004"},
        {"email": "fernando@precisioncredito.pt", "password": "power2026", "name": "Fernando Andrade", "role": UserRole.INTERMEDIARIO, "phone": "+351 912 000 005"},
        {"email": "carina@powerealestate.pt", "password": "power2026", "name": "Carina Amuedo", "role": UserRole.DIRETOR, "phone": "+351 912 000 006"},
        {"email": "marisa@powerealestate.pt", "password": "power2026", "name": "Marisa Rodrigues", "role": UserRole.ADMINISTRATIVO, "phone": "+351 912 000 007"},
    ]
    
    for user_data in default_users:
        user_exists = await db.users.find_one({"email": user_data["email"]})
        if not user_exists:
            user_doc = {
                "id": str(uuid.uuid4()),
                "email": user_data["email"],
                "password": hash_password(user_data["password"]),
                "name": user_data["name"],
                "phone": user_data.get("phone"),
                "role": user_data["role"],
                "is_active": True,
                "onedrive_folder": None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user_doc)
            logger.info(f"User created: {user_data['name']} ({user_data['role']}) - {user_data['email']}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
