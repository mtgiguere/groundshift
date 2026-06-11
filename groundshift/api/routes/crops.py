from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


class ClimateThreshold(BaseModel):
    viable_min: float
    optimal_min: float
    optimal_max: float
    viable_max: float


class ClimateEnvelope(BaseModel):
    thresholds: dict[str, ClimateThreshold]


class CropSummary(BaseModel):
    id: str
    name: str
    scientific_name: str | None = None


class CropDetail(BaseModel):
    id: str
    name: str
    scientific_name: str | None = None
    climate_envelope: ClimateEnvelope


class CropListResponse(BaseModel):
    crops: list[CropSummary]
    total: int


def make_crops_router(profiles_dir: Path) -> APIRouter:
    router = APIRouter()

    def _load_yaml(path: Path) -> dict:
        with path.open() as f:
            return yaml.safe_load(f)

    @router.get("/crops", response_model=CropListResponse)
    def list_crops():
        crops = []
        for path in sorted(profiles_dir.glob("*.yaml")):
            data = _load_yaml(path)
            crops.append(
                CropSummary(
                    id=data["crop_id"],
                    name=data["name"],
                    scientific_name=data.get("scientific_name"),
                )
            )
        return CropListResponse(crops=crops, total=len(crops))

    @router.get("/crops/{crop_id}", response_model=CropDetail)
    def get_crop(crop_id: str):
        path = profiles_dir / f"{crop_id}.yaml"
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' not found.")
        data = _load_yaml(path)
        return CropDetail(
            id=data["crop_id"],
            name=data["name"],
            scientific_name=data.get("scientific_name"),
            climate_envelope=ClimateEnvelope(
                thresholds={
                    var: ClimateThreshold(**bounds)
                    for var, bounds in data["climate_envelope"]["thresholds"].items()
                }
            ),
        )

    return router
