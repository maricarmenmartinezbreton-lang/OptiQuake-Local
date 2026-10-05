"""Pixel features for OptiQuake Local: spatial coverage and global image shift.
Copyright (c) 2026 Lic. Juan Esteban Ramírez
SPDX-License-Identifier: AGPL-3.0-only

Ground shaking moves the whole camera, so the entire image shifts coherently.
A person or object moving in front of the camera changes only one region.
These features help tell the two apart without OpenCV or NumPy.
"""

def grid_mad(a, b, width, height, grid=4):
    """Mean absolute difference for the whole frame and for each grid cell.

    Returns (score, cells) where score equals the full-frame MAD and cells is
    a row-major list of grid*grid per-cell MADs.
    """
    cols = [(c*width)//grid for c in range(grid+1)]
    sums = [0]*(grid*grid)
    counts = [0]*(grid*grid)
    total = 0
    for y in range(height):
        gy = (y*grid)//height
        row = y*width
        for gx in range(grid):
            x0, x1 = row+cols[gx], row+cols[gx+1]
            s = sum(abs(p-q) for p, q in zip(a[x0:x1], b[x0:x1]))
            sums[gy*grid+gx] += s
            counts[gy*grid+gx] += x1-x0
            total += s
    cells = [s/c if c else 0.0 for s, c in zip(sums, counts)]
    return total/(width*height), cells

def profiles(frame, width, height):
    """Column and row brightness means (projection profiles)."""
    cols = [sum(frame[x::width])/height for x in range(width)]
    rows = [sum(frame[y*width:(y+1)*width])/width for y in range(height)]
    return cols, rows

def _centered(p):
    m = sum(p)/len(p)
    return [v-m for v in p]

def best_shift(p, q, max_shift=3):
    """Sub-pixel shift s that best aligns q to p (q[i+s] ~ p[i]).

    Means are removed first so automatic exposure changes do not bias the
    estimate. Parabolic interpolation refines the integer minimum.
    """
    p, q = _centered(p), _centered(q)
    n = len(p)
    max_shift = min(max_shift, n//4)
    if max_shift < 1:
        return 0.0
    cost = {}
    for s in range(-max_shift, max_shift+1):
        lo, hi = max(0, -s), min(n, n-s)
        cost[s] = sum(abs(p[i]-q[i+s]) for i in range(lo, hi))/(hi-lo)
    if max(cost.values()) - min(cost.values()) < 1e-9:
        return 0.0  # flat profile: no texture along this axis
    s0 = min(cost, key=lambda s: (cost[s], abs(s)))
    if -max_shift < s0 < max_shift:
        c0, cm, cp = cost[s0], cost[s0-1], cost[s0+1]
        denom = cm - 2*c0 + cp
        if denom > 0:
            return s0 + 0.5*(cm-cp)/denom
    return float(s0)

def frame_shift(prev_profiles, cur_profiles, max_shift=3):
    """Global (dx, dy) image shift in pixels between two frames."""
    (pc, pr), (cc, cr) = prev_profiles, cur_profiles
    return best_shift(pc, cc, max_shift), best_shift(pr, cr, max_shift)

def dominant_frequency(velocity, fps, hysteresis=0.3):
    """Rough dominant frequency (Hz) of an oscillation from per-frame shifts.

    The shifts are integrated into a displacement (much smoother than the
    noisy velocity), a linear drift is removed, and zero crossings are
    counted with a hysteresis band so small jitter is ignored.
    """
    n = len(velocity)
    if n < 4:
        return None
    pos, acc = [], 0.0
    for v in velocity:
        acc += v
        pos.append(acc)
    xm = (n-1)/2
    ym = sum(pos)/n
    sxx = sum((i-xm)**2 for i in range(n))
    slope = sum((i-xm)*(p-ym) for i, p in enumerate(pos))/sxx
    pos = [p - ym - slope*(i-xm) for i, p in enumerate(pos)]
    rms = (sum(p*p for p in pos)/n) ** 0.5
    if rms < 1e-9:
        return None
    band = hysteresis*rms
    state, crossings = 0, []
    for i, p in enumerate(pos):
        if p > band and state <= 0:
            if state < 0:
                crossings.append(i)
            state = 1
        elif p < -band and state >= 0:
            if state > 0:
                crossings.append(i)
            state = -1
    if len(crossings) < 2 or crossings[-1] == crossings[0]:
        return None
    # Consecutive zero crossings are half a period apart.
    return (len(crossings)-1)*fps/(2*(crossings[-1]-crossings[0]))
