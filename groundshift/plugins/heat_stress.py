"""HeatStressPlugin — stress-tier heat threat scored from CMIP6 mean-temperature projections."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

_RAMP_WIDTH_C = 5.0  # linear ramp over 5°C above threshold

_METADATA = PluginMetadata(
    plugin_id="heat_stress",
    name="Heat Stress",
    version="0.1.0",
    description="Stress-tier heat damage from CMIP6 mean-temperature projections.",
    author="Groundshift",
    compatible_crops=["*"],
    data_sources=["cmip6"],
    requires_network=False,
    phase_applicability=["describe"],
    threat_tier="stress",
)


class HeatStressPlugin(GroundshiftPlugin):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    @property
    def metadata(self) -> PluginMetadata:
        return _METADATA

    def validate_config(self, crop_profile: dict) -> bool:
        return "heat_max_threshold_c" in crop_profile

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        scenario = time_range.scenario or "ssp245"
        horizon = time_range.horizon_year or 2040
        path = self._data_dir / f"heat_stress_mean_temp_{scenario}_{horizon}.nc"
        if not path.exists():
            raise FileNotFoundError(f"Heat stress data not found: {path}")
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
            plugin_id="heat_stress",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "mean_annual_temp_c", "source": "cmip6"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        mean_temp = layer_data.data
        threshold = float(crop_profile["heat_max_threshold_c"])
        probability = ((mean_temp - threshold) / _RAMP_WIDTH_C).clip(0.0, 1.0)
        factor_value = 1.0 - probability
        confidence = xr.full_like(mean_temp, 0.75)
        return SuitabilityModifier(
            plugin_id="heat_stress",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={"threat_tier": "stress", "custom_weight": 1.0},
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_prob = float(score.probability.mean())
        if mean_prob < 0.05:
            label = "low"
        elif mean_prob < 0.3:
            label = "moderate"
        else:
            label = "high"
        return f"Heat stress: {label} ({mean_prob:.0%} mean heat stress probability)"
