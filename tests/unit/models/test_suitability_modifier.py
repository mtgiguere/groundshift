import pytest

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_modifier import SuitabilityModifier

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)


def test_suitability_modifier_stores_fields():
    modifier = SuitabilityModifier(
        plugin_id="groundwater",
        region=REGION,
        modifier_value=-0.3,
        confidence=0.7,
        geometry=None,
        metadata={"source": "GRACE"},
    )
    assert modifier.plugin_id == "groundwater"
    assert modifier.modifier_value == -0.3
    assert modifier.confidence == 0.7


def test_suitability_modifier_raises_if_modifier_value_above_1():
    with pytest.raises(ValueError, match="modifier_value"):
        SuitabilityModifier(
            plugin_id="x",
            region=REGION,
            modifier_value=1.01,
            confidence=0.5,
            geometry=None,
            metadata={},
        )


def test_suitability_modifier_raises_if_modifier_value_below_minus_1():
    with pytest.raises(ValueError, match="modifier_value"):
        SuitabilityModifier(
            plugin_id="x",
            region=REGION,
            modifier_value=-1.01,
            confidence=0.5,
            geometry=None,
            metadata={},
        )


def test_suitability_modifier_raises_if_confidence_above_1():
    with pytest.raises(ValueError, match="confidence"):
        SuitabilityModifier(
            plugin_id="x",
            region=REGION,
            modifier_value=0.0,
            confidence=1.01,
            geometry=None,
            metadata={},
        )


def test_suitability_modifier_raises_if_confidence_below_0():
    with pytest.raises(ValueError, match="confidence"):
        SuitabilityModifier(
            plugin_id="x",
            region=REGION,
            modifier_value=0.0,
            confidence=-0.01,
            geometry=None,
            metadata={},
        )


@pytest.mark.parametrize(
    "modifier_value,confidence",
    [
        (1.0, 1.0),
        (-1.0, 0.0),
        (0.0, 0.5),
    ],
)
def test_suitability_modifier_accepts_exact_boundary_values(modifier_value, confidence):
    modifier = SuitabilityModifier(
        plugin_id="x",
        region=REGION,
        modifier_value=modifier_value,
        confidence=confidence,
        geometry=None,
        metadata={},
    )
    assert modifier.modifier_value == modifier_value
    assert modifier.confidence == confidence
