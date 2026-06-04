"""
Saved places routes:
  GET    /saved-places              — list user's saved destinations
  POST   /save-place                — save a destination
  GET    /saved-places/check        — check if a place is saved
  GET    /saved-places/{saved_id}   — single saved place detail
  PATCH  /saved-places/{saved_id}/note — update note
  DELETE /saved-places/{saved_id}   — remove saved place
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.session import get_db
from ml.recommender import engine
from models.saved_place import SavedPlace
from utils.dependencies import get_verified_user
from routes.schemas import (
    CheckSavedResponse, SavedPlace as SavedPlaceSchema,
    SavedPlaceListResponse, SavedPlaceResponse,
    SavePlaceRequest, UpdateNoteRequest,
)

router = APIRouter(tags=["Saved Places"])


def _enrich(sp: SavedPlace) -> SavedPlaceSchema:
    """Merge a SavedPlace ORM row with live destination data from the ML engine."""
    dest = engine.get_destination(sp.place)
    if not dest:
        raise HTTPException(
            status_code=404,
            detail=f"Destination '{sp.place}' no longer exists in the dataset.",
        )
    return SavedPlaceSchema(
        saved_id=sp.id,
        saved_at=sp.saved_at,
        note    =sp.note,
        is_saved=True,
        **dest,
    )


def _get_or_404(saved_id: str, user_id: str, db: Session) -> SavedPlace:
    sp = db.query(SavedPlace).filter(
        SavedPlace.id      == saved_id,
        SavedPlace.user_id == user_id,
    ).first()
    if not sp:
        raise HTTPException(status_code=404, detail="Saved place not found.")
    return sp


# ── List saved places ─────────────────────────────────────────────────────────

@router.get("/saved-places", response_model=SavedPlaceListResponse, summary="My saved destinations")
def list_saved_places(
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """Returns all destinations saved by the current user, enriched with full destination detail."""
    rows = db.query(SavedPlace).filter(SavedPlace.user_id == user.id).all()
    return SavedPlaceListResponse(count=len(rows), results=[_enrich(sp) for sp in rows])


# ── Save a place ──────────────────────────────────────────────────────────────

@router.post("/save-place", response_model=SavedPlaceResponse, status_code=201, summary="Save a destination")
def save_place(
    body: SavePlaceRequest,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """
    Save a destination to the user's list. Returns 409 if already saved.
    The place name is validated against the ML dataset.
    """
    dest = engine.get_destination(body.place)
    if not dest:
        raise HTTPException(
            status_code=404,
            detail=f"Destination '{body.place}' not found. Use GET /places to browse valid destinations.",
        )

    sp = SavedPlace(
        id     =str(uuid.uuid4()),
        user_id=user.id,
        place  =dest["place"],     # use canonical casing from dataset
        note   =body.note,
    )
    db.add(sp)
    try:
        db.commit()
        db.refresh(sp)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"'{dest['place']}' is already saved.")

    return SavedPlaceResponse(
        message=f"'{dest['place']}' saved successfully.",
        saved  =_enrich(sp),
    )


# ── Check if saved ────────────────────────────────────────────────────────────

@router.get("/saved-places/check", response_model=CheckSavedResponse, summary="Check if a place is saved")
def check_saved(
    place: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    """Quick boolean check — useful for toggling heart/bookmark icons in the frontend."""
    sp = db.query(SavedPlace).filter(
        SavedPlace.user_id == user.id,
        SavedPlace.place   == place,
    ).first()
    return CheckSavedResponse(
        place   =place,
        is_saved=sp is not None,
        saved_id=sp.id if sp else None,
    )


# ── Single saved place ────────────────────────────────────────────────────────

@router.get("/saved-places/{saved_id}", response_model=SavedPlaceSchema, summary="Get one saved place")
def get_saved_place(
    saved_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    return _enrich(_get_or_404(saved_id, user.id, db))


# ── Update note ───────────────────────────────────────────────────────────────

@router.patch("/saved-places/{saved_id}/note", response_model=SavedPlaceSchema, summary="Update note")
def update_note(
    saved_id: str,
    body    : UpdateNoteRequest,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    sp      = _get_or_404(saved_id, user.id, db)
    sp.note = body.note
    db.commit()
    db.refresh(sp)
    return _enrich(sp)


# ── Remove saved place ────────────────────────────────────────────────────────

@router.delete("/saved-places/{saved_id}", status_code=204, summary="Remove saved place")
def remove_saved_place(
    saved_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    sp = _get_or_404(saved_id, user.id, db)
    db.delete(sp)
    db.commit()
