"""
OneDrive Links Management - Simple link storage for OneDrive shared folders
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import get_current_user, require_staff


router = APIRouter(prefix="/onedrive", tags=["OneDrive Links"])


class OneDriveLinkCreate(BaseModel):
    name: str  # e.g., "Documentos Pessoais", "Comprovativos de Rendimento"
    url: str   # OneDrive sharing link
    description: Optional[str] = None


class OneDriveLinkResponse(BaseModel):
    id: str
    name: str
    url: str
    description: Optional[str] = None
    added_by: str
    added_at: str


@router.get("/status")
async def get_onedrive_status():
    """Check OneDrive configuration status"""
    return {
        "configured": True,
        "mode": "manual_links",
        "description": "Links de partilha do OneDrive são geridos manualmente por processo"
    }


@router.get("/links/{process_id}", response_model=List[OneDriveLinkResponse])
async def get_process_links(process_id: str, user: dict = Depends(require_staff())):
    """Get all OneDrive links for a process"""
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    links = process.get("onedrive_links", [])
    return [OneDriveLinkResponse(**link) for link in links]


@router.post("/links/{process_id}", response_model=OneDriveLinkResponse)
async def add_process_link(
    process_id: str, 
    data: OneDriveLinkCreate, 
    user: dict = Depends(require_staff())
):
    """Add a new OneDrive link to a process"""
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Validate URL (basic check)
    if not data.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL deve começar com https://")
    
    import uuid
    link_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    new_link = {
        "id": link_id,
        "name": data.name,
        "url": data.url,
        "description": data.description,
        "added_by": user["name"],
        "added_at": now
    }
    
    # Add to process
    await db.processes.update_one(
        {"id": process_id},
        {"$push": {"onedrive_links": new_link}}
    )
    
    return OneDriveLinkResponse(**new_link)


@router.delete("/links/{process_id}/{link_id}")
async def delete_process_link(
    process_id: str, 
    link_id: str, 
    user: dict = Depends(require_staff())
):
    """Delete a OneDrive link from a process"""
    result = await db.processes.update_one(
        {"id": process_id},
        {"$pull": {"onedrive_links": {"id": link_id}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Link não encontrado")
    
    return {"message": "Link eliminado com sucesso"}


@router.get("/all-links")
async def get_all_links(user: dict = Depends(require_staff())):
    """Get all OneDrive links across all processes (for admin/ceo)"""
    if user["role"] not in [UserRole.ADMIN, UserRole.CEO]:
        raise HTTPException(status_code=403, detail="Apenas admin/CEO podem ver todos os links")
    
    processes = await db.processes.find(
        {"onedrive_links": {"$exists": True, "$ne": []}},
        {"_id": 0, "id": 1, "client_name": 1, "onedrive_links": 1}
    ).to_list(1000)
    
    result = []
    for p in processes:
        for link in p.get("onedrive_links", []):
            result.append({
                "process_id": p["id"],
                "client_name": p["client_name"],
                **link
            })
    
    return result
