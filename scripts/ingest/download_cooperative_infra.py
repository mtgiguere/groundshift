"""
Cooperative infrastructure accessibility ingest script.

Queries OSM (OpenStreetMap) via the Overpass API for coffee mills, wet
processors, cooperative collection points, and export-route road networks.
For each grid cell, computes an accessibility score using inverse-distance
decay from the nearest facility, then saves as NetCDF to data/plugin_data/
for use by the CooperativeInfraPlugin.

The output file is cooperative_infra_access.nc — a single spatial grid
of access scores in [0.0, 1.0] where 1.0 = at a facility, approaching 0
at remote distances.

Usage:
    python scripts/ingest/download_cooperative_infra.py \
        [--bbox MIN_LON MIN_LAT MAX_LON MAX_LAT] \
        [--resolution 0.1] \
        [--decay-km 50]

Requires internet access for the Overpass API query. No authentication needed.
Install optional ingest dependencies first:
    pip install groundshift[ingest]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "plugin_data"

_DEFAULT_DECAY_KM = 50.0


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filename() -> str:
    return "cooperative_infra_access.nc"


def _all_files_present(dest_dir: Path) -> bool:
    return (dest_dir / _expected_filename()).exists()


def _access_score_from_distance_km(
    distance_km: xr.DataArray,
    decay_km: float = _DEFAULT_DECAY_KM,
) -> xr.DataArray:
    """Compute access score [0, 1] from distance to nearest facility using exponential decay.

    score = exp(-distance_km / decay_km)

    At distance 0: score = 1.0 (at a facility).
    At distance = decay_km: score ≈ 0.37.
    At distance = 3 × decay_km: score ≈ 0.05.
    """
    return np.exp(-distance_km / decay_km).clip(0.0, 1.0)


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------

_OVERPASS_QUERY = """
[out:json][timeout:120];
(
  node["amenity"="coffee_mill"];
  node["craft"="coffee_roaster"];
  node["industrial"="coffee"];
  way["landuse"="farmyard"]["crop"="coffee"];
  node["amenity"="cooperative"];
  node["office"="cooperative"];
);
out center;
"""


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))


def download_cooperative_infra(
    dest_dir: Path = DATA_DIR,
    bbox: tuple[float, float, float, float] | None = None,
    resolution: float = 0.1,
    decay_km: float = _DEFAULT_DECAY_KM,
) -> None:
    """Query OSM facilities and write access score grid to dest_dir.

    Skips download if the baseline file already exists.
    """
    try:
        import requests
    except ImportError as exc:
        raise ImportError(
            "requests is required for Overpass API queries. "
            "Install with: pip install groundshift[ingest]"
        ) from exc

    dest_dir.mkdir(parents=True, exist_ok=True)

    if _all_files_present(dest_dir):
        print(f"Cooperative infrastructure data already present at {dest_dir} — skipping.")
        return

    if bbox is None:
        # Default to a broad Ethiopia+Kenya+Colombia extent
        min_lon, min_lat, max_lon, max_lat = -78.0, -5.0, 45.0, 15.0
    else:
        min_lon, min_lat, max_lon, max_lat = bbox

    bbox_filter = f"({min_lat},{min_lon},{max_lat},{max_lon})"
    query = _OVERPASS_QUERY.replace("];", f"{bbox_filter};", 1)

    print("Querying Overpass API for cooperative infrastructure...")
    response = requests.get(
        "https://overpass-api.de/api/interpreter",
        params={"data": query},
        timeout=120,
    )
    response.raise_for_status()
    elements = response.json().get("elements", [])

    facilities = []
    for el in elements:
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is not None and lon is not None:
            facilities.append((float(lat), float(lon)))

    print(f"Found {len(facilities)} facilities.")

    lats = np.arange(min_lat, max_lat + resolution, resolution)
    lons = np.arange(min_lon, max_lon + resolution, resolution)

    access_grid = np.zeros((len(lats), len(lons)), dtype="float32")
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            if facilities:
                min_dist = min(_haversine_km(lat, lon, f[0], f[1]) for f in facilities)
                access_grid[i, j] = float(
                    _access_score_from_distance_km(
                        xr.DataArray(np.array([[min_dist]])), decay_km
                    ).values.flat[0]
                )

    da = xr.DataArray(
        access_grid,
        coords={"lat": lats, "lon": lons},
        dims=["lat", "lon"],
    )
    out_path = dest_dir / _expected_filename()
    da.to_dataset(name="access_score").to_netcdf(out_path)
    print(f"  -> {out_path}")
    print("Cooperative infrastructure download complete.")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=None,
    )
    parser.add_argument("--resolution", type=float, default=0.1)
    parser.add_argument("--decay-km", type=float, default=_DEFAULT_DECAY_KM)
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    return parser


if __name__ == "__main__":
    args = _build_arg_parser().parse_args()
    bbox = tuple(args.bbox) if args.bbox else None
    download_cooperative_infra(
        dest_dir=args.output_dir,
        bbox=bbox,
        resolution=args.resolution,
        decay_km=args.decay_km,
    )
