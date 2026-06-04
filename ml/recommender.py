"""
Recommendation engine — faithful to ML_PROJECT-1.ipynb.

Strategy 1 — filter_recommend:
  Filters by budget, trip_type, month, days (and optional crowd), then ranks
  using the composite score:
      score = (rating x 2) + safety - (budget / 2000) + crowd_value

Strategy 2 — similar_places:
  CountVectorizer on (type + best_months + crowd + description), then
  cosine similarity to find the most similar destinations.
"""
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config


class RecommenderEngine:
    def __init__(self) -> None:
        self.df                : pd.DataFrame   = None
        self.similarity_matrix : np.ndarray     = None
        self._place_index      : dict[str, int] = {}

    # ── Startup ───────────────────────────────────────────────────────────────

    def load(self, path=config.DATA_PATH) -> None:
        df = pd.read_csv(path)

        # Normalise text columns
        for col in ("type", "best_months", "crowd", "description"):
            df[col] = (
                df[col]
                .astype(str)
                .str.lower()
                .str.strip()
                .str.replace('"', '', regex=False)
                .str.replace("'", '', regex=False)
            )

        # Force numeric columns
        df["budget"]      = pd.to_numeric(df["budget"],      errors="coerce").fillna(0).astype(int)
        df["days"]        = pd.to_numeric(df["days"],        errors="coerce").fillna(1).astype(int)
        df["rating"]      = pd.to_numeric(df["rating"],      errors="coerce").fillna(4.0)
        df["safety"]      = pd.to_numeric(df["safety"],      errors="coerce").fillna(5).astype(int)
        df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce").fillna(25).astype(int)

        # Composite score
        df["crowd_value"] = df["crowd"].map(config.CROWD_SCORE).fillna(0)
        df["score"] = (
            (df["rating"] * 2)
            + df["safety"]
            - (df["budget"] / 2000)
            + df["crowd_value"]
        )

        # NLP feature string
        df["features"] = (
            df["type"] + " "
            + df["best_months"] + " "
            + df["crowd"] + " "
            + df["description"]
        )

        df = df.reset_index(drop=True)

        # Fit vectorizer and precompute similarity matrix
        vectors = CountVectorizer(stop_words="english").fit_transform(df["features"])
        self.similarity_matrix = cosine_similarity(vectors)
        self.df           = df
        self._place_index = {p.lower(): i for i, p in enumerate(df["place"])}

    # ── Strategy 1: rule-based filter + score ranking ─────────────────────────

    def filter_recommend(
        self,
        budget    : int,
        trip_type : str,
        month     : str,
        days      : int,
        crowd     : str | None = None,
        top_n     : int = 5,
    ) -> list[dict]:
        df = self.df

        # Step 1: Type filter — always required
        type_mask = df["type"] == trip_type.lower()

        # Step 2: Budget filter — 30% flexibility
        budget_mask = df["budget"] <= budget * 1.3

        # Step 3: Days filter — 2 extra days flexibility
        days_mask = df["days"] <= days + 2

        # Step 4: Combined base mask
        mask = type_mask & budget_mask & days_mask

        # Step 5: Try adding month filter — only apply if results remain
        month_mask = df["best_months"].str.contains(month.lower(), na=False)
        if (mask & month_mask).sum() > 0:
            mask = mask & month_mask

        # Step 6: Try adding crowd filter — only apply if results remain
        if crowd:
            crowd_mask = df["crowd"] == crowd.lower()
            if (mask & crowd_mask).sum() > 0:
                mask = mask & crowd_mask
            # else: skip crowd filter, still show results

        results = df[mask].nlargest(top_n, "score")

        # Fallback — if still empty, return top of that type ignoring all filters
        if len(results) == 0:
            results = df[df["type"] == trip_type.lower()].nlargest(top_n, "score")

        return self._to_records(results)

    # ── Strategy 2: cosine similarity ─────────────────────────────────────────

    def similar_places(self, place_name: str, top_n: int = 5) -> list[dict]:
        idx = self._place_index.get(place_name.lower())
        if idx is None:
            name_lower = place_name.lower()
            candidates = [i for p, i in self._place_index.items() if name_lower in p]
            idx = candidates[0] if candidates else None
        if idx is None:
            return []

        ranked      = np.argsort(self.similarity_matrix[idx])[::-1]
        top_indices = [i for i in ranked if i != idx][:top_n]
        return self._to_records(self.df.iloc[top_indices])

    # ── Browsing helpers ──────────────────────────────────────────────────────

    def all_destinations(
        self,
        trip_type  : str | None = None,
        state      : str | None = None,
        min_budget : int | None = None,
        max_budget : int | None = None,
        crowd      : str | None = None,
    ) -> list[dict]:
        mask = pd.Series(True, index=self.df.index)
        if trip_type:
            mask &= self.df["type"] == trip_type.lower()
        if state:
            mask &= self.df["state"].str.lower().str.contains(state.lower(), na=False)
        if min_budget is not None:
            mask &= self.df["budget"] >= min_budget
        if max_budget is not None:
            mask &= self.df["budget"] <= max_budget
        if crowd:
            mask &= self.df["crowd"] == crowd.lower()
        return self._to_records(self.df[mask].sort_values("score", ascending=False))

    def get_destination(self, place_name: str) -> dict | None:
        idx = self._place_index.get(place_name.lower())
        return self._to_records(self.df.iloc[[idx]])[0] if idx is not None else None

    def available_types(self) -> list[str]:
        return sorted(self.df["type"].unique().tolist())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _to_records(self, df: pd.DataFrame) -> list[dict]:
        return df[config.DESTINATION_COLS].to_dict(orient="records")


# Module-level singleton — loaded once at app startup
engine = RecommenderEngine()