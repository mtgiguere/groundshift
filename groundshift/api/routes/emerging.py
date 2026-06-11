import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class EmergingZone(BaseModel):
    region: str
    scenario: str
    horizon_year: int
    cell_count: int
    confidence: str


class EmergingResponse(BaseModel):
    crop_id: str
    emerging_zones: list[EmergingZone]


def _load_result_files(results_dir: Path, crop_id: str) -> list[dict]:
    if not results_dir.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(results_dir.glob(f"{crop_id}_*.json"))]


def make_emerging_router(results_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/crops/{crop_id}/emerging", response_model=EmergingResponse)
    def get_emerging(crop_id: str, region: str | None = None):
        result_files = _load_result_files(results_dir, crop_id)
        if not result_files:
            raise HTTPException(
                status_code=404, detail=f"No emerging-zone results for '{crop_id}'."
            )

        zones = [EmergingZone(region=f["region"], **z) for f in result_files for z in f["zones"]]

        if region is not None:
            zones = [z for z in zones if z.region == region]
            if not zones:
                raise HTTPException(
                    status_code=404,
                    detail=f"No emerging-zone results for '{crop_id}' in region '{region}'.",
                )

        return EmergingResponse(crop_id=crop_id, emerging_zones=zones)

    return router
