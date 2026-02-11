"""
====================================================================
SERVIÇO DE IA PARA ANÁLISE DE PÁGINAS (GPT-4o)
====================================================================
Este serviço usa o GPT-4o para:
- Analisar conteúdo HTML de páginas web
- Extrair informações de imóveis
- Análise inteligente de dados estruturados

Configuração:
- Modelo: gpt-4o (OpenAI)
- Provider: OpenAI via emergentintegrations
====================================================================
"""
import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Configuração do modelo - GPT-4o é muito capaz para análise
AI_MODEL = "gpt-4o"
AI_PROVIDER = "openai"


async def analyze_page_with_claude(
    html_content: str,
    url: str,
    extraction_type: str = "property"
) -> Dict[str, Any]:
    """
    Analisa o conteúdo HTML de uma página usando Claude 3.5 Sonnet.
    
    Args:
        html_content: Conteúdo HTML da página
        url: URL da página para contexto
        extraction_type: Tipo de extração ("property", "contact", "general")
        
    Returns:
        Dict com dados extraídos
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            logger.error("EMERGENT_LLM_KEY não configurada")
            return {"error": "API key não configurada"}
        
        # Limitar tamanho do HTML (Claude tem limite de contexto)
        max_html_length = 50000
        if len(html_content) > max_html_length:
            html_content = html_content[:max_html_length] + "...[truncated]"
        
        # Configurar chat com GPT-4o
        chat = LlmChat(
            api_key=api_key,
            session_id=f"page-analysis-{url[:50]}",
            system_message=get_system_prompt(extraction_type)
        ).with_model(AI_PROVIDER, AI_MODEL)
        
        # Criar mensagem
        user_message = UserMessage(
            text=f"""Analisa o seguinte conteúdo HTML de uma página imobiliária.
            
URL: {url}

HTML Content:
{html_content}

Extrai as informações relevantes e retorna em formato JSON estruturado."""
        )
        
        # Enviar e obter resposta
        response = await chat.send_message(user_message)
        
        # Tentar parsear como JSON
        import json
        try:
            # Remover possíveis markdown code blocks
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            data = json.loads(clean_response.strip())
            return {"success": True, "data": data, "model": CLAUDE_MODEL}
        except json.JSONDecodeError:
            # Se não for JSON válido, retornar texto
            return {"success": True, "data": {"raw_analysis": response}, "model": CLAUDE_MODEL}
            
    except Exception as e:
        logger.error(f"Erro ao analisar página com Claude: {e}")
        return {"success": False, "error": str(e)}


async def analyze_weekly_errors_with_ai(
    errors: list,
    patterns: Dict[str, int]
) -> Dict[str, Any]:
    """
    Usa IA (Claude) para analisar erros semanais e gerar sugestões inteligentes.
    
    Args:
        errors: Lista de erros da semana
        patterns: Padrões de erro identificados
        
    Returns:
        Dict com análise e sugestões da IA
    """
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return {"error": "API key não configurada"}
        
        # Preparar dados para análise
        error_summary = []
        for err in errors[:50]:  # Limitar a 50 erros
            error_summary.append({
                "source": err.get("source", "unknown"),
                "message": (err.get("error_message") or err.get("error", ""))[:200],
                "count": 1
            })
        
        # Configurar chat com Claude
        chat = LlmChat(
            api_key=api_key,
            session_id="weekly-error-analysis",
            system_message="""És um analista de sistemas especializado em CRM imobiliário.
Analisa os erros de importação e gera sugestões práticas de resolução.
Responde sempre em Português de Portugal.
Formato de resposta: JSON com campos "summary", "root_causes", "suggestions", "priority_actions"."""
        ).with_model(CLAUDE_PROVIDER, CLAUDE_MODEL)
        
        # Criar mensagem
        user_message = UserMessage(
            text=f"""Analisa os seguintes erros de importação da última semana:

ERROS ({len(errors)} total):
{error_summary[:20]}

PADRÕES IDENTIFICADOS:
{patterns}

Gera um relatório com:
1. Sumário executivo
2. Causas raiz identificadas
3. Sugestões de resolução (ordenadas por impacto)
4. Acções prioritárias para a próxima semana

Responde em JSON."""
        )
        
        response = await chat.send_message(user_message)
        
        # Parsear resposta
        import json
        try:
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            
            return json.loads(clean_response.strip())
        except json.JSONDecodeError:
            return {"summary": response, "ai_model": CLAUDE_MODEL}
            
    except Exception as e:
        logger.error(f"Erro na análise IA de erros: {e}")
        return {"error": str(e)}


def get_system_prompt(extraction_type: str) -> str:
    """Retorna o system prompt adequado ao tipo de extração."""
    
    prompts = {
        "property": """És um especialista em extração de dados imobiliários.
Analisa páginas HTML de portais imobiliários portugueses e extrai:
- Título do imóvel
- Preço (em euros)
- Localização (distrito, concelho, freguesia)
- Tipologia (T0, T1, T2, etc.)
- Área (útil e bruta em m²)
- Características (quartos, casas de banho, garagem, etc.)
- Descrição
- Contacto do anunciante

Responde sempre em JSON estruturado. Usa null para campos não encontrados.
Normaliza preços para números (sem € ou pontos de milhar).
Responde em Português de Portugal.""",

        "contact": """És um especialista em extração de contactos.
Extrai informações de contacto de páginas web:
- Nome
- Email
- Telefone (formato português)
- Morada
- Website

Responde em JSON. Usa null para campos não encontrados.""",

        "general": """És um assistente de análise de conteúdo web.
Extrai as informações principais da página fornecida.
Identifica o tipo de conteúdo e estrutura os dados relevantes.
Responde em JSON estruturado."""
    }
    
    return prompts.get(extraction_type, prompts["general"])


# Instância para uso global
class PageAnalyzer:
    """Wrapper para análise de páginas com Claude."""
    
    def __init__(self):
        self.model = CLAUDE_MODEL
        self.provider = CLAUDE_PROVIDER
    
    async def analyze(self, html: str, url: str, type: str = "property") -> Dict:
        return await analyze_page_with_claude(html, url, type)
    
    async def analyze_errors(self, errors: list, patterns: dict) -> Dict:
        return await analyze_weekly_errors_with_ai(errors, patterns)


page_analyzer = PageAnalyzer()
