"""
ERA5 reanalysis data ingestion script.

Downloads monthly 2m temperature, total precipitation, and surface geopotential
from the Copernicus Climate Data Store (CDS), computes period averages, converts
units to the Groundshift standard (°C, mm/year, m), and saves as NetCDF to
data/era5/.

Usage:
    python scripts/ingest/download_era5.py [--year-start 2015] [--year-end 2024]

Requires a CDS API key:
    https://cds.climate.copernicus.eu/how-to-api

Install the optional ingest dependencies first:
    pip install groundshift[ingest]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "era5"

_G = 9.80665  # m/s² — standard gravity for geopotential conversion


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------

def _temp_cds_request(year_start: int, year_end: int) -> dict:
    return {
        "product_type": "monthly_averaged_reanalysis",
        "variable": "2m_temperature",
        "year": [str(y) for y in range(year_start, year_end + 1)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": "00:00",
        "format": "netcdf",
    }


def _precip_cds_request(year_start: int, year_end: int) -> dict:
    return {
        "product_type": "monthly_averaged_reanalysis",
        "variable": "total_precipitation",
        "year": [str(y) for y in range(year_start, year_end + 1)],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": "00:00",
        "format": "netcdf",
    }


def _expected_filenames() -> list[str]:
    return [
        "era5_mean_annual_temp_c.nc",
        "era5_annual_precipitation_mm.nc",
        "era5_altitude_m.nc",
    ]


def _all_files_present(dest_dir: Path) -> bool:
    return all((dest_dir / name).exists() for name in _expected_filenames())


def _kelvin_to_celsius(da: xr.DataArray) -> xr.DataArray:
    return da - 273.15


def _precip_to_mm_per_year(da: xr.DataArray) -> xr.DataArray:
    """Convert ERA5 total_precipitation (m/day) to annual mm."""
    return da * 365.25 * 1000.0


def _geopotential_to_altitude(da: xr.DataArray) -> xr.DataArray:
    """Convert ERA5 surface geopotential (m²/s²) to elevation (m)."""
    return da / _G


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------

def download_era5(
    dest_dir: Path = DATA_DIR,
    year_start: int = 2015,
    year_end: int = 2024,
) -> None:
    """Download and pre-process ERA5 data, saving results to dest_dir.

    Skips download if all expected files already exist.
    Requires cdsapi: pip install groundshift[ingest]
    """
    try:
        import cdsapi
    except ImportError as exc:
        raise ImportError(
            "cdsapi is required for ERA5 download. "
            "Install it with: pip install groundshift[ingest]"
        ) from exc

    dest_dir.mkdir(parents=True, exist_ok=True)

    if _all_files_present(dest_dir):
        print(f"ERA5 data already present at {dest_dir} — skipping download.")
        return

    client = cdsapi.Client()
    tmp = dest_dir / "_tmp"
    tmp.mkdir(exist_ok=True)

    # --- Temperature ---
    print("Downloading ERA5 2m temperature...")
    temp_raw = tmp / "era5_t2m_raw.nc"
    client.retrieve(
        "reanalysis-era5-single-levels-monthly-means",
        _temp_cds_request(year_start, year_end),
        str(temp_raw),
    )
    ds_temp = xr.open_dataset(temp_raw)
    mean_temp = _kelvin_to_celsius(ds_temp["t2m"].mean(dim="time"))
    mean_temp.to_netcdf(dest_dir / "era5_mean_annual_temp_c.nc")
    print(f"  -> {dest_dir / 'era5_mean_annual_temp_c.nc'}")

    # --- Precipitation ---
    print("Downloading ERA5 total precipitation...")
    precip_raw = tmp / "era5_tp_raw.nc"
    client.retrieve(
        "reanalysis-era5-single-levels-monthly-means",
        _precip_cds_request(year_start, year_end),
        str(precip_raw),
    )
    ds_precip = xr.open_dataset(precip_raw)
    annual_precip = _precip_to_mm_per_year(ds_precip["tp"].mean(dim="time"))
    annual_precip.to_netcdf(dest_dir / "era5_annual_precipitation_mm.nc")
    print(f"  -> {dest_dir / 'era5_annual_precipitation_mm.nc'}")

    # --- Elevation from geopotential (static field, no year range needed) ---
    print("Downloading ERA5 surface geopotential (orography)...")
    geopot_raw = tmp / "era5_z_raw.nc"
    client.retrieve(
        "reanalysis-era5-single-levels-monthly-means",
        {
            "product_type": "monthly_averaged_reanalysis",
            "variable": "geopotential",
            "year": [str(year_start)],
            "month": ["01"],
            "time": "00:00",
            "format": "netcdf",
        },
        str(geopot_raw),
    )
    ds_z = xr.open_dataset(geopot_raw)
    altitude = _geopotential_to_altitude(ds_z["z"].squeeze())
    altitude.to_netcdf(dest_dir / "era5_altitude_m.nc")
    print(f"  -> {dest_dir / 'era5_altitude_m.nc'}")

    print("ERA5 download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download ERA5 climate data.")
    parser.add_argument("--year-start", type=int, default=2015)
    parser.add_argument("--year-end", type=int, default=2024)
    args = parser.parse_args()
    download_era5(year_start=args.year_start, year_end=args.year_end)
