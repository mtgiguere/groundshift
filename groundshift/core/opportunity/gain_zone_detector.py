from __future__ import annotations

from groundshift.models.describe_result import DescribeResult
from groundshift.models.opportunity_zone import OpportunityZone, OpportunityZoneResult
from groundshift.models.prescribe_result import PrescribeResult


class GainZoneDetector:
    def __init__(self, current_threshold: float = 0.3, delta_threshold: float = 0.1):
        self._current_threshold = current_threshold
        self._delta_threshold = delta_threshold

    def detect(
        self, describe_result: DescribeResult, prescribe_result: PrescribeResult
    ) -> OpportunityZoneResult:
        current = describe_result.suitability.score
        zones = [
            OpportunityZone(
                scenario=proj.scenario,
                horizon_year=proj.horizon_year,
                mask=(current < self._current_threshold) & (proj.delta > self._delta_threshold),
                confidence="low",
            )
            for proj in prescribe_result.change_projections
        ]
        return OpportunityZoneResult(zones=zones)
