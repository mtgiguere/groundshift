from pathlib import Path

import rioxarray  # noqa: F401 — registers the .rio accessor on xr.DataArray
import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

_VARIABLE_MAP: dict[str, str] = {
    "mean_annual_temp_c": "bio_1",
    "annual_precipitation_mm": "bio_12",
    "altitude_m": "elev",
}


class WorldClimSource(ClimateDataSource):
    """ClimateDataSource backed by WorldClim v2.1 GeoTIFF files.

    Files are expected at base_dir/wc2.1_{resolution}_{variable_code}.tif.
    time_range is accepted but ignored — WorldClim is a 1970-2000 climatological
    baseline, not a time series.
    """

    def __init__(self, base_dir: Path, resolution: str = "10m") -> None:
        self._base_dir = Path(base_dir)
        self._resolution = resolution

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        if variable not in _VARIABLE_MAP:
            raise KeyError(f"'{variable}' — known variables: {sorted(_VARIABLE_MAP)}")

        var_code = _VARIABLE_MAP[variable]
        path = self._base_dir / f"wc2.1_{self._resolution}_{var_code}.tif"

        if not path.exists():
            raise FileNotFoundError(f"WorldClim file not found: {path}")

        da = xr.open_dataarray(path, engine="rasterio").squeeze("band", drop=True)
        return da.rio.clip_box(
            minx=region.min_lon,
            miny=region.min_lat,
            maxx=region.max_lon,
            maxy=region.max_lat,
        )
