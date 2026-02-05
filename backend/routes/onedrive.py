"""
OneDrive Shared Routes - Acesso via link partilhado
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from database import db
from services.auth import get_current_user
from services.onedrive_shared import onedrive_shared_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onedrive", tags=["OneDrive"])


@router.get("/status")
async def get_onedrive_status(user: dict = Depends(get_current_user)):
    """Verificar estado da integração OneDrive."""
    return {
        "configured": onedrive_shared_service.is_configured(),
        "method": "shared_link",
        "authenticated": True  # Não precisa de auth com link partilhado
    }


@router.get("/folders")
async def list_client_folders(
    refresh: bool = Query(False, description="Forçar refresh do cache"),
    user: dict = Depends(get_current_user)
):
    """Listar todas as pastas de clientes."""
    if not onedrive_shared_service.is_configured():
        raise HTTPException(status_code=400, detail="OneDrive não configurado")
    
    try:
        folders = await onedrive_shared_service.list_client_folders(force_refresh=refresh)
        return {
            "folders": folders,
            "count": len(folders)
        }
    except Exception as e:
        logger.error(f"Erro ao listar pastas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/find-folder")
async def find_client_folder(
    client_name: str = Query(..., description="Nome do cliente"),
    threshold: int = Query(65, description="Limiar de correspondência (0-100)"),
    user: dict = Depends(get_current_user)
):
    """Encontrar pasta do cliente por nome."""
    if not onedrive_shared_service.is_configured():
        raise HTTPException(status_code=400, detail="OneDrive não configurado")
    
    try:
        folder = await onedrive_shared_service.find_client_folder(client_name, threshold)
        
        if not folder:
            return {
                "found": False,
                "client_name": client_name,
                "message": f"Pasta não encontrada para '{client_name}'"
            }
        
        return {
            "found": True,
            **folder
        }
    except Exception as e:
        logger.error(f"Erro ao procurar pasta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder/{folder_id}/files")
async def list_folder_files(
    folder_id: str,
    user: dict = Depends(get_current_user)
):
    """Listar ficheiros de uma pasta."""
    if not onedrive_shared_service.is_configured():
        raise HTTPException(status_code=400, detail="OneDrive não configurado")
    
    try:
        files = await onedrive_shared_service.list_folder_files(folder_id)
        return {
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        logger.error(f"Erro ao listar ficheiros: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/process/{process_id}/documents")
async def get_process_documents(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter documentos do OneDrive para um processo.
    Procura automaticamente a pasta pelo nome do cliente.
    """
    if not onedrive_shared_service.is_configured():
        raise HTTPException(status_code=400, detail="OneDrive não configurado")
    
    # Obter processo
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    client_name = process.get("client_name")
    
    if not client_name:
        raise HTTPException(status_code=400, detail="Processo sem nome de cliente")
    
    try:
        # Procurar pasta do cliente
        folder = await onedrive_shared_service.find_client_folder(client_name)
        
        if not folder:
            return {
                "found": False,
                "client_name": client_name,
                "message": f"Pasta não encontrada para '{client_name}'",
                "files": []
            }
        
        # Listar ficheiros
        files = await onedrive_shared_service.list_folder_files(folder["id"])
        
        # Obter URL web da pasta
        web_url = await onedrive_shared_service.get_folder_web_url(folder["id"])
        
        return {
            "found": True,
            "client_name": client_name,
            "folder": {
                **folder,
                "web_url": web_url or folder.get("web_url")
            },
            "files": files,
            "count": len(files)
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter documentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
