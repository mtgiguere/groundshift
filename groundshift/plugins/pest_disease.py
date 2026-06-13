"""PestDiseasePlugin — existential Coffee Leaf Rust risk from CMIP6 climate projections."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

_COMPATIBLE_CROPS = {"coffee", "coffee_arabica"}

_METADATA = PluginMetadata(
    plugin_id="pest_disease",
    name="Coffee Leaf Rust Risk",
    version="0.1.0",
    description=(
        "Existential Coffee Leaf Rust (Hemileia vastatrix) risk from CMIP6-derived "
        "climate suitability index. CLR requires warm, humid conditions; warming and "
        "shifting rainfall patterns are expanding its viable range into higher altitudes "
        "where Arabica coffee is increasingly grown."
    ),
    author="Groundshift",
    compatible_crops=sorted(_COMPATIBLE_CROPS),
    data_sources=["cmip6"],
    requires_network=False,
    phase_applicability=["describe"],
    threat_tier="existential",
)


class PestDiseasePlugin(GroundshiftPlugin):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    @property
    def metadata(self) -> PluginMetadata:
        return _METADATA

    def validate_config(self, crop_profile: dict) -> bool:
        return crop_profile.get("crop_id") in _COMPATIBLE_CROPS

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        scenario = time_range.scenario or "ssp245"
        horizon = time_range.horizon_year or 2040
        path = self._data_dir / f"pest_disease_clr_{scenario}_{horizon}.nc"
        if not path.exists():
            raise FileNotFoundError(f"Pest disease CLR data not found: {path}")
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
            plugin_id="pest_disease",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "clr_risk_index", "source": "cmip6"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        clr_risk = layer_data.data
        # CLR risk IS the outbreak probability; factor_value is its complement.
        # Existential tier: when CLR strikes, the crop is lost — factor = 0.
        factor_value = xr.zeros_like(clr_risk)
        probability = clr_risk.clip(0.0, 1.0)
        confidence = xr.full_like(clr_risk, 0.65)
        return SuitabilityModifier(
            plugin_id="pest_disease",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={"threat_tier": "existential", "custom_weight": 1.0},
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_prob = float(score.probability.mean())
        if mean_prob < 0.15:
            label = "low"
            detail = "Climate conditions are unfavourable for Coffee Leaf Rust outbreaks."
        elif mean_prob < 0.60:
            label = "moderate"
            detail = (
                "Climate conditions are becoming favourable for Coffee Leaf Rust. "
                "Monitoring and preventive fungicide programmes are advisable."
            )
        else:
            label = "high"
            detail = (
                "Climate strongly favours Coffee Leaf Rust outbreaks. "
                "This is an existential threat to the harvest — resistant varieties "
                "and aggressive management are essential."
            )
        return (
            f"Coffee Leaf Rust risk: {label} ({mean_prob:.0%} mean outbreak probability). {detail}"
        )
