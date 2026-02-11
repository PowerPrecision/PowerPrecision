"""
Rotas para Web Scraping de Imóveis
==================================
Endpoints para extrair dados de portais imobiliários.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from services.auth import get_current_user, require_roles, UserRole
from services.scraper import scrape_property_url, crawl_properties

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scraper", tags=["Scraper"])


class ScrapeRequest(BaseModel):
    """Request para scraping de uma única URL."""
    url: str


class CrawlRequest(BaseModel):
    """Request para crawling recursivo."""
    url: str
    max_pages: int = 10
    max_depth: int = 2


class ScrapeResponse(BaseModel):
    """Response do scraping."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/single", response_model=ScrapeResponse)
async def scrape_single_url(
    request: ScrapeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Extrai dados de uma única URL de imóvel.
    
    Suporta: Idealista, Imovirtual, Casa Sapo, SuperCasa, ERA, Remax, KW, etc.
    """
    try:
        logger.info(f"Scraping URL: {request.url} (user: {user.get('email')})")
        
        result = await scrape_property_url(request.url)
        
        if result.get("error"):
            return ScrapeResponse(
                success=False,
                error=result.get("error"),
                data=result
            )
        
        return ScrapeResponse(
            success=True,
            data=result
        )
        
    except Exception as e:
        logger.error(f"Erro no scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl")
async def crawl_website(
    request: CrawlRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.DIRETOR, UserRole.CONSULTOR]))
):
    """
    Crawler recursivo para extrair múltiplos imóveis de um site.
    
    Navega pelo site a partir da URL inicial, seguindo links de imóveis
    até atingir o limite de páginas ou profundidade.
    
    Args:
        url: URL inicial (ex: página de listagem de imóveis)
        max_pages: Número máximo de páginas a visitar (default: 10, max: 50)
        max_depth: Profundidade máxima de navegação (default: 2, max: 3)
        
    Returns:
        Lista de imóveis encontrados com seus dados extraídos
    """
    # Limitar parâmetros para evitar abusos
    max_pages = min(request.max_pages, 50)
    max_depth = min(request.max_depth, 3)
    
    try:
        logger.info(
            f"Iniciando crawl: {request.url} "
            f"(max_pages={max_pages}, max_depth={max_depth}, user={user.get('email')})"
        )
        
        result = await crawl_properties(
            start_url=request.url,
            max_pages=max_pages,
            max_depth=max_depth
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Erro no crawling: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-sites")
async def get_supported_sites(user: dict = Depends(get_current_user)):
    """
    Lista os sites imobiliários suportados pelo scraper.
    """
    return {
        "supported_sites": [
            {
                "name": "Idealista",
                "domain": "idealista.pt",
                "quality": "alta",
                "notes": "Pode necessitar de múltiplas tentativas"
            },
            {
                "name": "Imovirtual",
                "domain": "imovirtual.com",
                "quality": "alta",
                "notes": None
            },
            {
                "name": "Casa Sapo",
                "domain": "casa.sapo.pt",
                "quality": "média",
                "notes": None
            },
            {
                "name": "SuperCasa",
                "domain": "supercasa.pt",
                "quality": "média",
                "notes": None
            },
            {
                "name": "ERA",
                "domain": "era.pt",
                "quality": "alta",
                "notes": None
            },
            {
                "name": "Remax",
                "domain": "remax.pt",
                "quality": "média",
                "notes": None
            },
            {
                "name": "Keller Williams",
                "domain": "kwportugal.pt",
                "quality": "média",
                "notes": None
            }
        ],
        "generic_support": True,
        "ai_analysis": {
            "available": True,
            "model": "gemini-1.5-flash (configurable)",
            "description": "Análise IA disponível para sites não suportados (Gemini por defeito)"
        },
        "notes": "Sites não listados são processados com extração genérica ou IA"
    }


@router.post("/analyze-with-ai")
async def analyze_page_with_ai_endpoint(
    request: ScrapeRequest,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CEO, UserRole.DIRETOR]))
):
    """
    Analisa uma página usando IA configurada (Gemini por defeito).
    
    Útil para sites que bloqueiam scraping ou têm estrutura complexa.
    A IA extrai automaticamente informações de imóveis do HTML.
    
    Custo: Usa créditos da API configurada (Gemini é muito económico)
    """
    try:
        from services.scraper import analyze_page_with_ai
        from services.ai_page_analyzer import get_ai_config
        import httpx
        
        logger.info(f"Análise IA solicitada para: {request.url}")
        
        # Obter modelo configurado
        config = await get_ai_config()
        model = config.get("scraper_extraction", "gemini-1.5-flash")
        
        # Primeiro, obter o HTML da página
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(request.url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Não foi possível aceder à página (HTTP {response.status_code})"
                }
            
            html_content = response.text
        
        # Analisar com IA
        result = await analyze_page_with_ai(request.url, html_content)
        
        return {
            "success": True,
            "url": request.url,
            "ai_model": model,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Erro na análise IA: {e}")
        raise HTTPException(status_code=500, detail=str(e))
