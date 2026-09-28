"""Plugin discovery and lifecycle manager for OptiQuake Local."""
import importlib.util
import pathlib
from importlib import metadata
from typing import Any, Iterable

from plugin_api import PLUGIN_API_VERSION, VibrationEvent

ENTRYPOINT_GROUP = "optiquake.plugins"

class PluginLoadError(RuntimeError):
    pass

class PluginManager:
    def __init__(self) -> None:
        self.plugins: list[Any] = []

    def _validate(self, plugin: Any) -> Any:
        required = ("name", "version", "api_version", "on_start", "on_event", "on_stop")
        missing = [x for x in required if not hasattr(plugin, x)]
        if missing:
            raise PluginLoadError(f"Plugin missing: {', '.join(missing)}")
        if str(plugin.api_version) != PLUGIN_API_VERSION:
            raise PluginLoadError(
                f"{plugin.name}: API {plugin.api_version} != {PLUGIN_API_VERSION}"
            )
        return plugin

    def load_file(self, path: pathlib.Path) -> None:
        spec = importlib.util.spec_from_file_location(f"optiquake_plugin_{path.stem}", path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot load {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "create_plugin"):
            raise PluginLoadError(f"{path}: create_plugin() not found")
        self.plugins.append(self._validate(module.create_plugin()))

    def load_directory(self, directory: str | None) -> None:
        if not directory:
            return
        root = pathlib.Path(directory)
        if not root.exists():
            raise PluginLoadError(f"Plugin directory not found: {root}")
        for path in sorted(root.glob("*.py")):
            if path.name.startswith("_"):
                continue
            self.load_file(path)

    def load_entrypoints(self) -> None:
        eps = metadata.entry_points()
        selected: Iterable[Any] = eps.select(group=ENTRYPOINT_GROUP)
        for ep in selected:
            factory = ep.load()
            self.plugins.append(self._validate(factory()))

    def _safe_call(self, method: str, *args: Any) -> list[str]:
        errors: list[str] = []
        items = reversed(self.plugins) if method == "on_stop" else self.plugins
        for plugin in items:
            try:
                getattr(plugin, method)(*args)
            except Exception as exc:
                errors.append(f"{plugin.name}: {exc}")
        return errors

    def start(self, context: dict[str, Any]) -> list[str]:
        return self._safe_call("on_start", context)

    def emit(self, event: VibrationEvent) -> list[str]:
        return self._safe_call("on_event", event)

    def stop(self) -> list[str]:
        return self._safe_call("on_stop")

    def describe(self) -> list[dict[str, str]]:
        return [
            {"name": p.name, "version": p.version, "api_version": p.api_version}
            for p in self.plugins
        ]
