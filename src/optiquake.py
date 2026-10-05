#!/usr/bin/env python3
"""OptiQuake Local - experimental optical vibration detector.
Author: Lic. Juan Esteban Ramírez | License: AGPL-3.0-only
"""
import argparse, collections, json, shutil, statistics, subprocess, sys, time

from plugin_api import VibrationEvent
from plugin_loader import PluginLoadError, PluginManager

__version__ = "0.1.2"

# FFmpeg input formats per platform. "auto" resolves through sys.platform.
BACKENDS = {"win32": "dshow", "linux": "v4l2", "darwin": "avfoundation"}
DEFAULT_CAMERAS = {"dshow": "Insta360 Link", "v4l2": "/dev/video0",
                   "avfoundation": "0"}

def emit(obj):
    print(json.dumps(obj), flush=True)

def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if not p:
        raise SystemExit("FFmpeg not found in PATH")
    return p

def resolve_backend(backend):
    if backend != "auto":
        return backend
    for prefix, name in BACKENDS.items():
        if sys.platform.startswith(prefix):
            return name
    return "v4l2"

def capture_input_args(backend, camera, fps, input_file=None):
    """FFmpeg input arguments for a live camera or a recorded file."""
    if input_file:
        return ["-i", input_file]
    if backend == "dshow":
        return ["-f", "dshow", "-framerate", str(fps), "-i", f"video={camera}"]
    if backend == "avfoundation":
        return ["-f", "avfoundation", "-framerate", str(fps), "-i", f"{camera}:none"]
    return ["-f", backend, "-framerate", str(fps), "-i", camera]

def capture(backend, camera, fps, width, height, input_file=None):
    vf = f"fps={fps},scale={width}:{height},format=gray"
    cmd = [find_ffmpeg(), "-hide_banner", "-loglevel", "error",
           *capture_input_args(backend, camera, fps, input_file),
           "-an", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            bufsize=width*height*4)

def mad(a, b):
    return sum(abs(x-y) for x, y in zip(a, b)) / len(a)

class Detector:
    """Adaptive robust-z detector over a stream of frame-difference scores.

    feed() returns a VibrationEvent when a vibration starts and records a
    summary (duration, peak) in `self.summary` when it ends.
    """

    def __init__(self, fps, baseline_frames=600, z_threshold=8.0,
                 min_score=1.0, min_frames=3, cooldown=0.0):
        self.fps = fps
        self.base = collections.deque(maxlen=baseline_frames)
        self.warmup = min(max(30, fps), baseline_frames)
        self.z_threshold = z_threshold
        self.min_score = min_score
        self.min_frames = min_frames
        self.cooldown = cooldown
        self.streak = 0
        self.streak_peak = (0.0, 0.0)
        self.active = None
        self.last_event_t = None
        self.summary = None
        self.events = 0

    @property
    def ready(self):
        return len(self.base) >= self.warmup

    def feed(self, score, t):
        self.summary = None
        if not self.ready:
            self.base.append(score)
            return None
        med = statistics.median(self.base)
        dev = statistics.median(abs(x-med) for x in self.base) or 0.01
        z = (score-med)/(1.4826*dev)
        hit = z >= self.z_threshold and score >= self.min_score
        event = None
        if hit:
            self.streak += 1
            if score > self.streak_peak[0] or self.streak == 1:
                self.streak_peak = (score, z)
            if self.active is not None:
                self.active["frames"] += 1
                if score > self.active["peak_score"]:
                    self.active["peak_score"], self.active["peak_z"] = score, z
            if self.streak == self.min_frames and self._cooled_down(t):
                start = t - (self.min_frames-1)/self.fps
                self.active = {"start": start, "frames": self.min_frames,
                               "peak_score": self.streak_peak[0],
                               "peak_z": self.streak_peak[1]}
                self.last_event_t = t
                self.events += 1
                event = VibrationEvent(t=round(t,3), score=round(score,4),
                                       baseline=round(med,4), robust_z=round(z,2))
        else:
            self.streak = 0
            self.base.append(score)
            if self.active is not None:
                self.summary = self._finish(t)
        return event

    def _cooled_down(self, t):
        return self.last_event_t is None or t - self.last_event_t >= self.cooldown

    def _finish(self, t):
        a, self.active = self.active, None
        return {"status": "vibration_end", "t": round(t,3),
                "start": round(a["start"],3), "duration": round(t-a["start"],3),
                "frames": a["frames"], "peak_score": round(a["peak_score"],4),
                "peak_robust_z": round(a["peak_z"],2)}

    def flush(self, t):
        """Close a vibration that is still active when the stream ends."""
        return self._finish(t) if self.active is not None else None

def iter_frames(stream, n):
    while True:
        frame = stream.read(n)
        if len(frame) != n:
            return
        yield frame

def process(frames, detector, plugins, fps, seconds=0, clock=None):
    """Run the detector over raw grayscale frames, emitting JSONL.

    With clock=None timestamps come from the frame index (media time), which
    makes recorded inputs reproducible. Pass time.monotonic for live cameras.
    """
    started = clock() if clock else 0.0
    prev = None
    t = 0.0
    count = 0
    for frame in frames:
        count += 1
        t = clock()-started if clock else (count-1)/fps
        if prev is not None:
            event = detector.feed(mad(prev, frame), t)
            if event is not None:
                emit(event.to_dict())
                emit_plugin_errors("event", plugins.emit(event))
            if detector.summary is not None:
                emit(detector.summary)
        prev = frame
        if seconds and t >= seconds:
            break
    summary = detector.flush(t)
    if summary is not None:
        emit(summary)
    return count

def build_plugins(args):
    manager = PluginManager()
    manager.load_directory(args.plugin_dir)
    if args.installed_plugins:
        manager.load_entrypoints()
    return manager

def emit_plugin_errors(stage, errors):
    for error in errors:
        emit({"plugin_error": stage, "detail": error})

def stop_process(p):
    p.terminate()
    try:
        p.wait(timeout=2)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()

def run(args):
    try:
        plugins = build_plugins(args)
    except PluginLoadError as exc:
        emit({"status": "error", "detail": str(exc)})
        return 2
    backend = resolve_backend(args.backend)
    camera = args.camera or DEFAULT_CAMERAS.get(backend, "0")
    source = args.input or camera
    p = capture(backend, camera, args.fps, args.width, args.height, args.input)
    detector = Detector(args.fps, args.baseline_frames, args.z_threshold,
                        args.min_score, args.min_frames, args.cooldown)
    context = {"camera": source, "fps": args.fps, "backend": backend,
               "width": args.width, "height": args.height,
               "replay": bool(args.input)}
    emit_plugin_errors("start", plugins.start(context))
    emit({"status": "started", "camera": source, "fps": args.fps,
          "backend": "file" if args.input else backend,
          "plugins": plugins.describe()})
    count = 0
    interrupted = False
    try:
        frames = iter_frames(p.stdout, args.width*args.height)
        clock = None if args.input else time.monotonic
        count = process(frames, detector, plugins, args.fps, args.seconds, clock)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        stop_process(p)
        emit_plugin_errors("stop", plugins.stop())
    if count == 0 and not interrupted:
        err = p.stderr.read().decode("utf-8", "replace").strip()
        emit({"status": "error", "detail": err or "no frames received from FFmpeg"})
        return 1
    emit({"status": "stopped", "frames": count, "events": detector.events,
          "baseline_samples": len(detector.base)})
    return 0

def health(args):
    """Report whether the local environment can run the detector."""
    ffmpeg = shutil.which("ffmpeg")
    backend = resolve_backend(args.backend)
    report = {"status": "health", "version": __version__,
              "python": sys.version.split()[0], "platform": sys.platform,
              "backend": backend, "ffmpeg": ffmpeg,
              "ok": ffmpeg is not None}
    emit(report)
    return 0 if report["ok"] else 1

def self_test():
    assert mad(bytes([0]*100), bytes([10]*100)) == 10
    assert resolve_backend("v4l2") == "v4l2"
    # Synthetic stream: quiet noise, one 5-frame burst, quiet again.
    d = Detector(fps=60, baseline_frames=120, z_threshold=8, min_score=1, min_frames=3)
    scores = [0.4 + 0.01*(i % 5) for i in range(120)] + [9.0]*5 + [0.41]*10
    events, summaries = [], []
    for i, s in enumerate(scores):
        e = d.feed(s, i/60)
        if e:
            events.append(e)
        if d.summary:
            summaries.append(d.summary)
    assert len(events) == 1 and events[0].event == "vibration", events
    assert len(summaries) == 1 and summaries[0]["frames"] == 5, summaries
    print("SELF_TEST_OK")
    return 0

def positive_int(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return n

def non_negative(value):
    n = float(value)
    if n < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return n

def main(argv=None):
    ap = argparse.ArgumentParser(description="Experimental local optical vibration detector")
    ap.add_argument("--camera", help="camera name/device (default depends on backend)")
    ap.add_argument("--backend", default="auto",
                    choices=["auto", "dshow", "v4l2", "avfoundation"],
                    help="FFmpeg capture backend (auto: by operating system)")
    ap.add_argument("--input", metavar="FILE",
                    help="replay a recorded video file instead of a live camera")
    ap.add_argument("--fps", type=positive_int, default=60)
    ap.add_argument("--width", type=positive_int, default=160)
    ap.add_argument("--height", type=positive_int, default=90)
    ap.add_argument("--baseline-frames", type=positive_int, default=600)
    ap.add_argument("--z-threshold", type=float, default=8.0)
    ap.add_argument("--min-score", type=float, default=1.0)
    ap.add_argument("--min-frames", type=positive_int, default=3)
    ap.add_argument("--cooldown", type=non_negative, default=0.0,
                    help="minimum seconds between vibration events")
    ap.add_argument("--seconds", type=non_negative, default=0)
    ap.add_argument("--plugin-dir")
    ap.add_argument("--installed-plugins", action="store_true")
    ap.add_argument("--health", action="store_true",
                    help="check FFmpeg and platform support, then exit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.health:
        return health(args)
    return run(args)

if __name__ == "__main__":
    sys.exit(main())
