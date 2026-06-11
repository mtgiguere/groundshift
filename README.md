# Groundshift

**The ground is shifting under the world's smallholder farmers. Groundshift maps where — and what to do about it.**

Groundshift is an open geospatial intelligence platform that combines climate projections, satellite imagery, and agronomic science to track where crops are gaining and losing viability as the climate shifts. It is built for the NGOs, cooperatives, researchers, and extension services that work directly with the farmers most affected.

The platform is not just a loss map. Climate change is a redistribution story — some regions lose, others gain, and the transition zones in between are where the most urgent decisions are being made right now. Groundshift illuminates all three.

---

## The Problem

A smallholder coffee farmer in southern Ethiopia is making 20-year land investment decisions with no access to the same climate intelligence that institutional investors use. Her cooperative doesn't know that suitability in her valley has been quietly declining since 2015, or that a highland 200km north is emerging as a viable coffee zone with no experienced growers. That information asymmetry costs livelihoods.

Groundshift is built to close that gap.

---

## What Groundshift Does

For any supported crop and region, Groundshift produces a three-phase analysis:

**Describe** — Where are we now? Current crop suitability mapped against observed satellite signals. Where do models and ground truth agree? Where do they diverge, and what does that tell us?

**Predict** — Where are we heading? CMIP6 climate projections at two emission scenarios (SSP2-4.5 and SSP5-8.5) mapped against crop climate envelopes through 2100. Confidence surfaces included — we are honest about uncertainty.

**Prescribe** — What should happen next? Opportunity zones where suitability is emerging, transition recommendations for stressed regions, and the infrastructure and market-access context that determines whether an opportunity is real or theoretical.

---

## Anchor Crop: Coffee

Groundshift launches with Arabica coffee (*Coffea arabica*) as its anchor crop, for three reasons:

- It is the world's most traded smallholder commodity, supporting 125 million livelihoods
- Its climate envelope is narrow and well-documented, making it an ideal test case
- The stress signals are already measurable — this is not a future problem

Additional crop profiles (wine grape, olive, wheat, cocoa, tea) are included in the repository and follow the same pipeline.

---

## Key Capabilities

- **Crop climate envelope modeling** — temperature, precipitation, altitude thresholds with trapezoid scoring (viable min/max, optimal min/max)
- **Multiple climate data sources** — WorldClim v2.1 (1970–2000 baseline) and ERA5 reanalysis (2015–present) both implement the same `ClimateDataSource` interface; swap with `--source era5`
- **Calibration anchor monitoring** — named reference zones (origin centers, production references, stress references) scored on every run; alerts fire when a documented high-suitability zone drops below threshold
- **Satellite imagery divergence** — Sentinel-2 NDVI composites compared against the climate suitability score; the signed divergence surface shows where model and ground truth agree or disagree; add `--imagery sentinel2`
- **CMIP6 suitability projection** — SSP2 and SSP5 scenarios, 2040 / 2060 / 2100 horizons; run with `--phase predict`
- **Climate change delta surfaces** — signed per-cell suitability change (projected − current) per scenario and horizon; run with `--phase prescribe`
- **Opportunity zone detection** — cells currently low-suitability but meaningfully gaining; appended to every Prescribe run
- **Landsat historical NDVI trend** — per-pixel OLS slope over the full Landsat archive (1985–present); add `--imagery landsat`
- **Loss zone detection** — cells currently viable but meaningfully declining under projected scenarios; appended to every Prescribe run alongside opportunity zones
- **Transition recommendations** — for losing regions, ranks alternative crops by Jaccard overlap of viable climate envelopes; the higher the score, the more similar the climate requirements
- **REST API** — FastAPI service; `GET /api/v1/crops`, `GET /api/v1/crops/{id}`, `GET /api/v1/regions`, `GET /api/v1/regions/{id}`, `GET /api/v1/crops/{id}/emerging` all live
- **Opportunity zone identification with infrastructure context** — scoring against cooperative and market access layers (planned)
- **Plugin architecture** — extensible evidence layers (pest/disease, frost risk, groundwater, land tenure) drop in without touching core logic
- **Confidence visualization** — uncertainty surfaces alongside every suitability output

---

## Who This Is For

Groundshift is designed to be useful to:

- **NGOs and development organizations** working on smallholder farmer resilience
- **Agricultural cooperatives** making regional investment and support decisions
- **Climate researchers** studying crop suitability shifts and human adaptation
- **Extension services** advising farmers on transition options
- **Journalists and policymakers** who need spatially honest communication of agricultural climate risk

It is not designed for institutional investors or land acquisition. The framing, outputs, and delivery mechanisms are oriented toward farmer welfare and information equity.

---

## Getting Started

### Prerequisites

- Python 3.12+
- WorldClim data on disk (see below) — ERA5 optional but recommended for current-period analysis
- PostgreSQL 15+ with PostGIS 3.4+ (for future phases — not required for Describe phase)

### Installation

```bash
git clone https://github.com/mtgiguere/groundshift.git
cd groundshift
pip install -e ".[dev]"
```

### Download climate and imagery data

```bash
# WorldClim v2.1 — 1970–2000 climatological baseline (~300MB)
python scripts/ingest/download_worldclim.py

# ERA5 reanalysis — 2015–2024 recent observed climate (requires CDS API key)
# See https://cds.climate.copernicus.eu/how-to-api to set up ~/.cdsapirc
pip install -e ".[ingest]"   # installs cdsapi, pystac-client, stackstac
python scripts/ingest/download_era5.py

# Sentinel-2 NDVI composite — free, no account required (uses AWS Earth Search)
python scripts/ingest/download_sentinel2.py --region ethiopia --year 2023

# CMIP6 climate projections — free, no account required (uses Pangeo/Google Cloud)
python scripts/ingest/download_cmip6.py

# Landsat Collection 2 NDVI trend surface — free, no account required (uses AWS Earth Search)
# Computes per-pixel OLS slope over the full archive (1985–present)
python scripts/ingest/download_landsat.py --region ethiopia
```

### Run your first analysis

```bash
# Describe current coffee suitability in Ethiopia (WorldClim baseline)
groundshift run --crop coffee --region ethiopia --phase describe

# Sample output:
# Groundshift — Describe phase
#   crop:    coffee
#   region:  ethiopia
#   cells:   6017 scored, 655 viable (score > 0)
#   score:   min=0.000  mean=0.073  max=1.000
#
#   calibration anchors:
#     [origin_center] Yirgacheffe / Sidama: 0.812  (expected >= 0.70)
#     [production_reference] Colombia Huila: n/a (outside region)  (expected >= 0.60)
#     [stress_reference] Central America Pacific Coast: n/a (outside region)  (stress reference — no floor)

# Add Sentinel-2 imagery divergence (requires sentinel2_ndvi.tif in data/sentinel2/)
groundshift run --crop coffee --region ethiopia --phase describe --imagery sentinel2

# Additional output line:
#   divergence (climate − observed):  min=-0.412  mean=0.118  max=0.631

# Add Landsat historical NDVI trend (requires landsat_ndvi_trend_ethiopia.tif in data/landsat/)
groundshift run --crop coffee --region ethiopia --phase describe --imagery landsat

# Additional output line:
#   trend (NDVI/year):  mean=-0.0021  declining=412  improving=243 cells

# Use ERA5 reanalysis instead of WorldClim baseline
groundshift run --crop coffee --region ethiopia --phase describe --source era5

# Predict future suitability under both SSP scenarios across 2040 / 2060 / 2100
# (requires CMIP6 data — run download_cmip6.py first)
groundshift run --crop coffee --region ethiopia --phase predict

# Sample output:
# Groundshift — Predict phase
#   crop:    coffee
#   region:  ethiopia
#
#   [ssp245 / 2040]    min=0.000  mean=0.041  max=0.998  viable=399 cells
#   [ssp245 / 2060]    min=0.000  mean=0.033  max=0.972  viable=361 cells
#   [ssp245 / 2100]    min=0.000  mean=0.025  max=0.934  viable=289 cells
#   [ssp585 / 2040]    min=0.000  mean=0.039  max=0.991  viable=387 cells
#   [ssp585 / 2060]    min=0.000  mean=0.027  max=0.951  viable=318 cells
#   [ssp585 / 2100]    min=0.000  mean=0.011  max=0.823  viable=174 cells

# Prescribe — compute delta surfaces (projected minus current) per scenario and horizon
# (requires both WorldClim and CMIP6 data)
groundshift run --crop coffee --region ethiopia --phase prescribe

# Sample output:
# Groundshift — Prescribe phase
#   crop:    coffee
#   region:  ethiopia
#
#   [ssp245 / 2040]    gaining= 214  losing= 441  mean_delta=-0.032
#   [ssp245 / 2060]    gaining= 163  losing= 492  mean_delta=-0.040
#   [ssp245 / 2100]    gaining= 118  losing= 537  mean_delta=-0.048
#   [ssp585 / 2040]    gaining= 198  losing= 457  mean_delta=-0.034
#   [ssp585 / 2060]    gaining= 131  losing= 524  mean_delta=-0.046
#   [ssp585 / 2100]    gaining=  71  losing= 584  mean_delta=-0.062
#
#   opportunity zones (emerging — currently low suitability, meaningfully gaining):
#   [ssp245 / 2040]      87 cells  confidence=low
#   [ssp245 / 2060]      71 cells  confidence=low
#   [ssp245 / 2100]      54 cells  confidence=low
#   [ssp585 / 2040]      83 cells  confidence=low
#   [ssp585 / 2060]      61 cells  confidence=low
#   [ssp585 / 2100]      38 cells  confidence=low
#
#   loss zones (currently viable, meaningfully declining):
#   [ssp245 / 2040]     214 cells  confidence=low
#   [ssp245 / 2060]     263 cells  confidence=low
#   [ssp245 / 2100]     318 cells  confidence=low
#   [ssp585 / 2040]     231 cells  confidence=low
#   [ssp585 / 2060]     301 cells  confidence=low
#   [ssp585 / 2100]     389 cells  confidence=low
```

### Run tests

```bash
pytest                   # full suite (unit + integration)
pytest -m unit           # unit tests only (no data files required)
pytest -m integration    # requires WorldClim data on disk
```

---

## Crop Profiles

Groundshift ships with the following crop profiles. Each profile defines the complete climate envelope and calibration anchors for the pipeline.

| Crop | Status | Calibration anchors |
|---|---|---|
| Arabica coffee | Active | Yirgacheffe/Sidama (origin), Colombia Huila (production), Central America Pacific (stress) |
| Wine grape | Profile included | — |
| Olive | Profile included | — |
| Wheat | Profile included | — |
| Cocoa | Profile stub | — |
| Tea | Profile stub | — |

Adding a new crop requires only a YAML profile. See [PLUGIN.md](docs/PLUGIN.md) for the crop profile specification.

---

## Plugin System

Groundshift is designed for extensibility. Evidence layers beyond the core climate envelope are implemented as plugins that drop into the pipeline without modifying core logic.

**Stretch plugins (interfaces defined, implementations planned):**
- `pest_disease` — Coffee leaf rust, grapevine downy mildew, wheat blast range expansion
- `frost_risk` — Daily temperature extremes, late frost event modeling
- `groundwater` — GRACE aquifer depletion surfaces
- `phenology` — MODIS/Sentinel flowering and harvest timing shifts
- `land_tenure` — Ownership type context for prescribe-phase recommendations
- `cooperative_infra` — Mill, processing, and export route accessibility scoring

See [PLUGIN.md](docs/PLUGIN.md) for complete plugin development documentation.

---

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design, data flow, technology decisions, and pipeline structure.

---

## Development Philosophy

Groundshift is built under strict TDD discipline. Every pipeline component has tests before implementation. Every data transformation is validated at ingestion and output. Confidence surfaces are first-class outputs — the platform is honest about what it knows and what it is estimating.

AI-assisted development (Claude Code) is used throughout, operating under the same TDD discipline: no untested code merges regardless of how it was generated.

See [TDD_CONTRACT.md](TDD_CONTRACT.md) for the evidence base behind this discipline, including bugs caught and prevented in real development sessions on this codebase.

---

## Data Sources

| Data | Source | License | Status |
|---|---|---|---|
| Climate baseline (1970–2000) | WorldClim v2.1 | CC BY 4.0 | ✓ Integrated |
| Recent observed climate (2015–present) | ERA5 (Copernicus/ECMWF) | Copernicus licence | ✓ Integrated |
| Climate projections | CMIP6 (Pangeo/Google Cloud) | CC BY 4.0 | ✓ Integrated |
| Crop suitability baselines | FAO GAEZ v4 | CC BY-NC 4.0 | Planned |
| Satellite imagery | Sentinel-2 (AWS Earth Search) | CC BY 4.0 | ✓ Integrated |
| Historical NDVI trend | Landsat Collection 2 (AWS Earth Search) | Public domain | ✓ Integrated |
| Soil properties | SoilGrids 250m (ISRIC) | CC BY 4.0 | Planned |
| Surface water | JRC Global Surface Water | CC BY 4.0 | Planned |
| Smallholder farm locations | SPAM 2020 (IFPRI) | CC BY 4.0 | Planned |

---

## License

MIT License. See LICENSE for details.

Data sources carry their own licenses — see the table above for status and attribution requirements.

---

## Contributing

Groundshift welcomes contributions, especially crop profiles, regional data integrations, and plugin implementations. Please read [PLUGIN.md](docs/PLUGIN.md) before writing any plugin code, and ensure full test coverage accompanies any submission.

Open an issue before beginning significant work — coordination avoids duplication.

---

## Project Status

Active development. The Describe, Predict, and Prescribe phases are complete and runnable end-to-end. Describe covers climate envelope scoring, calibration anchor monitoring, Sentinel-2 NDVI divergence, and Landsat historical trend detection. Predict covers CMIP6 projections under SSP2-4.5 and SSP5-8.5 through 2100. Prescribe computes signed delta surfaces (projected − current suitability), detects opportunity zones and loss zones, and ranks alternative crops by climate envelope overlap. The REST API serves crop profiles, named regions, and pre-computed opportunity zone results. Cooperative infrastructure context and an export script to feed the API are next.

| Component | Status |
|---|---|
| Core models (BoundingBox, TimeRange, LayerData, PluginMetadata) | ✓ Complete |
| SuitabilityModifier (factor_value, probability, confidence as DataArrays) | ✓ Complete |
| SuitabilityResult (score, confidence as DataArrays) | ✓ Complete |
| DescribeResult (suitability + divergence) | ✓ Complete |
| DivergenceResult (climate vs. observed NDVI surface) | ✓ Complete |
| PredictProjection (scenario + horizon_year + suitability) | ✓ Complete |
| PredictResult (list of projections) | ✓ Complete |
| ChangeProjection (scenario + horizon_year + delta DataArray) | ✓ Complete |
| PrescribeResult (list of change projections) | ✓ Complete |
| TrendResult (per-pixel NDVI/year slope DataArray) | ✓ Complete |
| OpportunityZone (scenario + horizon_year + mask DataArray + confidence) | ✓ Complete |
| OpportunityZoneResult (list of opportunity zones) | ✓ Complete |
| Plugin base class (GroundshiftPlugin ABC) | ✓ Complete |
| Plugin registry | ✓ Complete |
| Three-tier aggregator (existential / stress / custom, envelope as hard gate) | ✓ Complete |
| Scorer (plugin orchestration + aggregation) | ✓ Complete |
| ClimateThreshold + EnvelopeScorer (trapezoid scoring, scalar + spatial DataArray) | ✓ Complete |
| Crop profile YAML loader | ✓ Complete |
| ClimateDataSource ABC | ✓ Complete |
| compute_envelope (envelope pipeline step) | ✓ Complete |
| WorldClimSource (1970–2000 baseline) | ✓ Complete |
| ERA5Source (2015–present reanalysis) | ✓ Complete |
| ImagerySource ABC | ✓ Complete |
| Sentinel2Source (NDVI from pre-computed GeoTIFF) | ✓ Complete |
| compute_divergence (climate score − normalized NDVI) | ✓ Complete |
| Calibration anchor model + loader + scorer | ✓ Complete |
| Regions resolver (Ethiopia, Colombia, Central America) | ✓ Complete |
| DescribePhaseRunner (climate + optional imagery, returns DescribeResult) | ✓ Complete |
| CMIP6Source (scenario/horizon-aware ClimateDataSource) | ✓ Complete |
| PredictPhaseRunner (SSP2/SSP5 × 2040/2060/2100, returns PredictResult) | ✓ Complete |
| PrescribePhaseRunner (delta surfaces from DescribeResult + PredictResult) | ✓ Complete |
| GainZoneDetector (emerging cells: low current suitability + positive delta) | ✓ Complete |
| LossZoneDetector (declining cells: high current suitability + negative delta) | ✓ Complete |
| TransitionRecommender (Jaccard envelope overlap across candidate crop profiles) | ✓ Complete |
| LandsatSource (file-backed ImagerySource, OLS trend slope GeoTIFF) | ✓ Complete |
| CLI (`groundshift run --crop --region --phase --source --imagery`) | ✓ Complete |
| Raster utility (geodataframe_to_modifier) | ✓ Complete |
| WorldClim download script | ✓ Complete |
| ERA5 download script | ✓ Complete |
| Sentinel-2 download script (AWS Earth Search, free, no auth) | ✓ Complete |
| CMIP6 download script (Pangeo/Google Cloud, free, no auth) | ✓ Complete |
| Landsat download script (AWS Earth Search, free, no auth; OLS trend) | ✓ Complete |
| REST API — GET /api/v1/crops, GET /api/v1/crops/{id} | ✓ Complete |
| REST API — GET /api/v1/regions, GET /api/v1/regions/{id} | ✓ Complete |
| REST API — GET /api/v1/crops/{id}/emerging (pre-computed results, ?region= filter) | ✓ Complete |
| Emerging zone export script (writes results for API to serve) | Planned |
| REST API — runs, packages endpoints | Planned |

*Built with the belief that information equity is a precondition for climate adaptation justice.*
