import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel


class RunSummary(BaseModel):
    crop_id: str
    region_id: str
    zone_count: int


class RunsResponse(BaseModel):
    runs: list[RunSummary]
    total: int


def _load_all_runs(results_dir: Path) -> list[RunSummary]:
    if not results_dir.exists():
        return []
    runs = []
    for path in sorted(results_dir.glob("*.json")):
        data = json.loads(path.read_text())
        runs.append(
            RunSummary(
                crop_id=data["crop_id"],
                region_id=data["region"],
                zone_count=len(data["zones"]),
            )
        )
    return runs


def make_runs_router(results_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/runs", response_model=RunsResponse)
    def list_runs(crop_id: str | None = None, region_id: str | None = None):
        runs = _load_all_runs(results_dir)
        if crop_id is not None:
            runs = [r for r in runs if r.crop_id == crop_id]
        if region_id is not None:
            runs = [r for r in runs if r.region_id == region_id]
        return RunsResponse(runs=runs, total=len(runs))

    return router
