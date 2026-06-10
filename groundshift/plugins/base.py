from abc import ABC, abstractmethod

from groundshift.models.bounding_box import BoundingBox
from groundshift.models.layer_data import LayerData
from groundshift.models.plugin_metadata import PluginMetadata
from groundshift.models.suitability_modifier import SuitabilityModifier
from groundshift.models.time_range import TimeRange


class GroundshiftPlugin(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata: ...

    @abstractmethod
    def validate_config(self, crop_profile: dict) -> bool: ...

    @abstractmethod
    def fetch_data(self, region: BoundingBox, time_range: TimeRange) -> LayerData: ...

    @abstractmethod
    def score(self, layer_data: LayerData, crop_profile: dict) -> SuitabilityModifier: ...

    @abstractmethod
    def describe(self, score: SuitabilityModifier) -> str: ...
