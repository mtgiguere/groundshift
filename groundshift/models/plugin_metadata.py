from dataclasses import dataclass


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
