
import random
import smtplib
import string
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


from sqlalchemy.orm import Session

import config
from models.otp import OTP


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=config.OTP_LENGTH))


def _send_email(to: str, subject: str, body: str) -> None:
    if not config.EMAIL_ENABLED:
        print(f"[DEV EMAIL] To: {to} | Subject: {subject}\n{body}")
        return

    import urllib.request
    import base64
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = config.SMTP_FROM
    msg["To"]      = to
    msg.attach(MIMEText(body, "html"))

    # Print OTP to logs as fallback
    print(f"[OTP EMAIL] To: {to} | Subject: {subject} | Body: {body}")
    
def _otp_email_body(purpose: str, code: str) -> tuple[str, str]:
    titles = {
        "verify_email"   : "Verify your Smart Travel account",
        "login"          : "Your Smart Travel login OTP",
        "reset_password" : "Reset your Smart Travel password",
    }
    subject = titles.get(purpose, "Your OTP code")
    body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#2563eb">Smart Travel</h2>
      <p>Your one-time code is:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1e40af;padding:16px 0">{code}</div>
      <p>This code expires in <strong>{config.OTP_EXPIRE_MINUTES} minutes</strong>.</p>
      <p style="color:#6b7280;font-size:13px">If you did not request this, please ignore this email.</p>
    </div>
    """
    return subject, body


def create_and_send_otp(db: Session, user_id: str, email: str, purpose: str) -> str:
    db.query(OTP).filter(
        OTP.email   == email,
        OTP.purpose == purpose,
        OTP.used    == False,
    ).update({"used": True})
    db.flush()

    code       = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=config.OTP_EXPIRE_MINUTES)

    otp = OTP(
        id        =str(uuid.uuid4()),
        user_id   =user_id,
        email     =email,
        code      =code,
        purpose   =purpose,
        expires_at=expires_at,
    )
    db.add(otp)
    db.commit()

    subject, body = _otp_email_body(purpose, code)
    _send_email(email, subject, body)
    return code


def verify_otp(db: Session, email: str, code: str, purpose: str) -> bool:
    otp = (
        db.query(OTP)
        .filter(
            OTP.email   == email,
            OTP.purpose == purpose,
            OTP.used    == False,
            OTP.code    == code,
        )
        .order_by(OTP.created_at.desc())
        .first()
    )
    if not otp:
        return False
    now     = datetime.now(timezone.utc)
    expires = otp.expires_at if otp.expires_at.tzinfo else otp.expires_at.replace(tzinfo=timezone.utc)
    if now > expires:
        return False
    otp.used = True
    db.commit()
    return True
