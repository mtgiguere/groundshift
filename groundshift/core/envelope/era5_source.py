from pathlib import Path

import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

# Maps Groundshift variable names to the pre-processed ERA5 NetCDF filenames.
# Files are produced by scripts/ingest/download_era5.py, which handles unit
# conversion (K→°C for temperature, m→mm/year for precipitation) before saving.
_VARIABLE_MAP: dict[str, str] = {
    "mean_annual_temp_c": "era5_mean_annual_temp_c.nc",
    "annual_precipitation_mm": "era5_annual_precipitation_mm.nc",
    "altitude_m": "era5_altitude_m.nc",
}


class ERA5Source(ClimateDataSource):
    """ClimateDataSource backed by pre-processed ERA5 reanalysis NetCDF files.

    Files are expected at base_dir/<variable>.nc, produced by the ERA5 ingest
    script. time_range is accepted but not used for selection — the files already
    represent the desired period average.

    ERA5 NetCDF coordinates (latitude/longitude) are renamed to y/x on output
    so all pipeline components receive consistent coordinate names regardless
    of which ClimateDataSource is active.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        if variable not in _VARIABLE_MAP:
            raise KeyError(f"'{variable}' — known variables: {sorted(_VARIABLE_MAP)}")

        path = self._base_dir / _VARIABLE_MAP[variable]
        if not path.exists():
            raise FileNotFoundError(f"ERA5 file not found: {path}")

        ds = xr.open_dataset(path)
        varname = list(ds.data_vars)[0]
        da = ds[varname]

        # Normalize ERA5 coordinate names to the pipeline convention.
        if "latitude" in da.coords:
            da = da.rename({"latitude": "y", "longitude": "x"})

        return da.sel(
            x=slice(region.min_lon, region.max_lon),
            y=slice(region.max_lat, region.min_lat),
        )
