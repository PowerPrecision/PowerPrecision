"""
====================================================================
RATE LIMITING MIDDLEWARE - ENTERPRISE SECURITY
====================================================================
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

def _get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return get_remote_address(request)

# Instância ÚNICA partilhada
limiter = Limiter(key_func=_get_client_ip)

async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    client_ip = _get_client_ip(request)
    logger.warning(f"Rate limit excedido para IP {client_ip}: {request.url.path}")
    return JSONResponse(
        status_code=429,
        content={"error": f"Rate limit exceeded: {exc.detail}"}
    )