"""
Rotas para Match Cliente-Imóvel
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends

from services.auth import get_current_user
from services.client_match import (
    find_matching_leads_for_client,
    find_matching_clients_for_lead,
    get_match_summary_for_client
)

router = APIRouter(prefix="/match", tags=["Client-Property Match"])
logger = logging.getLogger(__name__)


@router.get("/client/{process_id}/leads")
async def get_matching_leads(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Encontrar leads de imóveis compatíveis com o perfil do cliente.
    """
    matches = await find_matching_leads_for_client(process_id)
    
    return {
        "process_id": process_id,
        "total_matches": len(matches),
        "matches": matches,
    }


@router.get("/lead/{lead_id}/clients")
async def get_matching_clients(
    lead_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Encontrar clientes que podem ter interesse num imóvel específico.
    """
    matches = await find_matching_clients_for_lead(lead_id)
    
    return {
        "lead_id": lead_id,
        "total_matches": len(matches),
        "matches": matches,
    }


@router.get("/client/{process_id}/summary")
async def get_client_match_summary(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter resumo de correspondências para um cliente.
    """
    summary = await get_match_summary_for_client(process_id)
    summary["process_id"] = process_id
    
    return summary
