# OptiQuake Local

Experimental local optical vibration detection using an ordinary high-frame-rate webcam.

**Author:** Lic. Juan Esteban Ramírez  
**Origin:** Dominican Republic, 27 September 2026  
**Version:** 0.1.0-experimental  
**License:** MIT

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
