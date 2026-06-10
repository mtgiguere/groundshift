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
- **Multiple climate data sources** — WorldClim v2.1 (1970–2000 baseline) and ERA5 reanalysis (2015–present) both implement the same `ClimateDataSource` interface; swap with a single argument
- **Calibration anchor monitoring** — named reference zones (origin centers, production references, stress references) scored on every run; alerts fire when a documented high-suitability zone drops below threshold
- **CMIP6 suitability projection** — SSP2 and SSP5 scenarios, 2040 / 2060 / 2100 horizons (planned)
- **Satellite imagery analysis** — Sentinel-2 NDVI/EVI crop health, Landsat historical change detection (planned)
- **Ground truth vs. model divergence detection** — where observed signals lead or lag projections (planned)
- **Opportunity zone identification** — emerging suitability zones with infrastructure and market-access scoring (planned)
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

### Download climate data

```bash
# WorldClim v2.1 — 1970–2000 climatological baseline (~300MB)
python scripts/ingest/download_worldclim.py

# ERA5 reanalysis — 2015–2024 recent observed climate (requires CDS API key)
# See https://cds.climate.copernicus.eu/how-to-api to set up ~/.cdsapirc
pip install -e ".[ingest]"   # installs cdsapi
python scripts/ingest/download_era5.py
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
| Climate projections | CMIP6 (ESGF) | CC BY 4.0 | Planned |
| Crop suitability baselines | FAO GAEZ v4 | CC BY-NC 4.0 | Planned |
| Satellite imagery | Sentinel-2 (ESA/AWS) | CC BY 4.0 | Planned |
| Historical imagery | Landsat (USGS/AWS) | Public domain | Planned |
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

Active development. The Describe phase climate envelope pipeline is complete and runnable end-to-end from the CLI. The imagery analysis layer (Sentinel-2 NDVI, Landsat trend detection) is next.

| Component | Status |
|---|---|
| Core models (BoundingBox, TimeRange, LayerData, PluginMetadata) | ✓ Complete |
| SuitabilityModifier (factor_value, probability, confidence as DataArrays) | ✓ Complete |
| SuitabilityResult (score, confidence as DataArrays) | ✓ Complete |
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
| Calibration anchor model + loader + scorer | ✓ Complete |
| Regions resolver (Ethiopia, Colombia, Central America) | ✓ Complete |
| DescribePhaseRunner (end-to-end Describe orchestration) | ✓ Complete |
| CLI (`groundshift run --crop --region --phase`) | ✓ Complete |
| Raster utility (geodataframe_to_modifier) | ✓ Complete |
| WorldClim download script | ✓ Complete |
| ERA5 download script | ✓ Complete |
| Sentinel-2 / Landsat imagery pipeline | Planned |
| CMIP6 projection pipeline | Planned |
| Opportunity zone detector (Phase 3) | Planned |
| REST API | Planned |

*Built with the belief that information equity is a precondition for climate adaptation justice.*
