#!/usr/bin/env python3
"""OptiQuake Local - experimental optical vibration detector.
Author: Lic. Juan Esteban Ramírez | License: AGPL-3.0-only
"""
import argparse, collections, json, shutil, statistics, subprocess, time

from plugin_api import VibrationEvent
from plugin_loader import PluginManager

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
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            bufsize=width*height*4)

def mad(a, b):
    return sum(abs(x-y) for x, y in zip(a, b)) / len(a)

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
    plugins = build_plugins(args)
    p = capture(args.camera, args.fps, args.width, args.height)
    n = args.width * args.height
    prev = None
    base = collections.deque(maxlen=args.baseline_frames)
    streak = 0
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
            if prev is None:
                prev = frame
                continue
            score = mad(prev, frame)
            prev = frame
            if len(base) >= max(30, args.fps):
                med = statistics.median(base)
                dev = statistics.median(abs(x-med) for x in base) or 0.01
                z = (score-med)/(1.4826*dev)
                hit = z >= args.z_threshold and score >= args.min_score
                streak = streak + 1 if hit else 0
                if streak == args.min_frames:
                    event = VibrationEvent(
                        t=round(time.time()-started,3), score=round(score,4),
                        baseline=round(med,4), robust_z=round(z,2))
                    print(json.dumps(event.to_dict()), flush=True)
                    emit_plugin_errors("event", plugins.emit(event))
                if not hit:
                    base.append(score)
            else:
                base.append(score)
            if args.seconds and time.time()-started >= args.seconds:
                break
    finally:
        p.terminate()
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            p.kill()
        emit_plugin_errors("stop", plugins.stop())
    print(json.dumps({"status":"stopped","baseline_samples":len(base)}), flush=True)

def self_test():
    assert mad(bytes([0]*100), bytes([10]*100)) == 10
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
    self_test() if args.self_test else run(args)

if __name__ == "__main__":
    main()
