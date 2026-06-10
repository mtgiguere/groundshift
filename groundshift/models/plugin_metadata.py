from dataclasses import dataclass
from typing import Literal

_VALID_TIERS = {"existential", "stress", "custom"}


@dataclass
class PluginMetadata:
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    compatible_crops: list[str]
    data_sources: list[str]
    requires_network: bool
    phase_applicability: list[str]
    threat_tier: Literal["existential", "stress", "custom"] = "stress"
    custom_weight: float = 1.0

    def __post_init__(self) -> None:
        if self.threat_tier not in _VALID_TIERS:
            raise ValueError(
                f"threat_tier must be one of {sorted(_VALID_TIERS)}, got '{self.threat_tier}'"
            )
