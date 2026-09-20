import uuid
from datetime import datetime

def send_email(to: str, subject: str, body: str):
    # medium-risk: simulate success, log
    return {"success": True, "email_id": f"E{uuid.uuid4().hex[:6]}", "to": to, "subject": subject, "sent_at": datetime.utcnow().isoformat()}

def send_notification(customer_id: str, message: str, channel: str = "email"):
    return {"success": True, "customer_id": customer_id, "channel": channel, "message": message}
