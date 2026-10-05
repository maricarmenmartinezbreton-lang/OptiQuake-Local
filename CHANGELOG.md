# Changelog

All notable project changes should be recorded here.

## Unreleased
- Insta360 Link multi-channel sensing using only the camera's USB streams:
  - Pixel features: spatial `coverage` on a 4x4 grid, sub-pixel global `shift_px`, and `dominant_hz` from the shift oscillation.
  - Low-frequency microphone channel (`--audio`, 20–200 Hz band, robust baseline) with `audio_z`, `audio_peak_z` and `corroborated`.
  - `--min-coverage` rejects motion confined to one image region; `--list-devices` shows camera/microphone names.
- Guided field test `scripts/prueba_campo.py` (Windows): records a 52 s protocol (quiet, desk knocks, walking, mount shake) with on-screen prompts, analyzes it and saves a JSON report locally.
- Vibrations now start when `--min-frames` hits fall within a short window (oscillations dip through zero velocity), so short knocks are detected.
- `dominant_hz` is estimated from integrated displacement with hysteresis, which is robust to noisy shifts.
- Vibrations now close after `--end-seconds` (default 0.25 s) of quiet so one oscillation is not split into several events.
- `VibrationEvent` gained optional `coverage`, `shift_px` and `audio_z` fields, omitted when unset; plugin API stays at v1.
- Documented that the Insta360 Link SDK exposes no live gyro/IMU stream (`docs/INSTA360_LINK.md`).
- Refactored detection into a testable `Detector` class; the `event=vibration` contract and plugin API v1 are unchanged.
- Added `status=vibration_end` summaries with start time, duration, frame count and peak score/robust z.
- Added experimental Linux (V4L2) and macOS (AVFoundation) capture backends via `--backend` (auto-selected by OS).
- Added `--input FILE` to replay recorded video with reproducible media-time timestamps.
- Added `--cooldown`, `--health` and `--version`; validated numeric CLI arguments.
- Ctrl+C now stops cleanly; FFmpeg capture failures and plugin load errors are reported as `status=error` JSON with a non-zero exit code.
- Added synthetic detector tests (`tests/test_detector.py`) to CI.
- Fixed a stray line-break artifact in the README.

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
