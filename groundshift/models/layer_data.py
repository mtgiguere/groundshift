from dataclasses import dataclass

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange


@dataclass
class LayerData:
    plugin_id: str
    region: BoundingBox
    time_range: TimeRange
    data: xr.DataArray
    metadata: dict
