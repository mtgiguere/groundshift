"""
CMIP6 daily minimum temperature (tasmin) ingest script.

Downloads monthly near-surface daily minimum air temperature (tasmin) for
SSP2-4.5 and SSP5-8.5 scenarios from the Pangeo CMIP6 mirror on Google Cloud,
computes the annual minimum within each horizon window (2040, 2060, 2100),
converts units to °C, and saves as NetCDF to data/plugin_data/ for use by
the FrostRiskPlugin.

Usage:
    python scripts/ingest/download_cmip6_tasmin.py [--model UKESM1-0-LL]

Free — no account or API key required. Uses the public Pangeo CMIP6 Zarr store.

Install the optional ingest dependencies first:
    pip install groundshift[ingest]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "plugin_data"

_SCENARIOS = ["ssp245", "ssp585"]
_HORIZONS = [2040, 2060, 2100]
_HALF_WIDTH = 5

_DEFAULT_MODEL = "UKESM1-0-LL"
_DEFAULT_MEMBER = "r1i1p1f2"


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filenames(
    scenarios: list[str] = _SCENARIOS,
    horizons: list[int] = _HORIZONS,
) -> list[str]:
    return [
        f"frost_risk_min_temp_{scenario}_{horizon}.nc"
        for scenario in scenarios
        for horizon in horizons
    ]


def _all_files_present(dest_dir: Path) -> bool:
    return all((dest_dir / name).exists() for name in _expected_filenames())


def _tasmin_to_celsius(da: xr.DataArray) -> xr.DataArray:
    return da - 273.15


def _annual_min_from_monthly(da: xr.DataArray) -> xr.DataArray:
    """Collapse a monthly tasmin time series into annual minimums."""
    return da.groupby("time.year").min()


def _slice_horizon(
    da: xr.DataArray,
    horizon_year: int,
    half_width: int = _HALF_WIDTH,
) -> xr.DataArray:
    """Average an annual DataArray (year dim) over the horizon window."""
    windowed = da.sel(year=slice(horizon_year - half_width, horizon_year + half_width))
    return windowed.mean(dim="year")


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def download_cmip6_tasmin(
    dest_dir: Path = DATA_DIR,
    model: str = _DEFAULT_MODEL,
    member: str = _DEFAULT_MEMBER,
) -> None:
    """Download and pre-process CMIP6 tasmin, saving results to dest_dir.

    Skips download if all expected files already exist.
    Requires gcsfs and intake-esm: pip install groundshift[ingest]
    """
    try:
        import intake
    except ImportError as exc:
        raise ImportError(
            "gcsfs and intake-esm are required for CMIP6 download. "
            "Install with: pip install groundshift[ingest]"
        ) from exc

    dest_dir.mkdir(parents=True, exist_ok=True)

    if _all_files_present(dest_dir):
        print(f"Tasmin data already present at {dest_dir} — skipping download.")
        return

    catalog = intake.open_esm_datastore("https://storage.googleapis.com/cmip6/pangeo-cmip6.json")

    for scenario in _SCENARIOS:
        print(f"Downloading CMIP6 tasmin / {scenario}...")
        subset = catalog.search(
            experiment_id=scenario,
            table_id="Amon",
            variable_id="tasmin",
            source_id=model,
            member_id=member,
        )
        dsets = subset.to_dataset_dict(zarr_kwargs={"consolidated": True})
        key = list(dsets.keys())[0]
        da = dsets[key]["tasmin"]

        if "lat" in da.coords:
            da = da.rename({"lat": "y", "lon": "x"})

        annual_min = _annual_min_from_monthly(_tasmin_to_celsius(da))

        for horizon in _HORIZONS:
            surface = _slice_horizon(annual_min, horizon)
            filename = f"frost_risk_min_temp_{scenario}_{horizon}.nc"
            surface.to_netcdf(dest_dir / filename)
            print(f"  -> {dest_dir / filename}")

    print("CMIP6 tasmin download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download CMIP6 tasmin for frost risk.")
    parser.add_argument("--model", default=_DEFAULT_MODEL, help="CMIP6 source model ID.")
    parser.add_argument("--member", default=_DEFAULT_MEMBER, help="Ensemble member ID.")
    args = parser.parse_args()
    download_cmip6_tasmin(model=args.model, member=args.member)
