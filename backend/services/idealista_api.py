"""
Idealista Partner API Integration

Integração oficial com a API do Idealista para pesquisa de imóveis.
Requer credenciais de parceiro (IDEALISTA_API_KEY e IDEALISTA_API_SECRET).
"""

import os
import time
import base64
import logging
import httpx
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IdealistaProperty:
    """Representação de um imóvel do Idealista."""
    property_code: str
    title: str
    price: float
    price_by_area: Optional[float]
    operation: str  # sale/rent
    property_type: str
    typology: str
    size: float
    rooms: int
    bathrooms: int
    floor: Optional[str]
    exterior: bool
    has_parking: bool
    has_garden: bool
    has_terrace: bool
    has_pool: bool
    has_lift: bool
    address: str
    municipality: str
    province: str
    country: str
    latitude: float
    longitude: float
    url: str
    thumbnail: Optional[str]
    images: List[str]
    description: str
    features: List[str]
    agency_name: Optional[str]
    agency_phone: Optional[str]
    published_date: Optional[str]
    
    @classmethod
    def from_api_response(cls, data: dict) -> "IdealistaProperty":
        """Criar instância a partir da resposta da API."""
        return cls(
            property_code=data.get("propertyCode", ""),
            title=data.get("suggestedTexts", {}).get("title", data.get("address", "")),
            price=data.get("price", 0),
            price_by_area=data.get("priceByArea"),
            operation=data.get("operation", "sale"),
            property_type=data.get("propertyType", ""),
            typology=cls._extract_typology(data),
            size=data.get("size", 0),
            rooms=data.get("rooms", 0),
            bathrooms=data.get("bathrooms", 0),
            floor=data.get("floor"),
            exterior=data.get("exterior", False),
            has_parking=data.get("hasParkingSpace", False),
            has_garden=data.get("hasGarden", False),
            has_terrace=data.get("hasTerrace", False),
            has_pool=data.get("hasSwimmingPool", False),
            has_lift=data.get("hasLift", False),
            address=data.get("address", ""),
            municipality=data.get("municipality", ""),
            province=data.get("province", ""),
            country=data.get("country", "pt"),
            latitude=data.get("latitude", 0),
            longitude=data.get("longitude", 0),
            url=data.get("url", ""),
            thumbnail=data.get("thumbnail"),
            images=data.get("multimedia", {}).get("images", []),
            description=data.get("description", ""),
            features=data.get("features", []),
            agency_name=data.get("contactInfo", {}).get("name"),
            agency_phone=data.get("contactInfo", {}).get("phone"),
            published_date=data.get("propertyDate")
        )
    
    @staticmethod
    def _extract_typology(data: dict) -> str:
        """Extrair tipologia (T0, T1, T2, etc.)."""
        rooms = data.get("rooms", 0)
        if rooms == 0:
            return "T0"
        return f"T{rooms}"
    
    def to_dict(self) -> dict:
        """Converter para dicionário."""
        return {
            "property_code": self.property_code,
            "title": self.title,
            "price": self.price,
            "price_by_area": self.price_by_area,
            "operation": self.operation,
            "property_type": self.property_type,
            "typology": self.typology,
            "size": self.size,
            "rooms": self.rooms,
            "bathrooms": self.bathrooms,
            "floor": self.floor,
            "exterior": self.exterior,
            "has_parking": self.has_parking,
            "has_garden": self.has_garden,
            "has_terrace": self.has_terrace,
            "has_pool": self.has_pool,
            "has_lift": self.has_lift,
            "address": self.address,
            "municipality": self.municipality,
            "province": self.province,
            "country": self.country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "images": self.images,
            "description": self.description,
            "features": self.features,
            "agency_name": self.agency_name,
            "agency_phone": self.agency_phone,
            "published_date": self.published_date,
            "source": "idealista"
        }


class IdealistaAPI:
    """Cliente da API oficial do Idealista."""
    
    BASE_URL = "https://api.idealista.com"
    API_VERSION = "3.5"
    TOKEN_URL = f"{BASE_URL}/oauth/token"
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Inicializar cliente da API.
        
        Args:
            api_key: Chave da API (ou IDEALISTA_API_KEY do ambiente)
            api_secret: Secret da API (ou IDEALISTA_API_SECRET do ambiente)
        """
        self.api_key = api_key or os.environ.get("IDEALISTA_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("IDEALISTA_API_SECRET", "")
        self._token: Optional[str] = None
        self._token_expires: float = 0
        
        if not self.api_key or not self.api_secret:
            logger.warning("Credenciais do Idealista não configuradas")
    
    @property
    def is_configured(self) -> bool:
        """Verificar se as credenciais estão configuradas."""
        return bool(self.api_key and self.api_secret)
    
    def _get_auth_header(self) -> str:
        """Criar header de autorização base64."""
        credentials = f"{self.api_key}:{self.api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"
    
    async def _get_token(self) -> str:
        """Obter token OAuth2."""
        # Usar token em cache se ainda válido
        if self._token and self._token_expires > time.time():
            return self._token
        
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "read"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                headers=headers,
                data=data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Erro ao obter token Idealista: {response.status_code} - {response.text}")
                raise Exception(f"Falha na autenticação Idealista: {response.status_code}")
            
            token_data = response.json()
            self._token = token_data["access_token"]
            # Refrescar 1 minuto antes de expirar
            self._token_expires = time.time() + token_data.get("expires_in", 3600) - 60
            
            logger.info("Token Idealista obtido com sucesso")
            return self._token
    
    async def search_properties(
        self,
        country: str = "pt",
        operation: str = "sale",
        property_type: str = "homes",
        center: Optional[str] = None,
        distance: int = 10000,
        location_id: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_size: Optional[float] = None,
        max_size: Optional[float] = None,
        min_rooms: Optional[int] = None,
        max_rooms: Optional[int] = None,
        order: str = "publicationDate",
        sort: str = "desc",
        max_items: int = 50,
        num_page: int = 1
    ) -> Dict[str, Any]:
        """
        Pesquisar imóveis no Idealista.
        
        Args:
            country: Código do país (pt, es, it)
            operation: Tipo de operação (sale, rent)
            property_type: Tipo de imóvel (homes, offices, premises, garages)
            center: Centro da pesquisa (latitude,longitude)
            distance: Raio em metros
            location_id: ID da localização Idealista
            min_price: Preço mínimo
            max_price: Preço máximo
            min_size: Área mínima (m²)
            max_size: Área máxima (m²)
            min_rooms: Quartos mínimos
            max_rooms: Quartos máximos
            order: Ordenação (publicationDate, price, size)
            sort: Direção (asc, desc)
            max_items: Máximo de resultados por página
            num_page: Número da página
        
        Returns:
            Dicionário com resultados da pesquisa
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "API Idealista não configurada. Configure IDEALISTA_API_KEY e IDEALISTA_API_SECRET.",
                "properties": []
            }
        
        try:
            token = await self._get_token()
            
            search_url = f"{self.BASE_URL}/{self.API_VERSION}/{country}/search"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Construir parâmetros
            params = {
                "operation": operation,
                "propertyType": property_type,
                "order": order,
                "sort": sort,
                "maxItems": max_items,
                "numPage": num_page
            }
            
            if center:
                params["center"] = center
                params["distance"] = distance
            elif location_id:
                params["locationId"] = location_id
            
            if min_price:
                params["minPrice"] = min_price
            if max_price:
                params["maxPrice"] = max_price
            if min_size:
                params["minSize"] = min_size
            if max_size:
                params["maxSize"] = max_size
            if min_rooms:
                params["minRooms"] = min_rooms
            if max_rooms:
                params["maxRooms"] = max_rooms
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    search_url,
                    headers=headers,
                    data=params,
                    timeout=60
                )
                
                if response.status_code != 200:
                    logger.error(f"Erro na pesquisa Idealista: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": f"Erro na API Idealista: {response.status_code}",
                        "properties": []
                    }
                
                data = response.json()
                
                # Processar resultados
                properties = []
                for item in data.get("elementList", []):
                    try:
                        prop = IdealistaProperty.from_api_response(item)
                        properties.append(prop.to_dict())
                    except Exception as e:
                        logger.warning(f"Erro ao processar imóvel: {e}")
                
                return {
                    "success": True,
                    "total": data.get("total", len(properties)),
                    "total_pages": data.get("totalPages", 1),
                    "actual_page": data.get("actualPage", 1),
                    "items_per_page": data.get("itemsPerPage", max_items),
                    "properties": properties
                }
                
        except Exception as e:
            logger.error(f"Erro na pesquisa Idealista: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "properties": []
            }
    
    async def get_property_details(
        self,
        property_code: str,
        country: str = "pt"
    ) -> Dict[str, Any]:
        """
        Obter detalhes de um imóvel específico.
        
        Args:
            property_code: Código do imóvel
            country: Código do país
        
        Returns:
            Dicionário com detalhes do imóvel
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "API Idealista não configurada"
            }
        
        try:
            token = await self._get_token()
            
            details_url = f"{self.BASE_URL}/{self.API_VERSION}/{country}/property/{property_code}"
            
            headers = {
                "Authorization": f"Bearer {token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    details_url,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Imóvel não encontrado: {property_code}"
                    }
                
                data = response.json()
                prop = IdealistaProperty.from_api_response(data)
                
                return {
                    "success": True,
                    "property": prop.to_dict()
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter detalhes Idealista: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Instância global
idealista_api = IdealistaAPI()


async def search_idealista(
    location: str = "Lisboa",
    operation: str = "sale",
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rooms: Optional[int] = None,
    max_rooms: Optional[int] = None,
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Função de conveniência para pesquisar no Idealista.
    
    Args:
        location: Nome da localização (usa geocoding simplificado)
        operation: sale ou rent
        min_price: Preço mínimo
        max_price: Preço máximo
        min_rooms: Quartos mínimos
        max_rooms: Quartos máximos
        max_results: Máximo de resultados
    
    Returns:
        Dicionário com resultados
    """
    # Coordenadas aproximadas de cidades portuguesas
    CITY_COORDS = {
        "lisboa": "38.7223,-9.1393",
        "porto": "41.1579,-8.6291",
        "braga": "41.5454,-8.4265",
        "coimbra": "40.2033,-8.4103",
        "faro": "37.0194,-7.9322",
        "setubal": "38.5244,-8.8882",
        "aveiro": "40.6405,-8.6538",
        "leiria": "39.7437,-8.8070",
        "viseu": "40.6566,-7.9125",
        "evora": "38.5711,-7.9092"
    }
    
    # Procurar coordenadas
    location_lower = location.lower()
    center = None
    
    for city, coords in CITY_COORDS.items():
        if city in location_lower:
            center = coords
            break
    
    if not center:
        # Default: Lisboa
        center = CITY_COORDS["lisboa"]
    
    return await idealista_api.search_properties(
        country="pt",
        operation=operation,
        center=center,
        distance=15000,  # 15km
        min_price=min_price,
        max_price=max_price,
        min_rooms=min_rooms,
        max_rooms=max_rooms,
        max_items=max_results
    )
