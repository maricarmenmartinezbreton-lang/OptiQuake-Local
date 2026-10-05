# AI Skill Integration

OptiQuake Local can run as a reusable local sensor skill for AI agents and automation systems.

## Contract
The detector writes one JSON object per line to stdout. Agents should parse events without requiring any cloud seismic feed.

Example start event:
```json
{"status":"started","camera":"Insta360 Link","fps":60}
```

Example vibration event:
```json
{"event":"vibration","t":1.42,"score":13.40,"baseline":0.39,"robust_z":34.1}
```

Example end-of-vibration summary (illustrative values; pixel and microphone evidence appear when enabled):
```json
{"status":"vibration_end","t":5.0,"start":4.017,"duration":1.0,"frames":50,"peak_score":12.42,"peak_robust_z":28.27,"peak_coverage":1.0,"peak_shift_px":2.654,"dominant_hz":5.09,"audio_peak_z":44.8,"corroborated":true}
```

`coverage` near 1 with a non-zero `shift_px` indicates the whole camera moved; low `coverage` indicates local motion (people, objects). `corroborated` means the low-frequency microphone band also rose during the event.

Errors are reported as `{"status":"error","detail":"..."}` with a non-zero exit code. Run `--health` before monitoring to check FFmpeg and backend availability.

## Integration targets
- OpenClaw/JARVIS skill
- Generic subprocess-capable AI agents
- MCP wrappers
- n8n or other local automation
- Home/edge AI projects

## Decision semantics
`vibration` means only that local motion exceeded the learned baseline. An agent must not rename it to `earthquake` unless another trusted local or external confirmation layer justifies that conclusion.

## Privacy
The current detector processes reduced grayscale frames in memory and does not need to save raw video. Deployments should preserve this as the default.

