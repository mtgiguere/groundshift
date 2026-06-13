"""GroundwaterPlugin — stress-tier aquifer depletion scored from GRACE-FO TWS anomaly."""

from pathlib import Path

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

# cm EWT at which the factor_value reaches 0 (full suppression)
_FULL_DEPLETION_CM = 50.0

_METADATA = PluginMetadata(
    plugin_id="groundwater",
    name="Groundwater Stress",
    version="0.1.0",
    description=(
        "Stress-tier aquifer depletion from GRACE-FO Terrestrial Water Storage anomaly. "
        "Negative TWS anomalies indicate below-baseline water storage, suppressing "
        "suitability in regions dependent on groundwater for irrigation or soil moisture."
    ),
    author="Groundshift",
    compatible_crops=["*"],
    data_sources=["grace_fo"],
    requires_network=False,
    phase_applicability=["describe"],
    threat_tier="stress",
)


class GroundwaterPlugin(GroundshiftPlugin):
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    @property
    def metadata(self) -> PluginMetadata:
        return _METADATA

    def validate_config(self, crop_profile: dict) -> bool:
        return True

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        # GRACE is observational — single baseline file, scenario/horizon unused.
        path = self._data_dir / "groundwater_tws_baseline.nc"
        if not path.exists():
            raise FileNotFoundError(f"Groundwater TWS data not found: {path}")
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
            plugin_id="groundwater",
            region=region,
            time_range=time_range,
            data=clipped,
            metadata={"variable": "tws_anomaly_cm", "source": "grace_fo"},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        tws = layer_data.data
        # factor_value: 1.0 at zero anomaly, 0.0 at -50cm, clamped to [0, 1]
        factor_value = (1.0 + tws / _FULL_DEPLETION_CM).clip(0.0, 1.0)
        probability = xr.ones_like(tws)
        confidence = xr.full_like(tws, 0.7)
        return SuitabilityModifier(
            plugin_id="groundwater",
            region=layer_data.region,
            factor_value=factor_value,
            probability=probability,
            confidence=confidence,
            metadata={
                "threat_tier": "stress",
                "custom_weight": 1.0,
                "mean_tws_cm": float(tws.mean()),
            },
        )

    def describe(self, score: SuitabilityModifier) -> str:
        mean_tws = score.metadata.get("mean_tws_cm", 0.0)
        mean_factor = float(score.factor_value.mean())
        if mean_factor > 0.8:
            return (
                f"Groundwater within normal range (mean GRACE-FO TWS anomaly: {mean_tws:+.1f} cm)."
            )
        elif mean_factor > 0.5:
            return (
                f"Moderate groundwater depletion detected "
                f"(GRACE-FO anomaly: {mean_tws:.1f} cm below baseline). "
                f"Water availability should be verified before long-term investment."
            )
        else:
            return (
                f"Severe groundwater depletion detected "
                f"(GRACE-FO anomaly: {mean_tws:.1f} cm below baseline). "
                f"Aquifer stress poses a significant risk to irrigation-dependent cultivation."
            )
