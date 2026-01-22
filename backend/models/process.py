from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from warnings import warn


class ProcessType:
    CREDITO = "credito"
    IMOBILIARIA = "imobiliaria"
    AMBOS = "ambos"


class PersonalData(BaseModel):
    """
    Dados pessoais do titular.
    
    Campos activos:
    - nif, documento_id, naturalidade, nacionalidade, morada_fiscal
    - birth_date, estado_civil, compra_tipo, menor_35_anos
    
    Campos DEPRECATED (manter para compatibilidade com dados antigos):
    - address -> usar morada_fiscal
    - marital_status -> usar estado_civil
    - nationality -> usar nacionalidade
    """
    # Dados básicos (activos)
    nif: Optional[str] = None
    documento_id: Optional[str] = None
    naturalidade: Optional[str] = None
    nacionalidade: Optional[str] = None
    morada_fiscal: Optional[str] = None
    birth_date: Optional[str] = None
    estado_civil: Optional[str] = None
    compra_tipo: Optional[str] = None
    menor_35_anos: Optional[bool] = None  # Checkbox apoio ao estado
    
    # DEPRECATED - mantidos apenas para compatibilidade com dados importados
    address: Optional[str] = Field(default=None, deprecated=True)  # Usar morada_fiscal
    marital_status: Optional[str] = Field(default=None, deprecated=True)  # Usar estado_civil
    nationality: Optional[str] = Field(default=None, deprecated=True)  # Usar nacionalidade


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
    """
    Dados imobiliários.
    
    Campos activos:
    - tipo_imovel, num_quartos, localizacao, caracteristicas
    - outras_caracteristicas, outras_informacoes
    
    Campos DEPRECATED (manter para compatibilidade):
    - property_type -> usar tipo_imovel
    - property_zone -> usar localizacao
    - desired_area, max_budget, property_purpose, notes
    """
    # Campos activos (do novo formulário)
    tipo_imovel: Optional[str] = None
    num_quartos: Optional[str] = None
    localizacao: Optional[str] = None
    caracteristicas: Optional[List[str]] = None
    outras_caracteristicas: Optional[str] = None
    outras_informacoes: Optional[str] = None
    
    # DEPRECATED - mantidos para compatibilidade
    property_type: Optional[str] = Field(default=None, deprecated=True)
    property_zone: Optional[str] = Field(default=None, deprecated=True)
    desired_area: Optional[float] = Field(default=None, deprecated=True)
    max_budget: Optional[float] = Field(default=None, deprecated=True)
    property_purpose: Optional[str] = Field(default=None, deprecated=True)
    notes: Optional[str] = Field(default=None, deprecated=True)


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
