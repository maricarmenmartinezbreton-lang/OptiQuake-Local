# Initial validation record

Date: 2026-09-27  
Platform: Windows / PC2-ULTRA-PRO  
Camera: Insta360 Link, USB VID:PID `2E1A:4C01`  
Observed mode: 1920x1080 up to 60 fps; validation capture used 60 fps.

## Quiet baseline
- Mean: 0.3927
- P95: 0.4548
- Maximum: 0.7864

## Controlled mechanical events
| Event | Time | Peak | Peak / quiet mean |
|---|---:|---:|---:|
| 1 | 0.62 s | 7.7565 | 19.8x |
| 2 | 1.42 s | 13.4026 | 34.1x |
| 3 | 2.17 s | 9.2156 | 23.5x |

Microphone observations were exploratory and are not used as a trigger in v0.1.0.

## Interpretation
The setup demonstrated that webcam-derived frame differences can strongly separate deliberate mechanical motion from a quiet interval. This is proof of **vibration observability**, not proof of seismic-event specificity.

