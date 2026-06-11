"""Download Sentinel-2 NDVI composite for use with Sentinel2Source.

Queries the AWS Element 84 Earth Search STAC catalog (free, no account required)
for cloud-free Sentinel-2 L2A scenes over a named region, computes a median NDVI
composite from bands B04 (Red) and B08 (NIR), and saves the result as a GeoTIFF
to data/sentinel2/sentinel2_ndvi.tif.

Usage:
    python scripts/ingest/download_sentinel2.py [--region ethiopia] [--year 2023]

Install the optional ingest dependencies first:
    pip install groundshift[ingest]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "sentinel2"

# AWS Element 84 Earth Search STAC API — free, no authentication required.
_STAC_URL = "https://earth-search.aws.element84.com/v1"
_COLLECTION = "sentinel-2-l2a"

# Region bounding boxes [west, south, east, north] for STAC bbox query.
_REGION_BBOX: dict[str, list[float]] = {
    "ethiopia": [33.0, 3.0, 48.0, 15.0],
    "colombia": [-79.0, -4.0, -67.0, 13.0],
    "central_america": [-92.0, 7.0, -77.0, 18.0],
}


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _ndvi_from_bands(b4: xr.DataArray, b8: xr.DataArray) -> xr.DataArray:
    """Compute NDVI = (NIR − Red) / (NIR + Red). Result ∈ [−1, 1]."""
    return (b8 - b4) / (b8 + b4)


def _expected_filenames() -> list[str]:
    return ["sentinel2_ndvi.tif"]


def _all_files_present(dest_dir: Path) -> bool:
    return all((dest_dir / name).exists() for name in _expected_filenames())


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def download_sentinel2(
    region: str = "ethiopia",
    dest_dir: Path = DATA_DIR,
    year: int = 2023,
    max_cloud_cover: float = 20.0,
) -> None:
    """Download a Sentinel-2 NDVI composite for the named region.

    Skips download if sentinel2_ndvi.tif already exists.
    Requires pystac-client and stackstac: pip install groundshift[ingest]
    """
    try:
        import pystac_client
        import stackstac
    except ImportError as exc:
        raise ImportError(
            "pystac-client and stackstac are required for Sentinel-2 download. "
            "Install them with: pip install groundshift[ingest]"
        ) from exc

    if _all_files_present(dest_dir):
        print(f"Sentinel-2 data already present at {dest_dir} — skipping download.")
        return

    if region not in _REGION_BBOX:
        raise ValueError(f"Unknown region '{region}'. Available: {sorted(_REGION_BBOX)}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    bbox = _REGION_BBOX[region]
    date_range = f"{year}-01-01/{year}-12-31"

    print(f"Querying Sentinel-2 L2A scenes for {region} ({year})...")
    catalog = pystac_client.Client.open(_STAC_URL)
    search = catalog.search(
        collections=[_COLLECTION],
        bbox=bbox,
        datetime=date_range,
        query={"eo:cloud_cover": {"lt": max_cloud_cover}},
    )
    items = list(search.items())
    if not items:
        raise RuntimeError(
            f"No Sentinel-2 scenes found for {region} in {year} "
            f"with cloud cover < {max_cloud_cover}%. "
            "Try a wider date range or higher cloud cover threshold."
        )

    print(f"  Found {len(items)} scenes — compositing...")
    stack = stackstac.stack(
        items,
        assets=["B04", "B08"],
        bounds_latlon=bbox,
        resolution=0.1,  # ~10km — coarse enough to be fast, fine enough for regional analysis
    )

    b4 = stack.sel(band="B04").median(dim="time", skipna=True)
    b8 = stack.sel(band="B08").median(dim="time", skipna=True)
    ndvi = _ndvi_from_bands(b4, b8)

    out_path = dest_dir / "sentinel2_ndvi.tif"
    ndvi.rio.to_raster(out_path)
    print(f"  -> {out_path}")
    print("Sentinel-2 download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Sentinel-2 NDVI composite.")
    parser.add_argument("--region", default="ethiopia", choices=list(_REGION_BBOX))
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--max-cloud-cover", type=float, default=20.0)
    args = parser.parse_args()
    download_sentinel2(region=args.region, year=args.year, max_cloud_cover=args.max_cloud_cover)
