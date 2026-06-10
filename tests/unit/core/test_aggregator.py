from hypothesis import given
from hypothesis import strategies as st

from groundshift.core.aggregator import aggregate_modifiers
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.suitability_result import SuitabilityResult

REGION = BoundingBox(min_lon=35.0, min_lat=3.0, max_lon=42.0, max_lat=15.0)


def _modifier(value: float, confidence: float) -> SuitabilityModifier:
    return SuitabilityModifier(
        plugin_id="test_plugin",
        region=REGION,
        modifier_value=value,
        confidence=confidence,
        geometry=None,
        metadata={},
    )


def test_aggregate_modifiers_returns_suitability_result():
    result = aggregate_modifiers(base_score=0.5, modifiers=[])
    assert isinstance(result, SuitabilityResult)
    assert result.score == 0.5
    assert result.confidence == 1.0


def test_empty_modifiers_returns_base_score_unchanged():
    score, confidence = aggregate_modifiers(base_score=0.75, modifiers=[])
    assert score == 0.75


def test_empty_modifiers_returns_confidence_of_1():
    score, confidence = aggregate_modifiers(base_score=0.75, modifiers=[])
    assert confidence == 1.0


def test_single_positive_modifier_increases_score():
    # modifier_value=0.5, confidence=1.0, cap=0.25
    # impact = min(0.5 * 1.0, 0.25) * base = min(0.5, 0.25) * 0.6 = 0.15
    # expected score = 0.6 + 0.15 = 0.75
    score, _ = aggregate_modifiers(
        base_score=0.60,
        modifiers=[_modifier(value=0.5, confidence=1.0)],
        max_single_plugin_impact=0.25,
    )
    assert abs(score - 0.75) < 1e-9


def test_modifier_impact_is_capped_at_max_single_plugin_impact():
    # A modifier_value of 1.0 at full confidence would move a 0.5 base by 0.5,
    # but the cap is 0.25 — so the maximum move is 0.25 * 0.5 = 0.125.
    # With confidence=1.0 weighted adjustment = 0.125 * 1.0 / 1.0 = 0.125
    # expected score = 0.5 + 0.125 = 0.625
    score, _ = aggregate_modifiers(
        base_score=0.50,
        modifiers=[_modifier(value=1.0, confidence=1.0)],
        max_single_plugin_impact=0.25,
    )
    assert abs(score - 0.625) < 1e-9


def test_negative_modifier_decreases_score():
    # modifier_value=-0.5, confidence=1.0, cap=0.25
    # raw_impact = -0.5, capped to -0.25*0.6 = -0.15
    # adjustment = -0.15 * 1.0 / 1.0 = -0.15
    # expected score = 0.6 - 0.15 = 0.45
    score, _ = aggregate_modifiers(
        base_score=0.60,
        modifiers=[_modifier(value=-0.5, confidence=1.0)],
        max_single_plugin_impact=0.25,
    )
    assert abs(score - 0.45) < 1e-9


def test_output_score_is_clamped_to_0_1_on_overflow():
    # Even if modifiers would push the score above 1.0 or below 0.0,
    # the result must stay within [0.0, 1.0].
    high_score, _ = aggregate_modifiers(
        base_score=0.95,
        modifiers=[_modifier(value=1.0, confidence=1.0)],
        max_single_plugin_impact=0.25,
    )
    assert high_score <= 1.0

    low_score, _ = aggregate_modifiers(
        base_score=0.05,
        modifiers=[_modifier(value=-1.0, confidence=1.0)],
        max_single_plugin_impact=0.25,
    )
    assert low_score >= 0.0


def test_base_score_zero_uses_unit_magnitude_for_cap():
    # When base_score=0 the cap would be 0 without the explicit 1.0 fallback,
    # making every modifier useless. Verify a modifier still moves the score.
    result = aggregate_modifiers(
        base_score=0.0,
        modifiers=[_modifier(value=0.5, confidence=1.0)],
        max_single_plugin_impact=0.25,
    )
    assert result.score > 0.0


def test_all_zero_confidence_modifiers_leave_score_unchanged():
    result = aggregate_modifiers(
        base_score=0.6,
        modifiers=[
            _modifier(value=0.5, confidence=0.0),
            _modifier(value=-0.5, confidence=0.0),
        ],
    )
    assert result.score == 0.6
    assert result.confidence == 0.0


def test_opposing_equal_modifiers_cancel():
    result = aggregate_modifiers(
        base_score=0.5,
        modifiers=[
            _modifier(value=0.4, confidence=1.0),
            _modifier(value=-0.4, confidence=1.0),
        ],
        max_single_plugin_impact=0.25,
    )
    assert result.score == 0.5


# ── Property tests ────────────────────────────────────────────────────────────


@given(
    base_score=st.floats(0.0, 1.0, allow_nan=False),
    modifier_values=st.lists(st.floats(-1.0, 1.0, allow_nan=False), min_size=0, max_size=10),
    confidence_values=st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=0, max_size=10),
)
def test_output_score_always_in_0_1(base_score, modifier_values, confidence_values):
    modifiers = [_modifier(v, c) for v, c in zip(modifier_values, confidence_values)]
    score, _ = aggregate_modifiers(base_score=base_score, modifiers=modifiers)
    assert 0.0 <= score <= 1.0


@given(
    base_score=st.floats(0.0, 1.0, allow_nan=False),
    modifier_values=st.lists(st.floats(-1.0, 1.0, allow_nan=False), min_size=1, max_size=10),
    confidence_values=st.lists(st.floats(0.0, 1.0, allow_nan=False), min_size=1, max_size=10),
)
def test_output_confidence_always_in_0_1(base_score, modifier_values, confidence_values):
    modifiers = [_modifier(v, c) for v, c in zip(modifier_values, confidence_values)]
    _, confidence = aggregate_modifiers(base_score=base_score, modifiers=modifiers)
    assert 0.0 <= confidence <= 1.0
