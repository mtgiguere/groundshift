from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.suitability_result import SuitabilityResult


def aggregate_modifiers(
    base_score: float,
    modifiers: list[SuitabilityModifier],
    max_single_plugin_impact: float = 0.25,
) -> SuitabilityResult:
    if not modifiers:
        return SuitabilityResult(score=base_score, confidence=1.0)

    adjustment = 0.0
    total_weight = 0.0

    for m in modifiers:
        # Each plugin's raw impact is its modifier_value weighted by confidence.
        # Cap it so no single plugin can swing the score by more than
        # max_single_plugin_impact * base_score.
        raw_impact = m.modifier_value * m.confidence
        base_magnitude = abs(base_score) if base_score != 0 else 1.0
        cap = max_single_plugin_impact * base_magnitude
        capped_impact = max(-cap, min(cap, raw_impact))
        adjustment += capped_impact * m.confidence
        total_weight += m.confidence

    weighted_adjustment = adjustment / total_weight if total_weight > 0 else 0.0
    new_score = max(0.0, min(1.0, base_score + weighted_adjustment))
    aggregate_confidence = total_weight / len(modifiers)

    return SuitabilityResult(score=new_score, confidence=aggregate_confidence)
