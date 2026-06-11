from pathlib import Path

from fastapi import FastAPI

from groundshift.api.routes.crops import make_crops_router

_PROFILES_DIR = Path(__file__).parents[2] / "crop_profiles"


def create_app(profiles_dir: Path = _PROFILES_DIR) -> FastAPI:
    app = FastAPI(
        title="Groundshift API",
        description="Crop climate suitability intelligence for smallholder farmers.",
        version="0.1.0",
    )
    app.include_router(make_crops_router(profiles_dir), prefix="/api/v1")
    return app


app = create_app()
