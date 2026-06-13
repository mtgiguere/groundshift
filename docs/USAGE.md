# Groundshift — Usage Guide

This guide has two parts. Jump to the one that fits you.

- **[Part 1 — For Cooperative and Smallholder Partners](#part-1--for-cooperative-and-smallholder-partners):** Plain-language explanation of what Groundshift produces, what the numbers mean, and what questions to ask your technical partner.
- **[Part 2 — For Field Agronomists and NGO Staff](#part-2--for-field-agronomists-and-ngo-staff):** How to install, run, and interpret results; common workflows; API and offline package delivery.

---

## Part 1 — For Cooperative and Smallholder Partners

### What Groundshift Does

Groundshift is a tool that reads climate data and satellite images to tell you where a crop can grow well — today and in the future.

Think of it as a set of three questions asked for a specific crop in a specific region:

1. **Where are we now?** — How well does the current climate match what this crop needs? And does what farmers and satellites are actually seeing on the ground agree with that picture?

2. **Where are we heading?** — Under two different scenarios for future greenhouse gas emissions, how will suitability change by 2040, 2060, and 2100?

3. **What should we do?** — Which areas are emerging as opportunities? Which are declining and need support? And for farmers who need to transition, which other crops have the most similar requirements?

Groundshift does not tell farmers what to do. It surfaces the information that NGOs, cooperatives, and extension officers need to support better decisions.

---

### Understanding the Suitability Score

Every cell on the map has a **suitability score** between **0.0 and 1.0**.

| Score range | What it means |
|---|---|
| **0.8 – 1.0** | Excellent conditions — temperature, rainfall, and altitude are all close to ideal |
| **0.5 – 0.8** | Good conditions — one or more factors are somewhat off-optimal but the crop is viable |
| **0.1 – 0.5** | Marginal conditions — the crop can survive but yields and quality will be limited |
| **0.0** | Outside the viable range — this location cannot support this crop under current conditions |

A score does not tell you about soil quality, pest pressure, or market access — it tells you whether the *climate* is right. Other factors matter, but climate is the gate.

---

### What a Typical Report Looks Like

Your technical partner will run Groundshift and share output that looks something like this for a coffee analysis in Ethiopia:

```
Groundshift — Describe phase
  crop:    coffee
  region:  ethiopia
  cells:   6017 scored, 655 viable (score > 0)
  score:   min=0.000  mean=0.073  max=1.000

  calibration anchors:
    [origin_center] Yirgacheffe / Sidama: 0.812  (expected >= 0.70)
    [stress_reference] Central America Pacific Coast: n/a (outside region)
```

Here is what each line means:

- **cells: 6017 scored, 655 viable** — The region was divided into a grid. Of 6,017 cells, only 655 currently have climate conditions that can support coffee at all.
- **score: mean=0.073** — Averaged across the whole region (including zero-score unsuitable areas), the mean is low. This is expected — Ethiopia has a wide range of elevations and climates, most of which are not coffee country.
- **score: max=1.000** — Somewhere in this region the climate is as close to perfect for this crop as we can find. For Ethiopia, that's the Yirgacheffe highlands.
- **Yirgacheffe / Sidama: 0.812** — The origin heartland for Ethiopian coffee scores 0.812. That is above the alert threshold of 0.70, so no alarm is raised today. If that number drops below 0.70 in future runs, something important is changing.

---

### What a Calibration Anchor Is

Groundshift cross-checks its results against **calibration anchors** — named zones with known, documented real-world status.

| Anchor type | What it is | What to watch for |
|---|---|---|
| **Origin center** | A historically documented zone where this crop originated or reached peak quality | Scores should stay above 0.70. A decline is a meaningful signal. |
| **Production reference** | An active, commercially productive zone where the crop is grown at scale today | Scores should stay above 0.60. A decline warrants investigation. |
| **Stress reference** | A zone where real-world climate stress is already documented | Scores should be *low and declining*. A *high* score here means the model is missing something. |

When an origin or production anchor drops below its expected minimum, the report will show `*** ALERT ***`. This does not mean the model is broken — it may mean the climate in that region is genuinely changing. That distinction matters and requires agronomic judgement to interpret.

---

### Reading a Future Projection

A Predict phase run shows suitability under future climate scenarios:

```
Groundshift — Predict phase
  [ssp245 / 2040]    mean=0.041  viable=399 cells
  [ssp245 / 2100]    mean=0.025  viable=289 cells
  [ssp585 / 2100]    mean=0.011  viable=174 cells
```

- **ssp245** — a moderate emissions scenario (current policies roughly maintained)
- **ssp585** — a high emissions scenario (limited climate action)
- The numbers show that under either scenario, viable coffee area in this region shrinks over time.
- The difference between ssp245 and ssp585 at 2100 (289 vs 174 viable cells) is the estimated value of more aggressive climate action — in terms of sustained coffee viability in this region.

---

### Opportunity Zones and Loss Zones

The Prescribe phase identifies two types of areas:

**Opportunity zones** — places that are currently too cold or otherwise unsuitable for the crop, but are expected to gain suitability as temperatures rise. These are *not* a recommendation to expand farming immediately — they are signals worth watching and investigating on the ground.

**Loss zones** — places that are currently viable but are projected to decline meaningfully. Farmers in these zones are the highest priority for early transition support.

Each zone has a **confidence tier**:

| Confidence | What it means |
|---|---|
| **High** | Climate projections, satellite imagery, and historical trend data all agree |
| **Medium** | Two of the three signals agree |
| **Low** | Climate projections only — satellite data is either absent or disagrees |

A low-confidence opportunity zone does not mean it is wrong — it means there is not yet enough observational evidence to confirm it. High-confidence loss zones, where the climate model, the satellite imagery, and the historical Landsat trend are all pointing in the same direction, are the ones to act on urgently.

---

### Transition Recommendations

When a region is identified as a loss zone, Groundshift ranks alternative crops by how similar their climate requirements are to the current crop. A score of **1.0** means the alternative needs nearly identical conditions; **0.0** means there is almost no overlap.

This is a starting point, not a prescription. Soil conditions, markets, skills, and cultural context all matter. What the transition ranking tells you is: *given that this climate suits crop X, these are the alternatives that need the most similar conditions*, so existing farmer knowledge may transfer.

---

### What to Ask Your Technical Partner

If your organization is using Groundshift, here are useful questions to ask when you receive results:

- **"What is the current suitability score in our main production zones?"** — This gives you the baseline to track over time.
- **"Are any of our calibration anchors below threshold or trending downward?"** — This is the early warning system.
- **"How many cells are projected to become loss zones by 2040 under ssp245?"** — This gives you the urgency framing for medium-term planning.
- **"What is the confidence tier on the opportunity zones?"** — Low-confidence zones need ground verification before investment decisions.
- **"For our loss zones, what does the transition recommender show?"** — This opens the conversation about viable alternatives with similar climate requirements.

---

## Part 2 — For Field Agronomists and NGO Staff

### Prerequisites

- Python 3.12 or later
- Git
- At minimum 5 GB of free disk space for climate data
- An internet connection for the first data download

```bash
git clone https://github.com/mtgiguere/groundshift.git
cd groundshift
pip install -e ".[dev]"
```

---

### Step 1 — Download Climate Data

You need at least **WorldClim** data to run the Describe phase. Everything else is optional and adds additional outputs.

```bash
# WorldClim v2.1 — 1970–2000 baseline (~300 MB, free, no account required)
python scripts/ingest/download_worldclim.py
```

Optional additions:

```bash
# ERA5 reanalysis — more recent (2015–present), better for current-state analysis
# Requires a free CDS API key: https://cds.climate.copernicus.eu/how-to-api
pip install -e ".[ingest]"
python scripts/ingest/download_era5.py

# Sentinel-2 NDVI composite — satellite ground-truth signal (free, no account)
python scripts/ingest/download_sentinel2.py --region ethiopia --year 2023

# Landsat historical trend — per-pixel NDVI slope since 1985 (free, no account)
python scripts/ingest/download_landsat.py --region ethiopia

# CMIP6 climate projections — required for Predict and Prescribe phases
python scripts/ingest/download_cmip6.py

# CMIP6 minimum temperature — required for FrostRiskPlugin
python scripts/ingest/download_cmip6_tasmin.py
```

After downloading CMIP6 data, run the plugin data preparation script to derive files for the drought and heat stress plugins:

```bash
python scripts/prepare_plugin_data.py
```

Plugin files land in `data/plugin_data/`. Once they are present, all three climate threat plugins (frost risk, drought stress, heat stress) activate automatically on the next run — no configuration change needed.

---

### Step 2 — Run the Describe Phase

The Describe phase answers: **what is the current situation?**

```bash
groundshift run --crop coffee --region ethiopia --phase describe
```

Add `--source era5` to use ERA5 reanalysis (2015–present) instead of the WorldClim baseline:

```bash
groundshift run --crop coffee --region ethiopia --phase describe --source era5
```

Add `--imagery sentinel2` to compare the climate suitability score against actual satellite-observed NDVI:

```bash
groundshift run --crop coffee --region ethiopia --phase describe --imagery sentinel2
```

Add `--imagery landsat` to include the historical NDVI trend (per-pixel OLS slope since 1985):

```bash
groundshift run --crop coffee --region ethiopia --phase describe --imagery landsat
```

Combine both imagery sources in one run:

```bash
groundshift run --crop coffee --region ethiopia --phase describe --imagery sentinel2 landsat
```

**Interpreting Describe output:**

```
Groundshift — Describe phase
  crop:    coffee
  region:  ethiopia
  cells:   6017 scored, 655 viable (score > 0)
  score:   min=0.000  mean=0.073  max=1.000
  divergence (climate − observed):  min=-0.412  mean=0.118  max=0.631
  trend (NDVI/year):  mean=-0.0021  declining=412  improving=243 cells
```

- **viable cells** — cells where the climate envelope allows a score above zero. Use this for region sizing.
- **score mean** — average over all cells including zeros; typically low for heterogeneous regions.
- **divergence** — (climate suitability − satellite NDVI), normalized to the same 0–1 scale. Positive means the model predicts viability but satellites see weak vegetation — a potential emerging stress signal. Negative means satellites see strong vegetation the model underestimates — possible microclimate, variety adaptation, or a model gap to investigate.
- **trend** — number of cells with declining and improving NDVI slope. `declining > improving` with a negative mean slope is an early stress signal that predates most model predictions.

**Calibration anchor alerts:**

```
  calibration anchors:
    [origin_center] Yirgacheffe / Sidama: 0.812  (expected >= 0.70)
    [production_reference] Colombia Huila: n/a (outside region)  (expected >= 0.60)
    [stress_reference] Central America Pacific Coast: n/a (outside region)  (stress reference — no floor)
```

- `n/a (outside region)` — the anchor is not within the requested analysis region. Run a broader region to score it.
- `*** ALERT ***` — score is below the role-based expected minimum. Record it. Investigate whether it reflects real climate change, data gap, or a modeling issue before raising an alarm to stakeholders.

---

### Step 3 — Run the Predict Phase

The Predict phase requires CMIP6 data. It runs the same climate envelope model against projected climate conditions under SSP2-4.5 and SSP5-8.5 for 2040, 2060, and 2100.

```bash
groundshift run --crop coffee --region ethiopia --phase predict
```

Output:

```
[ssp245 / 2040]    min=0.000  mean=0.041  max=0.998  viable=399 cells
[ssp245 / 2060]    min=0.000  mean=0.033  max=0.972  viable=361 cells
[ssp245 / 2100]    min=0.000  mean=0.025  max=0.934  viable=289 cells
[ssp585 / 2040]    min=0.000  mean=0.039  max=0.991  viable=387 cells
[ssp585 / 2060]    min=0.000  mean=0.027  max=0.951  viable=318 cells
[ssp585 / 2100]    min=0.000  mean=0.011  max=0.823  viable=174 cells
```

The gap between ssp245 and ssp585 at each horizon reflects projected divergence under different emissions trajectories. Use this to frame the cost of inaction in terms stakeholders can respond to — not abstract temperature numbers, but viable area for their specific crop.

---

### Step 4 — Run the Prescribe Phase

The Prescribe phase requires both WorldClim and CMIP6 data. It computes change from current conditions, detects opportunity and loss zones, and ranks transition alternatives.

```bash
groundshift run --crop coffee --region ethiopia --phase prescribe
```

**Delta surface output:**

```
[ssp245 / 2040]    gaining= 214  losing= 441  mean_delta=-0.032
[ssp585 / 2100]    gaining=  71  losing= 584  mean_delta=-0.062
```

- **gaining** — cells improving in suitability relative to current baseline
- **losing** — cells declining
- **mean_delta** — average signed change across all cells. Negative means the region is overall declining.

**Opportunity zones:**

```
opportunity zones (emerging — currently low suitability, meaningfully gaining):
[ssp245 / 2040]      87 cells  confidence=low
```

These are cells currently below the viable threshold but gaining meaningfully under projections. `confidence=low` means the signal comes from CMIP6 only — satellite and Landsat data either weren't provided or do not yet agree. Satellite-verify on the ground before making investment recommendations based on low-confidence zones.

**Loss zones:**

```
loss zones (currently viable, meaningfully declining):
[ssp245 / 2040]     214 cells  confidence=low
```

Currently viable cells projected to decline significantly. These are the priority for early transition support conversations with farmers. Higher confidence tiers (medium = two signals agree, high = all three agree) indicate more urgent intervention timelines.

**Transition recommendations:**

```
transition suggestions (crops with most similar climate envelopes):
  1. tea                  overlap=0.71
  2. maize                overlap=0.58
```

Overlap scores use Jaccard similarity on the viable climate ranges for each variable averaged across all shared variables. An overlap of 0.71 means tea can grow in approximately 71% of the same climate range where coffee can grow. This is a starting point for discussions — soil type, market access, and farmer skills all require separate assessment.

---

### Available Crops

The following crop profiles are included:

| Crop | File | Calibration anchors |
|---|---|---|
| Coffee (Arabica) | `coffee.yaml` | Yirgacheffe/Sidama (origin), Colombia Huila (production), Central America Pacific (stress) |
| Coffee (Arabica, explicit) | `coffee_arabica.yaml` | Same anchors |
| Tea | `tea.yaml` | Darjeeling (origin), Kenya Highlands Kericho (production), Assam Brahmaputra (stress) |
| Cacao | `cacao.yaml` | Côte d'Ivoire Southwest (origin), Ghana Ashanti (production), Central Sulawesi (stress) |
| Maize | `maize.yaml` | Iowa Corn Belt (origin), Ethiopia Jimma/Wolega (production), NE Brazil Nordeste (stress) |

To run any crop, use its file stem as the `--crop` argument:

```bash
groundshift run --crop tea --region ethiopia --phase describe
groundshift run --crop cacao --region colombia --phase predict
groundshift run --crop maize --region ethiopia --phase prescribe
```

---

### Available Regions

The currently supported region identifiers are:

```
ethiopia
colombia
central_america
```

These are defined in `groundshift/regions/resolver.py`. Passing any other value raises an `UnknownRegionError`. If you need a region that is not listed, open an issue on GitHub.

---

### Using the REST API

Start the API server:

```bash
uvicorn groundshift.api.app:app --reload
# API is now available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

Key endpoints:

| Endpoint | What it returns |
|---|---|
| `GET /api/v1/crops` | All available crop profiles |
| `GET /api/v1/crops/coffee` | Full coffee climate envelope and thresholds |
| `GET /api/v1/regions` | All named regions with bounding boxes |
| `GET /api/v1/plugins` | All plugins with `available` or `unavailable` status based on data files present |
| `GET /api/v1/crops/coffee/emerging?region=ethiopia` | Pre-computed opportunity zones for coffee in Ethiopia |
| `GET /api/v1/crops/coffee/transitions` | Ranked alternative crops by Jaccard overlap with coffee's climate envelope |
| `GET /api/v1/packages/coffee/ethiopia` | Download a pre-generated MBTiles file for offline use |

The `/api/v1/plugins` endpoint is useful for checking which plugins are active before running an analysis. If a plugin shows `unavailable`, the corresponding data file is missing from `data/plugin_data/` and the plugin will not fire.

---

### Generating Offline Packages

Offline packages are for teams working with CivTAK or in low-connectivity field environments.

**Generate a pre-computed opportunity zone export (JSON):**

```bash
python scripts/export_emerging.py --crop coffee --region ethiopia
# Output: data/results/emerging/coffee_ethiopia.json
# Available via GET /api/v1/crops/coffee/emerging?region=ethiopia
```

**Export a zone mask to MBTiles (raster tile archive for CivTAK):**

```bash
python scripts/export_mbtiles.py \
  --input data/results/emerging/coffee_ethiopia.json \
  --output data/mbtiles/coffee_ethiopia.mbtiles \
  --color 255,165,0,180
# Produces a zoomable tile archive (zoom 4–10) with orange overlay cells
```

**Export a zone mask to KMZ (polygon overlay for CivTAK):**

```bash
python scripts/export_kmz.py \
  --input data/results/emerging/coffee_ethiopia.json \
  --output data/kmz/coffee_ethiopia.kmz
# Produces a KML+ZIP file; open directly in CivTAK for polygon overlays
```

The MBTiles file can also be downloaded via the API endpoint `GET /api/v1/packages/coffee/ethiopia` once the file is placed in `data/mbtiles/`.

---

### Adding a New Crop

Adding a crop requires only a YAML file in `crop_profiles/`. Copy an existing profile and fill in:

1. `crop_id`, `name`, `scientific_name`
2. `climate_envelope.thresholds` — temperature, precipitation, altitude viable/optimal ranges
3. Plugin threshold keys: `frost_threshold_c`, `precip_viable_min_mm`, `precip_optimal_min_mm`, `heat_max_threshold_c`
4. `calibration_anchors` — at minimum one origin center and one production reference

See the full crop profile specification in [PLUGIN.md](PLUGIN.md).

---

### Checking Which Plugins Are Active

```bash
# Via the API (start the server first):
curl http://localhost:8000/api/v1/plugins

# Response shows each plugin's status:
# {
#   "plugins": [
#     {"plugin_id": "frost_risk", "status": "available", ...},
#     {"plugin_id": "drought_stress", "status": "unavailable", ...},
#     ...
#   ]
# }
```

`unavailable` means the corresponding NetCDF data file is missing from `data/plugin_data/`. Run the relevant ingest script to activate it:

```bash
# Frost risk plugin:
python scripts/ingest/download_cmip6_tasmin.py

# Drought stress + heat stress plugins:
python scripts/prepare_plugin_data.py  # requires CMIP6 data already downloaded
```

---

### Running Tests

```bash
# Full test suite
pytest

# Unit tests only (no data files required)
pytest tests/unit/

# Integration smoke tests (requires WorldClim + ERA5 data on disk)
pytest tests/integration/
```

For the mutation audit (end-of-development quality check):

```bash
python scripts/mutation_audit.py --sample 47 --seed 42
```

This tests 47 randomly-sampled operator mutations across 11 core files and reports any that survive (i.e., no test caught the change). Survivors are worth investigating — they may indicate test gaps, or they may indicate the mutation doesn't change behaviour in a meaningful way.
