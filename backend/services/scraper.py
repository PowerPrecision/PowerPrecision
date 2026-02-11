"""
====================================================================
SCRAPER SERVICE - EXTRAÇÃO HÍBRIDA (BeautifulSoup + Gemini)
====================================================================
Este serviço extrai dados de portais imobiliários usando:
1. Parsers específicos (BeautifulSoup) para sites conhecidos
2. Gemini 2.0 Flash como fallback para sites desconhecidos ou 
   quando a extração falha
3. "Deep Link" - Segue links externos para encontrar dados de contacto
4. Cache local - Guarda resultados para evitar chamadas repetidas

Configuração:
- GEMINI_API_KEY: Chave API do Google Gemini
- Os parsers específicos são gratuitos (sem custo de API)
- O Gemini é usado apenas quando necessário (custo muito baixo)

Deep Link Logic:
- Após extracção inicial, se faltar telefone/email do agente
- Procura links para sites de agências (remax, era, century21, etc.)
- Faz scraping da página do agente para encontrar contactos

Cache:
- Resultados são guardados na colecção `scraper_cache` por 7 dias
- URLs já processadas retornam o resultado em cache
====================================================================
"""
import logging
import re
import json
import ssl
import httpx
import hashlib
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
from fake_useragent import UserAgent
from urllib.parse import urlparse, urljoin
from collections import deque
import asyncio
from datetime import datetime, timezone, timedelta

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Padrões de domínios de agências imobiliárias
AGENCY_DOMAINS = [
    "remax", "era.pt", "century21", "coldwellbanker", "kw.com", "kwportugal",
    "engel", "sothebys", "christies", "savills", "cbre", "jll", "cushwake",
    "iad-", "iadportugal", "zome", "comprarcasa", "casasdobarlavento"
]

# Padrões regex para contactos
PHONE_PATTERNS = [
    r'\+351\s*\d{3}\s*\d{3}\s*\d{3}',
    r'\+351\s*\d{9}',
    r'9[1236]\d{7}',
    r'2[1-9]\d{7}',
    r'\d{3}\s*\d{3}\s*\d{3}',
]

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

# Cache settings
CACHE_EXPIRY_DAYS = 7


class PropertyScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.timeout = 30.0
        self._db = None
    
    async def _get_db(self):
        """Lazy load database connection."""
        if self._db is None:
            from database import db
            self._db = db
        return self._db
    
    # ================================================================
    # CACHE SYSTEM
    # ================================================================
    
    def _get_url_hash(self, url: str) -> str:
        """Gera hash único para uma URL."""
        return hashlib.md5(url.lower().strip().encode()).hexdigest()
    
    async def _get_cached_result(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se existe resultado em cache para esta URL.
        
        Returns:
            Resultado em cache ou None
        """
        try:
            db = await self._get_db()
            url_hash = self._get_url_hash(url)
            
            # Buscar cache não expirado
            expiry_date = datetime.now(timezone.utc) - timedelta(days=CACHE_EXPIRY_DAYS)
            
            cached = await db.scraper_cache.find_one(
                {
                    "url_hash": url_hash,
                    "created_at": {"$gte": expiry_date.isoformat()}
                },
                {"_id": 0}
            )
            
            if cached:
                logger.info(f"✓ Cache hit para {url[:50]}...")
                cached["_from_cache"] = True
                return cached.get("result")
            
            return None
            
        except Exception as e:
            logger.debug(f"Erro ao verificar cache: {e}")
            return None
    
    async def _save_to_cache(self, url: str, result: Dict[str, Any]) -> None:
        """
        Guarda resultado no cache.
        
        Args:
            url: URL processada
            result: Resultado da extracção
        """
        try:
            db = await self._get_db()
            url_hash = self._get_url_hash(url)
            
            cache_doc = {
                "url_hash": url_hash,
                "url": url,
                "result": result,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert (actualizar se existir)
            await db.scraper_cache.update_one(
                {"url_hash": url_hash},
                {"$set": cache_doc},
                upsert=True
            )
            
            logger.debug(f"Resultado guardado em cache para {url[:50]}...")
            
        except Exception as e:
            logger.debug(f"Erro ao guardar cache: {e}")
    
    async def clear_cache(self, url: Optional[str] = None) -> int:
        """
        Limpa cache de scraping.
        
        Args:
            url: URL específica para limpar, ou None para limpar tudo
            
        Returns:
            Número de registos eliminados
        """
        try:
            db = await self._get_db()
            
            if url:
                url_hash = self._get_url_hash(url)
                result = await db.scraper_cache.delete_one({"url_hash": url_hash})
            else:
                result = await db.scraper_cache.delete_many({})
            
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        try:
            db = await self._get_db()
            
            total = await db.scraper_cache.count_documents({})
            
            expiry_date = datetime.now(timezone.utc) - timedelta(days=CACHE_EXPIRY_DAYS)
            valid = await db.scraper_cache.count_documents({
                "created_at": {"$gte": expiry_date.isoformat()}
            })
            
            return {
                "total_entries": total,
                "valid_entries": valid,
                "expired_entries": total - valid,
                "cache_expiry_days": CACHE_EXPIRY_DAYS
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # ================================================================
    # AI MODEL CONFIGURATION
    # ================================================================
    
    async def _get_ai_model_for_scraping(self) -> str:
        """
        Obtém o modelo de IA configurado para scraping.
        
        Returns:
            Nome do modelo (ex: 'gemini-2.0-flash', 'gpt-4o-mini')
        """
        try:
            from services.ai_page_analyzer import get_ai_config
            config = await get_ai_config()
            return config.get("scraper_extraction", "gemini-2.0-flash")
        except Exception:
            return "gemini-2.0-flash"
    
    def _get_headers(self) -> Dict[str, str]:
        """Gera headers realistas para evitar bloqueios."""
        return {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.google.pt/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    
    def _clean_text(self, text: str) -> str:
        """Limpa texto HTML removendo scripts, estilos e whitespace extra."""
        if not text:
            return ""
        # Remover tags script e style
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remover tags HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalizar whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    # ================================================================
    # DEEP LINK - EXTRAÇÃO DE CONTACTOS DE PÁGINAS EXTERNAS
    # ================================================================
    
    def _find_agency_links(self, soup: BeautifulSoup, current_domain: str) -> List[str]:
        """
        Encontra links para sites de agências imobiliárias na página.
        
        Returns:
            Lista de URLs de páginas de agentes/agências
        """
        agency_links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '')
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
            # Normalizar URL
            if not href.startswith('http'):
                continue  # Ignorar links relativos - queremos externos
            
            parsed = urlparse(href)
            link_domain = parsed.netloc.lower()
            
            # Ignorar links para o mesmo domínio
            if current_domain in link_domain:
                continue
            
            # Verificar se é um domínio de agência
            for agency_pattern in AGENCY_DOMAINS:
                if agency_pattern in link_domain:
                    agency_links.append(href)
                    break
        
        return list(set(agency_links))[:5]  # Max 5 links únicos
    
    def _extract_contacts_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extrai telefones e emails de texto usando regex.
        
        Returns:
            Dict com telefones e emails encontrados
        """
        contacts = {
            "telefones": [],
            "emails": []
        }
        
        # Extrair telefones
        for pattern in PHONE_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                # Normalizar telefone
                phone = re.sub(r'\s+', '', match)
                if len(phone) >= 9 and phone not in contacts["telefones"]:
                    contacts["telefones"].append(phone)
        
        # Extrair emails
        email_matches = re.findall(EMAIL_PATTERN, text, re.IGNORECASE)
        for email in email_matches:
            email_lower = email.lower()
            # Filtrar emails genéricos/inválidos
            if any(x in email_lower for x in ['@example', '@test', 'noreply', 'info@', 'geral@']):
                continue
            if email_lower not in contacts["emails"]:
                contacts["emails"].append(email_lower)
        
        return contacts
    
    async def _fetch_page_content(self, url: str) -> Optional[str]:
        """
        Faz download do conteúdo HTML de uma URL.
        
        Returns:
            Conteúdo HTML ou None se falhar
        """
        for verify_ssl in [True, False]:
            try:
                await asyncio.sleep(0.5)  # Delay para evitar bloqueios
                
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl,
                    http2=True
                ) as client:
                    response = await client.get(url, headers=self._get_headers())
                    
                    if response.status_code == 200:
                        return response.text
                    
            except Exception as e:
                if verify_ssl:
                    continue
                logger.debug(f"Erro ao buscar {url}: {e}")
        
        return None
    
    async def _deep_link_contacts(self, soup: BeautifulSoup, current_url: str) -> Dict[str, Any]:
        """
        Segue links externos para encontrar dados de contacto.
        
        Este método implementa a lógica "Deep Link":
        1. Procura links para sites de agências na página actual
        2. Visita cada link encontrado
        3. Extrai telefones e emails dessas páginas
        
        Returns:
            Dict com contactos encontrados via deep link
        """
        parsed_url = urlparse(current_url)
        current_domain = parsed_url.netloc.lower()
        
        # Encontrar links de agências
        agency_links = self._find_agency_links(soup, current_domain)
        
        if not agency_links:
            logger.debug(f"Nenhum link de agência encontrado em {current_url}")
            return {}
        
        logger.info(f"Deep Link: Encontrados {len(agency_links)} links de agência em {current_url}")
        
        all_contacts = {
            "telefones": [],
            "emails": [],
            "deep_link_sources": []
        }
        
        for link in agency_links[:3]:  # Limitar a 3 para não sobrecarregar
            try:
                html_content = await self._fetch_page_content(link)
                
                if not html_content:
                    continue
                
                # Extrair contactos do texto limpo
                clean_text = self._clean_text(html_content)
                contacts = self._extract_contacts_from_text(clean_text)
                
                if contacts["telefones"] or contacts["emails"]:
                    logger.info(f"Deep Link: Encontrados contactos em {link}")
                    all_contacts["telefones"].extend(contacts["telefones"])
                    all_contacts["emails"].extend(contacts["emails"])
                    all_contacts["deep_link_sources"].append(link)
                
            except Exception as e:
                logger.debug(f"Deep Link erro em {link}: {e}")
                continue
        
        # Remover duplicados
        all_contacts["telefones"] = list(set(all_contacts["telefones"]))[:3]
        all_contacts["emails"] = list(set(all_contacts["emails"]))[:3]
        
        return all_contacts
    
    # ================================================================
    # EXTRAÇÃO COM GEMINI (FALLBACK IA)
    # ================================================================
    
    async def _extract_with_gemini(self, html_content: str, url: str) -> Dict[str, Any]:
        """
        Usa Gemini 2.0 Flash para extrair dados de imóveis quando 
        os parsers específicos falham.
        
        O modelo usado é determinado pela configuração do admin em
        /api/admin/ai-config.
        
        Args:
            html_content: Conteúdo HTML da página
            url: URL da página (para contexto)
            
        Returns:
            Dict com dados extraídos ou erro
        """
        # Obter modelo configurado
        configured_model = await self._get_ai_model_for_scraping()
        logger.info(f"Usando modelo configurado: {configured_model}")
        
        # Verificar se é Gemini ou OpenAI
        if configured_model.startswith("gpt"):
            return await self._extract_with_openai(html_content, url, configured_model)
        
        # Gemini (default)
        if not GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY não configurada - fallback IA desactivado")
            return {}
        
        try:
            import google.generativeai as genai
            
            # Configurar API
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Limitar HTML para poupar tokens (15k chars ~= 3-4k tokens)
            clean_html = self._clean_text(html_content)[:15000]
            
            prompt = f"""Analisa este conteúdo de uma página imobiliária portuguesa e extrai os dados em formato JSON estrito.

URL: {url}

Extrai APENAS os seguintes campos (usa null se não encontrares):
- titulo: título/nome do imóvel
- preco: preço em número (sem €, sem pontos de milhar)
- localizacao: localização completa (freguesia, concelho, distrito)
- tipologia: tipo (T0, T1, T2, T3, etc. ou moradia, terreno, loja)
- area: área útil em m² (apenas número)
- quartos: número de quartos
- casas_banho: número de casas de banho
- descricao: descrição breve (max 200 chars)
- certificacao_energetica: certificado energético (A, B, C, D, E, F, G)
- ano_construcao: ano de construção
- estado: estado do imóvel (novo, usado, para renovar)
- agente_nome: nome do agente/consultor imobiliário
- agente_telefone: telefone do agente (formato +351 XXX XXX XXX)
- agente_email: email do agente
- agencia_nome: nome da agência imobiliária

IMPORTANTE: Responde APENAS com o JSON, sem explicações ou markdown.

Conteúdo:
{clean_html}"""
            
            # Usar Gemini 2.0 Flash
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            
            result_text = response.text.strip()
            
            # Limpar possíveis markdown code blocks
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            # Parsear JSON
            data = json.loads(result_text.strip())
            
            logger.info(f"✓ Gemini extraiu dados de {url}: {data.get('titulo', 'N/A')}")
            
            return {
                "titulo": data.get("titulo"),
                "preco": data.get("preco"),
                "localizacao": data.get("localizacao"),
                "tipologia": data.get("tipologia"),
                "area": data.get("area"),
                "quartos": data.get("quartos"),
                "casas_banho": data.get("casas_banho"),
                "descricao": data.get("descricao"),
                "certificado_energetico": data.get("certificacao_energetica"),
                "ano_construcao": data.get("ano_construcao"),
                "estado": data.get("estado"),
                "agente_nome": data.get("agente_nome"),
                "agente_telefone": data.get("agente_telefone"),
                "agente_email": data.get("agente_email"),
                "agencia_nome": data.get("agencia_nome"),
                "_extracted_by": "gemini-2.0-flash"
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Gemini retornou JSON inválido: {e}")
            return {"_error": "JSON inválido da IA"}
        except Exception as e:
            error_str = str(e).lower()
            # Tratamento específico para quota excedida
            if "quota" in error_str or "rate" in error_str or "resource" in error_str or "exhausted" in error_str:
                logger.warning(f"Gemini quota excedida - continuando sem IA: {e}")
                return {"_error": "quota_exceeded", "_fallback": True}
            logger.error(f"Erro Gemini: {type(e).__name__}: {e}")
            return {"_error": str(e)}
    
    async def _extract_with_openai(self, html_content: str, url: str, model: str) -> Dict[str, Any]:
        """
        Usa OpenAI como alternativa ao Gemini para extracção.
        
        Args:
            html_content: Conteúdo HTML da página
            url: URL da página
            model: Modelo OpenAI a usar (ex: 'gpt-4o-mini')
            
        Returns:
            Dict com dados extraídos ou erro
        """
        from config import EMERGENT_LLM_KEY
        
        if not EMERGENT_LLM_KEY:
            logger.warning("EMERGENT_LLM_KEY não configurada - OpenAI desactivado")
            return {"_error": "EMERGENT_LLM_KEY não configurada"}
        
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            clean_html = self._clean_text(html_content)[:15000]
            
            prompt = f"""Analisa este conteúdo de uma página imobiliária portuguesa e extrai os dados em formato JSON.

URL: {url}

Extrai: titulo, preco (número), localizacao, tipologia, area, quartos, casas_banho, descricao, certificacao_energetica, ano_construcao, estado, agente_nome, agente_telefone, agente_email, agencia_nome

Responde APENAS com JSON. Usa null para campos não encontrados.

Conteúdo:
{clean_html}"""
            
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id="scraper-extraction",
                system_message="Extrais dados de páginas imobiliárias. Respondes sempre em JSON válido."
            ).with_model("openai", model)
            
            response = await chat.send_message(UserMessage(text=prompt))
            
            result_text = response.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            data = json.loads(result_text.strip())
            
            logger.info(f"✓ OpenAI ({model}) extraiu dados de {url}")
            
            return {
                **data,
                "_extracted_by": f"openai-{model}"
            }
            
        except Exception as e:
            logger.error(f"Erro OpenAI: {e}")
            return {"_error": str(e)}
    
    # ================================================================
    # SCRAPING PRINCIPAL (HÍBRIDO COM DEEP LINK E CACHE)
    # ================================================================
    
    async def scrape_url(self, url: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extrai dados de uma URL imobiliária usando abordagem híbrida:
        1. Verifica cache local (se use_cache=True)
        2. Tenta parsers específicos (BeautifulSoup)
        3. Se falhar, usa Gemini como fallback
        4. Se faltar contacto do agente, usa Deep Link
        5. Guarda resultado em cache
        
        Args:
            url: URL a processar
            use_cache: Se deve usar/guardar cache (default: True)
            
        Returns:
            Dict com dados do imóvel
        """
        if not url:
            return {"error": "URL vazia"}
        
        # Normalizar URL
        if not url.startswith("http"):
            url = "https://" + url
        
        # ============================================================
        # VERIFICAR CACHE
        # ============================================================
        if use_cache:
            cached = await self._get_cached_result(url)
            if cached:
                return cached
        
        html_content = None
        parser_used = None
        
        # Tentar obter HTML (primeiro com SSL, depois sem)
        for verify_ssl in [True, False]:
            try:
                import random
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    verify=verify_ssl,
                    http2=True
                ) as client:
                    response = await client.get(url, headers=self._get_headers())
                    
                    if response.status_code == 200:
                        html_content = response.text
                        break
                    elif response.status_code == 403:
                        return {"error": "Acesso bloqueado (403). Site pode ter protecção anti-bot."}
                    elif response.status_code == 404:
                        return {"error": "Página não encontrada (404)"}
                        
            except httpx.ConnectError:
                if verify_ssl:
                    logger.warning(f"SSL error em {url}, tentando sem verificação")
                    continue
            except Exception as e:
                logger.error(f"Erro HTTP: {e}")
                return {"error": f"Erro de conexão: {str(e)}"}
        
        if not html_content:
            return {"error": "Não foi possível obter o conteúdo da página"}
        
        # Parsear HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Detectar fonte e usar parser específico
        url_lower = url.lower()
        result = {}
        
        if "idealista" in url_lower:
            result = self._parse_idealista(soup, html_content)
            parser_used = "idealista"
        elif "imovirtual" in url_lower:
            result = self._parse_imovirtual(soup)
            parser_used = "imovirtual"
        elif "casasapo" in url_lower or "casa.sapo" in url_lower:
            result = self._parse_casasapo(soup)
            parser_used = "casasapo"
        elif "remax" in url_lower:
            result = self._parse_remax(soup)
            parser_used = "remax"
        elif "era.pt" in url_lower:
            result = self._parse_era(soup, html_content)
            parser_used = "era"
        elif "kw.com" in url_lower or "kwportugal" in url_lower:
            result = self._parse_kw(soup)
            parser_used = "kw"
        elif "supercasa" in url_lower:
            result = self._parse_supercasa(soup)
            parser_used = "supercasa"
        else:
            result = self._parse_generic(soup)
            parser_used = "generic"
        
        # ============================================================
        # FALLBACK GEMINI: Se dados essenciais estiverem em falta
        # ============================================================
        needs_gemini = False
        
        # Verificar se dados essenciais foram extraídos
        if not result.get("titulo") and not result.get("preco"):
            needs_gemini = True
            logger.info(f"Parser {parser_used} falhou - título e preço em falta")
        elif parser_used == "generic":
            # Para sites genéricos, sempre tentar Gemini para melhor extração
            needs_gemini = True
            logger.info(f"Site genérico detectado - usando Gemini para melhor extração")
        
        if needs_gemini:
            gemini_result = await self._extract_with_gemini(html_content, url)
            
            if gemini_result and not gemini_result.get("_error"):
                # Fundir resultados (Gemini tem prioridade para campos nulos)
                for key, value in gemini_result.items():
                    if key.startswith("_"):
                        continue
                    if value is not None and (not result.get(key) or result.get(key) == "N/A"):
                        result[key] = value
                
                result["_extracted_by"] = "hybrid (parser + gemini)"
            elif gemini_result.get("_error") == "quota_exceeded":
                # Quota excedida - continuar sem Gemini
                logger.info("Quota Gemini excedida - continuando apenas com parser")
                result["_extracted_by"] = parser_used
                result["_gemini_quota_exceeded"] = True
            else:
                result["_extracted_by"] = parser_used
        else:
            result["_extracted_by"] = parser_used
        
        # ============================================================
        # DEEP LINK: Se faltar contacto do agente
        # ============================================================
        has_agent_contact = (
            result.get("agente_telefone") or 
            result.get("agente_email") or
            result.get("telefone_agente")
        )
        
        if not has_agent_contact:
            logger.info(f"Contacto de agente em falta - iniciando Deep Link para {url}")
            
            # Primeiro tentar extrair contactos da página actual com regex
            page_contacts = self._extract_contacts_from_text(self._clean_text(html_content))
            
            if page_contacts["telefones"]:
                result["agente_telefone"] = page_contacts["telefones"][0]
                result["_contact_source"] = "regex_current_page"
            
            if page_contacts["emails"]:
                result["agente_email"] = page_contacts["emails"][0]
                result["_contact_source"] = "regex_current_page"
            
            # Se ainda não tiver contactos, tentar Deep Link
            if not result.get("agente_telefone") and not result.get("agente_email"):
                deep_contacts = await self._deep_link_contacts(soup, url)
                
                if deep_contacts.get("telefones"):
                    result["agente_telefone"] = deep_contacts["telefones"][0]
                    result["_contact_source"] = "deep_link"
                    result["_deep_link_source"] = deep_contacts.get("deep_link_sources", [])
                
                if deep_contacts.get("emails"):
                    result["agente_email"] = deep_contacts["emails"][0]
                    result["_contact_source"] = "deep_link"
        
        # Adicionar URL e metadados
        result["url"] = url
        result["_parser"] = parser_used
        
        # ============================================================
        # GUARDAR EM CACHE
        # ============================================================
        if use_cache and not result.get("error"):
            await self._save_to_cache(url, result)
        
        return result
    
    # ================================================================
    # PARSERS ESPECÍFICOS
    # ================================================================
    
    def _parse_idealista(self, soup: BeautifulSoup, raw_html: str = "") -> Dict[str, Any]:
        """Parser para Idealista.pt"""
        data = {}
        
        # Título
        title = soup.find('h1', class_='main-info__title')
        if title:
            data["titulo"] = title.get_text(strip=True)
        
        # Preço
        price = soup.find('span', class_='info-data-price')
        if not price:
            price = soup.find('span', {'class': lambda x: x and 'price' in x.lower()})
        if price:
            price_text = re.sub(r'[^\d]', '', price.get_text())
            if price_text:
                data["preco"] = int(price_text)
        
        # Localização
        location = soup.find('span', class_='main-info__title-minor')
        if location:
            data["localizacao"] = location.get_text(strip=True)
        
        # Características
        features = soup.find_all('li', class_='info-features-item')
        for feat in features:
            text = feat.get_text(strip=True).lower()
            if 'm²' in text or 'm2' in text:
                area = re.search(r'(\d+)', text)
                if area:
                    data["area"] = int(area.group(1))
            elif 'quarto' in text or 'hab' in text:
                rooms = re.search(r'(\d+)', text)
                if rooms:
                    data["quartos"] = int(rooms.group(1))
            elif 'wc' in text or 'banho' in text:
                baths = re.search(r'(\d+)', text)
                if baths:
                    data["casas_banho"] = int(baths.group(1))
        
        # Tipologia
        if data.get("quartos"):
            data["tipologia"] = f"T{data['quartos']}"
        
        # Descrição
        desc = soup.find('div', class_='comment')
        if desc:
            data["descricao"] = desc.get_text(strip=True)[:500]
        
        return data
    
    def _parse_imovirtual(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parser para Imovirtual.com"""
        data = {}
        
        # Título
        title = soup.find('h1', {'data-cy': 'adPageAdTitle'})
        if not title:
            title = soup.find('h1')
        if title:
            data["titulo"] = title.get_text(strip=True)
        
        # Preço
        price = soup.find('strong', {'data-cy': 'adPageHeaderPrice'})
        if not price:
            price = soup.find('strong', class_=lambda x: x and 'price' in str(x).lower())
        if price:
            price_text = re.sub(r'[^\d]', '', price.get_text())
            if price_text:
                data["preco"] = int(price_text)
        
        # Localização
        location = soup.find('a', {'data-cy': 'adPageHeaderBreadcrumb'})
        if location:
            data["localizacao"] = location.get_text(strip=True)
        
        # Área
        area_elem = soup.find('div', {'data-testid': 'table-value-area'})
        if area_elem:
            area = re.search(r'(\d+)', area_elem.get_text())
            if area:
                data["area"] = int(area.group(1))
        
        # Quartos
        rooms_elem = soup.find('div', {'data-testid': 'table-value-rooms_num'})
        if rooms_elem:
            rooms = re.search(r'(\d+)', rooms_elem.get_text())
            if rooms:
                data["quartos"] = int(rooms.group(1))
                data["tipologia"] = f"T{data['quartos']}"
        
        return data
    
    def _parse_casasapo(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parser para Casa.sapo.pt"""
        data = {}
        
        title = soup.find('h1')
        if title:
            data["titulo"] = title.get_text(strip=True)
        
        price = soup.find('span', class_='priceValue')
        if not price:
            price = soup.find(class_=lambda x: x and 'price' in str(x).lower())
        if price:
            price_text = re.sub(r'[^\d]', '', price.get_text())
            if price_text:
                data["preco"] = int(price_text)
        
        return data
    
    def _parse_remax(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parser para Remax.pt"""
        data = {}
        
        title = soup.find('h1', class_='details-title')
        if not title:
            title = soup.find('h1')
        if title:
            data["titulo"] = title.get_text(strip=True)
        
        price = soup.find('div', class_='details-price')
        if price:
            price_text = re.sub(r'[^\d]', '', price.get_text())
            if price_text:
                data["preco"] = int(price_text)
        
        return data
    
    def _parse_era(self, soup: BeautifulSoup, raw_html: str = "") -> Dict[str, Any]:
        """Parser para ERA.pt"""
        data = {}
        
        # Tentar JSON-LD primeiro
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict):
                    if json_data.get('@type') == 'Product' or json_data.get('@type') == 'RealEstateListing':
                        if json_data.get('name'):
                            data["titulo"] = json_data['name']
                        if json_data.get('offers', {}).get('price'):
                            data["preco"] = int(float(json_data['offers']['price']))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        
        # Fallback para HTML
        if not data.get("titulo"):
            title = soup.find('h1')
            if title:
                data["titulo"] = title.get_text(strip=True)
        
        return data
    
    def _parse_kw(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parser para KW Portugal"""
        data = {}
        
        title = soup.find('h1')
        if title:
            data["titulo"] = title.get_text(strip=True)
        
        price = soup.find(class_=lambda x: x and 'price' in str(x).lower())
        if price:
            price_text = re.sub(r'[^\d]', '', price.get_text())
            if price_text:
                data["preco"] = int(price_text)
        
        return data
    
    def _parse_supercasa(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parser para SuperCasa.pt"""
        data = {}
        
        title = soup.find('h1')
        if title:
            data["titulo"] = title.get_text(strip=True)
        
        price = soup.find(class_=lambda x: x and 'price' in str(x).lower())
        if price:
            price_text = re.sub(r'[^\d]', '', price.get_text())
            if price_text:
                data["preco"] = int(price_text)
        
        return data
    
    def _parse_generic(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parser genérico usando meta tags OpenGraph e Schema.org"""
        data = {}
        
        # OpenGraph
        og_title = soup.find('meta', property='og:title')
        if og_title:
            data["titulo"] = og_title.get('content', '')
        
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            data["descricao"] = og_desc.get('content', '')[:500]
        
        # Schema.org
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict):
                    if json_data.get('name'):
                        data["titulo"] = json_data['name']
                    if json_data.get('offers', {}).get('price'):
                        data["preco"] = int(float(json_data['offers']['price']))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        
        # Fallback: H1
        if not data.get("titulo"):
            h1 = soup.find('h1')
            if h1:
                data["titulo"] = h1.get_text(strip=True)
        
        # Tentar encontrar preço no texto
        if not data.get("preco"):
            text = soup.get_text()
            prices = re.findall(r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€', text)
            if prices:
                price_text = prices[0].replace('.', '').replace(',', '.')
                try:
                    data["preco"] = int(float(price_text))
                except ValueError:
                    pass
        
        return data
    
    # ================================================================
    # CRAWLING RECURSIVO
    # ================================================================
    
    async def crawl_recursive(
        self, 
        start_url: str, 
        max_pages: int = 10,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Crawler recursivo que navega por várias páginas do mesmo domínio.
        """
        if not start_url.startswith("http"):
            start_url = "https://" + start_url
        
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc
        
        queue = deque([(start_url, 0)])
        visited = set()
        properties = []
        errors = []
        
        logger.info(f"Iniciando crawl em {base_domain} (max_pages={max_pages})")
        
        while queue and len(visited) < max_pages:
            current_url, depth = queue.popleft()
            
            if current_url in visited:
                continue
            
            visited.add(current_url)
            
            try:
                import random
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Tentar com SSL primeiro
                for verify_ssl in [True, False]:
                    try:
                        async with httpx.AsyncClient(
                            timeout=self.timeout,
                            follow_redirects=True,
                            verify=verify_ssl,
                            http2=True
                        ) as client:
                            response = await client.get(current_url, headers=self._get_headers())
                            
                            if response.status_code != 200:
                                errors.append({"url": current_url, "error": f"HTTP {response.status_code}"})
                                break
                            
                            html_content = response.text
                            soup = BeautifulSoup(html_content, 'html.parser')
                            
                            # Extrair dados
                            property_data = await self.scrape_url(current_url)
                            
                            if property_data and not property_data.get("error"):
                                if property_data.get("titulo") or property_data.get("preco"):
                                    property_data["crawl_depth"] = depth
                                    properties.append(property_data)
                            
                            # Encontrar mais links se não atingimos profundidade máxima
                            if depth < max_depth:
                                new_links = self._extract_property_links(soup, base_domain, current_url)
                                for link in new_links:
                                    if link not in visited:
                                        queue.append((link, depth + 1))
                            
                            break  # Sucesso
                            
                    except httpx.ConnectError:
                        if verify_ssl:
                            continue
                        raise
                        
            except Exception as e:
                errors.append({"url": current_url, "error": str(e)})
        
        return {
            "success": True,
            "domain": base_domain,
            "pages_visited": len(visited),
            "properties_found": len(properties),
            "properties": properties,
            "errors": errors if errors else None
        }
    
    def _extract_property_links(self, soup: BeautifulSoup, base_domain: str, current_url: str) -> List[str]:
        """Extrai links de imóveis de uma página."""
        links = []
        
        property_patterns = [
            r'/imovel/', r'/property/', r'/anuncio/', r'/listing/',
            r'/detalhe/', r'/ficha/', r'/ad/', r'/casa-', r'/apartamento-',
            r'/moradia-', r'/terreno-', r'/comprar/', r'/venda/'
        ]
        
        skip_patterns = [
            r'page=', r'/login', r'/registo', r'/contacto', r'/sobre',
            r'#', r'javascript:', r'mailto:', r'tel:'
        ]
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '')
            if not href:
                continue
            
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)
            
            if base_domain not in parsed.netloc:
                continue
            
            if any(re.search(p, full_url.lower()) for p in skip_patterns):
                continue
            
            is_property = any(re.search(p, full_url.lower()) for p in property_patterns)
            has_id = re.search(r'/\d{4,}', full_url)
            
            if is_property or has_id:
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean_url not in links:
                    links.append(clean_url)
        
        return links[:50]
    
    # ================================================================
    # ANÁLISE DIRECTA COM IA
    # ================================================================
    
    async def analyze_with_ai(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Usa Gemini directamente para analisar uma página.
        """
        return await self._extract_with_gemini(html_content, url)


from datetime import datetime, timezone

# Instância global
property_scraper = PropertyScraper()
scrape_property_url = property_scraper.scrape_url
crawl_properties = property_scraper.crawl_recursive
analyze_page_with_ai = property_scraper.analyze_with_ai
