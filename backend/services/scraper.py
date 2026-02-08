"""
Serviço de Deep Scraping para Imóveis
Extrai dados do Idealista e faz "deep scraping" para encontrar contactos de consultores

Funcionalidades:
1. Extração básica: Preço, Tipologia, Área, Foto
2. Deep Scraping: Navega para sites de agências para encontrar contacto do consultor
3. Extração de telemóveis com validação portuguesa
4. ScraperAPI: Usa proxy rotativo para contornar bloqueios
"""
import os
import re
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, urljoin, quote
from dataclasses import dataclass, asdict

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import phonenumbers
from phonenumbers import geocoder, carrier

logger = logging.getLogger(__name__)

# ScraperAPI configuration
SCRAPERAPI_KEY = os.environ.get('SCRAPERAPI_API_KEY', '')
SCRAPERAPI_BASE_URL = "http://api.scraperapi.com"

# Inicializar UserAgent
try:
    ua = UserAgent()
except:
    ua = None


@dataclass
class ConsultorInfo:
    """Informação do consultor/agência extraída"""
    nome: Optional[str] = None
    telefone: Optional[str] = None
    telefone_secundario: Optional[str] = None
    email: Optional[str] = None
    agencia: Optional[str] = None
    cargo: Optional[str] = None
    url_origem: Optional[str] = None
    confianca: str = "baixa"  # baixa, media, alta


@dataclass
class ImovelScrapedData:
    """Dados extraídos de um anúncio de imóvel"""
    url_original: str
    titulo: Optional[str] = None
    preco: Optional[float] = None
    preco_texto: Optional[str] = None
    tipologia: Optional[str] = None
    area: Optional[float] = None
    area_texto: Optional[str] = None
    localizacao: Optional[str] = None
    descricao: Optional[str] = None
    foto_principal: Optional[str] = None
    fotos: List[str] = None
    caracteristicas: List[str] = None
    consultor: Optional[ConsultorInfo] = None
    fonte: str = "idealista"
    link_agencia: Optional[str] = None
    raw_html_preview: Optional[str] = None
    erros: List[str] = None
    
    def __post_init__(self):
        if self.fotos is None:
            self.fotos = []
        if self.caracteristicas is None:
            self.caracteristicas = []
        if self.erros is None:
            self.erros = []
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.consultor:
            data['consultor'] = asdict(self.consultor)
        return data


class DeepScraper:
    """
    Scraper avançado com capacidade de "deep scraping" para sites de agências.
    """
    
    # Padrões para encontrar links de agências
    AGENCY_LINK_PATTERNS = [
        r'visitar?\s*site',
        r'ver\s*site',
        r'link\s*adicional',
        r'site\s*oficial',
        r'website',
        r'página\s*do\s*anunciante',
        r'ver\s*mais\s*no\s*site',
        r'ir\s*para\s*o?\s*site',
    ]
    
    # Padrões para identificar nomes de consultores
    CONSULTANT_PATTERNS = [
        r'(?:consultor|angariador|agente|comercial|responsável)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})',
        r'(?:contacto|contacte)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})',
        r'(?:nome|name)[:\s]+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+){1,3})',
    ]
    
    # Prefixos de telemóveis portugueses
    PT_MOBILE_PREFIXES = ['91', '92', '93', '96']
    PT_LANDLINE_PREFIXES = ['21', '22', '23', '24', '25', '26', '27', '28', '29']
    
    def __init__(self, timeout: float = 15.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Gera headers realistas para evitar bloqueios."""
        user_agent = ua.random if ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        return {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-PT,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
    
    async def _fetch_page(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Faz fetch de uma página com retry e tratamento de erros.
        Retorna (html_content, error_message).
        """
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True, 
                    timeout=self.timeout,
                    verify=False  # Alguns sites têm certificados inválidos
                ) as client:
                    response = await client.get(url, headers=self._get_headers())
                    
                    if response.status_code == 200:
                        return response.text, None
                    elif response.status_code == 403:
                        logger.warning(f"Bloqueado (403) em {url}")
                        return None, "Acesso bloqueado pelo site"
                    elif response.status_code == 404:
                        return None, "Página não encontrada"
                    else:
                        logger.warning(f"Status {response.status_code} em {url}")
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout ao aceder {url} (tentativa {attempt + 1})")
            except Exception as e:
                logger.error(f"Erro ao aceder {url}: {e}")
                
            # Aguardar antes de retry
            if attempt < self.max_retries - 1:
                await asyncio.sleep(1 + attempt)
        
        return None, "Não foi possível aceder à página"
    
    def _extract_phone_numbers(self, text: str) -> List[str]:
        """
        Extrai números de telefone portugueses do texto.
        Prioriza telemóveis (91/92/93/96).
        """
        phones = []
        
        # Padrões de telefone português
        patterns = [
            r'\+351\s*(\d{3})\s*(\d{3})\s*(\d{3})',  # +351 xxx xxx xxx
            r'\(351\)\s*(\d{3})\s*(\d{3})\s*(\d{3})',  # (351) xxx xxx xxx
            r'(?<!\d)(9[1-36]\d)\s*(\d{3})\s*(\d{3})(?!\d)',  # 9xx xxx xxx (móvel)
            r'(?<!\d)(2\d{2})\s*(\d{3})\s*(\d{3})(?!\d)',  # 2xx xxx xxx (fixo)
            r'(?<!\d)(9[1-36]\d)[\s.-]?(\d{3})[\s.-]?(\d{3})(?!\d)',  # Com separadores
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.replace('\n', ' '))
            for match in matches:
                if isinstance(match, tuple):
                    phone = ''.join(match)
                else:
                    phone = match
                
                # Limpar e formatar
                phone = re.sub(r'\D', '', phone)
                
                # Validar comprimento
                if len(phone) == 9:
                    # Verificar se é válido com phonenumbers
                    try:
                        parsed = phonenumbers.parse(phone, 'PT')
                        if phonenumbers.is_valid_number(parsed):
                            formatted = f"+351 {phone[:3]} {phone[3:6]} {phone[6:]}"
                            if formatted not in phones:
                                phones.append(formatted)
                    except:
                        # Adicionar mesmo sem validação completa
                        formatted = f"+351 {phone[:3]} {phone[3:6]} {phone[6:]}"
                        if formatted not in phones:
                            phones.append(formatted)
        
        # Ordenar: telemóveis primeiro
        def sort_key(phone):
            prefix = phone.replace('+351 ', '')[:2]
            if prefix in ['91', '92', '93', '96']:
                return 0
            return 1
        
        return sorted(phones, key=sort_key)
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extrai emails do texto."""
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        return list(set(emails))
    
    def _extract_consultant_name(self, soup: BeautifulSoup, text: str) -> Optional[str]:
        """
        Tenta extrair o nome do consultor usando múltiplas estratégias.
        """
        # Estratégia 1: Procurar em elementos específicos
        name_selectors = [
            '.professional-name',
            '.agent-name',
            '.consultant-name',
            '.broker-name',
            '[class*="agent"]',
            '[class*="consultor"]',
            '[class*="broker"]',
            '.contact-name',
        ]
        
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                name = elem.get_text(strip=True)
                if name and len(name) > 3 and len(name) < 50:
                    return name
        
        # Estratégia 2: Regex no texto
        for pattern in self.CONSULTANT_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 3 and len(name) < 50:
                    return name
        
        return None
    
    def _extract_agency_name(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extrai o nome da agência."""
        # Tentar pelo título da página
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Limpar sufixos comuns
            for suffix in [' - Home', ' | Imobiliária', ' - Imóveis', ' | Home']:
                title_text = title_text.replace(suffix, '')
            if len(title_text) < 100:
                return title_text
        
        # Tentar pelo domínio
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain
    
    def _find_agency_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Procura links para sites de agências na página.
        """
        agency_links = []
        
        # Procurar por links com texto indicativo
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True).lower()
            href = link['href']
            
            # Verificar se o texto corresponde a padrões de link de agência
            for pattern in self.AGENCY_LINK_PATTERNS:
                if re.search(pattern, link_text, re.IGNORECASE):
                    # Construir URL absoluto
                    full_url = urljoin(base_url, href)
                    # Filtrar links do próprio Idealista
                    if 'idealista' not in full_url.lower():
                        agency_links.append(full_url)
                    break
            
            # Verificar também atributos data-*
            for attr in link.attrs:
                if 'url' in attr.lower() or 'link' in attr.lower():
                    value = link[attr]
                    if value and value.startswith('http') and 'idealista' not in value.lower():
                        agency_links.append(value)
        
        # Procurar também em elementos com onclick ou data attributes
        for elem in soup.find_all(attrs={'onclick': True}):
            onclick = elem['onclick']
            urls = re.findall(r'https?://[^\s\'"]+', onclick)
            for url in urls:
                if 'idealista' not in url.lower():
                    agency_links.append(url)
        
        return list(set(agency_links))
    
    async def _deep_scrape_agency(self, agency_url: str) -> Optional[ConsultorInfo]:
        """
        Faz deep scraping no site da agência para encontrar contacto do consultor.
        """
        logger.info(f"Deep scraping em: {agency_url}")
        
        html, error = await self._fetch_page(agency_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        
        # Extrair informações
        phones = self._extract_phone_numbers(text)
        emails = self._extract_emails(text)
        name = self._extract_consultant_name(soup, text)
        agency = self._extract_agency_name(soup, agency_url)
        
        if phones or emails or name:
            consultor = ConsultorInfo(
                nome=name,
                telefone=phones[0] if phones else None,
                telefone_secundario=phones[1] if len(phones) > 1 else None,
                email=emails[0] if emails else None,
                agencia=agency,
                url_origem=agency_url,
                confianca="alta" if (phones and name) else "media"
            )
            return consultor
        
        return None
    
    async def scrape_idealista(self, url: str) -> ImovelScrapedData:
        """
        Faz scraping completo de um anúncio do Idealista.
        Inclui deep scraping para encontrar contacto do consultor.
        """
        result = ImovelScrapedData(url_original=url, fonte="idealista")
        
        # Fetch da página principal
        html, error = await self._fetch_page(url)
        if not html:
            result.erros.append(error or "Erro ao aceder à página")
            return result
        
        soup = BeautifulSoup(html, 'html.parser')
        result.raw_html_preview = html[:500]  # Preview para debug
        
        try:
            # === EXTRAÇÃO BÁSICA ===
            
            # Título
            title_elem = soup.select_one('h1.main-info__title-main, .main-info__title-main, h1')
            if title_elem:
                result.titulo = title_elem.get_text(strip=True)
            
            # Preço
            price_selectors = [
                '.info-data-price span',
                '.price-row span',
                '[class*="price"]',
                '.info-data-price',
            ]
            for selector in price_selectors:
                price_elem = soup.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    result.preco_texto = price_text
                    # Extrair valor numérico
                    price_match = re.search(r'[\d.,]+', price_text.replace('.', '').replace(',', '.'))
                    if price_match:
                        try:
                            result.preco = float(price_match.group().replace('.', ''))
                        except:
                            pass
                    break
            
            # Localização
            location_selectors = [
                '.main-info__title-minor',
                '.header-map-list',
                '.location',
                '[class*="location"]',
            ]
            for selector in location_selectors:
                loc_elem = soup.select_one(selector)
                if loc_elem:
                    result.localizacao = loc_elem.get_text(strip=True)
                    break
            
            # Tipologia e Área
            details = soup.select('.info-features span, .info-data span, .details-property span')
            for detail in details:
                text = detail.get_text(strip=True).lower()
                
                # Tipologia
                if re.match(r't[0-5]\+?', text):
                    result.tipologia = text.upper()
                
                # Área
                if 'm²' in text or 'm2' in text:
                    result.area_texto = text
                    area_match = re.search(r'(\d+)', text)
                    if area_match:
                        result.area = float(area_match.group())
            
            # Foto principal
            img_selectors = [
                '.detail-image-gallery img',
                '.gallery-container img',
                '.main-image img',
                'picture img',
                '[class*="gallery"] img',
            ]
            for selector in img_selectors:
                img_elem = soup.select_one(selector)
                if img_elem:
                    result.foto_principal = img_elem.get('src') or img_elem.get('data-src')
                    if result.foto_principal:
                        break
            
            # Todas as fotos
            for img in soup.select('[class*="gallery"] img, .multimedia img'):
                src = img.get('src') or img.get('data-src')
                if src and src not in result.fotos:
                    result.fotos.append(src)
            
            # Descrição
            desc_elem = soup.select_one('.comment, .description, [class*="description"]')
            if desc_elem:
                result.descricao = desc_elem.get_text(strip=True)[:1000]
            
            # Características
            for item in soup.select('.details-property-feature-one li, .details-property li'):
                feature = item.get_text(strip=True)
                if feature and feature not in result.caracteristicas:
                    result.caracteristicas.append(feature)
            
            # === EXTRAÇÃO DE CONTACTO (BÁSICA) ===
            
            # Tentar extrair contacto da página do Idealista
            text = soup.get_text(separator=' ')
            phones = self._extract_phone_numbers(text)
            
            # Nome do agente no Idealista
            agent_name = None
            agent_selectors = [
                '.professional-name',
                '.advertiser-name span',
                '[class*="agent-name"]',
            ]
            for selector in agent_selectors:
                elem = soup.select_one(selector)
                if elem:
                    agent_name = elem.get_text(strip=True)
                    break
            
            # Agência no Idealista
            agency_name = None
            agency_selectors = [
                '.professional-name__logo img',
                '.advertiser-name',
                '[class*="agency"]',
            ]
            for selector in agency_selectors:
                elem = soup.select_one(selector)
                if elem:
                    if elem.name == 'img':
                        agency_name = elem.get('alt')
                    else:
                        agency_name = elem.get_text(strip=True)
                    break
            
            # Criar info básica do consultor
            if phones or agent_name:
                result.consultor = ConsultorInfo(
                    nome=agent_name,
                    telefone=phones[0] if phones else None,
                    agencia=agency_name,
                    url_origem=url,
                    confianca="media" if phones else "baixa"
                )
            
            # === DEEP SCRAPING ===
            
            # Procurar links para sites de agências
            agency_links = self._find_agency_links(soup, url)
            
            if agency_links:
                result.link_agencia = agency_links[0]
                logger.info(f"Encontrados {len(agency_links)} links de agência")
                
                # Tentar deep scraping no primeiro link
                deep_consultor = await self._deep_scrape_agency(agency_links[0])
                
                if deep_consultor:
                    # Usar dados do deep scraping se forem melhores
                    if not result.consultor or deep_consultor.confianca == "alta":
                        result.consultor = deep_consultor
                    elif result.consultor and not result.consultor.telefone and deep_consultor.telefone:
                        result.consultor.telefone = deep_consultor.telefone
                        result.consultor.confianca = "media"
            
        except Exception as e:
            logger.error(f"Erro no scraping de {url}: {e}")
            result.erros.append(f"Erro no processamento: {str(e)}")
        
        return result
    
    async def scrape_url(self, url: str) -> ImovelScrapedData:
        """
        Ponto de entrada principal. Detecta a fonte e faz o scraping apropriado.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if 'idealista' in domain:
            return await self.scrape_idealista(url)
        elif 'imovirtual' in domain:
            # TODO: Implementar scraper específico
            return await self._scrape_generic(url, "imovirtual")
        elif 'casa.sapo' in domain:
            return await self._scrape_generic(url, "casa.sapo")
        else:
            return await self._scrape_generic(url, "desconhecido")
    
    async def _scrape_generic(self, url: str, fonte: str) -> ImovelScrapedData:
        """Scraping genérico para sites não suportados especificamente."""
        result = ImovelScrapedData(url_original=url, fonte=fonte)
        
        html, error = await self._fetch_page(url)
        if not html:
            result.erros.append(error or "Erro ao aceder à página")
            return result
        
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text(separator=' ')
        
        # Título
        title = soup.find('h1')
        if title:
            result.titulo = title.get_text(strip=True)[:200]
        
        # Tentar extrair preço
        price_patterns = [
            r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*€',
            r'€\s*(\d{1,3}(?:[.,]\d{3})*)',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                result.preco_texto = match.group(0)
                price_str = match.group(1).replace('.', '').replace(',', '.')
                try:
                    result.preco = float(price_str)
                    if result.preco > 10000:  # Provavelmente um preço válido
                        break
                except:
                    pass
        
        # Contactos
        phones = self._extract_phone_numbers(text)
        if phones:
            result.consultor = ConsultorInfo(
                telefone=phones[0],
                telefone_secundario=phones[1] if len(phones) > 1 else None,
                url_origem=url,
                confianca="baixa"
            )
        
        return result


# Instância global para reutilização
scraper = DeepScraper()


async def scrape_property_url(url: str) -> Dict[str, Any]:
    """
    Função de conveniência para fazer scraping de um URL.
    Retorna um dicionário com os dados extraídos.
    """
    result = await scraper.scrape_url(url)
    return result.to_dict()
