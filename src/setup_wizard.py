"""Interactive first-time setup for OptiQuake Local alerts (Spanish/English).
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Asks for location, camera, phones and sensor mesh, runs a drill, and can make
the alerts start with Windows. Every question has a safe default, so pressing
Enter repeatedly gives a working setup.
"""
import json, os, re, secrets, shutil, socket, subprocess

import autostart, geo

# City-level coordinates; good enough to decide whether a quake can be felt.
CITIES = [
    ("Santo Domingo", 18.4861, -69.9312), ("Santiago de los Caballeros", 19.4517, -70.6970),
    ("La Romana", 18.4273, -68.9728), ("San Pedro de Macorís", 18.4539, -69.3086),
    ("Puerto Plata", 19.7934, -70.6884), ("La Vega", 19.2221, -70.5296),
    ("San Francisco de Macorís", 19.3008, -70.2526), ("Higüey", 18.6150, -68.7076),
    ("Punta Cana", 18.5601, -68.3725), ("San Cristóbal", 18.4167, -70.1000),
    ("Moca", 19.3941, -70.5251), ("Bonao", 18.9370, -70.4092), ("Baní", 18.2797, -70.3314),
    ("Samaná", 19.2056, -69.3361), ("Barahona", 18.2085, -71.1008),
    ("San Juan de la Maguana", 18.8053, -71.2297), ("Azua", 18.4532, -70.7349),
    ("Nagua", 19.3833, -69.8500), ("Montecristi", 19.8500, -71.6500),
    ("Mao", 19.5517, -71.0781), ("Cotuí", 19.0528, -70.1492), ("Dajabón", 19.5486, -71.7083),
]

T = {
    "es": {
        "hello": "\n=== OptiQuake Local · Configuración de alertas de sismo ===\n"
                 "Pulsa Enter para aceptar la opción entre [corchetes].\n",
        "loc": "\n1) ¿Dónde está este equipo?\n  1. Elegir ciudad de República Dominicana\n"
               "  2. Detectar por internet (aproximado)\n  3. Escribir latitud y longitud\n",
        "pick": "Opción", "city": "Número de ciudad", "lat": "Latitud", "lon": "Longitud",
        "place": "Nombre del lugar",
        "loc_ok": "Ubicación guardada: {name} ({lat:.4f}, {lon:.4f})",
        "loc_fail": "No se pudo detectar. Elige una ciudad.",
        "cam": "\n2) Cámara para detectar vibraciones:",
        "cam_none": "  0. Sin cámara (solo reportes oficiales por internet)",
        "cam_missing": "No se encontró FFmpeg o ninguna cámara: se usarán solo reportes oficiales.",
        "lan": "\n3) ¿Avisar a los teléfonos conectados al Wi-Fi de casa? (funciona sin internet)",
        "ntfy": "\n4) ¿Enviar también notificación al celular con la app ntfy? (necesita internet)",
        "ntfy_ok": "Instala la app ntfy en el celular y suscríbete al tema: {topic}",
        "mesh": "\n5) ¿Hay otros equipos con OptiQuake en la casa o el vecindario para confirmarse entre sí?",
        "mesh_key": "Clave compartida (Enter = crear una nueva; si otro equipo ya tiene una, escríbela)",
        "mesh_ok": "Clave de la red de sensores: {key}  <- usa la MISMA en los otros equipos",
        "node": "Nombre de este equipo",
        "drill": "\n6) ¿Hacer un simulacro ahora para probar sonido, voz y pantalla?",
        "auto": "\n7) ¿Iniciar las alertas automáticamente al encender Windows?",
        "auto_ok": "Listo: las alertas se iniciarán solas al entrar a Windows.",
        "done": "\nConfiguración guardada. Para iniciar ahora:\n  {cmd}\n",
        "yes": "s", "yn": "[S/n]", "ny": "[s/N]",
    },
    "en": {
        "hello": "\n=== OptiQuake Local · Earthquake alert setup ===\n"
                 "Press Enter to accept the option in [brackets].\n",
        "loc": "\n1) Where is this computer?\n  1. Pick a Dominican Republic city\n"
               "  2. Detect from the internet (approximate)\n  3. Type latitude and longitude\n",
        "pick": "Option", "city": "City number", "lat": "Latitude", "lon": "Longitude",
        "place": "Place name",
        "loc_ok": "Location saved: {name} ({lat:.4f}, {lon:.4f})",
        "loc_fail": "Could not detect it. Pick a city.",
        "cam": "\n2) Camera used to detect vibration:",
        "cam_none": "  0. No camera (official internet reports only)",
        "cam_missing": "FFmpeg or a camera was not found: official reports only.",
        "lan": "\n3) Alert phones connected to the home Wi-Fi? (works without internet)",
        "ntfy": "\n4) Also push to a phone with the ntfy app? (needs internet)",
        "ntfy_ok": "Install the ntfy app on the phone and subscribe to topic: {topic}",
        "mesh": "\n5) Are there other OptiQuake computers at home or nearby to confirm each other?",
        "mesh_key": "Shared key (Enter = create a new one; if another computer has one, type it)",
        "mesh_ok": "Sensor network key: {key}  <- use the SAME key on the other computers",
        "node": "Name of this computer",
        "drill": "\n6) Run a drill now to test sound, voice and screen?",
        "auto": "\n7) Start the alerts automatically when Windows starts?",
        "auto_ok": "Done: alerts will start when you sign in to Windows.",
        "done": "\nSettings saved. To start now:\n  {cmd}\n",
        "yes": "y", "yn": "[Y/n]", "ny": "[y/N]",
    },
}

def list_cameras(ffmpeg=None):
    """Video devices reported by FFmpeg's DirectShow input (Windows)."""
    ffmpeg = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg:
        return []
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow",
                            "-i", "dummy"], capture_output=True, text=True, timeout=20,
                           encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_dshow_devices(r.stderr)

def parse_dshow_devices(text):
    cams, section = [], None
    for line in text.splitlines():
        if "DirectShow video devices" in line:
            section = "video"; continue
        if "DirectShow audio devices" in line:
            section = "audio"; continue
        m = re.search(r'\]\s+"([^"]+)"(?:\s+\((video|audio|none)\))?\s*$', line)
        if m and "Alternative name" not in line:
            kind = m.group(2) or section
            if kind == "video" and m.group(1) not in cams:
                cams.append(m.group(1))
    return cams

class Wizard:
    def __init__(self, lang="es", ask=input, say=print, home=None, cameras=None,
                 locate=geo.locate_by_ip, startup=None, run_drill=None):
        self.t = T[lang]
        self.lang = lang
        self.ask, self.say = ask, say
        self.home = home or geo.config_dir()
        self.cameras = cameras
        self.locate = locate
        self.startup = startup
        self.run_drill = run_drill

    def _q(self, prompt, default=""):
        ans = self.ask(f"{prompt} [{default}]: " if default != "" else f"{prompt}: ").strip()
        return ans or str(default)

    def _yes(self, prompt, default=True):
        ans = self.ask(f"{prompt} {self.t['yn'] if default else self.t['ny']} ").strip().lower()
        return default if not ans else ans.startswith(self.t["yes"]) or ans.startswith("y")

    def _number(self, prompt, default, lo, hi, cast=int):
        while True:
            try:
                v = cast(self._q(prompt, default))
                if lo <= v <= hi:
                    return v
            except ValueError:
                pass

    def _city(self):
        for i, (name, _, _) in enumerate(CITIES, 1):
            self.say(f"  {i:2d}. {name}")
        i = self._number(self.t["city"], 1, 1, len(CITIES))
        name, lat, lon = CITIES[i - 1]
        return geo.Location(lat, lon, name, "manual")

    def location(self):
        self.say(self.t["loc"])
        choice = self._number(self.t["pick"], 1, 1, 3)
        if choice == 2:
            try:
                loc = self.locate()
            except Exception:
                self.say(self.t["loc_fail"])
                loc = self._city()
        elif choice == 3:
            lat = self._number(self.t["lat"], "", -90, 90, float)
            lon = self._number(self.t["lon"], "", -180, 180, float)
            loc = geo.Location(lat, lon, self._q(self.t["place"], ""), "manual")
        else:
            loc = self._city()
        geo.save_location(loc, pathlib_join(self.home, "location.json"))
        self.say(self.t["loc_ok"].format(name=loc.name or "?", lat=loc.lat, lon=loc.lon))
        return loc

    def run(self):
        self.say(self.t["hello"])
        loc = self.location()
        args = ["--alerts", "--lang", self.lang, "--lat", f"{loc.lat}", "--lon", f"{loc.lon}"]
        if loc.name:
            args += ["--place", loc.name]

        self.say(self.t["cam"])
        cams = list_cameras() if self.cameras is None else self.cameras
        if cams:
            self.say(self.t["cam_none"])
            for i, c in enumerate(cams, 1):
                self.say(f"  {i}. {c}")
            i = self._number(self.t["pick"], 1, 0, len(cams))
            args += ["--camera", cams[i - 1]] if i else ["--no-camera"]
        else:
            self.say(self.t["cam_missing"])
            args.append("--no-camera")

        if self._yes(self.t["lan"], True):
            args.append("--lan-port")
        if self._yes(self.t["ntfy"], False):
            topic = "optiquake-" + secrets.token_hex(8)
            args += ["--ntfy-topic", topic]
            self.say(self.t["ntfy_ok"].format(topic=topic))
        if self._yes(self.t["mesh"], False):
            key = self._q(self.t["mesh_key"], "") or secrets.token_urlsafe(12)
            node = self._q(self.t["node"], socket.gethostname())
            args += ["--mesh-key", key, "--node-name", node]
            self.say(self.t["mesh_ok"].format(key=key))

        settings = pathlib_join(self.home, "settings.json")
        os.makedirs(os.path.dirname(settings), exist_ok=True)
        with open(settings, "w", encoding="utf-8") as f:
            json.dump({"args": args}, f, ensure_ascii=False, indent=2)

        if self._yes(self.t["drill"], True) and self.run_drill:
            self.run_drill(args)
        if self._yes(self.t["auto"], True):
            autostart.install(args, self.home, startup=self.startup)
            self.say(self.t["auto_ok"])
        self.say(self.t["done"].format(cmd="python src\\optiquake.py --from-settings"))
        return args

def pathlib_join(*parts):
    return os.path.join(*[str(p) for p in parts])

def load_settings(home=None):
    path = pathlib_join(home or geo.config_dir(), "settings.json")
    try:
        with open(path, encoding="utf-8") as f:
            return list(json.load(f)["args"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
