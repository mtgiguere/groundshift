from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TimeRange:
    start: datetime
    end: datetime
    scenario: str | None = None
    horizon_year: int | None = None

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"end ({self.end}) must not be before start ({self.start})")
