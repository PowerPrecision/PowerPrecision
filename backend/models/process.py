from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
import re


class ProcessType:
    CREDITO = "credito"
    IMOBILIARIA = "imobiliaria"
    AMBOS = "ambos"


def validate_nif(nif: str, allow_company: bool = False) -> str:
    """
    Validar NIF português (9 dígitos numéricos).
    Por defeito, não permite NIFs de empresas (começam por 5).
    
    Args:
        nif: O NIF a validar
        allow_company: Se True, permite NIFs de empresas (5xxxxxxxx)
    
    Returns:
        O NIF limpo se válido
        
    Raises:
        ValueError: Se o NIF for inválido
    """
    if not nif:
        return nif
    
    # Remover espaços e caracteres especiais
    nif_clean = re.sub(r'[^\d]', '', nif)
    
    if len(nif_clean) != 9:
        raise ValueError(f"NIF deve ter 9 dígitos (recebido: {len(nif_clean)})")
    
    if not nif_clean.isdigit():
        raise ValueError("NIF deve conter apenas dígitos")
    
    # Validar primeiro dígito - NIFs que começam com 5 são de empresas
    if not allow_company and nif_clean.startswith('5'):
        raise ValueError("NIF de empresa (começado por 5) não é permitido para clientes particulares")
    
    return nif_clean


class PersonalData(BaseModel):
    """
    Dados pessoais do titular.
    
    Campos activos:
    - nif (validado: 9 dígitos), documento_id, naturalidade, nacionalidade, morada_fiscal
    - birth_date, estado_civil, compra_tipo, menor_35_anos
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
    
    @field_validator('nif', mode='before')
    @classmethod
    def validate_nif_field(cls, v):
        if v is None or v == '':
            return None
        return validate_nif(v)


class Titular2Data(BaseModel):
    """Dados do segundo titular."""
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
    
    @field_validator('nif', mode='before')
    @classmethod
    def validate_nif_field(cls, v):
        if v is None or v == '':
            return None
        return validate_nif(v)


class RealEstateData(BaseModel):
    """
    Dados imobiliários.
    
    Campos activos:
    - tipo_imovel, num_quartos, localizacao, caracteristicas
    - outras_caracteristicas, outras_informacoes
    - ja_tem_imovel (indica se o cliente já tem imóvel identificado)
    - Dados do proprietário: owner_name, owner_email, owner_phone
    - Dados do CPCV: valor_imovel, datas, etc.
    """
    tipo_imovel: Optional[str] = None
    num_quartos: Optional[str] = None
    localizacao: Optional[str] = None
    caracteristicas: Optional[List[str]] = None
    outras_caracteristicas: Optional[str] = None
    outras_informacoes: Optional[str] = None
    ja_tem_imovel: Optional[bool] = None  # Indica se cliente já tem imóvel identificado
    has_property: Optional[bool] = None   # Alias para ja_tem_imovel
    # Dados do proprietário do imóvel
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    # Dados do CPCV
    valor_imovel: Optional[float] = None
    codigo_postal: Optional[str] = None
    localidade: Optional[str] = None
    freguesia: Optional[str] = None
    concelho: Optional[str] = None
    tipologia: Optional[str] = None
    area_bruta: Optional[str] = None
    area_util: Optional[str] = None
    fracao: Optional[str] = None
    artigo_matricial: Optional[str] = None
    conservatoria: Optional[str] = None
    numero_predial: Optional[str] = None
    certificado_energetico: Optional[str] = None
    estacionamento: Optional[str] = None
    arrecadacao: Optional[str] = None
    descricao_imovel: Optional[str] = None
    valor_patrimonial: Optional[float] = None
    # Datas do CPCV
    data_cpcv: Optional[str] = None
    data_escritura_prevista: Optional[str] = None
    prazo_escritura_dias: Optional[int] = None
    data_entrega_chaves: Optional[str] = None
    # Condições
    condicao_suspensiva: Optional[str] = None
    observacoes_cpcv: Optional[str] = None


class FinancialData(BaseModel):
    """
    Dados financeiros.
    
    Campos activos:
    - acesso_portal_financas, chave_movel_digital, renda_habitacao_atual
    - precisa_vender_casa, efetivo, fiador, bancos_creditos
    - capital_proprio, valor_financiado
    - Dados do CPCV: valor_entrada, valor_pretendido, etc.
    """
    acesso_portal_financas: Optional[str] = None
    chave_movel_digital: Optional[str] = None
    renda_habitacao_atual: Optional[float] = None
    precisa_vender_casa: Optional[str] = None
    efetivo: Optional[str] = None
    fiador: Optional[str] = None
    bancos_creditos: Optional[List[str]] = None
    capital_proprio: Optional[float] = None
    valor_financiado: Optional[str] = None
    # Dados do CPCV - Valores
    valor_pretendido: Optional[float] = None
    valor_entrada: Optional[float] = None
    data_sinal: Optional[str] = None
    reforco_sinal: Optional[float] = None
    comissao_mediacao: Optional[float] = None


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
    client_name: Optional[str] = None
    client_email: Optional[str] = None
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
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    # Campos adicionais para CPCV e documentos com múltiplos compradores
    co_buyers: Optional[List[dict]] = None  # Co-compradores do CPCV
    co_applicants: Optional[List[dict]] = None  # Co-proponentes de simulação/IRS
    vendedor: Optional[dict] = None  # Dados do vendedor do CPCV
    mediador: Optional[dict] = None  # Dados do mediador imobiliário


class ProcessResponse(BaseModel):
    id: str
    process_number: Optional[int] = None  # Número sequencial único do processo
    client_id: Optional[str] = None
    client_name: str
    client_email: Optional[str] = None
    client_phone: Optional[str] = None
    client_nif: Optional[str] = None
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
    has_property: Optional[bool] = None  # Flag para indicar se cliente já tem imóvel
    trello_card_id: Optional[str] = None  # ID do card no Trello
    trello_list_id: Optional[str] = None  # ID da lista no Trello
    source: Optional[str] = None  # Origem do processo (trello_import, web_form, etc.)
    monitored_emails: Optional[List[str]] = None  # Emails adicionais para monitorizar
    # Campos do CPCV
    co_buyers: Optional[List[dict]] = None  # Co-compradores
    co_applicants: Optional[List[dict]] = None  # Co-proponentes
    vendedor: Optional[dict] = None  # Dados do vendedor
    mediador: Optional[dict] = None  # Dados do mediador imobiliário
