#!/usr/bin/env python3
"""OptiQuake Local - experimental optical vibration detector.
Author: Lic. Juan Esteban Ramírez | License: AGPL-3.0-only
"""
import argparse, collections, json, shutil, statistics, subprocess, sys, threading, time

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
    if args.feed_interval < 10:
        ap.error("--feed-interval must be >= 10 seconds (be polite to official servers)")
    if (args.drill or args.no_camera) and not args.alerts:
        ap.error("--drill and --no-camera require --alerts")
    if args.no_camera and args.no_feeds:
        ap.error("--no-camera and --no-feeds together leave nothing to monitor")
    if args.baseline_frames < warmup_frames(args.fps):
        ap.error(f"--baseline-frames must be >= {warmup_frames(args.fps)} "
                 "(max of 30 and --fps), otherwise detection never starts")

def build_plugins(args):
    manager = PluginManager()
    manager.load_directory(args.plugin_dir)
    if args.installed_plugins:
        manager.load_entrypoints()
    return manager

def setup_location(args):
    import geo
    if args.lat is not None or args.lon is not None:
        if args.lat is None or args.lon is None:
            raise SystemExit("Use --lat and --lon together")
        loc = geo.Location(args.lat, args.lon, args.place or "", "manual")
        geo.save_location(loc)
        return loc
    if args.auto_location:
        try:
            loc = geo.locate_by_ip()
            geo.save_location(loc)
            return loc
        except Exception as exc:
            print(json.dumps({"notice": "auto location failed, using saved location",
                              "detail": str(exc)[:200]}), flush=True)
    return geo.load_location()

def build_alert_center(args):
    import quake_alerts as qa, quake_feeds
    location = setup_location(args)
    print(json.dumps({"status": "location", "location": location.__dict__ if location else None}),
          flush=True)
    if location is None:
        print(json.dumps({"notice": "No location set: official reports cannot be filtered by "
                          "distance. Use --lat/--lon (once; it is saved) or --auto-location."}),
              flush=True)
    channels = [qa.ConsoleChannel()]
    if not args.no_sound:
        channels.append(qa.SirenChannel(boost_volume=not args.no_volume_boost))
    if not args.no_voice:
        channels.append(qa.VoiceChannel())
    if not args.no_window:
        channels.append(qa.WindowChannel())
    if args.ntfy_topic:
        channels.append(qa.NtfyChannel(args.ntfy_topic))
    if args.lan_port:
        try:
            lan = qa.LanChannel(args.lan_port)
        except OSError as exc:
            raise SystemExit(f"Cannot open home-network alert page on port {args.lan_port}: {exc}")
        channels.append(lan)
        print(json.dumps({"status": "lan_alerts", "url": lan.url,
                          "help": "open this address on phones connected to the same Wi-Fi"}),
              flush=True)
    center = qa.AlertCenter(location, channels, lang=args.lang, camera=not args.no_camera)
    if not args.no_feeds:
        center.monitor = quake_feeds.FeedMonitor(center.on_quake, center.on_status,
                                                 interval=args.feed_interval)
    return center

def monitor_feeds_only(args, plugins):
    """No camera: official feeds only (works on any OS, needs internet)."""
    started = time.time()
    emit_plugin_errors("start", plugins.start({"camera": None}))
    print(json.dumps({"status": "started", "camera": None,
                      "plugins": plugins.describe()}), flush=True)
    try:
        while not args.seconds or time.time() - started < args.seconds:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        emit_plugin_errors("stop", plugins.stop())
    print(json.dumps({"status": "stopped"}), flush=True)

def emit_plugin_errors(stage, errors):
    for error in errors:
        print(json.dumps({"plugin_error": stage, "detail": error}), flush=True)

def run(args):
    try:
        plugins = build_plugins(args)
    except (PluginLoadError, ImportError, SyntaxError) as exc:
        raise SystemExit(f"Plugin load failed: {exc}")
    if args.alerts:
        center = build_alert_center(args)
        if args.drill:
            if args.lan_port:
                print(json.dumps({"notice": "drill in 15 s: open the page on your phone "
                                  "and tap 'Activar alertas'"}), flush=True)
                time.sleep(15)
            center.drill()
            time.sleep(25 if args.lan_port else 3)  # let siren/voice/window/phones react
            center.on_stop()
            return
        plugins.plugins.insert(0, center)
    if args.no_camera:
        return monitor_feeds_only(args, plugins)
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
    # Spanish alert text must never crash a console that cannot show accents.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
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
    al = ap.add_argument_group("earthquake alerts (experimental)")
    al.add_argument("--alerts", action="store_true",
                    help="enable alerts: camera events + official feeds (USGS, EMSC, GFZ)")
    al.add_argument("--lat", type=float, help="your latitude (saved for offline use)")
    al.add_argument("--lon", type=float, help="your longitude (saved for offline use)")
    al.add_argument("--place", help="name for your location, e.g. 'Santo Domingo'")
    al.add_argument("--auto-location", action="store_true",
                    help="approximate location from your public IP (needs internet)")
    al.add_argument("--lang", choices=["es", "en"], default="es")
    al.add_argument("--no-feeds", action="store_true", help="camera only, never use internet")
    al.add_argument("--no-camera", action="store_true", help="official feeds only")
    al.add_argument("--feed-interval", type=float, default=30.0,
                    help="seconds between official feed checks (default 30)")
    al.add_argument("--no-sound", action="store_true")
    al.add_argument("--no-volume-boost", action="store_true",
                    help="do not raise the Windows volume before the siren")
    al.add_argument("--no-voice", action="store_true")
    al.add_argument("--no-window", action="store_true")
    al.add_argument("--ntfy-topic", help="ntfy.sh topic to push alerts to your phone (internet)")
    al.add_argument("--lan-port", type=int, nargs="?", const=8765, default=None,
                    help="serve an alert page for phones on the home Wi-Fi "
                         "(no internet needed; default port 8765)")
    al.add_argument("--drill", action="store_true", help="trigger a test alert (simulacro) and exit")
    args = ap.parse_args()
    validate_args(ap, args)
    self_test() if args.self_test else run(args)

if __name__ == "__main__":
    main()
