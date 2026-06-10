import pytest

from groundshift.plugins.registry import PluginRegistry


def test_new_registry_is_empty():
    registry = PluginRegistry()
    assert registry.list_plugins() == []


def test_registered_plugin_is_retrievable_by_id(make_plugin):
    registry = PluginRegistry()
    plugin = make_plugin("crop_drought")
    registry.register(plugin)
    assert registry.get("crop_drought") is plugin


def test_list_plugins_returns_all_registered(make_plugin):
    registry = PluginRegistry()
    a, b = make_plugin("alpha"), make_plugin("beta")
    registry.register(a)
    registry.register(b)
    assert set(registry.list_plugins()) == {a, b}


def test_registering_duplicate_id_raises(make_plugin):
    registry = PluginRegistry()
    registry.register(make_plugin("dup"))
    with pytest.raises(ValueError, match="dup"):
        registry.register(make_plugin("dup"))


def test_get_unknown_id_raises():
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.get("nonexistent")
