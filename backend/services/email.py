"""
====================================================================
EMAIL SERVICE - CREDITOIMO
====================================================================
Serviço de envio de emails com templates HTML profissionais.

Templates disponíveis:
1. Confirmação de registo (para o cliente)
2. Lista de documentos necessários
3. Aprovação de crédito
4. Notificação de novo cliente (para staff)
5. Actualização de estado
====================================================================
"""
import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List

logger = logging.getLogger(__name__)

# SMTP Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# Company info
COMPANY_NAME = "Power Real Estate & Precision Crédito"
COMPANY_WEBSITE = "https://powerealestate.pt"
COMPANY_PHONE = "+351 XXX XXX XXX"


def is_smtp_configured() -> bool:
    """Check if SMTP is properly configured"""
    return all([SMTP_SERVER, SMTP_PORT, SMTP_EMAIL, SMTP_PASSWORD])


def get_base_template(content: str, title: str = "") -> str:
    """Template HTML base com estilos consistentes."""
    return f"""
<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
        }}
        .wrapper {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
            padding: 30px 20px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .header .subtitle {{
            margin-top: 8px;
            font-size: 14px;
            color: #f5c518;
            font-weight: 500;
        }}
        .content {{
            padding: 30px;
        }}
        .greeting {{
            font-size: 18px;
            margin-bottom: 20px;
        }}
        .info-box {{
            background: #f8f9fa;
            border-left: 4px solid #1e3a5f;
            padding: 15px 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        .info-box h3 {{
            margin: 0 0 10px 0;
            color: #1e3a5f;
            font-size: 16px;
        }}
        .info-box p {{
            margin: 5px 0;
            color: #555;
        }}
        .highlight-box {{
            background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            border: 1px solid #4caf50;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}
        .highlight-box h2 {{
            color: #2e7d32;
            margin: 0 0 10px 0;
        }}
        .checklist {{
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .checklist h3 {{
            margin: 0 0 15px 0;
            color: #1e3a5f;
        }}
        .checklist ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .checklist li {{
            padding: 8px 0;
            border-bottom: 1px dashed #e0e0e0;
        }}
        .checklist li:last-child {{
            border-bottom: none;
        }}
        .btn {{
            display: inline-block;
            background: #f5c518;
            color: #1e3a5f;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 10px 0;
        }}
        .btn:hover {{
            background: #e6b800;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #e0e0e0;
        }}
        .footer p {{
            margin: 5px 0;
            font-size: 12px;
            color: #666;
        }}
        .footer .company {{
            font-weight: 600;
            color: #1e3a5f;
        }}
        .social-links {{
            margin-top: 15px;
        }}
        .social-links a {{
            color: #1e3a5f;
            text-decoration: none;
            margin: 0 10px;
        }}
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>🏠 Power Real Estate</h1>
                <p class="subtitle">& Precision Crédito</p>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p class="company">{COMPANY_NAME}</p>
                <p>Intermediação de Crédito • Consultoria Imobiliária</p>
                <p style="margin-top: 15px; font-size: 11px; color: #999;">
                    Este email foi enviado automaticamente. Por favor não responda diretamente a este email.
                </p>
            </div>
        </div>
    </div>
</body>
</html>
"""


async def send_email_notification(to_email: str, subject: str, body: str, html_body: str = None) -> bool:
    """
    Enviar email via SMTP SSL.
    
    Args:
        to_email: Email do destinatário
        subject: Assunto do email
        body: Corpo em texto simples
        html_body: Corpo em HTML (opcional)
    
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    if not is_smtp_configured():
        logger.warning(f"[EMAIL SIMULATED] SMTP not configured")
        logger.info(f"  To: {to_email}")
        logger.info(f"  Subject: {subject}")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{COMPANY_NAME} <{SMTP_EMAIL}>"
        msg["To"] = to_email
        
        # Texto simples
        part1 = MIMEText(body, "plain", "utf-8")
        msg.attach(part1)
        
        # HTML
        if html_body:
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part2)
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            # Codificar o email corretamente para suportar caracteres especiais
            server.sendmail(SMTP_EMAIL, to_email.encode('utf-8').decode('ascii', 'ignore'), msg.as_bytes())
        
        logger.info(f"[EMAIL SENT] To: {to_email}, Subject: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Failed to send email to {to_email}: {str(e)}")
        return False


# ====================================================================
# TEMPLATES DE EMAIL
# ====================================================================

async def send_registration_confirmation(client_email: str, client_name: str) -> bool:
    """
    Email de confirmação de registo para o cliente.
    Enviado imediatamente após submissão do formulário.
    """
    subject = "✅ Recebemos o seu pedido - Power Real Estate & Precision"
    
    body = f"""
Olá {client_name},

Recebemos o seu pedido de análise de crédito habitação.

A nossa equipa irá analisar a sua informação e entrará em contacto consigo brevemente, 
normalmente dentro de 24-48 horas úteis.

Enquanto aguarda, pode preparar os seguintes documentos:
- Cartão de Cidadão (frente e verso)
- Últimos 3 recibos de vencimento
- Declaração de IRS do último ano
- Extratos bancários dos últimos 3 meses

Se tiver alguma questão urgente, não hesite em contactar-nos.

Cumprimentos,
{COMPANY_NAME}
"""
    
    content = f"""
<p class="greeting">Olá <strong>{client_name}</strong>,</p>

<div class="highlight-box">
    <h2>✅ Pedido Recebido com Sucesso!</h2>
    <p>A sua solicitação foi registada no nosso sistema.</p>
</div>

<p>A nossa equipa irá analisar a sua informação e entrará em contacto consigo 
<strong>brevemente</strong>, normalmente dentro de <strong>24-48 horas úteis</strong>.</p>

<div class="info-box">
    <h3>📋 O que acontece a seguir?</h3>
    <p>1. A nossa equipa analisa o seu perfil</p>
    <p>2. Entramos em contacto para esclarecer dúvidas</p>
    <p>3. Solicitamos documentação necessária</p>
    <p>4. Apresentamos as melhores soluções de crédito</p>
</div>

<div class="checklist">
    <h3>📄 Documentos a Preparar</h3>
    <ul>
        <li>Cartão de Cidadão (frente e verso)</li>
        <li>Últimos 3 recibos de vencimento</li>
        <li>Declaração de IRS do último ano</li>
        <li>Extratos bancários dos últimos 3 meses</li>
        <li>Comprovativo de morada</li>
    </ul>
</div>

<p>Se tiver alguma questão urgente, não hesite em contactar-nos.</p>

<p>Cumprimentos,<br>
<strong>Equipa {COMPANY_NAME}</strong></p>
"""
    
    html_body = get_base_template(content, "Pedido Recebido")
    return await send_email_notification(client_email, subject, body, html_body)


async def send_documents_checklist(client_email: str, client_name: str, documents: List[str] = None) -> bool:
    """
    Email com lista de documentos necessários para crédito habitação.
    """
    subject = "📋 Lista de Documentos Necessários - Crédito Habitação"
    
    default_documents = [
        "Cartão de Cidadão (frente e verso) de todos os titulares",
        "Últimos 3 recibos de vencimento",
        "Declaração de IRS do último ano (Modelo 3)",
        "Nota de liquidação do IRS",
        "Extratos bancários dos últimos 3 meses (todas as contas)",
        "Declaração da entidade patronal (antiguidade e tipo de contrato)",
        "Comprovativo de morada atual",
        "Mapa de responsabilidades do Banco de Portugal",
        "Se tiver créditos: contratos e comprovativos de prestações",
    ]
    
    docs_list = documents or default_documents
    docs_text = "\n".join([f"- {doc}" for doc in docs_list])
    
    body = f"""
Olá {client_name},

Para avançarmos com a análise do seu crédito habitação, necessitamos dos seguintes documentos:

{docs_text}

Por favor, envie os documentos digitalizados ou fotografados com boa qualidade.

Pode responder a este email com os documentos em anexo ou entregar presencialmente.

Estamos ao dispor para qualquer esclarecimento.

Cumprimentos,
{COMPANY_NAME}
"""
    
    docs_html = "".join([f"<li>{doc}</li>" for doc in docs_list])
    
    content = f"""
<p class="greeting">Olá <strong>{client_name}</strong>,</p>

<p>Para avançarmos com a análise do seu crédito habitação, necessitamos dos seguintes documentos:</p>

<div class="checklist">
    <h3>📄 Documentos Necessários</h3>
    <ul>
        {docs_html}
    </ul>
</div>

<div class="info-box">
    <h3>💡 Dicas Importantes</h3>
    <p>• Digitalize ou fotografe com boa qualidade e iluminação</p>
    <p>• Certifique-se que todos os dados estão legíveis</p>
    <p>• Envie ficheiros em PDF, JPG ou PNG</p>
    <p>• Pode enviar por email ou entregar presencialmente</p>
</div>

<p>Quanto mais rapidamente nos enviar a documentação, mais depressa poderemos avançar com a sua proposta.</p>

<p>Estamos ao dispor para qualquer esclarecimento.</p>

<p>Cumprimentos,<br>
<strong>Equipa {COMPANY_NAME}</strong></p>
"""
    
    html_body = get_base_template(content, "Documentos Necessários")
    return await send_email_notification(client_email, subject, body, html_body)


async def send_credit_approved(
    client_email: str, 
    client_name: str, 
    bank_name: str,
    approved_amount: str,
    interest_rate: str = None,
    monthly_payment: str = None
) -> bool:
    """
    Email de notificação de aprovação de crédito.
    """
    subject = "🎉 Parabéns! O seu Crédito foi Aprovado!"
    
    details = f"Banco: {bank_name}\nValor Aprovado: {approved_amount}"
    if interest_rate:
        details += f"\nTaxa de Juro: {interest_rate}"
    if monthly_payment:
        details += f"\nPrestação Mensal: {monthly_payment}"
    
    body = f"""
Olá {client_name},

PARABÉNS! Temos excelentes notícias!

O seu crédito habitação foi APROVADO!

{details}

A nossa equipa irá entrar em contacto consigo para explicar os próximos passos 
e agendar a assinatura da documentação.

Obrigado por confiar em nós para este momento tão importante da sua vida!

Cumprimentos,
{COMPANY_NAME}
"""
    
    details_html = f"""
<p><strong>Banco:</strong> {bank_name}</p>
<p><strong>Valor Aprovado:</strong> {approved_amount}</p>
"""
    if interest_rate:
        details_html += f"<p><strong>Taxa de Juro:</strong> {interest_rate}</p>"
    if monthly_payment:
        details_html += f"<p><strong>Prestação Mensal:</strong> {monthly_payment}</p>"
    
    content = f"""
<p class="greeting">Olá <strong>{client_name}</strong>,</p>

<div class="highlight-box" style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-color: #2196f3;">
    <h2 style="color: #1565c0;">🎉 PARABÉNS!</h2>
    <p style="font-size: 18px; color: #1565c0;"><strong>O seu Crédito foi Aprovado!</strong></p>
</div>

<div class="info-box" style="border-left-color: #4caf50;">
    <h3 style="color: #2e7d32;">📋 Detalhes da Aprovação</h3>
    {details_html}
</div>

<p>A nossa equipa irá entrar em contacto consigo para explicar os <strong>próximos passos</strong> 
e agendar a assinatura da documentação.</p>

<div class="info-box">
    <h3>🏠 Próximos Passos</h3>
    <p>1. Reunião para revisão das condições</p>
    <p>2. Assinatura do contrato de crédito</p>
    <p>3. Agendamento da escritura</p>
    <p>4. Entrega das chaves da sua nova casa!</p>
</div>

<p>Obrigado por confiar em nós para este momento tão importante da sua vida!</p>

<p>Cumprimentos,<br>
<strong>Equipa {COMPANY_NAME}</strong></p>
"""
    
    html_body = get_base_template(content, "Crédito Aprovado")
    return await send_email_notification(client_email, subject, body, html_body)


async def send_new_client_notification(
    client_name: str,
    client_email: str,
    client_phone: str,
    process_type: str,
    staff_email: str,
    staff_name: str
) -> bool:
    """Notificação para staff sobre novo cliente registado."""
    
    subject = f"🆕 Novo Cliente: {client_name}"
    
    body = f"""
Olá {staff_name},

Foi registado um novo cliente no sistema:

Nome: {client_name}
Email: {client_email}
Telefone: {client_phone}
Tipo de Processo: {process_type}

Aceda à plataforma para ver todos os detalhes e dar seguimento.

Cumprimentos,
Sistema CreditoIMO
"""
    
    content = f"""
<p class="greeting">Olá <strong>{staff_name}</strong>,</p>

<p>Foi registado um <strong>novo cliente</strong> no sistema:</p>

<div class="info-box">
    <h3>👤 Dados do Cliente</h3>
    <p><strong>Nome:</strong> {client_name}</p>
    <p><strong>Email:</strong> <a href="mailto:{client_email}">{client_email}</a></p>
    <p><strong>Telefone:</strong> <a href="tel:{client_phone}">{client_phone}</a></p>
    <p><strong>Tipo de Processo:</strong> {process_type}</p>
</div>

<p style="text-align: center; margin-top: 25px;">
    <a href="#" class="btn">Aceder à Plataforma</a>
</p>

<p>Cumprimentos,<br>
<strong>Sistema CreditoIMO</strong></p>
"""
    
    html_body = get_base_template(content, "Novo Cliente")
    return await send_email_notification(staff_email, subject, body, html_body)


async def send_status_update_notification(
    client_email: str,
    client_name: str,
    new_status: str,
    message: str = ""
) -> bool:
    """Notificação de actualização de estado para o cliente."""
    
    subject = f"📋 Atualização do seu Processo - {new_status}"
    
    body = f"""
Olá {client_name},

O estado do seu processo foi atualizado para: {new_status}

{message if message else ''}

Para mais informações, entre em contacto connosco.

Cumprimentos,
{COMPANY_NAME}
"""
    
    message_html = f"<p>{message}</p>" if message else ""
    
    content = f"""
<p class="greeting">Olá <strong>{client_name}</strong>,</p>

<div class="info-box">
    <h3>📋 Atualização do Processo</h3>
    <p>O estado do seu processo foi atualizado para:</p>
    <p style="font-size: 18px; font-weight: bold; color: #1e3a5f;">{new_status}</p>
</div>

{message_html}

<p>Para mais informações, não hesite em contactar-nos.</p>

<p>Cumprimentos,<br>
<strong>Equipa {COMPANY_NAME}</strong></p>
"""
    
    html_body = get_base_template(content, "Atualização do Processo")
    return await send_email_notification(client_email, subject, body, html_body)
