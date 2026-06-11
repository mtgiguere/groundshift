from __future__ import annotations

from groundshift.models.describe_result import DescribeResult
from groundshift.models.predict_result import PredictResult
from groundshift.models.prescribe_result import ChangeProjection, PrescribeResult


class PrescribePhaseRunner:
    def run(
        self, describe_result: DescribeResult, predict_result: PredictResult
    ) -> PrescribeResult:
        current = describe_result.suitability.score
        change_projections = [
            ChangeProjection(
                scenario=proj.scenario,
                horizon_year=proj.horizon_year,
                delta=proj.suitability.score - current,
            )
            for proj in predict_result.projections
        ]
        return PrescribeResult(change_projections=change_projections)
