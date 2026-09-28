---
title: OptiQuake Local
description: Open-source experimental optical vibration monitoring with webcam sensors, plugins and AI-agent integrations.
---

# OptiQuake Local

**Created by Lic. Juan Esteban Ramírez — Dominican Republic.**

OptiQuake Local is an open-source experimental platform for local vibration monitoring using accessible hardware such as high-frame-rate webcams. It includes a plugin API and AI-agent skill interface so researchers, makers and communities can extend it.

## Why it exists
Many communities do not have equal access to dense early-warning infrastructure. OptiQuake Local explores low-cost local sensing without depending on an external earthquake feed to trigger a vibration event.

## What is validated
Controlled testing with an Insta360 Link at 60 fps demonstrated clear optical detection of intentional mechanical vibration events above the quiet baseline.

## What is not claimed
The project is not a certified seismometer, earthquake predictor or guaranteed early-warning system. Vibration events require independent validation before seismic classification.

## Ecosystem
- Python package and CLI
- AI skill interface
- Plugin API v1
- Community plugin registry
- JSONL event stream
- AGPL-3.0-only copyleft licensing

See the repository README, validation notes and contribution guide for installation and research details.

## Install
`python -m pip install optiquake-local`

PyPI: https://pypi.org/project/optiquake-local/

Project DOI: https://doi.org/10.5281/zenodo.23004638

## More resources
- [Resumen en español](es.md)
- [Agent-readable summary](llms.txt)
