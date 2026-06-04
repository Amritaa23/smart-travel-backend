"""
All Pydantic schemas for request bodies and API responses.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ═══════════════════════════════════════════════════════════════════════════════
# Auth schemas
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email   : EmailStr
    name    : str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=8)


class RegisterResponse(BaseModel):
    message: str
    email  : str


class LoginRequest(BaseModel):
    email   : EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token : str
    refresh_token: str
    token_type   : str = "bearer"
    expires_in   : int


class RefreshRequest(BaseModel):
    refresh_token: str


class OTPVerifyRequest(BaseModel):
    email  : EmailStr
    code   : str = Field(..., min_length=6, max_length=6)
    purpose: str = Field("verify_email")


class OTPResendRequest(BaseModel):
    email  : EmailStr
    purpose: str = Field("verify_email")


class OTPLoginRequest(BaseModel):
    email  : EmailStr
    purpose: Literal["login"] = "login"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email       : EmailStr
    code        : str = Field(default="verified")   # optional — not checked in set-password
    new_password: str = Field(..., min_length=8)


class OTPResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id         : str
    email      : str
    name       : str
    is_verified: bool
    created_at : datetime


# ═══════════════════════════════════════════════════════════════════════════════
# Destination / ML schemas
# ═══════════════════════════════════════════════════════════════════════════════

class Destination(BaseModel):
    place      : str
    state      : str
    type       : str
    budget     : int
    days       : int
    rating     : float
    crowd      : Literal["low", "medium", "high"]
    safety     : int
    temperature: int
    best_months: str
    description: str
    lat        : float
    lon        : float
    score      : float
    is_saved   : bool = False


class RecommendRequest(BaseModel):
    budget    : int      = Field(..., gt=0)
    trip_type : str      = Field(...)
    month     : str      = Field(...)
    days      : int      = Field(..., gt=0, le=30)
    crowd     : str|None = Field(None)
    top_n     : int      = Field(5, ge=1, le=20)


class SimilarRequest(BaseModel):
    place: str = Field(...)
    top_n: int = Field(5, ge=1, le=20)


class RecommendResponse(BaseModel):
    query  : dict
    count  : int
    results: list[Destination]


class SimilarResponse(BaseModel):
    reference: str
    count    : int
    results  : list[Destination]


class PlaceListResponse(BaseModel):
    count  : int
    results: list[Destination]


class MetaResponse(BaseModel):
    trip_types  : list[str]
    months      : list[str]
    crowd_levels: list[str]


# ═══════════════════════════════════════════════════════════════════════════════
# Saved places schemas
# ═══════════════════════════════════════════════════════════════════════════════

class SavePlaceRequest(BaseModel):
    place: str = Field(...)
    note : str = Field("", max_length=500)


class UpdateNoteRequest(BaseModel):
    note: str = Field(..., max_length=500)


class SavedPlace(Destination):
    saved_id : str
    saved_at : datetime
    note     : str


class SavedPlaceListResponse(BaseModel):
    count  : int
    results: list[SavedPlace]


class SavedPlaceResponse(BaseModel):
    message: str
    saved  : SavedPlace


class CheckSavedResponse(BaseModel):
    place   : str
    is_saved: bool
    saved_id: str | None