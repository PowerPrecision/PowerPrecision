"""
====================================================================
ROTAS DE GESTÃO DE DOCUMENTOS - CREDITOIMO (S3 + VALIDADES)
====================================================================
Inclui:
- Upload com normalização automática de nomes
- Conversão automática de imagens para PDF
- Gestão de validades de documentos
- Categorização automática com IA
====================================================================
"""
import uuid
import logging
import re
import unicodedata
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from io import BytesIO

# Adicionados UploadFile, File, Form para o S3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks

from database import db
from models.auth import UserRole
from models.document import DocumentExpiryCreate, DocumentExpiryUpdate, DocumentExpiryResponse
from services.auth import get_current_user, require_roles

# Importar o novo serviço S3
from services.s3_storage import s3_service

# Importar serviço de processamento de documentos (conversão imagem → PDF)
from services.document_processor import convert_image_to_pdf, IMG2PDF_AVAILABLE

router = APIRouter(prefix="/documents", tags=["Document Management"])
logger = logging.getLogger(__name__)


# ====================================================================
# FUNÇÃO DE CATEGORIZAÇÃO AUTOMÁTICA EM BACKGROUND
# ====================================================================

async def auto_categorize_document_background(
    process_id: str,
    client_name: str,
    s3_path: str,
    filename: str,
    file_content: bytes
):
    """
    Categoriza um documento automaticamente em background após upload.
    Esta função é chamada de forma assíncrona para não bloquear o upload.
    """
    from services.document_categorization import extract_text_from_pdf, categorize_document_with_ai
    
    try:
        logger.info(f"[AUTO-CAT] Iniciando categorização automática para: {filename}")
        
        # Verificar se já existe metadados para este ficheiro
        existing = await db.document_metadata.find_one({"s3_path": s3_path}, {"_id": 0})
        
        # Extrair texto do documento
        extracted_text = ""
        if filename.lower().endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_content)
        
        # Se não conseguir extrair texto, usar apenas o nome do ficheiro
        text_for_analysis = extracted_text if extracted_text else f"Ficheiro: {filename}"
        
        # Obter categorias existentes para consistência
        existing_categories = await db.document_metadata.distinct("ai_category")
        
        # Categorizar com IA
        result = await categorize_document_with_ai(
            text_content=text_for_analysis,
            filename=filename,
            existing_categories=existing_categories
        )
        
        if not result.get("success"):
            logger.warning(f"[AUTO-CAT] Falha ao categorizar {filename}: {result.get('error')}")
            return
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Criar ou actualizar metadados
        doc_id = existing.get("id") if existing else str(uuid.uuid4())
        
        metadata = {
            "id": doc_id,
            "process_id": process_id,
            "client_name": client_name,
            "s3_path": s3_path,
            "filename": filename,
            "ai_category": result.get("category"),
            "ai_subcategory": result.get("subcategory"),
            "ai_confidence": result.get("confidence"),
            "ai_tags": result.get("tags", []),
            "ai_summary": result.get("summary"),
            "expiry_date": result.get("expiry_date"),  # Nova: data de validade
            "expiry_alert_sent": False,  # Nova: flag de alerta
            "extracted_text": extracted_text[:5000] if extracted_text else None,
            "file_size": len(file_content),
            "mime_type": "application/pdf" if filename.lower().endswith('.pdf') else None,
            "is_categorized": True,
            "categorized_at": now,
            "updated_at": now
        }
        
        if existing:
            await db.document_metadata.update_one(
                {"id": doc_id},
                {"$set": metadata}
            )
            logger.info(f"[AUTO-CAT] Metadados actualizados para: {filename}")
        else:
            metadata["created_at"] = now
            await db.document_metadata.insert_one(metadata)
            logger.info(f"[AUTO-CAT] Metadados criados para: {filename}")
        
        logger.info(f"[AUTO-CAT] Categorização concluída: {filename} -> {result.get('category')}/{result.get('subcategory')}, expiry: {result.get('expiry_date')}")
        
    except Exception as e:
        logger.error(f"[AUTO-CAT] Erro ao categorizar {filename}: {e}")


# ====================================================================
# FUNÇÕES DE NORMALIZAÇÃO DE NOMES DE FICHEIROS
# ====================================================================

def normalize_filename(filename: str, category: str = None) -> str:
    """
    Normaliza o nome do ficheiro para um formato consistente.
    
    Formato: {Categoria}_{Data}_{NomeOriginalNormalizado}.{ext}
    
    Args:
        filename: Nome original do ficheiro
        category: Categoria do documento (opcional)
        
    Returns:
        Nome normalizado
    """
    if not filename:
        return f"documento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Separar nome e extensão
    if '.' in filename:
        name_part, ext = filename.rsplit('.', 1)
        ext = ext.lower()
    else:
        name_part = filename
        ext = 'pdf'
    
    # Normalizar texto (remover acentos)
    name_normalized = unicodedata.normalize('NFKD', name_part)
    name_normalized = name_normalized.encode('ASCII', 'ignore').decode('ASCII')
    
    # Substituir espaços e caracteres especiais
    name_normalized = re.sub(r'[^\w\s-]', '', name_normalized)
    name_normalized = re.sub(r'[\s_]+', '_', name_normalized.strip())
    name_normalized = name_normalized[:50] if name_normalized else "documento"
    
    # Construir nome final
    date_str = datetime.now().strftime('%Y%m%d')
    
    if category:
        # Normalizar categoria
        cat_normalized = unicodedata.normalize('NFKD', category)
        cat_normalized = cat_normalized.encode('ASCII', 'ignore').decode('ASCII')
        cat_normalized = re.sub(r'[^\w]', '', cat_normalized)[:20]
        return f"{cat_normalized}_{date_str}_{name_normalized}.{ext}"
    
    return f"{date_str}_{name_normalized}.{ext}"


def is_image_file(filename: str, content_type: str = None) -> bool:
    """Verifica se o ficheiro é uma imagem suportada para conversão."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
    image_mimes = {'image/jpeg', 'image/png', 'image/tiff'}
    
    if filename:
        ext = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext in image_extensions:
            return True
    
    if content_type and content_type.lower() in image_mimes:
        return True
    
    return False

# ====================================================================
# PARTE 1: GESTÃO DE FICHEIROS (S3 STORAGE) - NOVO
# ====================================================================

@router.get("/client/{client_id}/files")
async def list_client_files(
    client_id: str, 
    user: dict = Depends(get_current_user)
):
    """Lista todos os ficheiros do cliente no S3 organizados por pastas."""
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    client_name = process.get("client_name", "Cliente")
    # Obter segundo titular se existir
    second_client_name = process.get("second_client_name") or \
                         process.get("titular2_data", {}).get("nome")
    
    # Chama o serviço S3
    files = s3_service.list_files(client_id, client_name, second_client_name)
    return files

@router.post("/client/{client_id}/upload")
async def upload_file_s3(
    client_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    category: str = Form(...), # Ex: "Financeiros", "Imovel"
    user: dict = Depends(get_current_user)
):
    """
    Faz upload de um ficheiro físico para o S3.
    
    Funcionalidades automáticas:
    - Normalização do nome do ficheiro
    - Conversão de imagens (JPG, PNG) para PDF
    - Categorização automática com IA (em background)
    """
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    client_name = process.get("client_name", "Cliente")
    second_client_name = process.get("second_client_name") or \
                         process.get("titular2_data", {}).get("nome")
    
    # Ler o conteúdo do ficheiro
    file_content = await file.read()
    original_filename = file.filename
    content_type = file.content_type
    
    # Verificar se é uma imagem e converter para PDF
    converted_to_pdf = False
    if is_image_file(original_filename, content_type) and IMG2PDF_AVAILABLE:
        try:
            logger.info(f"A converter imagem para PDF: {original_filename}")
            pdf_bytes, new_filename = await convert_image_to_pdf(file_content, original_filename)
            
            if new_filename != original_filename:
                file_content = pdf_bytes
                original_filename = new_filename
                content_type = "application/pdf"
                converted_to_pdf = True
                logger.info(f"Conversão concluída: {new_filename}")
        except Exception as e:
            logger.warning(f"Não foi possível converter imagem para PDF: {e}")
            # Continua com o ficheiro original
    
    # Normalizar nome do ficheiro
    normalized_filename = normalize_filename(original_filename, category)
    logger.info(f"Nome normalizado: {file.filename} -> {normalized_filename}")
    
    # Criar BytesIO para o upload
    file_buffer = BytesIO(file_content)
    
    # Upload para o S3
    s3_path = s3_service.upload_file(
        file_buffer,
        client_id,
        client_name,
        category,
        normalized_filename,
        content_type,
        second_client_name=second_client_name
    )
    
    if not s3_path:
        raise HTTPException(status_code=500, detail="Erro ao enviar ficheiro para o armazenamento S3")
    
    # Agendar categorização automática em background (não bloqueia o response)
    background_tasks.add_task(
        auto_categorize_document_background,
        process_id=client_id,
        client_name=client_name,
        s3_path=s3_path,
        filename=normalized_filename,
        file_content=file_content
    )
    
    return {
        "success": True, 
        "path": s3_path, 
        "message": "Ficheiro guardado com sucesso",
        "original_filename": file.filename,
        "normalized_filename": normalized_filename,
        "converted_to_pdf": converted_to_pdf,
        "auto_categorization": "iniciada"  # Indica que categorização foi agendada
    }

@router.post("/client/{client_id}/init-folders")
async def initialize_folders(client_id: str, user: dict = Depends(get_current_user)):
    """Cria a estrutura de pastas inicial no S3 (se não existir)."""
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    client_name = process.get("client_name", "Cliente")
    second_client_name = process.get("second_client_name") or \
                         process.get("titular2_data", {}).get("nome")
    
    success = s3_service.initialize_client_folders(
        client_id, 
        client_name,
        second_client_name=second_client_name
    )
    return {"success": success}


@router.get("/client/{client_id}/download")
async def get_download_url(
    client_id: str,
    file_path: str,
    user: dict = Depends(get_current_user)
):
    """Gera um URL temporário para download de um ficheiro."""
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar se o ficheiro pertence ao cliente (segurança)
    expected_prefix = f"clientes/{client_id}_"
    
    if not file_path.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Acesso não autorizado a este ficheiro")
    
    url = s3_service.get_presigned_url(file_path)
    if not url:
        raise HTTPException(status_code=500, detail="Erro ao gerar link de download")
    
    return {"success": True, "url": url}


@router.delete("/client/{client_id}/file")
async def delete_file_s3(
    client_id: str,
    file_path: str,
    user: dict = Depends(get_current_user)
):
    """Elimina um ficheiro do S3."""
    process = await db.processes.find_one({"id": client_id})
    if not process:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar se o ficheiro pertence ao cliente (segurança)
    expected_prefix = f"clientes/{client_id}_"
    
    if not file_path.startswith(expected_prefix):
        raise HTTPException(status_code=403, detail="Acesso não autorizado a este ficheiro")
    
    success = s3_service.delete_file(file_path)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao eliminar ficheiro")
    
    return {"success": True, "message": "Ficheiro eliminado"}


# ====================================================================
# PARTE 2: GESTÃO DE VALIDADES (EXISTENTE)
# ====================================================================
EXPIRY_WARNING_DAYS = 60 

@router.post("/expiry", response_model=DocumentExpiryResponse)
async def create_document_expiry(
    data: DocumentExpiryCreate,
    user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CONSULTOR, UserRole.MEDIADOR]))
):
    """Registar validade de um documento."""
    process = await db.processes.find_one({"id": data.process_id})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    doc = {
        "id": doc_id,
        "process_id": data.process_id,
        "document_type": data.document_type,
        "document_name": data.document_name,
        "expiry_date": data.expiry_date,
        "notes": data.notes,
        "created_at": now,
        "created_by": user["id"]
    }
    
    await db.document_expiries.insert_one(doc)
    return DocumentExpiryResponse(**{k: v for k, v in doc.items() if k != "_id"})

@router.get("/expiry", response_model=List[DocumentExpiryResponse])
async def get_document_expiries(
    process_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Obter registos de validade."""
    query = {}
    if process_id:
        query["process_id"] = process_id
    elif user["role"] == UserRole.CONSULTOR:
        processes = await db.processes.find({"assigned_consultor_id": user["id"]}, {"id": 1}).to_list(1000)
        query["process_id"] = {"$in": [p["id"] for p in processes]}
    elif user["role"] == UserRole.MEDIADOR:
        processes = await db.processes.find({"assigned_mediador_id": user["id"]}, {"id": 1}).to_list(1000)
        query["process_id"] = {"$in": [p["id"] for p in processes]}
    
    docs = await db.document_expiries.find(query, {"_id": 0}).to_list(1000)
    return [DocumentExpiryResponse(**d) for d in docs]

@router.get("/expiry/upcoming")
async def get_upcoming_expiries(
    days: int = EXPIRY_WARNING_DAYS,
    user: dict = Depends(get_current_user)
):
    """Alertas de documentos a expirar."""
    today = datetime.now(timezone.utc).date()
    future_date = today + timedelta(days=days)
    excluded_statuses = ["concluido", "desistencia", "desistência"]
    
    query = {
        "expiry_date": {
            "$gte": today.isoformat(),
            "$lte": future_date.isoformat()
        }
    }
    
    # Filtros de role (simplificado para brevidade, mantém a lógica original)
    if user["role"] == UserRole.CONSULTOR:
        procs = await db.processes.find({"$or": [{"assigned_consultor_id": user["id"]}, {"consultor_id": user["id"]}]}, {"id": 1}).to_list(1000)
        query["process_id"] = {"$in": [p["id"] for p in procs]} if procs else {"$in": []}
    
    docs = await db.document_expiries.find(query, {"_id": 0}).sort("expiry_date", 1).to_list(1000)
    
    result = []
    for doc in docs:
        process = await db.processes.find_one({"id": doc["process_id"]}, {"_id": 0})
        if process and process.get("status", "").lower() not in excluded_statuses:
            expiry = datetime.strptime(doc["expiry_date"], "%Y-%m-%d").date()
            days_until = (expiry - today).days
            result.append({
                **doc,
                "client_name": process.get("client_name"),
                "days_until_expiry": days_until,
                "urgency": "critical" if days_until <= 7 else "warning" if days_until <= 30 else "normal"
            })
    return result

@router.get("/expiry/calendar")
async def get_expiry_calendar_events(user: dict = Depends(get_current_user)):
    """Eventos para calendário."""
    upcoming = await get_upcoming_expiries(days=EXPIRY_WARNING_DAYS, user=user)
    events = []
    for doc in upcoming:
        color = "#EF4444" if doc["urgency"] == "critical" else "#F59E0B" if doc["urgency"] == "warning" else "#3B82F6"
        events.append({
            "id": f"doc-expiry-{doc['id']}",
            "title": f"📄 {doc['document_name']} - {doc['client_name']}",
            "date": doc["expiry_date"],
            "color": color
        })
    return events

@router.delete("/expiry/{doc_id}")
async def delete_document_expiry(doc_id: str, user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.CONSULTOR]))):
    result = await db.document_expiries.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Registo não encontrado")
    return {"message": "Eliminado"}

# Tipos de documentos (mantido)
DOCUMENT_TYPES = [
    {"type": "cc", "name": "Cartão de Cidadão", "validity_years": 5},
    {"type": "irs", "name": "Declaração de IRS", "validity_years": 1},
    {"type": "recibo", "name": "Recibo Vencimento", "validity_months": 3},
    {"type": "outro", "name": "Outro", "validity_years": None},
]

@router.get("/types")
async def get_document_types(user: dict = Depends(get_current_user)):
    return DOCUMENT_TYPES


# ====================================================================
# PARTE 3: CATEGORIZAÇÃO E PESQUISA COM IA (NOVO)
# ====================================================================

from services.document_categorization import (
    extract_text_from_pdf,
    categorize_document_with_ai,
    search_documents_by_content,
    get_unique_categories
)
from models.document import (
    DocumentMetadata, 
    DocumentMetadataCreate,
    DocumentMetadataResponse,
    DocumentSearchRequest,
    DocumentSearchResult
)


@router.post("/categorize/{process_id}")
async def categorize_document(
    process_id: str,
    s3_path: str = Form(...),
    filename: str = Form(...),
    user: dict = Depends(get_current_user)
):
    """
    Categorizar um documento específico usando IA.
    
    A IA analisa o conteúdo do documento e atribui:
    - Categoria principal
    - Subcategoria (tipo específico)
    - Tags relevantes
    - Resumo do conteúdo
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    client_name = process.get("client_name", "Cliente")
    now = datetime.now(timezone.utc).isoformat()
    
    # Verificar se já existe metadados para este ficheiro
    existing = await db.document_metadata.find_one({"s3_path": s3_path}, {"_id": 0})
    
    # Obter o ficheiro do S3
    try:
        file_content = s3_service.get_file_content(s3_path)
        if not file_content:
            raise HTTPException(status_code=404, detail="Ficheiro não encontrado no S3")
    except Exception as e:
        logger.error(f"Erro ao obter ficheiro do S3: {e}")
        raise HTTPException(status_code=500, detail="Erro ao aceder ao ficheiro")
    
    # Extrair texto do documento
    extracted_text = ""
    if filename.lower().endswith('.pdf'):
        extracted_text = extract_text_from_pdf(file_content)
    
    # Se não conseguir extrair texto, usar apenas o nome do ficheiro
    text_for_analysis = extracted_text if extracted_text else f"Ficheiro: {filename}"
    
    # Obter categorias existentes para consistência
    existing_categories = await db.document_metadata.distinct("ai_category")
    
    # Categorizar com IA
    result = await categorize_document_with_ai(
        text_content=text_for_analysis,
        filename=filename,
        existing_categories=existing_categories
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500, 
            detail=result.get("error", "Erro ao categorizar documento")
        )
    
    # Criar ou actualizar metadados
    doc_id = existing.get("id") if existing else str(uuid.uuid4())
    
    metadata = {
        "id": doc_id,
        "process_id": process_id,
        "client_name": client_name,
        "s3_path": s3_path,
        "filename": filename,
        "ai_category": result.get("category"),
        "ai_subcategory": result.get("subcategory"),
        "ai_confidence": result.get("confidence"),
        "ai_tags": result.get("tags", []),
        "ai_summary": result.get("summary"),
        "expiry_date": result.get("expiry_date"),  # Nova: data de validade
        "expiry_alert_sent": False,  # Nova: flag de alerta
        "extracted_text": extracted_text[:5000] if extracted_text else None,  # Limitar tamanho
        "file_size": len(file_content),
        "mime_type": "application/pdf" if filename.lower().endswith('.pdf') else None,
        "is_categorized": True,
        "categorized_at": now,
        "updated_at": now
    }
    
    if existing:
        await db.document_metadata.update_one(
            {"id": doc_id},
            {"$set": metadata}
        )
    else:
        metadata["created_at"] = now
        await db.document_metadata.insert_one(metadata)
    
    return {
        "success": True,
        "id": doc_id,
        "category": result.get("category"),
        "subcategory": result.get("subcategory"),
        "confidence": result.get("confidence"),
        "tags": result.get("tags", []),
        "summary": result.get("summary"),
        "expiry_date": result.get("expiry_date")
    }


@router.post("/categorize-all/{process_id}")
async def categorize_all_documents(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Categorizar TODOS os documentos de um cliente/processo.
    Processa documentos que ainda não foram categorizados.
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    client_name = process.get("client_name", "Cliente")
    second_client_name = process.get("second_client_name") or \
                         process.get("titular2_data", {}).get("nome")
    
    # Listar ficheiros do S3
    files_data = s3_service.list_files(process_id, client_name, second_client_name)
    files = files_data.get("files", {})
    
    results = {
        "total": 0,
        "categorized": 0,
        "skipped": 0,
        "errors": 0,
        "documents": []
    }
    
    # Obter categorias existentes
    existing_categories = await db.document_metadata.distinct("ai_category")
    now = datetime.now(timezone.utc).isoformat()
    
    # Processar cada categoria de ficheiros
    for category, file_list in files.items():
        for file_info in file_list:
            results["total"] += 1
            
            s3_path = file_info.get("path")
            filename = file_info.get("name")
            
            if not s3_path or not filename:
                continue
            
            # Verificar se já foi categorizado
            existing = await db.document_metadata.find_one(
                {"s3_path": s3_path, "is_categorized": True},
                {"_id": 0}
            )
            
            if existing:
                results["skipped"] += 1
                results["documents"].append({
                    "filename": filename,
                    "status": "skipped",
                    "category": existing.get("ai_category")
                })
                continue
            
            try:
                # Obter ficheiro do S3
                file_content = s3_service.get_file_content(s3_path)
                if not file_content:
                    results["errors"] += 1
                    continue
                
                # Extrair texto
                extracted_text = ""
                if filename.lower().endswith('.pdf'):
                    extracted_text = extract_text_from_pdf(file_content)
                
                text_for_analysis = extracted_text if extracted_text else f"Ficheiro: {filename}"
                
                # Categorizar
                result = await categorize_document_with_ai(
                    text_content=text_for_analysis,
                    filename=filename,
                    existing_categories=existing_categories
                )
                
                if result.get("success"):
                    # Guardar metadados
                    doc_id = str(uuid.uuid4())
                    metadata = {
                        "id": doc_id,
                        "process_id": process_id,
                        "client_name": client_name,
                        "s3_path": s3_path,
                        "filename": filename,
                        "ai_category": result.get("category"),
                        "ai_subcategory": result.get("subcategory"),
                        "ai_confidence": result.get("confidence"),
                        "ai_tags": result.get("tags", []),
                        "ai_summary": result.get("summary"),
                        "expiry_date": result.get("expiry_date"),  # Nova: data de validade
                        "expiry_alert_sent": False,  # Nova: flag de alerta
                        "extracted_text": extracted_text[:5000] if extracted_text else None,
                        "file_size": len(file_content),
                        "is_categorized": True,
                        "categorized_at": now,
                        "created_at": now,
                        "updated_at": now
                    }
                    
                    await db.document_metadata.insert_one(metadata)
                    
                    # Actualizar lista de categorias
                    if result.get("category") and result["category"] not in existing_categories:
                        existing_categories.append(result["category"])
                    
                    results["categorized"] += 1
                    results["documents"].append({
                        "filename": filename,
                        "status": "categorized",
                        "category": result.get("category"),
                        "subcategory": result.get("subcategory"),
                        "expiry_date": result.get("expiry_date")
                    })
                else:
                    results["errors"] += 1
                    results["documents"].append({
                        "filename": filename,
                        "status": "error",
                        "error": result.get("error")
                    })
                    
            except Exception as e:
                logger.error(f"Erro ao categorizar {filename}: {e}")
                results["errors"] += 1
                results["documents"].append({
                    "filename": filename,
                    "status": "error",
                    "error": str(e)
                })
    
    return results


@router.get("/metadata/{process_id}")
async def get_document_metadata(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Obter metadados de todos os documentos de um processo.
    Inclui categorização IA se disponível.
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Obter metadados existentes
    metadata_list = await db.document_metadata.find(
        {"process_id": process_id},
        {"_id": 0, "extracted_text": 0}  # Não retornar texto completo
    ).to_list(1000)
    
    # Obter categorias únicas
    categories = await db.document_metadata.distinct(
        "ai_category",
        {"process_id": process_id, "ai_category": {"$ne": None}}
    )
    
    return {
        "process_id": process_id,
        "client_name": process.get("client_name"),
        "documents": metadata_list,
        "total": len(metadata_list),
        "categorized": sum(1 for d in metadata_list if d.get("is_categorized")),
        "categories": sorted(categories)
    }


@router.post("/search")
async def search_documents(
    request: DocumentSearchRequest,
    user: dict = Depends(get_current_user)
):
    """
    Pesquisar documentos por conteúdo.
    
    Pesquisa em:
    - Nome do ficheiro
    - Categoria e subcategoria IA
    - Tags
    - Resumo
    - Texto extraído
    """
    query = {"is_categorized": True}
    
    # Filtrar por processo se especificado
    if request.process_id:
        query["process_id"] = request.process_id
    
    # Filtrar por categorias se especificado
    if request.categories:
        query["ai_category"] = {"$in": request.categories}
    
    # Obter documentos
    documents = await db.document_metadata.find(query, {"_id": 0}).to_list(1000)
    
    # Pesquisar
    results = await search_documents_by_content(
        query=request.query,
        process_id=request.process_id,
        documents=documents,
        limit=request.limit
    )
    
    return {
        "query": request.query,
        "total_results": len(results),
        "results": results
    }


@router.get("/categories")
async def get_all_categories(
    process_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Obter todas as categorias de documentos.
    Opcionalmente filtrar por processo.
    """
    query = {"ai_category": {"$ne": None}}
    
    if process_id:
        query["process_id"] = process_id
    
    # Contar documentos por categoria
    pipeline = [
        {"$match": query},
        {"$group": {"_id": "$ai_category", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    category_counts = await db.document_metadata.aggregate(pipeline).to_list(100)
    
    return {
        "categories": [
            {
                "name": cat["_id"],
                "count": cat["count"]
            }
            for cat in category_counts if cat["_id"]
        ],
        "total_categories": len(category_counts)
    }



# ====================================================================
# DASHBOARD DE VALIDADES DE DOCUMENTOS
# ====================================================================

@router.get("/expiring-dashboard")
async def get_expiring_documents_dashboard(
    days_ahead: int = 60,
    urgency: Optional[str] = None,  # "critical", "high", "medium"
    consultor_id: Optional[str] = None,
    search: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """
    Dashboard de documentos a expirar.
    
    Permissões:
    - CEO/Diretor/Admin: Vêem todos os clientes
    - Consultor/Intermediário: Vêem apenas os seus clientes
    
    Args:
        days_ahead: Dias a verificar (default 60)
        urgency: Filtro por urgência (critical=<7, high=7-29, medium=30-60)
        consultor_id: Filtro por consultor (apenas para management)
        search: Pesquisa por nome de cliente
    
    Returns:
        Dashboard com estatísticas e lista de documentos agrupados por cliente
    """
    from datetime import timezone
    
    user_role = user.get("role", "")
    user_id = user.get("id", "")
    
    # Verificar se é management (pode ver tudo)
    is_management = user_role in UserRole.MANAGEMENT_ROLES
    
    today = datetime.now(timezone.utc)
    future_date = today + timedelta(days=days_ahead)
    
    # Query base para documentos com data de expiração
    doc_query = {
        "expiry_date": {
            "$ne": None,
            "$gte": today.strftime("%Y-%m-%d"),
            "$lte": future_date.strftime("%Y-%m-%d")
        }
    }
    
    # Aplicar filtro de urgência
    if urgency:
        if urgency == "critical":
            critical_date = (today + timedelta(days=7)).strftime("%Y-%m-%d")
            doc_query["expiry_date"]["$lt"] = critical_date
        elif urgency == "high":
            high_start = (today + timedelta(days=7)).strftime("%Y-%m-%d")
            high_end = (today + timedelta(days=30)).strftime("%Y-%m-%d")
            doc_query["expiry_date"]["$gte"] = high_start
            doc_query["expiry_date"]["$lt"] = high_end
        elif urgency == "medium":
            medium_start = (today + timedelta(days=30)).strftime("%Y-%m-%d")
            doc_query["expiry_date"]["$gte"] = medium_start
    
    # Buscar todos os documentos a expirar
    expiring_docs = await db.document_metadata.find(
        doc_query,
        {"_id": 0, "extracted_text": 0}
    ).to_list(1000)
    
    # Obter process_ids únicos
    process_ids = list(set(doc.get("process_id") for doc in expiring_docs if doc.get("process_id")))
    
    # Buscar processos para obter informações dos clientes e consultores
    processes_query = {"id": {"$in": process_ids}}
    
    # Se não é management, filtrar apenas processos do utilizador
    if not is_management:
        processes_query["$or"] = [
            {"assigned_consultor_id": user_id},
            {"consultor_id": user_id},
            {"assigned_mediador_id": user_id},
            {"mediador_id": user_id}
        ]
    
    # Filtro por consultor específico (apenas para management)
    if is_management and consultor_id:
        processes_query["$or"] = [
            {"assigned_consultor_id": consultor_id},
            {"consultor_id": consultor_id},
            {"assigned_mediador_id": consultor_id},
            {"mediador_id": consultor_id}
        ]
    
    processes = await db.processes.find(
        processes_query,
        {"_id": 0, "id": 1, "client_name": 1, "assigned_consultor_id": 1, 
         "consultor_id": 1, "assigned_mediador_id": 1, "mediador_id": 1}
    ).to_list(500)
    
    # Criar mapa de processos
    process_map = {p["id"]: p for p in processes}
    
    # Filtrar documentos apenas dos processos autorizados
    authorized_process_ids = set(process_map.keys())
    filtered_docs = [d for d in expiring_docs if d.get("process_id") in authorized_process_ids]
    
    # Aplicar filtro de pesquisa
    if search:
        search_lower = search.lower()
        search_process_ids = [
            pid for pid, p in process_map.items() 
            if search_lower in (p.get("client_name") or "").lower()
        ]
        filtered_docs = [d for d in filtered_docs if d.get("process_id") in search_process_ids]
    
    # Obter nomes dos consultores
    consultor_ids = set()
    for p in processes:
        if p.get("assigned_consultor_id"):
            consultor_ids.add(p["assigned_consultor_id"])
        if p.get("consultor_id"):
            consultor_ids.add(p["consultor_id"])
        if p.get("assigned_mediador_id"):
            consultor_ids.add(p["assigned_mediador_id"])
        if p.get("mediador_id"):
            consultor_ids.add(p["mediador_id"])
    
    consultors = await db.users.find(
        {"id": {"$in": list(consultor_ids)}},
        {"_id": 0, "id": 1, "name": 1}
    ).to_list(100)
    consultor_map = {c["id"]: c.get("name", "N/D") for c in consultors}
    
    # Calcular estatísticas
    stats = {"critical": 0, "high": 0, "medium": 0, "total": len(filtered_docs)}
    
    for doc in filtered_docs:
        try:
            expiry = datetime.strptime(doc["expiry_date"], "%Y-%m-%d")
            days_until = (expiry - today).days
            if days_until < 7:
                stats["critical"] += 1
            elif days_until < 30:
                stats["high"] += 1
            else:
                stats["medium"] += 1
        except:
            pass
    
    # Agrupar documentos por cliente
    clients_data = {}
    
    for doc in filtered_docs:
        process_id = doc.get("process_id")
        if not process_id or process_id not in process_map:
            continue
        
        process = process_map[process_id]
        client_name = doc.get("client_name") or process.get("client_name", "Cliente")
        
        if process_id not in clients_data:
            # Identificar consultor responsável
            consultor_id = process.get("assigned_consultor_id") or process.get("consultor_id") or \
                          process.get("assigned_mediador_id") or process.get("mediador_id")
            consultor_name = consultor_map.get(consultor_id, "N/D")
            
            clients_data[process_id] = {
                "process_id": process_id,
                "client_name": client_name,
                "consultor_id": consultor_id,
                "consultor_name": consultor_name,
                "documents": [],
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0
            }
        
        # Calcular urgência do documento
        try:
            expiry = datetime.strptime(doc["expiry_date"], "%Y-%m-%d")
            days_until = (expiry - today).days
            
            if days_until < 7:
                urgency_level = "critical"
                clients_data[process_id]["critical_count"] += 1
            elif days_until < 30:
                urgency_level = "high"
                clients_data[process_id]["high_count"] += 1
            else:
                urgency_level = "medium"
                clients_data[process_id]["medium_count"] += 1
        except:
            urgency_level = "unknown"
            days_until = None
        
        clients_data[process_id]["documents"].append({
            "id": doc.get("id"),
            "filename": doc.get("filename"),
            "category": doc.get("ai_category"),
            "subcategory": doc.get("ai_subcategory"),
            "expiry_date": doc.get("expiry_date"),
            "days_until": days_until,
            "urgency": urgency_level,
            "s3_path": doc.get("s3_path")
        })
    
    # Converter para lista e ordenar por urgência (mais críticos primeiro)
    clients_list = list(clients_data.values())
    clients_list.sort(key=lambda x: (-x["critical_count"], -x["high_count"], -x["medium_count"]))
    
    # Obter lista de consultores para filtro (apenas para management)
    consultors_filter = []
    if is_management:
        all_consultors = await db.users.find(
            {"role": {"$in": ["consultor", "intermediario", "mediador"]}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(100)
        consultors_filter = [{"id": c["id"], "name": c.get("name", "N/D")} for c in all_consultors]
    
    return {
        "stats": stats,
        "clients": clients_list,
        "total_clients": len(clients_list),
        "is_management": is_management,
        "consultors_filter": consultors_filter,
        "filters_applied": {
            "days_ahead": days_ahead,
            "urgency": urgency,
            "consultor_id": consultor_id,
            "search": search
        }
    }