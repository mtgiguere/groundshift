from __future__ import annotations

from groundshift.models.describe_result import DescribeResult
from groundshift.models.opportunity_zone import OpportunityZone, OpportunityZoneResult
from groundshift.models.prescribe_result import PrescribeResult


def _gain_confidence(describe_result: DescribeResult) -> str:
    signals = 1  # CMIP6 always present
    if describe_result.trend is not None:
        if float(describe_result.trend.slope.median()) > 0:
            signals += 1
    if describe_result.divergence is not None:
        if float(describe_result.divergence.surface.median()) < 0:
            signals += 1
    return {1: "low", 2: "medium", 3: "high"}[signals]


class GainZoneDetector:
    def __init__(self, current_threshold: float = 0.3, delta_threshold: float = 0.1):
        self._current_threshold = current_threshold
        self._delta_threshold = delta_threshold

    def detect(
        self, describe_result: DescribeResult, prescribe_result: PrescribeResult
    ) -> OpportunityZoneResult:
        current = describe_result.suitability.score
        confidence = _gain_confidence(describe_result)
        zones = [
            OpportunityZone(
                scenario=proj.scenario,
                horizon_year=proj.horizon_year,
                mask=(current < self._current_threshold) & (proj.delta > self._delta_threshold),
                confidence=confidence,
            )
            for proj in prescribe_result.change_projections
        ]
        return OpportunityZoneResult(zones=zones)
