"""FrostRiskPlugin — existential frost threat scored from CMIP6 min-temp projections."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

_DANGER_ZONE_C = 2.0  # linear ramp width around frost threshold

_METADATA = PluginMetadata(
    plugin_id="frost_risk",
    name="Frost Risk",
    version="0.1.0",
    description="Existential frost threat from CMIP6 minimum-temperature projections.",
    author="Groundshift",
    compatible_crops=["*"],
    data_sources=["cmip6"],
    requires_network=False,
    phase_applicability=["describe"],
    threat_tier="existential",
)


class FrostRiskPlugin(GroundshiftPlugin):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    @property
    def metadata(self) -> PluginMetadata:
        return _METADATA

    def validate_config(self, crop_profile: dict) -> bool:
        return True

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        scenario = time_range.scenario or "ssp245"
        horizon = time_range.horizon_year or 2040
        path = self._data_dir / f"frost_risk_min_temp_{scenario}_{horizon}.nc"
        if not path.exists():
            raise FileNotFoundError(f"Frost risk data not found: {path}")
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
            plugin_id="frost_risk",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "min_annual_temp_c", "source": "cmip6"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        min_temp = layer_data.data
        threshold = float(crop_profile.get("frost_threshold_c", 0.0))
        probability = ((threshold - min_temp) / _DANGER_ZONE_C).clip(0.0, 1.0)
        factor_value = xr.zeros_like(min_temp)
        confidence = xr.full_like(min_temp, 0.7)
        return SuitabilityModifier(
            plugin_id="frost_risk",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={"threat_tier": "existential", "custom_weight": 1.0},
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_prob = float(score.probability.mean())
        if mean_prob < 0.05:
            label = "low"
        elif mean_prob < 0.2:
            label = "moderate"
        else:
            label = "high"
        return f"Frost risk: {label} ({mean_prob:.0%} mean annual frost probability)"
