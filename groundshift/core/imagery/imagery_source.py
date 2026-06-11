from abc import ABC, abstractmethod

import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange


class ImagerySource(ABC):
    @abstractmethod
    def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
        """Return a DataArray of imagery values for the named variable over the region."""
