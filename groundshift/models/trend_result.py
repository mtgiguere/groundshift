from dataclasses import dataclass

import xarray as xr


@dataclass
class TrendResult:
    slope: xr.DataArray
