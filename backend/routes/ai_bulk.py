"""
Bulk AI Document Analysis Routes
Upload de documentos para análise com IA e preenchimento automático das fichas de clientes.

IMPORTANTE: Os ficheiros são processados um a um pelo frontend.
O endpoint /analyze-single recebe e processa um ficheiro de cada vez.

FUNCIONALIDADES:
- Normalização de nomes de ficheiros
- Junção de CC frente+verso num único PDF para análise
- Conversão de PDFs scan para imagem
- Detecção de documentos duplicados (evita reanalisar recibos/extratos iguais)
- Matching flexível de nomes (suporta acentos, parênteses, nomes compostos)

SEGURANÇA:
- Validação de ficheiros usando Magic Bytes (não confia na extensão)
- Whitelist de MIME types permitidos (PDF, JPEG, PNG, etc.)
- Bloqueio de ficheiros executáveis e scripts
"""
import os
import re
import uuid
import base64
import logging
import hashlib
import unicodedata
from typing import List, Optional, Dict, Tuple, Set
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel

from database import db
from models.auth import UserRole
from services.auth import require_roles, get_current_user
from services.file_validation import validate_file_content, validate_file_upload
from services.ai_document import (
    MAX_FILE_SIZE,
    detect_document_type,
    get_mime_type,
    validate_file_size,
    analyze_single_document,
    build_update_data_from_extraction,
    merge_images_to_pdf,
    analyze_document_from_base64
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai/bulk", tags=["AI Bulk Analysis"])

# Tamanho do chunk para leitura (64KB)
CHUNK_SIZE = 64 * 1024

# Nomes normalizados de documentos
NORMALIZED_NAMES = {
    "cc": "CC.pdf",
    "recibo_vencimento": "Recibo_Vencimento.pdf",
    "irs": "IRS.pdf",
    "contrato_trabalho": "Contrato_Trabalho.pdf",
    "caderneta_predial": "Caderneta_Predial.pdf",
    "extrato_bancario": "Extrato_Bancario.pdf",
    "outro": "Documento.pdf"
}

# Cache temporário para CC frente/verso por cliente
# Estrutura: {process_id: {"frente": (bytes, mime), "verso": (bytes, mime)}}
cc_cache: Dict[str, Dict[str, Tuple[bytes, str]]] = {}

# Cache para hashes de documentos já analisados (evitar duplicados)
# Estrutura: {process_id: {document_type: {hash: extracted_data}}}
document_hash_cache: Dict[str, Dict[str, Dict[str, dict]]] = {}

# Tipos de documentos que tipicamente vêm em múltiplas cópias idênticas
# Expandido para incluir mais tipos comuns
DUPLICATE_PRONE_TYPES = {
    "recibo_vencimento",  # Recibos de vencimento mensais
    "extrato_bancario",   # Extratos bancários
    "recibo",             # Recibos genéricos
    "irs",                # Declarações IRS (mesmo ano)
    "contrato_trabalho",  # Contratos de trabalho
    "certidao",           # Certidões
}


def normalize_text_for_matching(text: str) -> str:
    """
    Normaliza texto para comparação de nomes.
    Remove acentos, converte para minúsculas, remove caracteres especiais.
    """
    if not text:
        return ""
    
    # Remover acentos
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Converter para minúsculas
    text = text.lower()
    
    # Remover caracteres especiais exceto espaços
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Normalizar espaços
    text = ' '.join(text.split())
    
    return text


def extract_all_names_from_string(text: str) -> Set[str]:
    """
    Extrai todos os nomes possíveis de uma string.
    Suporta formatos: "João e Maria", "João (Maria)", "João / Maria", "João, Maria"
    """
    names = set()
    if not text:
        return names
    
    # Extrair nomes de parênteses primeiro (ex: "Claúdia Batista (Edson)")
    parens_names = re.findall(r'\(([^)]+)\)', text)
    for name in parens_names:
        names.add(normalize_text_for_matching(name))
    
    # Remover conteúdo dos parênteses para processar o resto
    text_clean = re.sub(r'\([^)]+\)', '', text)
    text_clean = normalize_text_for_matching(text_clean)
    
    # Separar por delimitadores comuns
    separators = [' e ', ' / ', ', ', ' - ']
    parts = [text_clean]
    for sep in separators:
        new_parts = []
        for part in parts:
            new_parts.extend(part.split(sep))
        parts = new_parts
    
    for part in parts:
        part = part.strip()
        if part and len(part) > 2:
            names.add(part)
            # Adicionar também o primeiro nome
            first_name = part.split()[0] if part.split() else ""
            if first_name and len(first_name) > 2:
                names.add(first_name)
    
    return names


def calculate_document_hash(content: bytes) -> str:
    """Calcular hash MD5 do conteúdo do documento."""
    # CORREÇÃO DE SEGURANÇA: Adicionado usedforsecurity=False
    return hashlib.md5(content, usedforsecurity=False).hexdigest()


async def is_duplicate_document_db(process_id: str, document_type: str, doc_hash: str) -> Optional[dict]:
    """
    Verifica se o documento já foi analisado anteriormente (persistido na DB).
    
    Returns:
        Dados do documento se for duplicado, None caso contrário
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "analyzed_documents": 1}
    )
    
    if not process:
        return None
    
    analyzed_docs = process.get("analyzed_documents", [])
    
    for doc in analyzed_docs:
        if doc.get("hash") == doc_hash:
            logger.info(f"Documento duplicado detectado (DB): hash={doc_hash[:8]}... para {process_id}")
            return doc
        
        # Verificar também por tipo + mês de referência (para recibos do mesmo mês)
        if doc.get("document_type") == document_type:
            if document_type in ["recibo_vencimento", "extrato_bancario"]:
                # Se já existe um recibo/extrato do mesmo tipo, pode ser duplicado
                # (verificado pelo hash acima)
                pass
    
    return None


def is_duplicate_document(process_id: str, document_type: str, content: bytes) -> Optional[dict]:
    """
    Verifica se o documento é duplicado de um já analisado (cache em memória).
    
    Returns:
        Dados extraídos anteriormente se for duplicado, None caso contrário
    """
    if document_type not in DUPLICATE_PRONE_TYPES:
        return None
    
    doc_hash = calculate_document_hash(content)
    
    if process_id in document_hash_cache:
        if document_type in document_hash_cache[process_id]:
            if doc_hash in document_hash_cache[process_id][document_type]:
                logger.info(f"Documento duplicado detectado (cache): {document_type} para {process_id}")
                return document_hash_cache[process_id][document_type][doc_hash]
    
    return None


async def check_duplicate_comprehensive(process_id: str, document_type: str, content: bytes) -> Optional[dict]:
    """
    Verificação completa de duplicados: cache em memória + base de dados.
    
    Returns:
        Dados do documento se for duplicado, None caso contrário
    """
    if document_type not in DUPLICATE_PRONE_TYPES:
        return None
    
    doc_hash = calculate_document_hash(content)
    
    # 1. Verificar cache em memória (rápido)
    cached = is_duplicate_document(process_id, document_type, content)
    if cached:
        return cached
    
    # 2. Verificar base de dados (persistente)
    db_record = await is_duplicate_document_db(process_id, document_type, doc_hash)
    if db_record:
        return db_record
    
    return None


def cache_document_analysis(process_id: str, document_type: str, content: bytes, extracted_data: dict):
    """Guardar resultado da análise em cache de memória para detectar duplicados futuros."""
    if document_type not in DUPLICATE_PRONE_TYPES:
        return
    
    doc_hash = calculate_document_hash(content)
    
    if process_id not in document_hash_cache:
        document_hash_cache[process_id] = {}
    if document_type not in document_hash_cache[process_id]:
        document_hash_cache[process_id][document_type] = {}
    
    document_hash_cache[process_id][document_type][doc_hash] = extracted_data


async def persist_document_analysis(process_id: str, document_type: str, content: bytes, extracted_data: dict, filename: str = ""):
    """
    Persistir registo de documento analisado na base de dados.
    Evita re-análise mesmo após reinício do servidor.
    """
    doc_hash = calculate_document_hash(content)
    
    # Extrair mês de referência se disponível (para recibos/extratos)
    mes_referencia = extracted_data.get("mes_referencia") or extracted_data.get("periodo") or ""
    
    doc_record = {
        "hash": doc_hash,
        "document_type": document_type,
        "filename": filename,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "mes_referencia": mes_referencia,
        "fields_extracted": list(extracted_data.keys()) if extracted_data else []
    }
    
    # Adicionar ao array analyzed_documents do processo
    await db.processes.update_one(
        {"id": process_id},
        {
            "$push": {"analyzed_documents": doc_record},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    logger.info(f"Documento persistido: {document_type} (hash={doc_hash[:8]}...) para {process_id}")


def validate_nif(nif: str) -> bool:
    """
    Valida se o NIF é válido para pessoa singular.
    NIFs de pessoas singulares começam por 1, 2, 6 ou 9.
    NIFs começados por 5 são de empresas/colectividades - REJEITADOS.
    """
    if not nif:
        return True  # Permitir vazio
    
    # Remover espaços e caracteres não numéricos
    nif = re.sub(r'\D', '', str(nif))
    
    if len(nif) != 9:
        return False
    
    # Rejeitar NIFs placeholder
    if nif in ['123456789', '000000000', '111111111', '999999999']:
        logger.warning(f"NIF {nif} é um placeholder - rejeitado")
        return False
    
    first_digit = nif[0]
    
    # 5 é para entidades colectivas - SEMPRE REJEITAR para clientes
    if first_digit == '5':
        logger.warning(f"NIF {nif} começa por 5 (entidade colectiva) - REJEITADO")
        return False
    
    # NIFs válidos para pessoas singulares: 1, 2, 6, 9
    if first_digit not in ['1', '2', '6', '9']:
        logger.warning(f"NIF {nif} tem primeiro dígito inválido: {first_digit}")
        return False
    
    return True


def is_placeholder_value(value: str) -> bool:
    """Verifica se um valor é um placeholder (não real)."""
    if not value:
        return False
    
    value_str = str(value).strip().upper()
    
    # Datas placeholder
    if value_str in ['YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY', 'N/A', 'NA', 'NULL', 'NONE', '']:
        return True
    
    # Valores numéricos placeholder
    if value_str in ['123456789', '000000000', '0', '00000000', '12345678']:
        return True
    
    # Se contém YYYY ou DD sem ser uma data real
    if 'YYYY' in value_str or value_str == 'DD':
        return True
    
    return False


def clean_extracted_value(value):
    """Limpa um valor extraído, removendo placeholders."""
    if value is None:
        return None
    
    if isinstance(value, str):
        if is_placeholder_value(value):
            return None
        return value.strip() if value.strip() else None
    
    return value


def is_cc_frente_or_verso(filename: str) -> Optional[str]:
    """
    Verificar se o ficheiro é frente ou verso do CC.
    
    Returns:
        "frente", "verso" ou None
    """
    filename_lower = filename.lower()
    
    # Padrões para frente
    frente_patterns = ["frente", "front", "_f.", "_f_", "cc_1", "cc1", "ccf"]
    for p in frente_patterns:
        if p in filename_lower:
            return "frente"
    
    # Padrões para verso
    verso_patterns = ["verso", "back", "tras", "_v.", "_v_", "cc_2", "cc2", "ccv"]
    for p in verso_patterns:
        if p in filename_lower:
            return "verso"
    
    return None


def get_normalized_filename(document_type: str) -> str:
    """Obter nome normalizado para o tipo de documento."""
    return NORMALIZED_NAMES.get(document_type, NORMALIZED_NAMES["outro"])


class SingleAnalysisResult(BaseModel):
    success: bool
    client_name: str
    filename: str
    document_type: str = ""
    fields_extracted: List[str] = []
    updated: bool = False
    error: Optional[str] = None


async def find_client_by_name(client_name: str) -> Optional[dict]:
    """
    Encontrar cliente pelo nome (busca flexível).
    
    Suporta:
    - Nomes com/sem acentos: "Cláudia" encontra "Claudia"
    - Nomes compostos: "João e Maria", "João (Maria)", "João / Maria"
    - Nomes parciais: pasta "João" encontra cliente "João e Maria"
    - Nomes entre parênteses: "Claúdia Batista (Edson)" é encontrado por "Edson"
    """
    if not client_name:
        return None
    
    client_name = client_name.strip()
    client_name_normalized = normalize_text_for_matching(client_name)
    client_names = extract_all_names_from_string(client_name)
    
    logger.info(f"Procurando cliente: '{client_name}' | Normalizado: '{client_name_normalized}' | Nomes extraídos: {client_names}")
    
    # 1. Busca exacta (com acentos)
    process = await db.processes.find_one(
        {"client_name": client_name},
        {"_id": 0}
    )
    if process:
        logger.info(f"Cliente encontrado (exacto): {process.get('client_name')}")
        return process
    
    # 2. Busca case-insensitive exacta
    process = await db.processes.find_one(
        {"client_name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}},
        {"_id": 0}
    )
    if process:
        logger.info(f"Cliente encontrado (case-insensitive): {process.get('client_name')}")
        return process
    
    # 3. Buscar todos os processos e fazer matching flexível
    all_processes = await db.processes.find(
        {},
        {"_id": 0, "id": 1, "client_name": 1}
    ).to_list(length=None)
    
    best_match = None
    best_score = 0
    
    for proc in all_processes:
        proc_name = proc.get("client_name", "")
        proc_name_normalized = normalize_text_for_matching(proc_name)
        proc_names = extract_all_names_from_string(proc_name)
        
        score = 0
        
        # Match exacto normalizado (sem acentos)
        if client_name_normalized == proc_name_normalized:
            score = 100
        
        # Match parcial - nome da pasta contido no nome do cliente
        elif client_name_normalized in proc_name_normalized:
            score = 80
        
        # Match parcial inverso - nome do cliente contido no nome da pasta
        elif proc_name_normalized in client_name_normalized:
            score = 75
        
        # Match de nomes individuais
        else:
            # Verificar se algum nome da pasta está no cliente
            common_names = client_names & proc_names
            if common_names:
                # Quanto mais nomes em comum, maior o score
                score = 50 + (len(common_names) * 10)
            else:
                # Verificar substrings (primeiro nome)
                for cn in client_names:
                    for pn in proc_names:
                        if cn and pn and len(cn) > 2 and len(pn) > 2:
                            if cn in pn or pn in cn:
                                score = max(score, 40)
        
        if score > best_score:
            best_score = score
            best_match = proc
            logger.debug(f"Novo melhor match: '{proc_name}' com score {score}")
    
    if best_match and best_score >= 40:
        # Buscar documento completo
        full_process = await db.processes.find_one(
            {"id": best_match["id"]},
            {"_id": 0}
        )
        if full_process:
            logger.info(f"Cliente encontrado (fuzzy, score={best_score}): '{best_match.get('client_name')}' para '{client_name}'")
            return full_process
    
    logger.warning(f"Cliente não encontrado: '{client_name}' (melhor score: {best_score})")
    return None


async def read_file_with_limit(file: UploadFile) -> bytes:
    """
    Ler ficheiro com limite de tamanho.
    Lê em chunks para não sobrecarregar a memória.
    """
    chunks = []
    total_size = 0
    
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise ValueError(f"Ficheiro excede o limite de {MAX_FILE_SIZE // (1024*1024)}MB")
        
        chunks.append(chunk)
    
    return b''.join(chunks)


async def update_client_data(process_id: str, extracted_data: dict, document_type: str) -> Tuple[bool, List[str]]:
    """
    Actualizar ficha do cliente com dados extraídos.
    
    Returns:
        Tuple de (success, list of updated fields)
    """
    updated_fields = []
    
    try:
        logger.info(f"update_client_data: process_id={process_id}, document_type={document_type}")
        logger.info(f"extracted_data: {list(extracted_data.keys())}")
        
        # Validar NIF antes de guardar
        nif = extracted_data.get('nif') or extracted_data.get('NIF')
        if nif and not validate_nif(nif):
            logger.warning(f"NIF inválido rejeitado: {nif}")
            if 'nif' in extracted_data:
                del extracted_data['nif']
            if 'NIF' in extracted_data:
                del extracted_data['NIF']
        
        # Obter dados existentes (incluindo novos campos do CPCV)
        process = await db.processes.find_one(
            {"id": process_id},
            {"_id": 0, "personal_data": 1, "financial_data": 1, "real_estate_data": 1, 
             "ai_extracted_notes": 1, "client_name": 1, "co_buyers": 1, "co_applicants": 1,
             "vendedor": 1, "mediador": 1}
        )
        
        if not process:
            logger.error(f"Processo não encontrado: {process_id}")
            return False, []
        
        # Construir dados de actualização
        update_data = build_update_data_from_extraction(
            extracted_data,
            document_type,
            process or {}
        )
        
        # Identificar campos que serão actualizados
        for key, value in update_data.items():
            if key != "updated_at" and value:
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        if subvalue:
                            updated_fields.append(f"{key}.{subkey}")
                elif isinstance(value, list):
                    updated_fields.append(f"{key} ({len(value)} items)")
                else:
                    updated_fields.append(key)
        
        logger.info(f"Campos a actualizar: {updated_fields}")
        
        # Aplicar actualização
        if len(update_data) > 1:
            result = await db.processes.update_one(
                {"id": process_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Cliente '{process.get('client_name')}' actualizado com sucesso! Campos: {updated_fields}")
                return True, updated_fields
            else:
                # Verificar se os dados já eram iguais
                logger.info("Nenhuma alteração necessária (dados já existentes)")
                return True, updated_fields
        else:
            logger.warning(f"Nenhum dado para actualizar (update_data tem apenas {len(update_data)} campos)")
        
        return False, []
        
    except Exception as e:
        logger.error(f"Erro ao actualizar cliente {process_id}: {e}", exc_info=True)
        return False, []


@router.post("/analyze-single", response_model=SingleAnalysisResult)
async def analyze_single_file(
    file: UploadFile = File(...),
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Analisar um único ficheiro.
    
    O frontend envia um ficheiro de cada vez, evitando problemas de memória
    e ficheiros fechados prematuramente pelo browser.
    
    FUNCIONALIDADES:
    - Se detectar CC frente ou verso, guarda em cache e espera pelo outro
    - Quando tem frente+verso, junta num PDF e analisa
    - Normaliza nomes de ficheiros
    - Detecta documentos duplicados (ex: 3 recibos de vencimento iguais)
    - Validação melhorada de NIF
    
    Estrutura do path: PastaRaiz/NomeCliente/[subpastas/]documento.pdf
    """
    filename = file.filename or "documento.pdf"
    
    # Extrair nome do cliente do path
    parts = filename.replace("\\", "/").split("/")
    
    if len(parts) >= 2:
        client_name = parts[1]
        doc_filename = parts[-1]
    else:
        doc_filename = parts[0]
        if "_" in doc_filename:
            client_name = doc_filename.rsplit("_", 1)[0]
        else:
            client_name = "Desconhecido"
    
    result = SingleAnalysisResult(
        success=False,
        client_name=client_name,
        filename=doc_filename
    )
    
    try:
        # Ler ficheiro imediatamente
        content = await read_file_with_limit(file)
        
        # ================================================================
        # VALIDAÇÃO DE SEGURANÇA - Magic Bytes
        # Verifica se o conteúdo real corresponde a um tipo permitido
        # ================================================================
        try:
            validate_file_content(content, doc_filename)
        except HTTPException as security_error:
            logger.warning(f"[SECURITY] Ficheiro rejeitado: {filename} - {security_error.detail}")
            result.error = f"Ficheiro rejeitado: {security_error.detail}"
            return result
        
        mime_type = get_mime_type(doc_filename)
        
        # Procurar cliente
        process = await find_client_by_name(client_name)
        if not process:
            result.error = f"Cliente não encontrado: {client_name}. Verifique se o nome está correcto (acentos, parênteses)."
            logger.warning(f"Cliente não encontrado para '{client_name}'. Pasta: {filename}")
            return result
        
        process_id = process.get("id")
        actual_client_name = process.get("client_name", client_name)
        result.client_name = actual_client_name  # Usar nome real do cliente
        
        # Detectar tipo de documento
        document_type = detect_document_type(doc_filename)
        result.document_type = document_type
        
        # Verificar se é documento duplicado (cache + DB)
        duplicate_data = await check_duplicate_comprehensive(process_id, document_type, content)
        if duplicate_data:
            logger.info(f"Documento duplicado detectado para {actual_client_name}: {document_type}")
            result.success = True
            result.error = "Documento idêntico já analisado anteriormente (ignorado)"
            return result
        
        # Nome normalizado
        normalized_name = get_normalized_filename(document_type)
        
        # Verificar se é CC frente ou verso
        if document_type == "cc":
            cc_side = is_cc_frente_or_verso(doc_filename)
            
            if cc_side:
                # Guardar em cache
                if process_id not in cc_cache:
                    cc_cache[process_id] = {}
                
                cc_cache[process_id][cc_side] = (content, mime_type)
                logger.info(f"CC {cc_side} guardado em cache para {actual_client_name}")
                
                # Verificar se já temos frente E verso
                if "frente" in cc_cache[process_id] and "verso" in cc_cache[process_id]:
                    logger.info(f"CC completo (frente+verso) para {actual_client_name}, a juntar...")
                    
                    # Juntar frente e verso num PDF
                    frente_data = cc_cache[process_id]["frente"]
                    verso_data = cc_cache[process_id]["verso"]
                    
                    merged_pdf = merge_images_to_pdf([frente_data, verso_data])
                    
                    if merged_pdf:
                        # Analisar o PDF combinado
                        merged_base64 = base64.b64encode(merged_pdf).decode('utf-8')
                        
                        analysis_result = await analyze_document_from_base64(
                            merged_base64,
                            "application/pdf",
                            "cc"
                        )
                        
                        # Limpar cache
                        del cc_cache[process_id]
                        
                        if analysis_result.get("success") or analysis_result.get("extracted_data"):
                            result.success = True
                            result.fields_extracted = list(analysis_result.get("extracted_data", {}).keys())
                            result.filename = normalized_name
                            
                            # Persistir análise do CC na DB
                            await persist_document_analysis(
                                process_id,
                                "cc",
                                merged_pdf,
                                analysis_result.get("extracted_data", {}),
                                "CC_frente_verso.pdf"
                            )
                            
                            # Actualizar ficha do cliente
                            updated, fields = await update_client_data(
                                process_id,
                                analysis_result.get("extracted_data", {}),
                                document_type
                            )
                            result.updated = updated
                            
                            logger.info(f"CC (frente+verso) analisado para {actual_client_name}: {len(result.fields_extracted)} campos, actualizados: {fields}")
                        else:
                            result.error = analysis_result.get("error", "Erro na análise do CC combinado")
                    else:
                        result.error = "Erro ao juntar CC frente+verso"
                        del cc_cache[process_id]
                else:
                    # Ainda falta frente ou verso
                    result.success = True
                    result.filename = f"CC_{cc_side} (a aguardar {'verso' if cc_side == 'frente' else 'frente'})"
                    result.fields_extracted = []
                    logger.info(f"A aguardar {'verso' if cc_side == 'frente' else 'frente'} do CC para {actual_client_name}")
                
                return result
        
        # Análise normal (não é CC frente/verso)
        analysis_result = await analyze_single_document(
            content=content,
            filename=doc_filename,
            client_name=actual_client_name,
            process_id=process_id
        )
        
        if analysis_result.get("success") and analysis_result.get("extracted_data"):
            result.success = True
            result.fields_extracted = list(analysis_result["extracted_data"].keys())
            result.filename = normalized_name  # Nome normalizado
            
            # Guardar em cache (memória) para detectar duplicados durante a sessão
            cache_document_analysis(process_id, document_type, content, analysis_result["extracted_data"])
            
            # Persistir na DB para detectar duplicados após reinício
            await persist_document_analysis(
                process_id, 
                document_type, 
                content, 
                analysis_result["extracted_data"],
                doc_filename
            )
            
            # Actualizar ficha do cliente
            updated, fields = await update_client_data(
                process_id,
                analysis_result["extracted_data"],
                document_type
            )
            result.updated = updated
            
            logger.info(f"✅ {doc_filename} -> {normalized_name} para '{actual_client_name}': {len(result.fields_extracted)} campos extraídos, {len(fields)} actualizados")
        else:
            result.error = analysis_result.get("error", "Erro na análise")
            logger.warning(f"❌ Falha ao analisar {doc_filename}: {result.error}")
            
            # Guardar erro no log de importação
            await log_import_error(
                client_name=actual_client_name,
                process_id=process_id,
                filename=doc_filename,
                document_type=document_type,
                error=result.error,
                user_email=user.get("email")
            )
        
    except ValueError as e:
        result.error = str(e)
        await log_import_error(
            client_name=client_name,
            process_id=process_id if 'process_id' in dir() else None,
            filename=doc_filename,
            document_type=document_type if 'document_type' in dir() else "desconhecido",
            error=str(e),
            user_email=user.get("email")
        )
    except Exception as e:
        result.error = f"Erro inesperado: {str(e)}"
        logger.error(f"Erro ao processar {filename}: {e}", exc_info=True)
        await log_import_error(
            client_name=client_name,
            process_id=process_id if 'process_id' in dir() else None,
            filename=doc_filename,
            document_type=document_type if 'document_type' in dir() else "desconhecido",
            error=str(e),
            user_email=user.get("email")
        )
    
    return result


async def log_import_error(
    client_name: str,
    process_id: Optional[str],
    filename: str,
    document_type: str,
    error: str,
    user_email: str = None
):
    """
    Guardar erro de importação na base de dados para análise posterior.
    """
    try:
        error_log = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "client_name": client_name,
            "process_id": process_id,
            "filename": filename,
            "document_type": document_type,
            "error": error,
            "user_email": user_email,
            "resolved": False
        }
        
        await db.import_errors.insert_one(error_log)
        logger.info(f"Erro de importação registado: {filename} -> {error[:50]}...")
        
    except Exception as e:
        logger.error(f"Falha ao registar erro de importação: {e}")


@router.get("/import-errors")
async def get_import_errors(
    limit: int = 100,
    document_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obter lista de erros de importação para análise.
    
    Parâmetros:
    - limit: Número máximo de erros a retornar (default 100)
    - document_type: Filtrar por tipo de documento
    - resolved: Filtrar por estado (True=resolvidos, False=pendentes)
    """
    query = {}
    
    if document_type:
        query["document_type"] = document_type
    if resolved is not None:
        query["resolved"] = resolved
    
    errors = await db.import_errors.find(
        query,
        {"_id": 0}
    ).sort("timestamp", -1).to_list(length=limit)
    
    # Agrupar por tipo de erro para análise
    error_summary = {}
    for err in errors:
        error_key = err.get("error", "Desconhecido")[:100]  # Truncar para agrupar
        if error_key not in error_summary:
            error_summary[error_key] = {
                "count": 0,
                "document_types": set(),
                "clients": set()
            }
        error_summary[error_key]["count"] += 1
        error_summary[error_key]["document_types"].add(err.get("document_type", "?"))
        error_summary[error_key]["clients"].add(err.get("client_name", "?"))
    
    # Converter sets para listas
    for key in error_summary:
        error_summary[key]["document_types"] = list(error_summary[key]["document_types"])
        error_summary[key]["clients"] = list(error_summary[key]["clients"])[:5]  # Limitar a 5 exemplos
    
    return {
        "total_errors": len(errors),
        "errors": errors,
        "summary": error_summary
    }


@router.get("/import-errors/summary")
async def get_import_errors_summary(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Obter resumo estatístico dos erros de importação.
    Útil para identificar padrões e áreas de melhoria.
    """
    # Agregação por tipo de documento
    pipeline_by_type = [
        {"$group": {"_id": "$document_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    # Agregação por erro (primeiros 50 caracteres)
    pipeline_by_error = [
        {"$project": {
            "error_prefix": {"$substr": ["$error", 0, 80]},
            "document_type": 1
        }},
        {"$group": {"_id": "$error_prefix", "count": {"$sum": 1}, "types": {"$addToSet": "$document_type"}}},
        {"$sort": {"count": -1}},
        {"$limit": 20}
    ]
    
    # Agregação temporal (últimas 24h, 7 dias, 30 dias)
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    
    errors_24h = await db.import_errors.count_documents({
        "timestamp": {"$gte": (now - timedelta(hours=24)).isoformat()}
    })
    errors_7d = await db.import_errors.count_documents({
        "timestamp": {"$gte": (now - timedelta(days=7)).isoformat()}
    })
    errors_30d = await db.import_errors.count_documents({
        "timestamp": {"$gte": (now - timedelta(days=30)).isoformat()}
    })
    total_errors = await db.import_errors.count_documents({})
    unresolved = await db.import_errors.count_documents({"resolved": False})
    
    by_type_cursor = db.import_errors.aggregate(pipeline_by_type)
    by_type = [doc async for doc in by_type_cursor]
    
    by_error_cursor = db.import_errors.aggregate(pipeline_by_error)
    by_error = [doc async for doc in by_error_cursor]
    
    return {
        "total_errors": total_errors,
        "unresolved": unresolved,
        "temporal": {
            "last_24h": errors_24h,
            "last_7d": errors_7d,
            "last_30d": errors_30d
        },
        "by_document_type": [{"type": d["_id"], "count": d["count"]} for d in by_type],
        "top_errors": [{"error": d["_id"], "count": d["count"], "types": d["types"]} for d in by_error]
    }


@router.post("/import-errors/{error_id}/resolve")
async def resolve_import_error(
    error_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Marcar um erro de importação como resolvido."""
    result = await db.import_errors.update_one(
        {"id": error_id},
        {"$set": {"resolved": True, "resolved_by": user.get("email"), "resolved_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count > 0:
        return {"success": True, "message": "Erro marcado como resolvido"}
    else:
        return {"success": False, "message": "Erro não encontrado"}


@router.delete("/import-errors/clear")
async def clear_import_errors(
    older_than_days: int = 30,
    only_resolved: bool = True,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Limpar erros de importação antigos.
    
    Parâmetros:
    - older_than_days: Limpar erros mais antigos que X dias (default 30)
    - only_resolved: Se True, limpa apenas erros resolvidos (default True)
    """
    from datetime import timedelta
    
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
    
    query = {"timestamp": {"$lt": cutoff_date}}
    if only_resolved:
        query["resolved"] = True
    
    result = await db.import_errors.delete_many(query)
    
    return {
        "success": True,
        "deleted_count": result.deleted_count,
        "message": f"{result.deleted_count} erros removidos (anteriores a {older_than_days} dias)"
    }


@router.get("/check-client")
async def check_client_exists(
    name: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Verificar se um cliente existe pelo nome.
    Usado para validar antes de processar ficheiros.
    """
    if not name:
        return {"exists": False, "client": None}
    
    process = await find_client_by_name(name)
    
    if process:
        return {
            "exists": True,
            "client": {
                "id": process.get("id"),
                "name": process.get("client_name"),
                "number": process.get("process_number")
            }
        }
    
    return {"exists": False, "client": None}


@router.get("/clients-list")
async def get_clients_list(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Obter lista de clientes para referência no upload."""
    clients = await db.processes.find(
        {},
        {"_id": 0, "id": 1, "client_name": 1, "process_number": 1}
    ).sort("client_name", 1).to_list(None)
    
    return {
        "total": len(clients),
        "clients": [
            {
                "id": c.get("id"),
                "name": c.get("client_name"),
                "number": c.get("process_number")
            }
            for c in clients
        ]
    }



@router.get("/diagnose-client/{client_name}")
async def diagnose_client_data(
    client_name: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Diagnóstico de dados de um cliente.
    Mostra quais campos estão preenchidos e quais estão vazios.
    Inclui co-compradores/co-proponentes se existirem.
    """
    process = await find_client_by_name(client_name)
    
    if not process:
        return {
            "found": False,
            "error": f"Cliente '{client_name}' não encontrado"
        }
    
    # Verificar campos preenchidos
    personal = process.get("personal_data", {})
    financial = process.get("financial_data", {})
    real_estate = process.get("real_estate_data", {})
    
    def count_filled(data: dict) -> Tuple[int, int, list]:
        if not data:
            return 0, 0, []
        filled = [(k, v) for k, v in data.items() if v is not None and v != ""]
        return len(filled), len(data), [k for k, _ in filled]
    
    personal_filled, personal_total, personal_fields = count_filled(personal)
    financial_filled, financial_total, financial_fields = count_filled(financial)
    real_estate_filled, real_estate_total, real_estate_fields = count_filled(real_estate)
    
    # Verificar co-compradores/co-proponentes
    co_buyers = process.get("co_buyers", [])
    co_applicants = process.get("co_applicants", [])
    
    result = {
        "found": True,
        "client_name": process.get("client_name"),
        "process_id": process.get("id"),
        "summary": {
            "personal_data": f"{personal_filled}/{personal_total} campos",
            "financial_data": f"{financial_filled}/{financial_total} campos",
            "real_estate_data": f"{real_estate_filled}/{real_estate_total} campos",
        },
        "filled_fields": {
            "personal": personal_fields,
            "financial": financial_fields,
            "real_estate": real_estate_fields,
        },
        "raw_data": {
            "email": process.get("client_email"),
            "phone": process.get("client_phone"),
            "personal_data": personal,
            "financial_data": financial,
        },
        "analyzed_documents": process.get("analyzed_documents", [])
    }
    
    # Adicionar co-compradores se existirem
    if co_buyers:
        result["co_buyers"] = co_buyers
        result["summary"]["co_buyers"] = f"{len(co_buyers)} pessoa(s)"
    
    if co_applicants:
        result["co_applicants"] = co_applicants
        result["summary"]["co_applicants"] = f"{len(co_applicants)} pessoa(s)"
    
    return result


@router.get("/analyzed-documents/{process_id}")
async def get_analyzed_documents(
    process_id: str,
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """
    Listar documentos já analisados para um processo.
    Útil para verificar quais documentos não precisam ser re-analisados.
    """
    process = await db.processes.find_one(
        {"id": process_id},
        {"_id": 0, "client_name": 1, "analyzed_documents": 1}
    )
    
    if not process:
        return {"found": False, "error": "Processo não encontrado"}
    
    analyzed_docs = process.get("analyzed_documents", [])
    
    # Agrupar por tipo de documento
    by_type = {}
    for doc in analyzed_docs:
        doc_type = doc.get("document_type", "outro")
        if doc_type not in by_type:
            by_type[doc_type] = []
        by_type[doc_type].append({
            "filename": doc.get("filename"),
            "analyzed_at": doc.get("analyzed_at"),
            "mes_referencia": doc.get("mes_referencia"),
            "fields_extracted": len(doc.get("fields_extracted", []))
        })
    
    return {
        "found": True,
        "client_name": process.get("client_name"),
        "total_documents": len(analyzed_docs),
        "by_type": by_type
    }


@router.post("/clear-duplicate-cache")
async def clear_duplicate_cache(
    user: dict = Depends(require_roles([UserRole.ADMIN]))
):
    """Limpar cache de documentos duplicados."""
    global document_hash_cache
    count = sum(
        sum(len(hashes) for hashes in types.values())
        for types in document_hash_cache.values()
    )
    document_hash_cache = {}
    return {"message": f"Cache limpo. {count} documentos removidos do cache."}