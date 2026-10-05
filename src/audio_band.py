"""Low-frequency microphone channel for OptiQuake Local.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Measures band-limited energy (default 20-200 Hz) of mono 16-bit PCM in short
windows and keeps a robust baseline, so a structural rumble that coincides
with an optical vibration can corroborate it. Audio is analyzed in memory and
never stored.
"""
import array, collections, math, statistics, sys, threading

class Biquad:
    """RBJ cookbook second-order low-pass or high-pass filter."""

    def __init__(self, kind, cutoff, rate, q=0.7071):
        w = 2*math.pi*cutoff/rate
        alpha = math.sin(w)/(2*q)
        cw = math.cos(w)
        if kind == "lowpass":
            b0, b1, b2 = (1-cw)/2, 1-cw, (1-cw)/2
        elif kind == "highpass":
            b0, b1, b2 = (1+cw)/2, -(1+cw), (1+cw)/2
        else:
            raise ValueError(kind)
        a0 = 1+alpha
        self.b = (b0/a0, b1/a0, b2/a0)
        self.a = (-2*cw/a0, (1-alpha)/a0)
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0

    def process(self, samples):
        b0, b1, b2 = self.b
        a1, a2 = self.a
        x1, x2, y1, y2 = self.x1, self.x2, self.y1, self.y2
        out = []
        for x in samples:
            y = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2
            x2, x1, y2, y1 = x1, x, y1, y
            out.append(y)
        self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2
        return out

class AudioBand:
    """Rolling robust z-score of band-limited RMS energy."""

    def __init__(self, rate=8000, low=20.0, high=200.0, window=0.05,
                 baseline_windows=400, z_threshold=4.0, history_seconds=60.0):
        self.rate = rate
        self.window = window
        self.win_samples = max(1, int(rate*window))
        # 2nd-order high-pass and 4th-order low-pass (two cascaded biquads)
        # so voices and fan hum above the band are strongly attenuated.
        self.filters = [Biquad("highpass", low, rate), Biquad("lowpass", high, rate),
                        Biquad("lowpass", high, rate)]
        self.base = collections.deque(maxlen=baseline_windows)
        self.warmup = min(40, baseline_windows)
        self.z_threshold = z_threshold
        self.history = collections.deque(maxlen=int(history_seconds/window))
        self.pending = array.array("h")
        self.windows = 0
        self.lock = threading.Lock()

    def feed(self, pcm, t0):
        """Analyze 16-bit little-endian mono PCM whose first sample is at t0.

        Samples carried over from the previous call are placed just before t0.
        Returns a list of (t, rms, z) for each complete window.
        """
        chunk = array.array("h")
        chunk.frombytes(pcm[:len(pcm)//2*2])
        if sys.byteorder == "big":
            chunk.byteswap()
        start = t0 - len(self.pending)/self.rate
        samples = self.pending + chunk
        results = []
        n = self.win_samples
        full = len(samples)//n*n
        for i in range(0, full, n):
            y = samples[i:i+n]
            for f in self.filters:
                y = f.process(y)
            rms = math.sqrt(sum(v*v for v in y)/n)
            t = start + (i+n)/self.rate
            results.append((t, rms, self._score(rms)))
        self.pending = samples[full:]
        with self.lock:
            self.history.extend((t, z) for t, _, z in results)
        self.windows += len(results)
        return results

    def _score(self, rms):
        if len(self.base) < self.warmup:
            self.base.append(rms)
            return 0.0
        med = statistics.median(self.base)
        dev = max(statistics.median(abs(x-med) for x in self.base), 0.1*med, 1.0)
        z = (rms-med)/(1.4826*dev)
        if z < self.z_threshold:
            self.base.append(rms)
        return z

    def peak_z(self, t_start, t_end):
        """Highest z observed in [t_start, t_end], or None without data."""
        with self.lock:
            zs = [z for t, z in self.history if t_start <= t <= t_end]
        return max(zs) if zs else None

def read_stream(band, stream, clock, stop, resync=1.0):
    """Feed a live PCM stream into band.

    FFmpeg delivers audio in bursts, so arrival time is a poor timestamp.
    Samples are timed by their count from an anchor taken on clock(), and the
    anchor is reset only if the two drift apart by more than `resync` seconds
    (for example after dropped audio).
    """
    nbytes = band.win_samples*2
    anchor, samples = None, 0
    while not stop.is_set():
        data = stream.read(nbytes)
        if not data:
            return
        n = len(data)//2
        now = clock()
        if anchor is None or abs(anchor + (samples+n)/band.rate - now) > resync:
            anchor = now - (samples+n)/band.rate
        band.feed(data, anchor + samples/band.rate)
        samples += n
