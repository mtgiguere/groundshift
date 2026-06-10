import numpy as np
import pytest
import xarray as xr
from hypothesis import given
from hypothesis import strategies as st

from groundshift.core.aggregator import aggregate_modifiers
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.suitability_result import SuitabilityResult

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)


def _da(value: float) -> xr.DataArray:
    return xr.DataArray(np.array([[value]]))


def _envelope(value: float) -> xr.DataArray:
    return _da(value)


def _modifier(
    factor: float,
    probability: float = 1.0,
    confidence: float = 1.0,
    threat_tier: str = "stress",
    custom_weight: float = 1.0,
) -> SuitabilityModifier:
    return SuitabilityModifier(
        plugin_id="test",
        region=REGION,
        factor_value=_da(factor),
        probability=_da(probability),
        confidence=_da(confidence),
        metadata={"threat_tier": threat_tier, "custom_weight": custom_weight},
    )


# ── Return type ───────────────────────────────────────────────────────────────


def test_aggregate_modifiers_returns_suitability_result():
    result = aggregate_modifiers(envelope=_envelope(0.8), modifiers=[])
    assert isinstance(result, SuitabilityResult)


# ── No plugins ────────────────────────────────────────────────────────────────


def test_no_modifiers_returns_envelope_score_unchanged():
    result = aggregate_modifiers(envelope=_envelope(0.75), modifiers=[])
    assert float(result.score.mean()) == pytest.approx(0.75)


def test_no_modifiers_returns_full_confidence():
    result = aggregate_modifiers(envelope=_envelope(0.75), modifiers=[])
    assert float(result.confidence.mean()) == pytest.approx(1.0)


# ── Envelope as hard gate ─────────────────────────────────────────────────────


def test_zero_envelope_produces_zero_score_regardless_of_plugins():
    result = aggregate_modifiers(
        envelope=_envelope(0.0),
        modifiers=[_modifier(factor=1.0, probability=1.0)],
    )
    assert float(result.score.mean()) == pytest.approx(0.0)


def test_final_score_never_exceeds_envelope():
    result = aggregate_modifiers(
        envelope=_envelope(0.6),
        modifiers=[_modifier(factor=1.0, probability=0.0)],
    )
    assert float(result.score.mean()) <= 0.6 + 1e-9


# ── Stress tier ───────────────────────────────────────────────────────────────


def test_stress_modifier_reduces_score_multiplicatively():
    # envelope=0.8, factor=0.5, prob=1.0 → eff=0.5 → score=0.8*0.5=0.4
    result = aggregate_modifiers(
        envelope=_envelope(0.8),
        modifiers=[_modifier(factor=0.5, probability=1.0, threat_tier="stress")],
    )
    assert float(result.score.mean()) == pytest.approx(0.4)


def test_two_stress_modifiers_compound():
    # envelope=1.0, eff_1=0.8, eff_2=0.5 → score=1.0*0.8*0.5=0.4
    result = aggregate_modifiers(
        envelope=_envelope(1.0),
        modifiers=[
            _modifier(factor=0.8, probability=1.0, threat_tier="stress"),
            _modifier(factor=0.5, probability=1.0, threat_tier="stress"),
        ],
    )
    assert float(result.score.mean()) == pytest.approx(0.4)


# ── Existential tier ──────────────────────────────────────────────────────────


def test_existential_modifier_applies_liebig_min_with_envelope():
    # envelope=0.9, existential factor=0.3 → ceiling=min(0.9,0.3)=0.3
    result = aggregate_modifiers(
        envelope=_envelope(0.9),
        modifiers=[_modifier(factor=0.3, probability=1.0, threat_tier="existential")],
    )
    assert float(result.score.mean()) == pytest.approx(0.3)


def test_existential_modifier_higher_than_envelope_does_not_raise_ceiling():
    # existential factor=1.0 (no threat) → ceiling stays at envelope=0.6
    result = aggregate_modifiers(
        envelope=_envelope(0.6),
        modifiers=[_modifier(factor=1.0, probability=1.0, threat_tier="existential")],
    )
    assert float(result.score.mean()) == pytest.approx(0.6)


# ── Custom tier ───────────────────────────────────────────────────────────────


def test_custom_modifier_weight_1_equals_stress_behaviour():
    result_stress = aggregate_modifiers(
        envelope=_envelope(1.0),
        modifiers=[_modifier(factor=0.7, probability=1.0, threat_tier="stress")],
    )
    result_custom = aggregate_modifiers(
        envelope=_envelope(1.0),
        modifiers=[_modifier(factor=0.7, probability=1.0, threat_tier="custom", custom_weight=1.0)],
    )
    assert float(result_stress.score.mean()) == pytest.approx(float(result_custom.score.mean()))


def test_custom_modifier_weight_2_hits_harder_than_weight_1():
    result_w1 = aggregate_modifiers(
        envelope=_envelope(1.0),
        modifiers=[_modifier(factor=0.7, probability=1.0, threat_tier="custom", custom_weight=1.0)],
    )
    result_w2 = aggregate_modifiers(
        envelope=_envelope(1.0),
        modifiers=[_modifier(factor=0.7, probability=1.0, threat_tier="custom", custom_weight=2.0)],
    )
    assert float(result_w2.score.mean()) < float(result_w1.score.mean())


# ── Probability / expected value ──────────────────────────────────────────────


def test_zero_probability_stressor_leaves_score_at_envelope():
    # prob=0.0 → eff = 1 - 0*(1-factor) = 1.0 → no reduction
    result = aggregate_modifiers(
        envelope=_envelope(0.8),
        modifiers=[_modifier(factor=0.0, probability=0.0, threat_tier="stress")],
    )
    assert float(result.score.mean()) == pytest.approx(0.8)


def test_partial_probability_produces_partial_reduction():
    # factor=0.0 (catastrophic if occurs), prob=0.5 → eff=1-0.5*1=0.5
    # score = 0.8 * 0.5 = 0.4
    result = aggregate_modifiers(
        envelope=_envelope(0.8),
        modifiers=[_modifier(factor=0.0, probability=0.5, threat_tier="stress")],
    )
    assert float(result.score.mean()) == pytest.approx(0.4)


# ── Property tests ────────────────────────────────────────────────────────────


@given(
    envelope_val=st.floats(0.0, 1.0, allow_nan=False),
    factors=st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=0, max_size=5),
    probs=st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=0, max_size=5),
)
def test_output_score_always_in_0_1(envelope_val, factors, probs):
    modifiers = [_modifier(f, p) for f, p in zip(factors, probs)]
    result = aggregate_modifiers(envelope=_envelope(envelope_val), modifiers=modifiers)
    score = float(result.score.mean())
    assert 0.0 <= score <= 1.0


@given(
    envelope_val=st.floats(0.0, 1.0, allow_nan=False),
    factors=st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=0, max_size=5),
    probs=st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=0, max_size=5),
)
def test_output_score_never_exceeds_envelope(envelope_val, factors, probs):
    modifiers = [_modifier(f, p) for f, p in zip(factors, probs)]
    result = aggregate_modifiers(envelope=_envelope(envelope_val), modifiers=modifiers)
    assert float(result.score.mean()) <= envelope_val + 1e-9
