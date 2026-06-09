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

- **Crop climate envelope modeling** — temperature, precipitation, soil, altitude thresholds with quality scoring distinct from viability scoring
- **CMIP6 suitability projection** — SSP2 and SSP5 scenarios, 2040 / 2060 / 2100 horizons
- **Satellite imagery analysis** — Sentinel-2 NDVI/EVI crop health, Landsat historical change detection (40+ year archive)
- **Ground truth vs. model divergence detection** — where observed signals lead or lag projections
- **Opportunity zone identification** — emerging suitability zones with infrastructure and market-access scoring
- **Plugin architecture** — extensible evidence layers (pest/disease, frost risk, groundwater, land tenure) drop in without touching core logic
- **Scenario comparison** — SSP2 vs. SSP5 side-by-side for any region
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
- PostgreSQL 15+ with PostGIS 3.4+
- Docker (recommended)
- AWS credentials (for S3 imagery access) or local Sentinel-2/Landsat data

### Installation

```bash
git clone https://github.com/mtgiguere/groundshift.git
cd groundshift
pip install -e ".[dev]"
cp .env.example .env  # configure your database and API keys
```

### Run your first analysis

```bash
# Describe current coffee suitability in Ethiopia
python -m groundshift run \
  --crop coffee \
  --region ethiopia \
  --phase describe \
  --output ./outputs/ethiopia_coffee_describe

# Full three-phase analysis
python -m groundshift run \
  --crop coffee \
  --region colombia \
  --phase all \
  --scenarios ssp245 ssp585 \
  --output ./outputs/colombia_coffee_full
```

### Run tests

```bash
pytest                   # full suite
pytest -m unit           # unit tests only
pytest -m integration    # requires live database and credentials
```

---

## Crop Profiles

Groundshift ships with the following crop profiles. Each profile defines the complete climate envelope, imagery parameters, and framing for the three-phase pipeline.

| Crop | Status | Primary Stress Region | Primary Opportunity Region |
|---|---|---|---|
| Arabica coffee | Active | Ethiopia, Colombia, Central America | Rwanda highlands, emerging elevation bands |
| Wine grape | Profile included | Burgundy, Napa, Rioja | England, Scandinavia, Tasmania |
| Olive | Profile included | Spain, Italy | UK, Pacific Northwest, New Zealand |
| Wheat | Profile included | South Asia, MENA | Canadian prairies, Siberia |
| Cocoa | Profile stub | Ghana, Ivory Coast | East Africa highlands |
| Tea | Profile stub | Darjeeling, Assam | Scottish Highlands (emerging) |

Adding a new crop requires only a YAML profile. See [PLUGIN.md](docs/PLUGIN.md) for the crop profile specification.

---

## Plugin System

Groundshift is designed for extensibility. Evidence layers beyond the core climate envelope and imagery analysis are implemented as plugins that drop into the pipeline without modifying core logic.

**Builtin plugins (shipped):**
- `climate_envelope` — CMIP6 + FAO GAEZ suitability scoring
- `imagery` — Sentinel-2 + Landsat NDVI and change detection

**Stretch plugins (interfaces defined, implementations in progress):**
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

---

## Data Sources

| Data | Source | License |
|---|---|---|
| Climate projections | CMIP6 (ESGF) | CC BY 4.0 |
| Crop suitability baselines | FAO GAEZ v4 | CC BY-NC 4.0 |
| Satellite imagery | Sentinel-2 (ESA/AWS) | CC BY 4.0 |
| Historical imagery | Landsat (USGS/AWS) | Public domain |
| Soil properties | SoilGrids 250m (ISRIC) | CC BY 4.0 |
| Surface water | JRC Global Surface Water | CC BY 4.0 |
| Smallholder farm locations | SPAM 2020 (IFPRI) | CC BY 4.0 |
| Crop production data | World Coffee Research | Various |

---

## License

MIT License. See LICENSE for details.

Data sources carry their own licenses — see the table above and `docs/data_licenses.md` for full attribution requirements.

---

## Contributing

Groundshift welcomes contributions, especially crop profiles, regional data integrations, and plugin implementations. Please read [PLUGIN.md](PLUGIN.md) before writing any plugin code, and ensure full test coverage accompanies any submission.

Open an issue before beginning significant work — coordination avoids duplication.

---

## Project Status

Active development. Phase 1 (Describe) targeting completion Q3 2026. See the project board for current sprint status.

*Built with the belief that information equity is a precondition for climate adaptation justice.*
