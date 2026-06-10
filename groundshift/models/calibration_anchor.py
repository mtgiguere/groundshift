from dataclasses import dataclass, field

from groundshift.models.bounding_box import BoundingBox

_VALID_ROLES = frozenset({"origin_center", "production_reference", "stress_reference"})


@dataclass
class CalibrationAnchor:
    anchor_id: str
    name: str
    role: str
    region: BoundingBox
    notes: str = field(default="")

    def __post_init__(self) -> None:
        if self.role not in _VALID_ROLES:
            raise ValueError(
                f"role must be one of {sorted(_VALID_ROLES)}, got '{self.role}'"
            )
