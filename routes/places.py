"""
Place browsing routes:
  GET /places            — list all destinations (with filters)
  GET /place/{name}      — single destination detail
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.session import get_db
from ml.recommender import engine
from models.saved_place import SavedPlace
from utils.dependencies import get_verified_user
from routes.schemas import Destination, PlaceListResponse

router = APIRouter(tags=["Places"])


def _is_saved(place: str, user_id: str, db: Session) -> bool:
    return db.query(SavedPlace).filter(
        SavedPlace.user_id == user_id,
        SavedPlace.place   == place,
    ).first() is not None


@router.get("/places", response_model=PlaceListResponse, summary="List all destinations")
def list_places(
    search    : str|None = Query(None, description="Search by place name, state or description"),
    trip_type : str|None = Query(None),
    state     : str|None = Query(None),
    min_budget: int|None = Query(None),
    max_budget: int|None = Query(None),
    crowd     : str|None = Query(None),
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    results = engine.all_destinations(
        trip_type=trip_type, state=state,
        min_budget=min_budget, max_budget=max_budget, crowd=crowd,
    )

    # Search filter — matches place name, state, or description
    if search and search.strip():
        term = search.lower().strip()
        results = [
            r for r in results
            if term in r["place"].lower()
            or term in r["state"].lower()
            or term in r["description"].lower()
        ]

    saved_set = {
        sp.place.lower()
        for sp in db.query(SavedPlace.place).filter(SavedPlace.user_id == user.id).all()
    }
    for r in results:
        r["is_saved"] = r["place"].lower() in saved_set

    return PlaceListResponse(count=len(results), results=results)


@router.get("/place/{place_name}", response_model=Destination, summary="Get destination detail")
def get_place(
    place_name: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    result = engine.get_destination(place_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Destination '{place_name}' not found.")
    result["is_saved"] = _is_saved(result["place"], user.id, db)
    return result