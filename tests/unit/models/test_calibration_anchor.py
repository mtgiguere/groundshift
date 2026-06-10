import pytest

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.calibration_anchor import CalibrationAnchor

_REGION = BoundingBox(min_lon=37.0, min_lat=5.0, max_lon=40.0, max_lat=9.0)


def test_calibration_anchor_stores_fields():
    anchor = CalibrationAnchor(
        anchor_id="yirgacheffe",
        name="Yirgacheffe / Sidama",
        role="origin_center",
        region=_REGION,
    )
    assert anchor.anchor_id == "yirgacheffe"
    assert anchor.name == "Yirgacheffe / Sidama"
    assert anchor.role == "origin_center"
    assert anchor.region == _REGION
    assert anchor.notes == ""


def test_calibration_anchor_accepts_notes():
    anchor = CalibrationAnchor(
        anchor_id="a",
        name="A",
        role="production_reference",
        region=_REGION,
        notes="some context",
    )
    assert anchor.notes == "some context"


def test_calibration_anchor_accepts_all_valid_roles():
    for role in ("origin_center", "production_reference", "stress_reference"):
        anchor = CalibrationAnchor(anchor_id="x", name="X", role=role, region=_REGION)
        assert anchor.role == role


def test_calibration_anchor_raises_on_invalid_role():
    with pytest.raises(ValueError, match="role"):
        CalibrationAnchor(anchor_id="x", name="X", role="invented_tier", region=_REGION)
