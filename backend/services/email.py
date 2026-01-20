import os
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Resend configuration
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')

# Check if Resend is configured
resend_configured = bool(RESEND_API_KEY)

if resend_configured:
    import resend
    resend.api_key = RESEND_API_KEY
    logger.info("Resend email service configured")
else:
    logger.warning("Resend not configured - emails will be simulated")


async def send_email_notification(to_email: str, subject: str, body: str, html: Optional[str] = None):
    """
    Send email notification using Resend or simulate if not configured.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text body (used for logging/fallback)
        html: HTML content (optional, used if Resend is configured)
    """
    from database import db
    
    # Generate HTML if not provided
    if html is None:
        html = generate_html_email(subject, body)
    
    # Log the email
    email_log = {
        "id": str(uuid.uuid4()),
        "to": to_email,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    
    if resend_configured:
        try:
            params = {
                "from": SENDER_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html
            }
            
            # Run sync SDK in thread to keep FastAPI non-blocking
            result = await asyncio.to_thread(resend.Emails.send, params)
            
            email_log["status"] = "sent"
            email_log["resend_id"] = result.get("id")
            logger.info(f"📧 Email sent to {to_email}: {subject}")
            
        except Exception as e:
            email_log["status"] = "failed"
            email_log["error"] = str(e)
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
    else:
        # Simulate email
        email_log["status"] = "simulated"
        logger.info(f"📧 EMAIL SIMULADO")
        logger.info(f"   To: {to_email}")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Body: {body[:100]}...")
    
    # Save to database
    await db.email_logs.insert_one(email_log)
    return email_log["status"] == "sent" or email_log["status"] == "simulated"


def generate_html_email(subject: str, body: str) -> str:
    """Generate a professional HTML email template."""
    
    # Convert newlines to HTML breaks
    html_body = body.replace('\n', '<br>')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f5;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 40px 20px;">
                    <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: #1e293b; padding: 30px 40px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">
                                    Power Real Estate & Precision
                                </h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px;">
                                <h2 style="margin: 0 0 20px 0; color: #1e293b; font-size: 20px; font-weight: 600;">
                                    {subject}
                                </h2>
                                <div style="color: #475569; font-size: 16px; line-height: 1.6;">
                                    {html_body}
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8fafc; padding: 20px 40px; text-align: center; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0; color: #94a3b8; font-size: 12px;">
                                    Este email foi enviado automaticamente pelo sistema Power Real Estate & Precision.
                                    <br>
                                    Por favor, não responda a este email.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


async def send_new_client_notification(client_name: str, client_email: str, client_phone: str, 
                                       process_type: str, staff_email: str, staff_name: str):
    """Send notification to staff when a new client registers."""
    
    subject = f"🆕 Novo Cliente: {client_name}"
    
    body = f"""Olá {staff_name},

Um novo cliente registou-se através do formulário público.

📋 DADOS DO CLIENTE
Nome: {client_name}
Email: {client_email}
Telefone: {client_phone}
Tipo de Processo: {process_type}

Aceda ao sistema para dar seguimento ao processo.

Cumprimentos,
Sistema Power Real Estate & Precision"""

    await send_email_notification(staff_email, subject, body)


async def send_status_update_notification(client_email: str, client_name: str, 
                                          new_status: str, process_type: str):
    """Send notification to client when their process status changes."""
    
    subject = f"📋 Atualização do seu Processo"
    
    body = f"""Olá {client_name},

O estado do seu processo de {process_type} foi atualizado.

Novo Estado: {new_status}

Em breve entraremos em contacto consigo com mais informações.

Cumprimentos,
Equipa Power Real Estate & Precision"""

    await send_email_notification(client_email, subject, body)


async def send_deadline_reminder(staff_email: str, staff_name: str, 
                                 deadline_title: str, due_date: str, 
                                 client_name: str):
    """Send deadline reminder to staff."""
    
    subject = f"⏰ Prazo a Aproximar: {deadline_title}"
    
    body = f"""Olá {staff_name},

Tem um prazo a aproximar-se:

📅 Prazo: {deadline_title}
📆 Data Limite: {due_date}
👤 Cliente: {client_name}

Por favor, verifique o processo e tome as ações necessárias.

Cumprimentos,
Sistema Power Real Estate & Precision"""

    await send_email_notification(staff_email, subject, body)
