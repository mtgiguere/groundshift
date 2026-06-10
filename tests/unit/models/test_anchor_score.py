from groundshift.models.anchor_score import AnchorScore
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.calibration_anchor import CalibrationAnchor

_ANCHOR = CalibrationAnchor(
    anchor_id="yirgacheffe",
    name="Yirgacheffe / Sidama",
    role="origin_center",
    region=BoundingBox(min_lon=37.0, min_lat=5.0, max_lon=40.0, max_lat=9.0),
)


def test_anchor_score_stores_fields():
    result = AnchorScore(
        anchor=_ANCHOR,
        score=0.75,
        confidence=0.9,
        expected_min=0.70,
        alert_triggered=False,
    )
    assert result.anchor is _ANCHOR
    assert result.score == 0.75
    assert result.confidence == 0.9
    assert result.expected_min == 0.70
    assert result.alert_triggered is False


def test_anchor_score_allows_none_expected_min():
    stress_anchor = CalibrationAnchor(
        anchor_id="ca_stress",
        name="Central America Stress",
        role="stress_reference",
        region=BoundingBox(min_lon=-90.0, min_lat=13.0, max_lon=-87.0, max_lat=15.0),
    )
    result = AnchorScore(
        anchor=stress_anchor,
        score=0.4,
        confidence=0.8,
        expected_min=None,
        alert_triggered=False,
    )
    assert result.expected_min is None
