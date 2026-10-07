# Changelog

All notable project changes should be recorded here.

## Unreleased
- Spoken alerts now use an installed voice in the alert's language (classic or modern Windows 10/11 voices) instead of the system default voice, keep accents intact, read naturally (no "·", no spelled-out capitals), and report how to install a Spanish voice when none exists.
- Experimental earthquake alerts (`--alerts`): official feeds from USGS, EMSC and GFZ GEOFON, merged across agencies and filtered by the user's location (felt/strong-shaking distance estimates), plus immediate camera alerts that keep working offline and are marked confirmed when an official report matches.
- Alert messages in Spanish and English: "ALERTA DE SISMO", Drop-Cover-Hold-On while shaking, calm evacuation to a safe open area afterwards, tsunami advice for large shallow quakes nearby.
- Alert channels: full-screen flashing window, siren with Windows volume boost (speakers, Bluetooth or headphones), offline Windows speech, an alert page for phones on the home Wi-Fi that needs no internet (`--lan-port`), and ntfy phone push (`--ntfy-topic`).
- Sensor network (`--mesh-key`): OptiQuake computers on the same network share HMAC-signed detections over UDP; alerts are upgraded to "confirmed by N sensors", peer-only detections need two sensors, drills run on every sensor; stale, replayed or unsigned messages are rejected.
- Always on: Windows is kept awake while monitoring, `--install-autostart`/`--uninstall-autostart` (Startup folder, no admin, self-restarting), rotating `--log` file.
- Guided setup (`--setup`, `INSTALAR-WINDOWS.cmd`): installs Python/FFmpeg with winget if missing, Dominican Republic city list, camera detection, phones, sensor network, drill and start with Windows; `--from-settings` reuses the saved choices; `--list-cameras`.
- `--drill` (simulacro), `--no-camera` (feeds only), `--no-feeds` (never use internet), saved location for offline use, optional `--auto-location`.
- Fixed a hang when FFmpeg writes many warnings: its error output is now drained in the background instead of filling the pipe.
- A missing or busy camera now reports `{"status": "capture_failed"}` with FFmpeg's error message and exits with code 1, instead of a silent `stopped`.
- Invalid options (`--min-frames 0`, `--fps 0`, negative `--seconds`, or `--baseline-frames` smaller than the warm-up window) are rejected with a clear message; previously some of them made detection fire on every quiet frame or never start.
- Plugin load failures print a one-line message instead of a traceback.
- Detection logic moved into a testable `Detector` class (same behaviour), covered by the new `tests/test_detector.py` and an extended `--self-test`.
- Fixed literal `` `r`n `` characters and a byte-order mark at the top of the README.

## 0.1.2-experimental — 2026-09-27
- Added public documentation in English, Spanish, Portuguese, French, German, Italian, Simplified Chinese, Japanese, Korean, Arabic, Hindi, and Russian.
- Added hreflang links, expanded sitemap coverage, multilingual search keywords, and localized discovery pages.
- Updated AI-readable `llms.txt` with multilingual documentation endpoints.
- Added multilingual documentation links to the package README so PyPI visitors can reach localized pages.
- Scientific scope remains unchanged: experimental local vibration observability, not validated earthquake classification or guaranteed early warning.

## 0.1.1-experimental — 2026-09-27
- Added secure PyPI Trusted Publishing workflow using GitHub OIDC.
- Added protected `pypi` deployment environment with required owner review.
- Enabled Zenodo-ready software metadata for DOI archival.
- Added GitHub Pages, CodeMeta, `llms.txt`, and discovery metadata.
- No change to the scientific claim: this remains experimental vibration monitoring, not validated earthquake detection or guaranteed early warning.

## 0.1.0-experimental — 2026-09-27
- Initial optical vibration detector validated with Insta360 Link at 60 fps.
- JSONL event output and AI skill packaging.
- AGPL-3.0-only licensing and explicit provenance documentation.
- Plugin API v1 with local and Python entry-point discovery.
- Plugin failure isolation and bundled example plugin.
- Community plugin registry, manifest schema, contribution workflow, and roadmap.
- Installable Python wheel and CLI packaging.

This release validates local vibration observability, not earthquake classification or guaranteed early warning.
