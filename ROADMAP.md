# OptiQuake Local Roadmap

## Phase 0 — Completed foundation

- Local optical vibration detection from a 60 fps webcam stream.
- JSONL event output for automation and AI systems.
- Experimental AI skill packaging.
- AGPL-3.0 licensing, authorship, and reproducible validation notes.

Research notes on what an early-warning-capable roadmap requires: [docs/INVESTIGACION_ALERTA_TEMPRANA.md](docs/INVESTIGACION_ALERTA_TEMPRANA.md) (Spanish).

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
## Plugin ecosystem milestones

### Plugin API v1 — implemented
- Event-consumer plugins with lifecycle hooks.
- Local-directory discovery.
- Python package entry-point discovery.
- Failure isolation so plugin exceptions do not stop the detector.
- Community registry and manifest schema.

### Plugin API v2 — proposed
- Sensor-source plugins for external IMUs, phones, MEMS devices, microphones, and network nodes.
- Detector/feature plugins that can contribute measurements before event classification.
- Capability negotiation and permissions for network, storage, camera, and microphone access.
- Signed release metadata and reproducible plugin test fixtures.

### Ecosystem adapters
- MCP server adapter.
- n8n/Home Assistant nodes.
- Webhook/REST event gateway.
- Dashboard and time-series storage plugins.
