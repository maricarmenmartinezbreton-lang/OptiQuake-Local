# OptiQuake Local

[![PyPI version](https://img.shields.io/pypi/v/optiquake-local.svg)](https://pypi.org/project/optiquake-local/) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23004638.svg)](https://doi.org/10.5281/zenodo.23004638) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE) [![Public reach metrics](https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local/actions/workflows/public-metrics.yml/badge.svg)](https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local/actions/workflows/public-metrics.yml)

Experimental local optical vibration detection using an ordinary high-frame-rate webcam.`r`n`r`n**Live public reach:** [METRICS.md](METRICS.md) tracks GitHub traffic, PyPI downloads and Zenodo views/downloads every two days.

**Languages:** [English](docs/index.md) · [Español](docs/es.md) · [Português](docs/pt.md) · [Français](docs/fr.md) · [Deutsch](docs/de.md) · [Italiano](docs/it.md) · [简体中文](docs/zh-cn.md) · [日本語](docs/ja.md) · [한국어](docs/ko.md) · [العربية](docs/ar.md) · [हिन्दी](docs/hi.md) · [Русский](docs/ru.md)

**Author:** Lic. Juan Esteban Ramírez<br>
**Origin:** Dominican Republic, 27 September 2026<br>
**Version:** 0.1.2-experimental<br>
**License:** AGPL-3.0

OptiQuake Local turns a compatible webcam into an auxiliary vibration sensor by measuring frame-to-frame scene motion locally. It does **not** require earthquake feeds, catalogs, or cloud detection to trigger a vibration event.

## Initial validation
A controlled Insta360 Link test at 60 fps produced three intentional mechanical events at approximately 0.62 s, 1.42 s and 2.17 s. Their visual peaks were about **19.8x, 34.1x and 23.5x** the quiet-section mean.

This validates **vibration observability**, not earthquake classification, prediction, magnitude estimation, or guaranteed early warning.

## Requirements
- Windows 10/11
- Python 3.10+
- FFmpeg in PATH
- UVC webcam; experimentally tested with Insta360 Link

No OpenCV or NumPy is required.

## Install from PyPI
```powershell
python -m pip install optiquake-local
optiquake-local --self-test
```

Published package: `https://pypi.org/project/optiquake-local/`

Citable archive: project DOI `10.5281/zenodo.23004638`; v0.1.2-experimental DOI `10.5281/zenodo.23005112`.

## Run
```powershell
python src\optiquake.py --self-test
python src\optiquake.py --camera "Insta360 Link" --fps 60
```

## Safety and scientific limits
OptiQuake Local is a research prototype, **not a certified seismometer or life-safety system**. A single sensor at the user's location cannot reliably warn before the first seismic waves reach that same sensor.

Local vibration can come from footsteps, doors, traffic, fans, camera motion, construction, or other non-seismic sources. Do not replace official emergency alerts or certified seismic systems with this software.

The project intentionally reports **vibration events**, not "earthquakes," until independent multi-sensor validation supports classification.

## Privacy
The MVP processes frames locally and does not save video. It emits numeric vibration-event metadata to stdout.

## Roadmap
1. Collect labeled non-seismic disturbances.
2. Compare against a calibrated accelerometer/seismometer.
3. Add phone accelerometer/gyroscope correlation.
4. Add optional low-frequency microphone features.
5. Support multiple physically separated nodes.
6. Publish false-positive/false-negative metrics before any earthquake-classification claim.

## AI skill

The repository also includes `skill/SKILL.md` and `skill/manifest.json` so OptiQuake Local can be consumed as a reusable sensor skill by AI agents and automation projects.

The skill emits structured JSONL events and deliberately reports `vibration`, not `earthquake`, unless a separate corroboration layer confirms the event.

See `docs/AI_SKILL_INTEGRATION.md` for the integration contract.


## Contributing

OptiQuake Local is designed to be improved by the community. See `CONTRIBUTING.md`, `GOVERNANCE.md`, and `ROADMAP.md` before submitting changes.

Developers can fork the repository, create focused branches, and propose pull requests. New hardware adapters and AI integrations should preserve the public JSON event contract whenever practical.

Experimental vibration events must not be presented as confirmed earthquakes or guaranteed early warnings without appropriate validation.

## Plugin ecosystem

OptiQuake Local includes a versioned **Plugin API v1** so community extensions can receive vibration events without modifying the detector core.

Plugins can be loaded from a local directory or discovered as installed Python packages through the `optiquake.plugins` entry-point group.

Example:
```powershell
python src\optiquake.py --plugin-dir plugins --seconds 10
```

The repository includes:
- `src/plugin_api.py` — stable event contract.
- `src/plugin_loader.py` — discovery and lifecycle isolation.
- `plugins/example_console.py` — minimal bundled example.
- `examples/plugin-package/` — independently installable plugin template.
- `registry/plugins.json` — community discovery registry.
- `schemas/plugin-manifest.schema.json` — manifest schema.

See `docs/PLUGIN_DEVELOPMENT.md` and `docs/PLUGIN_REGISTRY.md`.

