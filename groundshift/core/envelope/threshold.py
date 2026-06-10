from dataclasses import dataclass


@dataclass
class ClimateThreshold:
    viable_min: float
    optimal_min: float
    optimal_max: float
    viable_max: float

    def score(self, value: float) -> float:
        if value < self.viable_min or value > self.viable_max:
            return 0.0
        if self.optimal_min <= value <= self.optimal_max:
            return 1.0
        if value < self.optimal_min:
            return (value - self.viable_min) / (self.optimal_min - self.viable_min)
        return (self.viable_max - value) / (self.viable_max - self.optimal_max)

    def __post_init__(self) -> None:
        if self.viable_min > self.optimal_min:
            raise ValueError(
                f"viable_min ({self.viable_min}) must not exceed optimal_min ({self.optimal_min})"
            )
        if self.optimal_min > self.optimal_max:
            raise ValueError(
                f"optimal_min ({self.optimal_min}) must not exceed optimal_max ({self.optimal_max})"
            )
        if self.optimal_max > self.viable_max:
            raise ValueError(
                f"optimal_max ({self.optimal_max}) must not exceed viable_max ({self.viable_max})"
            )
