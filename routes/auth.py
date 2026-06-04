"""
Authentication routes:
  POST /auth/register
  POST /auth/verify-otp
  POST /auth/resend-otp
  POST /auth/login
  POST /auth/request-login-otp
  POST /auth/login-otp
  POST /auth/refresh
  POST /auth/logout
  POST /auth/forgot-password
  POST /auth/reset-password
  POST /auth/set-password        ← new: set password after OTP verified
  DELETE /auth/delete-account    ← new: permanently delete account
  GET  /auth/me
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import config
from database.session import get_db
from models.user import User
from utils.dependencies import get_current_user, get_verified_user
from utils.otp import create_and_send_otp, verify_otp
from utils.security import (
    create_access_token, create_refresh_token,
    decode_token, hash_password, verify_password,
)
from routes.schemas import (
    ForgotPasswordRequest, LoginRequest, OTPLoginRequest,
    OTPResendRequest, OTPResponse, OTPVerifyRequest,
    RefreshRequest, RegisterRequest, RegisterResponse,
    ResetPasswordRequest, TokenResponse, UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _issue_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token =create_access_token(user.id, user.email),
        refresh_token=create_refresh_token(user.id),
        expires_in   =config.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create account and send email verification OTP."""
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        id              =str(uuid.uuid4()),
        email           =body.email,
        name            =body.name,
        hashed_password =hash_password(body.password),
        is_verified     =False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    create_and_send_otp(db, user.id, user.email, purpose="verify_email")
    return RegisterResponse(
        message="Account created. Check your email for the verification OTP.",
        email  =user.email,
    )


# ── Verify OTP ────────────────────────────────────────────────────────────────

@router.post("/verify-otp", response_model=OTPResponse)
def verify_otp_route(body: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Verify an OTP for any purpose."""
    if not verify_otp(db, body.email, body.code, body.purpose):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    if body.purpose == "verify_email":
        user = db.query(User).filter(User.email == body.email).first()
        if user:
            user.is_verified = True
            db.commit()
        return OTPResponse(message="Email verified successfully.")

    return OTPResponse(message="OTP verified.")


# ── Resend OTP ────────────────────────────────────────────────────────────────

@router.post("/resend-otp", response_model=OTPResponse)
def resend_otp(body: OTPResendRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account found for this email.")
    create_and_send_otp(db, user.id, user.email, purpose=body.purpose)
    return OTPResponse(message=f"OTP resent to {body.email}.")


# ── Password login ────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Email not verified. Use /auth/resend-otp to get a new code.",
        )
    return _issue_tokens(user)


# ── Passwordless OTP login ────────────────────────────────────────────────────

@router.post("/request-login-otp", response_model=OTPResponse)
def request_login_otp(body: OTPLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        create_and_send_otp(db, user.id, user.email, purpose="login")
    return OTPResponse(message="If that email is registered, a login OTP has been sent.")


@router.post("/login-otp", response_model=TokenResponse)
def login_with_otp(body: OTPVerifyRequest, db: Session = Depends(get_db)):
    if body.purpose != "login":
        raise HTTPException(status_code=400, detail="Purpose must be 'login'.")
    if not verify_otp(db, body.email, body.code, "login"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not user.is_verified:
        user.is_verified = True
        db.commit()

    return _issue_tokens(user)


# ── Token refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return _issue_tokens(user)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", status_code=204)
def logout():
    """Stateless logout — client discards tokens."""


# ── Forgot password ───────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=OTPResponse)
def forgot_password(body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        create_and_send_otp(db, user.id, user.email, purpose="reset_password")
    return OTPResponse(message="If that email is registered, a reset OTP has been sent.")


# ── Reset password (OTP + new password in one step) ──────────────────────────

@router.post("/reset-password", response_model=OTPResponse)
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Verify OTP and update password in one step."""
    if not verify_otp(db, body.email, body.code, "reset_password"):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return OTPResponse(message="Password reset successfully. Please log in again.")


# ── Set password (after OTP already verified separately) ─────────────────────

@router.post("/set-password", response_model=OTPResponse)
def set_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Set a new password after the reset OTP has already been verified
    via /verify-otp. The code field is ignored here.
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return OTPResponse(message="Password updated successfully. Please log in.")


# ── Delete account ────────────────────────────────────────────────────────────

@router.delete("/delete-account", status_code=204)
def delete_account(
    user: User = Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    Permanently delete the user account and ALL their data.
    Cascades to saved_places and otps via SQLAlchemy relationships.
    """
    db.delete(user)
    db.commit()


# ── Current user profile ──────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_verified_user)):
    return UserResponse(
        id         =user.id,
        email      =user.email,
        name       =user.name,
        is_verified=user.is_verified,
        created_at =user.created_at,
    )