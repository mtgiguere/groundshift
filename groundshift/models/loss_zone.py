from dataclasses import dataclass

import xarray as xr


@dataclass
class LossZone:
    scenario: str
    horizon_year: int
    mask: xr.DataArray
    confidence: str


@dataclass
class LossZoneResult:
    zones: list[LossZone]
