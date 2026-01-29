"""
====================================================================
SERVIÇO DE EMAIL - CREDITOIMO
====================================================================
Serviço para enviar e receber emails via SMTP/IMAP.
Suporta dois servidores: Precision Crédito e Power Real Estate.
====================================================================
"""

import logging
import os
import email
import imaplib
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import re

from database import db

logger = logging.getLogger(__name__)


class EmailAccount:
    """Configuração de uma conta de email."""
    def __init__(self, name: str, imap_server: str, imap_port: int, 
                 smtp_server: str, smtp_port: int, email: str, password: str):
        self.name = name
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = email
        self.password = password


# Configuração das contas de email
def get_email_accounts() -> List[EmailAccount]:
    """Obter configuração das contas de email do ambiente."""
    accounts = []
    
    # Precision Crédito
    if os.environ.get("PRECISION_EMAIL"):
        accounts.append(EmailAccount(
            name="precision",
            imap_server=os.environ.get("PRECISION_IMAP_SERVER", "mail.precisioncredito.pt"),
            imap_port=int(os.environ.get("PRECISION_IMAP_PORT", 993)),
            smtp_server=os.environ.get("PRECISION_SMTP_SERVER", "mail.precisioncredito.pt"),
            smtp_port=int(os.environ.get("PRECISION_SMTP_PORT", 465)),
            email=os.environ.get("PRECISION_EMAIL"),
            password=os.environ.get("PRECISION_PASSWORD")
        ))
    
    # Power Real Estate
    if os.environ.get("POWER_EMAIL"):
        accounts.append(EmailAccount(
            name="power",
            imap_server=os.environ.get("POWER_IMAP_SERVER", "webmail2.hcpro.pt"),
            imap_port=int(os.environ.get("POWER_IMAP_PORT", 993)),
            smtp_server=os.environ.get("POWER_SMTP_SERVER", "webmail2.hcpro.pt"),
            smtp_port=int(os.environ.get("POWER_SMTP_PORT", 465)),
            email=os.environ.get("POWER_EMAIL"),
            password=os.environ.get("POWER_PASSWORD")
        ))
    
    return accounts


def decode_email_header(header: str) -> str:
    """Descodificar header de email."""
    if not header:
        return ""
    decoded_parts = decode_header(header)
    result = []
    for content, charset in decoded_parts:
        if isinstance(content, bytes):
            try:
                result.append(content.decode(charset or 'utf-8', errors='replace'))
            except:
                result.append(content.decode('utf-8', errors='replace'))
        else:
            result.append(content)
    return ' '.join(result)


def extract_email_address(header: str) -> str:
    """Extrair endereço de email de um header."""
    if not header:
        return ""
    # Procurar padrão <email@domain.com>
    match = re.search(r'<([^>]+)>', header)
    if match:
        return match.group(1).lower()
    # Se não encontrar, devolver o header limpo
    return header.strip().lower()


def get_email_body(msg) -> tuple:
    """Extrair corpo do email (texto e HTML)."""
    body_text = ""
    body_html = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if "attachment" not in content_disposition:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        text = payload.decode(charset, errors='replace')
                        if content_type == "text/plain":
                            body_text = text
                        elif content_type == "text/html":
                            body_html = text
                except Exception as e:
                    logger.warning(f"Erro ao extrair corpo: {e}")
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body_text = payload.decode(charset, errors='replace')
        except Exception as e:
            logger.warning(f"Erro ao extrair corpo simples: {e}")
    
    return body_text, body_html


async def fetch_emails_from_account(
    account: EmailAccount,
    client_emails: List[str],
    since_days: int = 30,
    folder: str = "INBOX"
) -> List[Dict[str, Any]]:
    """
    Buscar emails de uma conta IMAP relacionados com clientes.
    
    Args:
        account: Configuração da conta
        client_emails: Lista de emails de clientes para filtrar
        since_days: Buscar emails dos últimos X dias
        folder: Pasta IMAP (INBOX, Sent, etc.)
    
    Returns:
        Lista de emails encontrados
    """
    emails_found = []
    
    try:
        # Conectar ao servidor IMAP
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(account.imap_server, account.imap_port, ssl_context=context)
        mail.login(account.email, account.password)
        
        logger.info(f"Conectado a {account.name} ({account.email})")
        
        # Selecionar pasta
        mail.select(folder)
        
        # Calcular data de início
        since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        
        # Buscar emails
        for client_email in client_emails:
            if not client_email:
                continue
                
            # Buscar emails de/para este cliente
            for search_type in ["FROM", "TO"]:
                try:
                    _, message_numbers = mail.search(None, f'({search_type} "{client_email}" SINCE {since_date})')
                    
                    for num in message_numbers[0].split():
                        try:
                            _, msg_data = mail.fetch(num, "(RFC822)")
                            email_body = msg_data[0][1]
                            msg = email.message_from_bytes(email_body)
                            
                            # Extrair informações
                            from_email = extract_email_address(msg.get("From", ""))
                            to_emails = [extract_email_address(e) for e in (msg.get("To", "")).split(",")]
                            subject = decode_email_header(msg.get("Subject", ""))
                            date_str = msg.get("Date", "")
                            body_text, body_html = get_email_body(msg)
                            
                            # Determinar direção
                            direction = "received" if from_email == client_email else "sent"
                            
                            # Parsear data
                            try:
                                from email.utils import parsedate_to_datetime
                                sent_at = parsedate_to_datetime(date_str).isoformat()
                            except:
                                sent_at = datetime.now(timezone.utc).isoformat()
                            
                            email_data = {
                                "account": account.name,
                                "direction": direction,
                                "from_email": from_email,
                                "to_emails": to_emails,
                                "subject": subject,
                                "body": body_text or body_html,
                                "body_html": body_html,
                                "sent_at": sent_at,
                                "client_email": client_email,
                                "message_id": msg.get("Message-ID", "")
                            }
                            
                            emails_found.append(email_data)
                            
                        except Exception as e:
                            logger.warning(f"Erro ao processar email {num}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Erro na pesquisa {search_type} para {client_email}: {e}")
        
        mail.close()
        mail.logout()
        
        logger.info(f"Encontrados {len(emails_found)} emails em {account.name}")
        
    except Exception as e:
        logger.error(f"Erro ao conectar a {account.name}: {e}")
    
    return emails_found


async def sync_emails_for_process(process_id: str, days: int = 30) -> Dict[str, Any]:
    """
    Sincronizar emails para um processo específico.
    Busca emails de ambas as contas relacionados com o cliente e emails monitorizados.
    """
    # Obter processo
    process = await db.processes.find_one({"id": process_id}, {"_id": 0})
    if not process:
        return {"success": False, "error": "Processo não encontrado"}
    
    # Coletar todos os emails a monitorizar
    emails_to_monitor = []
    
    # Email principal do cliente
    client_email = process.get("client_email")
    if client_email:
        emails_to_monitor.append(client_email)
    
    # Emails adicionais monitorizados
    monitored_emails = process.get("monitored_emails", [])
    if monitored_emails:
        emails_to_monitor.extend(monitored_emails)
    
    # Remover duplicados
    emails_to_monitor = list(set([e.lower().strip() for e in emails_to_monitor if e]))
    
    if not emails_to_monitor:
        return {"success": False, "error": "Nenhum email para monitorizar"}
    
    accounts = get_email_accounts()
    if not accounts:
        return {"success": False, "error": "Nenhuma conta de email configurada"}
    
    all_emails = []
    
    # Buscar emails de todas as contas
    for account in accounts:
        # Buscar na inbox
        inbox_emails = await fetch_emails_from_account(
            account, emails_to_monitor, days, "INBOX"
        )
        all_emails.extend(inbox_emails)
        
        # Tentar buscar nos enviados
        for sent_folder in ["Sent", "INBOX.Sent", "Sent Items", "Enviados"]:
            try:
                sent_emails = await fetch_emails_from_account(
                    account, emails_to_monitor, days, sent_folder
                )
                all_emails.extend(sent_emails)
                break
            except:
                continue
    
    # Remover duplicados por Message-ID
    seen_ids = set()
    unique_emails = []
    for em in all_emails:
        msg_id = em.get("message_id", "")
        if msg_id and msg_id in seen_ids:
            continue
        if msg_id:
            seen_ids.add(msg_id)
        unique_emails.append(em)
    
    # Guardar na base de dados
    new_count = 0
    for em in unique_emails:
        # Verificar se já existe
        existing = await db.emails.find_one({
            "process_id": process_id,
            "subject": em["subject"],
            "sent_at": em["sent_at"],
            "from_email": em["from_email"]
        })
        
        if not existing:
            email_doc = {
                "id": str(uuid.uuid4()),
                "process_id": process_id,
                "direction": em["direction"],
                "from_email": em["from_email"],
                "to_emails": em["to_emails"],
                "cc_emails": [],
                "bcc_emails": [],
                "subject": em["subject"],
                "body": em["body"],
                "body_html": em.get("body_html"),
                "attachments": [],
                "status": "sent",
                "sent_at": em["sent_at"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": None,
                "notes": f"Sincronizado de {em['account']}",
                "synced": True,
                "account": em["account"]
            }
            await db.emails.insert_one(email_doc)
            new_count += 1
    
    logger.info(f"Sincronizados {new_count} novos emails para processo {process_id}")
    
    return {
        "success": True,
        "total_found": len(unique_emails),
        "new_imported": new_count,
        "process_id": process_id
    }


async def send_email(
    account_name: str,
    to_emails: List[str],
    subject: str,
    body: str,
    body_html: Optional[str] = None,
    cc_emails: Optional[List[str]] = None,
    bcc_emails: Optional[List[str]] = None,
    process_id: Optional[str] = None,
    created_by: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enviar email através de uma das contas configuradas.
    
    Args:
        account_name: "precision" ou "power"
        to_emails: Lista de destinatários
        subject: Assunto
        body: Corpo do email (texto)
        body_html: Corpo do email (HTML)
        cc_emails: CC
        bcc_emails: BCC
        process_id: ID do processo (para guardar no histórico)
        created_by: ID do utilizador que enviou
    """
    accounts = get_email_accounts()
    account = next((a for a in accounts if a.name == account_name), None)
    
    if not account:
        # Usar primeira conta disponível
        if accounts:
            account = accounts[0]
        else:
            return {"success": False, "error": "Nenhuma conta de email configurada"}
    
    try:
        # Criar mensagem
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = account.email
        msg["To"] = ", ".join(to_emails)
        
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)
        
        # Adicionar corpo
        msg.attach(MIMEText(body, "plain", "utf-8"))
        if body_html:
            msg.attach(MIMEText(body_html, "html", "utf-8"))
        
        # Enviar
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(account.smtp_server, account.smtp_port, context=context) as server:
            server.login(account.email, account.password)
            
            all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])
            server.sendmail(account.email, all_recipients, msg.as_string())
        
        logger.info(f"Email enviado via {account.name} para {to_emails}")
        
        # Guardar no histórico
        if process_id:
            email_doc = {
                "id": str(uuid.uuid4()),
                "process_id": process_id,
                "direction": "sent",
                "from_email": account.email,
                "to_emails": to_emails,
                "cc_emails": cc_emails or [],
                "bcc_emails": bcc_emails or [],
                "subject": subject,
                "body": body,
                "body_html": body_html,
                "attachments": [],
                "status": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": created_by,
                "notes": f"Enviado via {account.name}",
                "synced": False,
                "account": account.name
            }
            await db.emails.insert_one(email_doc)
        
        return {"success": True, "account": account.name}
        
    except Exception as e:
        logger.error(f"Erro ao enviar email via {account.name}: {e}")
        return {"success": False, "error": str(e)}


async def test_email_connection(account_name: str = None) -> Dict[str, Any]:
    """Testar conexão com as contas de email."""
    accounts = get_email_accounts()
    
    if account_name:
        accounts = [a for a in accounts if a.name == account_name]
    
    results = {}
    
    for account in accounts:
        result = {"imap": False, "smtp": False, "error": None}
        
        # Testar IMAP
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(account.imap_server, account.imap_port, ssl_context=context)
            mail.login(account.email, account.password)
            mail.logout()
            result["imap"] = True
        except Exception as e:
            result["error"] = f"IMAP: {str(e)}"
        
        # Testar SMTP
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(account.smtp_server, account.smtp_port, context=context) as server:
                server.login(account.email, account.password)
            result["smtp"] = True
        except Exception as e:
            if result["error"]:
                result["error"] += f"; SMTP: {str(e)}"
            else:
                result["error"] = f"SMTP: {str(e)}"
        
        results[account.name] = result
    
    return results
