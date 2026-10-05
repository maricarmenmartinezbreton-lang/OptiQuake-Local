"""Detector tests using synthetic scores and frames (no camera or FFmpeg)."""
import contextlib, io, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import array, math
import threading
from audio_band import AudioBand, read_stream
from optiquake import (Detector, audio_input_args, capture_input_args, main, mad,
                       process, resolve_backend)
from pixel_features import dominant_frequency, frame_shift, grid_mad, profiles
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
events, _ = run_scores(d, quiet(120) + [9.0, 9.0] + quiet(20))
assert events == []

# One burst -> one event plus an end summary with duration and peak.
d = Detector(fps=60, baseline_frames=120, min_frames=3)
events, summaries = run_scores(d, quiet(120) + [6.0, 9.0, 7.0, 8.0] + quiet(20))
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

# Brief dips inside an oscillation do not split the vibration (end_frames).
burst = quiet(120) + [9.0]*4 + quiet(3) + [9.0]*4 + quiet(20)
events, summaries = run_scores(Detector(fps=60, baseline_frames=120), burst)
assert len(events) == 1 and summaries[0]["frames"] == 8, summaries
assert abs(summaries[0]["duration"] - 11/60) < 1e-3, summaries

# Separate bursts give separate events; cooldown merges them.
burst = quiet(120) + [9.0]*4 + quiet(20) + [9.0]*4 + quiet(20)
assert len(run_scores(Detector(fps=60, baseline_frames=120), burst)[0]) == 2
assert len(run_scores(Detector(fps=60, baseline_frames=120, cooldown=1.0), burst)[0]) == 1

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

# Pixel features on synthetic textured frames (no FFmpeg needed).
W, H = 64, 36
def scene(dx=0.0, dy=0.0, block=None):
    """Smooth texture sampled with a sub-pixel offset; optional bright block."""
    px = []
    for y in range(H):
        for x in range(W):
            v = 128 + 60*math.sin((x+dx)*0.45) + 50*math.cos((y+dy)*0.6)
            if block and block[0] <= x < block[0]+12 and block[1] <= y < block[1]+12:
                v = 255
            px.append(max(0, min(255, int(v))))
    return bytes(px)

score, cells = grid_mad(scene(), scene(1.0), W, H, grid=4)
assert len(cells) == 16 and abs(score - mad(scene(), scene(1.0))) < 1e-9
dx, dy = frame_shift(profiles(scene(), W, H), profiles(scene(1.5, -1.0), W, H))
# scene(dx) samples at x+dx, so the content moves by -dx.
assert abs(dx + 1.5) < 0.4 and abs(dy - 1.0) < 0.4, (dx, dy)
assert dominant_frequency([math.sin(2*math.pi*5*i/60) for i in range(60)], 60) == 5.0

def run_frames(frames, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        process(iter(frames), Detector(fps=60, baseline_frames=120, **kw),
                PluginManager(), fps=60, width=W, height=H)
    return [json.loads(x) for x in out.getvalue().splitlines()]

quiet_frames = [scene(0.05*(i % 2)) for i in range(150)]
shake = [scene(2*math.sin(2*math.pi*5*i/60), math.sin(2*math.pi*5*i/60))
         for i in range(60)]
local = [scene(block=(4 + (i*7) % 10, 4)) for i in range(60)]
tail = quiet_frames[:30]

lines = run_frames(quiet_frames + shake + tail)
end = [x for x in lines if x.get("status") == "vibration_end"][0]
assert end["peak_coverage"] >= 0.5 and end["peak_shift_px"] > 0.5, end
assert 4.0 <= end["dominant_hz"] <= 6.0 and abs(end["duration"] - 1.0) < 0.1, end

lines = run_frames(quiet_frames + local + tail)
ev = [x for x in lines if x.get("event") == "vibration"]
assert ev and ev[0]["coverage"] < 0.5 and ev[0]["shift_px"] < 0.5, ev
assert run_frames(quiet_frames + local + tail, min_coverage=0.5) == []
assert len(run_frames(quiet_frames + shake + tail, min_coverage=0.5)) == 2

# Audio band: low-frequency rumble is detected, high-frequency hum is not.
import random
rng = random.Random(7)
def tone(f, amp, secs, rate=8000, noise=300):
    """Sine plus a broadband noise floor, like a real microphone."""
    return array.array("h", (int(amp*math.sin(2*math.pi*f*i/rate) + rng.gauss(0, noise))
                             for i in range(int(rate*secs)))).tobytes()
band = AudioBand(rate=8000, window=0.05, baseline_windows=100)
band.feed(tone(1000, 2000, 3) + tone(1000, 8000, 0.5) + tone(50, 3000, 0.5), 0.0)
assert band.peak_z(0.5, 2.9) < 4
assert band.peak_z(3.05, 3.45) < 4      # louder 1 kHz hum is out of band
assert band.peak_z(3.6, 4.0) > 10       # 50 Hz rumble is in band
# Chunked feeding keeps timestamps continuous.
band2 = AudioBand(rate=8000, window=0.05, baseline_windows=100)
pcm = tone(1000, 2000, 1)
for i in range(0, len(pcm), 333*2):
    band2.feed(pcm[i:i+333*2], i/2/8000)
assert band2.windows == 20 and abs(band2.history[-1][0] - 1.0) < 1e-6

# Live reader: bursty delivery (all data arriving at once) still yields
# timestamps that advance with the sample count, not the arrival time.
band3 = AudioBand(rate=8000, window=0.05, baseline_windows=100)
read_stream(band3, io.BytesIO(tone(1000, 2000, 0.9)), lambda: 5.0, threading.Event())
ts = [t for t, _ in band3.history]
assert band3.windows == 18 and abs((ts[-1] - ts[0]) - 0.85) < 1e-6, ts[:3]

# Capture backends and CLI helpers.
assert resolve_backend("dshow") == "dshow"
assert resolve_backend("auto") in {"dshow", "v4l2", "avfoundation"}
assert capture_input_args("dshow", "Cam", 60)[-1] == "video=Cam"
assert capture_input_args("avfoundation", "0", 60)[-1] == "0:none"
assert capture_input_args("v4l2", "/dev/video0", 60)[:2] == ["-f", "v4l2"]
assert capture_input_args("v4l2", "x", 60, "clip.mp4") == ["-i", "clip.mp4"]
assert mad(b"\x00\x04", b"\x02\x00") == 3
assert audio_input_args("dshow", "Mic (Insta360 Link)")[-1] == "audio=Mic (Insta360 Link)"
assert "-audio_buffer_size" in audio_input_args("dshow", "Mic")
assert audio_input_args("v4l2", "default")[:2] == ["-f", "alsa"]
assert audio_input_args("avfoundation", "0")[-1] == "none:0"
assert audio_input_args("dshow", None, "clip.mp4") == ["-i", "clip.mp4"]
with contextlib.redirect_stdout(io.StringIO()):
    assert main(["--self-test"]) == 0

print("DETECTOR_TEST_OK")
