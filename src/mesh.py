"""Sensor mesh for OptiQuake Local: several computers on the same network share
camera detections so a vibration seen by two or more sensors can be confirmed.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Messages are UDP broadcasts on the local network (no internet needed) signed
with HMAC-SHA256 using a shared key, so only sensors that know the key can
raise or confirm an alert. Replayed or stale messages are rejected.
"""
import hashlib, hmac, json, os, socket, threading, time

DEFAULT_PORT = 8766
MAX_SKEW_S = 120.0  # computers' clocks may differ a little

def _sign(key, body):
    return hmac.new(key, body, hashlib.sha256).hexdigest()

def encode(key, node, kind, payload, now=None):
    msg = {"v": 1, "node": node, "kind": kind, "ts": time.time() if now is None else now,
           "nonce": os.urandom(8).hex(), "data": payload}
    body = json.dumps(msg, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return json.dumps({"m": msg, "sig": _sign(key, body)}).encode("utf-8")

def decode(key, raw, now=None):
    """Return the message dict if authentic and fresh, else None."""
    try:
        outer = json.loads(raw.decode("utf-8"))
        msg, sig = outer["m"], outer["sig"]
        body = json.dumps(msg, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        return None
    if not isinstance(sig, str) or not hmac.compare_digest(sig, _sign(key, body)):
        return None
    now = time.time() if now is None else now
    if abs(now - float(msg.get("ts", 0))) > MAX_SKEW_S:
        return None
    return msg

class Mesh:
    """Broadcasts local detections and reports authentic detections from peers.

    on_peer(node, data) is called once per authentic peer message."""

    def __init__(self, key, node, on_peer, port=DEFAULT_PORT, broadcast="255.255.255.255",
                 bind_host=""):
        if len(key) < 8:
            raise ValueError("mesh key must have at least 8 characters")
        self.key = key.encode("utf-8")
        self.node = node
        self.on_peer = on_peer
        self.port = port
        self.broadcast = broadcast
        self.seen = {}  # nonce -> receive time (replay protection)
        self.rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rx.bind((bind_host, port))
        self.rx.settimeout(0.5)
        self.tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tx.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="mesh")
        self._thread.start()

    def send(self, kind, payload):
        raw = encode(self.key, self.node, kind, payload)
        try:
            self.tx.sendto(raw, (self.broadcast, self.port))
        except OSError:
            pass  # network down: the local alert already happened

    def handle(self, raw, now=None):
        msg = decode(self.key, raw, now)
        if not msg or msg.get("node") == self.node:
            return False
        now = time.time() if now is None else now
        self.seen = {n: t for n, t in self.seen.items() if now - t <= MAX_SKEW_S * 2}
        if msg["nonce"] in self.seen:
            return False
        self.seen[msg["nonce"]] = now
        self.on_peer(msg["node"], msg.get("kind"), msg.get("data") or {})
        return True

    def _loop(self):
        while not self._stop.is_set():
            try:
                raw, _ = self.rx.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                if self._stop.is_set():
                    return
                time.sleep(1)
                continue
            self.handle(raw)

    def close(self):
        self._stop.set()
        self._thread.join(timeout=2)
        self.rx.close()
        self.tx.close()
