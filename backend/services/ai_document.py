"""
AI Document Analysis Service
Uses GPT-4o to extract structured data from documents (CC, salary receipts, IRS)
"""
import os
import json
import logging
import base64
import httpx
from typing import Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')


async def analyze_document_from_url(document_url: str, document_type: str) -> Dict[str, Any]:
    """
    Analyze a document from URL using GPT-4o vision.
    
    Args:
        document_url: URL of the document (from OneDrive)
        document_type: Type of document ('cc', 'recibo_vencimento', 'irs', 'outro')
    
    Returns:
        Dictionary with extracted data
    """
    if not EMERGENT_LLM_KEY:
        logger.error("EMERGENT_LLM_KEY not configured")
        return {"error": "AI service not configured", "extracted_data": {}}
    
    # Get the appropriate prompt based on document type
    system_prompt, user_prompt = get_extraction_prompts(document_type)
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"doc-analysis-{datetime.now().timestamp()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o")
        
        # Create message with image URL
        user_message = UserMessage(
            text=f"{user_prompt}\n\nDocument URL: {document_url}"
        )
        
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        extracted_data = parse_ai_response(response, document_type)
        
        return {
            "success": True,
            "document_type": document_type,
            "extracted_data": extracted_data,
            "raw_response": response
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {}
        }


async def analyze_document_from_base64(base64_content: str, mime_type: str, document_type: str) -> Dict[str, Any]:
    """
    Analyze a document from base64 content using GPT-4o vision.
    
    Args:
        base64_content: Base64 encoded document content
        mime_type: MIME type of the document (image/jpeg, image/png, application/pdf)
        document_type: Type of document ('cc', 'recibo_vencimento', 'irs', 'outro')
    
    Returns:
        Dictionary with extracted data
    """
    if not EMERGENT_LLM_KEY:
        logger.error("EMERGENT_LLM_KEY not configured")
        return {"error": "AI service not configured", "extracted_data": {}}
    
    system_prompt, user_prompt = get_extraction_prompts(document_type)
    
    try:
        # Use OpenAI API directly for base64 image analysis
        import httpx
        
        headers = {
            "Authorization": f"Bearer {EMERGENT_LLM_KEY}",
            "Content-Type": "application/json"
        }
        
        # Build the message with image
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_content}"
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "model": "gpt-4o",
            "messages": messages,
            "max_tokens": 2000
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
        
        ai_response = result["choices"][0]["message"]["content"]
        extracted_data = parse_ai_response(ai_response, document_type)
        
        return {
            "success": True,
            "document_type": document_type,
            "extracted_data": extracted_data,
            "raw_response": ai_response
        }
        
    except Exception as e:
        logger.error(f"Error analyzing document: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {}
        }


def get_extraction_prompts(document_type: str) -> tuple:
    """Get system and user prompts based on document type."""
    
    if document_type == "cc":
        system_prompt = """Você é um assistente especializado em extrair dados de documentos de identificação portugueses (Cartão de Cidadão).
        
Extraia TODOS os dados visíveis do documento e retorne em formato JSON estruturado.
Seja preciso com datas, números e nomes.
Se algum campo não for legível ou não existir, use null."""
        
        user_prompt = """Analise este Cartão de Cidadão português e extraia os seguintes dados em formato JSON:

{
    "nome_completo": "Nome completo da pessoa",
    "nif": "Número de Identificação Fiscal (9 dígitos)",
    "numero_documento": "Número do CC",
    "data_nascimento": "Data de nascimento (formato YYYY-MM-DD)",
    "data_validade": "Data de validade do documento (formato YYYY-MM-DD)",
    "naturalidade": "Local de nascimento",
    "nacionalidade": "Nacionalidade",
    "sexo": "M ou F",
    "altura": "Altura em metros",
    "pai": "Nome do pai",
    "mae": "Nome da mãe"
}

Retorne APENAS o JSON, sem texto adicional."""

    elif document_type == "recibo_vencimento":
        system_prompt = """Você é um assistente especializado em extrair dados de recibos de vencimento portugueses.
        
Extraia TODOS os valores financeiros e dados do funcionário visíveis.
Valores monetários devem ser números decimais.
Se algum campo não for legível ou não existir, use null."""
        
        user_prompt = """Analise este recibo de vencimento e extraia os seguintes dados em formato JSON:

{
    "nome_funcionario": "Nome do funcionário",
    "nif": "NIF do funcionário",
    "empresa": "Nome da empresa empregadora",
    "mes_referencia": "Mês de referência (formato YYYY-MM)",
    "salario_bruto": 0.00,
    "salario_liquido": 0.00,
    "descontos_irs": 0.00,
    "descontos_ss": 0.00,
    "subsidio_alimentacao": 0.00,
    "outros_abonos": 0.00,
    "tipo_contrato": "Efetivo/Termo/Outro",
    "categoria_profissional": "Categoria/função"
}

Retorne APENAS o JSON, sem texto adicional."""

    elif document_type == "irs":
        system_prompt = """Você é um assistente especializado em extrair dados de declarações de IRS portuguesas.
        
Extraia os dados fiscais principais visíveis no documento.
Valores monetários devem ser números decimais.
Se algum campo não for legível ou não existir, use null."""
        
        user_prompt = """Analise esta declaração de IRS e extraia os seguintes dados em formato JSON:

{
    "ano_fiscal": 2024,
    "nif_titular": "NIF do titular",
    "nome_titular": "Nome do titular",
    "estado_civil_fiscal": "Solteiro/Casado/União de facto",
    "rendimento_bruto_anual": 0.00,
    "rendimento_liquido_anual": 0.00,
    "imposto_pago": 0.00,
    "reembolso_ou_pagamento": 0.00,
    "numero_dependentes": 0,
    "tem_imoveis": true,
    "tem_creditos_habitacao": true
}

Retorne APENAS o JSON, sem texto adicional."""

    else:
        system_prompt = """Você é um assistente especializado em extrair dados de documentos.
Extraia todos os dados relevantes que encontrar no documento."""
        
        user_prompt = """Analise este documento e extraia todos os dados relevantes em formato JSON estruturado.
Inclua nomes, datas, valores, números de identificação, e qualquer outra informação importante.
Retorne APENAS o JSON, sem texto adicional."""

    return system_prompt, user_prompt


def parse_ai_response(response: str, document_type: str) -> Dict[str, Any]:
    """Parse the AI response and extract JSON data."""
    
    try:
        # Try to find JSON in the response
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # Parse JSON
        data = json.loads(response)
        return data
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI response as JSON: {e}")
        return {"raw_text": response, "parse_error": str(e)}


def map_cc_to_personal_data(cc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map extracted CC data to personal_data format."""
    return {
        "nif": cc_data.get("nif"),
        "documento_id": cc_data.get("numero_documento"),
        "naturalidade": cc_data.get("naturalidade"),
        "nacionalidade": cc_data.get("nacionalidade"),
        "birth_date": cc_data.get("data_nascimento"),
    }


def map_recibo_to_financial_data(recibo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map extracted salary receipt data to financial_data format."""
    return {
        "monthly_income": recibo_data.get("salario_liquido"),
        "employment_type": recibo_data.get("tipo_contrato"),
        "employer_name": recibo_data.get("empresa"),
        "efetivo": "sim" if recibo_data.get("tipo_contrato", "").lower() == "efetivo" else "nao",
    }


def map_irs_to_financial_data(irs_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map extracted IRS data to financial_data format."""
    annual_income = irs_data.get("rendimento_liquido_anual") or irs_data.get("rendimento_bruto_anual")
    monthly_income = annual_income / 14 if annual_income else None  # 14 months in Portugal
    
    return {
        "monthly_income": round(monthly_income, 2) if monthly_income else None,
        "annual_income": annual_income,
    }
