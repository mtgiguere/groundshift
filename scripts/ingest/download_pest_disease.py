"""
Coffee Leaf Rust (CLR) climate risk index ingest script.

Derives a Coffee Leaf Rust (Hemileia vastatrix) climate suitability index
from existing CMIP6 temperature and precipitation projections, and saves
as NetCDF to data/plugin_data/ for use by the PestDiseasePlugin.

CLR outbreak probability is modelled as the product of:
  - A temperature suitability score (peak at 18–22°C, zero below 10°C or above 30°C)
  - A precipitation suitability score (rises with rainfall above 800mm, saturates at 2000mm)

This is a simplified, climatological approximation of CLR seasonality.
For precision disease modelling, replace with outputs from a dedicated
epidemiological model (e.g. CARAH CLR or similar).

Usage:
    python scripts/ingest/download_pest_disease.py [--cmip6-dir PATH] [--output-dir PATH]

Run after scripts/ingest/download_cmip6.py — requires the CMIP6 mean temperature
and precipitation files to be present.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

_CMIP6_DIR = Path(__file__).parents[2] / "data" / "cmip6"
_OUTPUT_DIR = Path(__file__).parents[2] / "data" / "plugin_data"

_SCENARIOS = ["ssp245", "ssp585"]
_HORIZONS = [2040, 2060, 2100]

# CLR temperature envelope (°C)
_TEMP_VIABLE_MIN = 10.0
_TEMP_OPTIMAL_MIN = 18.0
_TEMP_OPTIMAL_MAX = 22.0
_TEMP_VIABLE_MAX = 30.0

# CLR moisture threshold (mm)
_PRECIP_LOW = 800.0  # below this: minimal spore germination
_PRECIP_HIGH = 2000.0  # above this: saturation (no further increase)


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filenames(
    scenarios: list[str] = _SCENARIOS,
    horizons: list[int] = _HORIZONS,
) -> list[str]:
    return [
        f"pest_disease_clr_{scenario}_{horizon}.nc"
        for scenario in scenarios
        for horizon in horizons
    ]


def _all_files_present(dest_dir: Path) -> bool:
    return all((dest_dir / name).exists() for name in _expected_filenames())


def _clr_risk_from_climate(
    temp_c: xr.DataArray,
    precip_mm: xr.DataArray,
) -> xr.DataArray:
    """Compute CLR climate risk index [0, 1] from mean annual temp and precip."""
    # Temperature score: trapezoid peaking between optimal_min and optimal_max
    below_ramp = (temp_c - _TEMP_VIABLE_MIN) / (_TEMP_OPTIMAL_MIN - _TEMP_VIABLE_MIN)
    above_ramp = (_TEMP_VIABLE_MAX - temp_c) / (_TEMP_VIABLE_MAX - _TEMP_OPTIMAL_MAX)
    temp_score = xr.where(
        temp_c < _TEMP_VIABLE_MIN,
        0.0,
        xr.where(
            temp_c < _TEMP_OPTIMAL_MIN,
            below_ramp,
            xr.where(
                temp_c <= _TEMP_OPTIMAL_MAX,
                1.0,
                xr.where(temp_c <= _TEMP_VIABLE_MAX, above_ramp, 0.0),
            ),
        ),
    ).clip(0.0, 1.0)

    # Precipitation score: linear ramp from low to high threshold
    precip_score = ((precip_mm - _PRECIP_LOW) / (_PRECIP_HIGH - _PRECIP_LOW)).clip(0.0, 1.0)

    return (temp_score * precip_score).clip(0.0, 1.0)


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def derive_clr_risk(cmip6_dir: Path, output_dir: Path) -> list[Path]:
    """Derive CLR risk index files from CMIP6 temperature and precip data."""
    created = []
    for scenario in _SCENARIOS:
        for horizon in _HORIZONS:
            temp_src = cmip6_dir / f"cmip6_mean_annual_temp_c_{scenario}_{horizon}.nc"
            precip_src = cmip6_dir / f"cmip6_annual_precipitation_mm_{scenario}_{horizon}.nc"
            if not temp_src.exists() or not precip_src.exists():
                continue

            temp_ds = xr.open_dataset(temp_src)
            precip_ds = xr.open_dataset(precip_src)

            temp_var = list(temp_ds.data_vars)[0]
            precip_var = list(precip_ds.data_vars)[0]

            clr_risk = _clr_risk_from_climate(temp_ds[temp_var], precip_ds[precip_var])
            output_dir.mkdir(parents=True, exist_ok=True)
            dst = output_dir / f"pest_disease_clr_{scenario}_{horizon}.nc"
            clr_risk.to_dataset(name="clr_risk_index").to_netcdf(dst)
            created.append(dst)
            print(f"  -> {dst}")

    return created


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmip6-dir", type=Path, default=_CMIP6_DIR)
    parser.add_argument("--output-dir", type=Path, default=_OUTPUT_DIR)
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    created = derive_clr_risk(args.cmip6_dir, args.output_dir)
    if created:
        print(f"Created {len(created)} CLR risk file(s).")
    else:
        print("No CMIP6 source files found — run scripts/ingest/download_cmip6.py first.")
