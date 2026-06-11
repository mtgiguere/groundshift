from dataclasses import dataclass

from groundshift.models.suitability_result import SuitabilityResult


@dataclass
class PredictProjection:
    scenario: str
    horizon_year: int
    suitability: SuitabilityResult


@dataclass
class PredictResult:
    projections: list[PredictProjection]
