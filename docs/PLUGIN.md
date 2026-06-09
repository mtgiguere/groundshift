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

        modifier_value: float in [-1.0, 1.0]
            Positive = amplifies opportunity signal
            Negative = suppresses suitability (stress or risk)
            0.0 = no effect

        confidence: float in [0.0, 1.0]
            How much trust to give this modifier.
            Use lower values when data is sparse or methodology is uncertain.
            Be honest — a low-confidence modifier with correct sign is
            more useful than an overconfident wrong one.
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
    modifier_value: float       # [-1.0, 1.0] signed modifier
    confidence: float           # [0.0, 1.0]
    geometry: Any               # Shapely geometry or GeoDataFrame
                                # Can be spatially variable — different
                                # modifier values in different sub-regions
    metadata: dict              # Anything useful for debugging or reporting
```

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
        tws = layer_data.data

        # Negative anomaly = groundwater depletion
        # Scale to [-1.0, 0.0] range — groundwater only suppresses, never amplifies
        modifier = max(-1.0, tws.anomaly_mean / 50.0)  # normalize to cm scale
        confidence = 0.7 if tws.record_length_years >= 10 else 0.4

        return SuitabilityModifier(
            plugin_id=self.metadata.plugin_id,
            region=layer_data.region,
            modifier_value=modifier,
            confidence=confidence,
            geometry=tws.geometry,
            metadata={"anomaly_cm": tws.anomaly_mean, "record_years": tws.record_length_years}
        )

    def describe(self, score: SuitabilityModifier) -> str:
        anomaly = score.metadata.get("anomaly_cm", 0)
        if score.modifier_value < -0.5:
            return (
                f"Severe groundwater depletion detected in this region "
                f"(GRACE anomaly: {anomaly:.1f}cm below baseline). "
                f"Irrigation-dependent cultivation faces significant long-term water risk."
            )
        elif score.modifier_value < -0.2:
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

If you are adding a new crop rather than a plugin, you need a YAML crop profile. All pipeline behavior for a crop — envelope thresholds, imagery parameters, framing language — lives here.

```yaml
# crop_profiles/your_crop.yaml

# ── Identity ──────────────────────────────────────────────────────────────────
name: Arabica Coffee                     # Display name
profile_id: coffee                       # Used in CLI --crop flag
scientific_name: Coffea arabica
status: active                           # active | profile | stub
version: "1.0.0"

# Framing affects how outputs are described in reports
smallholder_weight: high                 # high | medium | low
framing:
  loss_narrative: "smallholder livelihood threat"
  gain_narrative: "emerging origin opportunity"
  transition_narrative: "cooperative relocation and transition support"

# ── Climate Envelope ──────────────────────────────────────────────────────────
# All thresholds define the VIABLE range unless noted
# optimal sub-ranges score higher within the viable range

climate_envelope:
  temp_mean_annual:
    optimal: [18, 22]         # °C
    viable:  [15, 24]         # °C
  temp_max_monthly:
    stress_threshold: 30      # °C — above this = yield stress
    fail_threshold:   34      # °C — above this = crop failure
  temp_min_monthly:
    frost_threshold:  2       # °C — below this = frost risk
  precipitation_annual:
    optimal: [1500, 2500]     # mm
    viable:  [1000, 3000]     # mm
  dry_season_months:
    max: 3                    # months with <60mm rainfall
  altitude_m:
    optimal: [1000, 2000]     # metres ASL
    viable:  [600,  2400]

# Quality scoring — separate from viability
# These affect quality grade in Prescribe phase outputs
quality_signals:
  diurnal_temp_range:
    min: 8                    # °C — drives cup quality
  rainfall_distribution: bimodal   # bimodal | unimodal | any

irrigation_dependent: false   # affects groundwater plugin compatibility

# ── Soil ─────────────────────────────────────────────────────────────────────
soil:
  ph_range: [5.5, 6.5]
  drainage: well-drained       # well-drained | moderate | any
  organic_matter: high         # high | medium | any
  texture_preference: [loam, clay-loam, sandy-loam]

# ── Imagery ───────────────────────────────────────────────────────────────────
imagery:
  ndvi_healthy_threshold: 0.55    # above = healthy canopy
  ndvi_stress_threshold:  0.40    # below = stress signal
  ndvi_failure_threshold: 0.25    # below = likely abandonment

  # When to acquire imagery for best crop signal (avoids cloud season)
  optimal_composite_season: dry_season

  # Sentinel-2 band combination for change detection
  change_detection_bands: [B8, B4, B3]   # NIR, Red, Green

  # Minimum Landsat archive years for reliable trend analysis
  min_trend_years: 10

# ── Geographies ───────────────────────────────────────────────────────────────
# Calibration anchors: permanent historical and scientific reference points.
# These exist to validate model output and calibrate the suitability pipeline.
# They are NOT claims about current or future suitability — a region can be
# a calibration anchor and a climate stress zone simultaneously.
#
# NEVER REMOVE an anchor, even if the region becomes severely climate-stressed.
# A degrading anchor is either the most important signal in the dataset,
# or evidence of a model error. Either way, you need it.
#
# Current production zones, stressed zones, and emerging zones are all
# PIPELINE OUTPUTS — detected dynamically from SPAM + imagery + suitability
# surfaces and written to dated GeoJSON files. They are never hardcoded here.
calibration_anchors:
  - id: ethiopia
    name: Ethiopia
    role: origin_center          # genetic diversity baseline, primary model ground truth
    notes: "Coffea arabica origin. Jimma, Sidama, Yirgacheffe. High suitability
            scores expected under current climate. Declining scores are a
            meaningful signal — validate before assuming model error."
  - id: colombia
    name: Colombia
    role: production_reference   # well-documented smallholder system
    notes: "Andes elevation gradient provides a natural suitability transect
            across altitude bands — ideal for validating envelope scoring."
  - id: central_america
    name: Central America
    role: stress_reference       # already-degrading zone for loss model validation
    notes: "Documented rust and heat stress already underway. Should score
            declining under current and projected climate — validates the
            loss detection pipeline."

# Emergence criteria: the thresholds the pipeline uses to detect emerging
# opportunity zones dynamically from live suitability surfaces.
# Emerging regions are OUTPUTS of the pipeline, not inputs.
# They are written to dated GeoJSON files and the database — never to this file.
# These criteria define what qualifies as "emerging" for this crop.
emergence_criteria:
  min_suitability_score: 0.65          # minimum score to qualify as emerging
  min_suitability_trend_years: 5       # positive trend must hold for this many years
  model_imagery_agreement: required    # both CMIP6 and imagery streams must agree
  min_confidence: 0.60                 # discard low-confidence signals
  max_current_cultivation_density: 0.05  # low existing cultivation = "emerging" not "established"

# Confidence tier assignment — how many agreeing signals are required
# for each confidence tier in the output. More signals = higher confidence.
emergence_confidence_tiers:
  high:   4    # all signals agree: CMIP6 + Sentinel-2 + Landsat trend + active plugins
  medium: 3    # three signals agree
  low:    2    # two signals agree (minimum to surface at all)

# ── Plugin Compatibility ───────────────────────────────────────────────────────
# Plugins that are particularly relevant for this crop
recommended_plugins:
  - climate_envelope      # always required
  - imagery               # always required
  - frost_risk            # relevant for highland zones
  - pest_disease          # coffee leaf rust is critical

# ── Data Sources ──────────────────────────────────────────────────────────────
primary_data_sources:
  - "FAO GAEZ v4 — coffee suitability baseline"
  - "World Coffee Research — Varieties Catalog climate data"
  - "CABI Crop Protection Compendium — Hemileia vastatrix"

references:
  - "Davis et al. (2012) — The impact of climate change on indigenous arabica coffee"
  - "Bunn et al. (2015) — A bitter cup: climate change profile of global production"
```

---

## Plugin Registry

To register your plugin, add it to `groundshift/plugins/registry.py`:

```python
from groundshift.plugins.stretch.groundwater.plugin import GroundwaterPlugin

PLUGIN_REGISTRY: dict[str, type[GroundshiftPlugin]] = {
    # Builtin — always available
    "climate_envelope":   ClimateEnvelopePlugin,
    "imagery":            ImageryPlugin,

    # Stretch — opt-in
    "frost_risk":         FrostRiskPlugin,
    "pest_disease":       PestDiseasePlugin,
    "groundwater":        GroundwaterPlugin,       # ← add yours here
    "phenology":          PhenologyPlugin,
    "land_tenure":        LandTenurePlugin,
    "cooperative_infra":  CooperativeInfraPlugin,
}
```

Activate a plugin for an analysis run by including it in your run config or `.env`:

```bash
GROUNDSHIFT_PLUGINS=climate_envelope,imagery,groundwater

# or via CLI
python -m groundshift run \
  --crop coffee \
  --region ethiopia \
  --plugins climate_envelope imagery groundwater
```

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

def test_score_returns_modifier_in_valid_range(mock_layer_data, coffee_profile):
    plugin = GroundwaterPlugin()
    result = plugin.score(mock_layer_data, coffee_profile)
    assert -1.0 <= result.modifier_value <= 1.0

def test_score_returns_confidence_in_valid_range(mock_layer_data, coffee_profile):
    plugin = GroundwaterPlugin()
    result = plugin.score(mock_layer_data, coffee_profile)
    assert 0.0 <= result.confidence <= 1.0

def test_describe_returns_nonempty_string(mock_modifier):
    plugin = GroundwaterPlugin()
    result = plugin.describe(mock_modifier)
    assert isinstance(result, str) and len(result) > 0

def test_describe_is_human_readable_for_severe_depletion():
    plugin = GroundwaterPlugin()
    modifier = SuitabilityModifier(
        plugin_id="groundwater",
        modifier_value=-0.8,
        confidence=0.7,
        metadata={"anomaly_cm": -42.0, "record_years": 15},
        # ... other fields
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

| Plugin ID | Description | Primary Data Source | Crops | Priority |
|---|---|---|---|---|
| `pest_disease` | Climate-driven range expansion of crop pathogens — coffee leaf rust, grapevine downy mildew, wheat blast | CABI CPC, FAO EMPRES | coffee, wine_grape, wheat | High |
| `frost_risk` | Late frost event frequency and trend from daily temperature data | ERA5 daily, GHCND station data | wine_grape, olive, coffee | High |
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
