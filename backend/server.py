"""
====================================================================
CREDITOIMO - BACKEND SERVER
====================================================================
Sistema de Gestão de Processos de Crédito Habitação

Observabilidade: Sentry SDK para error tracking e performance monitoring
====================================================================
"""
import logging
import uuid
from datetime import datetime, timezone

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.pymongo import PyMongoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, 
    CORS_ALLOW_HEADERS, CORS_MAX_AGE,
    SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE,
    SENTRY_PROFILES_SAMPLE_RATE, SENTRY_SEND_DEFAULT_PII
)
from database import db, client
from models.auth import UserRole
from services.auth import hash_password
# CORREÇÃO: Importar o limiter e USAR este, não criar outro
from middleware.rate_limit import limiter
from routes import (
    auth_router, processes_router, admin_router, users_router,
    deadlines_router, activities_router,
    public_router, stats_router, ai_router, documents_router
)
from routes.alerts import router as alerts_router
from routes.websocket import router as websocket_router
from routes.push_notifications import router as push_notifications_router
from routes.tasks import router as tasks_router
from routes.emails import router as emails_router
from routes.trello import router as trello_router
from routes.ai_bulk import router as ai_bulk_router
from routes.leads import router as leads_router
from routes.match import router as match_router
from routes.system_config import router as system_config_router
from routes.properties import router as properties_router
from routes.clients import router as clients_router
from routes.gdpr import router as gdpr_router
from routes.backup import router as backup_router


# ====================================================================
# SENTRY INITIALIZATION (antes de qualquer outra coisa)
# ====================================================================
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            PyMongoIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        send_default_pii=SENTRY_SEND_DEFAULT_PII,
        before_send=_sentry_before_send,
        release=f"creditoimo@{datetime.now().strftime('%Y.%m.%d')}",
        attach_stacktrace=True,
        debug=SENTRY_ENVIRONMENT == "development",
    )

def _sentry_before_send(event, hint):
    if "exception" in event:
        exc_type = event.get("exception", {}).get("values", [{}])[0].get("type", "")
        if exc_type in ["RateLimitExceeded"]:
            return None
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[FILTERED]"
    return event

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sistema de Gestão de Processos")

# CORREÇÃO: Usar o limiter importado de middleware.rate_limit
# Não criar um novo instance aqui com limiter = Limiter(...)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include all routers under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(processes_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(deadlines_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(push_notifications_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(trello_router, prefix="/api")
app.include_router(ai_bulk_router, prefix="/api")
app.include_router(leads_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(system_config_router, prefix="/api")
app.include_router(properties_router, prefix="/api")
app.include_router(clients_router, prefix="/api")
app.include_router(gdpr_router, prefix="/api")
app.include_router(backup_router, prefix="/api")

# ====================================================================
# HEALTH CHECK ENDPOINTS
# ====================================================================
@app.get("/health")
async def health_check():
    from fastapi.responses import JSONResponse
    components = {}
    is_healthy = True
    
    try:
        await db.command("ping")
        components["mongodb"] = {"status": "up", "latency_ms": None}
    except Exception as e:
        components["mongodb"] = {"status": "down", "error": str(e)[:100]}
        is_healthy = False
        logger.error(f"[HEALTH] MongoDB down: {str(e)}")
    
    try:
        from services.task_queue import task_queue
        if task_queue.is_connected:
            redis_health = await task_queue.health_check()
            if redis_health.get("redis"):
                components["redis"] = {"status": "up", "version": redis_health.get("redis_version", "unknown")}
            else:
                components["redis"] = {"status": "down", "error": redis_health.get("error", "Unknown error")}
        else:
            components["redis"] = {"status": "not_configured", "message": "Task queue not connected"}
    except Exception as e:
        components["redis"] = {"status": "error", "error": str(e)[:100]}
    
    response_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "components": components,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if not is_healthy:
        return JSONResponse(status_code=503, content=response_data)
    return response_data

@app.get("/health/live")
async def liveness_probe():
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness_probe():
    from fastapi.responses import JSONResponse
    is_ready = True
    checks = {}
    try:
        await db.command("ping")
        checks["mongodb"] = "ready"
    except Exception:
        checks["mongodb"] = "not_ready"
        is_ready = False
    
    response = {"status": "ready" if is_ready else "not_ready", "checks": checks}
    if not is_ready:
        return JSONResponse(status_code=503, content=response)
    return response

@app.get("/health/detailed")
async def health_check_detailed():
    from services.task_queue import task_queue
    import psutil
    components = {}
    try:
        start = datetime.now(timezone.utc)
        result = await db.command("ping")
        latency = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        server_status = await db.command("serverStatus")
        components["mongodb"] = {
            "status": "healthy",
            "latency_ms": round(latency, 2),
            "connections": {
                "current": server_status.get("connections", {}).get("current", 0),
                "available": server_status.get("connections", {}).get("available", 0)
            },
            "version": server_status.get("version", "unknown")
        }
    except Exception as e:
        components["mongodb"] = {"status": "unhealthy", "error": str(e)[:200]}
    try:
        redis_health = await task_queue.health_check()
        components["redis"] = redis_health
    except Exception as e:
        components["redis"] = {"status": "error", "error": str(e)[:100]}
    try:
        process = psutil.Process()
        components["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {"used_mb": round(process.memory_info().rss / 1024 / 1024, 2), "percent": round(process.memory_percent(), 2)},
            "open_files": len(process.open_files()),
            "threads": process.num_threads()
        }
    except Exception:
        components["system"] = {"status": "unavailable"}
    components["app"] = {
        "sentry_enabled": bool(SENTRY_DSN),
        "environment": SENTRY_ENVIRONMENT if SENTRY_DSN else "unknown",
        "cors_origins": len(CORS_ORIGINS),
    }
    db_healthy = components.get("mongodb", {}).get("status") == "healthy"
    overall_status = "healthy" if db_healthy else "degraded"
    return {"status": overall_status, "components": components, "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/test/enqueue-email")
async def test_enqueue_email(to_email: str = "test@example.com"):
    from services.task_queue import task_queue
    job_id = await task_queue.send_email(to=to_email, subject="Teste de Task Queue", body="Este é um email de teste enviado via Task Queue.")
    return {"success": bool(job_id), "job_id": job_id, "message": "Email enfileirado" if job_id else "Task Queue não disponível"}

@app.get("/sentry-debug")
async def sentry_debug():
    logger.info("Sentry debug endpoint called - about to trigger error")
    sentry_sdk.set_context("debug_info", {"purpose": "Test Sentry integration", "timestamp": datetime.now(timezone.utc).isoformat()})
    sentry_sdk.set_tag("test_type", "manual_debug")
    division_by_zero = 1 / 0
    return {"this": "will never be reached"}

@app.get("/sentry-test-message")
async def sentry_test_message():
    sentry_sdk.capture_message("Test message from CreditoIMO", level="info")
    return {"success": True, "message": "Mensagem de teste enviada ao Sentry", "sentry_enabled": bool(SENTRY_DSN)}

app.add_middleware(
    CORSMiddleware,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_origins=CORS_ORIGINS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
    max_age=CORS_MAX_AGE,
)

@app.on_event("startup")
async def startup():
    logger.info("🚀 Iniciando aplicação CreditoIMO...")
    try:
        from services.task_queue import task_queue
        connected = await task_queue.connect()
        if connected:
            logger.info("✅ Task Queue (Redis) conectada")
        else:
            logger.warning("⚠️ Task Queue não disponível - tarefas executadas localmente")
    except Exception as e:
        logger.warning(f"⚠️ Task Queue não disponível: {str(e)}")
    
    # Database Indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.processes.create_index("id", unique=True)
    await db.processes.create_index("client_id")
    await db.deadlines.create_index("id", unique=True)
    await db.deadlines.create_index("process_id")
    await db.activities.create_index("process_id")
    await db.history.create_index("process_id")
    await db.workflow_statuses.create_index("name", unique=True)
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index("user_id")
    await db.notifications.create_index("process_id")
    await db.properties.create_index("id", unique=True)
    await db.properties.create_index("internal_reference", unique=True, sparse=True)
    await db.properties.create_index("status")
    await db.properties.create_index("address.district")
    await db.properties.create_index("financials.asking_price")
    await db.notifications.create_index("created_at")
    await db.notifications.create_index([("user_id", 1), ("read", 1)])
    await db.push_subscriptions.create_index("id", unique=True)
    await db.push_subscriptions.create_index("user_id")
    await db.push_subscriptions.create_index("endpoint", unique=True)
    await db.push_subscriptions.create_index([("user_id", 1), ("is_active", 1)])
    await db.tasks.create_index("id", unique=True)
    await db.tasks.create_index("process_id")
    await db.tasks.create_index("created_by")
    await db.tasks.create_index("assigned_to")
    await db.tasks.create_index([("completed", 1), ("created_at", -1)])
    await db.clients.create_index("id", unique=True)
    await db.clients.create_index("nome")
    await db.clients.create_index("contacto.email", sparse=True)
    await db.clients.create_index("dados_pessoais.nif", sparse=True)
    await db.clients.create_index("process_ids")
    await db.emails.create_index("id", unique=True)
    await db.emails.create_index("process_id")
    await db.emails.create_index([("process_id", 1), ("sent_at", -1)])
    await db.emails.create_index("direction")
    await db.gdpr_audit.create_index("timestamp")
    await db.gdpr_audit.create_index("action")
    await db.gdpr_audit.create_index([("action", 1), ("timestamp", -1)])
    await db.processes.create_index("is_anonymized", sparse=True)
    
    status_count = await db.workflow_statuses.count_documents({})
    if status_count == 0:
        default_statuses = [
            {"id": str(uuid.uuid4()), "name": "clientes_espera", "label": "Clientes em Espera", "order": 1, "color": "yellow", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "fase_documental", "label": "Fase Documental", "order": 2, "color": "blue", "is_default": True},
            {"id": str(uuid.uuid4()), "name": "entregue_intermediarios", "label": "Entregue aos Intermediários", "order": 3, "color": "indigo", "is_default": True},
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
    
    user_count = await db.users.count_documents({})
    if user_count == 0:
        logger.warning("Nenhum utilizador encontrado! Execute 'python seed.py' para criar utilizadores iniciais.")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()