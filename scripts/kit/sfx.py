"""Synthesized sound palettes shared by every look.

electronic (NEON)  whoosh, swish, riser, impact, pop, glitch
acoustic   (ink)   pluck (pentatonic string), bell, drop, breeze, brush, seal, gliss, tear
synth(kind, var, remap) renders one; remap maps generic names onto a palette (SFX_MAP: whoosh->breeze, pop->pluck…).
"""
import numpy as np

SR = 48000
KINDS = {'pluck', 'bell', 'drop', 'breeze', 'brush', 'seal', 'gliss', 'tear'}
SFX_MAP = {'whoosh': 'breeze', 'swish': 'brush', 'pop': 'pluck', 'impact': 'bell', 'riser': 'gliss', 'glitch': 'drop'}
PENTA = [293.66, 329.63, 369.99, 440.0, 493.88, 587.33]   # D gong pentatonic (宫商角徵羽)
RNG = np.random.RandomState(7)


def _reverb(x, wet=.28, tail=1.4, seed=3):
    r = np.random.RandomState(seed)
    n = int(tail * SR); tt = np.arange(n) / SR
    ir = r.randn(n) * np.exp(-tt / .38)
    ir = np.convolve(ir, np.ones(12) / 12, 'same'); ir /= np.abs(ir).sum() / 6
    L = len(x) + n
    nf = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(ir, nf), nf)[:L]
    out = np.concatenate([x, np.zeros(n)]) + y * wet
    return out / (np.abs(out).max() + 1e-9)


def _band(d, f0, f1, seed, nb=20):
    r = np.random.RandomState(seed)
    n = int(d * SR); noise = r.randn(n); out = np.zeros(n)
    blk = max(64, n // nb * 2); hop = blk // 2; win = np.hanning(blk)
    for b in range(nb * 2):
        i0 = b * hop
        if i0 + blk > n: break
        Fq = np.fft.rfft(noise[i0:i0 + blk] * win); fr = np.fft.rfftfreq(blk, 1 / SR)
        fc = f0 * (f1 / f0) ** (b / (nb * 2))
        Fq *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * .45 ** 2))
        out[i0:i0 + blk] += np.fft.irfft(Fq, blk)
    return out / (np.abs(out).max() + 1e-9)


def _ks(freq, d, seed, damp=.996):
    """Karplus-Strong plucked string (古琴-ish when low and slow)."""
    r = np.random.RandomState(seed)
    N = int(SR / freq); n = int(d * SR)
    buf = r.uniform(-1, 1, N); buf = np.convolve(buf, np.ones(3) / 3, 'same')
    out = np.zeros(n)
    for i in range(n):
        j = i % N
        out[i] = buf[j]
        buf[j] = damp * .5 * (buf[j] + buf[(j + 1) % N])
    return out


def _ink_synth(kind, var=0):
    tt = lambda d: np.arange(int(d * SR)) / SR
    if kind == 'pluck':
        f = PENTA[var % len(PENTA)]
        x = _ks(f, 1.6, var) * .8 + _ks(f / 2, 1.6, var + 9, .997) * .35
        t = tt(1.6); x *= np.minimum(1, t / .004) * np.exp(-t * 1.6)
        return _reverb(x, .3) * .5
    if kind == 'bell':   # 磬 / small temple bell: inharmonic partials
        t = tt(3.2); f = [520, 780][var % 2]
        x = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / dd) for m, a, dd in [(1, 1, 1.4), (2.76, .5, .7), (5.4, .25, .35), (8.93, .12, .18)])
        x *= np.minimum(1, t / .003)
        return _reverb(x, .35) * .42
    if kind == 'drop':   # water drop
        t = tt(.35)
        fq = 700 + 1500 * (1 - np.exp(-t * 90))
        x = np.sin(2 * np.pi * np.cumsum(fq) / SR) * np.exp(-t * 28)
        return _reverb(x, .4) * .45
    if kind == 'breeze':
        x = _band(1.2, 220, 1300, var + 20); t = np.linspace(0, 1, len(x))
        return x * np.sin(np.pi * t) ** 2 * .32
    if kind == 'brush':
        x = _band(.45, 900, 3200, var + 40); t = np.linspace(0, 1, len(x))
        return x * (t ** .4) * (1 - t) ** 1.5 * 1.1 * .45
    if kind == 'gliss':  # rising breeze + a pentatonic run
        x = _band(1.4, 260, 2600, var + 60); t = np.linspace(0, 1, len(x))
        x = x * t ** 1.5 * .3
        for k, f in enumerate(PENTA[:4]):
            i0 = int((.55 + k * .18) * SR)
            pl = _ks(f * 2, .6, k) * np.exp(-np.arange(int(.6 * SR)) / SR * 5) * .22
            x[i0:i0 + len(pl)] += pl[:max(0, len(x) - i0)]
        return _reverb(x, .3) * .8
    if kind == 'tear':   # paper tearing: a crackle of fibre snaps over a dry rustle
        r = np.random.RandomState(var + 70)
        d = .55; n = int(d * SR); x = _band(d, 1200, 4200, var + 80) * .25
        t = np.linspace(0, 1, n); x *= np.sin(np.pi * t) ** .6
        k = 0.0
        while k < d - .02:
            i0 = int(k * SR); L = int(r.uniform(.002, .006) * SR)
            x[i0:i0 + L] += r.randn(L) * np.exp(-np.arange(L) / (L / 4)) * r.uniform(.3, .9)
            k += r.uniform(.004, .02) * (1.3 - t[min(n - 1, i0)])
        x = np.convolve(x, [.5, .5], 'same')
        return x / (np.abs(x).max() + 1e-9) * .5
    if kind == 'seal':   # soft wooden press
        t = tt(.4)
        body = np.sin(2 * np.pi * np.cumsum(90 + 80 * np.exp(-t * 30)) / SR) * np.exp(-t * 14)
        r = np.random.RandomState(var)
        click = np.convolve(r.randn(len(t)) * np.exp(-t * 90), np.ones(24) / 24, 'same') * 2
        return np.tanh((body + click) * 1.2) * .6
    raise ValueError(kind)


def band_sweep(d, f0, f1, nb=24):
    n = int(d * SR); noise = RNG.randn(n); out = np.zeros(n)
    blk = n // nb * 2; hop = blk // 2; win = np.hanning(blk)
    for b in range(nb * 2):
        i0 = b * hop
        if i0 + blk > n: break
        Fq = np.fft.rfft(noise[i0:i0 + blk] * win); fr = np.fft.rfftfreq(blk, 1 / SR)
        fc = f0 * (f1 / f0) ** (b / (nb * 2))
        Fq *= np.exp(-((np.log(fr + 1) - np.log(fc)) ** 2) / (2 * .5 ** 2))
        out[i0:i0 + blk] += np.fft.irfft(Fq, blk)
    return out / (np.abs(out).max() + 1e-9)


def synth(kind, var=0, remap=None):
    """one sound. remap renames kinds first (a theme's sound palette, e.g. SFX_MAP turns whoosh into breeze);
    var picks a variation (pitch / noise seed) for the acoustic kinds; the electronic kinds ignore it."""
    if remap: kind = remap.get(kind, kind)
    if kind in KINDS:
        return _ink_synth(kind, var)
    if kind == 'whoosh':
        x = band_sweep(.55, 300, 4000); t = np.linspace(0, 1, len(x)); return x * np.sin(np.pi * t ** 1.4) ** 2 * .6
    if kind == 'swish':
        x = band_sweep(.25, 1500, 7000); t = np.linspace(0, 1, len(x)); return x * np.sin(np.pi * t) ** 2 * .5
    if kind == 'riser':
        x = band_sweep(1.0, 400, 6000); t = np.linspace(0, 1, len(x))
        return (x * .6 + np.sin(2 * np.pi * np.cumsum(200 + 700 * t ** 2) / SR) * .25) * t ** 2 * .7
    if kind == 'impact':
        t = np.arange(int(.9 * SR)) / SR
        body = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-t * 12)) / SR) * np.exp(-t * 4.5)
        click = np.convolve(RNG.randn(len(t)) * np.exp(-t * 60) * .5, np.ones(8) / 8, 'same')
        return np.tanh((body + click) * 1.6) * .9
    if kind == 'pop':
        d = .12; t = np.arange(int(d * SR)) / SR
        return np.sin(2 * np.pi * np.cumsum(1100 - 500 * t / d) / SR) * np.exp(-t * 45) * .55
    if kind == 'glitch':
        n = int(.22 * SR); x = np.zeros(n)
        for _ in range(7):
            i0 = RNG.randint(0, n - 1500); L = RNG.randint(300, 1500); fq = RNG.choice([220, 440, 880, 1760])
            x[i0:i0 + L] += np.sign(np.sin(2 * np.pi * fq * np.arange(L) / SR)) * .3
        return np.round(x * 6) / 6 * .5
    raise ValueError(kind)
