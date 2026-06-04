from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import config
from ml.recommender import engine
from models.saved_place import SavedPlace
from utils.dependencies import get_verified_user
from database.session import get_db
from routes.schemas import (
    Destination, MetaResponse,
    RecommendRequest, RecommendResponse,
    SimilarRequest, SimilarResponse,
)

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


def _flag_saved(results: list[dict], user_id: str, db: Session) -> list[dict]:
    saved_places = {
        sp.place.lower()
        for sp in db.query(SavedPlace.place).filter(SavedPlace.user_id == user_id).all()
    }
    for r in results:
        r["is_saved"] = r["place"].lower() in saved_places
    return results


@router.post("", response_model=RecommendResponse, summary="Get recommendations (body)")
def recommend(
    body: RecommendRequest,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    results = engine.filter_recommend(
        budget=body.budget,
        trip_type=body.trip_type,
        month=body.month,
        days=body.days,
        crowd=body.crowd,
        top_n=body.top_n,
    )
    # Strict budget filter — only show places within exact range
    if hasattr(body, 'budget_min') and body.budget_min:
        results = [r for r in results if r["budget"] >= body.budget_min]

    return RecommendResponse(
        query=body.model_dump(),
        count=len(results),
        results=_flag_saved(results, user.id, db),
    )


@router.get("", response_model=RecommendResponse, summary="Get recommendations (query params)")
def recommend_get(
    budget_min: int = Query(0, ge=0, description="Minimum budget in INR"),
    budget    : int = Query(..., gt=0, description="Maximum budget in INR"),
    trip_type : str = Query(...),
    month     : str = Query(...),
    days      : int = Query(..., gt=0),
    crowd     : str | None = Query(None),
    top_n     : int = Query(20, ge=1, le=50),
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    # Get more results then filter strictly by budget range
    results = engine.filter_recommend(
        budget=budget,
        trip_type=trip_type,
        month=month,
        days=days,
        crowd=crowd,
        top_n=50,  # get more so filtering doesn't leave us empty
    )

    # Strict min AND max budget filter
    results = [r for r in results if budget_min <= r["budget"] <= budget]

    # If strict filter leaves nothing, relax only the min (keep max strict)
    if not results:
        results = engine.filter_recommend(
            budget=budget,
            trip_type=trip_type,
            month=month,
            days=days,
            crowd=crowd,
            top_n=50,
        )
        results = [r for r in results if r["budget"] <= budget]

    results = results[:top_n]

    return RecommendResponse(
        query={"budget_min": budget_min, "budget": budget, "trip_type": trip_type, "month": month, "days": days, "crowd": crowd},
        count=len(results),
        results=_flag_saved(results, user.id, db),
    )


@router.post("/similar", response_model=SimilarResponse, summary="Find similar destinations")
def similar(
    body: SimilarRequest,
    user=Depends(get_verified_user),
    db: Session = Depends(get_db),
):
    results = engine.similar_places(place_name=body.place, top_n=body.top_n)
    if not results and not engine.get_destination(body.place):
        raise HTTPException(status_code=404, detail=f"Place '{body.place}' not found.")
    return SimilarResponse(
        reference=body.place,
        count=len(results),
        results=_flag_saved(results, user.id, db),
    )


@router.get("/meta", response_model=MetaResponse, summary="Available filter values (public)")
def meta():
    return MetaResponse(
        trip_types=engine.available_types(),
        months=config.MONTHS,
        crowd_levels=["low", "medium", "high"],
    )