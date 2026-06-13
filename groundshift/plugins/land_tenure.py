"""LandTenurePlugin — stress-tier land tenure security from PRINDEX baseline data."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

_METADATA = PluginMetadata(
    plugin_id="land_tenure",
    name="Land Tenure Security",
    version="0.1.0",
    description=(
        "Stress-tier land tenure security from PRINDEX property-rights data. "
        "Scores the strength of land ownership and use rights for smallholder farmers. "
        "Insecure tenure suppresses the viability of long-term crop investment even where "
        "climate conditions are favorable — farmers without secure rights cannot capture "
        "the returns from multi-year perennial crops."
    ),
    author="Groundshift",
    compatible_crops=["*"],
    data_sources=["prindex"],
    requires_network=False,
    phase_applicability=["prescribe"],
    threat_tier="stress",
)


class LandTenurePlugin(GroundshiftPlugin):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    @property
    def metadata(self) -> PluginMetadata:
        return _METADATA

    def validate_config(self, crop_profile: dict) -> bool:
        return True

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        # PRINDEX is a static baseline — single file, scenario/horizon unused.
        path = self._data_dir / "land_tenure_security.nc"
        if not path.exists():
            raise FileNotFoundError(f"Land tenure security data not found: {path}")
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
            plugin_id="land_tenure",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "security_score", "source": "prindex"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        security = layer_data.data
        # factor_value IS the security score: 1.0 = fully secure, 0.0 = no rights.
        factor_value = security.clip(0.0, 1.0)
        probability = xr.ones_like(security)
        confidence = xr.full_like(security, 0.60)
        return SuitabilityModifier(
            plugin_id="land_tenure",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={
                "threat_tier": "stress",
                "custom_weight": 1.0,
                "mean_security_score": float(security.clip(0.0, 1.0).mean()),
            },
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_score = score.metadata.get("mean_security_score", float(score.factor_value.mean()))
        if mean_score >= 0.70:
            label = "secure"
            detail = (
                "Property rights and land use protections are strong in this zone. "
                "Farmers can make long-term investments in perennial crops with "
                "confidence in capturing future returns."
            )
        elif mean_score >= 0.40:
            label = "moderate"
            detail = (
                "Land tenure protections are partial or inconsistently enforced. "
                "Verify ownership and use-right security with local partners "
                "before committing to multi-year crop investments."
            )
        else:
            label = "insecure"
            detail = (
                "Weak land tenure security poses a significant risk to investment "
                "viability. Farmers in this zone may be unable to capture returns "
                "from long-lived crops due to displacement or expropriation risk."
            )
        return f"Land tenure security: {label} (mean PRINDEX score: {mean_score:.2f}). {detail}"
