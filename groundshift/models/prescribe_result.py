from dataclasses import dataclass

import xarray as xr


@dataclass
class ChangeProjection:
    scenario: str
    horizon_year: int
    delta: xr.DataArray


@dataclass
class PrescribeResult:
    change_projections: list[ChangeProjection]
