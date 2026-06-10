import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin


def _scalar_da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]]))


@pytest.fixture
def make_plugin():
    def _factory(
        plugin_id: str = "test_plugin",
        factor: float = 1.0,
        probability: float = 1.0,
        confidence: float = 1.0,
        threat_tier: str = "stress",
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
            threat_tier=threat_tier,
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
                    data=_scalar_da(0.0),
                    metadata={},
                )

            def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
                return SuitabilityModifier(
                    plugin_id=self.metadata.plugin_id,
                    region=layer_data.region,
                    factor_value=_scalar_da(factor),
                    probability=_scalar_da(probability),
                    confidence=_scalar_da(confidence),
                    metadata={},
                )

            def describe(self, score: SuitabilityModifier) -> str:
                return f"factor={factor}"

        return _Plugin()

    return _factory
