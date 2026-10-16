"""Official earthquake feeds (USGS, EMSC, GFZ GEOFON) for OptiQuake Local.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Official catalogues usually publish an event 1-20 minutes after it happens, so
these feeds confirm and describe earthquakes; the camera sensor is what reacts
in real time. Every network failure is tolerated: the monitor just reports
that it is offline and keeps retrying.
"""
import json, re, threading, time, urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from geo import haversine_km

USER_AGENT = "optiquake-local (+https://github.com/maricarmenmartinezbreton-lang/OptiQuake-Local)"

@dataclass(frozen=True)
class Quake:
    source: str
    id: str
    time: float  # origin time, unix seconds UTC
    lat: float
    lon: float
    depth_km: float
    mag: float
    place: str = ""
    tsunami: bool = False
    url: str = ""

def _iso_to_unix(text):
    # Feeds use 1-6 fractional digits and a trailing Z; Python 3.10 accepts neither.
    text = text.strip().replace("Z", "+00:00")
    text = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), text, count=1)
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()

def parse_usgs(data):
    out = []
    for f in data.get("features", []):
        p, c = f.get("properties") or {}, (f.get("geometry") or {}).get("coordinates") or []
        if p.get("mag") is None or len(c) < 2 or p.get("time") is None:
            continue
        if p.get("type", "earthquake") != "earthquake":  # quarry blast, explosion...
            continue
        out.append(Quake("USGS", str(f.get("id")), p["time"] / 1000.0, float(c[1]), float(c[0]),
                         float(c[2]) if len(c) > 2 and c[2] is not None else 10.0,
                         float(p["mag"]), p.get("place") or "",
                         bool(p.get("tsunami")), p.get("url") or ""))
    return out

def parse_emsc(data):
    out = []
    for f in data.get("features", []):
        p = f.get("properties") or {}
        if p.get("mag") is None or p.get("lat") is None or not p.get("time"):
            continue
        uid = str(p.get("unid") or f.get("id"))
        out.append(Quake("EMSC", uid, _iso_to_unix(p["time"]), float(p["lat"]), float(p["lon"]),
                         abs(float(p.get("depth") or 10.0)), float(p["mag"]),
                         (p.get("flynn_region") or "").title(), False,
                         f"https://www.seismicportal.eu/eventdetails.html?unid={uid}"))
    return out

def parse_fdsn_text(text, source):
    out = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        cols = line.split("|")
        if len(cols) < 13 or not cols[10].strip():
            continue
        if len(cols) > 13 and cols[13].strip() not in ("", "earthquake"):
            continue  # "not existing" (deleted), explosion, quarry blast...
        try:
            out.append(Quake(source, cols[0], _iso_to_unix(cols[1]), float(cols[2]),
                             float(cols[3]), float(cols[4] or 10.0), float(cols[10]),
                             cols[12].strip()))
        except ValueError:
            continue
    return out

def _get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def _since(minutes):
    t = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return t.strftime("%Y-%m-%dT%H:%M:%S")

def fetch_usgs(timeout=10):
    return parse_usgs(json.loads(_get(
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson", timeout)))

def fetch_emsc(timeout=10, minutes=60):
    return parse_emsc(json.loads(_get(
        "https://www.seismicportal.eu/fdsnws/event/1/query?format=json&orderby=time"
        f"&limit=200&starttime={_since(minutes)}", timeout)))

def fetch_gfz(timeout=10, minutes=60):
    return parse_fdsn_text(_get(
        "https://geofon.gfz.de/fdsnws/event/1/query?format=text&orderby=time"
        f"&limit=200&starttime={_since(minutes)}", timeout), "GFZ")

FEEDS = {"USGS": fetch_usgs, "EMSC": fetch_emsc, "GFZ": fetch_gfz}

def same_event(a, b, max_dt=90.0, max_km=150.0):
    return (abs(a.time - b.time) <= max_dt
            and haversine_km(a.lat, a.lon, b.lat, b.lon) <= max_km)

class FeedMonitor:
    """Polls every feed in the background and calls on_quake(quake, confirmations)
    once per new physical event (the same quake reported by several agencies is
    merged; later reports only increase the confirmation count)."""

    def __init__(self, on_quake, on_status=None, feeds=None, interval=30.0,
                 max_age_s=1800.0, timeout=10.0, clock=time.time):
        self.on_quake = on_quake
        self.on_status = on_status or (lambda status: None)
        self.feeds = dict(feeds if feeds is not None else FEEDS)
        self.interval = interval
        self.max_age_s = max_age_s
        self.timeout = timeout
        self.clock = clock
        self.events = []  # list of [quake, set(sources)]
        self.seen_ids = {}  # (source, id) -> origin time
        self.online = None
        self._stop = threading.Event()
        self._thread = None

    def poll_once(self):
        ok, failures, fresh = [], {}, []
        for name, fetch in self.feeds.items():
            try:
                fresh.extend(fetch(timeout=self.timeout))
                ok.append(name)
            except Exception as exc:  # network, HTTP or parse errors
                failures[name] = str(exc)[:200]
        online = bool(ok)
        if online != self.online:
            self.online = online
            self.on_status({"feeds_online": online, "ok": ok, "failed": failures})
        now = self.clock()
        self.events = [e for e in self.events if now - e[0].time <= self.max_age_s * 2]
        self.seen_ids = {k: t for k, t in self.seen_ids.items() if now - t <= self.max_age_s * 2}
        for q in sorted(fresh, key=lambda q: q.time):
            key = (q.source, q.id)
            if key in self.seen_ids or now - q.time > self.max_age_s:
                continue
            self.seen_ids[key] = q.time
            match = next((e for e in self.events if same_event(e[0], q)), None)
            if match:
                match[1].add(q.source)
                continue
            self.events.append([q, {q.source}])
            self.on_quake(q, len(self.events[-1][1]))
        return online

    def _loop(self):
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self.interval)

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True, name="feed-monitor")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.timeout + 1)
