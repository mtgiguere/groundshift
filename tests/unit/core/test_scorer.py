from datetime import datetime

import pytest

from groundshift.core.scorer import Scorer
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.time_range import TimeRange
from groundshift.plugins.base import GroundshiftPlugin
from groundshift.plugins.registry import PluginRegistry

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)
TIME_RANGE = TimeRange(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1))
CROP_PROFILE: dict = {"crop_id": "coffee"}


def test_scorer_with_no_plugins_returns_base_score():
    registry = PluginRegistry()
    scorer = Scorer(registry)
    score, confidence = scorer.run(0.65, REGION, TIME_RANGE, CROP_PROFILE)
    assert score == 0.65
    assert confidence == 1.0


def test_scorer_applies_plugin_modifier_to_base_score(make_plugin):
    registry = PluginRegistry()
    registry.register(make_plugin("p1", modifier=0.2, confidence=1.0))
    scorer = Scorer(registry)
    score, _ = scorer.run(0.5, REGION, TIME_RANGE, CROP_PROFILE)
    assert score > 0.5


@pytest.mark.parametrize("base,modifier", [(0.95, 1.0), (0.05, -1.0)])
def test_scorer_output_score_is_clamped_to_0_1(base: float, modifier: float, make_plugin):
    registry = PluginRegistry()
    registry.register(make_plugin("p1", modifier=modifier, confidence=1.0))
    scorer = Scorer(registry)
    score, _ = scorer.run(base, REGION, TIME_RANGE, CROP_PROFILE)
    assert 0.0 <= score <= 1.0


def test_scorer_run_returns_suitability_result():
    registry = PluginRegistry()
    scorer = Scorer(registry)
    result = scorer.run(0.5, REGION, TIME_RANGE, CROP_PROFILE)
    assert isinstance(result, SuitabilityResult)
    assert result.score == 0.5
    assert result.confidence == 1.0


def test_scorer_skips_plugin_that_rejects_crop_profile():
    class _RejectingPlugin(GroundshiftPlugin):
        @property
        def metadata(self) -> PluginMetadata:
            return PluginMetadata(
                plugin_id="rejector",
                name="Rejector",
                version="0.1.0",
                description="",
                author="Test",
                compatible_crops=[],
                data_sources=[],
                requires_network=False,
                phase_applicability=["describe"],
            )

        def validate_config(self, crop_profile: dict) -> bool:
            return False

        def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
            raise AssertionError("fetch_data must not be called when validate_config returns False")

        def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
            raise AssertionError("score must not be called when validate_config returns False")

        def describe(self, score: SuitabilityModifier) -> str:
            return ""

    registry = PluginRegistry()
    registry.register(_RejectingPlugin())
    scorer = Scorer(registry)
    result_score, result_confidence = scorer.run(0.7, REGION, TIME_RANGE, CROP_PROFILE)
    assert result_score == 0.7
    assert result_confidence == 1.0
