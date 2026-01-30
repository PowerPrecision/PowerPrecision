"""
==============================================
TRELLO INTEGRATION SERVICE
==============================================
Sincronização bidirecional entre CreditoIMO e Trello.

Funcionalidades:
- Sincronização em tempo real via webhooks
- Mapeamento automático de listas/estados
- Criação/atualização/movimentação de cards
==============================================
"""

import os
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

# Trello API Configuration
TRELLO_API_KEY = os.environ.get("TRELLO_API_KEY", "")
TRELLO_TOKEN = os.environ.get("TRELLO_TOKEN", "")
TRELLO_BOARD_ID = os.environ.get("TRELLO_BOARD_ID", "")
TRELLO_BASE_URL = "https://api.trello.com/1"


class TrelloService:
    """Serviço de integração com o Trello."""
    
    def __init__(self, api_key: str = None, token: str = None, board_id: str = None):
        self.api_key = api_key or TRELLO_API_KEY
        self.token = token or TRELLO_TOKEN
        self.board_id = board_id or TRELLO_BOARD_ID
        self._lists_cache = {}
        self._lists_cache_time = None
    
    @property
    def auth_params(self) -> Dict[str, str]:
        return {"key": self.api_key, "token": self.token}
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Fazer pedido à API do Trello."""
        url = f"{TRELLO_BASE_URL}{endpoint}"
        params = kwargs.pop("params", {})
        params.update(self.auth_params)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, params=params, **kwargs)
            response.raise_for_status()
            return response.json() if response.text else None
    
    async def get_board(self) -> Dict:
        """Obter informações do board."""
        return await self._request("GET", f"/boards/{self.board_id}")
    
    async def get_lists(self, force_refresh: bool = False) -> List[Dict]:
        """Obter listas (colunas) do board com cache."""
        now = datetime.now()
        
        # Cache por 5 minutos
        if not force_refresh and self._lists_cache and self._lists_cache_time:
            if (now - self._lists_cache_time).seconds < 300:
                return list(self._lists_cache.values())
        
        lists = await self._request("GET", f"/boards/{self.board_id}/lists")
        self._lists_cache = {l["id"]: l for l in lists}
        self._lists_cache_time = now
        return lists
    
    async def get_list_by_name(self, name: str) -> Optional[Dict]:
        """Encontrar lista por nome (case-insensitive)."""
        lists = await self.get_lists()
        name_lower = name.lower().strip()
        for lst in lists:
            if lst["name"].lower().strip() == name_lower:
                return lst
        return None
    
    async def get_cards(self, list_id: str = None) -> List[Dict]:
        """Obter cards do board ou de uma lista específica."""
        if list_id:
            return await self._request("GET", f"/lists/{list_id}/cards")
        return await self._request("GET", f"/boards/{self.board_id}/cards")
    
    async def get_card(self, card_id: str) -> Dict:
        """Obter um card específico."""
        return await self._request("GET", f"/cards/{card_id}")
    
    async def create_card(self, list_id: str, name: str, desc: str = "", 
                          labels: List[str] = None, due: str = None) -> Dict:
        """Criar um novo card no Trello."""
        data = {
            "idList": list_id,
            "name": name,
            "desc": desc,
        }
        if labels:
            data["idLabels"] = ",".join(labels)
        if due:
            data["due"] = due
        
        return await self._request("POST", "/cards", json=data)
    
    async def update_card(self, card_id: str, **updates) -> Dict:
        """Atualizar um card existente."""
        return await self._request("PUT", f"/cards/{card_id}", json=updates)
    
    async def move_card(self, card_id: str, list_id: str) -> Dict:
        """Mover card para outra lista."""
        return await self._request("PUT", f"/cards/{card_id}", json={"idList": list_id})
    
    async def delete_card(self, card_id: str) -> None:
        """Eliminar um card."""
        await self._request("DELETE", f"/cards/{card_id}")
    
    async def archive_card(self, card_id: str) -> Dict:
        """Arquivar um card."""
        return await self._request("PUT", f"/cards/{card_id}", json={"closed": True})
    
    async def get_card_actions(self, card_id: str, filter: str = "commentCard") -> List[Dict]:
        """Obter atividades/comentários de um card."""
        return await self._request(
            "GET", 
            f"/cards/{card_id}/actions",
            params={"filter": filter}
        )
    
    async def get_card_full(self, card_id: str) -> Dict:
        """Obter card com todos os detalhes incluindo atividades."""
        card = await self.get_card(card_id)
        # Obter comentários
        comments = await self.get_card_actions(card_id, "commentCard")
        card["comments"] = comments
        # Obter todas as ações (criação, movimentos, etc.)
        all_actions = await self.get_card_actions(card_id, "all")
        card["actions"] = all_actions
        return card
    
    async def get_cards_with_details(self, list_id: str = None) -> List[Dict]:
        """Obter cards com todos os dados, labels, membros e atividades."""
        if list_id:
            cards = await self._request(
                "GET", 
                f"/lists/{list_id}/cards",
                params={"fields": "all", "members": "true"}
            )
        else:
            cards = await self._request(
                "GET", 
                f"/boards/{self.board_id}/cards",
                params={"fields": "all", "members": "true"}
            )
        
        # Obter comentários para cada card
        for card in cards:
            try:
                comments = await self.get_card_actions(card["id"], "commentCard")
                card["comments"] = comments
            except Exception:
                card["comments"] = []
        
        return cards
    
    # === Webhooks ===
    
    async def create_webhook(self, callback_url: str, id_model: str = None, 
                             description: str = "CreditoIMO Sync") -> Dict:
        """Criar webhook para receber notificações do Trello."""
        # Se não for fornecido, obter o ID real do board
        if not id_model:
            board = await self.get_board()
            id_model = board.get("id", self.board_id)
        
        data = {
            "callbackURL": callback_url,
            "idModel": id_model,
            "description": description,
        }
        return await self._request("POST", "/webhooks", json=data)
    
    async def get_webhooks(self) -> List[Dict]:
        """Listar webhooks ativos."""
        return await self._request("GET", f"/tokens/{self.token}/webhooks")
    
    async def delete_webhook(self, webhook_id: str) -> None:
        """Eliminar um webhook."""
        await self._request("DELETE", f"/webhooks/{webhook_id}")


# Mapeamento entre nomes de listas do Trello e estados do sistema
TRELLO_TO_STATUS = {
    "clientes em espera": "clientes_espera",
    "fase documental": "fase_documental",
    "fase documental ii": "fase_documental_ii",
    "entregue aos intermediarios": "entregue_intermediarios",
    "enviado ao bruno": "enviado_bruno",
    "enviado ao luís": "enviado_luis",
    "enviado bcp rui": "enviado_bcp_rui",
    "entradas precision": "entradas_precision",
    "fase bancária - pré aprovação": "fase_bancaria",
    "fase de visitas": "fase_visitas",
    "ch aprovado - avaliação": "ch_aprovado",
    "fase de escritura": "fase_escritura",
    "escritura agendada": "escritura_agendada",
    "concluidos": "concluidos",
    "desistências": "desistencias",
}

STATUS_TO_TRELLO = {v: k for k, v in TRELLO_TO_STATUS.items()}


def normalize_list_name(name: str) -> str:
    """Normalizar nome de lista para comparação."""
    return name.lower().strip()


def trello_list_to_status(list_name: str) -> Optional[str]:
    """Converter nome de lista Trello para status do sistema."""
    normalized = normalize_list_name(list_name)
    return TRELLO_TO_STATUS.get(normalized)


def status_to_trello_list(status: str) -> Optional[str]:
    """Converter status do sistema para nome de lista Trello."""
    return STATUS_TO_TRELLO.get(status)


def parse_card_description(desc: str) -> Dict[str, str]:
    """Extrair dados estruturados da descrição do card."""
    data = {}
    if not desc:
        return data
    
    lines = desc.strip().split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            data[key] = value.strip()
    
    return data


def build_card_description(process: Dict) -> str:
    """Construir descrição do card a partir dos dados do processo."""
    lines = []
    
    # Dados principais
    if process.get("client_email"):
        lines.append(f"📧 Email: {process['client_email']}")
    if process.get("client_phone"):
        lines.append(f"📱 Telefone: {process['client_phone']}")
    if process.get("client_nif"):
        lines.append(f"🆔 NIF: {process['client_nif']}")
    
    # Dados pessoais
    personal = process.get("personal_data", {})
    if personal.get("morada_fiscal"):
        lines.append(f"📍 Morada: {personal['morada_fiscal']}")
    if personal.get("data_nascimento"):
        lines.append(f"🎂 Nascimento: {personal['data_nascimento']}")
    
    # Dados financeiros
    financial = process.get("financial_data", {})
    if financial.get("rendimento_mensal"):
        lines.append(f"💰 Rendimento: €{financial['rendimento_mensal']:,.0f}/mês")
    if financial.get("valor_pretendido") or process.get("valor_pretendido"):
        valor = financial.get("valor_pretendido") or process.get("valor_pretendido")
        lines.append(f"🏦 Valor Pretendido: €{valor:,.0f}")
    
    # Dados do imóvel
    real_estate = process.get("real_estate_data", {})
    if real_estate.get("morada_imovel"):
        lines.append(f"🏠 Imóvel: {real_estate['morada_imovel']}")
    if real_estate.get("valor_aquisicao"):
        lines.append(f"💶 Valor Aquisição: €{real_estate['valor_aquisicao']:,.0f}")
    
    # Flags especiais
    if process.get("idade_menos_35"):
        lines.append("⭐ Elegível Apoio ao Estado (<35 anos)")
    if process.get("has_property"):
        lines.append("🏡 Tem imóvel identificado")
    
    # Atribuições
    if process.get("consultor_name"):
        lines.append(f"👤 Consultor: {process['consultor_name']}")
    if process.get("mediador_name"):
        lines.append(f"👤 Intermediário: {process['mediador_name']}")
    
    return "\n".join(lines)


# Instância global do serviço
trello_service = TrelloService()
