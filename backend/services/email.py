import logging
import uuid
from datetime import datetime, timezone

from database import db


logger = logging.getLogger(__name__)


async def send_email_notification(to_email: str, subject: str, body: str):
    """Mock email service - logs instead of sending"""
    logger.info(f"📧 EMAIL NOTIFICATION")
    logger.info(f"   To: {to_email}")
    logger.info(f"   Subject: {subject}")
    logger.info(f"   Body: {body[:100]}...")
    await db.email_logs.insert_one({
        "id": str(uuid.uuid4()),
        "to": to_email,
        "subject": subject,
        "body": body,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "simulated"
    })
    return True
