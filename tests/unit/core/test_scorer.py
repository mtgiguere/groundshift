from datetime import datetime

import numpy as np
import pytest
import xarray as xr

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


def _da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]]))


def test_scorer_with_no_plugins_returns_envelope_unchanged():
    registry = PluginRegistry()
    scorer = Scorer(registry)
    result = scorer.run(_da(0.65), REGION, TIME_RANGE, CROP_PROFILE)
    assert float(result.score.mean()) == 0.65
    assert float(result.confidence.mean()) == 1.0


def test_scorer_returns_suitability_result():
    registry = PluginRegistry()
    result = Scorer(registry).run(_da(0.5), REGION, TIME_RANGE, CROP_PROFILE)
    assert isinstance(result, SuitabilityResult)


def test_scorer_stress_plugin_reduces_score(make_plugin):
    registry = PluginRegistry()
    registry.register(make_plugin("p1", factor=0.5, probability=1.0, threat_tier="stress"))
    result = Scorer(registry).run(_da(0.8), REGION, TIME_RANGE, CROP_PROFILE)
    assert float(result.score.mean()) < 0.8


def test_scorer_zero_probability_plugin_leaves_score_unchanged(make_plugin):
    registry = PluginRegistry()
    registry.register(make_plugin("p1", factor=0.0, probability=0.0, threat_tier="stress"))
    result = Scorer(registry).run(_da(0.8), REGION, TIME_RANGE, CROP_PROFILE)
    assert float(result.score.mean()) == 0.8


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
                threat_tier="stress",
            )

        def validate_config(self, crop_profile: dict) -> bool:
            return False

        def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData:
            raise AssertionError("fetch_data must not be called")

        def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier:
            raise AssertionError("score must not be called")

        def describe(self, score: SuitabilityModifier) -> str:
            return ""

    registry = PluginRegistry()
    registry.register(_RejectingPlugin())
    result = Scorer(registry).run(_da(0.7), REGION, TIME_RANGE, CROP_PROFILE)
    assert float(result.score.mean()) == 0.7
    assert float(result.confidence.mean()) == 1.0


def test_scorer_with_two_plugins_aggregates_confidence(make_plugin):
    registry = PluginRegistry()
    registry.register(make_plugin("p1", factor=1.0, confidence=0.4))
    registry.register(make_plugin("p2", factor=1.0, confidence=0.8))
    result = Scorer(registry).run(_da(0.5), REGION, TIME_RANGE, CROP_PROFILE)
    assert float(result.confidence.mean()) == pytest.approx(0.6)


def test_existential_tier_plugin_applies_liebig_ceiling_not_multiplicative(make_plugin):
    # existential factor=0.3, envelope=0.8:
    #   correct (existential): min(0.8, 0.3) = 0.3
    #   wrong   (stress bug):  0.8 × 0.3    = 0.24
    registry = PluginRegistry()
    registry.register(make_plugin("p1", factor=0.3, probability=1.0, threat_tier="existential"))
    result = Scorer(registry).run(_da(0.8), REGION, TIME_RANGE, CROP_PROFILE)
    assert float(result.score.mean()) == pytest.approx(0.3)
