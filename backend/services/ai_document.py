"""
====================================================================
AI DOCUMENT ANALYSIS SERVICE - CREDITOIMO
====================================================================
Serviço de análise de documentos com IA (GPT-4o-mini).

OPTIMIZAÇÕES:
1. Tenta extrair texto do PDF com pypdf primeiro
2. Se conseguir texto suficiente, envia apenas texto (mais barato/rápido)
3. Só usa modelo de visão se extracção de texto falhar
4. Redimensiona imagens para max 1024px antes de enviar

Tipos de documentos suportados:
- CC (Cartão de Cidadão)
- Recibo de Vencimento
- IRS
- Outros
====================================================================
"""
import os
import io
import json
import logging
import base64
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Modelo a usar - gpt-4o-mini é mais barato e rápido
AI_MODEL = "gpt-4o-mini"

# Mínimo de caracteres para considerar extracção de texto bem sucedida
MIN_TEXT_LENGTH = 100

# Tamanho máximo de imagem (lado maior)
MAX_IMAGE_SIZE = 1024


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extrair texto de um PDF usando pypdf.
    
    Args:
        pdf_content: Conteúdo do PDF em bytes
    
    Returns:
        Texto extraído do PDF
    """
    try:
        from pypdf import PdfReader
        
        pdf_file = io.BytesIO(pdf_content)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        
        full_text = "\n".join(text_parts).strip()
        logger.info(f"PDF text extraction: {len(full_text)} caracteres extraídos")
        return full_text
        
    except Exception as e:
        logger.warning(f"Falha na extracção de texto do PDF: {e}")
        return ""


def resize_image_base64(base64_content: str, mime_type: str, max_size: int = MAX_IMAGE_SIZE) -> Tuple[str, str]:
    """
    Redimensionar imagem para ter no máximo max_size pixels no lado maior.
    
    Args:
        base64_content: Imagem em base64
        mime_type: Tipo MIME da imagem
        max_size: Tamanho máximo do lado maior
    
    Returns:
        Tuple (base64 redimensionado, novo mime_type)
    """
    try:
        from PIL import Image
        
        # Decodificar base64
        image_data = base64.b64decode(base64_content)
        image = Image.open(io.BytesIO(image_data))
        
        # Verificar se precisa redimensionar
        width, height = image.size
        
        if width <= max_size and height <= max_size:
            logger.info(f"Imagem já é pequena ({width}x{height}), não redimensionando")
            return base64_content, mime_type
        
        # Calcular novo tamanho mantendo proporção
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        
        # Redimensionar
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Converter para RGB se necessário (para JPEG)
        if resized.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', resized.size, (255, 255, 255))
            if resized.mode == 'P':
                resized = resized.convert('RGBA')
            background.paste(resized, mask=resized.split()[-1] if resized.mode == 'RGBA' else None)
            resized = background
        
        # Guardar em buffer
        buffer = io.BytesIO()
        resized.save(buffer, format='JPEG', quality=85, optimize=True)
        
        # Converter para base64
        new_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        original_size = len(base64_content)
        new_size = len(new_base64)
        logger.info(f"Imagem redimensionada: {width}x{height} -> {new_width}x{new_height}, "
                   f"tamanho: {original_size//1024}KB -> {new_size//1024}KB")
        
        return new_base64, "image/jpeg"
        
    except Exception as e:
        logger.warning(f"Falha ao redimensionar imagem: {e}")
        return base64_content, mime_type


async def analyze_with_text(text: str, document_type: str) -> Dict[str, Any]:
    """
    Analisar documento usando apenas texto (sem visão).
    Mais rápido e barato que usar modelo de visão.
    
    Args:
        text: Texto extraído do documento
        document_type: Tipo de documento
    
    Returns:
        Dados extraídos
    """
    system_prompt, user_prompt = get_extraction_prompts(document_type)
    
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {EMERGENT_LLM_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"{user_prompt}\n\n--- TEXTO DO DOCUMENTO ---\n{text}"
            }
        ]
        
        payload = {
            "model": AI_MODEL,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.1  # Baixa temperatura para respostas mais consistentes
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
            "analysis_method": "text",
            "model": AI_MODEL,
            "raw_response": ai_response
        }
        
    except Exception as e:
        logger.error(f"Erro na análise de texto: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {}
        }


async def analyze_with_vision(base64_content: str, mime_type: str, document_type: str) -> Dict[str, Any]:
    """
    Analisar documento usando modelo de visão.
    Usado quando extracção de texto não é possível.
    
    Args:
        base64_content: Imagem em base64
        mime_type: Tipo MIME
        document_type: Tipo de documento
    
    Returns:
        Dados extraídos
    """
    system_prompt, user_prompt = get_extraction_prompts(document_type)
    
    # Redimensionar imagem antes de enviar
    resized_base64, new_mime_type = resize_image_base64(base64_content, mime_type)
    
    try:
        import httpx
        
        headers = {
            "Authorization": f"Bearer {EMERGENT_LLM_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{new_mime_type};base64,{resized_base64}",
                            "detail": "low"  # Usar detalhe baixo para reduzir custos
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "model": AI_MODEL,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.1
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
            "analysis_method": "vision",
            "model": AI_MODEL,
            "raw_response": ai_response
        }
        
    except Exception as e:
        logger.error(f"Erro na análise com visão: {e}")
        return {
            "success": False,
            "error": str(e),
            "extracted_data": {}
        }


async def analyze_document_from_base64(base64_content: str, mime_type: str, document_type: str) -> Dict[str, Any]:
    """
    Analisar documento a partir de conteúdo base64.
    
    ESTRATÉGIA:
    1. Se for PDF, tenta extrair texto primeiro
    2. Se texto suficiente, usa análise de texto (mais barato)
    3. Se não, usa modelo de visão com imagem redimensionada
    
    Args:
        base64_content: Conteúdo em base64
        mime_type: Tipo MIME
        document_type: Tipo de documento
    
    Returns:
        Dados extraídos
    """
    if not EMERGENT_LLM_KEY:
        logger.error("EMERGENT_LLM_KEY não configurada")
        return {"error": "Serviço AI não configurado", "extracted_data": {}}
    
    # Decodificar base64
    try:
        content_bytes = base64.b64decode(base64_content)
    except Exception as e:
        logger.error(f"Erro ao decodificar base64: {e}")
        return {"error": "Base64 inválido", "extracted_data": {}}
    
    # Se for PDF, tentar extrair texto primeiro
    if mime_type == "application/pdf":
        logger.info("Documento PDF detectado, tentando extrair texto...")
        extracted_text = extract_text_from_pdf(content_bytes)
        
        if len(extracted_text) >= MIN_TEXT_LENGTH:
            logger.info(f"Texto suficiente extraído ({len(extracted_text)} chars), usando análise de texto")
            return await analyze_with_text(extracted_text, document_type)
        else:
            logger.info(f"Texto insuficiente ({len(extracted_text)} chars), usando modelo de visão")
    
    # Usar modelo de visão
    return await analyze_with_vision(base64_content, mime_type, document_type)


async def analyze_document_from_url(document_url: str, document_type: str) -> Dict[str, Any]:
    """
    Analisar documento a partir de URL.
    
    Args:
        document_url: URL do documento
        document_type: Tipo de documento
    
    Returns:
        Dados extraídos
    """
    if not EMERGENT_LLM_KEY:
        logger.error("EMERGENT_LLM_KEY não configurada")
        return {"error": "Serviço AI não configurado", "extracted_data": {}}
    
    try:
        import httpx
        
        # Download do documento
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(document_url)
            response.raise_for_status()
            content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")
        
        # Determinar MIME type
        if "pdf" in content_type.lower():
            mime_type = "application/pdf"
        elif "jpeg" in content_type.lower() or "jpg" in content_type.lower():
            mime_type = "image/jpeg"
        elif "png" in content_type.lower():
            mime_type = "image/png"
        else:
            mime_type = content_type.split(";")[0]
        
        # Converter para base64 e analisar
        base64_content = base64.b64encode(content).decode('utf-8')
        return await analyze_document_from_base64(base64_content, mime_type, document_type)
        
    except Exception as e:
        logger.error(f"Erro ao fazer download do documento: {e}")
        return {"success": False, "error": str(e), "extracted_data": {}}


def get_extraction_prompts(document_type: str) -> tuple:
    """Obter prompts de sistema e utilizador baseado no tipo de documento."""
    
    if document_type == "cc":
        system_prompt = """És um assistente especializado em extrair dados de documentos de identificação portugueses (Cartão de Cidadão).
        
Extraia TODOS os dados visíveis do documento e retorna em formato JSON estruturado.
Sê preciso com datas, números e nomes.
Se algum campo não for legível ou não existir, usa null."""
        
        user_prompt = """Analisa este Cartão de Cidadão português e extrai os seguintes dados em formato JSON:

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

Retorna APENAS o JSON, sem texto adicional."""

    elif document_type == "recibo_vencimento":
        system_prompt = """És um assistente especializado em extrair dados de recibos de vencimento portugueses.
        
Extrai TODOS os valores financeiros e dados do funcionário visíveis.
Valores monetários devem ser números decimais.
Se algum campo não for legível ou não existir, usa null."""
        
        user_prompt = """Analisa este recibo de vencimento e extrai os seguintes dados em formato JSON:

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

Retorna APENAS o JSON, sem texto adicional."""

    elif document_type == "irs":
        system_prompt = """És um assistente especializado em extrair dados de declarações de IRS portuguesas.
        
Extrai os dados fiscais principais visíveis no documento.
Valores monetários devem ser números decimais.
Se algum campo não for legível ou não existir, usa null."""
        
        user_prompt = """Analisa esta declaração de IRS e extrai os seguintes dados em formato JSON:

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

Retorna APENAS o JSON, sem texto adicional."""

    else:
        system_prompt = """És um assistente especializado em extrair dados de documentos.
Extrai todos os dados relevantes que encontrares no documento."""
        
        user_prompt = """Analisa este documento e extrai todos os dados relevantes em formato JSON estruturado.
Inclui nomes, datas, valores, números de identificação, e qualquer outra informação importante.
Retorna APENAS o JSON, sem texto adicional."""

    return system_prompt, user_prompt


def parse_ai_response(response: str, document_type: str) -> Dict[str, Any]:
    """Fazer parse da resposta da IA e extrair dados JSON."""
    
    try:
        response = response.strip()
        
        # Remover blocos de código markdown se presentes
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
        logger.warning(f"Falha ao fazer parse da resposta como JSON: {e}")
        return {"raw_text": response, "parse_error": str(e)}


def map_cc_to_personal_data(cc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mapear dados extraídos do CC para formato personal_data."""
    return {
        "nif": cc_data.get("nif"),
        "documento_id": cc_data.get("numero_documento"),
        "naturalidade": cc_data.get("naturalidade"),
        "nacionalidade": cc_data.get("nacionalidade"),
        "birth_date": cc_data.get("data_nascimento"),
    }


def map_recibo_to_financial_data(recibo_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mapear dados extraídos do recibo para formato financial_data."""
    return {
        "renda_habitacao_atual": recibo_data.get("salario_liquido"),
        "efetivo": "sim" if recibo_data.get("tipo_contrato", "").lower() == "efetivo" else "nao",
    }


def map_irs_to_financial_data(irs_data: Dict[str, Any]) -> Dict[str, Any]:
    """Mapear dados extraídos do IRS para formato financial_data."""
    annual_income = irs_data.get("rendimento_liquido_anual") or irs_data.get("rendimento_bruto_anual")
    monthly_income = annual_income / 14 if annual_income else None  # 14 meses em Portugal
    
    return {
        "renda_habitacao_atual": round(monthly_income, 2) if monthly_income else None,
    }
