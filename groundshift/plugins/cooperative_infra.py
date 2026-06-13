"""CooperativeInfraPlugin — market/processing infrastructure accessibility, stress tier."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

_METADATA = PluginMetadata(
    plugin_id="cooperative_infra",
    name="Cooperative Infrastructure Access",
    version="0.1.0",
    description=(
        "Stress-tier market and processing infrastructure accessibility. "
        "Scores proximity to mills, wet processors, cooperative collection points, "
        "and export routes using an inverse-distance decay from OSM facility locations. "
        "A climatically suitable cell with poor infrastructure access is not a real "
        "opportunity for smallholder farmers."
    ),
    author="Groundshift",
    compatible_crops=["*"],
    data_sources=["osm"],
    requires_network=False,
    phase_applicability=["prescribe"],
    threat_tier="stress",
)


class CooperativeInfraPlugin(GroundshiftPlugin):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    @property
    def metadata(self) -> PluginMetadata:
        return _METADATA

    def validate_config(self, crop_profile: dict) -> bool:
        return True

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        # Infrastructure is static — single baseline file, scenario/horizon unused.
        path = self._data_dir / "cooperative_infra_access.nc"
        if not path.exists():
            raise FileNotFoundError(f"Cooperative infrastructure data not found: {path}")
        ds = xr.open_dataset(path)
        varname = list(ds.data_vars)[0]
        da = ds[varname]
        if "lat" in da.coords:
            da = da.rename({"lat": "y", "lon": "x"})
        clipped = da.sel(
            x=slice(region.min_lon, region.max_lon),
            y=slice(region.max_lat, region.min_lat),
        )
        return LayerData(
            plugin_id="cooperative_infra",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "access_score", "source": "osm"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        access = layer_data.data
        # factor_value IS the access score: 1.0 = fully accessible, 0.0 = inaccessible.
        # probability = 1.0: the accessibility condition is always in effect.
        factor_value = access.clip(0.0, 1.0)
        probability = xr.ones_like(access)
        confidence = xr.full_like(access, 0.7)
        return SuitabilityModifier(
            plugin_id="cooperative_infra",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={
                "threat_tier": "stress",
                "custom_weight": 1.0,
                "mean_access_score": float(access.mean()),
            },
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_access = score.metadata.get("mean_access_score", float(score.factor_value.mean()))
        if mean_access >= 0.65:
            label = "good"
            detail = (
                "Proximity to mills, processors, and export routes supports "
                "smallholder market participation in this zone."
            )
        elif mean_access >= 0.35:
            label = "limited"
            detail = (
                "Processing and market access is available but constrained. "
                "Investment in cooperative infrastructure or transport links "
                "would materially improve opportunity viability."
            )
        else:
            label = "poor"
            detail = (
                "This zone has poor access to mills, processors, and export routes. "
                "Infrastructure gaps are likely to suppress farmer returns even where "
                "climate suitability is strong."
            )
        return (
            f"Cooperative infrastructure access: {label} "
            f"(mean access score: {mean_access:.2f}). {detail}"
        )
