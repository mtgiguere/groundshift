from dataclasses import dataclass

import xarray as xr


@dataclass
class DivergenceResult:
    surface: xr.DataArray
