import geopandas as gpd
import numpy as np
import rasterio.features
import rasterio.transform
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_modifier import SuitabilityModifier


def geodataframe_to_modifier(
    gdf: gpd.GeoDataFrame,
    *,
    factor_column: str,
    plugin_id: str,
    region: BoundingBox,
    resolution_deg: float,
    probability: float = 1.0,
    confidence: float = 1.0,
    metadata: dict | None = None,
) -> SuitabilityModifier:
    """Rasterize a GeoDataFrame column onto a regular WGS84 grid.

    The GeoDataFrame must be in EPSG:4326. Cells not covered by any geometry
    receive factor_value=0.0 (no impact — treated as suitability-neutral).
    """
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        raise ValueError(f"GeoDataFrame must be in EPSG:4326, got {gdf.crs}")

    if factor_column not in gdf.columns:
        raise KeyError(factor_column)

    nrows = int((region.max_lat - region.min_lat) / resolution_deg)
    ncols = int((region.max_lon - region.min_lon) / resolution_deg)
    transform = rasterio.transform.from_bounds(
        region.min_lon, region.min_lat, region.max_lon, region.max_lat, ncols, nrows
    )

    shapes = zip(gdf.geometry, gdf[factor_column].astype("float64"))
    grid = rasterio.features.rasterize(
        shapes=shapes,
        out_shape=(nrows, ncols),
        transform=transform,
        fill=0.0,
        dtype="float32",
    )

    half = resolution_deg / 2
    lats = np.linspace(region.max_lat - half, region.min_lat + half, nrows)
    lons = np.linspace(region.min_lon + half, region.max_lon - half, ncols)
    factor_da = xr.DataArray(grid, dims=["y", "x"], coords={"y": lats, "x": lons})

    prob_da = xr.full_like(factor_da, probability)
    conf_da = xr.full_like(factor_da, confidence)

    return SuitabilityModifier(
        plugin_id=plugin_id,
        region=region,
        factor_value=factor_da,
        probability=prob_da,
        confidence=conf_da,
        metadata=metadata or {},
    )
