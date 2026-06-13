"""PhenologyPlugin — stress-tier GDD-based phenological synchrony from CMIP6 projections."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

_METADATA = PluginMetadata(
    plugin_id="phenology",
    name="Phenological Synchrony",
    version="0.1.0",
    description=(
        "Stress-tier phenological synchrony from CMIP6 Growing Degree Day projections. "
        "Scores how well projected heat accumulation aligns with the crop's optimal "
        "phenological window, identifying regions where climate change may shift "
        "flowering, fruiting, or harvest timing outside viable bounds."
    ),
    author="Groundshift",
    compatible_crops=["*"],
    data_sources=["cmip6"],
    requires_network=False,
    phase_applicability=["describe"],
    threat_tier="stress",
)

_GDD_SCALE = 365.0  # mean annual temp (°C) × 365 → annual GDD (base 0°C)


def _gdd_thresholds(crop_profile: dict) -> tuple[float, float, float, float]:
    thresholds = crop_profile.get("climate_envelope", {}).get("thresholds", {})
    temp = thresholds.get("mean_annual_temp_c", {})
    viable_min = max(0.0, float(temp.get("viable_min", 0.0))) * _GDD_SCALE
    optimal_min = max(0.0, float(temp.get("optimal_min", 0.0))) * _GDD_SCALE
    optimal_max = max(0.0, float(temp.get("optimal_max", 40.0))) * _GDD_SCALE
    viable_max = max(0.0, float(temp.get("viable_max", 50.0))) * _GDD_SCALE
    return viable_min, optimal_min, optimal_max, viable_max


class PhenologyPlugin(GroundshiftPlugin):
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
        path = self._data_dir / f"phenology_gdd_{scenario}_{horizon}.nc"
        if not path.exists():
            raise FileNotFoundError(f"Phenology GDD data not found: {path}")
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
            plugin_id="phenology",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "annual_gdd", "source": "cmip6"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        gdd = layer_data.data
        viable_min, optimal_min, optimal_max, viable_max = _gdd_thresholds(crop_profile)

        ramp_up_width = max(optimal_min - viable_min, 1.0)
        ramp_down_width = max(viable_max - optimal_max, 1.0)
        ramp_up = ((gdd - viable_min) / ramp_up_width).clip(0.0, 1.0)
        ramp_down = ((viable_max - gdd) / ramp_down_width).clip(0.0, 1.0)

        factor_value = xr.where(
            gdd < viable_min,
            0.0,
            xr.where(
                gdd < optimal_min,
                ramp_up,
                xr.where(gdd <= optimal_max, 1.0, ramp_down),
            ),
        )
        probability = xr.ones_like(gdd)
        confidence = xr.full_like(gdd, 0.65)
        return SuitabilityModifier(
            plugin_id="phenology",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={
                "threat_tier": "stress",
                "custom_weight": 1.0,
                "mean_gdd": float(gdd.mean()),
            },
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_factor = float(score.factor_value.mean())
        mean_gdd = score.metadata.get("mean_gdd", 0.0)
        if mean_factor >= 0.85:
            return (
                f"Phenological synchrony: optimal. Heat accumulation ({mean_gdd:.0f} GDD) "
                f"aligns closely with the crop's development window."
            )
        elif mean_factor >= 0.4:
            return (
                f"Phenological synchrony: moderate stress ({mean_gdd:.0f} GDD). "
                f"Heat accumulation is shifting outside the crop's optimal window; "
                f"flowering or harvest timing may become less predictable."
            )
        else:
            return (
                f"Phenological synchrony: significant stress ({mean_gdd:.0f} GDD). "
                f"Projected heat accumulation falls substantially outside the crop's "
                f"viable development window, threatening seasonal timing reliability."
            )
