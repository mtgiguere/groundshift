from pathlib import Path

import xarray as xr

from groundshift.core.envelope.climate_source import ClimateDataSource
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

_VARIABLE_MAP: dict[str, str] = {
    "mean_annual_temp_c": "mean_annual_temp_c",
    "annual_precipitation_mm": "annual_precipitation_mm",
}

_VALID_SCENARIOS = frozenset({"ssp245", "ssp585"})
_VALID_HORIZONS = frozenset({2040, 2060, 2100})


class CMIP6Source(ClimateDataSource):
    """ClimateDataSource backed by pre-processed CMIP6 NetCDF files.

    Files are expected at base_dir/cmip6_{variable}_{scenario}_{horizon_year}.nc,
    produced by the CMIP6 ingest script. time_range.scenario and
    time_range.horizon_year are required — CMIP6 data is scenario- and
    horizon-specific.

    CMIP6 NetCDF coordinates (lat/lon) are renamed to y/x on output so all
    pipeline components receive consistent coordinate names regardless of source.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)

    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        if variable not in _VARIABLE_MAP:
            raise KeyError(f"'{variable}' — known variables: {sorted(_VARIABLE_MAP)}")

        if not time_range.scenario:
            raise ValueError("CMIP6Source requires time_range.scenario (e.g. 'ssp245' or 'ssp585')")
        if not time_range.horizon_year:
            raise ValueError(
                "CMIP6Source requires time_range.horizon_year (e.g. 2040, 2060, or 2100)"
            )

        var_slug = _VARIABLE_MAP[variable]
        filename = f"cmip6_{var_slug}_{time_range.scenario}_{time_range.horizon_year}.nc"
        path = self._base_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"CMIP6 file not found: {path}")

        ds = xr.open_dataset(path)
        varname = list(ds.data_vars)[0]
        da = ds[varname]

        if "lat" in da.coords:
            da = da.rename({"lat": "y", "lon": "x"})

        return da.sel(
            x=slice(region.min_lon, region.max_lon),
            y=slice(region.max_lat, region.min_lat),
        )
