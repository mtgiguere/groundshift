"""
CMIP6 climate projection data ingestion script.

Downloads monthly near-surface air temperature (tas) and precipitation flux (pr)
for SSP2-4.5 and SSP5-8.5 scenarios from the Pangeo CMIP6 mirror on Google Cloud,
computes decadal means around each horizon year (2040, 2060, 2100), converts
units to the Groundshift standard (°C, mm/year), and saves as NetCDF to
data/cmip6/.

Usage:
    python scripts/ingest/download_cmip6.py [--model UKESM1-0-LL]

Free — no account or API key required. Uses the public Pangeo CMIP6 Zarr store.

Install the optional ingest dependencies first:
    pip install groundshift[ingest]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "cmip6"

_SCENARIOS = ["ssp245", "ssp585"]
_HORIZONS = [2040, 2060, 2100]
_HALF_WIDTH = 5  # years either side of each horizon year

_VARIABLE_MAP = {
    "mean_annual_temp_c": "tas",
    "annual_precipitation_mm": "pr",
}

# Default model — UKESM1-0-LL has good global coverage and is widely used
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
        f"cmip6_{var}_{scenario}_{horizon}.nc"
        for var in _VARIABLE_MAP
        for scenario in scenarios
        for horizon in horizons
    ]


def _all_files_present(dest_dir: Path) -> bool:
    return all((dest_dir / name).exists() for name in _expected_filenames())


def _kelvin_to_celsius(da: xr.DataArray) -> xr.DataArray:
    return da - 273.15


def _precip_flux_to_mm_year(da: xr.DataArray) -> xr.DataArray:
    """Convert CMIP6 precipitation flux (kg m⁻² s⁻¹) to annual mm."""
    return da * 86400.0 * 365.25


def _annual_mean_from_monthly(da: xr.DataArray) -> xr.DataArray:
    """Collapse a monthly time series into annual means."""
    return da.groupby("time.year").mean()


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


def download_cmip6(
    dest_dir: Path = DATA_DIR,
    model: str = _DEFAULT_MODEL,
    member: str = _DEFAULT_MEMBER,
) -> None:
    """Download and pre-process CMIP6 projections, saving results to dest_dir.

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
        print(f"CMIP6 data already present at {dest_dir} — skipping download.")
        return

    catalog = intake.open_esm_datastore("https://storage.googleapis.com/cmip6/pangeo-cmip6.json")

    for scenario in _SCENARIOS:
        for cmip_var, gs_var in [("tas", "mean_annual_temp_c"), ("pr", "annual_precipitation_mm")]:
            print(f"Downloading CMIP6 {cmip_var} / {scenario}...")
            subset = catalog.search(
                experiment_id=scenario,
                table_id="Amon",
                variable_id=cmip_var,
                source_id=model,
                member_id=member,
            )
            dsets = subset.to_dataset_dict(zarr_kwargs={"consolidated": True})
            key = list(dsets.keys())[0]
            da = dsets[key][cmip_var]

            # Rename spatial coords to Groundshift convention
            if "lat" in da.coords:
                da = da.rename({"lat": "y", "lon": "x"})

            annual = _annual_mean_from_monthly(da)

            if cmip_var == "tas":
                annual = _kelvin_to_celsius(annual)
            else:
                annual = _precip_flux_to_mm_year(annual)

            for horizon in _HORIZONS:
                surface = _slice_horizon(annual, horizon)
                filename = f"cmip6_{gs_var}_{scenario}_{horizon}.nc"
                surface.to_netcdf(dest_dir / filename)
                print(f"  -> {dest_dir / filename}")

    print("CMIP6 download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download CMIP6 climate projections.")
    parser.add_argument("--model", default=_DEFAULT_MODEL, help="CMIP6 source model ID.")
    parser.add_argument("--member", default=_DEFAULT_MEMBER, help="Ensemble member ID.")
    args = parser.parse_args()
    download_cmip6(model=args.model, member=args.member)
