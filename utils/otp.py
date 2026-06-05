import random
import string
import uuid
from datetime import datetime, timedelta, timezone

import resend
from sqlalchemy.orm import Session

import config
from models.otp import OTP


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=config.OTP_LENGTH))


def _send_email(to: str, subject: str, body: str) -> None:
    if not config.EMAIL_ENABLED:
        print(f"[DEV EMAIL] To: {to} | Subject: {subject}\n{body}")
        return

    resend.api_key = config.RESEND_API_KEY
    resend.Emails.send({
        "from": "onboarding@resend.dev",
        "to": to,
        "subject": subject,
        "html": body,
    })
    print(f"[EMAIL] Sent to {to} via Resend")


def _otp_email_body(purpose: str, code: str) -> tuple[str, str]:
    titles = {
        "verify_email":   "Verify your Smart Travel account",
        "login":          "Your Smart Travel login OTP",
        "reset_password": "Reset your Smart Travel password",
    }
    subject = titles.get(purpose, "Your OTP code")
    body = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2 style="color:#1a1a4e">Smart Travel 🌏</h2>
      <p>Your one-time code is:</p>
      <div style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#1a1a4e;padding:16px 0">{code}</div>
      <p>This code expires in <strong>{config.OTP_EXPIRE_MINUTES} minutes</strong>.</p>
      <p style="color:#6b7280;font-size:13px">If you did not request this, please ignore this email.</p>
    </div>
    """
    return subject, body


def create_and_send_otp(
    db: Session, user_id: str, email: str, purpose: str
) -> str:
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