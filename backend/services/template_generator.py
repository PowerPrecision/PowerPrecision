"""
====================================================================
SERVIÇO DE GERAÇÃO DE MINUTAS/TEMPLATES
====================================================================
Gera documentos preenchidos automaticamente com dados do processo.
Suporta:
- CPCV (Contrato Promessa Compra e Venda)
- Email de Apelação de Avaliação
- Outros templates configuráveis

O utilizador faz download e copia para o corpo do email no webmail.
====================================================================
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from database import db

logger = logging.getLogger(__name__)


# ====================================================================
# URLS DOS WEBMAILS
# ====================================================================
WEBMAIL_URLS = {
    "precision": "http://webmail.precisioncredito.pt/",
    "power": "https://webmail2.hcpro.pt/Mondo/lang/sys/login.aspx"
}


# ====================================================================
# TEMPLATES DE MINUTAS
# ====================================================================

def generate_cpcv_template(process: Dict[str, Any]) -> str:
    """
    Gera o texto do CPCV (Contrato Promessa Compra e Venda) preenchido.
    
    Args:
        process: Dados do processo
        
    Returns:
        Texto formatado do CPCV
    """
    # Dados do cliente
    client_name = process.get("client_name", "[NOME DO CLIENTE]")
    second_client = process.get("second_client_name") or process.get("titular2_data", {}).get("nome", "")
    
    personal_data = process.get("personal_data", {})
    nif = personal_data.get("nif", "[NIF]")
    cc = personal_data.get("cc", "[Nº CC]")
    morada = personal_data.get("morada", "[MORADA]")
    
    # Dados do imóvel
    property_data = process.get("property_data", {})
    property_address = property_data.get("morada", "[MORADA DO IMÓVEL]")
    property_freguesia = property_data.get("freguesia", "[FREGUESIA]")
    property_concelho = property_data.get("concelho", "[CONCELHO]")
    property_matriz = property_data.get("artigo_matricial", "[ARTIGO MATRICIAL]")
    property_fracao = property_data.get("fracao", "")
    
    # Dados financeiros
    financial_data = process.get("financial_data", {})
    valor_compra = financial_data.get("valor_pretendido") or property_data.get("valor_imovel", 0)
    valor_formatado = f"{valor_compra:,.2f}".replace(",", " ").replace(".", ",") if valor_compra else "[VALOR]"
    
    # Sinal
    sinal = financial_data.get("sinal", 0)
    sinal_formatado = f"{sinal:,.2f}".replace(",", " ").replace(".", ",") if sinal else "[SINAL]"
    
    # Data
    data_atual = datetime.now().strftime("%d de %B de %Y")
    
    # Vendedor (se disponível)
    vendedor = property_data.get("proprietario_nome", "[NOME DO VENDEDOR]")
    vendedor_nif = property_data.get("proprietario_nif", "[NIF DO VENDEDOR]")
    
    # Segundo comprador
    segundo_comprador_texto = ""
    if second_client:
        titular2 = process.get("titular2_data", {})
        segundo_comprador_texto = f"""
e

{second_client}, contribuinte fiscal nº {titular2.get('nif', '[NIF]')}, portador do Cartão de Cidadão nº {titular2.get('cc', '[CC]')}, residente em {titular2.get('morada', '[MORADA]')},
"""

    template = f"""
CONTRATO PROMESSA DE COMPRA E VENDA

Entre:

PRIMEIRO OUTORGANTE (PROMITENTE VENDEDOR):
{vendedor}, contribuinte fiscal nº {vendedor_nif},
doravante designado por "Promitente Vendedor"

e

SEGUNDO OUTORGANTE (PROMITENTE COMPRADOR):
{client_name}, contribuinte fiscal nº {nif}, portador do Cartão de Cidadão nº {cc}, residente em {morada},
{segundo_comprador_texto}
doravante designado(s) por "Promitente(s) Comprador(es)"

É celebrado o presente Contrato Promessa de Compra e Venda, que se rege pelas seguintes cláusulas:

CLÁUSULA PRIMEIRA
(Objeto)

O Promitente Vendedor é dono e legítimo possuidor do seguinte imóvel:
- Fração autónoma designada pela letra "{property_fracao}", correspondente ao {property_fracao} andar, do prédio urbano sito em {property_address}, freguesia de {property_freguesia}, concelho de {property_concelho}, inscrito na matriz predial urbana sob o artigo {property_matriz}.

CLÁUSULA SEGUNDA
(Preço)

O preço da compra e venda é de €{valor_formatado} (euros), a ser pago da seguinte forma:
a) A título de sinal e princípio de pagamento, a quantia de €{sinal_formatado} (euros), nesta data;
b) O remanescente, no montante de €[REMANESCENTE] (euros), será pago na data da celebração da escritura pública de compra e venda.

CLÁUSULA TERCEIRA
(Prazo)

A escritura pública de compra e venda será celebrada no prazo máximo de [PRAZO] dias a contar da presente data, em Cartório Notarial a designar pelo Promitente Comprador, ficando este obrigado a comunicar ao Promitente Vendedor a data, hora e local da escritura com a antecedência mínima de 10 (dez) dias úteis.

CLÁUSULA QUARTA
(Sinal)

O sinal ora entregue ficará sujeito ao regime legal previsto no artigo 442º do Código Civil.

CLÁUSULA QUINTA
(Encargos)

O Promitente Vendedor declara que o imóvel se encontra livre de quaisquer ónus ou encargos, designadamente hipotecas, penhoras ou quaisquer outras limitações ao direito de propriedade, obrigando-se a mantê-lo nessa situação até à data da escritura.

CLÁUSULA SEXTA
(Documentação)

O Promitente Vendedor obriga-se a entregar ao Promitente Comprador, no prazo de [PRAZO DOCS] dias, toda a documentação necessária à celebração da escritura pública.

CLÁUSULA SÉTIMA
(Posse)

A posse do imóvel será entregue ao Promitente Comprador na data da celebração da escritura pública de compra e venda.

CLÁUSULA OITAVA
(Despesas)

As despesas com a celebração da escritura pública, incluindo os respetivos impostos, serão suportadas pelo Promitente Comprador.

CLÁUSULA NONA
(Foro)

Para resolução de quaisquer litígios emergentes do presente contrato, as partes elegem o foro da comarca de {property_concelho}, com expressa renúncia a qualquer outro.

Feito em duplicado, ficando cada uma das partes com um exemplar.

{property_concelho}, {data_atual}

O Promitente Vendedor:
_______________________________
{vendedor}

O(s) Promitente(s) Comprador(es):
_______________________________
{client_name}
{"_______________________________" if second_client else ""}
{second_client if second_client else ""}
"""
    
    return template.strip()


def generate_valuation_appeal_template(process: Dict[str, Any]) -> str:
    """
    Gera o texto de email para apelação/contestação de avaliação bancária.
    "Botão de Pânico" - usado quando avaliação < valor de compra.
    
    Args:
        process: Dados do processo
        
    Returns:
        Texto formatado do email de apelação
    """
    client_name = process.get("client_name", "[NOME DO CLIENTE]")
    
    # Dados do imóvel
    property_data = process.get("property_data", {})
    property_address = property_data.get("morada", "[MORADA DO IMÓVEL]")
    property_concelho = property_data.get("concelho", "[CONCELHO]")
    
    # Dados de crédito e avaliação
    credit_data = process.get("credit_data", {})
    valuation_value = credit_data.get("valuation_value", 0)
    valuation_bank = credit_data.get("valuation_bank", "[BANCO]")
    valuation_date = credit_data.get("valuation_date", "[DATA]")
    
    # Valor de compra
    financial_data = process.get("financial_data", {})
    purchase_value = financial_data.get("valor_pretendido") or property_data.get("valor_imovel", 0)
    
    # Calcular diferença
    difference = purchase_value - valuation_value if purchase_value and valuation_value else 0
    percentage = (difference / purchase_value * 100) if purchase_value else 0
    
    # Formatação
    valuation_fmt = f"{valuation_value:,.2f}".replace(",", " ").replace(".", ",") if valuation_value else "[VALOR AVALIAÇÃO]"
    purchase_fmt = f"{purchase_value:,.2f}".replace(",", " ").replace(".", ",") if purchase_value else "[VALOR COMPRA]"
    difference_fmt = f"{difference:,.2f}".replace(",", " ").replace(".", ",") if difference else "[DIFERENÇA]"
    
    template = f"""
Assunto: Pedido de Reavaliação - Processo de Crédito Habitação - {client_name}

Exmos. Senhores,

Venho por este meio solicitar a reavaliação do imóvel referente ao processo de crédito habitação do(a) cliente {client_name}.

DADOS DO IMÓVEL:
- Localização: {property_address}, {property_concelho}
- Valor de Aquisição Acordado: €{purchase_fmt}

AVALIAÇÃO ATUAL:
- Banco Avaliador: {valuation_bank}
- Data da Avaliação: {valuation_date}
- Valor Atribuído: €{valuation_fmt}

FUNDAMENTAÇÃO DO PEDIDO:

A avaliação realizada apresenta uma diferença de €{difference_fmt} ({percentage:.1f}%) face ao valor de aquisição acordado entre as partes, o que consideramos não refletir adequadamente o valor de mercado do imóvel pelos seguintes motivos:

1. COMPARÁVEIS DE MERCADO:
   [Incluir 2-3 imóveis semelhantes vendidos recentemente na zona com valores superiores]
   - Imóvel 1: [Descrição e valor]
   - Imóvel 2: [Descrição e valor]
   - Imóvel 3: [Descrição e valor]

2. CARACTERÍSTICAS DIFERENCIADORAS:
   [Listar características que valorizam o imóvel]
   - [Característica 1]
   - [Característica 2]
   - [Característica 3]

3. MELHORAMENTOS RECENTES:
   [Se aplicável, listar obras/renovações realizadas]
   - [Melhoramento 1]
   - [Melhoramento 2]

4. LOCALIZAÇÃO PRIVILEGIADA:
   [Destacar vantagens da localização]
   - Proximidade a [transportes/escolas/serviços]
   - [Outras vantagens]

Solicitamos, assim, que seja efetuada nova avaliação ao imóvel, preferencialmente por outro perito, tendo em consideração os elementos acima indicados.

Encontramo-nos disponíveis para fornecer documentação adicional que suporte este pedido, nomeadamente:
- Fotografias atualizadas do imóvel
- Documentação de obras/melhoramentos
- Estudos de mercado da zona

Agradecemos a vossa melhor atenção para este assunto e aguardamos resposta com a maior brevidade possível.

Com os melhores cumprimentos,

[ASSINATURA]
[EMPRESA]
[CONTACTOS]

---
Processo interno: {process.get('id', '[ID]')}
Cliente: {client_name}
"""
    
    return template.strip()


def generate_document_request_template(process: Dict[str, Any], missing_docs: list) -> str:
    """
    Gera email para solicitar documentos em falta ao cliente.
    
    Args:
        process: Dados do processo
        missing_docs: Lista de documentos em falta
        
    Returns:
        Texto formatado do email
    """
    client_name = process.get("client_name", "[NOME DO CLIENTE]")
    client_email = process.get("client_email", "")
    
    docs_list = "\n".join([f"   • {doc}" for doc in missing_docs]) if missing_docs else "   • [DOCUMENTOS]"
    
    template = f"""
Assunto: Documentação Necessária - Processo de Crédito Habitação

Caro(a) {client_name},

Esperamos que esteja bem.

No seguimento do seu processo de crédito habitação, vimos por este meio solicitar o envio da seguinte documentação, necessária para dar continuidade à análise:

DOCUMENTOS EM FALTA:
{docs_list}

Pedimos que envie os documentos em formato digital (PDF ou imagem) para este email, ou que os carregue diretamente na plataforma através do link do seu processo.

Caso tenha alguma dúvida sobre os documentos solicitados, não hesite em contactar-nos.

Agradecemos a sua colaboração e rapidez no envio, de forma a agilizar o processo.

Com os melhores cumprimentos,

[ASSINATURA]
[EMPRESA]
[CONTACTOS]
"""
    
    return template.strip()


def generate_deed_reminder_template(process: Dict[str, Any]) -> str:
    """
    Gera email de lembrete para escritura.
    
    Args:
        process: Dados do processo
        
    Returns:
        Texto formatado do email
    """
    client_name = process.get("client_name", "[NOME DO CLIENTE]")
    
    property_data = process.get("property_data", {})
    property_address = property_data.get("morada", "[MORADA DO IMÓVEL]")
    
    credit_data = process.get("credit_data", {})
    bank_name = credit_data.get("bank_name", "[BANCO]")
    
    # Data da escritura (se disponível)
    deed_date = process.get("deed_date", "[DATA A DEFINIR]")
    deed_location = process.get("deed_location", "[LOCAL A DEFINIR]")
    
    template = f"""
Assunto: Lembrete - Escritura de Compra e Venda

Caro(a) {client_name},

Esperamos que esteja bem.

Vimos por este meio relembrar que a escritura de compra e venda do imóvel sito em:
{property_address}

está agendada para:
- Data: {deed_date}
- Local: {deed_location}

DOCUMENTOS A LEVAR:
   • Cartão de Cidadão (original)
   • Comprovativo de IBAN
   • Comprovativo de morada atualizado
   • [Outros documentos específicos]

INFORMAÇÃO IMPORTANTE:
   • O financiamento será disponibilizado pelo {bank_name}
   • Deverá comparecer 15 minutos antes da hora marcada
   • Em caso de impossibilidade, contacte-nos com a maior antecedência possível

Caso tenha alguma dúvida, não hesite em contactar-nos.

Com os melhores cumprimentos,

[ASSINATURA]
[EMPRESA]
[CONTACTOS]
"""
    
    return template.strip()


async def get_template_for_process(
    process_id: str,
    template_type: str,
    extra_data: dict = None
) -> Dict[str, Any]:
    """
    Obtém um template preenchido para um processo.
    
    Args:
        process_id: ID do processo
        template_type: Tipo de template (cpcv, valuation_appeal, document_request, deed_reminder)
        extra_data: Dados adicionais (ex: lista de documentos em falta)
        
    Returns:
        Dict com o template e metadata
    """
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    
    if not process:
        return {"error": "Processo não encontrado", "template": None}
    
    templates = {
        "cpcv": generate_cpcv_template,
        "valuation_appeal": generate_valuation_appeal_template,
        "deed_reminder": generate_deed_reminder_template,
    }
    
    if template_type == "document_request":
        missing_docs = extra_data.get("missing_docs", []) if extra_data else []
        template_text = generate_document_request_template(process, missing_docs)
    elif template_type in templates:
        template_text = templates[template_type](process)
    else:
        return {"error": f"Tipo de template desconhecido: {template_type}", "template": None}
    
    return {
        "template_type": template_type,
        "process_id": process_id,
        "client_name": process.get("client_name"),
        "template": template_text,
        "webmail_urls": WEBMAIL_URLS,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
