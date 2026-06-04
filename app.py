"""
Smart Travel Recommendation System — FastAPI application entry point.

Startup sequence:
  1. Create all DB tables (idempotent)
  2. Load the ML recommender engine (CSV → CountVectorizer → cosine similarity)
  3. Register all routers
"""
from dotenv import load_dotenv
load_dotenv()
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.session import create_tables
import models  # noqa: F401 — registers User, OTP, SavedPlace with Base.metadata
from ml.recommender import engine as recommender_engine
from routes import auth, recommend, places, saved


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    create_tables()
    recommender_engine.load()
    print(f"[startup] DB tables ready. ML engine loaded — {len(recommender_engine.df)} destinations.")
    yield
    # ── Shutdown (no-op for now) ───────────────────────────────────────────────


app = FastAPI(
    title      ="Smart Travel Recommendation System",
    description="AI-powered travel recommendations for India with JWT auth, OTP, and saved places.",
    version    ="1.0.0",
    lifespan   =lifespan,
)

# ── CORS — allow all origins in dev; restrict in production ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins    =["*"],
    allow_credentials=True,
    allow_methods    =["*"],
    allow_headers    =["*"],
)


# ── Health check (no auth required) ──────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health():
    loaded = recommender_engine.df is not None
    return {
        "status"              : "ok" if loaded else "degraded",
        "destinations_loaded" : len(recommender_engine.df) if loaded else 0,
        "version"             : "1.0.0",
    }


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth.router,      prefix="/api/v1")
app.include_router(recommend.router, prefix="/api/v1")
app.include_router(places.router,    prefix="/api/v1")
app.include_router(saved.router,     prefix="/api/v1")
