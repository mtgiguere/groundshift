from dataclasses import dataclass

import xarray as xr


@dataclass
class OpportunityZone:
    scenario: str
    horizon_year: int
    mask: xr.DataArray
    confidence: str


@dataclass
class OpportunityZoneResult:
    zones: list[OpportunityZone]
