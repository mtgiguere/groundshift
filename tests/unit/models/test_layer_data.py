from datetime import datetime

import numpy as np
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.time_range import TimeRange

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1))


def test_layer_data_stores_fields():
    data = xr.DataArray(np.array([[0.6, 0.7], [0.8, 0.9]]))
    layer = LayerData(
        plugin_id="imagery",
        region=REGION,
        time_range=TIME_RANGE,
        data=data,
        metadata={"source": "Sentinel-2"},
    )
    assert layer.plugin_id == "imagery"
    assert isinstance(layer.data, xr.DataArray)
    assert layer.metadata["source"] == "Sentinel-2"
