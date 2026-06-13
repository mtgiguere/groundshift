"""
Land tenure security ingest script.

Downloads and processes PRINDEX (Property Rights Index) data for smallholder
land tenure security and writes land_tenure_security.nc to data/plugin_data/
for use by the LandTenurePlugin.

PRINDEX scores range 0–100 (fully insecure to fully secure). This script
normalises them to [0.0, 1.0] before saving.

Usage:
    python scripts/ingest/download_land_tenure.py [--data-dir PATH]

Requires a PRINDEX API key or manual CSV export from https://www.prindex.net/data/.
Set the PRINDEX_API_KEY environment variable or pass --csv-path to use a local file.
Install optional ingest dependencies first:
    pip install groundshift[ingest]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "plugin_data"


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filename() -> str:
    return "land_tenure_security.nc"


def _all_files_present(dest_dir: Path) -> bool:
    return (dest_dir / _expected_filename()).exists()


def _security_score_from_prindex(prindex_value: xr.DataArray) -> xr.DataArray:
    """Normalise PRINDEX score [0–100] to security score [0.0–1.0].

    Clips out-of-range values (survey artefacts or missing data flags).
    """
    return (prindex_value / 100.0).clip(0.0, 1.0)


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def download_land_tenure(
    dest_dir: Path = DATA_DIR,
    csv_path: Path | None = None,
) -> None:
    """Rasterise PRINDEX country scores to a spatial grid and write to dest_dir.

    Skips download if the baseline file already exists.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    if _all_files_present(dest_dir):
        print(f"Land tenure data already present at {dest_dir} — skipping.")
        return

    try:
        import requests
    except ImportError as exc:
        raise ImportError(
            "requests is required for PRINDEX API access. "
            "Install with: pip install groundshift[ingest]"
        ) from exc

    if csv_path is not None:
        import csv

        rows = list(csv.DictReader(csv_path.read_text().splitlines()))
    else:
        import os

        api_key = os.environ.get("PRINDEX_API_KEY", "")
        if not api_key:
            raise OSError(
                "Set PRINDEX_API_KEY environment variable or pass --csv-path "
                "to provide a local PRINDEX CSV export."
            )
        resp = requests.get(
            "https://api.prindex.net/v1/scores",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json().get("data", [])

    # Build {iso3: score} mapping and rasterise to a 1°×1° global grid
    country_scores: dict[str, float] = {}
    for row in rows:
        iso3 = row.get("iso3") or row.get("country_code", "")
        score_raw = row.get("score") or row.get("prindex_score")
        if iso3 and score_raw is not None:
            country_scores[iso3.upper()] = float(score_raw)

    print(f"Loaded PRINDEX scores for {len(country_scores)} countries.")

    try:
        import geopandas as gpd
    except ImportError as exc:
        raise ImportError(
            "geopandas is required for country rasterisation. "
            "Install with: pip install groundshift[ingest]"
        ) from exc

    world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    world["prindex"] = world["iso_a3"].map(country_scores).fillna(np.nan)

    lats = np.arange(-90.0, 90.5, 1.0)
    lons = np.arange(-180.0, 180.5, 1.0)
    grid = np.full((len(lats), len(lons)), np.nan, dtype="float32")

    from shapely.geometry import Point

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            pt = Point(lon, lat)
            match = world[world.geometry.contains(pt)]
            if not match.empty:
                raw = match.iloc[0]["prindex"]
                if not np.isnan(raw):
                    grid[i, j] = float(
                        _security_score_from_prindex(xr.DataArray(np.array([[raw]]))).values.flat[0]
                    )

    da = xr.DataArray(
        grid,
        coords={"lat": lats, "lon": lons},
        dims=["lat", "lon"],
    )
    out_path = dest_dir / _expected_filename()
    da.to_dataset(name="security_score").to_netcdf(out_path)
    print(f"  -> {out_path}")
    print("Land tenure download complete.")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=None,
        help="Path to a local PRINDEX CSV export (skips API download).",
    )
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    download_land_tenure(dest_dir=args.data_dir, csv_path=args.csv_path)
