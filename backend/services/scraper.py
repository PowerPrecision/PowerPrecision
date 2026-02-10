import logging
import re
import json
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class PropertyScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.timeout = 30.0

    def _get_headers(self) -> Dict[str, str]:
        """Gera headers realistas para evitar bloqueios."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Extrai dados de uma URL imobiliária.
        Suporta Idealista, Imovirtual, Casa Sapo, SuperCasa, etc.
        """
        if not url:
            return {"error": "URL vazia"}

        # Normalizar URL
        if not url.startswith("http"):
            url = "https://" + url

        # Tentar primeiro com SSL, depois sem verificação (alguns sites têm certificados problemáticos)
        for verify_ssl in [True, False]:
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl
                ) as client:
                    response = await client.get(url, headers=self._get_headers())
                    
                    if response.status_code != 200:
                        logger.warning(f"Erro ao aceder {url}: Status {response.status_code}")
                        if response.status_code == 403:
                            return {
                                "url": url,
                                "error": "Site bloqueou o acesso (código 403). Tente novamente mais tarde.",
                                "fonte": "erro"
                            }
                        return {
                            "url": url,
                            "error": f"Erro HTTP {response.status_code}",
                            "fonte": "erro"
                        }

                    html_content = response.text
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Detectar fonte e extrair dados específicos
                    domain = url.lower()
                    data = {}

                    if "idealista.pt" in domain:
                        data = self._parse_idealista(soup, html_content)
                    elif "imovirtual.com" in domain:
                        data = self._parse_imovirtual(soup)
                    elif "supercasa.pt" in domain:
                        data = self._parse_supercasa(soup)
                    elif "casasapo.pt" in domain:
                        data = self._parse_casasapo(soup)
                    elif "remax.pt" in domain:
                        data = self._parse_remax(soup)
                    elif "era.pt" in domain:
                        data = self._parse_era(soup, html_content)
                    elif "kwportugal.pt" in domain:
                        data = self._parse_kw(soup)
                    else:
                        data = self._parse_generic(soup)

                # Adicionar metadados comuns
                data["url"] = url
                data["scraped_at"] = datetime.now(timezone.utc).isoformat()
                
                # Se não extraiu consultor, tentar genérico
                if not data.get("consultor"):
                    data["consultor"] = self._extract_generic_contacts(soup)

                return data

        except httpx.RequestError as e:
            logger.error(f"Erro de rede ao fazer scraping de {url}: {str(e)}")
            return {"url": url, "error": f"Erro de rede: {str(e)}"}
        except Exception as e:
            logger.error(f"Erro inesperado no scraping de {url}: {str(e)}")
            return {"url": url, "error": f"Erro interno: {str(e)}"}

    def _clean_price(self, price_str: str) -> Optional[float]:
        """Limpa string de preço para float."""
        if not price_str:
            return None
        # Remover símbolos e texto
        clean = re.sub(r'[^\d,.]', '', price_str)
        # Normalizar separadores (assumindo formato PT 1.000,00 ou EN 1,000.00)
        if ',' in clean and '.' in clean:
            if clean.find(',') > clean.find('.'): # 1.000,00
                clean = clean.replace('.', '').replace(',', '.')
            else: # 1,000.00
                clean = clean.replace(',', '')
        elif ',' in clean:
            clean = clean.replace(',', '.')
        
        try:
            return float(clean)
        except ValueError:
            return None

    def _clean_text(self, text: str) -> str:
        """Limpa espaços extras e quebras de linha."""
        if not text:
            return ""
        return " ".join(text.split())

    # --- Parsers Específicos (Lógica de Extração) ---

    def _parse_idealista(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "idealista"}
        
        # Título
        title_elem = soup.find('h1', class_='txt-bold') or soup.find('span', class_='main-info__title-main')
        if title_elem:
            data["titulo"] = self._clean_text(title_elem.get_text())

        # Preço
        price_elem = soup.find('span', class_='txt-bold', string=re.compile(r'€')) or soup.find('span', class_='info-data-price')
        if price_elem:
            data["preco"] = self._clean_price(price_elem.get_text())

        # Localização
        loc_elem = soup.find('div', id='headerMap') or soup.find('span', class_='main-info__title-minor')
        if loc_elem:
            data["localizacao"] = self._clean_text(loc_elem.get_text())

        # Características (Tipologia, Área)
        features = soup.find_all('span', class_='txt-big')
        for feat in features:
            text = feat.get_text().lower()
            if 't' in text and any(c.isdigit() for c in text):
                data["tipologia"] = self._clean_text(text)
            elif 'm²' in text:
                data["area"] = self._clean_text(text)

        # Foto Principal
        img_elem = soup.find('img', class_='main-image_img')
        if img_elem and img_elem.get('src'):
            data["foto_principal"] = img_elem.get('src')

        # Consultor / Agência
        advertiser = soup.find('div', class_='advertiser-name')
        if advertiser:
            data["consultor"] = {
                "nome": self._clean_text(advertiser.get_text()),
                "tipo": "Agência/Profissional"
            }
            
        phone_btn = soup.find('a', class_='phone-cta')
        if phone_btn and phone_btn.get('href'):
             if not data.get("consultor"): data["consultor"] = {}
             data["consultor"]["telefone"] = phone_btn.get('href').replace('tel:', '')

        return data

    def _parse_imovirtual(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "imovirtual"}
        
        # Implementação básica para Imovirtual (estrutura muda frequentemente)
        title = soup.find('h1', {'data-cy': 'adPageAdTitle'})
        if title: data["titulo"] = self._clean_text(title.get_text())
        
        price = soup.find('strong', {'data-cy': 'adPageHeaderPrice'})
        if price: data["preco"] = self._clean_price(price.get_text())
        
        return data

    def _parse_supercasa(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "supercasa"}
        title = soup.find('h1', class_='property-title')
        if title: data["titulo"] = self._clean_text(title.get_text())
        
        price = soup.find('div', class_='property-price')
        if price: data["preco"] = self._clean_price(price.get_text())
        
        return data
        
    def _parse_casasapo(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "casasapo"}
        # Lógica Casa Sapo
        return data

    def _parse_remax(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "remax"}
        # Lógica Remax
        return data
        
    def _parse_era(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "era"}
        # Lógica ERA
        return data
        
    def _parse_kw(self, soup: BeautifulSoup) -> Dict[str, Any]:
        data = {"fonte": "kw"}
        # Lógica KW
        return data

    def _parse_generic(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Tentativa de extração genérica usando meta tags OpenGraph."""
        data = {"fonte": "generico"}
        
        # Título
        og_title = soup.find('meta', property='og:title')
        if og_title: data["titulo"] = og_title.get('content')
        else: 
            title = soup.find('title')
            if title: data["titulo"] = title.get_text()

        # Imagem
        og_image = soup.find('meta', property='og:image')
        if og_image: data["foto_principal"] = og_image.get('content')

        # Descrição
        og_desc = soup.find('meta', property='og:description')
        if og_desc: data["descricao"] = og_desc.get('content')
        
        # Tentar encontrar preço (procura por símbolo € e dígitos)
        # Muito rudimentar, apenas fallback
        body_text = soup.get_text()
        price_match = re.search(r'€\s?[\d.,]+', body_text)
        if price_match:
            data["preco"] = self._clean_price(price_match.group(0))

        return data

    def _extract_generic_contacts(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Tenta encontrar contactos telefónicos e emails na página."""
        contacts = {}
        
        text = soup.get_text()
        
        # Email regex simples
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if emails:
            contacts["email"] = emails[0] # Pega o primeiro encontrado
            
        # Telefone PT regex (9 digitos começando por 9, 2 ou 3)
        phones = re.findall(r'\b(?:9[1236]|2\d|3\d)\d{7}\b', text.replace(' ', ''))
        if phones:
            contacts["telefone"] = phones[0]
            
        return contacts

from datetime import datetime, timezone

# Instância global
property_scraper = PropertyScraper()
scrape_property_url = property_scraper.scrape_url