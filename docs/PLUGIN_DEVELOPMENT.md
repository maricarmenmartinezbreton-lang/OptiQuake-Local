# OptiQuake Local Plugin Development

Plugin API v1 lets community extensions consume local vibration events without modifying the detector core.

## Supported extension paths
- Local `.py` plugins loaded with `--plugin-dir`.
- Installed Python packages exposed through the `optiquake.plugins` entry-point group.
- Bridges to alerting, databases, dashboards, AI agents, MCP, n8n, Home Assistant, or research pipelines.

## Contract
A plugin factory named `create_plugin()` must return an object with:
- `name`
- `version`
- `api_version = "1"`
- `on_start(context)`
- `on_event(event)`
- `on_stop()`

Runtime exceptions are isolated and reported as `plugin_error` JSON events so one extension cannot stop the detector.

## Scientific boundary
Plugins receive `vibration` events. They must not relabel them as confirmed earthquakes or guaranteed early warnings without independent validation.

## Licensing
Contributions merged into the official OptiQuake Local repository are distributed under AGPL-3.0-only. External plugin authors are responsible for ensuring their licensing is compatible with how they combine and distribute software.
