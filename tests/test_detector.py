import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from optiquake import Detector

def make(**kw):
    opts = dict(fps=30, baseline_frames=60, z_threshold=8.0, min_score=1.0, min_frames=3)
    opts.update(kw)
    return Detector(**opts)

quiet = [0.10, 0.12, 0.11, 0.09, 0.13]

# No events during warm-up, even for large scores.
d = make()
assert all(d.update(9.0 if i == 10 else quiet[i % 5]) is None for i in range(30))

# One event per sustained burst, fired on the min_frames-th hit frame.
d = make()
for i in range(90):
    d.update(quiet[i % 5])
fired = [d.update(5.0) for _ in range(6)]
assert [f is not None for f in fired] == [False, False, True, False, False, False]
med, z = fired[2]
assert abs(med - 0.11) < 1e-9 and z > 8.0

# Burst frames do not pollute the baseline; a new burst fires again.
assert max(d.base) < 1.0
d.update(0.11)
assert [d.update(5.0) is not None for _ in range(3)] == [False, False, True]

# Bursts shorter than min_frames are ignored.
d = make()
for i in range(90):
    d.update(quiet[i % 5])
assert d.update(5.0) is None and d.update(5.0) is None and d.update(0.11) is None
assert d.streak == 0

# Scores below min_score never fire, even with a huge z-score.
d = make()
for _ in range(90):
    d.update(0.0)
assert all(d.update(0.5) is None for _ in range(10))

# Invalid CLI values are rejected before any capture starts.
cli = [sys.executable, str(ROOT / "src" / "optiquake.py")]
for bad in (["--min-frames", "0"], ["--fps", "0"], ["--baseline-frames", "10"],
            ["--seconds", "-1"]):
    r = subprocess.run(cli + bad + ["--self-test"], capture_output=True, text=True)
    assert r.returncode == 2, (bad, r.returncode, r.stderr)

print("DETECTOR_TEST_OK")
