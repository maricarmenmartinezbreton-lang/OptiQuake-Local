"""Location handling and simple seismic distance estimates for OptiQuake Local.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

The radius formulas below are coarse, conservative rules of thumb used only to
decide whether an official earthquake report is relevant to the user. They are
not a ground-motion model and must not be presented as a shaking forecast.
"""
import json, math, os, pathlib, urllib.request
from dataclasses import dataclass, asdict

EARTH_RADIUS_KM = 6371.0
S_WAVE_KM_S = 3.5  # typical crustal S-wave speed; strong shaking arrives with the S wave

@dataclass(frozen=True)
class Location:
    lat: float
    lon: float
    name: str = ""
    source: str = "manual"

    def __post_init__(self):
        if not (-90 <= self.lat <= 90 and -180 <= self.lon <= 180):
            raise ValueError(f"Invalid coordinates: {self.lat}, {self.lon}")

def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, a)))

def felt_radius_km(mag):
    """Rough distance within which an event is commonly felt (about MMI III).
    M3 ~ 25 km, M5 ~ 145 km, M7 ~ 800 km."""
    return 10 ** (0.375 * mag + 0.28)

def strong_radius_km(mag):
    """Rough distance within which strong shaking (about MMI VI+) is possible.
    M5 ~ 15 km, M6 ~ 38 km, M7 ~ 95 km, M8 ~ 240 km."""
    return 10 ** (0.4 * mag - 0.82)

def s_wave_eta_s(distance_km, depth_km, seconds_since_origin):
    """Seconds until the S wave reaches the user (negative: already passed)."""
    hypo = math.hypot(distance_km, max(depth_km, 0.0))
    return hypo / S_WAVE_KM_S - seconds_since_origin

def config_dir():
    base = os.environ.get("OPTIQUAKE_HOME")
    if base:
        return pathlib.Path(base)
    root = os.environ.get("APPDATA") or pathlib.Path.home()
    return pathlib.Path(root) / "OptiQuake"

def save_location(loc, path=None):
    path = pathlib.Path(path or config_dir() / "location.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(loc), ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def load_location(path=None):
    path = pathlib.Path(path or config_dir() / "location.json")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Location(float(data["lat"]), float(data["lon"]),
                        data.get("name", ""), "saved")
    except (OSError, ValueError, KeyError, TypeError):
        return None

def locate_by_ip(timeout=10):
    """Approximate city-level location from the public IP (opt-in, needs internet)."""
    req = urllib.request.Request("https://ipwho.is/", headers={"User-Agent": "optiquake-local"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    if not data.get("success", True):
        raise ValueError(data.get("message", "IP location failed"))
    name = ", ".join(x for x in (data.get("city"), data.get("country")) if x)
    return Location(float(data["latitude"]), float(data["longitude"]), name, "ip")
