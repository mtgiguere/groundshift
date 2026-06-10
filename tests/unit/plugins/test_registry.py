import pytest

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin
from groundshift.plugins.registry import PluginRegistry

_META = PluginMetadata(
    plugin_id="test_plugin",
    name="Test Plugin",
    version="0.1.0",
    description="Registry test plugin.",
    author="Test",
    compatible_crops=["*"],
    data_sources=[],
    requires_network=False,
    phase_applicability=["describe"],
)


class _Plugin(GroundshiftPlugin):
    def __init__(self, plugin_id: str = "test_plugin") -> None:
        self._meta = PluginMetadata(
            plugin_id=plugin_id,
            name=plugin_id,
            version="0.1.0",
            description="",
            author="Test",
            compatible_crops=["*"],
            data_sources=[],
            requires_network=False,
            phase_applicability=["describe"],
        )

    @property
    def metadata(self) -> PluginMetadata:
        return self._meta

    def validate_config(self, crop_profile: dict) -> bool:
        return True

    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
        return LayerData(
            plugin_id=self.metadata.plugin_id,
            region=region,
            time_range=time_range,
            data=None,
            metadata={},
        )

    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
        return SuitabilityModifier(
            plugin_id=self.metadata.plugin_id,
            region=layer_data.region,
            modifier_value=0.0,
            confidence=1.0,
            geometry=None,
            metadata={},
        )

    def describe(self, score: SuitabilityModifier) -> str:
        return "No effect."


def test_new_registry_is_empty():
    registry = PluginRegistry()
    assert registry.list_plugins() == []


def test_registered_plugin_is_retrievable_by_id():
    registry = PluginRegistry()
    plugin = _Plugin("crop_drought")
    registry.register(plugin)
    assert registry.get("crop_drought") is plugin


def test_list_plugins_returns_all_registered():
    registry = PluginRegistry()
    a, b = _Plugin("alpha"), _Plugin("beta")
    registry.register(a)
    registry.register(b)
    assert set(registry.list_plugins()) == {a, b}


def test_registering_duplicate_id_raises():
    registry = PluginRegistry()
    registry.register(_Plugin("dup"))
    with pytest.raises(ValueError, match="dup"):
        registry.register(_Plugin("dup"))


def test_get_unknown_id_raises():
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.get("nonexistent")
