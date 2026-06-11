from datetime import datetime

import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))


def test_imagery_source_cannot_be_instantiated_directly():
    from groundshift.core.imagery.imagery_source import ImagerySource

    with pytest.raises(TypeError):
        ImagerySource()  # type: ignore[abstract]


def test_imagery_source_subclass_without_fetch_cannot_be_instantiated():
    from groundshift.core.imagery.imagery_source import ImagerySource

    class Incomplete(ImagerySource):
        pass

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_imagery_source_concrete_subclass_satisfies_contract():
    from groundshift.core.imagery.imagery_source import ImagerySource

    class FakeSource(ImagerySource):
        def fetch(self, variable: str, region: BoundingBox, time_range: TimeRange) -> xr.DataArray:
            import numpy as np

            data = np.full((4, 4), 0.7, dtype="float32")
            return xr.DataArray(data, dims=["y", "x"])

    source = FakeSource()
    result = source.fetch("ndvi", REGION, TIME_RANGE)
    assert isinstance(result, xr.DataArray)
