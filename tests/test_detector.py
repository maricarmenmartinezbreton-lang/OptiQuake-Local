"""Detector tests using synthetic scores and frames (no camera or FFmpeg)."""
import contextlib, io, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from optiquake import (Detector, capture_input_args, main, mad, process,
                       resolve_backend)
from plugin_loader import PluginManager

def quiet(n):
    return [0.4 + 0.01*(i % 5) for i in range(n)]

def run_scores(detector, scores, fps=60):
    events, summaries = [], []
    for i, s in enumerate(scores):
        e = detector.feed(s, i/fps)
        if e:
            events.append(e)
        if detector.summary:
            summaries.append(detector.summary)
    return events, summaries

# No events while the baseline is still warming up, even for large scores.
d = Detector(fps=60, baseline_frames=120)
events, _ = run_scores(d, [50.0]*59)
assert events == [] and not d.ready

# Quiet stream never triggers.
d = Detector(fps=60, baseline_frames=120)
assert run_scores(d, quiet(600)) == ([], [])

# A burst shorter than min_frames is ignored.
d = Detector(fps=60, baseline_frames=120, min_frames=3)
events, _ = run_scores(d, quiet(120) + [9.0, 9.0] + quiet(10))
assert events == []

# One burst -> one event plus an end summary with duration and peak.
d = Detector(fps=60, baseline_frames=120, min_frames=3)
events, summaries = run_scores(d, quiet(120) + [6.0, 9.0, 7.0, 8.0] + quiet(10))
assert len(events) == 1
assert events[0].to_dict()["event"] == "vibration"
assert events[0].robust_z >= 8
s = summaries[0]
assert s["status"] == "vibration_end" and s["frames"] == 4
assert s["peak_score"] == 9.0
assert abs(s["duration"] - 4/60) < 1e-3, s

# Vibration frames do not contaminate the baseline.
assert 9.0 not in d.base

# min_score gates events even with a large robust z.
d = Detector(fps=60, baseline_frames=120, min_score=20.0)
assert run_scores(d, quiet(120) + [9.0]*5 + quiet(5))[0] == []

# Cooldown merges bursts that are close together.
burst = quiet(120) + [9.0]*4 + quiet(3) + [9.0]*4 + quiet(5)
assert len(run_scores(Detector(fps=60, baseline_frames=120), burst)[0]) == 2
assert len(run_scores(Detector(fps=60, baseline_frames=120, cooldown=0.5), burst)[0]) == 1

# A vibration still active at stream end is flushed.
d = Detector(fps=60, baseline_frames=120)
run_scores(d, quiet(120) + [9.0]*5)
assert d.flush(2.0)["frames"] == 5 and d.flush(2.1) is None

# process() over synthetic frames emits JSONL with media-time timestamps.
n = 16
frames = [bytes([100 + (i % 2)]*n) for i in range(200)]
frames[150:155] = [bytes([(100 + 60*(i % 2))]*n) for i in range(5)]
out = io.StringIO()
with contextlib.redirect_stdout(out):
    count = process(iter(frames), Detector(fps=60, baseline_frames=120),
                    PluginManager(), fps=60)
lines = [json.loads(x) for x in out.getvalue().splitlines()]
assert count == 200
kinds = [x.get("event") or x.get("status") for x in lines]
assert kinds == ["vibration", "vibration_end"], lines
assert 2.4 < lines[0]["t"] < 2.6, lines[0]

# Capture backends and CLI helpers.
assert resolve_backend("dshow") == "dshow"
assert resolve_backend("auto") in {"dshow", "v4l2", "avfoundation"}
assert capture_input_args("dshow", "Cam", 60)[-1] == "video=Cam"
assert capture_input_args("avfoundation", "0", 60)[-1] == "0:none"
assert capture_input_args("v4l2", "/dev/video0", 60)[:2] == ["-f", "v4l2"]
assert capture_input_args("v4l2", "x", 60, "clip.mp4") == ["-i", "clip.mp4"]
assert mad(b"\x00\x04", b"\x02\x00") == 3
with contextlib.redirect_stdout(io.StringIO()):
    assert main(["--self-test"]) == 0

print("DETECTOR_TEST_OK")
