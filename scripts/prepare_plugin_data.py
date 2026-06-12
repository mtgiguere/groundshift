"""
Derive plugin-specific data files from existing CMIP6 NetCDF downloads.

Reads from data/cmip6/ and writes plugin-ready files to data/plugin_data/.
Run after download_cmip6.py to unblock drought_stress and heat_stress plugins.

frost_risk requires CMIP6 tasmin data — see scripts/ingest/download_cmip6.py
(tasmin support not yet implemented; frost_risk files must be provided separately).

Usage:
    python scripts/prepare_plugin_data.py [--cmip6-dir PATH] [--output-dir PATH]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

_CMIP6_DIR = Path(__file__).parents[1] / "data" / "cmip6"
_OUTPUT_DIR = Path(__file__).parents[1] / "data" / "plugin_data"

_SCENARIOS = ["ssp245", "ssp585"]
_HORIZONS = [2040, 2060, 2100]


def _plugin_filenames(
    scenarios: list[str] = _SCENARIOS,
    horizons: list[int] = _HORIZONS,
) -> list[str]:
    names = []
    for scenario in scenarios:
        for horizon in horizons:
            names.append(f"drought_stress_precip_{scenario}_{horizon}.nc")
            names.append(f"heat_stress_mean_temp_{scenario}_{horizon}.nc")
    return names


def _derive_file(src: Path, dst: Path, new_varname: str) -> Path:
    ds = xr.open_dataset(src)
    old_varname = list(ds.data_vars)[0]
    ds = ds.rename({old_varname: new_varname})
    dst.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(dst)
    return dst


def prepare_drought_stress_data(cmip6_dir: Path, output_dir: Path) -> list[Path]:
    created = []
    for scenario in _SCENARIOS:
        for horizon in _HORIZONS:
            src = Path(cmip6_dir) / f"cmip6_annual_precipitation_mm_{scenario}_{horizon}.nc"
            if not src.exists():
                continue
            dst = Path(output_dir) / f"drought_stress_precip_{scenario}_{horizon}.nc"
            created.append(_derive_file(src, dst, "annual_precipitation_mm"))
    return created


def prepare_heat_stress_data(cmip6_dir: Path, output_dir: Path) -> list[Path]:
    created = []
    for scenario in _SCENARIOS:
        for horizon in _HORIZONS:
            src = Path(cmip6_dir) / f"cmip6_mean_annual_temp_c_{scenario}_{horizon}.nc"
            if not src.exists():
                continue
            dst = Path(output_dir) / f"heat_stress_mean_temp_{scenario}_{horizon}.nc"
            created.append(_derive_file(src, dst, "mean_annual_temp_c"))
    return created


def prepare_all_plugin_data(cmip6_dir: Path, output_dir: Path) -> dict[str, list[Path]]:
    return {
        "drought_stress": prepare_drought_stress_data(cmip6_dir, output_dir),
        "heat_stress": prepare_heat_stress_data(cmip6_dir, output_dir),
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmip6-dir", type=Path, default=_CMIP6_DIR)
    parser.add_argument("--output-dir", type=Path, default=_OUTPUT_DIR)
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    result = prepare_all_plugin_data(args.cmip6_dir, args.output_dir)
    total = sum(len(v) for v in result.values())
    print(f"Created {total} plugin data file(s) in {args.output_dir}")
    for plugin_id, paths in result.items():
        for p in paths:
            print(f"  [{plugin_id}] {p.name}")
    if total == 0:
        print("No CMIP6 source files found — run scripts/ingest/download_cmip6.py first.")
