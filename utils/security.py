from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

import config

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, email: str) -> str:
    now = _utcnow()
    return jwt.encode(
        {
            "sub"  : user_id,
            "email": email,
            "type" : "access",
            "iat"  : now,
            "exp"  : now + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
        },
        config.SECRET_KEY,
        algorithm=config.ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    now = _utcnow()
    return jwt.encode(
        {
            "sub" : user_id,
            "type": "refresh",
            "iat" : now,
            "exp" : now + timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS),
        },
        config.SECRET_KEY,
        algorithm=config.ALGORITHM,
    )


def decode_token(token: str, expected_type: str) -> dict | None:
    """Decode and validate a JWT. Returns payload dict or None."""
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        return payload if payload.get("type") == expected_type else None
    except JWTError:
        return None
