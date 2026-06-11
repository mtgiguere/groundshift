"""Download Landsat Collection 2 NDVI trend surface for use with LandsatSource.

Queries the AWS Element 84 Earth Search STAC catalog (free, no account required)
for Landsat Collection 2 Level-2 scenes over a named region, computes annual
median NDVI composites from the full archive (1985-present), fits an OLS linear
regression per pixel, and saves the slope surface as a GeoTIFF to
data/landsat/landsat_ndvi_trend_{region}.tif.

The slope value (NDVI/year) is the primary output: negative = multi-decade
decline, positive = long-term improvement.

Usage:
    python scripts/ingest/download_landsat.py [--region ethiopia]

Install the optional ingest dependencies first:
    pip install groundshift[ingest]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xarray as xr

DATA_DIR = Path(__file__).parents[2] / "data" / "landsat"

# AWS Element 84 Earth Search STAC API — same endpoint as Sentinel-2, free, no auth.
_STAC_URL = "https://earth-search.aws.element84.com/v1"
_COLLECTION = "landsat-c2-l2"

_REGION_BBOX: dict[str, list[float]] = {
    "ethiopia": [33.0, 3.0, 48.0, 15.0],
    "colombia": [-79.0, -4.0, -67.0, 13.0],
    "central_america": [-92.0, 7.0, -77.0, 18.0],
}

# Full archive start — Landsat 5 TM operational from 1984.
_ARCHIVE_START = "1985-01-01"


# ---------------------------------------------------------------------------
# Pure helpers — unit-tested
# ---------------------------------------------------------------------------


def _expected_filename(region: str) -> str:
    return f"landsat_ndvi_trend_{region}.tif"


def _all_files_present(dest_dir: Path, region: str) -> bool:
    return (dest_dir / _expected_filename(region)).exists()


def _compute_ndvi(red: xr.DataArray, nir: xr.DataArray) -> xr.DataArray:
    """Compute NDVI = (NIR − Red) / (NIR + Red). Result ∈ [−1, 1]."""
    return (nir - red) / (nir + red)


def _annual_median(ndvi: xr.DataArray) -> xr.DataArray:
    """Compute annual median composites from a time-indexed DataArray.

    Expects ndvi to have a 'time' coordinate of integer years.
    Returns a DataArray with a 'time' dimension of unique years.
    """
    return ndvi.groupby("time").median()


def _compute_trend(annual_ndvi: xr.DataArray) -> xr.DataArray:
    """OLS linear regression per pixel over annual NDVI values.

    annual_ndvi must have a 'time' dimension of integer years.
    Returns a DataArray of slopes (NDVI/year), same spatial shape.
    """
    years = annual_ndvi.coords["time"].values.astype(float)
    years_centered = xr.DataArray(years - years.mean(), dims=["time"])
    denom = float((years_centered**2).sum().values)

    slope_values = (annual_ndvi * years_centered).sum(dim="time") / denom
    return slope_values


# ---------------------------------------------------------------------------
# I/O boundary — not unit-tested
# ---------------------------------------------------------------------------


def download_landsat(
    region: str = "ethiopia",
    dest_dir: Path = DATA_DIR,
    end_year: int = 2023,
    max_cloud_cover: float = 30.0,
) -> None:
    """Download Landsat NDVI trend surface for the named region.

    Skips download if landsat_ndvi_trend_{region}.tif already exists.
    Requires pystac-client and stackstac: pip install groundshift[ingest]
    """
    try:
        import pystac_client
        import stackstac
    except ImportError as exc:
        raise ImportError(
            "pystac-client and stackstac are required for Landsat download. "
            "Install them with: pip install groundshift[ingest]"
        ) from exc

    if _all_files_present(dest_dir, region):
        print(f"Landsat trend data already present at {dest_dir} — skipping download.")
        return

    if region not in _REGION_BBOX:
        raise ValueError(f"Unknown region '{region}'. Available: {sorted(_REGION_BBOX)}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    bbox = _REGION_BBOX[region]
    date_range = f"{_ARCHIVE_START}/{end_year}-12-31"

    print(f"Querying Landsat C2 L2 scenes for {region} ({_ARCHIVE_START}–{end_year})...")
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
            f"No Landsat scenes found for {region} ({_ARCHIVE_START}–{end_year}) "
            f"with cloud cover < {max_cloud_cover}%. "
            "Try a higher cloud cover threshold."
        )

    print(f"  Found {len(items)} scenes — loading NDVI bands...")
    stack = stackstac.stack(
        items,
        assets=["red", "nir08"],
        bounds_latlon=bbox,
        resolution=0.1,
    )

    red = stack.sel(band="red")
    nir = stack.sel(band="nir08")
    ndvi = _compute_ndvi(red.astype(float), nir.astype(float))

    print("  Computing annual median composites...")
    ndvi_with_year = ndvi.assign_coords(time=ndvi.time.dt.year)
    annual = _annual_median(ndvi_with_year)

    print("  Fitting per-pixel OLS trend...")
    slope = _compute_trend(annual)

    out_path = dest_dir / _expected_filename(region)
    slope.rio.set_spatial_dims(x_dim="x", y_dim="y").rio.to_raster(out_path)
    print(f"  -> {out_path}")
    print("Landsat download complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Landsat NDVI trend surface.")
    parser.add_argument("--region", default="ethiopia", choices=list(_REGION_BBOX))
    parser.add_argument("--end-year", type=int, default=2023)
    parser.add_argument("--max-cloud-cover", type=float, default=30.0)
    args = parser.parse_args()
    download_landsat(
        region=args.region, end_year=args.end_year, max_cloud_cover=args.max_cloud_cover
    )
