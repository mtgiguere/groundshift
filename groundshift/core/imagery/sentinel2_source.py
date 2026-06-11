from pathlib import Path

import rioxarray  # noqa: F401 — registers the .rio accessor on xr.DataArray
import xarray as xr

from groundshift.core.imagery.imagery_source import ImagerySource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

_VARIABLE_MAP: dict[str, str] = {
    "ndvi": "sentinel2_ndvi.tif",
}


class Sentinel2Source(ImagerySource):
    """ImagerySource backed by pre-computed Sentinel-2 GeoTIFF files.

    Files are expected at base_dir/sentinel2_{variable}.tif.
    time_range is accepted but currently ignored — files represent a
    composited or single-date mosaic, not a time series.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        if variable not in _VARIABLE_MAP:
            raise KeyError(f"'{variable}' — known variables: {sorted(_VARIABLE_MAP)}")

        path = self._base_dir / _VARIABLE_MAP[variable]
        if not path.exists():
            raise FileNotFoundError(f"Sentinel-2 file not found: {path}")

        da = xr.open_dataarray(path, engine="rasterio").squeeze("band", drop=True)
        return da.rio.clip_box(
            minx=region.min_lon,
            miny=region.min_lat,
            maxx=region.max_lon,
            maxy=region.max_lat,
        )
