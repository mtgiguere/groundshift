"""
GRACE-FO Terrestrial Water Storage (TWS) anomaly ingest script.

Downloads the GRACE-FO Level 3 monthly TWS anomaly gridded product from
NASA GES DISC (Goddard Earth Sciences Data and Information Services Center),
computes the long-term mean anomaly, and saves as NetCDF to
data/plugin_data/ for use by the GroundwaterPlugin.

The output file is groundwater_tws_baseline.nc — a single spatial grid
of mean TWS anomaly in cm EWT (equivalent water thickness) over the
available GRACE-FO record.

Usage:
    python scripts/ingest/download_grace.py [--start-year 2018] [--end-year 2023]

Requires a free NASA Earthdata account (https://urs.earthdata.nasa.gov/).
Install optional ingest dependencies first:
    pip install groundshift[ingest]

The download uses the CMR (Common Metadata Repository) API so no
hard-coded URLs are needed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "plugin_data"

_DEFAULT_START_YEAR = 2018
_DEFAULT_END_YEAR = 2023


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filename() -> str:
    return "groundwater_tws_baseline.nc"


def _all_files_present(dest_dir: Path) -> bool:
    return (dest_dir / _expected_filename()).exists()


def _tws_to_cm(da: xr.DataArray, unit: str = "cm") -> xr.DataArray:
    """Normalise TWS to cm EWT. GRACE-FO products may ship in cm or m."""
    if unit == "m":
        return da * 100.0
    return da


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def download_grace_tws(
    dest_dir: Path = DATA_DIR,
    start_year: int = _DEFAULT_START_YEAR,
    end_year: int = _DEFAULT_END_YEAR,
) -> None:
    """Download and pre-process GRACE-FO TWS anomaly, saving result to dest_dir.

    Skips download if the baseline file already exists.
    Requires earthaccess: pip install groundshift[ingest]
    """
    try:
        import earthaccess
    except ImportError as exc:
        raise ImportError(
            "earthaccess is required for GRACE-FO download. "
            "Install with: pip install groundshift[ingest]\n"
            "You also need a free NASA Earthdata account: "
            "https://urs.earthdata.nasa.gov/"
        ) from exc

    dest_dir.mkdir(parents=True, exist_ok=True)

    if _all_files_present(dest_dir):
        print(f"GRACE-FO data already present at {dest_dir} — skipping download.")
        return

    print("Authenticating with NASA Earthdata...")
    earthaccess.login(strategy="netrc")

    results = earthaccess.search_data(
        short_name="TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.1_V3",
        temporal=(f"{start_year}-01-01", f"{end_year}-12-31"),
    )
    if not results:
        raise RuntimeError(
            f"No GRACE-FO data found for {start_year}–{end_year}. "
            "Verify your Earthdata credentials and the date range."
        )

    print(f"Downloading {len(results)} GRACE-FO granule(s)...")
    files = earthaccess.download(results, local_path=str(dest_dir / "_grace_tmp"))

    datasets = [xr.open_dataset(f) for f in files]
    combined = xr.concat(datasets, dim="time")

    tws_var = "lwe_thickness"
    da = combined[tws_var]
    da = _tws_to_cm(da, unit="cm")

    baseline = da.mean(dim="time")
    if "lat" in baseline.coords:
        baseline = baseline.rename({"lat": "y", "lon": "x"})

    out_path = dest_dir / _expected_filename()
    baseline.to_dataset(name="tws_anomaly_cm").to_netcdf(out_path)
    print(f"  -> {out_path}")
    print("GRACE-FO download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download GRACE-FO TWS anomaly for groundwater.")
    parser.add_argument("--start-year", type=int, default=_DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=_DEFAULT_END_YEAR)
    args = parser.parse_args()
    download_grace_tws(start_year=args.start_year, end_year=args.end_year)
