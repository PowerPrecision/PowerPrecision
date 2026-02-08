"""
OneDrive Routes - Acesso via link partilhado
Como a API Graph requer autenticação mesmo para links públicos de contas empresariais,
esta implementação fornece URLs diretos para o OneDrive web.
"""
import os
import logging
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException

from database import db
from services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/onedrive", tags=["OneDrive"])

# Configurações
ONEDRIVE_SHARED_LINK = os.environ.get('ONEDRIVE_SHARED_LINK', '')
ONEDRIVE_WEB_URL = os.environ.get('ONEDRIVE_WEB_URL', '')


@router.get("/status")
async def get_onedrive_status(user: dict = Depends(get_current_user)):
    """Verificar estado da integração OneDrive."""
    return {
        "configured": bool(ONEDRIVE_SHARED_LINK),
        "method": "direct_link",
        "shared_link": ONEDRIVE_SHARED_LINK,
        "web_url": ONEDRIVE_WEB_URL
    }


@router.get("/process/{process_id}/folder-url")
async def get_process_folder_url(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter URL para abrir a pasta do cliente no OneDrive.
    Retorna o link da pasta principal com sugestão de pesquisa.
    """
    if not ONEDRIVE_SHARED_LINK:
        raise HTTPException(status_code=400, detail="OneDrive não configurado")
    
    # Obter processo
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    client_name = process.get("client_name", "")
    
    # Verificar se o processo tem um link de pasta guardado
    saved_folder_url = process.get("onedrive_folder_url")
    
    if saved_folder_url:
        return {
            "url": saved_folder_url,
            "client_name": client_name,
            "type": "saved",
            "message": "Link guardado no processo"
        }
    
    # Retornar link da pasta principal
    # O utilizador pode navegar manualmente para encontrar a pasta do cliente
    return {
        "url": ONEDRIVE_SHARED_LINK,
        "web_url": ONEDRIVE_WEB_URL,
        "client_name": client_name,
        "type": "main_folder",
        "message": f"Abrir pasta principal e procurar por '{client_name}'"
    }


@router.put("/process/{process_id}/folder-url")
async def save_process_folder_url(
    process_id: str,
    folder_url: str,
    user: dict = Depends(get_current_user)
):
    """
    Guardar o link da pasta do cliente no processo.
    Permite ao utilizador guardar o link específico da pasta após encontrá-la.
    """
    # Verificar se processo existe
    process = await db.processes.find_one({"id": process_id})
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Validar URL (deve ser do OneDrive)
    if not folder_url.startswith(("https://1drv.ms/", "https://onedrive.live.com/", "https://onedrive.sharepoint.com/")):
        raise HTTPException(status_code=400, detail="URL inválido. Deve ser um link do OneDrive.")
    
    # Guardar no processo
    await db.processes.update_one(
        {"id": process_id},
        {"$set": {"onedrive_folder_url": folder_url}}
    )
    
    return {
        "success": True,
        "message": "Link da pasta guardado com sucesso"
    }


@router.delete("/process/{process_id}/folder-url")
async def remove_process_folder_url(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """Remover o link da pasta do processo."""
    result = await db.processes.update_one(
        {"id": process_id},
        {"$unset": {"onedrive_folder_url": ""}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Processo não encontrado ou link já removido")
    
    return {"success": True, "message": "Link removido"}


@router.post("/process/{process_id}/checklist")
async def generate_document_checklist(
    process_id: str,
    files: list[str],  # Lista de nomes de ficheiros da pasta
    user: dict = Depends(get_current_user)
):
    """
    Gerar checklist de documentos baseada nos ficheiros fornecidos.
    
    O frontend envia a lista de ficheiros que estão na pasta do cliente
    (obtidos via interface do OneDrive ou upload manual).
    
    Returns:
        Checklist com status de cada documento esperado.
    """
    from services.document_checklist import generate_checklist
    
    # Obter processo
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Determinar tipo de processo (por agora, todos são crédito habitação)
    tipo_processo = "credito_habitacao"
    
    # Gerar checklist
    result = generate_checklist(files, tipo_processo)
    result["client_name"] = process.get("client_name", "")
    result["process_id"] = process_id
    
    # Guardar resultado no processo
    await db.processes.update_one(
        {"id": process_id},
        {"$set": {"document_checklist": result}}
    )
    
    return result


@router.get("/process/{process_id}/checklist")
async def get_document_checklist(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter checklist de documentos guardada para um processo.
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"document_checklist": 1, "client_name": 1, "_id": 0}
    )
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    checklist = process.get("document_checklist")
    
    if not checklist:
        return {
            "checklist": [],
            "resumo": {
                "total_documentos": 0,
                "percentagem_conclusao": 0,
            },
            "message": "Checklist ainda não gerada. Envie a lista de ficheiros para gerar."
        }
    
    return checklist

