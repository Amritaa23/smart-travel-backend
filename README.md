# Smart Travel Recommendation System — Backend

AI-powered travel destination recommender for India.  
Built with **FastAPI**, **SQLAlchemy**, **scikit-learn**, and **JWT + OTP auth**.

---

## Project Structure

```
smart_travel/
├── app.py                     # FastAPI entry point — startup, CORS, router registration
├── config.py                  # All settings (env-driven)
├── newdata.csv                # 43 Indian destinations dataset
├── requirements.txt
├── .env.example
│
├── database/
│   └── session.py             # SQLAlchemy engine, SessionLocal, Base, get_db()
│
├── models/
│   ├── user.py                # users table
│   ├── otp.py                 # otps table
│   └── saved_place.py         # saved_places table (unique user+place)
│
├── ml/
│   └── recommender.py         # RecommenderEngine — CountVectorizer + cosine similarity
│
├── utils/
│   ├── security.py            # bcrypt hashing, JWT create/decode
│   ├── otp.py                 # OTP generation, SMTP email, DB persistence
│   └── dependencies.py        # FastAPI auth dependencies (get_current_user, get_verified_user)
│
└── routes/
    ├── schemas.py             # All Pydantic request/response models
    ├── auth.py                # Authentication endpoints
    ├── recommend.py           # Recommendation endpoints
    ├── places.py              # Place browsing endpoints
    └── saved.py               # Saved places endpoints
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set SECRET_KEY at minimum
```

### 3. Run

```bash
uvicorn app:app --reload --port 8000
```

Interactive API docs → *const API = "https://smart-travel-backend-production-aedc.up.railway.app/api/v1";*

---

## All API Endpoints

### Health (public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server + ML engine status |

---

### Auth — `/api/v1/auth/...`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | ✗ | Create account → sends email OTP |
| POST | `/auth/verify-otp` | ✗ | Verify OTP (any purpose) |
| POST | `/auth/resend-otp` | ✗ | Re-send OTP |
| POST | `/auth/login` | ✗ | Email + password → tokens |
| POST | `/auth/request-login-otp` | ✗ | Send passwordless login OTP |
| POST | `/auth/login-otp` | ✗ | OTP → tokens (passwordless) |
| POST | `/auth/refresh` | ✗ | Rotate refresh → new token pair |
| POST | `/auth/logout` | ✗ | Client discards tokens |
| POST | `/auth/forgot-password` | ✗ | Send reset OTP |
| POST | `/auth/reset-password` | ✗ | OTP + new password |
| GET | `/auth/me` | ✓ | Current user profile |

---

### Recommendations — `/api/v1/recommend/...`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/recommend` | ✓ | Filter by budget/type/month/days → scored results |
| GET | `/recommend` | ✓ | Same via query params |
| POST | `/recommend/similar` | ✓ | Cosine similarity — find similar destinations |
| GET | `/recommend/meta` | ✗ | Valid types, months, crowd levels |

**Scoring formula** (exact from notebook):
```
score = (rating × 2) + safety − (budget / 2000) + crowd_value
crowd_value: low=3, medium=2, high=1
```

---

### Places — `/api/v1/...`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/places` | ✓ | List all 43 destinations (filterable) |
| GET | `/place/{name}` | ✓ | Full detail for one destination |

Query filters for `/places`: `trip_type`, `state`, `min_budget`, `max_budget`, `crowd`

---

### Saved Places — `/api/v1/...`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/saved-places` | ✓ | All saved destinations (enriched) |
| POST | `/save-place` | ✓ | Save a destination + optional note |
| GET | `/saved-places/check?place=Goa` | ✓ | Check if a destination is saved |
| GET | `/saved-places/{saved_id}` | ✓ | Single saved place detail |
| PATCH | `/saved-places/{saved_id}/note` | ✓ | Update personal note |
| DELETE | `/saved-places/{saved_id}` | ✓ | Remove saved place |

---

## Authentication Flow

```
Register → verify-otp → login → [use API with Bearer token] → refresh → logout
```

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

---

## Dataset Columns

| Column | Type | Description |
|--------|------|-------------|
| place | str | Destination name |
| state | str | Indian state |
| type | str | beach / hill / mountain / heritage / spiritual / city / adventure / wildlife |
| best_months | str | Ideal months (space-separated) |
| budget | int | Estimated cost in ₹ |
| days | int | Recommended duration |
| rating | float | 4.3 – 4.9 |
| crowd | str | low / medium / high |
| safety | int | Safety score |
| temperature | int | Avg °C |
| lat / lon | float | Coordinates |
| description | str | Short text |

---

## ML Engine

- **CountVectorizer** — tokenises `type + best_months + crowd + description`
- **Cosine Similarity** — precomputed 43×43 matrix at startup (O(1) lookups)
- Engine loaded once at startup via FastAPI `lifespan` — zero overhead per request

---

## Production Checklist

- [ ] Set a strong `SECRET_KEY` in `.env`
- [ ] Switch `DATABASE_URL` to PostgreSQL and install `psycopg2-binary`
- [ ] Set `SMTP_*` vars to enable real email OTP delivery
- [ ] Add a Redis-backed token blocklist for `/auth/logout`
- [ ] Rate-limit `/auth/resend-otp`, `/auth/login`, `/auth/request-login-otp`
- [ ] Set `allow_origins` in CORS to your frontend domain only
