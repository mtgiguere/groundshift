import pytest

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin


@pytest.fixture
def make_plugin():
    def _factory(
        plugin_id: str = "test_plugin",
        modifier: float = 0.0,
        confidence: float = 1.0,
    ) -> GroundshiftPlugin:
        meta = PluginMetadata(
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

        class _Plugin(GroundshiftPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return meta

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
                    modifier_value=modifier,
                    confidence=confidence,
                    geometry=None,
                    metadata={},
                )

            def describe(self, score: SuitabilityModifier) -> str:
                return f"modifier={modifier}"

        return _Plugin()

    return _factory
