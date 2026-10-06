# Changelog

All notable project changes should be recorded here.

## Unreleased
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
