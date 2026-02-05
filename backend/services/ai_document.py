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
5. Processamento paralelo com asyncio.gather para bulk analysis
6. Validação de tamanho de ficheiro antes de carregar para memória

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
import asyncio
import httpx
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timezone

from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

load_dotenv()

logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

# Modelo a usar - gpt-4o-mini é mais barato e rápido
AI_MODEL = "gpt-4o-mini"

# Mínimo de caracteres para considerar extracção de texto bem sucedida
MIN_TEXT_LENGTH = 100

# Tamanho máximo de imagem (lado maior)
MAX_IMAGE_SIZE = 1024

# Tamanho máximo de ficheiro (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# Número máximo de ficheiros a processar em paralelo
MAX_CONCURRENT_ANALYSIS = 5

# Configuração de retry para erros 429 (rate limit)
RETRY_MAX_ATTEMPTS = 5
RETRY_MIN_WAIT = 2  # segundos
RETRY_MAX_WAIT = 32  # segundos


class RateLimitError(Exception):
    """Excepção para erros de rate limit (429)."""
    pass


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


def convert_pdf_to_image(pdf_content: bytes, page_num: int = 0, dpi: int = 150) -> Tuple[Optional[bytes], str]:
    """
    Converter uma página de PDF para imagem usando PyMuPDF.
    Útil para PDFs que são scans/imagens e não têm texto extraível.
    
    Args:
        pdf_content: Conteúdo do PDF em bytes
        page_num: Número da página a converter (0 = primeira)
        dpi: Resolução da imagem (150 é bom equilíbrio qualidade/tamanho)
    
    Returns:
        Tuple (bytes da imagem PNG, mime_type) ou (None, "") se falhar
    """
    try:
        import fitz  # PyMuPDF
        
        # Abrir PDF
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        if page_num >= len(doc):
            page_num = 0
        
        page = doc[page_num]
        
        # Converter para imagem com resolução especificada
        # Matrix para controlar DPI (default é 72)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        
        # Renderizar página como pixmap
        pix = page.get_pixmap(matrix=mat)
        
        # Converter para PNG
        img_bytes = pix.tobytes("png")
        
        doc.close()
        
        logger.info(f"PDF convertido para imagem: página {page_num}, {len(img_bytes)} bytes")
        return img_bytes, "image/png"
        
    except Exception as e:
        logger.error(f"Erro ao converter PDF para imagem: {e}")
        return None, ""


def merge_images_to_pdf(images_data: List[Tuple[bytes, str]]) -> Optional[bytes]:
    """
    Juntar múltiplas imagens num único PDF.
    Útil para juntar CC frente e verso.
    
    Args:
        images_data: Lista de tuples (bytes da imagem, mime_type)
    
    Returns:
        Bytes do PDF resultante ou None se falhar
    """
    try:
        import img2pdf
        from PIL import Image
        
        # Converter todas as imagens para formato compatível
        image_bytes_list = []
        
        for img_bytes, mime_type in images_data:
            # Abrir imagem com PIL para garantir formato correcto
            img = Image.open(io.BytesIO(img_bytes))
            
            # Converter para RGB se necessário (img2pdf não suporta RGBA)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Guardar como JPEG em memória
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=90)
            image_bytes_list.append(output.getvalue())
        
        # Criar PDF com todas as imagens
        pdf_bytes = img2pdf.convert(image_bytes_list)
        
        logger.info(f"Criado PDF com {len(images_data)} imagens: {len(pdf_bytes)} bytes")
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Erro ao criar PDF a partir de imagens: {e}")
        return None


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


@retry(
    stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(RateLimitError),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def call_openai_api(payload: dict, timeout: float = 60.0) -> dict:
    """
    Chamar API do OpenAI com retry automático para erros 429.
    
    Usa exponential backoff: 2s, 4s, 8s, 16s, 32s
    Máximo 5 tentativas antes de desistir.
    
    Args:
        payload: Payload JSON para enviar
        timeout: Timeout em segundos
    
    Returns:
        Resposta JSON da API
    
    Raises:
        RateLimitError: Se receber 429 (será tentado novamente)
        Exception: Outros erros
    """
    headers = {
        "Authorization": f"Bearer {EMERGENT_LLM_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        # Verificar rate limit
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "2")
            logger.warning(f"Rate limit atingido (429). Retry-After: {retry_after}s")
            raise RateLimitError(f"Rate limit atingido. Retry-After: {retry_after}s")
        
        response.raise_for_status()
        return response.json()


async def analyze_with_text(text: str, document_type: str) -> Dict[str, Any]:
    """
    Analisar documento usando apenas texto (sem visão).
    Mais rápido e barato que usar modelo de visão.
    
    Inclui retry automático para erros 429 (rate limit).
    
    Args:
        text: Texto extraído do documento
        document_type: Tipo de documento
    
    Returns:
        Dados extraídos
    """
    system_prompt, user_prompt = get_extraction_prompts(document_type)
    
    try:
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
            "temperature": 0.1
        }
        
        result = await call_openai_api(payload, timeout=60.0)
        
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
        
    except RateLimitError as e:
        logger.error(f"Rate limit excedido após {RETRY_MAX_ATTEMPTS} tentativas: {e}")
        return {
            "success": False,
            "error": f"Limite de pedidos excedido. Tente novamente mais tarde.",
            "extracted_data": {}
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
    
    Inclui retry automático para erros 429 (rate limit).
    
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
                            "detail": "low"
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
        
        result = await call_openai_api(payload, timeout=90.0)
        
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
        
    except RateLimitError as e:
        logger.error(f"Rate limit excedido após {RETRY_MAX_ATTEMPTS} tentativas: {e}")
        return {
            "success": False,
            "error": f"Limite de pedidos excedido. Tente novamente mais tarde.",
            "extracted_data": {}
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
    3. Se não, converte PDF para imagem e usa modelo de visão
    
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
            # PDF sem texto (provavelmente scan/imagem) - converter para imagem
            logger.info(f"Texto insuficiente ({len(extracted_text)} chars), convertendo PDF para imagem...")
            
            img_bytes, img_mime = convert_pdf_to_image(content_bytes, page_num=0, dpi=200)
            
            if img_bytes:
                # Usar a imagem convertida para análise de visão
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                logger.info("PDF convertido para imagem, usando modelo de visão")
                return await analyze_with_vision(img_base64, img_mime, document_type)
            else:
                logger.warning("Falha ao converter PDF para imagem, tentando com PDF original")
    
    # Usar modelo de visão com o conteúdo original
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


# ====================================================================
# BULK ANALYSIS SERVICE FUNCTIONS
# ====================================================================

def detect_document_type(filename: str) -> str:
    """Detectar tipo de documento pelo nome do ficheiro."""
    filename_lower = filename.lower()
    
    if any(x in filename_lower for x in ['cc', 'cartao', 'cidadao', 'identificacao', 'bi']):
        return 'cc'
    elif any(x in filename_lower for x in ['recibo', 'vencimento', 'salario', 'ordenado']):
        return 'recibo_vencimento'
    elif any(x in filename_lower for x in ['irs', 'declaracao', 'imposto']):
        return 'irs'
    elif any(x in filename_lower for x in ['contrato', 'trabalho']):
        return 'contrato_trabalho'
    elif any(x in filename_lower for x in ['caderneta', 'predial', 'imovel']):
        return 'caderneta_predial'
    elif any(x in filename_lower for x in ['extrato', 'bancario', 'banco']):
        return 'extrato_bancario'
    else:
        return 'outro'


def get_mime_type(filename: str) -> str:
    """Obter MIME type pelo nome do ficheiro."""
    ext = filename.lower().split('.')[-1]
    mime_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'webp': 'image/webp',
    }
    return mime_types.get(ext, 'application/octet-stream')


def validate_file_size(content: bytes, filename: str) -> Tuple[bool, str]:
    """
    Validar tamanho do ficheiro.
    
    Returns:
        Tuple (is_valid, error_message)
    """
    size = len(content)
    if size > MAX_FILE_SIZE:
        size_mb = size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return False, f"Ficheiro {filename} excede o limite de {max_mb}MB ({size_mb:.1f}MB)"
    return True, ""


async def analyze_single_document(
    content: bytes,
    filename: str,
    client_name: str,
    process_id: str
) -> Dict[str, Any]:
    """
    Analisar um único documento e retornar resultado.
    
    Args:
        content: Conteúdo do ficheiro em bytes
        filename: Nome do ficheiro
        client_name: Nome do cliente
        process_id: ID do processo
    
    Returns:
        Dict com resultado da análise
    """
    result = {
        "client_name": client_name,
        "filename": filename,
        "process_id": process_id,
        "success": False,
        "extracted_data": {},
        "document_type": "",
        "error": None,
        "updated": False
    }
    
    try:
        # Validar tamanho
        is_valid, error_msg = validate_file_size(content, filename)
        if not is_valid:
            result["error"] = error_msg
            return result
        
        # Detectar tipo de documento e MIME type
        document_type = detect_document_type(filename)
        mime_type = get_mime_type(filename)
        result["document_type"] = document_type
        
        # Converter para base64
        base64_content = base64.b64encode(content).decode('utf-8')
        
        logger.info(f"Analisando {filename} ({document_type}) para {client_name}")
        
        # Analisar com IA
        analysis_result = await analyze_document_from_base64(
            base64_content,
            mime_type,
            document_type
        )
        
        if analysis_result.get("success") and analysis_result.get("extracted_data"):
            result["success"] = True
            result["extracted_data"] = analysis_result["extracted_data"]
            result["fields_extracted"] = list(analysis_result["extracted_data"].keys())
        else:
            result["error"] = analysis_result.get("error", "Erro desconhecido na análise")
            
    except Exception as e:
        logger.error(f"Erro ao analisar {filename}: {e}")
        result["error"] = str(e)
    
    return result


async def process_bulk_documents(
    files_data: List[Dict[str, Any]],
    progress_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Processar múltiplos documentos em paralelo.
    
    Args:
        files_data: Lista de dicts com {content, filename, client_name, process_id}
        progress_callback: Função opcional para reportar progresso
    
    Returns:
        Dict com resultados agregados
    """
    total_files = len(files_data)
    results = []
    errors = []
    processed = 0
    
    # Criar semáforo para limitar concorrência
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_ANALYSIS)
    
    async def analyze_with_semaphore(file_data: Dict) -> Dict:
        async with semaphore:
            result = await analyze_single_document(
                content=file_data["content"],
                filename=file_data["filename"],
                client_name=file_data["client_name"],
                process_id=file_data["process_id"]
            )
            
            # Reportar progresso se callback fornecido
            if progress_callback:
                await progress_callback(file_data["filename"], result["success"])
            
            return result
    
    # Processar todos em paralelo (limitado pelo semáforo)
    tasks = [analyze_with_semaphore(fd) for fd in files_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Processar resultados
    successful_results = []
    for r in results:
        if isinstance(r, Exception):
            errors.append(str(r))
        elif isinstance(r, dict):
            successful_results.append(r)
            if r.get("success"):
                processed += 1
            if r.get("error"):
                errors.append(f"{r.get('client_name', '?')}/{r.get('filename', '?')}: {r['error']}")
    
    return {
        "success": processed > 0,
        "total_files": total_files,
        "processed": processed,
        "errors": errors,
        "results": successful_results
    }


def build_update_data_from_extraction(
    extracted_data: Dict[str, Any],
    document_type: str,
    existing_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Construir dados de actualização a partir dos dados extraídos.
    
    Args:
        extracted_data: Dados extraídos pela IA
        document_type: Tipo de documento
        existing_data: Dados existentes do processo (para merge)
    
    Returns:
        Dict com campos a actualizar no processo
    """
    if existing_data is None:
        existing_data = {}
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if document_type == 'cc':
        # Dados pessoais
        personal_update = {}
        field_mapping = {
            'nif': 'nif',
            'numero_documento': 'documento_id',
            'data_nascimento': 'data_nascimento',
            'naturalidade': 'naturalidade',
            'nacionalidade': 'nacionalidade',
            'sexo': 'sexo',
            'morada': 'morada',
            'codigo_postal': 'codigo_postal',
            'pai': 'nome_pai',
            'mae': 'nome_mae',
        }
        
        for src_key, dest_key in field_mapping.items():
            if extracted_data.get(src_key):
                personal_update[dest_key] = extracted_data[src_key]
        
        if personal_update:
            existing_personal = existing_data.get("personal_data", {})
            existing_personal.update(personal_update)
            update_data["personal_data"] = existing_personal
        
        if extracted_data.get('email'):
            update_data["client_email"] = extracted_data['email']
            
    elif document_type in ['recibo_vencimento', 'irs']:
        # Dados financeiros
        financial_update = {}
        field_mapping = {
            'salario_liquido': 'rendimento_mensal',
            'rendimento_liquido_mensal': 'rendimento_mensal',
            'salario_bruto': 'rendimento_bruto',
            'empresa': 'empresa',
            'tipo_contrato': 'tipo_contrato',
            'categoria_profissional': 'categoria_profissional',
            'rendimento_liquido_anual': 'rendimento_anual',
        }
        
        for src_key, dest_key in field_mapping.items():
            if extracted_data.get(src_key):
                financial_update[dest_key] = extracted_data[src_key]
        
        if financial_update:
            existing_financial = existing_data.get("financial_data", {})
            existing_financial.update(financial_update)
            update_data["financial_data"] = existing_financial
            
    elif document_type == 'caderneta_predial':
        # Dados do imóvel
        real_estate_update = {}
        field_mapping = {
            'artigo_matricial': 'artigo_matricial',
            'valor_patrimonial_tributario': 'valor_patrimonial',
            'area_bruta': 'area',
            'localizacao': 'localizacao',
            'tipologia': 'tipologia',
        }
        
        for src_key, dest_key in field_mapping.items():
            if extracted_data.get(src_key):
                real_estate_update[dest_key] = extracted_data[src_key]
        
        if real_estate_update:
            existing_real_estate = existing_data.get("real_estate_data", {})
            existing_real_estate.update(real_estate_update)
            update_data["real_estate_data"] = existing_real_estate
    
    return update_data

