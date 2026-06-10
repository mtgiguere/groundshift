from groundshift.plugins.base import GroundshiftPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, GroundshiftPlugin] = {}

    def register(self, plugin: GroundshiftPlugin) -> None:
        plugin_id = plugin.metadata.plugin_id
        if plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' is already registered")
        self._plugins[plugin_id] = plugin

    def get(self, plugin_id: str) -> GroundshiftPlugin:
        return self._plugins[plugin_id]

    def list_plugins(self) -> list[GroundshiftPlugin]:
        return list(self._plugins.values())
