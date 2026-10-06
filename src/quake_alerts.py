"""Earthquake alerts for OptiQuake Local: relevance by location, protective-action
messages, and alert channels (console, siren, voice, full-screen window, phone).
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Experimental and informational. It does not replace official early-warning
systems or instructions from local civil-protection authorities.
"""
import json, platform, subprocess, sys, threading, time, urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from geo import felt_radius_km, haversine_km, s_wave_eta_s, strong_radius_km

PLUGIN_API_VERSION = "1"

INFO, FELT, STRONG = "info", "felt", "strong"
LOCAL = "local"  # camera-only detection

TEXT = {
    "es": {
        "title": "ALERTA DE SISMO",
        "drill": "SIMULACRO · SIMULACRO · SIMULACRO",
        "during": "AGÁCHATE · CÚBRETE · SUJÉTATE",
        "during_detail": "Protégete bajo una mesa firme o junto a una pared interior. "
                         "Aléjate de ventanas, espejos y objetos que puedan caer. No uses ascensores.",
        "after": "Cuando pare el temblor: sal despacio, sin correr ni empujar, por las escaleras, "
                 "y busca un lugar seguro y abierto, lejos de edificios, postes y cables. Espera réplicas.",
        "tsunami": "PELIGRO DE TSUNAMI: si estás cerca de la costa, en cuanto pare el temblor "
                   "aléjate hacia una zona alta. No esperes otra alerta.",
        "local": "Vibración fuerte detectada por el sensor de la cámara (sin confirmar).",
        "local_confirmed": "Sismo confirmado por {sources}: M{mag:.1f}, {place}, a {dist:.0f} km de ti.",
        "quake": "Sismo M{mag:.1f} · {place} · a {dist:.0f} km de ti · fuente: {source}",
        "eta": "El temblor fuerte puede llegar en unos {eta:.0f} segundos.",
        "ago": "Ocurrió hace {mins:.0f} min.",
        "strong": "Posible sacudida fuerte en tu zona.",
        "felt": "Puede sentirse en tu zona.",
        "offline": "Sin internet: alertas solo por el sensor de la cámara.",
        "offline_no_camera": "Sin internet y sin cámara: no hay alertas hasta que vuelva la conexión.",
        "footer": "Aviso experimental de OptiQuake Local. Sigue siempre las indicaciones "
                  "de las autoridades (Defensa Civil, COE, 911).",
        "ok": "ENTENDIDO",
    },
    "en": {
        "title": "EARTHQUAKE ALERT",
        "drill": "DRILL · DRILL · DRILL",
        "during": "DROP · COVER · HOLD ON",
        "during_detail": "Get under a sturdy table or next to an interior wall. "
                         "Stay away from windows, mirrors and things that can fall. Do not use elevators.",
        "after": "When the shaking stops: leave calmly, without running or pushing, by the stairs, "
                 "and go to a safe open area away from buildings, poles and wires. Expect aftershocks.",
        "tsunami": "TSUNAMI DANGER: if you are near the coast, move to high ground as soon as "
                   "the shaking stops. Do not wait for another alert.",
        "local": "Strong vibration detected by the camera sensor (unconfirmed).",
        "local_confirmed": "Earthquake confirmed by {sources}: M{mag:.1f}, {place}, {dist:.0f} km from you.",
        "quake": "M{mag:.1f} earthquake · {place} · {dist:.0f} km from you · source: {source}",
        "eta": "Strong shaking may arrive in about {eta:.0f} seconds.",
        "ago": "It happened {mins:.0f} min ago.",
        "strong": "Strong shaking possible in your area.",
        "felt": "It may be felt in your area.",
        "offline": "No internet: alerts from the camera sensor only.",
        "offline_no_camera": "No internet and no camera: no alerts until the connection returns.",
        "footer": "Experimental OptiQuake Local alert. Always follow official instructions "
                  "from local authorities and emergency services.",
        "ok": "OK",
    },
}

@dataclass
class Assessment:
    level: str
    distance_km: float
    eta_s: float
    age_s: float
    tsunami: bool

def assess(quake, location, now=None):
    """Decide how relevant an official report is for the user's location."""
    now = time.time() if now is None else now
    dist = haversine_km(location.lat, location.lon, quake.lat, quake.lon)
    age = max(0.0, now - quake.time)
    if dist <= strong_radius_km(quake.mag):
        level = STRONG
    elif dist <= felt_radius_km(quake.mag):
        level = FELT
    else:
        level = INFO
    tsunami = level != INFO and (quake.tsunami or (
        quake.mag >= 7.0 and quake.depth_km <= 100 and dist <= 1000))
    return Assessment(level, dist, s_wave_eta_s(dist, quake.depth_km, age), age, tsunami)

@dataclass
class Alert:
    level: str
    title: str
    lines: list = field(default_factory=list)
    lang: str = "es"
    drill: bool = False

    def to_dict(self):
        return {"alert": self.level, "title": self.title, "lines": self.lines, "drill": self.drill}

def build_quake_alert(quake, a, lang="es", confirmations=1):
    t = TEXT[lang]
    lines = [t["quake"].format(mag=quake.mag, place=quake.place or "?", dist=a.distance_km,
                               source=quake.source),
             t["strong"] if a.level == STRONG else t["felt"]]
    shaking_now = a.eta_s > 0 or a.age_s < 120
    if a.eta_s > 0:
        lines.append(t["eta"].format(eta=a.eta_s))
    elif a.age_s >= 60:
        lines.append(t["ago"].format(mins=a.age_s / 60))
    if shaking_now:
        lines += [t["during"], t["during_detail"]]
    lines.append(t["after"])
    if a.tsunami:
        lines.append(t["tsunami"])
    lines.append(t["footer"])
    return Alert(a.level, t["title"], lines, lang)

def build_local_alert(lang="es", drill=False):
    t = TEXT[lang]
    lines = ([t["drill"]] if drill else []) + [t["local"], t["during"], t["during_detail"],
                                              t["after"], t["footer"]]
    return Alert(STRONG if drill else LOCAL, t["title"], lines, lang, drill)

# ----------------------------------------------------------------- channels

def _is_windows():
    return platform.system() == "Windows"

class ConsoleChannel:
    name = "console"
    def send(self, alert):
        bar = "!" * 60
        out = [bar, f"  {alert.title}", *[f"  {x}" for x in alert.lines], bar]
        red = "\033[1;97;41m" if sys.stdout.isatty() else ""
        reset = "\033[0m" if red else ""
        print(red + "\n".join(out) + reset, file=sys.stderr, flush=True)

class SirenChannel:
    """Loud alternating tone through the default audio device (built-in speakers,
    Bluetooth speaker or headphones). On Windows it first raises the system
    volume to the maximum. Uses the terminal bell on other systems."""
    name = "siren"
    VOLUME_UP = ("$w=New-Object -ComObject WScript.Shell;"
                 "1..50|ForEach-Object{$w.SendKeys([char]175)}")
    def __init__(self, seconds=20, boost_volume=True):
        self.seconds = seconds
        self.boost_volume = boost_volume
    def _play(self, seconds):
        end = time.time() + seconds
        if _is_windows():
            import winsound
            if self.boost_volume:
                try:
                    subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                                    "-Command", self.VOLUME_UP], timeout=5,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            while time.time() < end:
                winsound.Beep(1400, 350)
                winsound.Beep(900, 350)
        else:
            while time.time() < end:
                sys.stderr.write("\a"); sys.stderr.flush(); time.sleep(0.5)
    def send(self, alert):
        secs = self.seconds if alert.level in (STRONG, LOCAL) else max(3, self.seconds // 4)
        threading.Thread(target=self._play, args=(secs,), daemon=True).start()

class VoiceChannel:
    """Spoken alert with the offline Windows speech engine (say/spd-say elsewhere)."""
    name = "voice"
    PS = ("Add-Type -AssemblyName System.Speech;"
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.Volume=100;$t=[Console]::In.ReadToEnd();$s.Speak($t);$s.Speak($t)")
    def send(self, alert):
        text = ". ".join([alert.title] + [x for x in alert.lines[:4]])
        if _is_windows():
            cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command", self.PS]
        else:
            import shutil
            exe = shutil.which("say") or shutil.which("spd-say")
            if not exe:
                return
            cmd = [exe, text]
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            if _is_windows():
                p.stdin.write(text.encode("utf-8")); p.stdin.close()
        except OSError:
            pass

class WindowChannel:
    """Full-screen, always-on-top flashing window (separate process, tkinter)."""
    name = "window"
    def send(self, alert):
        script = Path(__file__).with_name("alert_window.py")
        payload = dict(alert.to_dict(), ok=TEXT[alert.lang]["ok"])
        try:
            p = subprocess.Popen([sys.executable, str(script)], stdin=subprocess.PIPE)
            p.stdin.write(json.dumps(payload).encode("utf-8")); p.stdin.close()
        except OSError:
            pass

class NtfyChannel:
    """Push to a phone through ntfy (https://ntfy.sh). Urgent priority makes the
    phone ring and vibrate. Needs internet and the ntfy app subscribed to the topic."""
    name = "ntfy"
    def __init__(self, topic, server="https://ntfy.sh"):
        self.topic, self.server = topic, server.rstrip("/")
    def send(self, alert):
        body = json.dumps({
            "topic": self.topic, "title": alert.title, "message": "\n".join(alert.lines),
            "priority": 5 if alert.level in (STRONG, LOCAL) else 4,
            "tags": ["rotating_light", "warning"],
        }).encode("utf-8")
        req = urllib.request.Request(self.server, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        def post():
            try:
                urllib.request.urlopen(req, timeout=10).close()
            except Exception as exc:
                print(json.dumps({"alert_channel_error": "ntfy", "detail": str(exc)[:200]}),
                      flush=True)
        threading.Thread(target=post, daemon=True).start()

# --------------------------------------------------------------- coordinator

class AlertCenter:
    """Plugin that turns camera events and official reports into alerts.

    - Camera event: immediate local alert (works offline), rate-limited.
    - Official report that may be felt at the user's location: alert with
      distance, magnitude and protective actions. Reports too far away are
      only logged.
    - Official report shortly after a camera event: confirmation message.
    """
    name = "alert-center"
    version = "0.1.0"
    api_version = PLUGIN_API_VERSION

    def __init__(self, location, channels, lang="es", monitor=None,
                 local_cooldown_s=60.0, confirm_window_s=180.0, clock=time.time,
                 log=None, camera=True):
        self.location = location
        self.channels = list(channels)
        self.lang = lang
        self.monitor = monitor
        self.local_cooldown_s = local_cooldown_s
        self.confirm_window_s = confirm_window_s
        self.clock = clock
        self.log = log or (lambda record: print(json.dumps(record, ensure_ascii=False), flush=True))
        self.camera = camera
        self.last_local = None
        self.lock = threading.Lock()

    def dispatch(self, alert):
        self.log(alert.to_dict())
        for ch in self.channels:
            try:
                ch.send(alert)
            except Exception as exc:
                self.log({"alert_channel_error": ch.name, "detail": str(exc)[:200]})

    def on_start(self, context):
        if self.monitor:
            self.monitor.start()

    def on_stop(self):
        if self.monitor:
            self.monitor.stop()
        for ch in self.channels:
            if hasattr(ch, "close"):
                ch.close()

    def on_event(self, event):
        now = self.clock()
        with self.lock:
            if self.last_local is not None and now - self.last_local < self.local_cooldown_s:
                return
            self.last_local = now
        self.dispatch(build_local_alert(self.lang))

    def on_status(self, status):
        self.log(status)
        for ch in self.channels:
            if hasattr(ch, "set_status"):
                ch.set_status(status)
        if status.get("feeds_online") is False:
            self.log({"notice": TEXT[self.lang]["offline" if self.camera else "offline_no_camera"]})

    def on_quake(self, quake, confirmations=1):
        if self.location is None:
            self.log({"quake": quake.__dict__, "note": "no location configured"})
            return
        a = assess(quake, self.location, self.clock())
        record = {"quake": quake.__dict__, "level": a.level,
                  "distance_km": round(a.distance_km, 1), "eta_s": round(a.eta_s, 1)}
        self.log(record)
        if a.level == INFO:
            return
        with self.lock:
            camera_saw_it = (self.last_local is not None and
                             abs(quake.time - self.last_local) <= self.confirm_window_s)
        alert = build_quake_alert(quake, a, self.lang, confirmations)
        if camera_saw_it:
            alert.lines.insert(0, TEXT[self.lang]["local_confirmed"].format(
                sources=quake.source, mag=quake.mag, place=quake.place or "?",
                dist=a.distance_km))
        self.dispatch(alert)

    def drill(self):
        self.dispatch(build_local_alert(self.lang, drill=True))

# ------------------------------------------------------------- home network

LAN_PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OptiQuake · Alertas</title><style>
body{margin:0;font-family:system-ui,sans-serif;background:#111;color:#fff;text-align:center}
#idle{padding:24px}#idle button{font-size:24px;padding:18px 28px;border-radius:12px;border:0;
background:#c00000;color:#fff;font-weight:700}
#alert{display:none;position:fixed;inset:0;padding:20px;overflow:auto;background:#c00000}
#alert h1{font-size:44px;margin:12px 0}#alert p{font-size:20px;margin:10px 0}
#alert p.big{font-size:30px;font-weight:800}#ok{font-size:24px;padding:14px 30px;margin:20px}
.flash{background:#fff!important;color:#c00000}small{opacity:.7}</style></head><body>
<div id="idle"><h2>OptiQuake Local</h2><p id="st">Conectando…</p>
<button id="arm">Activar alertas en este teléfono</button>
<p><small>Deja esta página abierta, con la pantalla encendida y el volumen alto
(idealmente cargando). Funciona por el Wi-Fi de casa aunque no haya internet.</small></p></div>
<div id="alert"><h1 id="t"></h1><div id="l"></div><button id="ok">ENTENDIDO</button></div>
<script>
let last=null,armed=false,ctx=null,osc=null,timer=null,flash=null;
const $=id=>document.getElementById(id);
$('arm').onclick=()=>{armed=true;ctx=new(window.AudioContext||window.webkitAudioContext)();
 $('arm').textContent='Alertas activadas ✓';$('arm').disabled=true;
 if(navigator.vibrate)navigator.vibrate(200)};
function siren(sec){if(!ctx)return;osc=ctx.createOscillator();const g=ctx.createGain();
 g.gain.value=1;osc.connect(g);g.connect(ctx.destination);osc.type='square';osc.start();
 let hi=false;timer=setInterval(()=>{hi=!hi;osc.frequency.value=hi?1400:900},350);
 setTimeout(stop,sec*1000)}
function stop(){try{osc&&osc.stop()}catch(e){}clearInterval(timer);clearInterval(flash);
 if(navigator.vibrate)navigator.vibrate(0)}
function show(a){$('t').textContent=a.title;$('l').innerHTML='';
 a.lines.forEach(x=>{const p=document.createElement('p');p.textContent=x;
  if(x===x.toUpperCase()&&x.length<60)p.className='big';$('l').appendChild(p)});
 $('alert').style.display='block';flash=setInterval(()=>$('alert').classList.toggle('flash'),500);
 if(navigator.vibrate)navigator.vibrate(Array(30).fill([800,300]).flat());
 siren(30);if(window.speechSynthesis){const u=new SpeechSynthesisUtterance(
  [a.title].concat(a.lines.slice(0,4)).join('. '));u.lang=a.lang||'es';speechSynthesis.speak(u)}}
$('ok').onclick=()=>{stop();$('alert').style.display='none'};
async function poll(){try{const r=await fetch('state',{cache:'no-store'});const s=await r.json();
 $('st').textContent='Conectado al PC ✓ '+(s.feeds_online===false?'(sin internet: solo cámara)':'');
 if(last!==null&&s.seq!==last&&s.alert)show(s.alert);last=s.seq}
 catch(e){$('st').textContent='Sin conexión con el PC…'}setTimeout(poll,1000)}
poll();
</script></body></html>"""

def lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.168.0.1", 9))  # no packet is sent; picks the LAN interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"

class LanChannel:
    """Serves an alert page on the home network. Phones and tablets on the same
    Wi-Fi open it once; on an alert it flashes, plays a siren, vibrates (Android)
    and speaks. Needs no internet, only the local router. Read-only: the page can
    see the latest alert, nothing else."""
    name = "lan"

    def __init__(self, port=8765, host="0.0.0.0"):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self.state = {"seq": 0, "alert": None, "feeds_online": None}
        channel = self
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path.split("?")[0] == "/state":
                    body, ctype = json.dumps(channel.state).encode(), "application/json"
                elif self.path.split("?")[0] in ("/", "/index.html"):
                    body, ctype = LAN_PAGE.encode("utf-8"), "text/html; charset=utf-8"
                else:
                    self.send_error(404); return
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *a):
                pass
        self.server = ThreadingHTTPServer((host, port), Handler)
        self.url = f"http://{lan_ip()}:{self.server.server_address[1]}/"
        threading.Thread(target=self.server.serve_forever, daemon=True, name="lan-alerts").start()

    def set_status(self, status):
        if "feeds_online" in status:
            self.state = dict(self.state, feeds_online=status["feeds_online"])

    def send(self, alert):
        self.state = dict(self.state, seq=self.state["seq"] + 1,
                          alert=dict(alert.to_dict(), lang=alert.lang))

    def close(self):
        self.server.shutdown()
        self.server.server_close()
