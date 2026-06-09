# Groundshift — Architecture

This document describes the technical design of Groundshift: how the system is structured, why key decisions were made, and how the pieces fit together. It is written for contributors and technical partners who want to understand or extend the system at depth.

For the project mission and getting started, see [README.md](../README.md).
For plugin development, see [PLUGIN.md](PLUGIN.md).

---

## Design Principles

**Ground truth before models.** Satellite-observed signals are the primary evidence stream. Climate model projections provide context and forward projection, but where observed imagery diverges from model predictions, that divergence is the signal — not noise to be corrected.

**Confidence is a first-class output.** Every suitability surface is accompanied by a confidence surface. The platform is honest about where data is sparse, where models disagree, and where conclusions are speculative.

**Plugins are modifiers, not replacements.** The core pipeline owns suitability scoring. Plugins submit signed modifiers — adjustments with confidence weights — that the core aggregates. No plugin can override the core calculation unilaterally.

**Crop profiles are configuration, not code.** Adding a crop means writing a YAML file. The pipeline is generic. This keeps the codebase stable as the crop library grows.

**The pipeline has no knowledge of clients.** The pipeline writes artifacts (PostGIS surfaces, dated GeoJSON exports, COG rasters on S3). The REST API delivers those artifacts. No pipeline code knows or cares whether a client is a web app, a mobile app, or an offline CivTAK instance.

**TDD throughout.** Every component is tested before it is implemented. No untested code merges. This applies equally to human-written and AI-assisted code.

---

## System Overview

### Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         Groundshift                             │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  Data Layer  │    │  Core Engine │    │  Output Layer    │  │
│  │              │    │              │    │                  │  │
│  │  CMIP6       │───▶│  Envelope    │───▶│  Suitability     │  │
│  │  Sentinel-2  │    │  Scorer      │    │  Surfaces        │  │
│  │  Landsat     │───▶│              │    │                  │  │
│  │  FAO GAEZ    │    │  Imagery     │───▶│  Change          │  │
│  │  SoilGrids   │───▶│  Analyzer    │    │  Detection Maps  │  │
│  │  JRC Water   │    │              │    │                  │  │
│  │  SPAM        │    │  Opportunity │───▶│  Opportunity     │  │
│  │              │    │  Scorer      │    │  Zone Atlas      │  │
│  └──────────────┘    │              │    │                  │  │
│                      │  Plugin      │───▶│  Confidence      │  │
│  ┌──────────────┐    │  Aggregator  │    │  Surfaces        │  │
│  │  Crop        │    │              │    │                  │  │
│  │  Profiles    │───▶│              │    │  GeoJSON/MBTiles │  │
│  │  (YAML)      │    └──────────────┘    └────────┬─────────┘  │
│  └──────────────┘           ▲                     │            │
│                             │                     ▼            │
│  ┌──────────────────────────┴──────────────────────────────┐   │
│  │                      Plugin Registry                     │   │
│  │  climate_envelope │ imagery │ frost_risk │ pest_disease  │   │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Delivery

```
  Pipeline Output Artifacts
  (PostGIS + S3 COGs + dated GeoJSON)
              │
              ▼
      ┌───────────────┐
      │   REST API    │
      │   (FastAPI)   │
      └───────┬───────┘
              │
   ┌──────────┼──────────┐
   │          │          │
   ▼          ▼          ▼
Web App   Mobile App   Offline
                       (CivTAK / KMZ)
```

The API layer is the only boundary between pipeline artifacts and clients. All three client types consume the same API. Offline packages are pre-generated artifacts served via the API — not a separate pipeline.

---

## Repository Structure

```
groundshift/
│
├── groundshift/                  # Core Python package
│   ├── core/
│   │   ├── envelope/
│   │   │   ├── envelope_scorer.py       # Generic crop envelope scoring
│   │   │   ├── cmip6_projector.py       # CMIP6 scenario projection
│   │   │   └── soil_matcher.py          # SoilGrids integration
│   │   ├── imagery/
│   │   │   ├── sentinel2_pipeline.py    # Sentinel-2 ingestion + compositing
│   │   │   ├── landsat_archive.py       # Landsat historical access
│   │   │   ├── ndvi_analyzer.py         # NDVI/EVI computation + thresholds
│   │   │   └── change_detector.py       # Multi-temporal change detection
│   │   ├── opportunity/
│   │   │   ├── emergence_detector.py    # Phase 3 — stub; interface defined
│   │   │   ├── gain_zone_detector.py    # Phase 3 — stub; interface defined
│   │   │   ├── loss_zone_detector.py    # Phase 3 — stub; interface defined
│   │   │   └── transition_recommender.py # Phase 3 — stub; interface defined
│   │   └── aggregator.py                # Plugin modifier aggregation
│   │
│   ├── api/
│   │   ├── app.py                       # FastAPI application entry point
│   │   └── routes/
│   │       ├── crops.py                 # GET /crops, GET /crops/{id}
│   │       ├── regions.py               # GET /regions
│   │       ├── runs.py                  # GET /runs, GET /runs/{id}/surfaces
│   │       ├── emerging.py              # GET /crops/{id}/emerging
│   │       └── packages.py              # GET /packages/{crop}/{region}
│   │
│   ├── plugins/
│   │   ├── base.py                      # GroundshiftPlugin ABC
│   │   ├── registry.py                  # Plugin registration and discovery
│   │   ├── builtin/
│   │   │   ├── climate_envelope/        # Always runs
│   │   │   └── imagery/                 # Always runs
│   │   └── stretch/
│   │       ├── pest_disease/            # Interface defined, impl in progress
│   │       ├── frost_risk/              # Interface defined, impl in progress
│   │       ├── groundwater/             # Stub
│   │       ├── phenology/               # Stub
│   │       ├── land_tenure/             # Stub
│   │       └── cooperative_infra/       # Stub
│   │
│   ├── models/
│   │   ├── layer_data.py                # Typed spatial data containers
│   │   ├── suitability_modifier.py      # Plugin output contract
│   │   ├── bounding_box.py
│   │   └── time_range.py
│   │
│   ├── db/
│   │   ├── migrations/                  # Alembic migrations
│   │   └── spatial_store.py             # PostGIS interface
│   │
│   ├── regions/
│   │   ├── registry.geojson             # Named region definitions
│   │   └── resolver.py                  # resolve_region(id) → BoundingBox
│   │
│   └── cli.py                           # groundshift run entrypoint
│
├── crop_profiles/
│   ├── coffee.yaml
│   ├── wine_grape.yaml
│   ├── olive.yaml
│   ├── wheat.yaml
│   ├── cocoa.yaml                       # Stub
│   └── tea.yaml                         # Stub
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── docs/
│   ├── ARCHITECTURE.md                  # This file
│   ├── PLUGIN.md
│   ├── data_licenses.md
│   └── data_sources.md
│
├── scripts/
│   └── ingest/                          # One-time and scheduled ingestion
│
├── infrastructure/
│   └── aws/                             # Lambda, S3, RDS terraform/CDK
│
├── pyproject.toml
└── README.md
```

---

## Three-Phase Pipeline

Each analysis run executes one or more phases in sequence. Phases share a common spatial context (bounding box, crop profile, scenarios) and write to the same output store.

### Phase 1: Describe

**Question:** What is actually happening right now?

**Inputs:**
- Crop profile climate envelope
- Current climatological baselines (WorldClim / ERA5)
- Sentinel-2 seasonal composites (most recent 2 years)
- Landsat time series (full archive where available)
- SoilGrids soil properties
- JRC Global Surface Water

**Outputs:**
- Current suitability surface with confidence
- NDVI/EVI crop health surface (recent)
- Historical NDVI trend (slope over archive period)
- Model vs. observed divergence surface — where do projections and imagery disagree?
- Stress signal onset dates — when did decline begin in already-stressed zones?

**Key design note:** The divergence surface is the most scientifically valuable Describe output. Where imagery shows decline years before models predict it, farmers are already adapting. Where imagery shows expansion into zones models say are unsuitable, local microclimates or variety adaptation may explain the gap. Both are important signals.

### Phase 2: Predict

**Question:** Where is this heading, and under which scenarios?

**Inputs:**
- Phase 1 suitability surface (as baseline anchor)
- CMIP6 projections: SSP2-4.5 and SSP5-8.5
- Horizons: 2040, 2060, 2100
- Crop profile envelope thresholds

**Outputs:**
- Projected suitability surfaces per scenario per horizon
- Suitability change surfaces (delta from current)
- Confidence surfaces per scenario (model ensemble spread)
- Scenario comparison surface (SSP2 vs. SSP5 divergence)

**Key design note:** CMIP6 native resolution is 25-100km. For field-level insight, we downscale using Copernicus DEM topographic correction — slope, aspect, elevation, cold air drainage. Downscaled outputs carry wider confidence bounds and are flagged accordingly. These outputs are appropriate for regional planning decisions; they are not field-level measurements. Confidence surfaces must be communicated clearly to all downstream users.

### Phase 3: Prescribe

**Question:** What should stakeholders do?

**Inputs:**
- Phase 1 and Phase 2 outputs
- All active plugin modifier surfaces
- Cooperative/mill infrastructure locations (where available)
- OSM road network and port proximity
- SPAM smallholder farm density

**Outputs:**
- **Loss zones with severity tiers** — where to prioritize transition support, ranked by onset timeline
- **Dynamically detected opportunity zones** — emerging suitability regions identified by the pipeline from live data, with confidence tiers determined by how many independent signals agree (see below)
- **Transition recommendations** — for a given losing region, what crop substitutions are viable given soil, water, and infrastructure context
- **Mobility opportunity signals** — where skilled growers from stress zones could find viable destinations with existing infrastructure
- **Dated GeoJSON outputs** — e.g. `coffee_emerging_regions_2026Q2.geojson` — versioned, timestamped, never overwritten

**Key design note on emerging region detection:** Emerging opportunity zones are **outputs of the pipeline, not inputs**. They are never hardcoded in crop profiles. The pipeline scans suitability surfaces against each crop's `emergence_criteria` thresholds and assigns confidence tiers based on signal agreement:

| Confidence tier | Signals required |
|---|---|
| High | CMIP6 + Sentinel-2 + Landsat trend + active plugins all agree |
| Medium | Any three of the above agree |
| Low | Any two agree (minimum threshold to surface at all) |

**Emerging region persistence:** A region's confidence tier can increase over time as more imagery accumulates, or decrease if trend data reverses. To prevent spurious oscillation (e.g. a zone bouncing in and out of the list due to cloud contamination or seasonal Sentinel-2 variation), a minimum persistence rule applies: a zone must score at or above the `low` confidence threshold for at least `emergence_criteria.min_suitability_trend_years` consecutive years before appearing in outputs. Once surfaced, it is retained until it fails the threshold for two consecutive runs. The full history of scores is always preserved in `emerging_regions` — the persistence rule only governs what appears in dated GeoJSON exports.

**Key design note on delivery:** The Prescribe phase is only as useful as its delivery mechanism. Raw GeoJSON outputs are provided for NGO GIS teams. Simplified human-readable reports are generated for cooperative partners. The core platform does not make decisions — it surfaces information that enables better ones.

---

## Data Architecture

### Primary Database

PostgreSQL 15+ with PostGIS 3.4+. All spatial data is stored in EPSG:4326 (WGS84) with GIST spatial indexes on geometry columns.

```sql
-- pipeline_runs: every analysis run is recorded here first.
-- All other tables reference run_id back to this one.
-- git_sha ensures outputs are reproducible and auditable.
CREATE TABLE pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crop_id         TEXT NOT NULL,
    region_id       TEXT NOT NULL,
    phases          TEXT[] NOT NULL,            -- ['describe'] | ['predict'] | ['all']
    scenarios       TEXT[],                     -- ['ssp245', 'ssp585']
    horizons        INTEGER[],                  -- [2040, 2060, 2100]
    plugins_active  TEXT[] NOT NULL,            -- plugin_ids that ran
    git_sha         TEXT,                       -- repo commit at time of run
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    status          TEXT NOT NULL DEFAULT 'running',  -- running | complete | failed
    error           TEXT                        -- populated on failure
);

-- suitability_surfaces: aggregate suitability scores only — one row per
-- spatial cell per run. No plugin_id here — this is the core output after
-- all plugin modifiers have been applied. Per-plugin breakdowns live in
-- plugin_modifiers. The distinction: this table answers "what is the score",
-- plugin_modifiers answers "why".
CREATE TABLE suitability_surfaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES pipeline_runs(id),
    crop_id         TEXT NOT NULL,
    region_id       TEXT NOT NULL,
    phase           TEXT NOT NULL,              -- describe | predict | prescribe
    scenario        TEXT,                       -- ssp245 | ssp585 | null for describe
    horizon         INTEGER,                    -- 2040 | 2060 | 2100 | null for describe
    score           NUMERIC(5,4) NOT NULL,      -- aggregate score, post-plugin-modifiers
    confidence      NUMERIC(5,4) NOT NULL,
    geom            GEOMETRY(POLYGON, 4326),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON suitability_surfaces USING GIST (geom);
CREATE INDEX ON suitability_surfaces (run_id, crop_id, region_id, phase, scenario, horizon);

-- plugin_modifiers: per-plugin modifier values that contributed to a surface score.
-- Join to suitability_surfaces via surface_id to understand what drove the aggregate.
CREATE TABLE plugin_modifiers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES pipeline_runs(id),
    surface_id      UUID NOT NULL REFERENCES suitability_surfaces(id),
    plugin_id       TEXT NOT NULL,
    modifier_value  NUMERIC(5,4) NOT NULL,      -- signed [-1.0, 1.0]
    confidence      NUMERIC(5,4) NOT NULL,
    geom            GEOMETRY(POLYGON, 4326),
    metadata        JSONB
);

CREATE INDEX ON plugin_modifiers (surface_id, plugin_id);

-- emerging_regions: pipeline-detected opportunity zones. Never manually authored.
-- Each row is a snapshot from one run. Rows are never deleted —
-- the full history of when zones appeared, strengthened, or dropped is preserved.
CREATE TABLE emerging_regions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               UUID NOT NULL REFERENCES pipeline_runs(id),
    crop_id              TEXT NOT NULL,
    detected_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence_tier      TEXT NOT NULL,          -- high | medium | low
    suitability_score    NUMERIC(5,4) NOT NULL,
    aggregate_confidence NUMERIC(5,4) NOT NULL,
    trend_years          INTEGER,
    signals_agreeing     JSONB NOT NULL,         -- {cmip6: true, sentinel2: true, landsat: true, plugins: [...]}
    infrastructure_score NUMERIC(5,4),           -- from cooperative_infra plugin if active
    geom                 GEOMETRY(POLYGON, 4326) NOT NULL,
    exported_geojson     TEXT                    -- S3 path of the dated GeoJSON export
);

CREATE INDEX ON emerging_regions USING GIST (geom);
CREATE INDEX ON emerging_regions (crop_id, detected_at, confidence_tier);

-- calibration_anchors: permanent historical reference points loaded from crop profiles.
-- Never pipeline-generated. Never deleted.
CREATE TABLE calibration_anchors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crop_id         TEXT NOT NULL,
    anchor_id       TEXT NOT NULL,              -- matches id in crop profile YAML
    name            TEXT NOT NULL,
    role            TEXT NOT NULL,              -- origin_center | production_reference | stress_reference
    notes           TEXT,
    geom            GEOMETRY(POLYGON, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- calibration_anchor_scores: suitability score recorded at every pipeline run.
-- Never shrinks. The long-term scientific record and model health monitor.
CREATE TABLE calibration_anchor_scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES pipeline_runs(id),
    anchor_id       UUID NOT NULL REFERENCES calibration_anchors(id),
    score           NUMERIC(5,4) NOT NULL,
    confidence      NUMERIC(5,4) NOT NULL,
    expected_min    NUMERIC(5,4),               -- null for stress_reference anchors
    alert_triggered BOOLEAN DEFAULT FALSE,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON calibration_anchor_scores (anchor_id, recorded_at);
```

### Region Name Resolution

The CLI and pipeline accept named regions (e.g. `--region ethiopia`) rather than raw coordinates. Named regions are resolved to a `BoundingBox` via a **regions registry** — a lightweight lookup table seeded from a GeoJSON file at `groundshift/regions/registry.geojson`.

```python
# groundshift/regions/resolver.py
def resolve_region(region_id: str) -> BoundingBox:
    """
    Looks up a named region and returns its bounding box.
    Raises UnknownRegionError if the id is not in the registry.
    """
```

The registry ships with a set of named regions covering established crop geographies. Contributors adding new regions should add an entry to `registry.geojson` with a stable `id`, human-readable `name`, and a bounding polygon. Arbitrary bounding boxes can also be passed directly via `--bbox min_lon,min_lat,max_lon,max_lat` to bypass the registry entirely.

---

### Raster Storage

Large raster datasets (Sentinel-2 composites, Landsat archives, CMIP6 grids) are stored as Cloud-Optimized GeoTIFFs (COGs) on S3. PostGIS raster tables are used for smaller derived surfaces that need spatial query support.

### Imagery Pipeline

Sentinel-2 and Landsat data are accessed via AWS Open Data Registry (no egress cost). Seasonal composites are computed as median composites over the dry season window defined in each crop profile — this maximises crop signal and minimises cloud contamination.

Change detection uses a two-pass approach:
1. NDVI trend (linear regression over full Landsat archive) — catches slow multi-decade decline
2. CUSUM (cumulative sum) change detection — catches abrupt transitions and onset dates

### Calibration Anchor Monitoring

Every pipeline run scores the crop's calibration anchors and records the results in `calibration_anchor_scores`. Each anchor has an expected minimum score based on its role:

| Role | Expected minimum score | Rationale |
|---|---|---|
| `origin_center` | 0.70 | Should be highly suitable under current climate |
| `production_reference` | 0.60 | Active production implies viable conditions |
| `stress_reference` | No minimum | Declining scores here *confirm* the model is working |

When an `origin_center` or `production_reference` anchor scores below its expected minimum, the pipeline raises a model alert. The alert does not halt the run — it is recorded in `calibration_anchor_scores.alert_triggered` and surfaced in the run report. The investigator must then answer:

**Is this real climate signal, or a model error?**

That question is the most scientifically important one the platform can ask. A genuine decline in Ethiopia's suitability score is not a bug — it is one of the most significant findings the platform could produce. An anchor that never degrades in a warming world would be the real warning sign.

`stress_reference` anchors (like Central America) work in reverse — consistently *high* scores there would trigger an alert, since the model should be detecting documented real-world stress.

---

## API Layer

The REST API is the delivery boundary between pipeline artifacts and all clients. No client reaches PostGIS or S3 directly.

### Technology

**FastAPI** — async-native, automatic OpenAPI docs, Pydantic validation. Runs as a lightweight service alongside the pipeline.

### Core Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/v1/crops` | List available crop profiles |
| `GET /api/v1/regions` | List/search named regions |
| `GET /api/v1/runs` | List pipeline runs with status |
| `GET /api/v1/runs/{run_id}/surfaces` | Suitability surfaces for a completed run |
| `GET /api/v1/crops/{crop_id}/emerging` | Latest emerging regions with confidence tiers |
| `GET /api/v1/packages/{crop_id}/{region_id}` | Download pre-generated offline package |

All endpoints return GeoJSON by default. The `Accept` header or a `?format=` query parameter selects simplified GeoJSON (for mobile bandwidth) or full-resolution GeoJSON.

### Client Types

**Web application** — standard REST + GeoJSON responses; map tile streaming from COGs on S3 via HTTP range requests.

**Mobile application** — same REST API; simplified GeoJSON responses with reduced geometry precision for mobile bandwidth constraints.

**Offline / CivTAK** — pre-generated packages downloaded in advance over any available connection. Two formats:
- **MBTiles** — SQLite-backed tile archive; renders offline in CivTAK and any offline-capable map app. Contains suitability surface tiles at zoom levels 4–12.
- **KMZ** — KML archive; CivTAK native format for polygon overlays and point markers. Contains emerging region polygons with confidence tier attributes.

Offline packages are generated as a post-step after each pipeline run and stored on S3. The `GET /packages/{crop_id}/{region_id}` endpoint streams the latest pre-generated package for download. A package contains the most recent Describe and Predict outputs for the requested crop and region — no network connection is needed to use it after download.

**Key rule:** The pipeline writes artifacts. The API delivers them. No pipeline code knows what type of client will consume its output.

---

## Plugin Architecture

See [PLUGIN.md](PLUGIN.md) for the full plugin development guide.

### Plugin Interface Contract

```python
from abc import ABC, abstractmethod
from groundshift.models import (
    BoundingBox, TimeRange, LayerData, SuitabilityModifier, PluginMetadata
)

class GroundshiftPlugin(ABC):

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Name, version, crop compatibility, data requirements."""

    @abstractmethod
    def validate_config(self, crop_profile: dict) -> bool:
        """Return True if this plugin can run for this crop profile."""

    @abstractmethod
    def fetch_data(
        self,
        region: BoundingBox,
        time_range: TimeRange
    ) -> LayerData:
        """Fetch and return the plugin's evidence data."""

    @abstractmethod
    def score(
        self,
        layer_data: LayerData,
        crop_profile: dict
    ) -> SuitabilityModifier:
        """
        Return a SuitabilityModifier.

        modifier_value: float in [-1.0, 1.0]
            Positive = opportunity signal (amplifies suitability)
            Negative = stress signal (suppresses suitability)
        confidence: float in [0.0, 1.0]
            How much weight the aggregator should give this modifier.
        """

    @abstractmethod
    def describe(self, score: SuitabilityModifier) -> str:
        """Human-readable explanation of this modifier for reporting."""
```

### Modifier Aggregation

The core aggregator combines plugin modifiers using a confidence-weighted approach. No single plugin can move the final score by more than a configurable cap (default: 25% of the base score). This prevents a single poorly-calibrated plugin from dominating outputs.

```python
def aggregate_modifiers(
    base_score: float,
    modifiers: list[SuitabilityModifier],
    max_single_plugin_impact: float = 0.25
) -> tuple[float, float]:
    """
    Returns (adjusted_score, aggregate_confidence).
    Each modifier is weighted by its confidence value.
    Individual modifier impact is capped at max_single_plugin_impact.
    """
```

---

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Spatial database | PostGIS | 20+ year production track record; native support for complex spatial queries required by large AOI processing |
| Climate projections | CMIP6 | IPCC-standard ensemble; SSP scenarios directly comparable to policy frameworks |
| Imagery: current | Sentinel-2 | 10m resolution, free, global, 5-day revisit — best available for crop health monitoring |
| Imagery: historical | Landsat | 40+ year archive, free — no alternative for long-term trend analysis |
| Raster storage | COG on S3 | Cloud-native, no egress cost via AWS Open Data, supports HTTP range requests for partial reads |
| Language | Python 3.12 | Dominant in geospatial and data science ecosystems; GeoPandas, Rasterio, Xarray all mature |
| API framework | FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation; clean boundary between pipeline and all client types |
| Offline formats | MBTiles + KMZ | MBTiles is SQLite-backed, renders offline in CivTAK and standard map apps; KMZ is CivTAK native for polygon overlays |
| Infrastructure | AWS | Lambda for ingestion tasks, S3 for raster storage, RDS for PostGIS — scales with usage, manageable cost at research scale |
| Testing | pytest + TDD | All components tested before implementation; CI runs full suite on every push |
| CI/CD | GitHub Actions | pytest, ruff, pip-audit vulnerability scanning |

---

## Coordinate Reference Systems

All geometry stored in **EPSG:4326 (WGS84)**. Metric calculations (area, distance) use **EPSG:3857 (Web Mercator)** for display and **appropriate UTM zones** for precision area calculations. Reprojection is handled in PostGIS at query time using ST_Transform — source CRS is always stored in layer metadata.

---

## Performance Considerations

**Large AOI processing:** Complex multipolygon queries (country-level or large regional AOIs) use geometry subdivision into manageable tiles with spatial index pre-filtering. This pattern is documented in `groundshift/db/spatial_store.py`.

**CMIP6 data volume:** Full global CMIP6 ensembles are large. We cache regionally-clipped subsets per crop analysis run on S3. Re-running the same region reuses the cached clip.

**Imagery compositing:** Seasonal median composites are computed once per region per season and cached as COGs. Incremental updates add new scenes to a rolling composite rather than reprocessing the full archive.

**API response size:** Suitability surfaces can be large. The API supports bbox-clipped responses (`?bbox=min_lon,min_lat,max_lon,max_lat`) and geometry simplification (`?simplify=0.01`) for mobile and web map use cases where full-resolution polygons are unnecessary.

---

## Testing Strategy

```
tests/
  unit/               Pure logic tests — no I/O, no database
                      Envelope scoring, modifier aggregation, profile parsing,
                      API route logic (with mocked storage)
  integration/        Database and external service tests — require live PostGIS
                      Spatial query correctness, CRS handling, large AOI behavior
  fixtures/           Small synthetic datasets that cover edge cases
                      Designed to be stable and fast — no real imagery
```

Every plugin must ship with unit tests covering at minimum:
- `validate_config` returns False for incompatible crops
- `score` returns a modifier within the valid range [-1.0, 1.0]
- `score` returns a confidence within the valid range [0.0, 1.0]
- `describe` returns a non-empty string for any valid modifier

---

## Configuration

Runtime configuration via `.env` (local) or AWS Parameter Store (production):

```bash
# Database
GROUNDSHIFT_DB_HOST=localhost
GROUNDSHIFT_DB_PORT=5432
GROUNDSHIFT_DB_NAME=groundshift
GROUNDSHIFT_DB_USER=groundshift
GROUNDSHIFT_DB_PASSWORD=...

# AWS
AWS_DEFAULT_REGION=us-east-1
GROUNDSHIFT_S3_BUCKET=groundshift-rasters

# Data APIs
CMIP6_ESGF_NODE=https://esgf-node.llnl.gov/esg-search
JRC_API_KEY=...

# Plugin flags (comma-separated list of active plugins)
GROUNDSHIFT_PLUGINS=climate_envelope,imagery

# Analysis defaults
GROUNDSHIFT_DEFAULT_SCENARIOS=ssp245,ssp585
GROUNDSHIFT_DEFAULT_HORIZONS=2040,2060,2100

# API
GROUNDSHIFT_API_HOST=0.0.0.0
GROUNDSHIFT_API_PORT=8000
```

---

## Roadmap

| Phase | Scope |
|---|---|
| Phase 1 — Describe | Climate envelope + imagery pipelines, coffee/Ethiopia, full test coverage |
| Phase 2 — Predict | CMIP6 projection pipeline, SSP2/SSP5 scenarios, scenario comparison |
| Phase 3 — Prescribe | Opportunity zone detection, transition recommender, cooperative infrastructure layer |
| API + delivery | REST API, web app, mobile app, offline package generation |
| Plugin expansion | Frost risk, pest/disease, phenology plugins |
| Additional crops | Wine grape, olive, wheat profiles production-ready |
