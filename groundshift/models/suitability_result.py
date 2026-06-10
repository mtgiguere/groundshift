from dataclasses import dataclass

import xarray as xr


@dataclass
class SuitabilityResult:
    score: xr.DataArray
    confidence: xr.DataArray
