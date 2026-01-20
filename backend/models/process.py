from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any


class ProcessType:
    CREDITO = "credito"
    IMOBILIARIA = "imobiliaria"
    AMBOS = "ambos"


class PersonalData(BaseModel):
    # Dados básicos
    nif: Optional[str] = None
    documento_id: Optional[str] = None
    naturalidade: Optional[str] = None
    nacionalidade: Optional[str] = None
    morada_fiscal: Optional[str] = None
    birth_date: Optional[str] = None
    estado_civil: Optional[str] = None
    compra_tipo: Optional[str] = None
    # Legacy fields (backwards compatibility)
    address: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = None


class Titular2Data(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    nif: Optional[str] = None
    documento_id: Optional[str] = None
    naturalidade: Optional[str] = None
    nacionalidade: Optional[str] = None
    phone: Optional[str] = None
    morada_fiscal: Optional[str] = None
    birth_date: Optional[str] = None
    estado_civil: Optional[str] = None


class RealEstateData(BaseModel):
    # Novos campos do formulário
    tipo_imovel: Optional[str] = None
    num_quartos: Optional[str] = None
    localizacao: Optional[str] = None
    caracteristicas: Optional[List[str]] = None
    outras_caracteristicas: Optional[str] = None
    outras_informacoes: Optional[str] = None
    # Legacy fields
    property_type: Optional[str] = None
    property_zone: Optional[str] = None
    desired_area: Optional[float] = None
    max_budget: Optional[float] = None
    property_purpose: Optional[str] = None
    notes: Optional[str] = None


class FinancialData(BaseModel):
    # Novos campos do formulário
    acesso_portal_financas: Optional[str] = None
    chave_movel_digital: Optional[str] = None
    renda_habitacao_atual: Optional[float] = None
    precisa_vender_casa: Optional[str] = None
    efetivo: Optional[str] = None
    fiador: Optional[str] = None
    bancos_creditos: Optional[List[str]] = None
    capital_proprio: Optional[float] = None
    valor_financiado: Optional[str] = None
    # Legacy fields
    monthly_income: Optional[float] = None
    other_income: Optional[float] = None
    monthly_expenses: Optional[float] = None
    employment_type: Optional[str] = None
    employer_name: Optional[str] = None
    employment_duration: Optional[str] = None
    has_debts: Optional[bool] = None
    debt_amount: Optional[float] = None


class CreditData(BaseModel):
    requested_amount: Optional[float] = None
    loan_term_years: Optional[int] = None
    interest_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    bank_name: Optional[str] = None
    bank_approval_date: Optional[str] = None
    bank_approval_notes: Optional[str] = None


class ProcessCreate(BaseModel):
    process_type: str
    personal_data: Optional[PersonalData] = None
    financial_data: Optional[FinancialData] = None


class PublicClientRegistration(BaseModel):
    name: str
    email: EmailStr
    phone: str
    process_type: str
    personal_data: Optional[PersonalData] = None
    titular2_data: Optional[Titular2Data] = None
    real_estate_data: Optional[RealEstateData] = None
    financial_data: Optional[FinancialData] = None


class ProcessUpdate(BaseModel):
    personal_data: Optional[PersonalData] = None
    titular2_data: Optional[Titular2Data] = None
    financial_data: Optional[FinancialData] = None
    real_estate_data: Optional[RealEstateData] = None
    credit_data: Optional[CreditData] = None
    status: Optional[str] = None


class ProcessResponse(BaseModel):
    id: str
    client_id: Optional[str] = None
    client_name: str
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    process_type: Optional[str] = None
    type: Optional[str] = None  # Alias for process_type (from Trello import)
    status: str
    personal_data: Optional[dict] = None
    titular2_data: Optional[dict] = None
    financial_data: Optional[dict] = None
    real_estate_data: Optional[dict] = None
    credit_data: Optional[dict] = None
    assigned_consultor_id: Optional[str] = None
    assigned_mediador_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    notes: Optional[str] = None
    valor_financiado: Optional[str] = None
    idade_menos_35: Optional[bool] = None
    prioridade: Optional[bool] = None
    labels: Optional[List[str]] = None
    onedrive_links: Optional[List[dict]] = None
