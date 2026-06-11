from __future__ import annotations

from dataclasses import dataclass, field

from groundshift.models.divergence_result import DivergenceResult
from groundshift.models.suitability_result import SuitabilityResult
from groundshift.models.trend_result import TrendResult


@dataclass
class DescribeResult:
    suitability: SuitabilityResult
    divergence: DivergenceResult | None = field(default=None)
    trend: TrendResult | None = field(default=None)
