import json, os, pathlib, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

import geo, quake_alerts as qa, quake_feeds as qf
from plugin_api import VibrationEvent

# ---- parsers (real samples from each agency)
usgs = qf.parse_usgs(json.loads((FIX / "usgs.json").read_text(encoding="utf-8")))
assert len(usgs) == 1, "events without magnitude are skipped"
q = usgs[0]
assert (q.source, q.id, q.mag, q.lat, q.lon, q.depth_km) == ("USGS", "pr71234567", 4.6, 20.02, -70.69, 15.0)
assert q.time == 1791299700.0 and "Puerto Plata" in q.place

emsc = qf.parse_emsc(json.loads((FIX / "emsc.json").read_text(encoding="utf-8")))
assert [e.id for e in emsc] == ["20260817_0000165", "20260817_0000166"]
assert emsc[0].depth_km == 30.0 and emsc[0].lat == -8.96 and emsc[0].place == "Flores Region, Indonesia"
assert emsc[0].time == datetime(2026, 8, 17, 4, 54, 50, tzinfo=timezone.utc).timestamp()

gfz = qf.parse_fdsn_text((FIX / "gfz.txt").read_text(encoding="utf-8"), "GFZ")
assert [g.mag for g in gfz] == [5.1, 5.78, 5.14] and gfz[1].place == "Kuril Islands"
extra = "x1|2026-10-06T10:00:00|1|1|5|||GFZ|x1|mb|4.0||Somewhere|not existing\n" \
        "x2|2026-10-06T10:00:00|1|1|5|||GFZ|x2|mb|4.0||Somewhere|quarry blast\n"
assert qf.parse_fdsn_text(extra, "GFZ") == []
blast = {"features": [{"id": "b", "properties": {"mag": 2.1, "time": 1, "type": "quarry blast"},
                       "geometry": {"coordinates": [-70, 19, 0]}}]}
assert qf.parse_usgs(blast) == []
assert abs(gfz[0].time - datetime(2026, 10, 6, 16, 53, 11, 970000, tzinfo=timezone.utc).timestamp()) < 1e-6

# ---- geography
SD = geo.Location(18.4861, -69.9312, "Santo Domingo")
MIAMI = geo.Location(25.7617, -80.1918, "Miami")
NYC = geo.Location(40.7128, -74.0060, "New York")
assert 1250 < geo.haversine_km(SD.lat, SD.lon, MIAMI.lat, MIAMI.lon) < 1350
assert 20 < geo.felt_radius_km(3) < 30 and 120 < geo.felt_radius_km(5) < 170
assert 30 < geo.strong_radius_km(6) < 45
assert geo.s_wave_eta_s(350, 0, 0) == 100.0

def quake(mag, lat=19.0, lon=-70.0, depth=15.0, age=10.0, source="USGS", id="x", tsunami=False):
    return qf.Quake(source, id, NOW - age, lat, lon, depth, mag, "Dominican Republic", tsunami)

NOW = 1_800_000_000.0
# Same RD quake: strong in Santo Domingo, irrelevant in New York.
a = qa.assess(quake(6.5), SD, NOW)
assert a.level == qa.STRONG and a.distance_km < 100
assert qa.assess(quake(6.5), NYC, NOW).level == qa.INFO
assert qa.assess(quake(4.0), SD, NOW).level == qa.FELT
assert qa.assess(quake(7.8, lat=19.8, lon=-69.0), MIAMI, NOW).level == qa.FELT
# Tsunami text only for large shallow quakes near the user.
assert qa.assess(quake(7.5, lat=19.5, lon=-69.5), SD, NOW).tsunami
assert not qa.assess(quake(7.5, depth=300), SD, NOW).tsunami
assert not qa.assess(quake(5.0), SD, NOW).tsunami

# ---- messages: protective actions while shaking, evacuate calmly afterwards
t = qa.TEXT["es"]
fresh = qa.build_quake_alert(quake(6.5), qa.assess(quake(6.5), SD, NOW))
assert fresh.title == "ALERTA DE SISMO"
assert t["during"] in fresh.lines and t["after"] in fresh.lines
assert fresh.lines.index(t["during"]) < fresh.lines.index(t["after"])
old = qa.build_quake_alert(quake(6.5, age=600), qa.assess(quake(6.5, age=600), SD, NOW))
assert t["during"] not in old.lines and t["after"] in old.lines and any("hace 10 min" in x for x in old.lines)
far = quake(7.9, lat=10.0, lon=-62.0, age=30)  # ~1300 km away: S wave not there yet
fa = qa.assess(far, SD, NOW)
assert fa.eta_s > 0 and any("segundos" in x for x in qa.build_quake_alert(far, fa).lines)
assert qa.build_local_alert("en").lines[1] == qa.TEXT["en"]["during"]
assert qa.build_local_alert(drill=True).lines[0].startswith("SIMULACRO")
assert set(qa.TEXT["es"]) == set(qa.TEXT["en"])

# ---- feed monitor: merge agencies, ignore old reports, survive outages
calls = []
feeds_up = {"ok": True}
def usgs_feed(timeout):
    if not feeds_up["ok"]:
        raise OSError("network down")
    return [quake(5.0, id="u1"), quake(6.0, age=7200, id="old")]
def emsc_feed(timeout):
    if not feeds_up["ok"]:
        raise OSError("network down")
    return [quake(5.1, lat=19.1, age=30, source="EMSC", id="e1")]
statuses = []
mon = qf.FeedMonitor(lambda q, n: calls.append(q.id), statuses.append,
                     feeds={"USGS": usgs_feed, "EMSC": emsc_feed}, clock=lambda: NOW)
assert mon.poll_once() is True
assert calls == ["e1"] or calls == ["u1"], calls  # one alert for one physical quake
assert mon.events[0][1] == {"USGS", "EMSC"}
mon.poll_once()
assert len(calls) == 1, "no repeat alerts"
feeds_up["ok"] = False
assert mon.poll_once() is False and statuses[-1]["feeds_online"] is False
feeds_up["ok"] = True
mon.poll_once()
assert statuses[-1]["feeds_online"] is True and len(calls) == 1

# ---- alert center
class Fake:
    name = "fake"
    def __init__(self): self.got = []
    def send(self, alert): self.got.append(alert)
clock = {"t": NOW}
fake = Fake()
logs = []
center = qa.AlertCenter(SD, [fake], clock=lambda: clock["t"], log=logs.append)
ev = VibrationEvent(t=1.0, score=5.0, baseline=0.1, robust_z=30.0)
center.on_event(ev); center.on_event(ev)
assert len(fake.got) == 1 and fake.got[0].level == qa.LOCAL, "camera alerts are rate-limited"
clock["t"] += 61
center.on_event(ev)
assert len(fake.got) == 2
center.on_quake(quake(6.5, age=40))
assert fake.got[-1].level == qa.STRONG and "confirmado" in fake.got[-1].lines[0]
center.on_quake(quake(6.5, lat=40.7, lon=-74.0))  # far away: logged only
assert len(fake.got) == 3 and logs[-1]["level"] == qa.INFO
class Broken:
    name = "broken"
    def send(self, alert): raise RuntimeError("speaker unplugged")
c2 = qa.AlertCenter(SD, [Broken(), fake], log=logs.append)
c2.drill()
assert fake.got[-1].drill and logs[-1]["alert_channel_error"] == "broken"
nolog = qa.AlertCenter(None, [fake], log=logs.append)
nolog.on_quake(quake(6.5))
assert len(fake.got) == 4 and logs[-1]["note"] == "no location configured"

# ---- home Wi-Fi page (no internet needed)
lan = qa.LanChannel(port=0, host="127.0.0.1")
port = lan.server.server_address[1]
get = lambda p: urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=5).read().decode()
assert "Activar alertas" in get("/")
assert json.loads(get("/state"))["seq"] == 0
lan.set_status({"feeds_online": False})
lan.send(qa.build_local_alert())
st = json.loads(get("/state"))
assert st["seq"] == 1 and st["alert"]["title"] == "ALERTA DE SISMO" and st["feeds_online"] is False
lan.close()

# ---- location persistence (offline reuse)
with tempfile.TemporaryDirectory() as tmp:
    path = geo.save_location(SD, pathlib.Path(tmp) / "loc.json")
    back = geo.load_location(path)
    assert (back.lat, back.lon, back.name, back.source) == (SD.lat, SD.lon, "Santo Domingo", "saved")
    assert geo.load_location(pathlib.Path(tmp) / "missing.json") is None

    # ---- CLI drill end to end (all noisy channels disabled)
    env = dict(os.environ, OPTIQUAKE_HOME=tmp, PYTHONIOENCODING="utf-8")
    cli = [sys.executable, str(ROOT / "src" / "optiquake.py")]
    r = subprocess.run(cli + ["--alerts", "--drill", "--no-sound", "--no-voice", "--no-window",
                              "--lat", "18.4861", "--lon", "-69.9312", "--place", "Santo Domingo"],
                       capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)
    assert r.returncode == 0, r.stderr
    assert '"drill": true' in r.stdout and "SIMULACRO" in r.stderr
    assert json.loads((pathlib.Path(tmp) / "location.json").read_text(encoding="utf-8"))["name"] == "Santo Domingo"
    for bad in (["--drill"], ["--alerts", "--no-camera", "--no-feeds"],
                ["--alerts", "--feed-interval", "1"]):
        r = subprocess.run(cli + bad, capture_output=True, text=True, timeout=30, env=env)
        assert r.returncode == 2, (bad, r.stderr)

print("ALERTS_TEST_OK")
