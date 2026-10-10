# OptiQuake Local

[![PyPI version](https://img.shields.io/pypi/v/optiquake-local.svg)](https://pypi.org/project/optiquake-local/) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23004638.svg)](https://doi.org/10.5281/zenodo.23004638) [![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE) [![Public reach metrics](https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local/actions/workflows/public-metrics.yml/badge.svg)](https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local/actions/workflows/public-metrics.yml)

Experimental local optical vibration detection using an ordinary high-frame-rate webcam.

**Live public reach:** [METRICS.md](METRICS.md) tracks GitHub traffic, PyPI downloads and Zenodo views/downloads every two days.

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

## Earthquake alerts (experimental)
`--alerts` combines the camera with official earthquake reports and warns people nearby in every way available:

```powershell
# once: set your location (saved, so it also works offline later)
python src\optiquake.py --alerts --lat 18.4861 --lon -69.9312 --place "Santo Domingo" --drill
# normal use: camera + official feeds + phones on the home Wi-Fi
python src\optiquake.py --alerts --lan-port
```

- **Official feeds:** USGS, EMSC and GFZ GEOFON are checked every 30 s (`--feed-interval`). Reports of the same quake from several agencies are merged. A report triggers an alert only if, given its magnitude and distance, it may be felt **at your location**; a quake in the Dominican Republic does not alert someone in New York. Official catalogues publish 1-20 minutes after the event, so they confirm and describe quakes; they are not early warning.
- **Camera (works without internet):** a strong vibration triggers an immediate alert marked *unconfirmed*. If an official report arrives shortly after, the alert says it was confirmed. If the internet drops, the program says so and keeps alerting from the camera.
- **Messages:** "EARTHQUAKE ALERT" + *Drop, Cover, Hold On* while shaking may be happening, then *leave calmly by the stairs to a safe open area*; tsunami advice for large shallow quakes nearby. Spanish (default) or English (`--lang en`).
- **Alert channels:** full-screen flashing window, siren through the default audio device (built-in speakers, Bluetooth speaker or headphones; on Windows the volume is raised to the maximum first), spoken message, and:
  - `--lan-port`: an alert page for phones and tablets on the same Wi-Fi. **No internet needed**, only the home router. Open the printed address on the phone, tap *Activar alertas* and leave it open with the screen on; it flashes, plays a siren, vibrates (Android) and speaks.
  - `--ntfy-topic NAME`: push notification to phones with the [ntfy](https://ntfy.sh) app, even with the screen off (needs internet). Use a long, hard-to-guess topic name.
- `--drill` runs a test alert (*SIMULACRO*) through every channel. `--no-camera` uses only the official feeds; `--no-feeds` never uses the internet.
- **Sensor network** (`--mesh-key KEY`): several OptiQuake computers on the same network (home, office, neighbours sharing a network) send each other signed detections. When another sensor sees the same vibration within 10 s the alert becomes *confirmed by N sensors*; detections from other sensors alone raise an alert only when at least two agree (`--mesh-min-sensors`), so a truck next to one house does not alarm everyone. A drill started on one computer runs on all of them. Use the same key on every computer.
- **Always on:** while monitoring, Windows is kept from sleeping (`--allow-sleep` to disable). `--install-autostart` starts the alerts when you sign in to Windows, restarts them if they stop, and logs to `%APPDATA%\OptiQuake\optiquake.log`. With the PC locked, the siren, voice and phones still work.

**Easiest install on Windows:** double-click `INSTALAR-WINDOWS.cmd`. It installs Python and FFmpeg if missing (with winget) and runs a guided setup: location (Dominican Republic city list, internet detection or coordinates), camera, phones, sensor network, a drill and start-with-Windows. `DESINSTALAR-ARRANQUE.cmd` removes the automatic start. The first time, allow Windows Firewall access on *private networks* so phones and other sensors can connect.

These alerts are informational and experimental. Keep official alerts enabled (for example Android Earthquake Alerts, ShakeAlert, national emergency alerts) and follow local authorities.

## Safety and scientific limits
OptiQuake Local is a research prototype, **not a certified seismometer or life-safety system**. A single sensor at the user's location cannot reliably warn before the first seismic waves reach that same sensor.

Local vibration can come from footsteps, doors, traffic, fans, camera motion, construction, or other non-seismic sources. Do not replace official emergency alerts or certified seismic systems with this software.

The project intentionally reports **vibration events**, not "earthquakes," until independent multi-sensor validation supports classification.

## Privacy
The MVP processes frames locally and does not save video. It emits numeric vibration-event metadata to stdout.

With `--alerts`, the program downloads public earthquake lists from USGS, EMSC and GFZ; your location is used only on your computer to compute distances and is saved in `%APPDATA%\OptiQuake\location.json`. `--auto-location` sends a request to ipwho.is, which sees your public IP. `--ntfy-topic` sends the alert text to ntfy.sh. `--lan-port` serves a read-only alert page on your local network.

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

