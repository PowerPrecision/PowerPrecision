"""
Serviço para extração de dados de anúncios de imóveis
Suporta: Idealista, Imovirtual, e input manual
Usa DeepScraper para extracção avançada com navegação para sites de agências
"""
import re
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from models.lead import ScrapedData, ConsultantInfo
from services.scraper import scraper as deep_scraper, ImovelScrapedData

logger = logging.getLogger(__name__)


async def extract_property_data(url: str, use_deep_scraping: bool = True) -> ScrapedData:
    """
    Extrai dados de um anúncio de imóvel a partir do URL.
    Detecta automaticamente a fonte (Idealista, Imovirtual, etc.)
    
    Args:
        url: URL do anúncio
        use_deep_scraping: Se True, usa o DeepScraper para encontrar contactos de consultores
    """
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    try:
        # Usar Deep Scraper para Idealista (melhor extração)
        if 'idealista' in domain and use_deep_scraping:
            return await extract_with_deep_scraper(url)
        elif 'idealista' in domain:
            return await scrape_idealista(url)
        elif 'imovirtual' in domain:
            return await scrape_imovirtual(url)
        elif 'casa.sapo' in domain:
            return await scrape_sapo(url)
        else:
            # Tentar extração genérica com deep scraper
            if use_deep_scraping:
                return await extract_with_deep_scraper(url)
            return await scrape_generic(url)
    except Exception as e:
        logger.warning(f"Erro ao extrair dados de {url}: {e}")
        # Retornar dados mínimos
        return ScrapedData(url=url, source="manual")


async def extract_with_deep_scraper(url: str) -> ScrapedData:
    """
    Usa o DeepScraper avançado para extração completa.
    Inclui navegação para sites de agências para encontrar contactos.
    """
    try:
        result: ImovelScrapedData = await deep_scraper.scrape_url(url)
        
        # Converter para o modelo ScrapedData
        consultant = None
        if result.consultor:
            consultant = ConsultantInfo(
                name=result.consultor.nome,
                phone=result.consultor.telefone,
                email=result.consultor.email,
                agency_name=result.consultor.agencia,
                source_url=result.consultor.url_origem
            )
        
        return ScrapedData(
            url=url,
            title=result.titulo,
            price=result.preco,
            location=result.localizacao,
            typology=result.tipologia,
            area=result.area,
            photo_url=result.foto_principal,
            consultant=consultant,
            source=result.fonte,
            raw_data={
                "descricao": result.descricao,
                "caracteristicas": result.caracteristicas,
                "fotos": result.fotos,
                "link_agencia": result.link_agencia,
                "erros": result.erros,
                "confianca_contacto": result.consultor.confianca if result.consultor else None
            }
        )
    except Exception as e:
        logger.error(f"Erro no Deep Scraper: {e}")
        # Fallback para scraping básico
        return await scrape_generic(url)


async def scrape_idealista(url: str) -> ScrapedData:
    """
    Extrai dados do Idealista.
    Nota: Idealista tem proteções anti-scraping. Esta função pode falhar.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                logger.warning(f"Idealista retornou status {response.status_code}")
                return ScrapedData(url=url, source="idealista")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair título
            title = None
            title_elem = soup.select_one('h1.main-info__title-main, .main-info__title-main')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Extrair preço
            price = None
            price_elem = soup.select_one('.info-data-price span, .price-row span')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
                if price_match:
                    price = float(price_match.group().replace('.', ''))
            
            # Extrair localização
            location = None
            location_elem = soup.select_one('.main-info__title-minor, .header-map-list')
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            # Extrair tipologia e área
            typology = None
            area = None
            details = soup.select('.info-features span, .info-data span')
            for detail in details:
                text = detail.get_text(strip=True).lower()
                if 't0' in text or 't1' in text or 't2' in text or 't3' in text or 't4' in text or 't5' in text:
                    typology = text.upper()
                elif 'm²' in text or 'm2' in text:
                    area_match = re.search(r'(\d+)', text)
                    if area_match:
                        area = float(area_match.group())
            
            # Extrair foto principal
            photo_url = None
            photo_elem = soup.select_one('.detail-image-gallery img, .gallery-container img')
            if photo_elem:
                photo_url = photo_elem.get('src') or photo_elem.get('data-src')
            
            # Extrair dados do consultor
            consultant = None
            agent_name = soup.select_one('.professional-name, .advertiser-name span')
            agent_phone = soup.select_one('.phone-btn-container a, [data-phone]')
            
            if agent_name or agent_phone:
                consultant = ConsultantInfo(
                    name=agent_name.get_text(strip=True) if agent_name else None,
                    phone=agent_phone.get('href', '').replace('tel:', '') if agent_phone else None,
                    source_url=url
                )
            
            return ScrapedData(
                url=url,
                title=title,
                price=price,
                location=location,
                typology=typology,
                area=area,
                photo_url=photo_url,
                consultant=consultant,
                source="idealista"
            )
            
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do Idealista: {e}")
        return ScrapedData(url=url, source="idealista")


async def scrape_imovirtual(url: str) -> ScrapedData:
    """Extrai dados do Imovirtual."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return ScrapedData(url=url, source="imovirtual")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair título
            title = None
            title_elem = soup.select_one('h1[data-cy="adPageAdTitle"], .css-1wnihf5')
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Extrair preço
            price = None
            price_elem = soup.select_one('[data-cy="adPageHeaderPrice"], .css-12vwvwj')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'[\d\s]+', price_text.replace(' ', ''))
                if price_match:
                    price = float(price_match.group().replace(' ', ''))
            
            # Extrair localização
            location = None
            location_elem = soup.select_one('[data-cy="adPageHeaderLocation"], .css-1helwne')
            if location_elem:
                location = location_elem.get_text(strip=True)
            
            return ScrapedData(
                url=url,
                title=title,
                price=price,
                location=location,
                source="imovirtual"
            )
            
    except Exception as e:
        logger.error(f"Erro ao fazer scraping do Imovirtual: {e}")
        return ScrapedData(url=url, source="imovirtual")


async def scrape_sapo(url: str) -> ScrapedData:
    """Extrai dados do Casa SAPO."""
    return ScrapedData(url=url, source="casa.sapo")


async def scrape_generic(url: str) -> ScrapedData:
    """Tentativa genérica de extração de dados."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code != 200:
                return ScrapedData(url=url, source="manual")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tentar extrair título
            title = None
            title_elem = soup.select_one('h1, .title, [class*="title"]')
            if title_elem:
                title = title_elem.get_text(strip=True)[:200]
            
            # Tentar extrair preço
            price = None
            price_patterns = soup.find_all(string=re.compile(r'€|EUR|\d+[\s.,]*\d*'))
            for p in price_patterns[:5]:
                match = re.search(r'(\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})?)\s*€?', p)
                if match:
                    price_str = match.group(1).replace(' ', '').replace('.', '').replace(',', '.')
                    try:
                        price = float(price_str)
                        if price > 10000:  # Provavelmente um preço válido
                            break
                    except:
                        pass
            
            return ScrapedData(
                url=url,
                title=title,
                price=price,
                source="manual"
            )
            
    except Exception as e:
        logger.error(f"Erro na extração genérica: {e}")
        return ScrapedData(url=url, source="manual")
