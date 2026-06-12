"""Verify that real crop profiles activate the expected plugins."""

from pathlib import Path

import pytest
import yaml

from groundshift.plugins.drought_stress import DroughtStressPlugin
from groundshift.plugins.frost_risk import FrostRiskPlugin
from groundshift.plugins.heat_stress import HeatStressPlugin

_PROFILES_DIR = Path(__file__).parents[3] / "crop_profiles"
_PROFILE_IDS = [p.stem for p in sorted(_PROFILES_DIR.glob("*.yaml"))]


@pytest.fixture(params=_PROFILE_IDS)
def profile(request):
    path = _PROFILES_DIR / f"{request.param}.yaml"
    return yaml.safe_load(path.read_text())


class TestFrostRiskCompatibility:
    def test_fires_for_all_profiles(self, profile, tmp_path):
        plugin = FrostRiskPlugin(tmp_path)
        assert plugin.validate_config(profile) is True


class TestDroughtStressCompatibility:
    def test_fires_for_all_profiles(self, profile, tmp_path):
        plugin = DroughtStressPlugin(tmp_path)
        assert plugin.validate_config(profile) is True


class TestHeatStressCompatibility:
    def test_fires_for_all_profiles(self, profile, tmp_path):
        plugin = HeatStressPlugin(tmp_path)
        assert plugin.validate_config(profile) is True
