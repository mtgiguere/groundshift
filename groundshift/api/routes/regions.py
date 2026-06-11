from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from groundshift.models.bounding_box import BoundingBox


class RegionBbox(BaseModel):
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float


class RegionSummary(BaseModel):
    id: str
    name: str
    bbox: RegionBbox


class RegionListResponse(BaseModel):
    regions: list[RegionSummary]
    total: int


def _display_name(region_id: str) -> str:
    return region_id.replace("_", " ").title()


def _to_bbox(bb: BoundingBox) -> RegionBbox:
    return RegionBbox(
        min_lon=bb.min_lon, min_lat=bb.min_lat, max_lon=bb.max_lon, max_lat=bb.max_lat
    )


def make_regions_router(registry: dict[str, BoundingBox]) -> APIRouter:
    router = APIRouter()

    @router.get("/regions", response_model=RegionListResponse)
    def list_regions():
        regions = [
            RegionSummary(id=region_id, name=_display_name(region_id), bbox=_to_bbox(bb))
            for region_id, bb in sorted(registry.items())
        ]
        return RegionListResponse(regions=regions, total=len(regions))

    @router.get("/regions/{region_id}", response_model=RegionSummary)
    def get_region(region_id: str):
        if region_id not in registry:
            raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found.")
        bb = registry[region_id]
        return RegionSummary(id=region_id, name=_display_name(region_id), bbox=_to_bbox(bb))

    return router
