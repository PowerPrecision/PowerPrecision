"""
Serviço para Match Cliente-Imóvel
Encontra correspondências entre clientes e imóveis (leads) baseado em perfil
"""
import logging
from typing import List, Dict, Any, Optional
from database import db

logger = logging.getLogger(__name__)


async def find_matching_leads_for_client(process_id: str) -> List[Dict[str, Any]]:
    """
    Encontra leads de imóveis que correspondem ao perfil do cliente.
    
    Critérios de match:
    - Preço dentro do orçamento (valor financiamento ou valor pretendido)
    - Localização (se especificada)
    - Tipologia (se especificada)
    
    Returns:
        Lista de leads compatíveis ordenados por relevância
    """
    # Obter dados do processo/cliente
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0}
    )
    
    if not process:
        return []
    
    # Extrair critérios do cliente
    financial = process.get("financial_data", {})
    real_estate = process.get("real_estate_data", {})
    
    max_price = None
    if financial.get("valor_pretendido"):
        try:
            max_price = float(str(financial["valor_pretendido"]).replace("€", "").replace(" ", "").replace(",", "."))
        except:
            pass
    if not max_price and real_estate.get("valor_imovel"):
        try:
            max_price = float(str(real_estate["valor_imovel"]).replace("€", "").replace(" ", "").replace(",", "."))
        except:
            pass
    
    desired_location = real_estate.get("localizacao", "").lower() if real_estate.get("localizacao") else None
    desired_typology = real_estate.get("tipologia", "").upper() if real_estate.get("tipologia") else None
    
    # Construir query para leads
    query = {
        "status": {"$in": ["novo", "contactado", "visita_agendada"]},  # Leads disponíveis
    }
    
    # Buscar todos os leads activos
    leads = await db.property_leads.find(query, {"_id": 0}).to_list(length=100)
    
    # Calcular score de match para cada lead
    matches = []
    for lead in leads:
        score = 0
        match_reasons = []
        
        lead_price = lead.get("price")
        lead_location = (lead.get("location") or "").lower()
        lead_typology = (lead.get("typology") or "").upper()
        
        # Match por preço (se o cliente tem orçamento definido)
        if max_price and lead_price:
            if lead_price <= max_price:
                score += 40
                match_reasons.append(f"Preço dentro do orçamento (€{lead_price:,.0f} ≤ €{max_price:,.0f})")
            elif lead_price <= max_price * 1.1:  # 10% acima
                score += 20
                match_reasons.append(f"Preço ligeiramente acima (+{((lead_price/max_price)-1)*100:.0f}%)")
        elif lead_price:
            score += 10  # Bonus pequeno se tem preço
        
        # Match por localização
        if desired_location and lead_location:
            # Verificar se há correspondência parcial
            if desired_location in lead_location or lead_location in desired_location:
                score += 35
                match_reasons.append(f"Localização compatível ({lead.get('location')})")
            else:
                # Verificar palavras comuns
                desired_words = set(desired_location.split())
                lead_words = set(lead_location.split())
                common = desired_words & lead_words
                if common:
                    score += 15
                    match_reasons.append(f"Zona próxima ({', '.join(common)})")
        
        # Match por tipologia
        if desired_typology and lead_typology:
            if desired_typology == lead_typology:
                score += 25
                match_reasons.append(f"Tipologia exacta ({lead_typology})")
            else:
                # Verificar tipologias próximas
                try:
                    desired_num = int(desired_typology.replace("T", "").replace("+", ""))
                    lead_num = int(lead_typology.replace("T", "").replace("+", ""))
                    if abs(desired_num - lead_num) == 1:
                        score += 10
                        match_reasons.append(f"Tipologia próxima ({lead_typology})")
                except:
                    pass
        
        if score > 0:
            matches.append({
                "lead": lead,
                "score": score,
                "match_reasons": match_reasons,
            })
    
    # Ordenar por score (maior primeiro)
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    return matches[:10]  # Top 10 matches


async def find_matching_clients_for_lead(lead_id: str) -> List[Dict[str, Any]]:
    """
    Encontra clientes que podem ter interesse num imóvel específico.
    
    Returns:
        Lista de clientes compatíveis ordenados por relevância
    """
    # Obter dados do lead
    lead = await db.property_leads.find_one(
        {"id": lead_id},
        {"_id": 0}
    )
    
    if not lead:
        return []
    
    lead_price = lead.get("price")
    lead_location = (lead.get("location") or "").lower()
    lead_typology = (lead.get("typology") or "").upper()
    lead_area = lead.get("area")
    
    # Buscar processos activos
    processes = await db.processes.find(
        {"status": {"$nin": ["escriturado", "recusado", "desistiu"]}},
        {"_id": 0, "id": 1, "client_name": 1, "status": 1, "financial_data": 1, "real_estate_data": 1}
    ).to_list(length=200)
    
    matches = []
    for process in processes:
        score = 0
        match_reasons = []
        
        financial = process.get("financial_data", {})
        real_estate = process.get("real_estate_data", {})
        
        # Obter orçamento do cliente
        client_budget = None
        if financial.get("valor_pretendido"):
            try:
                client_budget = float(str(financial["valor_pretendido"]).replace("€", "").replace(" ", "").replace(",", "."))
            except:
                pass
        if not client_budget and real_estate.get("valor_imovel"):
            try:
                client_budget = float(str(real_estate["valor_imovel"]).replace("€", "").replace(" ", "").replace(",", "."))
            except:
                pass
        
        client_location = (real_estate.get("localizacao") or "").lower()
        client_typology = (real_estate.get("tipologia") or "").upper()
        
        # Match por preço
        if lead_price and client_budget:
            if lead_price <= client_budget:
                score += 40
                match_reasons.append(f"Dentro do orçamento")
            elif lead_price <= client_budget * 1.15:
                score += 15
                match_reasons.append(f"Ligeiramente acima do orçamento")
        
        # Match por localização
        if lead_location and client_location:
            if client_location in lead_location or lead_location in client_location:
                score += 35
                match_reasons.append(f"Localização desejada")
        
        # Match por tipologia
        if lead_typology and client_typology:
            if lead_typology == client_typology:
                score += 25
                match_reasons.append(f"Tipologia exacta")
        
        if score > 0:
            matches.append({
                "process": {
                    "id": process["id"],
                    "client_name": process.get("client_name"),
                    "status": process.get("status"),
                },
                "score": score,
                "match_reasons": match_reasons,
            })
    
    matches.sort(key=lambda x: x["score"], reverse=True)
    
    return matches[:10]


async def get_match_summary_for_client(process_id: str) -> Dict[str, Any]:
    """
    Obter resumo de matches para um cliente.
    """
    matches = await find_matching_leads_for_client(process_id)
    
    return {
        "total_matches": len(matches),
        "top_matches": matches[:5],
        "has_perfect_match": any(m["score"] >= 80 for m in matches),
    }
