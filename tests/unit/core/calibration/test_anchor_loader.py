import pytest

from groundshift.core.calibration.anchor_loader import load_anchors_from_profile
from groundshift.models.calibration_anchor import CalibrationAnchor


def test_load_anchors_returns_empty_list_when_key_absent():
    profile = {"crop_id": "coffee", "climate_envelope": {}}
    result = load_anchors_from_profile(profile)
    assert result == []


def test_load_anchors_returns_empty_list_when_anchors_is_empty():
    profile = {"calibration_anchors": []}
    result = load_anchors_from_profile(profile)
    assert result == []


def test_load_anchors_parses_single_anchor():
    profile = {
        "calibration_anchors": [
            {
                "id": "yirgacheffe",
                "name": "Yirgacheffe / Sidama",
                "role": "origin_center",
                "bbox": [37.0, 5.0, 40.0, 9.0],
            }
        ]
    }
    result = load_anchors_from_profile(profile)
    assert len(result) == 1
    anchor = result[0]
    assert isinstance(anchor, CalibrationAnchor)
    assert anchor.anchor_id == "yirgacheffe"
    assert anchor.name == "Yirgacheffe / Sidama"
    assert anchor.role == "origin_center"
    assert anchor.region.min_lon == 37.0
    assert anchor.region.min_lat == 5.0
    assert anchor.region.max_lon == 40.0
    assert anchor.region.max_lat == 9.0


def test_load_anchors_parses_notes_when_present():
    profile = {
        "calibration_anchors": [
            {
                "id": "x",
                "name": "X",
                "role": "production_reference",
                "bbox": [-76.5, 1.5, -74.5, 3.0],
                "notes": "Colombian premium zone",
            }
        ]
    }
    result = load_anchors_from_profile(profile)
    assert result[0].notes == "Colombian premium zone"


def test_load_anchors_defaults_notes_to_empty_string_when_absent():
    profile = {
        "calibration_anchors": [
            {
                "id": "x",
                "name": "X",
                "role": "stress_reference",
                "bbox": [-90.0, 13.0, -87.0, 15.0],
            }
        ]
    }
    result = load_anchors_from_profile(profile)
    assert result[0].notes == ""


def test_load_anchors_raises_on_invalid_role():
    profile = {
        "calibration_anchors": [
            {
                "id": "x",
                "name": "X",
                "role": "nonsense",
                "bbox": [0.0, 0.0, 1.0, 1.0],
            }
        ]
    }
    with pytest.raises(ValueError, match="role"):
        load_anchors_from_profile(profile)
