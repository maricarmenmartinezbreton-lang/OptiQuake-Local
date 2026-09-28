---
name: optiquake-local
description: "Detección óptica local y experimental de vibraciones usando una webcam de alta frecuencia, con salida JSON para agentes de IA."
---

# OptiQuake Local

## Purpose
Use a local high-frame-rate camera as an auxiliary vibration sensor without relying on external seismic feeds.

## Entry point
`python src/optiquake.py --camera "Insta360 Link" --fps 60`

## Output contract
The process emits JSON Lines on stdout:
- `status=started`: sensor stream opened.
- `event=vibration`: local motion exceeded the adaptive baseline.
- `status=stopped`: monitoring ended.

A vibration event contains `t`, `score`, `baseline`, and `robust_z`.

## Agent rules
1. Treat every event as **local vibration**, not automatically as an earthquake.
2. Never claim early-warning capability from one co-located webcam.
3. Correlate with additional local sensors when available: phone IMU, microphone, or a dedicated accelerometer.
4. Use adaptive baselines and require repeated frames before raising an alert.
5. Keep raw video disabled by default; process frames in memory when possible.6. Report uncertainty explicitly and distinguish `vibration_detected` from `seismic_event_confirmed`.
7. External seismic feeds may be used only as optional post-event corroboration, never as a requirement for local triggering.

## Recommended actions for AI systems
- `monitor`: start local observation and stream JSON events.
- `calibrate`: learn a quiet baseline for the installation site.
- `health`: confirm camera availability, FPS and FFmpeg access.
- `correlate`: combine vibration events with other local sensor events.

## Safety boundary
This project is experimental and is not a certified seismometer or a replacement for official emergency or early-warning systems.

