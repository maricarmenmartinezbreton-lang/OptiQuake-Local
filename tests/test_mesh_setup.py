import json, os, pathlib, socket, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import autostart, geo, mesh, quake_alerts as qa, setup_wizard
from plugin_api import VibrationEvent

KEY = b"casa-secreta-123"
NOW = 1_800_000_000.0

# ---- signed messages
raw = mesh.encode(KEY, "sala", "vibration", {"score": 3.0}, now=NOW)
msg = mesh.decode(KEY, raw, now=NOW + 1)
assert msg["node"] == "sala" and msg["data"] == {"score": 3.0}
assert mesh.decode(b"otra-clave-xyz", raw, now=NOW) is None, "wrong key rejected"
assert mesh.decode(KEY, raw.replace(b'"sala"', b'"cocina"'), now=NOW) is None, "tampering rejected"
assert mesh.decode(KEY, raw, now=NOW + 3600) is None, "stale message rejected"
assert mesh.decode(KEY, b"not json", now=NOW) is None

# ---- real UDP socket on localhost, replay and self-echo protection
got = []
port = None
for p in range(18766, 18800):
    try:
        m = mesh.Mesh("casa-secreta-123", "oficina", lambda n, k, d: got.append((n, k)),
                      port=p, broadcast="127.0.0.1", bind_host="127.0.0.1")
        port = p
        break
    except OSError:
        continue
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
peer_raw = mesh.encode(KEY, "sala", "vibration", {})
s.sendto(peer_raw, ("127.0.0.1", port))
s.sendto(peer_raw, ("127.0.0.1", port))  # replay
m.send("vibration", {})                   # own broadcast echoes back: ignored
deadline = time.time() + 5
while time.time() < deadline and not got:
    time.sleep(0.05)
time.sleep(0.5)
assert got == [("sala", "vibration")], got
m.close(); s.close()

# ---- alert center with a sensor network
class Fake:
    name = "fake"
    def __init__(self): self.got = []
    def send(self, a): self.got.append(a)
class FakeMesh:
    def __init__(self): self.sent = []
    def send(self, kind, data): self.sent.append(kind)
    def close(self): pass
SD = geo.Location(18.4861, -69.9312, "Santo Domingo")
ev = VibrationEvent(t=1.0, score=5.0, baseline=0.1, robust_z=30.0)
clock = {"t": NOW}

def center(**kw):
    f, fm = Fake(), FakeMesh()
    c = qa.AlertCenter(SD, [f], clock=lambda: clock["t"], log=lambda r: None,
                       mesh=fm, node="oficina", **kw)
    return c, f, fm

# local detection + a peer within 10 s -> upgraded to "confirmed by 2 sensors"
c, f, fm = center()
c.on_event(ev)
assert fm.sent == ["vibration"] and f.got[-1].level == qa.LOCAL
clock["t"] += 3
c.on_peer("sala", "vibration", {})
assert len(f.got) == 2 and f.got[-1].level == qa.STRONG
assert f.got[-1].lines[0] == "Vibración confirmada por 2 sensores: oficina, sala."
c.on_peer("cocina", "vibration", {})
assert len(f.got) == 2, "one confirmation per burst"

# peers only: one peer is not enough (could be a truck at that house), two are
clock["t"] = NOW + 1000
c, f, fm = center()
c.on_peer("sala", "vibration", {})
assert f.got == []
c.on_peer("cocina", "vibration", {})
assert len(f.got) == 1 and "2 sensores cercanos" in f.got[0].lines[0]
# peers far apart in time do not confirm each other
clock["t"] = NOW + 2000
c, f, fm = center()
c.on_peer("sala", "vibration", {})
clock["t"] += 30
c.on_peer("cocina", "vibration", {})
assert f.got == []
c3, f3, fm3 = center(mesh_min_sensors=1)
c3.on_peer("sala", "vibration", {})
assert f3.got == [], "a single detection is never 'confirmed' by itself"

# drill propagates to every sensor and names who started it
c, f, fm = center()
c.drill()
assert fm.sent == ["drill"] and f.got[-1].drill
c.on_peer("sala", "drill", {})
assert f.got[-1].drill and f.got[-1].lines[1] == "Simulacro iniciado desde: sala."
assert fm.sent == ["drill", "drill_ack"], "a received drill is answered, not re-broadcast"

# drill answers from other computers appear in the drill report
c, f, fm = center()
c.drill()
c.on_peer("sala", "drill_ack", {"to": "oficina"})
c.on_peer("cocina", "drill_ack", {"to": "otro-equipo"})  # not for us
rows = {label: (ok, detail) for label, ok, detail in c.drill_report()}
assert rows["Otros equipos con OptiQuake"] == (True, "respondieron: sala")
c2, f2, fm2 = center()
c2.on_peer("sala", "drill", {})
assert fm2.sent == ["drill_ack"], "a sensor that receives a drill answers it"

# ---- start with Windows (files only; nothing is executed here)
with tempfile.TemporaryDirectory() as tmp:
    home, startup = pathlib.Path(tmp, "home José"), pathlib.Path(tmp, "Startup")
    runner, launcher = autostart.install(["--alerts", "--place", "Santo Domingo"], home,
                                         script=ROOT / "src" / "optiquake.py",
                                         python="C:\\Python313\\python.exe", startup=startup)
    rtext = runner.read_bytes().decode("utf-8")
    assert "\r\r\n" not in rtext
    assert "chcp 65001" in rtext and '--place "Santo Domingo"' in rtext and "--log" in rtext
    assert f"if not exist {launcher}" in rtext.replace('"', "") and "goto loop" in rtext
    assert "\r\n" in rtext
    assert str(runner) in launcher.read_text(encoding="utf-8").replace('"', "")
    assert autostart.uninstall(startup) is True and not launcher.exists()
    assert autostart.uninstall(startup) is False

    log = pathlib.Path(tmp, "o.log")
    log.write_bytes(b"x" * (autostart.LOG_MAX_BYTES + 1))
    with autostart.open_log(log) as fh:
        fh.write("nuevo\n")
    assert log.read_text() == "nuevo\n" and pathlib.Path(tmp, "o.log.1").stat().st_size > autostart.LOG_MAX_BYTES

# ---- camera list from FFmpeg (old and new output formats)
old = '''[dshow @ 0001] DirectShow video devices (some may be both video and audio devices)
[dshow @ 0001]  "Insta360 Link"
[dshow @ 0001]     Alternative name "@device_pnp_\\\\?\\usb#vid_2e1a"
[dshow @ 0001]  "Integrated Webcam"
[dshow @ 0001] DirectShow audio devices
[dshow @ 0001]  "Microphone (Insta360 Link)"
dummy: Immediate exit requested'''
new = '''[dshow @ 0002] "Insta360 Link" (video)
[dshow @ 0002]   Alternative name "@device_pnp_\\\\?\\usb#vid_2e1a"
[dshow @ 0002] "Microphone (Insta360 Link)" (audio)
[dshow @ 0002] "OBS Virtual Camera" (none)'''
assert setup_wizard.parse_dshow_devices(old) == ["Insta360 Link", "Integrated Webcam"]
assert setup_wizard.parse_dshow_devices(new) == ["Insta360 Link"]

# ---- guided setup, answering like a user
def scripted(answers):
    it = iter(answers)
    return lambda prompt: next(it)
with tempfile.TemporaryDirectory() as tmp:
    drills = []
    w = setup_wizard.Wizard("es", ask=scripted([
            "1", "3",            # city list -> La Romana
            "1",                 # camera 1
            "", "n",             # phones on Wi-Fi: default yes; ntfy: no
            "s", "", "Sala",     # mesh: yes, new key, node name
            "s", "s"]),          # drill, autostart
        say=lambda *a: None, home=tmp, cameras=["Insta360 Link"],
        startup=pathlib.Path(tmp, "Startup"), run_drill=drills.append)
    args = w.run()
    assert args[:2] == ["--alerts", "--lang"] and "--lan-port" in args and "--ntfy-topic" not in args
    assert args[args.index("--place") + 1] == "La Romana" and args[args.index("--camera") + 1] == "Insta360 Link"
    key = args[args.index("--mesh-key") + 1]
    assert len(key) >= 8 and args[args.index("--node-name") + 1] == "Sala"
    assert drills == [args]
    assert setup_wizard.load_settings(tmp) == args
    assert (pathlib.Path(tmp, "Startup") / autostart.LAUNCHER_NAME).exists()
    assert geo.load_location(pathlib.Path(tmp, "location.json")).name == "La Romana"

    # all defaults (Enter everywhere), no camera found, invalid input retried
    w = setup_wizard.Wizard("en", ask=scripted(["9", "x", "", "", "", "", "", "", "n"]),
                            say=lambda *a: None, home=tmp, cameras=[], startup=pathlib.Path(tmp, "S2"))
    args = w.run()
    assert "--no-camera" in args and args[args.index("--place") + 1] == "Santo Domingo"
    assert not (pathlib.Path(tmp, "S2") / autostart.LAUNCHER_NAME).exists()

    # IP location failure falls back to the city list
    def boom(): raise OSError("offline")
    w = setup_wizard.Wizard("es", ask=scripted(["2", "2", "", "n", "n", "n", "n"]),
                            say=lambda *a: None, home=tmp, cameras=[], locate=boom)
    assert w.run()[0] == "--alerts"

# ---- CLI: drill propagates the right options; mesh options are stripped for setup drills
import optiquake
assert optiquake.strip_mesh(["--alerts", "--mesh-key", "abcdefgh", "--node-name", "x", "--lan-port"]) == ["--alerts", "--lan-port"]

print("MESH_SETUP_TEST_OK")
