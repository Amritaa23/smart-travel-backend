import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()   # loads .env from current working directory

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "newdata.csv"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/travel.db")

# ── JWT ───────────────────────────────────────────────────────────────────────
SECRET_KEY                  : str = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
ALGORITHM                   : str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES : int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS   : int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
ACCESS_TOKEN_EXPIRE_SECONDS : int = ACCESS_TOKEN_EXPIRE_MINUTES * 60

# ── OTP ───────────────────────────────────────────────────────────────────────
OTP_EXPIRE_MINUTES : int = int(os.getenv("OTP_EXPIRE_MINUTES", "10"))
OTP_LENGTH         : int = 6

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
SMTP_HOST     : str  = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     : int  = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     : str  = os.getenv("SMTP_USER", "")
SMTP_PASSWORD : str  = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     : str  = os.getenv("SMTP_FROM", "noreply@smarttravel.com")
EMAIL_ENABLED : bool = bool(SMTP_USER and SMTP_PASSWORD)

# ── ML constants ──────────────────────────────────────────────────────────────
CROWD_SCORE: dict[str, int] = {"low": 3, "medium": 2, "high": 1}
MONTHS: list[str] = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
DESTINATION_COLS: list[str] = [
    "place", "state", "type", "budget", "days", "rating",
    "crowd", "safety", "temperature", "best_months", "description",
    "lat", "lon", "score",
]
