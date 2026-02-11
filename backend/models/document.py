from pydantic import BaseModel
from typing import Optional


class DocumentExpiry(BaseModel):
    """Document expiry date tracking for a client."""
    process_id: str
    document_type: str  # 'cc', 'carta_conducao', 'passaporte', 'contrato_trabalho', etc.
    document_name: str
    expiry_date: str  # YYYY-MM-DD
    data_emissao: Optional[str] = None  # Data de emissão do documento (YYYY-MM-DD)
    notes: Optional[str] = None


class DocumentExpiryCreate(BaseModel):
    process_id: str
    document_type: str
    document_name: str
    expiry_date: str
    data_emissao: Optional[str] = None
    notes: Optional[str] = None


class DocumentExpiryUpdate(BaseModel):
    document_name: Optional[str] = None
    expiry_date: Optional[str] = None
    data_emissao: Optional[str] = None
    notes: Optional[str] = None


class DocumentExpiryResponse(BaseModel):
    id: str
    process_id: str
    document_type: str
    document_name: str
    expiry_date: str
    data_emissao: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    created_by: str


class DocumentValidityCheck(BaseModel):
    """Resultado da verificação de validade de documento."""
    document_type: str
    has_expiry: bool
    is_valid: bool
    warning: Optional[str] = None
    error: Optional[str] = None
    days_remaining: Optional[int] = None
    expiry_date: Optional[str] = None
