"""
====================================================================
MINUTAS ROUTES - CREDITOIMO
====================================================================
Endpoints para gestao de minutas/templates de documentos.

Minutas sao templates de documentos que podem ser reutilizados.
Todos os utilizadores staff podem criar e usar minutas.

Endpoints:
- GET    /api/minutas              - Listar minutas
- POST   /api/minutas              - Criar minuta
- GET    /api/minutas/{id}         - Obter minuta
- PUT    /api/minutas/{id}         - Actualizar minuta
- DELETE /api/minutas/{id}         - Eliminar minuta
====================================================================
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import get_current_user, require_roles

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/minutas", tags=["Minutas"])


# ====================================================================
# MODELS
# ====================================================================
class MinutaCreate(BaseModel):
    """Dados para criar uma minuta."""
    titulo: str
    categoria: str = "contrato"
    descricao: Optional[str] = None
    conteudo: str
    tags: Optional[List[str]] = []


class MinutaUpdate(BaseModel):
    """Dados para actualizar uma minuta."""
    titulo: Optional[str] = None
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    conteudo: Optional[str] = None
    tags: Optional[List[str]] = None


# ====================================================================
# ENDPOINTS
# ====================================================================
@router.get("")
async def list_minutas(
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    search: Optional[str] = Query(None, description="Pesquisar por titulo ou tags"),
    limit: int = Query(100, le=500),
    skip: int = Query(0),
    user: dict = Depends(get_current_user)
):
    """
    Listar todas as minutas.
    
    Todos os utilizadores autenticados podem ver as minutas.
    """
    query = {}
    
    if categoria:
        query["categoria"] = categoria
    
    if search:
        query["$or"] = [
            {"titulo": {"$regex": search, "$options": "i"}},
            {"descricao": {"$regex": search, "$options": "i"}},
            {"tags": {"$in": [search]}}
        ]
    
    minutas = await db.minutas.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    total = await db.minutas.count_documents(query)
    
    return {
        "success": True,
        "total": total,
        "minutas": minutas
    }


@router.post("")
async def create_minuta(
    data: MinutaCreate,
    user: dict = Depends(get_current_user)
):
    """
    Criar uma nova minuta.
    
    Todos os utilizadores autenticados podem criar minutas.
    """
    minuta = {
        "id": str(uuid.uuid4()),
        "titulo": data.titulo.strip(),
        "categoria": data.categoria,
        "descricao": data.descricao.strip() if data.descricao else None,
        "conteudo": data.conteudo,
        "tags": [t.lower().strip() for t in (data.tags or []) if t.strip()],
        "created_by": user.get("id"),
        "created_by_name": user.get("name", user.get("email", "")).split("@")[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.minutas.insert_one(minuta)
    
    # Remover _id antes de retornar
    minuta.pop("_id", None)
    
    logger.info(f"Minuta criada: {minuta['titulo']} por {user.get('email')}")
    
    return {
        "success": True,
        "minuta": minuta
    }


@router.get("/{minuta_id}")
async def get_minuta(
    minuta_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter uma minuta especifica.
    """
    minuta = await db.minutas.find_one(
        {"id": minuta_id},
        {"_id": 0}
    )
    
    if not minuta:
        raise HTTPException(status_code=404, detail="Minuta nao encontrada")
    
    return {
        "success": True,
        "minuta": minuta
    }


@router.put("/{minuta_id}")
async def update_minuta(
    minuta_id: str,
    data: MinutaUpdate,
    user: dict = Depends(get_current_user)
):
    """
    Actualizar uma minuta.
    
    Apenas o criador ou admin pode editar.
    """
    minuta = await db.minutas.find_one({"id": minuta_id}, {"_id": 0})
    
    if not minuta:
        raise HTTPException(status_code=404, detail="Minuta nao encontrada")
    
    # Verificar permissoes
    is_owner = minuta.get("created_by") == user.get("id")
    is_admin = user.get("role") in ["admin", "ceo"]
    
    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Sem permissao para editar esta minuta"
        )
    
    # Preparar actualizacoes
    updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if data.titulo is not None:
        updates["titulo"] = data.titulo.strip()
    if data.categoria is not None:
        updates["categoria"] = data.categoria
    if data.descricao is not None:
        updates["descricao"] = data.descricao.strip() if data.descricao else None
    if data.conteudo is not None:
        updates["conteudo"] = data.conteudo
    if data.tags is not None:
        updates["tags"] = [t.lower().strip() for t in data.tags if t.strip()]
    
    await db.minutas.update_one(
        {"id": minuta_id},
        {"$set": updates}
    )
    
    # Retornar minuta actualizada
    updated = await db.minutas.find_one({"id": minuta_id}, {"_id": 0})
    
    logger.info(f"Minuta actualizada: {minuta_id} por {user.get('email')}")
    
    return {
        "success": True,
        "minuta": updated
    }


@router.delete("/{minuta_id}")
async def delete_minuta(
    minuta_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Eliminar uma minuta.
    
    Apenas o criador ou admin pode eliminar.
    """
    minuta = await db.minutas.find_one({"id": minuta_id}, {"_id": 0})
    
    if not minuta:
        raise HTTPException(status_code=404, detail="Minuta nao encontrada")
    
    # Verificar permissoes
    is_owner = minuta.get("created_by") == user.get("id")
    is_admin = user.get("role") in ["admin", "ceo"]
    
    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=403, 
            detail="Sem permissao para eliminar esta minuta"
        )
    
    await db.minutas.delete_one({"id": minuta_id})
    
    logger.info(f"Minuta eliminada: {minuta_id} por {user.get('email')}")
    
    return {
        "success": True,
        "message": "Minuta eliminada"
    }
