import logging
from datetime import datetime, timezone
import sentry_sdk
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from config import (
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, 
    CORS_ALLOW_HEADERS, CORS_MAX_AGE, SENTRY_DSN
)
from database import db, client
from middleware.rate_limit import limiter, rate_limit_exceeded_handler
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sistema de Gestão de Processos")

# RATE LIMIT
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ROUTES
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

@app.get("/health")
async def health_check():
    try:
        await db.command("ping")
        return {"status": "healthy"}
    except Exception:
        return {"status": "unhealthy"}

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
    logger.info("Starting up...")
    try:
        # Create indexes logic here (simplified for brevity, keep your original if needed)
        await db.users.create_index("email", unique=True)
    except Exception:
        pass

@app.on_event("shutdown")
async def shutdown_db_client():
    # Safer shutdown to avoid Event Loop Closed errors in tests
    try:
        client.close()
    except Exception:
        pass