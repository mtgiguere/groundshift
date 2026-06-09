from dataclasses import dataclass
from typing import Any

from groundshift.models.bounding_box import BoundingBox


@dataclass
class SuitabilityModifier:
    plugin_id: str
    region: BoundingBox
    modifier_value: float
    confidence: float
    geometry: Any
    metadata: dict

    def __post_init__(self) -> None:
        if not (-1.0 <= self.modifier_value <= 1.0):
            raise ValueError(f"modifier_value must be in [-1.0, 1.0], got {self.modifier_value}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
