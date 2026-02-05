"""
OneDrive Routes - API endpoints para integração OneDrive
"""
import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from database import db
from services.auth import get_current_user, require_roles
from models.user import UserRole
from services.onedrive import onedrive_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onedrive", tags=["OneDrive Integration"])

# Frontend URL para redirecionamento
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://process-hub-25.preview.emergentagent.com")


@router.get("/status")
async def get_onedrive_status(user: dict = Depends(get_current_user)):
    """Verificar estado da integração OneDrive."""
    # Verificar se há tokens guardados para este utilizador
    stored_tokens = await db.onedrive_tokens.find_one(
        {"user_id": user["id"]},
        {"_id": 0}
    )
    
    return {
        "configured": onedrive_service.is_configured(),
        "authenticated": stored_tokens is not None and stored_tokens.get("access_token"),
        "base_folder": onedrive_service.base_folder,
        "user_email": stored_tokens.get("microsoft_email") if stored_tokens else None
    }


@router.get("/auth/login")
async def initiate_onedrive_login(user: dict = Depends(get_current_user)):
    """
    Iniciar fluxo de autenticação OAuth2 com Microsoft.
    Retorna URL para redirecionar o utilizador.
    """
    if not onedrive_service.is_configured():
        raise HTTPException(status_code=400, detail="OneDrive não está configurado")
    
    # Gerar state para prevenir CSRF
    state = secrets.token_urlsafe(32)
    
    # Guardar state na base de dados associado ao utilizador
    await db.onedrive_auth_states.update_one(
        {"user_id": user["id"]},
        {"$set": {
            "user_id": user["id"],
            "state": state,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    auth_url = onedrive_service.get_auth_url(state)
    
    return {"auth_url": auth_url}


@router.get("/callback")
async def onedrive_oauth_callback(
    code: str = Query(...),
    state: str = Query(...)
):
    """
    Callback do OAuth2 da Microsoft.
    Troca o código por tokens e guarda na base de dados.
    """
    # Verificar state
    auth_state = await db.onedrive_auth_states.find_one({"state": state})
    
    if not auth_state:
        logger.error(f"Invalid OAuth state: {state}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?error=invalid_state",
            status_code=302
        )
    
    user_id = auth_state["user_id"]
    
    # Apagar state usado
    await db.onedrive_auth_states.delete_one({"state": state})
    
    try:
        # Trocar código por tokens
        tokens = await onedrive_service.exchange_code_for_tokens(code)
        
        # Obter informação do utilizador Microsoft
        microsoft_user = await onedrive_service.get_user_info(tokens["access_token"])
        
        # Guardar tokens na base de dados
        await db.onedrive_tokens.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": (datetime.now(timezone.utc) + 
                              timedelta(seconds=tokens["expires_in"])).isoformat(),
                "microsoft_id": microsoft_user.get("id"),
                "microsoft_email": microsoft_user.get("mail") or microsoft_user.get("userPrincipalName"),
                "microsoft_name": microsoft_user.get("displayName"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        logger.info(f"OneDrive autenticado para utilizador {user_id}")
        
        # Redirecionar para o frontend com sucesso
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?onedrive=success",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"OneDrive OAuth callback failed: {e}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?error=auth_failed",
            status_code=302
        )


async def get_valid_access_token(user_id: str) -> Optional[str]:
    """
    Obter token de acesso válido para um utilizador.
    Renova automaticamente se expirado.
    """
    stored_tokens = await db.onedrive_tokens.find_one({"user_id": user_id}, {"_id": 0})
    
    if not stored_tokens or not stored_tokens.get("access_token"):
        return None
    
    # Verificar se token expirou
    expires_at = stored_tokens.get("expires_at")
    if expires_at:
        expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) >= expires_dt:
            # Token expirado, tentar renovar
            refresh_token = stored_tokens.get("refresh_token")
            if not refresh_token:
                return None
            
            try:
                new_tokens = await onedrive_service.refresh_access_token(refresh_token)
                
                # Actualizar tokens na base de dados
                await db.onedrive_tokens.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "access_token": new_tokens["access_token"],
                        "refresh_token": new_tokens["refresh_token"],
                        "expires_at": (datetime.now(timezone.utc) + 
                                      timedelta(seconds=new_tokens["expires_in"])).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
                return new_tokens["access_token"]
                
            except Exception as e:
                logger.error(f"Falha ao renovar token OneDrive: {e}")
                return None
    
    return stored_tokens["access_token"]


@router.get("/folders")
async def list_onedrive_folders(
    path: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Listar pastas no OneDrive."""
    access_token = await get_valid_access_token(user["id"])
    
    if not access_token:
        raise HTTPException(status_code=401, detail="OneDrive não autenticado. Por favor, faça login primeiro.")
    
    try:
        folders = await onedrive_service.list_folders_in_path(access_token, path)
        return {"folders": folders, "base_folder": onedrive_service.base_folder}
    except Exception as e:
        logger.error(f"Erro ao listar pastas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/find-client-folder")
async def find_client_folder(
    client_name: str = Query(..., description="Nome do cliente"),
    threshold: int = Query(70, description="Limiar de correspondência (0-100)"),
    user: dict = Depends(get_current_user)
):
    """
    Encontrar pasta do cliente usando fuzzy matching.
    Procura na pasta base configurada.
    """
    access_token = await get_valid_access_token(user["id"])
    
    if not access_token:
        raise HTTPException(status_code=401, detail="OneDrive não autenticado")
    
    try:
        folder = await onedrive_service.find_client_folder(
            access_token, 
            client_name,
            threshold
        )
        
        if not folder:
            raise HTTPException(
                status_code=404, 
                detail=f"Nenhuma pasta encontrada para '{client_name}'"
            )
        
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao procurar pasta do cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folder/{folder_id}/files")
async def list_folder_files(
    folder_id: str,
    user: dict = Depends(get_current_user)
):
    """Listar ficheiros dentro de uma pasta."""
    access_token = await get_valid_access_token(user["id"])
    
    if not access_token:
        raise HTTPException(status_code=401, detail="OneDrive não autenticado")
    
    try:
        files = await onedrive_service.list_files_in_folder(access_token, folder_id)
        return {"files": files}
    except Exception as e:
        logger.error(f"Erro ao listar ficheiros: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{file_id}/download-url")
async def get_file_download_url(
    file_id: str,
    user: dict = Depends(get_current_user)
):
    """Obter URL de download pré-autenticado para um ficheiro."""
    access_token = await get_valid_access_token(user["id"])
    
    if not access_token:
        raise HTTPException(status_code=401, detail="OneDrive não autenticado")
    
    try:
        download_url = await onedrive_service.get_file_download_url(access_token, file_id)
        
        if not download_url:
            raise HTTPException(status_code=404, detail="URL de download não encontrado")
        
        return {"download_url": download_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter URL de download: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/process/{process_id}/documents")
async def get_process_documents(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter documentos do OneDrive para um processo específico.
    Procura automaticamente pela pasta do cliente.
    """
    access_token = await get_valid_access_token(user["id"])
    
    if not access_token:
        raise HTTPException(status_code=401, detail="OneDrive não autenticado")
    
    # Obter processo
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    client_name = process.get("client_name")
    
    if not client_name:
        raise HTTPException(status_code=400, detail="Processo não tem nome do cliente")
    
    try:
        # Procurar pasta do cliente
        folder = await onedrive_service.find_client_folder(access_token, client_name)
        
        if not folder:
            return {
                "found": False,
                "client_name": client_name,
                "message": f"Pasta não encontrada para '{client_name}'"
            }
        
        # Listar ficheiros na pasta
        files = await onedrive_service.list_files_in_folder(access_token, folder["id"])
        
        return {
            "found": True,
            "client_name": client_name,
            "folder": folder,
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter documentos do processo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/auth/logout")
async def logout_onedrive(user: dict = Depends(get_current_user)):
    """Remover autenticação OneDrive do utilizador."""
    await db.onedrive_tokens.delete_one({"user_id": user["id"]})
    return {"success": True, "message": "OneDrive desconectado"}
