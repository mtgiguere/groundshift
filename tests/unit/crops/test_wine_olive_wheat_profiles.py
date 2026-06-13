"""Structural validation for wine_grape, olive, and wheat crop profiles."""

from pathlib import Path

import pytest
import yaml

_PROFILES_DIR = Path(__file__).parents[3] / "crop_profiles"
_NEW_PROFILES = ["wine_grape", "olive", "wheat"]
_THRESHOLDS = ["mean_annual_temp_c", "annual_precipitation_mm", "altitude_m"]
_PLUGIN_KEYS = [
    "frost_threshold_c",
    "precip_viable_min_mm",
    "precip_optimal_min_mm",
    "heat_max_threshold_c",
]
_ANCHOR_ROLES = {"origin_center", "production_reference", "stress_reference"}


def _load(crop_id: str) -> dict:
    return yaml.safe_load((_PROFILES_DIR / f"{crop_id}.yaml").read_text())


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_profile_file_exists(crop_id):
    assert (_PROFILES_DIR / f"{crop_id}.yaml").exists()


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_has_required_top_level_keys(crop_id):
    profile = _load(crop_id)
    for key in ("crop_id", "name", "scientific_name", "climate_envelope", "calibration_anchors"):
        assert key in profile, f"'{key}' missing from {crop_id}.yaml"


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_crop_id_matches_filename(crop_id):
    assert _load(crop_id)["crop_id"] == crop_id


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_has_all_three_climate_threshold_variables(crop_id):
    thresholds = _load(crop_id)["climate_envelope"]["thresholds"]
    for var in _THRESHOLDS:
        assert var in thresholds, f"'{var}' missing from {crop_id}.yaml thresholds"


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
@pytest.mark.parametrize("variable", _THRESHOLDS)
def test_threshold_trapezoid_ordering(crop_id, variable):
    thresholds = _load(crop_id)["climate_envelope"]["thresholds"]
    t = thresholds[variable]
    assert t["viable_min"] <= t["optimal_min"], f"{crop_id} {variable}: viable_min > optimal_min"
    assert t["optimal_min"] <= t["optimal_max"], f"{crop_id} {variable}: optimal_min > optimal_max"
    assert t["optimal_max"] <= t["viable_max"], f"{crop_id} {variable}: optimal_max > viable_max"


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_has_all_plugin_keys(crop_id):
    profile = _load(crop_id)
    for key in _PLUGIN_KEYS:
        assert key in profile, f"'{key}' missing from {crop_id}.yaml"


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_plugin_keys_are_numeric(crop_id):
    profile = _load(crop_id)
    for key in _PLUGIN_KEYS:
        assert isinstance(profile[key], (int, float)), f"{crop_id}.yaml: '{key}' is not numeric"


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_calibration_anchors_cover_all_three_roles(crop_id):
    anchors = _load(crop_id)["calibration_anchors"]
    roles = {a["role"] for a in anchors}
    assert roles == _ANCHOR_ROLES, f"{crop_id}.yaml anchors missing roles: {_ANCHOR_ROLES - roles}"


@pytest.mark.parametrize("crop_id", _NEW_PROFILES)
def test_calibration_anchor_bboxes_are_valid(crop_id):
    for anchor in _load(crop_id)["calibration_anchors"]:
        bbox = anchor["bbox"]
        assert len(bbox) == 4, f"{crop_id} anchor {anchor['id']}: bbox must have 4 values"
        min_lon, min_lat, max_lon, max_lat = bbox
        assert -180 <= min_lon < max_lon <= 180, f"{crop_id} anchor {anchor['id']}: bad lon range"
        assert -90 <= min_lat < max_lat <= 90, f"{crop_id} anchor {anchor['id']}: bad lat range"
