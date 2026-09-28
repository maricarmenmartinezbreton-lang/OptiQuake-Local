# OptiQuake Local Roadmap

## Phase 0 — Completed foundation

- Local optical vibration detection from a 60 fps webcam stream.
- JSONL event output for automation and AI systems.
- Experimental AI skill packaging.
- AGPL-3.0 licensing, authorship, and reproducible validation notes.

## Phase 1 — Calibration and false-positive control

- Establish quiet baselines by device and installation position.
- Add event duration, frequency-shape, and persistence features.
- Build test cases for footsteps, doors, desk impacts, fans, and camera/gimbal motion.
- Add configurable confidence fields without labeling an event as an earthquake.

## Phase 2 — Multi-sensor fusion

- Add microphone-band features as auxiliary evidence.
- Add phone or external IMU adapters.
- Correlate independent local sensors by timestamp.
- Support geographically separated community nodes where available.

## Phase 3 — Interoperability and research

- Add MCP and REST adapters.
- Add Linux/macOS capture backends.
- Publish anonymized/reproducible benchmark datasets where consent and privacy permit.
- Evaluate seismic classification only against appropriately labeled reference data.

## Long-term goal

Enable inexpensive, locally operated vibration-monitoring nodes that researchers and communities can extend without mandatory subscriptions or dependence on a single vendor.