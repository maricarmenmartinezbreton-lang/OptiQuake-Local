# Discoverability and publication plan

OptiQuake Local should be published where developers, researchers, search engines and AI systems can discover it.

## Primary distribution
1. Public GitHub repository with topics, releases and GitHub Pages.
2. Python package distribution on PyPI: published as `optiquake-local`.
3. Zenodo archival of tagged releases: enabled; project DOI `10.5281/zenodo.23004638`.
4. Software Heritage archival: automatic GitHub push webhook enabled for long-term source preservation.

## Machine discovery
- `codemeta.json` for structured research-software metadata.
- `CITATION.cff` for citation metadata.
- `llms.txt` as a concise agent-readable project description.
- `skill/manifest.json` and plugin schema for machine integration.
- Consistent keywords in README and packaging metadata.

## Human discovery
- GitHub Pages project site.
- GitHub topics and repository description.
- Release notes and changelog.
- Documentation pages explaining installation, plugins and validation.

## Publication rule
Every public description must distinguish validated local vibration detection from unvalidated earthquake classification or guaranteed early warning.

## Attribution
Original creator: **Lic. Juan Esteban Ramírez**. License: **AGPL-3.0-only**.
