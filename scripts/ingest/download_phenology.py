"""
Phenology GDD ingest script.

Derives annual Growing Degree Day (GDD, base 0°C) grids from existing CMIP6
mean-temperature projection files and writes them as phenology_gdd_{scenario}_{horizon}.nc
to data/plugin_data/ for use by the PhenologyPlugin.

GDD = max(0, T_mean) × 365, where T_mean is the projected mean annual temperature (°C).
This approximation is appropriate when the underlying CMIP6 file already stores
annual-mean temperature rather than daily values.

Usage:
    python scripts/ingest/download_phenology.py [--data-dir PATH]

The CMIP6 source files (heat_stress_mean_temp_{scenario}_{horizon}.nc) must already
be present — run the WorldClim or CMIP6 download scripts first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "plugin_data"

_SCENARIOS = ["ssp245", "ssp585"]
_HORIZONS = [2040, 2060, 2080]


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filenames() -> list[str]:
    return [f"phenology_gdd_{s}_{h}.nc" for s in _SCENARIOS for h in _HORIZONS]


def _all_files_present(dest_dir: Path) -> bool:
    return all((dest_dir / f).exists() for f in _expected_filenames())


def _gdd_from_mean_temp(temp_c: xr.DataArray) -> xr.DataArray:
    """GDD (base 0°C) from mean annual temperature: GDD = max(0, T) × 365."""
    return xr.apply_ufunc(lambda t: np.maximum(0.0, t) * 365.0, temp_c)


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def derive_phenology_gdd(dest_dir: Path = DATA_DIR) -> None:
    """Derive GDD grids from existing CMIP6 mean-temp files and write to dest_dir.

    Skips derivation if all output files already exist.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    if _all_files_present(dest_dir):
        print(f"Phenology GDD files already present at {dest_dir} — skipping.")
        return

    for scenario in _SCENARIOS:
        for horizon in _HORIZONS:
            out_path = dest_dir / f"phenology_gdd_{scenario}_{horizon}.nc"
            if out_path.exists():
                continue

            src_path = dest_dir / f"heat_stress_mean_temp_{scenario}_{horizon}.nc"
            if not src_path.exists():
                print(f"  Source file missing: {src_path} — skipping {scenario}/{horizon}")
                continue

            ds = xr.open_dataset(src_path)
            varname = list(ds.data_vars)[0]
            temp_da = ds[varname]
            gdd_da = _gdd_from_mean_temp(temp_da)
            gdd_da.to_dataset(name="annual_gdd").to_netcdf(out_path)
            print(f"  -> {out_path}")

    print("Phenology GDD derivation complete.")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    derive_phenology_gdd(dest_dir=args.data_dir)
