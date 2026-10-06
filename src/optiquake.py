#!/usr/bin/env python3
"""OptiQuake Local - experimental optical vibration detector.
Author: Lic. Juan Esteban Ramírez | License: AGPL-3.0-only
"""
import argparse, collections, json, shutil, statistics, subprocess, threading, time

from plugin_api import VibrationEvent
from plugin_loader import PluginLoadError, PluginManager

def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if not p:
        raise SystemExit("FFmpeg not found in PATH")
    return p

def capture(camera, fps, width, height):
    vf = f"fps={fps},scale={width}:{height},format=gray"
    cmd = [find_ffmpeg(), "-hide_banner", "-loglevel", "error",
           "-f", "dshow", "-i", f"video={camera}", "-vf", vf,
           "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         bufsize=width*height*4)
    # Drain stderr so FFmpeg never blocks on a full pipe; keep the tail for diagnostics.
    p.stderr_tail = collections.deque(maxlen=20)
    def drain():
        for line in p.stderr:
            p.stderr_tail.append(line.decode("utf-8", errors="replace").rstrip())
    p.stderr_thread = threading.Thread(target=drain, daemon=True)
    p.stderr_thread.start()
    return p

def mad(a, b):
    return sum(abs(x-y) for x, y in zip(a, b)) / len(a)

def warmup_frames(fps):
    return max(30, fps)

class Detector:
    """Robust z-score detector over frame-to-frame motion scores."""
    def __init__(self, fps, baseline_frames, z_threshold, min_score, min_frames):
        self.warmup = warmup_frames(fps)
        self.base = collections.deque(maxlen=baseline_frames)
        self.z_threshold = z_threshold
        self.min_score = min_score
        self.min_frames = min_frames
        self.streak = 0

    def update(self, score):
        """Feed one score; return (median, robust_z) when an event fires, else None."""
        if len(self.base) < self.warmup:
            self.base.append(score)
            return None
        med = statistics.median(self.base)
        dev = statistics.median(abs(x-med) for x in self.base) or 0.01
        z = (score-med)/(1.4826*dev)
        hit = z >= self.z_threshold and score >= self.min_score
        self.streak = self.streak + 1 if hit else 0
        if not hit:
            self.base.append(score)
        if self.streak == self.min_frames:
            return med, z
        return None

def validate_args(ap, args):
    for name in ("fps", "width", "height", "min_frames"):
        if getattr(args, name) < 1:
            ap.error(f"--{name.replace('_', '-')} must be >= 1")
    if args.seconds < 0:
        ap.error("--seconds must be >= 0")
    if args.baseline_frames < warmup_frames(args.fps):
        ap.error(f"--baseline-frames must be >= {warmup_frames(args.fps)} "
                 "(max of 30 and --fps), otherwise detection never starts")

def build_plugins(args):
    manager = PluginManager()
    manager.load_directory(args.plugin_dir)
    if args.installed_plugins:
        manager.load_entrypoints()
    return manager

def emit_plugin_errors(stage, errors):
    for error in errors:
        print(json.dumps({"plugin_error": stage, "detail": error}), flush=True)

def run(args):
    try:
        plugins = build_plugins(args)
    except (PluginLoadError, ImportError, SyntaxError) as exc:
        raise SystemExit(f"Plugin load failed: {exc}")
    p = capture(args.camera, args.fps, args.width, args.height)
    n = args.width * args.height
    prev = None
    detector = Detector(args.fps, args.baseline_frames, args.z_threshold,
                        args.min_score, args.min_frames)
    frames = 0
    started = time.time()
    context = {"camera": args.camera, "fps": args.fps,
               "width": args.width, "height": args.height}
    emit_plugin_errors("start", plugins.start(context))
    print(json.dumps({"status":"started","camera":args.camera,"fps":args.fps,
                      "plugins":plugins.describe()}), flush=True)
    try:
        while True:
            frame = p.stdout.read(n)
            if len(frame) != n:
                break
            frames += 1
            if prev is None:
                prev = frame
                continue
            score = mad(prev, frame)
            prev = frame
            fired = detector.update(score)
            if fired:
                med, z = fired
                event = VibrationEvent(
                    t=round(time.time()-started,3), score=round(score,4),
                    baseline=round(med,4), robust_z=round(z,2))
                print(json.dumps(event.to_dict()), flush=True)
                emit_plugin_errors("event", plugins.emit(event))
            if args.seconds and time.time()-started >= args.seconds:
                break
    finally:
        p.terminate()
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            p.kill()
        p.stderr_thread.join(timeout=1)
        emit_plugin_errors("stop", plugins.stop())
    if frames == 0:
        detail = " | ".join(p.stderr_tail) or "no frames received"
        print(json.dumps({"status":"capture_failed","camera":args.camera,
                          "detail":detail}), flush=True)
        raise SystemExit(1)
    print(json.dumps({"status":"stopped","frames":frames,
                      "baseline_samples":len(detector.base)}), flush=True)

def self_test():
    assert mad(bytes([0]*100), bytes([10]*100)) == 10
    d = Detector(fps=30, baseline_frames=60, z_threshold=8.0, min_score=1.0, min_frames=3)
    quiet = [0.10, 0.12, 0.11, 0.09, 0.13]
    assert all(d.update(quiet[i % 5]) is None for i in range(90))
    hits = [d.update(5.0) for _ in range(5)]
    assert hits[:2] == [None, None] and hits[2] is not None and hits[3:] == [None, None]
    print("SELF_TEST_OK")

def main():
    ap = argparse.ArgumentParser(description="Experimental local optical vibration detector")
    ap.add_argument("--camera", default="Insta360 Link")
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--width", type=int, default=160)
    ap.add_argument("--height", type=int, default=90)
    ap.add_argument("--baseline-frames", type=int, default=600)
    ap.add_argument("--z-threshold", type=float, default=8.0)
    ap.add_argument("--min-score", type=float, default=1.0)
    ap.add_argument("--min-frames", type=int, default=3)
    ap.add_argument("--seconds", type=int, default=0)
    ap.add_argument("--plugin-dir")
    ap.add_argument("--installed-plugins", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    validate_args(ap, args)
    self_test() if args.self_test else run(args)

if __name__ == "__main__":
    main()
