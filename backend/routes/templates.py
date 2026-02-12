"""
====================================================================
ROTAS DE TEMPLATES E MINUTAS
====================================================================
Endpoints para geração e download de templates preenchidos.
====================================================================
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import Optional, List
from pydantic import BaseModel

from database import db
from services.auth import get_current_user
from services.template_generator import (
    get_template_for_process,
    WEBMAIL_URLS
)
from services.document_checklist import (
    generate_checklist,
    get_documentos_em_falta,
    DOCUMENTOS_CREDITO_HABITACAO
)

router = APIRouter(prefix="/templates", tags=["Templates"])


class DocumentRequestData(BaseModel):
    missing_docs: List[str] = []


@router.get("/webmail-urls")
async def get_webmail_urls(user: dict = Depends(get_current_user)):
    """
    Retorna as URLs dos webmails disponíveis.
    """
    return {
        "webmails": [
            {
                "id": "precision",
                "name": "Precision Crédito",
                "url": WEBMAIL_URLS["precision"]
            },
            {
                "id": "power",
                "name": "Power Real Estate",
                "url": WEBMAIL_URLS["power"]
            }
        ]
    }


@router.get("/process/{process_id}/cpcv")
async def get_cpcv_template(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Gera o template de CPCV (Contrato Promessa Compra e Venda) preenchido.
    Valida se todos os campos obrigatórios estão preenchidos.
    """
    result = await get_template_for_process(process_id, "cpcv")
    
    if result.get("error"):
        # Se for erro de validação, retorna 400 com detalhes
        if result.get("validation_error"):
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": result["error"],
                    "missing_fields": result.get("missing_fields", []),
                    "missing_fields_message": result.get("missing_fields_message", "")
                }
            )
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/process/{process_id}/cpcv/download")
async def download_cpcv_template(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Download do template de CPCV como ficheiro de texto.
    Valida se todos os campos obrigatórios estão preenchidos.
    """
    result = await get_template_for_process(process_id, "cpcv")
    
    if result.get("error"):
        if result.get("validation_error"):
            raise HTTPException(
                status_code=400, 
                detail={
                    "message": result["error"],
                    "missing_fields": result.get("missing_fields", []),
                    "missing_fields_message": result.get("missing_fields_message", "")
                }
            )
        raise HTTPException(status_code=404, detail=result["error"])
    
    client_name = result.get("client_name", "cliente").replace(" ", "_")
    filename = f"CPCV_{client_name}.txt"
    
    return PlainTextResponse(
        content=result["template"],
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/process/{process_id}/valuation-appeal")
async def get_valuation_appeal_template(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Gera o template de apelação de avaliação bancária (Botão de Pânico).
    Usado quando o valor de avaliação é inferior ao valor de compra.
    """
    result = await get_template_for_process(process_id, "valuation_appeal")
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/process/{process_id}/valuation-appeal/download")
async def download_valuation_appeal_template(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Download do template de apelação de avaliação como ficheiro de texto.
    """
    result = await get_template_for_process(process_id, "valuation_appeal")
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    client_name = result.get("client_name", "cliente").replace(" ", "_")
    filename = f"Apelacao_Avaliacao_{client_name}.txt"
    
    return PlainTextResponse(
        content=result["template"],
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/process/{process_id}/document-request")
async def get_document_request_template(
    process_id: str,
    data: DocumentRequestData,
    user: dict = Depends(get_current_user)
):
    """
    Gera o template de pedido de documentos ao cliente.
    """
    result = await get_template_for_process(
        process_id, 
        "document_request",
        extra_data={"missing_docs": data.missing_docs}
    )
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/process/{process_id}/deed-reminder")
async def get_deed_reminder_template(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Gera o template de lembrete de escritura.
    """
    result = await get_template_for_process(process_id, "deed_reminder")
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/process/{process_id}/deed-reminder/download")
async def download_deed_reminder_template(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Download do template de lembrete de escritura como ficheiro de texto.
    """
    result = await get_template_for_process(process_id, "deed_reminder")
    
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    
    client_name = result.get("client_name", "cliente").replace(" ", "_")
    filename = f"Lembrete_Escritura_{client_name}.txt"
    
    return PlainTextResponse(
        content=result["template"],
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/process/{process_id}/document-checklist")
async def get_document_checklist(
    process_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Retorna a checklist dinâmica de documentos para um processo.
    Lista documentos necessários, enviados e em falta.
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    if not process:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    # Obter lista de ficheiros já carregados
    uploaded_files = process.get("uploaded_documents", [])
    file_names = [f.get("name", f.get("filename", "")) for f in uploaded_files]
    
    # Usar o serviço de checklist existente
    checklist_result = generate_checklist(file_names, "credito_habitacao")
    missing_docs = get_documentos_em_falta(checklist_result, apenas_obrigatorios=False)
    
    return {
        "process_id": process_id,
        "client_name": process.get("client_name"),
        "checklist": checklist_result,
        "missing_documents": missing_docs,
        "webmail_urls": WEBMAIL_URLS
    }


@router.get("/document-types")
async def get_document_types(user: dict = Depends(get_current_user)):
    """
    Retorna a lista de tipos de documentos disponíveis.
    """
    return {
        "document_types": [
            {"id": doc["id"], "name": doc["nome"], "required": doc.get("obrigatorio", False)}
            for doc in DOCUMENTOS_CREDITO_HABITACAO
        ]
    }
