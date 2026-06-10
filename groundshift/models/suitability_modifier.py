from dataclasses import dataclass

import xarray as xr

from groundshift.models.bounding_box import BoundingBox


def _validate_unit_array(array: xr.DataArray, name: str) -> None:
    if float(array.min()) < 0.0 or float(array.max()) > 1.0:
        raise ValueError(f"{name} values must be in [0.0, 1.0]")


@dataclass
class SuitabilityModifier:
    plugin_id: str
    region: BoundingBox
    factor_value: xr.DataArray
    probability: xr.DataArray
    confidence: xr.DataArray
    metadata: dict

    def __post_init__(self) -> None:
        _validate_unit_array(self.factor_value, "factor_value")
        _validate_unit_array(self.probability, "probability")
        _validate_unit_array(self.confidence, "confidence")
