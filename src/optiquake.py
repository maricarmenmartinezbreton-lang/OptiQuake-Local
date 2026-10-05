#!/usr/bin/env python3
"""OptiQuake Local - experimental optical vibration detector.
Author: Lic. Juan Esteban Ramírez | License: AGPL-3.0-only
"""
import argparse, collections, dataclasses, json, math, shutil, statistics
import subprocess, sys, threading, time

from audio_band import AudioBand, read_stream
from pixel_features import dominant_frequency, frame_shift, grid_mad, profiles
from plugin_api import VibrationEvent
from plugin_loader import PluginLoadError, PluginManager

__version__ = "0.1.2"

# FFmpeg input formats per platform. "auto" resolves through sys.platform.
BACKENDS = {"win32": "dshow", "linux": "v4l2", "darwin": "avfoundation"}
DEFAULT_CAMERAS = {"dshow": "Insta360 Link", "v4l2": "/dev/video0",
                   "avfoundation": "0"}
# Audio capture: FFmpeg format and default device for each video backend.
AUDIO_BACKENDS = {"dshow": ("dshow", None), "v4l2": ("alsa", "default"),
                  "avfoundation": ("avfoundation", "0")}

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

def audio_input_args(backend, device, input_file=None):
    """FFmpeg input arguments for a live microphone or a recorded file."""
    if input_file:
        return ["-i", input_file]
    fmt, _ = AUDIO_BACKENDS.get(backend, ("alsa", "default"))
    if fmt == "dshow":
        # DirectShow buffers 500 ms of audio by default; 50 ms keeps the
        # microphone close in time to the video frames.
        return ["-f", "dshow", "-audio_buffer_size", "50", "-i", f"audio={device}"]
    if fmt == "avfoundation":
        return ["-f", "avfoundation", "-i", f"none:{device}"]
    return ["-f", fmt, "-i", device]

def capture_audio(backend, device, rate, input_file=None):
    cmd = [find_ffmpeg(), "-hide_banner", "-loglevel", "error",
           *audio_input_args(backend, device, input_file),
           "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "pipe:1"]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def list_devices(args):
    """Show the camera and microphone names FFmpeg can open."""
    backend = resolve_backend(args.backend)
    if backend == "v4l2":
        import glob
        emit({"status": "devices", "backend": backend,
              "video": sorted(glob.glob("/dev/video*")),
              "audio_hint": "use 'arecord -l'; pass e.g. --audio hw:1,0 or default"})
        return 0
    fmt = "dshow" if backend == "dshow" else "avfoundation"
    dummy = "dummy" if fmt == "dshow" else ""
    r = subprocess.run([find_ffmpeg(), "-hide_banner", "-f", fmt, "-list_devices",
                        "true", "-i", dummy], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    print(r.stderr.strip())
    return 0

def mad(a, b):
    return sum(abs(x-y) for x, y in zip(a, b)) / len(a)

class Detector:
    """Adaptive robust-z detector over a stream of frame-difference scores.

    feed() returns a VibrationEvent when a vibration starts and records a
    summary (duration, peak, coverage, frequency) in `self.summary` when it
    ends. Optional per-cell scores and global image shift add evidence that
    separates whole-camera shaking from local motion in the scene.
    """

    def __init__(self, fps, baseline_frames=600, z_threshold=8.0,
                 min_score=1.0, min_frames=3, cooldown=0.0, min_coverage=0.0,
                 end_frames=None):
        self.fps = fps
        self.base = collections.deque(maxlen=baseline_frames)
        self.warmup = min(max(30, fps), baseline_frames)
        self.z_threshold = z_threshold
        self.min_score = min_score
        self.min_frames = min_frames
        self.cooldown = cooldown
        self.min_coverage = min_coverage
        # A vibration starts when min_frames hits fall inside this many recent
        # frames: oscillations dip through zero velocity, so hits interleave
        # with quiet frames and are rarely consecutive.
        self.start_window = 2*min_frames
        # Quiet frames needed to close a vibration: oscillations pass through
        # zero velocity, so a single quiet frame must not end the event.
        self.end_frames = end_frames if end_frames is not None else max(1, fps//4)
        self.streak = []
        self.active = None
        self.last_event_t = None
        self.summary = None
        self.events = 0

    @property
    def ready(self):
        return len(self.base) >= self.warmup

    def feed(self, score, t, cells=None, shift=None):
        self.summary = None
        if not self.ready:
            self.base.append(score)
            return None
        med = statistics.median(self.base)
        dev = statistics.median(abs(x-med) for x in self.base) or 0.01
        z = (score-med)/(1.4826*dev)
        coverage = None
        if cells:
            cell_thr = max(self.min_score, med + self.z_threshold*1.4826*dev)
            coverage = sum(1 for c in cells if c >= cell_thr)/len(cells)
        hit = (z >= self.z_threshold and score >= self.min_score
               and (coverage is None or coverage >= self.min_coverage))
        sample = {"score": score, "z": z, "coverage": coverage, "shift": shift,
                  "hit": hit, "t": t}
        if self.active is not None:
            self.active["samples"].append(sample)
            if hit:
                self.active["quiet"] = 0
            else:
                self.active["quiet"] += 1
                if self.active["quiet"] >= self.end_frames:
                    self.summary = self._finish()
            return None
        if not hit:
            self.base.append(score)
        self.streak.append(sample)
        self.streak = self.streak[-self.start_window:]
        while self.streak and not self.streak[0]["hit"]:
            self.streak.pop(0)
        hits = sum(1 for x in self.streak if x["hit"])
        if not hit or hits < self.min_frames or not self._cooled_down(t):
            return None
        self.active = {"start": self.streak[0]["t"],
                       "samples": self.streak, "quiet": 0}
        self.streak = []
        self.last_event_t = t
        self.events += 1
        shift_px = None if shift is None else round(math.hypot(*shift), 3)
        return VibrationEvent(t=round(t,3), score=round(score,4),
                              baseline=round(med,4), robust_z=round(z,2),
                              coverage=None if coverage is None else round(coverage,3),
                              shift_px=shift_px)

    def _cooled_down(self, t):
        return self.last_event_t is None or t - self.last_event_t >= self.cooldown

    def _finish(self):
        a, self.active = self.active, None
        samples = a["samples"]
        if a["quiet"]:
            samples = samples[:-a["quiet"]]  # trailing quiet frames
        t = samples[-1]["t"]
        hits = [x for x in samples if x["hit"]]
        peak = max(hits, key=lambda x: x["score"])
        summary = {"status": "vibration_end", "t": round(t,3),
                   "start": round(a["start"],3),
                   "duration": round(t-a["start"]+1/self.fps,3),
                   "frames": len(hits), "peak_score": round(peak["score"],4),
                   "peak_robust_z": round(peak["z"],2)}
        covs = [x["coverage"] for x in hits if x["coverage"] is not None]
        if covs:
            summary["peak_coverage"] = round(max(covs),3)
        shifts = [x["shift"] for x in samples if x["shift"] is not None]
        if shifts:
            summary["peak_shift_px"] = round(max(math.hypot(*s) for s in shifts),3)
            xs, ys = [s[0] for s in shifts], [s[1] for s in shifts]
            axis = xs if statistics.pvariance(xs) >= statistics.pvariance(ys) else ys
            hz = dominant_frequency(axis, self.fps)
            if hz is not None:
                summary["dominant_hz"] = round(hz,2)
        return summary

    def flush(self, t):
        """Close a vibration that is still active when the stream ends."""
        return self._finish() if self.active is not None else None

def iter_frames(stream, n):
    while True:
        frame = stream.read(n)
        if len(frame) != n:
            return
        yield frame

def add_audio_evidence(summary, audio, threshold, margin=0.5):
    peak = audio.peak_z(summary["start"]-margin, summary["t"]+margin)
    if peak is not None:
        summary["audio_peak_z"] = round(peak,2)
        summary["corroborated"] = peak >= threshold
    return summary

def process(frames, detector, plugins, fps, seconds=0, clock=None,
            width=None, height=None, grid=4, audio=None, audio_threshold=4.0):
    """Run the detector over raw grayscale frames, emitting JSONL.

    With clock=None timestamps come from the frame index (media time), which
    makes recorded inputs reproducible. For live cameras pass a function that
    returns elapsed seconds. With width/height the pixel features (coverage
    and global shift) are computed; audio is an optional AudioBand.
    """
    features = bool(width and height)
    prev = prev_prof = None
    t = 0.0
    count = 0

    def close(summary):
        if audio is not None:
            add_audio_evidence(summary, audio, audio_threshold)
        emit(summary)

    for frame in frames:
        count += 1
        t = clock() if clock else (count-1)/fps
        prof = profiles(frame, width, height) if features else None
        if prev is not None:
            if features:
                score, cells = grid_mad(prev, frame, width, height, grid)
                event = detector.feed(score, t, cells, frame_shift(prev_prof, prof))
            else:
                event = detector.feed(mad(prev, frame), t)
            if event is not None:
                if audio is not None:
                    z = audio.peak_z(t-0.5, t+0.5)
                    if z is not None:
                        event = dataclasses.replace(event, audio_z=round(z,2))
                emit(event.to_dict())
                emit_plugin_errors("event", plugins.emit(event))
            if detector.summary is not None:
                close(detector.summary)
        prev, prev_prof = frame, prof
        if seconds and t >= seconds:
            break
    summary = detector.flush(t)
    if summary is not None:
        close(summary)
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

def start_audio(args, backend, clock):
    """Start the optional microphone channel. Returns (band, process, thread)."""
    band = AudioBand(rate=args.audio_rate, low=args.audio_low, high=args.audio_high,
                     z_threshold=args.audio_z_threshold)
    if args.input:
        # Replay: analyze the file's whole soundtrack first, in media time.
        ap = capture_audio(backend, None, args.audio_rate, args.input)
        pcm, err = ap.communicate()
        band.feed(pcm, 0.0)
        if band.windows == 0:
            emit({"status": "warning", "detail": "no audio track analyzed",
                  "ffmpeg": err.decode("utf-8", "replace").strip()})
        return band, None, None
    device = args.audio
    if device == "auto":
        device = AUDIO_BACKENDS.get(backend, ("alsa", "default"))[1]
    if not device:
        emit({"status": "error",
              "detail": "pass the microphone name, e.g. --audio \"Microphone "
                        "(Insta360 Link)\"; see --list-devices"})
        return None, None, None
    ap = capture_audio(backend, device, args.audio_rate)
    stop = threading.Event()
    th = threading.Thread(target=read_stream, args=(band, ap.stdout, clock, stop),
                          daemon=True)
    th.stop = stop
    th.start()
    return band, ap, th

def run(args):
    try:
        plugins = build_plugins(args)
    except PluginLoadError as exc:
        emit({"status": "error", "detail": str(exc)})
        return 2
    backend = resolve_backend(args.backend)
    camera = args.camera or DEFAULT_CAMERAS.get(backend, "0")
    source = args.input or camera
    t0 = time.monotonic()
    clock = None if args.input else (lambda: time.monotonic() - t0)
    audio = audio_proc = audio_thread = None
    if args.audio:
        audio, audio_proc, audio_thread = start_audio(
            args, backend, clock or (lambda: 0.0))
        if audio is None:
            return 2
    p = capture(backend, camera, args.fps, args.width, args.height, args.input)
    detector = Detector(args.fps, args.baseline_frames, args.z_threshold,
                        args.min_score, args.min_frames, args.cooldown,
                        args.min_coverage, max(1, round(args.end_seconds*args.fps)))
    context = {"camera": source, "fps": args.fps, "backend": backend,
               "width": args.width, "height": args.height,
               "replay": bool(args.input), "audio": bool(audio)}
    emit_plugin_errors("start", plugins.start(context))
    emit({"status": "started", "camera": source, "fps": args.fps,
          "backend": "file" if args.input else backend,
          "audio": args.audio if audio else None,
          "plugins": plugins.describe()})
    count = 0
    interrupted = False
    try:
        frames = iter_frames(p.stdout, args.width*args.height)
        grid_w, grid_h = (args.width, args.height) if args.grid > 1 else (None, None)
        count = process(frames, detector, plugins, args.fps, args.seconds, clock,
                        grid_w, grid_h, args.grid, audio, args.audio_z_threshold)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        stop_process(p)
        if audio_proc is not None:
            audio_thread.stop.set()
            stop_process(audio_proc)
        emit_plugin_errors("stop", plugins.stop())
    if count == 0 and not interrupted:
        err = p.stderr.read().decode("utf-8", "replace").strip()
        emit({"status": "error", "detail": err or "no frames received from FFmpeg"})
        return 1
    stopped = {"status": "stopped", "frames": count, "events": detector.events,
               "baseline_samples": len(detector.base)}
    if audio is not None:
        stopped["audio_windows"] = audio.windows
        if audio_proc is not None and audio.windows == 0:
            err = audio_proc.stderr.read().decode("utf-8", "replace").strip()
            emit({"status": "warning", "detail": "microphone produced no audio",
                  "ffmpeg": err})
    emit(stopped)
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
    scores = [0.4 + 0.01*(i % 5) for i in range(120)] + [9.0]*5 + [0.41]*20
    events, summaries = [], []
    for i, s in enumerate(scores):
        e = d.feed(s, i/60)
        if e:
            events.append(e)
        if d.summary:
            summaries.append(d.summary)
    assert len(events) == 1 and events[0].event == "vibration", events
    assert len(summaries) == 1 and summaries[0]["frames"] == 5, summaries
    # Pixel features: a frame shifted by 2 columns is detected as dx ~ 2.
    w, h = 32, 8
    a = bytes((x*37 % 251) for _ in range(h) for x in range(w))
    b = bytes(a[y*w + (x-2) % w] for y in range(h) for x in range(w))
    dx, dy = frame_shift(profiles(a, w, h), profiles(b, w, h))
    assert abs(dx-2) < 0.5 and abs(dy) < 0.5, (dx, dy)
    # Audio channel: a 60 Hz rumble stands out from a quiet 1 kHz hum.
    import array as _array
    band = AudioBand(rate=8000, window=0.05, baseline_windows=100)
    def tone(f, amp, secs):
        return _array.array("h", (int(amp*math.sin(2*math.pi*f*i/8000))
                                  for i in range(int(8000*secs)))).tobytes()
    band.feed(tone(1000, 3000, 3) + tone(60, 3000, 0.5), 0.0)
    assert band.peak_z(3.1, 3.5) > 10 and band.peak_z(1.0, 2.9) < 4
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
    ap.add_argument("--end-seconds", type=non_negative, default=0.25,
                    help="quiet time that closes a vibration (default 0.25 s)")
    ap.add_argument("--cooldown", type=non_negative, default=0.0,
                    help="minimum seconds between vibration events")
    ap.add_argument("--seconds", type=non_negative, default=0)
    ap.add_argument("--min-coverage", type=float, default=0.0,
                    help="require this fraction of image cells to move (0-1); "
                         "e.g. 0.5 ignores motion confined to one region")
    ap.add_argument("--grid", type=positive_int, default=4,
                    help="grid size for pixel coverage features (1 disables them)")
    ap.add_argument("--audio", nargs="?", const="auto", metavar="DEVICE",
                    help="add the low-frequency microphone channel; with --input "
                         "the file's audio track is used")
    ap.add_argument("--audio-low", type=float, default=20.0, help="band low edge, Hz")
    ap.add_argument("--audio-high", type=float, default=200.0, help="band high edge, Hz")
    ap.add_argument("--audio-rate", type=positive_int, default=8000)
    ap.add_argument("--audio-z-threshold", type=float, default=4.0,
                    help="audio robust z that corroborates an optical event")
    ap.add_argument("--plugin-dir")
    ap.add_argument("--installed-plugins", action="store_true")
    ap.add_argument("--list-devices", action="store_true",
                    help="list camera and microphone names, then exit")
    ap.add_argument("--health", action="store_true",
                    help="check FFmpeg and platform support, then exit")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.health:
        return health(args)
    if args.list_devices:
        return list_devices(args)
    return run(args)

if __name__ == "__main__":
    sys.exit(main())
