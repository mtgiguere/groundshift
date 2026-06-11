from pathlib import Path

from fastapi import FastAPI

from groundshift.api.routes.crops import make_crops_router
from groundshift.api.routes.emerging import make_emerging_router
from groundshift.api.routes.regions import make_regions_router
from groundshift.regions.resolver import _REGISTRY

_PROFILES_DIR = Path(__file__).parents[2] / "crop_profiles"
_RESULTS_DIR = Path(__file__).parents[2] / "data" / "results" / "emerging"


def create_app(
    profiles_dir: Path = _PROFILES_DIR,
    results_dir: Path = _RESULTS_DIR,
) -> FastAPI:
    app = FastAPI(
        title="Groundshift API",
        description="Crop climate suitability intelligence for smallholder farmers.",
        version="0.1.0",
    )
    app.include_router(make_crops_router(profiles_dir), prefix="/api/v1")
    app.include_router(make_regions_router(_REGISTRY), prefix="/api/v1")
    app.include_router(make_emerging_router(results_dir), prefix="/api/v1")
    return app


app = create_app()
