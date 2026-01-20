import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException

from config import ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET, ONEDRIVE_BASE_PATH
from models.auth import UserRole
from models.onedrive import OneDriveFile
from services.auth import get_current_user, require_roles
from services.onedrive import onedrive_service


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onedrive", tags=["OneDrive"])


@router.get("/files", response_model=List[OneDriveFile])
async def list_onedrive_files(
    folder: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List files from OneDrive for the current user"""
    if user["role"] == UserRole.CLIENTE:
        user_folder = user.get("onedrive_folder", user["name"])
        folder_path = f"{ONEDRIVE_BASE_PATH}/{user_folder}"
        if folder:
            folder_path = f"{folder_path}/{folder}"
    else:
        if folder:
            folder_path = f"{ONEDRIVE_BASE_PATH}/{folder}"
        else:
            folder_path = ONEDRIVE_BASE_PATH
    
    try:
        files = await onedrive_service.list_files(folder_path)
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OneDrive error: {e}")
        raise HTTPException(status_code=503, detail="Erro ao aceder ao OneDrive")


@router.get("/files/{client_name}", response_model=List[OneDriveFile])
async def list_client_onedrive_files(
    client_name: str,
    subfolder: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """List files from a specific client's OneDrive folder"""
    if user["role"] == UserRole.CLIENTE:
        user_folder = user.get("onedrive_folder", user["name"])
        if client_name != user_folder:
            raise HTTPException(status_code=403, detail="Acesso negado")
    
    folder_path = f"{ONEDRIVE_BASE_PATH}/{client_name}"
    if subfolder:
        folder_path = f"{folder_path}/{subfolder}"
    
    try:
        files = await onedrive_service.list_files(folder_path)
        return files
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OneDrive error: {e}")
        raise HTTPException(status_code=503, detail="Erro ao aceder ao OneDrive")


@router.get("/download/{item_id}")
async def get_onedrive_download_url(item_id: str, user: dict = Depends(get_current_user)):
    """Get download URL for a OneDrive file"""
    try:
        download_url = await onedrive_service.get_download_url(item_id)
        return {"download_url": download_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OneDrive download error: {e}")
        raise HTTPException(status_code=503, detail="Erro ao obter link de download")


@router.get("/status")
async def get_onedrive_status(user: dict = Depends(require_roles([UserRole.ADMIN]))):
    """Check OneDrive integration status"""
    configured = all([ONEDRIVE_TENANT_ID, ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET])
    return {
        "configured": configured,
        "tenant_id": ONEDRIVE_TENANT_ID[:8] + "..." if ONEDRIVE_TENANT_ID else None,
        "client_id": ONEDRIVE_CLIENT_ID[:8] + "..." if ONEDRIVE_CLIENT_ID else None,
        "base_path": ONEDRIVE_BASE_PATH
    }
