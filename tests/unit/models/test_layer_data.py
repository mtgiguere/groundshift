from datetime import datetime

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.time_range import TimeRange


def test_layer_data_stores_fields():
    region = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
    time_range = TimeRange(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1))
    data = {"ndvi": [0.6, 0.7]}

    layer = LayerData(
        plugin_id="imagery",
        region=region,
        time_range=time_range,
        data=data,
        metadata={"source": "Sentinel-2"},
    )
    assert layer.plugin_id == "imagery"
    assert layer.data == data
    assert layer.metadata["source"] == "Sentinel-2"
