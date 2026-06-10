from groundshift.core.aggregator import aggregate_modifiers
from groundshift.models.bounding_box import BoundingBox
from groundshift.models.time_range import TimeRange
from groundshift.plugins.registry import PluginRegistry


class Scorer:
    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def run(
        self,
        base_score: float,
        region: BoundingBox,
        time_range: TimeRange,
        crop_profile: dict,
    ) -> tuple[float, float]:
        modifiers = []
        for plugin in self._registry.list_plugins():
            if plugin.validate_config(crop_profile):
                layer = plugin.fetch_data(region, time_range)
                modifiers.append(plugin.score(layer, crop_profile))
        return aggregate_modifiers(base_score, modifiers)
