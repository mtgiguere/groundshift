# Groundshift — Plugin Development Guide

This document is for anyone who wants to build a Groundshift plugin. You do not need to understand the core pipeline to write a plugin. You need to understand this document.

For project context, see [README.md](../README.md).
For system architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## What a Plugin Does

Groundshift's core pipeline computes crop suitability from climate projections and satellite imagery. A plugin adds an additional evidence layer — pest and disease risk, frost events, groundwater stress, land tenure context, or anything else that affects whether a location is a real opportunity or a real threat for a given crop.

Plugins do not replace the core calculation. They submit **signed modifiers** — adjustments with confidence weights — that the core aggregator combines with the base score. This keeps the core stable and the plugin simple.

A plugin author's job is:
1. Know something the core doesn't (pest spread risk, aquifer depletion, frost frequency)
2. Express that knowledge as a spatial modifier for a given crop, region, and time range
3. Explain it in plain language for the reports that reach farmers and cooperatives

---

## The Plugin Contract

Every plugin implements the same Python abstract base class:

```python
from abc import ABC, abstractmethod
from groundshift.models import (
    BoundingBox,
    TimeRange,
    LayerData,
    SuitabilityModifier,
    PluginMetadata
)

class GroundshiftPlugin(ABC):

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Declare your plugin's identity and requirements.
        See PluginMetadata spec below.
        """

    @abstractmethod
    def validate_config(self, crop_profile: dict) -> bool:
        """
        Return True if your plugin can run for this crop.
        Return False (do not raise) if it cannot.

        Example: a coffee leaf rust plugin should return False
        for wine_grape or wheat.
        """

    @abstractmethod
    def fetch_data(
        self,
        region: BoundingBox,
        time_range: TimeRange
    ) -> LayerData:
        """
        Retrieve whatever external data your plugin needs.
        Return it as a LayerData object.

        Keep I/O here — keep score() pure.
        """

    @abstractmethod
    def score(
        self,
        layer_data: LayerData,
        crop_profile: dict
    ) -> SuitabilityModifier:
        """
        Compute and return a SuitabilityModifier.

        factor_value: xr.DataArray, values in [0.0, 1.0]
            Severity of the stressor at each grid cell.
            0.0 = stressor eliminates viability entirely at that cell.
            1.0 = stressor has no effect.

        probability: xr.DataArray, values in [0.0, 1.0]
            Likelihood the stressor occurs at each cell this season/horizon.

        confidence: xr.DataArray, values in [0.0, 1.0]
            Certainty of both the factor and probability estimates.
            Use lower values when data is sparse or methodology is uncertain.
            Be honest — a low-confidence modifier with correct sign is
            more useful than an overconfident wrong one.

        All three must be xr.DataArray grids. Uniform spatial coverage is fine:
            xr.DataArray(np.array([[0.8]]))
        """

    @abstractmethod
    def describe(self, score: SuitabilityModifier) -> str:
        """
        Return a plain-language explanation of what this modifier means.
        This text appears in reports read by NGO partners and cooperatives.

        Write for a non-technical reader. Avoid jargon.
        Be specific about what the modifier reflects.

        Good: "Elevated coffee leaf rust risk due to favorable humidity
               and temperature conditions in this zone. Historical outbreak
               records show three events in the past decade."

        Acceptable: Contextual numbers embedded in a plain-language sentence
               are fine — e.g. "GRACE anomaly of -42cm indicates severe
               depletion." The number supports the sentence; it is not the
               sentence. What to avoid is leading with or centering raw
               score values as if they are self-explanatory.

        Bad: "Pest modifier: -0.31 (confidence: 0.72)"
        """
```

---

## Data Models

### PluginMetadata

```python
@dataclass
class PluginMetadata:
    plugin_id: str              # Unique identifier, snake_case: "pest_disease_coffee"
    name: str                   # Human-readable: "Coffee Leaf Rust Risk"
    version: str                # Semantic version: "0.1.0"
    description: str            # One paragraph for PLUGIN.md registry
    author: str
    compatible_crops: list[str] # Crop profile IDs this plugin supports
                                # Use ["*"] to indicate all crops
    data_sources: list[str]     # Names of external data sources used
    requires_network: bool      # True if fetch_data calls external APIs
    phase_applicability: list[str]  # ["describe", "predict", "prescribe"]
                                    # Which phases this plugin is meaningful for
    threat_tier: str            # "existential" | "stress" | "custom"
                                # existential: hard ceiling — if P(stressor) * (1 - factor) > 0
                                #   reduces score to 0 regardless of climate envelope
                                # stress: multiplicative — score *= factor * probability
                                # custom: weighted blend — requires custom_weight
    custom_weight: float | None = None  # Required when threat_tier is "custom"
```

### BoundingBox

```python
@dataclass
class BoundingBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    crs: str = "EPSG:4326"
```

### TimeRange

```python
@dataclass
class TimeRange:
    start: datetime
    end: datetime
    scenario: str | None = None   # "ssp245" | "ssp585" | None for historical
    horizon_year: int | None = None  # 2040 | 2060 | 2100 | None for current
```

### LayerData

```python
@dataclass
class LayerData:
    plugin_id: str
    region: BoundingBox
    time_range: TimeRange
    data: Any                   # Your plugin's native data structure
                                # Can be a GeoDataFrame, xarray Dataset,
                                # numpy array, dict — whatever makes sense
    metadata: dict              # Source, retrieval timestamp, any provenance
```

### SuitabilityModifier

```python
@dataclass
class SuitabilityModifier:
    plugin_id: str
    region: BoundingBox
    factor_value: xr.DataArray  # [0.0, 1.0] — severity if stressor occurs
                                #   0.0 = stressor eliminates viability entirely
                                #   1.0 = stressor has no effect
    probability: xr.DataArray   # [0.0, 1.0] — likelihood stressor occurs at each cell
    confidence: xr.DataArray    # [0.0, 1.0] — certainty of factor and probability estimates
    metadata: dict              # Must include "threat_tier" (see Threat Tiers below).
                                # Include "custom_weight" if threat_tier is "custom".
```

`factor_value`, `probability`, and `confidence` are `xr.DataArray` grids — one value per
geographic cell. A uniform modifier (same value everywhere) is a scalar DataArray:
`xr.DataArray(np.array([[0.8]]))`. A spatially variable modifier uses a full grid.

**The three fields are not redundant.** A plugin can be highly confident (`confidence=0.9`)
that Coffee Leaf Rust would devastate a zone if it arrived, while the arrival probability
this season is low (`probability=0.15`). Conflating these misrepresents both the science
and the uncertainty. See Architecture docs for the full aggregation formula.

**Threat tiers must be declared in `metadata`:**

```python
metadata={
    "threat_tier": self.metadata.threat_tier,   # "existential" | "stress" | "custom"
    "custom_weight": self.metadata.custom_weight,  # required if tier is "custom"
}
```

The aggregator reads `metadata["threat_tier"]` to route each modifier into the correct
tier. If `threat_tier` is missing from `metadata`, the modifier will silently be routed
as a stress-tier modifier regardless of your declared intent. Always copy these fields
from `PluginMetadata` into the modifier's `metadata` dict in your `score()` method.

---

## Minimal Working Example

Here is the simplest possible plugin — a groundwater stress layer using GRACE satellite data:

```python
# groundshift/plugins/stretch/groundwater/plugin.py

import requests
import geopandas as gpd
from groundshift.plugins.base import GroundshiftPlugin
from groundshift.models import (
    BoundingBox, TimeRange, LayerData,
    SuitabilityModifier, PluginMetadata
)

class GroundwaterPlugin(GroundshiftPlugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            plugin_id="groundwater",
            name="Groundwater Stress (GRACE)",
            version="0.1.0",
            description=(
                "Applies a negative modifier in regions with significant "
                "aquifer depletion as measured by GRACE satellite gravity anomalies. "
                "Relevant for irrigation-dependent crops in water-stressed regions."
            ),
            author="Your Name",
            compatible_crops=["*"],   # applies to all crops
            data_sources=["NASA GRACE-FO Terrestrial Water Storage Anomaly"],
            requires_network=True,
            phase_applicability=["describe", "predict"]
        )

    def validate_config(self, crop_profile: dict) -> bool:
        # Groundwater stress is relevant for explicitly irrigation-dependent crops,
        # but also for any crop where regional groundwater depletion has been
        # documented. Crops with irrigation_dependent: false (e.g. coffee) rely
        # on rainfall, but can still be affected by aquifer depletion where
        # smallholders draw on shallow wells during dry seasons.
        #
        # We run for all crops rather than silently skipping — the score()
        # method will return a near-zero modifier with low confidence in
        # regions where depletion data is absent or mild. Silent skips hide
        # legitimate signals in edge cases (e.g. parts of Ethiopia).
        return True

    def fetch_data(
        self,
        region: BoundingBox,
        time_range: TimeRange
    ) -> LayerData:
        # Fetch GRACE TWS anomaly data for region
        # (Implementation connects to NASA GRACE data service)
        tws_data = self._fetch_grace_tws(region, time_range)

        return LayerData(
            plugin_id=self.metadata.plugin_id,
            region=region,
            time_range=time_range,
            data=tws_data,
            metadata={"source": "NASA GRACE-FO", "units": "cm equivalent water height"}
        )

    def score(
        self,
        layer_data: LayerData,
        crop_profile: dict
    ) -> SuitabilityModifier:
        import numpy as np
        import xarray as xr

        tws = layer_data.data

        # factor_value: 1.0 = no effect, 0.0 = eliminates viability entirely.
        # Groundwater depletion reduces suitability — clamp to [0, 1].
        raw_factor = 1.0 + (tws.anomaly_mean / 50.0)   # anomaly is negative → factor < 1
        factor = float(np.clip(raw_factor, 0.0, 1.0))
        conf = 0.7 if tws.record_length_years >= 10 else 0.4

        # Wrap scalars as DataArrays — the aggregator expects spatial grids.
        def _da(v: float) -> xr.DataArray:
            return xr.DataArray(np.array([[v]]))

        return SuitabilityModifier(
            plugin_id=self.metadata.plugin_id,
            region=layer_data.region,
            factor_value=_da(factor),
            probability=_da(1.0),       # groundwater depletion is a certain condition
            confidence=_da(conf),
            metadata={
                "threat_tier": self.metadata.threat_tier,     # required by aggregator
                "custom_weight": self.metadata.custom_weight, # required if tier is "custom"
                "anomaly_cm": tws.anomaly_mean,
                "record_years": tws.record_length_years,
            },
        )

    def describe(self, score: SuitabilityModifier) -> str:
        anomaly = score.metadata.get("anomaly_cm", 0)
        mean_factor = float(score.factor_value.mean())
        if mean_factor < 0.5:
            return (
                f"Severe groundwater depletion detected in this region "
                f"(GRACE anomaly: {anomaly:.1f}cm below baseline). "
                f"Irrigation-dependent cultivation faces significant long-term water risk."
            )
        elif mean_factor < 0.8:
            return (
                f"Moderate groundwater stress detected (GRACE anomaly: {anomaly:.1f}cm). "
                f"Water availability should be verified before investment decisions."
            )
        else:
            return "Groundwater levels within normal range for this region."

    def _fetch_grace_tws(self, region, time_range):
        # ... implementation
        pass
```

---

## Crop Profile Specification

If you are adding a new crop rather than a plugin, you need a YAML crop profile. The pipeline is generic — adding a crop means writing a YAML file, not touching code.

### Minimal profile (currently implemented)

The minimum required for a working profile is `crop_id` and `climate_envelope.thresholds`.
Each threshold variable maps to a `ClimateDataSource` variable name and defines a trapezoid
scoring range: scores 1.0 inside the optimal band, 0.0 outside the viable range, interpolated
in between.

```yaml
# crop_profiles/your_crop.yaml

crop_id: your_crop                       # Used in CLI --crop flag
name: Your Crop Display Name
scientific_name: Species name

climate_envelope:
  thresholds:
    mean_annual_temp_c:                  # must match a ClimateDataSource variable name
      viable_min: 15.0
      optimal_min: 18.0
      optimal_max: 24.0
      viable_max: 30.0

    annual_precipitation_mm:
      viable_min: 1200.0
      optimal_min: 1500.0
      optimal_max: 2500.0
      viable_max: 3000.0

    altitude_m:
      viable_min: 600.0
      optimal_min: 1000.0
      optimal_max: 2000.0
      viable_max: 3000.0
```

The threshold variable names (`mean_annual_temp_c`, `annual_precipitation_mm`, `altitude_m`)
must match the variable names supported by the active `ClimateDataSource`. Both
`WorldClimSource` and `ERA5Source` support exactly these three variables.

### Calibration anchors

Calibration anchors are permanent reference zones that the pipeline scores on every run
and alerts on when scores drop below expected minimums.

```yaml
# Calibration anchors: permanent historical and scientific reference points.
# These exist to validate model output — NOT to declare current suitability.
# A region can be a calibration anchor and a climate stress zone simultaneously.
#
# NEVER REMOVE an anchor, even if the region becomes severely climate-stressed.
# A degrading anchor is either the most important signal in the dataset,
# or evidence of a model error. Either way, you need it.
calibration_anchors:
  - id: yirgacheffe_sidama               # unique id, snake_case
    name: Yirgacheffe / Sidama           # human-readable name for output
    role: origin_center                  # origin_center | production_reference | stress_reference
    bbox: [37.0, 5.0, 40.0, 9.0]        # [min_lon, min_lat, max_lon, max_lat]
    notes: "Coffea arabica origin. Declining scores here are the most important
            signal the platform can produce."

  - id: colombia_huila
    name: Colombia Huila
    role: production_reference           # alert if score < 0.60
    bbox: [-76.5, 1.5, -74.5, 3.0]
    notes: "Premium Colombian arabica. Active export at scale."

  - id: central_america_stress
    name: Central America Pacific Coast
    role: stress_reference               # no minimum — declining score confirms model
    bbox: [-90.0, 13.0, -87.0, 15.0]
    notes: "Documented stress zone. High scores here indicate model failure."
```

**Role semantics:**

| Role | Expected minimum score | Alert behaviour |
|---|---|---|
| `origin_center` | 0.70 | Alert if score < 0.70 |
| `production_reference` | 0.60 | Alert if score < 0.60 |
| `stress_reference` | None | Never alerts — declining score is confirmation |

Anchors outside the current run region produce `n/a (outside region)` — not an alert.
This is safe: `NaN < 0.70` is `False` in Python.

### Full profile (planned fields)

Additional fields for imagery analysis and emergence detection will be supported in
later phases. The full specification is documented in ARCHITECTURE.md.

```yaml
# ── Imagery ───────────────────────────────────────────────────────────────────
# (Planned — Describe phase imagery pipeline)
imagery:
  ndvi_healthy_threshold: 0.55
  ndvi_stress_threshold:  0.40
  ndvi_failure_threshold: 0.25
  optimal_composite_season: dry_season
  change_detection_bands: [B8, B4, B3]
  min_trend_years: 10

# ── Emergence criteria ────────────────────────────────────────────────────────
# (Planned — Prescribe phase)
emergence_criteria:
  min_suitability_score: 0.65
  min_suitability_trend_years: 5
  model_imagery_agreement: required
  min_confidence: 0.60
  max_current_cultivation_density: 0.05
```

---

## Plugin Registry

Plugins register automatically based on whether their data files are present in `data/plugin_data/`. There is no manual registration step and no configuration file to edit.

The registration logic lives in `groundshift/plugins/auto_registry.py`:

```python
def build_plugin_registry(plugin_data_dir: Path) -> PluginRegistry:
    registry = PluginRegistry()
    if any(plugin_data_dir.glob("frost_risk_min_temp_*.nc")):
        registry.register(FrostRiskPlugin(plugin_data_dir))
    if any(plugin_data_dir.glob("drought_stress_precip_*.nc")):
        registry.register(DroughtStressPlugin(plugin_data_dir))
    if any(plugin_data_dir.glob("heat_stress_mean_temp_*.nc")):
        registry.register(HeatStressPlugin(plugin_data_dir))
    return registry
```

To ship a new plugin:

1. Implement `GroundshiftPlugin` and place the file in `groundshift/plugins/`
2. Define a sentinel file pattern that uniquely matches your plugin's data files (e.g. `my_plugin_variable_*.nc`)
3. Add a glob check for that pattern in `build_plugin_registry`
4. Run `scripts/prepare_plugin_data.py` (or your own ingest script) to place data files in `data/plugin_data/`

The plugin fires automatically on the next run. No env vars, no flags, no restarts required.

---

## Testing Requirements

Every plugin must ship with tests. Minimum required test coverage:

```python
# tests/unit/plugins/test_groundwater_plugin.py

def test_validate_config_returns_true_for_all_crops():
    # Groundwater runs for all crops — silent skips hide legitimate signals.
    # See validate_config docstring for rationale.
    plugin = GroundwaterPlugin()
    for profile in [
        {"profile_id": "coffee", "irrigation_dependent": False},
        {"profile_id": "wheat", "irrigation_dependent": True},
        {"profile_id": "wine_grape", "irrigation_dependent": False},
    ]:
        assert plugin.validate_config(profile) is True

def test_score_returns_factor_value_in_unit_range(mock_layer_data, coffee_profile):
    plugin = GroundwaterPlugin()
    result = plugin.score(mock_layer_data, coffee_profile)
    assert 0.0 <= float(result.factor_value.min()) <= float(result.factor_value.max()) <= 1.0

def test_score_returns_confidence_in_unit_range(mock_layer_data, coffee_profile):
    plugin = GroundwaterPlugin()
    result = plugin.score(mock_layer_data, coffee_profile)
    assert 0.0 <= float(result.confidence.min()) <= float(result.confidence.max()) <= 1.0

def test_describe_returns_nonempty_string(mock_modifier):
    plugin = GroundwaterPlugin()
    result = plugin.describe(mock_modifier)
    assert isinstance(result, str) and len(result) > 0

def test_describe_is_human_readable_for_severe_depletion():
    import numpy as np
    import xarray as xr
    plugin = GroundwaterPlugin()
    modifier = SuitabilityModifier(
        plugin_id="groundwater",
        region=SOME_REGION,
        factor_value=xr.DataArray(np.array([[0.2]])),   # severe depletion → low factor
        probability=xr.DataArray(np.array([[1.0]])),
        confidence=xr.DataArray(np.array([[0.7]])),
        metadata={"anomaly_cm": -42.0, "record_years": 15, "threat_tier": "stress"},
    )
    description = plugin.describe(modifier)
    # Should not contain raw numbers as the primary message
    assert "depletion" in description.lower() or "stress" in description.lower()
```

Run tests with:

```bash
pytest tests/unit/plugins/test_groundwater_plugin.py -v
```

---

## Plugin Ideas (Unimplemented)

The following plugins have been identified as high-value and are available for community development. Each has an open GitHub issue with more detail.

The following plugins have been identified as high-value. Shipped plugins (frost risk, drought stress, heat stress) are not listed here — see [ARCHITECTURE.md](ARCHITECTURE.md) for the shipped plugin index.

| Plugin ID | Description | Primary Data Source | Crops | Priority |
|---|---|---|---|---|
| `pest_disease` | Climate-driven range expansion of crop pathogens — coffee leaf rust, grapevine downy mildew, wheat blast | CABI CPC, FAO EMPRES | coffee, wine_grape, wheat | High |
| `phenology` | Flowering and harvest timing shifts from MODIS/Sentinel time series | MODIS MCD12Q2, Sentinel-2 | coffee, wine_grape | Medium |
| `groundwater` | Aquifer depletion from GRACE satellite gravity anomalies | NASA GRACE-FO | wheat, olive | Medium |
| `land_tenure` | Land ownership type context for prescribe-phase recommendations | FAO Land Tenure data, national cadasters | all | Medium |
| `cooperative_infra` | Mill, processing, and export route accessibility scoring | OSM, national cooperative registries | coffee, cocoa | High |
| `wildfire_risk` | Climate-projected wildfire risk surfaces | EFFIS, FIRMS | wine_grape, olive | Low |
| `traditional_knowledge` | Integration of documented farmer observation datasets | Various NGO/academic sources | coffee, cocoa | Research |

If you are building one of these, comment on the relevant issue before starting so we can coordinate.

---

## Questions and Contributions

Open an issue on GitHub before beginning significant plugin work. This avoids duplication and ensures the plugin will integrate cleanly with planned core changes.

Plugin contributions are welcome from domain experts, grad students, NGO data teams, and independent researchers. You do not need to be a professional software engineer — if you know the science and can write Python, the interface is designed to be accessible.

The only non-negotiable requirement is test coverage. A plugin without tests will not be merged.
