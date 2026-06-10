import numpy as np
import pytest
import xarray as xr

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_modifier import SuitabilityModifier

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)


def _da(value: float) -> xr.DataArray:
    return xr.DataArray(np.full((2, 2), value))


def _make_modifier(**kwargs) -> SuitabilityModifier:
    defaults = dict(
        plugin_id="groundwater",
        region=REGION,
        factor_value=_da(0.7),
        probability=_da(1.0),
        confidence=_da(0.8),
        metadata={"source": "GRACE"},
    )
    return SuitabilityModifier(**{**defaults, **kwargs})


def test_suitability_modifier_stores_fields():
    m = _make_modifier()
    assert m.plugin_id == "groundwater"
    assert m.region == REGION
    assert float(m.factor_value.mean()) == pytest.approx(0.7)
    assert float(m.probability.mean()) == pytest.approx(1.0)
    assert float(m.confidence.mean()) == pytest.approx(0.8)


def test_suitability_modifier_raises_if_factor_value_above_1():
    with pytest.raises(ValueError, match="factor_value"):
        _make_modifier(factor_value=_da(1.01))


def test_suitability_modifier_raises_if_factor_value_below_0():
    with pytest.raises(ValueError, match="factor_value"):
        _make_modifier(factor_value=_da(-0.01))


def test_suitability_modifier_raises_if_probability_above_1():
    with pytest.raises(ValueError, match="probability"):
        _make_modifier(probability=_da(1.01))


def test_suitability_modifier_raises_if_probability_below_0():
    with pytest.raises(ValueError, match="probability"):
        _make_modifier(probability=_da(-0.01))


def test_suitability_modifier_raises_if_confidence_above_1():
    with pytest.raises(ValueError, match="confidence"):
        _make_modifier(confidence=_da(1.01))


def test_suitability_modifier_raises_if_confidence_below_0():
    with pytest.raises(ValueError, match="confidence"):
        _make_modifier(confidence=_da(-0.01))


@pytest.mark.parametrize("factor_value", [0.0, 0.5, 1.0])
def test_suitability_modifier_accepts_boundary_factor_values(factor_value):
    m = _make_modifier(factor_value=_da(factor_value))
    assert float(m.factor_value.mean()) == pytest.approx(factor_value)
