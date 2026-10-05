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
- Windows 10/11 (DirectShow); Linux (V4L2) and macOS (AVFoundation) capture backends are experimental
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

Linux / macOS (experimental):
```bash
python3 src/optiquake.py --health                      # check FFmpeg and backend
python3 src/optiquake.py --camera /dev/video0 --fps 60 # Linux, V4L2
python3 src/optiquake.py --camera 0 --fps 60           # macOS, AVFoundation
```

Replay a recorded clip for reproducible, offline validation (timestamps use media time):
```bash
python3 src/optiquake.py --input recording.mp4 --fps 60
```

Useful options:

| Option | Purpose |
|---|---|
| `--backend auto\|dshow\|v4l2\|avfoundation` | FFmpeg capture backend (default: by operating system) |
| `--input FILE` | Analyze a recorded video instead of a live camera |
| `--cooldown SECONDS` | Minimum time between vibration events (merges nearby bursts) |
| `--end-seconds SECONDS` | Quiet time that closes a vibration (default 0.25 s) |
| `--min-coverage FRACTION` | Require this fraction of the image to move (e.g. 0.5) |
| `--audio [DEVICE]` | Add the low-frequency microphone channel (file audio with `--input`) |
| `--list-devices` | Show camera and microphone names |
| `--seconds SECONDS` | Stop after this much time |
| `--health` | Report FFmpeg/platform readiness as JSON and exit |
| `--version` | Print the version |

Each vibration produces an `event=vibration` line when it starts and a `status=vibration_end` line with `start`, `duration`, `frames`, `peak_score` and `peak_robust_z` when it ends.

### Insta360 Link: pixels + low-frequency microphone

The detector combines two channels that the camera already delivers over USB:

- **Pixels:** `coverage` (fraction of a 4x4 grid that moved) separates whole-camera shaking from a person or object moving in one region; `shift_px` is the sub-pixel global image shift; `dominant_hz` estimates the oscillation frequency.
- **Microphone:** band energy in 20–200 Hz (structural rumble) corroborates optical events (`audio_z`, `corroborated`).

```powershell
optiquake-local --list-devices
optiquake-local --camera "Insta360 Link" --audio "Microphone (Insta360 Link)" --min-coverage 0.5
```

Setup guide (tracking off, microphone noise reduction off, rigid mounting, gimbal IMU status): [docs/INSTA360_LINK.md](docs/INSTA360_LINK.md) (Spanish).

## Safety and scientific limits
OptiQuake Local is a research prototype, **not a certified seismometer or life-safety system**. A single sensor at the user's location cannot reliably warn before the first seismic waves reach that same sensor.

Local vibration can come from footsteps, doors, traffic, fans, camera motion, construction, or other non-seismic sources. Do not replace official emergency alerts or certified seismic systems with this software.

The project intentionally reports **vibration events**, not "earthquakes," until independent multi-sensor validation supports classification.

## Privacy
The MVP processes frames and audio locally and does not save video or audio. It emits numeric vibration-event metadata to stdout.

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

