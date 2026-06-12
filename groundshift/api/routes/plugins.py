from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from groundshift.plugins.drought_stress import DroughtStressPlugin
from groundshift.plugins.frost_risk import FrostRiskPlugin
from groundshift.plugins.heat_stress import HeatStressPlugin

_KNOWN_PLUGINS = [
    (FrostRiskPlugin, "frost_risk_min_temp_*.nc"),
    (DroughtStressPlugin, "drought_stress_precip_*.nc"),
    (HeatStressPlugin, "heat_stress_mean_temp_*.nc"),
]


class PluginSummary(BaseModel):
    plugin_id: str
    name: str
    description: str
    threat_tier: str
    version: str
    status: Literal["available", "unavailable"]


class PluginListResponse(BaseModel):
    plugins: list[PluginSummary]
    total: int


def make_plugins_router(plugin_data_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/plugins", response_model=PluginListResponse)
    def list_plugins():
        plugins = []
        for plugin_cls, glob_pattern in _KNOWN_PLUGINS:
            meta = plugin_cls(plugin_data_dir).metadata
            has_data = any(plugin_data_dir.glob(glob_pattern))
            plugins.append(
                PluginSummary(
                    plugin_id=meta.plugin_id,
                    name=meta.name,
                    description=meta.description,
                    threat_tier=meta.threat_tier,
                    version=meta.version,
                    status="available" if has_data else "unavailable",
                )
            )
        return PluginListResponse(plugins=plugins, total=len(plugins))

    return router
