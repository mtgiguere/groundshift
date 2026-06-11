from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


class PackageSummary(BaseModel):
    crop_id: str
    region_id: str
    size_bytes: int


class PackagesResponse(BaseModel):
    packages: list[PackageSummary]
    total: int


def _parse_stem(stem: str) -> tuple[str, str] | None:
    """Parse crop_id and region_id from a filename stem like 'coffee_ethiopia'."""
    parts = stem.split("_", 1)
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def _load_packages(mbtiles_dir: Path) -> list[PackageSummary]:
    if not mbtiles_dir.exists():
        return []
    packages = []
    for path in sorted(mbtiles_dir.glob("*.mbtiles")):
        parsed = _parse_stem(path.stem)
        if parsed is None:
            continue
        crop_id, region_id = parsed
        packages.append(
            PackageSummary(crop_id=crop_id, region_id=region_id, size_bytes=path.stat().st_size)
        )
    return packages


def make_packages_router(mbtiles_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/packages", response_model=PackagesResponse)
    def list_packages(crop_id: str | None = None, region_id: str | None = None):
        pkgs = _load_packages(mbtiles_dir)
        if crop_id is not None:
            pkgs = [p for p in pkgs if p.crop_id == crop_id]
        if region_id is not None:
            pkgs = [p for p in pkgs if p.region_id == region_id]
        return PackagesResponse(packages=pkgs, total=len(pkgs))

    @router.get("/packages/{crop_id}/{region_id}")
    def download_package(crop_id: str, region_id: str):
        filename = f"{crop_id}_{region_id}.mbtiles"
        path = mbtiles_dir / filename
        if not path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"No package for crop='{crop_id}', region='{region_id}'.",
            )
        return FileResponse(
            path,
            media_type="application/octet-stream",
            filename=filename,
        )

    return router
