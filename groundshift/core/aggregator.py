import xarray as xr

from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.suitability_result import SuitabilityResult


def aggregate_modifiers(
    envelope: xr.DataArray,
    modifiers: list[SuitabilityModifier],
) -> SuitabilityResult:
    if not modifiers:
        return SuitabilityResult(score=envelope, confidence=xr.ones_like(envelope))

    ceiling = envelope.copy()
    stress_factor = xr.ones_like(envelope)
    custom_factor = xr.ones_like(envelope)
    confidence_sum = xr.zeros_like(envelope)

    for m in modifiers:
        tier = m.metadata.get("threat_tier", "stress")
        weight = float(m.metadata.get("custom_weight", 1.0))
        effective = 1.0 - m.probability * (1.0 - m.factor_value)

        if tier == "existential":
            ceiling = xr.where(effective < ceiling, effective, ceiling)
        elif tier == "custom":
            custom_factor = custom_factor * (effective**weight)
        else:
            stress_factor = stress_factor * effective

        confidence_sum = confidence_sum + m.confidence

    score = (ceiling * stress_factor * custom_factor).clip(0.0, 1.0)
    aggregate_confidence = (confidence_sum / len(modifiers)).clip(0.0, 1.0)

    return SuitabilityResult(score=score, confidence=aggregate_confidence)
