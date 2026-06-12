from pathlib import Path

from fastapi import FastAPI

from groundshift.api.routes.crops import make_crops_router
from groundshift.api.routes.emerging import make_emerging_router
from groundshift.api.routes.packages import make_packages_router
from groundshift.api.routes.plugins import make_plugins_router
from groundshift.api.routes.regions import make_regions_router
from groundshift.api.routes.runs import make_runs_router
from groundshift.api.routes.transitions import make_transitions_router
from groundshift.regions.resolver import _REGISTRY

_PROFILES_DIR = Path(__file__).parents[2] / "crop_profiles"
_RESULTS_DIR = Path(__file__).parents[2] / "data" / "results" / "emerging"
_MBTILES_DIR = Path(__file__).parents[2] / "data" / "mbtiles"
_PLUGIN_DATA_DIR = Path(__file__).parents[2] / "data" / "plugin_data"


def create_app(
    profiles_dir: Path = _PROFILES_DIR,
    results_dir: Path = _RESULTS_DIR,
    mbtiles_dir: Path = _MBTILES_DIR,
    plugin_data_dir: Path = _PLUGIN_DATA_DIR,
) -> FastAPI:
    app = FastAPI(
        title="Groundshift API",
        description="Crop climate suitability intelligence for smallholder farmers.",
        version="0.1.0",
    )
    app.include_router(make_crops_router(profiles_dir), prefix="/api/v1")
    app.include_router(make_regions_router(_REGISTRY), prefix="/api/v1")
    app.include_router(make_emerging_router(results_dir), prefix="/api/v1")
    app.include_router(make_runs_router(results_dir), prefix="/api/v1")
    app.include_router(make_packages_router(mbtiles_dir), prefix="/api/v1")
    app.include_router(make_transitions_router(profiles_dir), prefix="/api/v1")
    app.include_router(make_plugins_router(plugin_data_dir), prefix="/api/v1")
    return app


app = create_app()
