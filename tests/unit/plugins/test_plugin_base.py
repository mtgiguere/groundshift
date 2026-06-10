from datetime import datetime

import pytest

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1))

_META = PluginMetadata(
    plugin_id="test_plugin",
    name="Test Plugin",
    version="0.1.0",
    description="A minimal plugin for testing the base contract.",
    author="Test",
    compatible_crops=["*"],
    data_sources=[],
    requires_network=False,
    phase_applicability=["describe"],
)


def test_complete_plugin_can_be_instantiated(make_plugin):
    assert make_plugin() is not None


def test_plugin_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        GroundshiftPlugin()  # type: ignore[abstract]


@pytest.mark.parametrize(
    "missing", ["metadata", "validate_config", "fetch_data", "score", "describe"]
)
def test_plugin_missing_any_method_cannot_be_instantiated(missing):
    bases = (GroundshiftPlugin,)
    attrs = {
        "metadata": property(lambda self: _META),
        "validate_config": lambda self, cp: True,
        "fetch_data": lambda self, r, tr: None,
        "score": lambda self, ld, cp: None,
        "describe": lambda self, s: "",
    }
    del attrs[missing]
    incomplete_plugin = type("IncompletePlugin", bases, attrs)
    with pytest.raises(TypeError):
        incomplete_plugin()


def test_metadata_returns_plugin_metadata(make_plugin):
    assert isinstance(make_plugin().metadata, PluginMetadata)


def test_validate_config_returns_bool(make_plugin):
    assert isinstance(make_plugin().validate_config({}), bool)


def test_fetch_data_returns_layer_data(make_plugin):
    result = make_plugin().fetch_data(REGION, TIME_RANGE)
    assert isinstance(result, LayerData)


def test_score_returns_valid_suitability_modifier(make_plugin):
    plugin = make_plugin()
    layer = plugin.fetch_data(REGION, TIME_RANGE)
    result = plugin.score(layer, {})
    assert isinstance(result, SuitabilityModifier)
    assert -1.0 <= result.modifier_value <= 1.0
    assert 0.0 <= result.confidence <= 1.0


def test_describe_returns_nonempty_string(make_plugin):
    plugin = make_plugin()
    layer = plugin.fetch_data(REGION, TIME_RANGE)
    modifier = plugin.score(layer, {})
    result = plugin.describe(modifier)
    assert isinstance(result, str)
    assert len(result) > 0
