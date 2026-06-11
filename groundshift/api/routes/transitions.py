from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from groundshift.core.opportunity.transition_recommender import TransitionRecommender


class TransitionSuggestionResponse(BaseModel):
    crop_id: str
    crop_name: str
    overlap_score: float


class TransitionsResponse(BaseModel):
    crop_id: str
    suggestions: list[TransitionSuggestionResponse]


def _load_yaml(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def make_transitions_router(profiles_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/crops/{crop_id}/transitions", response_model=TransitionsResponse)
    def get_transitions(crop_id: str):
        profile_path = profiles_dir / f"{crop_id}.yaml"
        if not profile_path.exists():
            raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' not found.")

        current = _load_yaml(profile_path)
        candidates = [
            _load_yaml(p) for p in sorted(profiles_dir.glob("*.yaml")) if p.stem != crop_id
        ]

        result = TransitionRecommender(candidates).recommend(current)
        return TransitionsResponse(
            crop_id=crop_id,
            suggestions=[
                TransitionSuggestionResponse(
                    crop_id=s.crop_id,
                    crop_name=s.crop_name,
                    overlap_score=round(s.overlap_score, 4),
                )
                for s in result.suggestions
            ],
        )

    return router
