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
│   │   │   ├── threshold.py             # ✓ ClimateThreshold — trapezoid scoring, float | DataArray
│   │   │   ├── scorer.py                # ✓ EnvelopeScorer — Liebig's min, float | DataArray
│   │   │   ├── profile_loader.py        # ✓ envelope_scorer_from_profile(dict) → EnvelopeScorer
│   │   │   ├── yaml_loader.py           # ✓ load_profile_from_yaml(Path) → dict — I/O boundary
│   │   │   ├── climate_source.py        # ✓ ClimateDataSource ABC — fetch(variable, region, time_range)
│   │   │   ├── climate_envelope.py      # ✓ compute_envelope(profile, source, region, time_range) → DataArray
│   │   │   ├── worldclim_source.py      # ✓ WorldClimSource — file-backed ClimateDataSource, 1970-2000 baseline
│   │   │   ├── era5_source.py           # ✓ ERA5Source — NetCDF-backed ClimateDataSource, 2015-present
│   │   │   ├── cmip6_source.py          # ✓ CMIP6Source — scenario/horizon-aware ClimateDataSource
│   │   │   └── soil_matcher.py          # SoilGrids integration — planned
│   │   ├── phases/
│   │   │   ├── describe.py              # ✓ DescribePhaseRunner — climate + optional imagery → DescribeResult
│   │   │   ├── predict.py               # ✓ PredictPhaseRunner — CMIP6 × scenarios × horizons → PredictResult
│   │   │   └── prescribe.py             # ✓ PrescribePhaseRunner — delta surfaces from DescribeResult + PredictResult
│   │   ├── imagery/
│   │   │   ├── imagery_source.py        # ✓ ImagerySource ABC — fetch(variable, region, time_range) → DataArray
│   │   │   ├── sentinel2_source.py      # ✓ Sentinel2Source — GeoTIFF-backed ImagerySource (NDVI)
│   │   │   ├── divergence.py            # ✓ compute_divergence(SuitabilityResult, ndvi) → DivergenceResult
│   │   │   ├── landsat_archive.py       # Landsat historical access — planned
│   │   │   └── change_detector.py       # Multi-temporal change detection — planned
│   │   ├── opportunity/
│   │   │   ├── emergence_detector.py    # Phase 3 — planned
│   │   │   ├── gain_zone_detector.py    # Phase 3 — planned
│   │   │   ├── loss_zone_detector.py    # Phase 3 — planned
│   │   │   └── transition_recommender.py # Phase 3 — planned
│   │   ├── aggregator.py                # ✓ three-tier aggregation (existential/stress/custom), envelope gate
│   │   ├── scorer.py                    # ✓ runs registry plugins against envelope, returns SuitabilityResult
│   │   └── utils/
│   │       └── raster.py                # ✓ geodataframe_to_modifier — rasterize GeoDataFrame to SuitabilityModifier
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
│   │   ├── base.py                      # ✓ GroundshiftPlugin ABC (5-method contract)
│   │   ├── registry.py                  # ✓ register, get, list_plugins; duplicate guard
│   │   └── stretch/                     # Modifier plugins (operate inside the envelope gate)
│   │       ├── pest_disease/            # Planned
│   │       ├── frost_risk/              # Planned
│   │       ├── groundwater/             # Planned
│   │       ├── phenology/               # Planned
│   │       ├── land_tenure/             # Planned
│   │       └── cooperative_infra/       # Planned
│   │
│   ├── models/
│   │   ├── bounding_box.py              # ✓ WGS84 bounding box with validation
│   │   ├── layer_data.py                # ✓ typed spatial data container (data: xr.DataArray)
│   │   ├── plugin_metadata.py           # ✓ plugin identity, threat_tier, custom_weight
│   │   ├── suitability_modifier.py      # ✓ factor_value/probability/confidence as DataArrays
│   │   ├── suitability_result.py        # ✓ score/confidence as DataArrays
│   │   ├── divergence_result.py         # ✓ DivergenceResult — signed climate-vs-observed surface
│   │   ├── describe_result.py           # ✓ DescribeResult — suitability + optional divergence
│   │   ├── predict_result.py            # ✓ PredictResult / PredictProjection — suitability per scenario+horizon
│   │   ├── prescribe_result.py          # ✓ PrescribeResult / ChangeProjection — delta surface per scenario+horizon
│   │   ├── time_range.py                # ✓ start/end with scenario and horizon support
│   │   ├── calibration_anchor.py        # ✓ CalibrationAnchor — role-validated reference zone
│   │   └── anchor_score.py              # ✓ AnchorScore — per-run score + alert result
│   │
│   ├── db/
│   │   ├── migrations/                  # Alembic migrations
│   │   └── spatial_store.py             # PostGIS interface
│   │
│   ├── calibration/
│   │   ├── anchor_loader.py             # ✓ load_anchors_from_profile(dict) → list[CalibrationAnchor]
│   │   └── anchor_scorer.py             # ✓ score_anchors(result, anchors) → list[AnchorScore]
│   │
│   ├── regions/
│   │   ├── __init__.py
│   │   └── resolver.py                  # ✓ resolve_region(id) → BoundingBox; UnknownRegionError
│   │
│   └── cli.py                           # ✓ run_describe + run_predict + run_prescribe; groundshift run --phase describe|predict|prescribe
│
├── crop_profiles/
│   ├── coffee_arabica.yaml              # ✓ Arabica thresholds (temp, precipitation, altitude)
│   ├── coffee.yaml                      # ✓ Alias for arabica (default --crop coffee CLI argument)
│   ├── wine_grape.yaml
│   ├── olive.yaml
│   ├── wheat.yaml
│   ├── cocoa.yaml                       # Stub
│   └── tea.yaml                         # Stub
│
├── tests/
│   ├── unit/
│   │   ├── conftest.py                  # ✓ make_plugin fixture (DataArray fields, threat_tier)
│   │   ├── core/
│   │   │   ├── envelope/                # ✓ test_threshold, test_envelope_scorer, test_profile_loader, test_climate_envelope, test_worldclim_source
│   │   │   ├── phases/                  # ✓ test_describe_phase_runner, test_predict_phase_runner, test_prescribe_phase_runner
│   │   │   ├── utils/                   # ✓ test_raster
│   │   │   ├── test_aggregator.py       # ✓ three-tier logic, probability/expected value, property tests
│   │   │   └── test_scorer.py           # ✓
│   │   ├── models/                      # ✓ all models covered
│   │   ├── plugins/                     # ✓ test_plugin_base.py, test_registry.py
│   │   ├── regions/                     # ✓ test_resolver.py
│   │   ├── scripts/                     # ✓ test_download_worldclim, test_download_era5, test_download_sentinel2, test_download_cmip6
│   │   └── test_cli.py                  # ✓ argument parsing, run_describe, run_predict, run_prescribe, --source, --imagery
│   ├── integration/
│   │   └── test_describe_phase_smoke.py # ✓ full pipeline + CLI + anchor + ERA5/Sentinel-2 skip tests
│   └── fixtures/                        # synthetic datasets — not yet written
│
├── docs/
│   ├── ARCHITECTURE.md                  # This file
│   ├── PLUGIN.md
│   ├── data_licenses.md
│   └── data_sources.md
│
├── data/
│   ├── worldclim/10m/                   # WorldClim GeoTIFFs (downloaded by ingest script, gitignored)
│   ├── era5/                            # ERA5 NetCDF files (downloaded by ingest script, gitignored)
│   ├── sentinel2/                       # Sentinel-2 NDVI GeoTIFFs (downloaded by ingest script, gitignored)
│   └── cmip6/                           # CMIP6 projection NetCDFs (downloaded by ingest script, gitignored)
│
├── scripts/
│   ├── __init__.py
│   └── ingest/                          # One-time and scheduled ingestion
│       ├── __init__.py
│       ├── download_worldclim.py        # ✓ downloads WorldClim v2.1 base data to data/worldclim/10m/
│       ├── download_era5.py             # ✓ downloads ERA5 reanalysis to data/era5/ (requires cdsapi)
│       ├── download_sentinel2.py        # ✓ downloads Sentinel-2 NDVI composite via AWS Earth Search (free)
│       └── download_cmip6.py            # ✓ downloads CMIP6 projections via Pangeo/Google Cloud (free)
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

**Implemented:** `PrescribePhaseRunner` computes signed per-cell delta surfaces (projected suitability − current suitability) for each scenario+horizon combination using `DescribeResult` and `PredictResult`. Positive delta cells are gaining viability; negative are losing. Opportunity zone detection, transition recommendations, and infrastructure context are next.

**Inputs:**
- Phase 1 and Phase 2 outputs (DescribeResult + PredictResult)
- All active plugin modifier surfaces (planned)
- Cooperative/mill infrastructure locations (where available, planned)
- OSM road network and port proximity (planned)
- SPAM smallholder farm density (planned)

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

## Suitability Model

This section documents the core scientific and architectural principles behind how Groundshift computes suitability. These were established through deliberate design — understanding them is essential before working on any pipeline component.

### The Envelope is the Gate

The climate envelope is not a plugin. It is the foundation of the suitability model.

The envelope answers one question: **can this crop physically exist here?** A cell where temperature, precipitation, or altitude falls outside the crop's viable range scores zero. No downstream factor can change that. The envelope defines the ceiling — plugins operate inside it.

This is not a software convenience; it is scientifically necessary. An additive modifier model would allow a cluster of positive signals (good infrastructure, low pest pressure) to push a climatically impossible zone into apparent viability. That is indefensible. The envelope is a hard gate.

```
final_score = 0.0  if  envelope_score = 0.0  (always, regardless of plugins)
final_score ≤ envelope_score  (always)
```

### Spatial Primitives

All suitability data flows as `xarray.DataArray` grids — one value per geographic cell. This applies to:

- `LayerData.data` — the raw evidence a plugin fetches
- `SuitabilityModifier` fields — factor, probability, confidence surfaces
- `SuitabilityResult` fields — the final score and confidence surfaces

A scalar is a degenerate DataArray. The aggregator math is identical; xarray applies it element-wise across the grid.

### Plugin Threat Tiers

Plugins declare a `threat_tier` in their metadata. The tier determines how the aggregator combines their output — because different threats have categorically different effects on crop viability.

**Tier 1 — Existential**

Threats that can eliminate viability in a zone regardless of other conditions: disease outbreaks (Coffee Leaf Rust, Panama Disease, Wheat Blast), catastrophic flooding. These combine with the envelope via Liebig's Law — the most limiting factor defines the ceiling.

```
ceiling = min(envelope, existential_1, existential_2, ...)
```

**Tier 2 — Stress**

Independent stressors that reduce achievable suitability but do not individually eliminate it: minor pest pressure, frost risk, water stress. These compound multiplicatively — three moderate stresses accumulate into a meaningful reduction.

```
stress_factor = effective_1 × effective_2 × effective_3 × ...
```

**Tier 3 — Custom**

For threat types not captured by the first two tiers. Plugin author declares a `custom_weight` that controls how hard their factor hits. The weight acts as an exponent:

```
custom_factor = factor_A^weight_A × factor_B^weight_B × ...
```

Suggested weights (document in PLUGIN.md):

| Weight | Meaning |
|---|---|
| `0.25` | Background signal — barely moves the score |
| `0.5` | Minor factor — noticeable, doesn't dominate |
| `1.0` | Standard — equivalent to a stress-tier plugin (default) |
| `2.0` | Significant — outsized influence, use carefully |

### Probability and Confidence

Each plugin factor carries three independent dimensions:

| Field | Meaning |
|---|---|
| `factor_value` | Severity if the stressor occurs — `0.0` = catastrophic, `1.0` = no effect |
| `probability` | Likelihood the stressor occurs — `[0.0, 1.0]` |
| `confidence` | Certainty of the estimates themselves — `[0.0, 1.0]` |

`probability` and `confidence` are not the same thing. A plugin can be highly confident (`confidence=0.9`) that Coffee Leaf Rust would devastate this zone if it arrived, while the arrival probability this season is low (`probability=0.15`). Conflating them would misrepresent both the science and the uncertainty.

The aggregator converts each plugin's raw factor to an **effective factor** before tier aggregation:

```
effective_factor = 1.0 - (probability × (1.0 - factor_value))
```

| factor_value | probability | effective_factor | meaning |
|---|---|---|---|
| 0.0 | 1.0 | 0.0 | certain catastrophe |
| 0.0 | 0.1 | 0.9 | catastrophic but unlikely |
| 0.8 | 1.0 | 0.8 | certain mild stress |
| 0.8 | 0.5 | 0.9 | 50% chance of mild stress |

### Full Aggregation Formula

```
# Step 1: effective factor per plugin
eff_i = 1.0 - (probability_i × (1.0 - factor_i))

# Step 2: tier aggregation
ceiling       = min(envelope, eff_existential_1, eff_existential_2, ...)
stress_factor = eff_stress_1 × eff_stress_2 × ...
custom_factor = eff_custom_A^weight_A × eff_custom_B^weight_B × ...

# Step 3: final surface
final_score = ceiling × stress_factor × custom_factor
```

All operations are element-wise on DataArrays. The final output is a spatially complete suitability surface.

---

## Envelope Pipeline Step

The climate envelope is computed as an explicit pipeline step **before** `Scorer.run()` — it is not a plugin and is not registered in `PluginRegistry`.

```python
# Pseudocode for a Describe phase run
profile       = load_profile_from_yaml(path)
envelope      = compute_envelope(profile, climate_source, region, time_range)
result        = scorer.run(envelope, region, time_range, profile)
```

`compute_envelope` builds an `EnvelopeScorer` from the crop profile, fetches each required climate variable from the `ClimateDataSource`, and returns the suitability surface as a `DataArray`.

### ClimateDataSource

`ClimateDataSource` is an ABC that abstracts where climate variable grids come from. Any concrete implementation provides one method:

```python
class ClimateDataSource(ABC):
    @abstractmethod
    def fetch(
        self,
        variable: str,
        region: BoundingBox,
        time_range: TimeRange,
    ) -> xr.DataArray:
        """Return a DataArray of values for the named variable over the region."""
```

Implementations:

| Implementation | Data | Phase | Status |
|---|---|---|---|
| `WorldClimSource` | Historical baseline climatology (1970–2000) | Describe | ✓ Complete |
| `ERA5Source` | Recent observed climate (2015–present) | Describe | ✓ Complete |
| `CMIP6Source` | Projected climate under SSP2/SSP5 scenarios | Predict | ✓ Complete |

Each implementation clips to the requested `BoundingBox`, reprojects to EPSG:4326, and returns a consistently named DataArray. The pipeline is indifferent to which source is used — swap `WorldClimSource` for `CMIP6Source` and the same `compute_envelope` call produces a projected suitability surface instead of a current one.

---

## Imagery Pipeline

`ImagerySource` is an ABC that mirrors `ClimateDataSource` exactly — same `fetch(variable, region, time_range) → DataArray` contract. This symmetry is intentional: imagery and climate data are both spatial evidence streams, and both deserve an interchangeable-source abstraction.

```python
class ImagerySource(ABC):
    @abstractmethod
    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        """Return a DataArray of imagery values for the named variable over the region."""
```

Implementations:

| Implementation | Data | Variable | Status |
|---|---|---|---|
| `Sentinel2Source` | Pre-computed NDVI GeoTIFF | `"ndvi"` | ✓ Complete |
| `LandsatSource` | Historical archive | `"ndvi_trend"` | Planned |

### Divergence

NDVI is not a suitability modifier — it is an independent ground-truth signal that answers a different question: *is vegetation actually growing here?* It does not feed into the suitability score. Instead, it is compared against the climate score to produce a **divergence surface**.

```python
def compute_divergence(suitability: SuitabilityResult, ndvi: xr.DataArray) -> DivergenceResult:
```

NDVI ∈ [−1, 1] is normalized to [0, 1] via `(ndvi + 1) / 2` before subtraction, making it directly comparable to the suitability score.

| Divergence sign | Meaning |
|---|---|
| Positive | Climate model predicts viability, satellite sees weak vegetation — potential emerging stress or model overestimation |
| Zero | Model and observed signal agree |
| Negative | Satellite sees strong vegetation the model underestimates — possible microclimate, variety adaptation, or model gap |

The divergence surface is the most scientifically valuable output of the Describe phase. It is where farmer ground truth meets modelled climate — and where the two disagreeing is often more informative than either alone.

### DescribeResult

`DescribePhaseRunner` returns `DescribeResult`, not `SuitabilityResult`. This separates phase-specific output (which may include imagery signals) from the general suitability model (which Predict and Prescribe phases also use).

```python
@dataclass
class DescribeResult:
    suitability: SuitabilityResult
    divergence: DivergenceResult | None  # None when no imagery source is provided
```

The runner accepts `imagery_source: ImagerySource | None = None`. When absent, divergence is `None` and the output is identical to a pure climate-envelope run.

---

## Plugin Architecture

See [PLUGIN.md](PLUGIN.md) for the full plugin development guide.

### Plugin Interface Contract

```python
from abc import ABC, abstractmethod
import xarray as xr
from groundshift.models import (
    BoundingBox, TimeRange, LayerData, SuitabilityModifier, PluginMetadata
)

class GroundshiftPlugin(ABC):

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Identity, threat tier, crop compatibility, data requirements."""

    @abstractmethod
    def validate_config(self, crop_profile: dict) -> bool:
        """Return True if this plugin can run for this crop profile."""

    @abstractmethod
    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        """Fetch and return the plugin's evidence data as a DataArray."""

    @abstractmethod
    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        """
        Return a SuitabilityModifier with spatial DataArray fields.

        factor_value: DataArray, values in [0.0, 1.0]
            0.0 = stressor eliminates viability entirely
            1.0 = stressor has no effect
        probability: DataArray, values in [0.0, 1.0]
            Likelihood the stressor occurs at each cell.
        confidence: DataArray, values in [0.0, 1.0]
            Certainty of the factor and probability estimates.
        """

    @abstractmethod
    def describe(self, score: SuitabilityModifier) -> str:
        """Human-readable explanation of this modifier for reporting."""
```

Plugins that work with vector data (GeoDataFrames, polygon features) should use the adapter utility before returning:

```python
from groundshift.core.utils.raster import geodataframe_to_modifier
```

### SuitabilityModifier Contract

```python
@dataclass
class SuitabilityModifier:
    plugin_id:    str
    region:       BoundingBox
    factor_value: xr.DataArray   # [0.0, 1.0] — severity if stressor occurs (0 = catastrophic)
    probability:  xr.DataArray   # [0.0, 1.0] — likelihood stressor occurs
    confidence:   xr.DataArray   # [0.0, 1.0] — certainty of the estimates
    metadata:     dict           # must include "threat_tier"; "custom_weight" for custom tier
```

`threat_tier` and `custom_weight` are declared on `PluginMetadata` and copied into `metadata` by the plugin. The aggregator reads them there to route each modifier into the correct tier.

### Modifier Aggregation

The aggregator applies the three-tier formula (see Suitability Model section). It accepts the envelope surface produced by `compute_envelope` and a list of plugin modifiers, returning a `SuitabilityResult` containing the final score surface and aggregate confidence surface — both as DataArrays.

```python
def aggregate_modifiers(
    envelope: xr.DataArray,
    modifiers: list[SuitabilityModifier],
) -> SuitabilityResult:
    """
    Returns SuitabilityResult(score, confidence) as DataArrays.
    Envelope is the hard ceiling — zero envelope cells are always zero output.
    Plugins are routed by threat_tier in their metadata dict.
    """
```

`Scorer.run()` accepts the same `envelope: xr.DataArray` and delegates directly to `aggregate_modifiers`. Plugins whose `validate_config` returns `False` are skipped entirely.

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

| Phase | Scope | Status |
|---|---|---|
| Phase 1 — Describe | Complete. WorldClimSource + ERA5Source + Sentinel2Source, DescribePhaseRunner, calibration anchor monitoring, imagery divergence surface, CLI `groundshift run --phase describe --source --imagery`. Landsat historical trend detection is next. | ✓ Functional |
| Phase 2 — Predict | Complete. CMIP6Source + PredictPhaseRunner + PredictResult, SSP2-4.5 and SSP5-8.5 scenarios, 2040/2060/2100 horizons, CLI `groundshift run --phase predict`. Scenario comparison surface and confidence surfaces are next. | ✓ Functional |
| Phase 3 — Prescribe | Core delta surfaces complete. `PrescribePhaseRunner` computes signed per-cell change (projected − current) per scenario+horizon; CLI `groundshift run --phase prescribe`. Opportunity zone detection, transition recommender, and cooperative infrastructure layer are next. | ✓ Partially functional |
| API + delivery | REST API, web app, mobile app, offline package generation | Planned |
| Plugin expansion | Frost risk, pest/disease, phenology plugins | Planned |
| Additional crops | Wine grape, olive, wheat profiles production-ready | Planned |
