"""Synthesized 120 BPM backing track (no samples, no licences) — dark, minimal, cool.

    python music.py bgm.wav [duration]

make(dur, secs, hits): secs = [(start_s, section)], section in intro / groove / full / break / build / outro / end;
hits = [t] impacts, each preceded by a riser.
"""
import sys, wave
import numpy as np
from scipy.signal import lfilter, butter

SR = 48000
BPM = 120
BEAT = 60 / BPM
BAR = BEAT * 4
rng = np.random.RandomState(11)

NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)
# Am7  Fmaj7  Dm9  Em7   (bass root, upper voicing)
CHORDS = [(45, [60, 64, 67, 71]), (41, [60, 64, 65, 69]), (38, [60, 62, 65, 69]), (40, [59, 62, 64, 67])]
SECS = [(0, 'intro'), (8, 'groove'), (34, 'break'), (45, 'full'), (75, 'build'), (86, 'outro')]
HITS = [8, 45, 86]


def section(t):
    cur = SECS[0][1]
    for s, name in SECS:
        if t >= s: cur = name
    return cur


def next_change(t):
    for s, _ in SECS:
        if s > t + 1e-6: return s
    return 1e9


def env_adsr(n, a=.005, d=.1, s=.6, r=.1):
    e = np.ones(n) * s
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    e[ai:ai + di] = np.linspace(1, s, len(e[ai:ai + di]))
    if ri: e[-ri:] *= np.linspace(1, 0, len(e[-ri:]))
    return e


def saw(f, n, ph=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + ph) % 1) - 1


def lp(x, fc, order=2):
    b, a = butter(order, min(fc, SR / 2 - 100) / (SR / 2), 'low'); return lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2), 'high'); return lfilter(b, a, x)


def kick():
    n = int(.5 * SR); t = np.arange(n) / SR
    f = 44 + 95 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6)
    x += np.exp(-t * 400) * rng.randn(n) * .08
    return np.tanh(x * 1.6) * .9


def hat(open_=False):
    n = int((.2 if open_ else .04) * SR); t = np.arange(n) / SR
    return hp(rng.randn(n), 8000) * np.exp(-t * (16 if open_ else 80)) * .28


def rim():
    n = int(.12 * SR); t = np.arange(n) / SR
    b, a = butter(2, [1500 / (SR / 2), 5000 / (SR / 2)], 'band')
    return lfilter(b, a, rng.randn(n)) * np.exp(-t * 45) * .9


def add(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0: return
    x = x[:len(buf) - i]; buf[i:i + len(x)] += x * g


def make(dur, secs=None, hits=None):
    global SECS, HITS
    if secs: SECS = sorted(secs)
    if hits is not None: HITS = hits
    N = int(dur * SR) + SR
    drums = np.zeros(N); bass = np.zeros(N); pad = np.zeros(N); arp = np.zeros(N); fx = np.zeros(N)
    side = np.ones(N)
    K, RM = kick(), rim()
    for b in range(int(dur / BEAT) + 1):
        t = b * BEAT; sec = section(t); bb = b % 4; tn = next_change(t)
        if sec == 'end': continue
        pre_drop = tn - t <= 1.0 and any(abs(tn - h) < .01 for h in HITS)     # drop out a bar before a hit
        kick_on = sec in ('groove', 'full', 'build') or (sec == 'intro' and t >= 4) or sec == 'outro'
        if pre_drop: kick_on = False
        if kick_on:
            add(drums, K, t, 1.0)
            i = int(t * SR); m = int(.36 * SR); seg = side[i:i + m]
            side[i:i + m] = np.minimum(seg, 1 - .6 * np.exp(-np.arange(len(seg)) / SR * 8))
        if sec in ('groove', 'full', 'build', 'outro') and bb in (1, 3) and not pre_drop:
            add(drums, RM, t, .35)
        if sec in ('groove', 'full', 'build', 'outro', 'intro') and not pre_drop:
            add(drums, hat(sec == 'full' and bb == 3), t + BEAT / 2, .8 if sec != 'intro' else .35)
            if sec in ('full', 'build'):
                add(drums, hat(), t + BEAT / 4, .25); add(drums, hat(), t + 3 * BEAT / 4, .25)
    for bar in range(int(dur / BAR) + 1):
        t = bar * BAR; sec = section(t)
        root, ch = CHORDS[bar % 4]
        n = int(BAR * SR)
        p = np.zeros(n)
        for m in ch:
            for det in (-.07, .0, .08):
                p += saw(NOTE(m) * 2 ** (det / 12), n, rng.rand())
        cut = {'intro': 500 + 120 * t, 'groove': 1300, 'break': 900, 'full': 1900, 'build': 1100 + 160 * (t - [s for s, x in SECS if x == 'build'][0] if any(x == 'build' for _, x in SECS) else 0),
               'outro': 1000, 'end': 700}[sec]
        p = lp(p / 12, cut) * env_adsr(n, .3, .4, .85, .5)
        add(pad, p, t, {'break': .8, 'end': .7}.get(sec, .55))
        if sec in ('groove', 'full', 'build', 'outro'):
            for e in range(8):
                ne = int(BEAT / 2 * SR); tt = np.arange(ne) / SR
                x = saw(NOTE(root), ne) * .45 + np.sin(2 * np.pi * NOTE(root) * tt) * .9
                x = lp(x, 380) * env_adsr(ne, .003, .09, .45, .05)
                add(bass, x, t + e * BEAT / 2, .6 if e % 2 == 0 else .4)
        if sec in ('full', 'break', 'build'):
            seq = [ch[0], ch[2], ch[3], ch[1] + 12, ch[2], ch[3] + 12]
            for s in range(16):
                ns = int(BEAT / 4 * SR); m = seq[s % len(seq)] + 12; tt = np.arange(ns) / SR
                x = (np.sin(2 * np.pi * NOTE(m) * tt) + .25 * saw(NOTE(m), ns)) * np.exp(-tt * 22)
                add(arp, lp(x, 2600), t + s * BEAT / 4, .11 if sec != 'break' else .16)

    def riser(d):
        n = int(d * SR); tt = np.linspace(0, 1, n)
        x = hp(rng.randn(n), 900) * tt ** 2.2
        return (lp(x, 8000) + np.sin(2 * np.pi * np.cumsum(120 + 900 * tt ** 2) / SR) * tt ** 2 * .2) * .28
    for t_hit in HITS:
        add(fx, riser(2.0), t_hit - 2.0, 1.0)
        tt = np.arange(int(2.0 * SR)) / SR
        boom = np.sin(2 * np.pi * np.cumsum(34 + 60 * np.exp(-tt * 9)) / SR) * np.exp(-tt * 2.2)
        add(fx, np.tanh(boom * 1.4) * .8, t_hit, 1.0)
    d = int(BEAT * .75 * SR)
    arpL = arp.copy(); arpR = arp.copy(); arpR[d:] += arp[:-d] * .45; arpL[2 * d:] += arp[:-2 * d] * .3
    # long smear on the pad for space
    rv = np.zeros_like(pad)
    for k, g in ((int(.11 * SR), .35), (int(.23 * SR), .25), (int(.37 * SR), .18)): rv[k:] += pad[:-k] * g
    padw = lp(pad + rv, 4500)
    music = np.stack([padw * side + bass * side + arpL * side, padw * side + bass * side + arpR * side], 1)
    music += drums[:, None] * .75 + fx[:, None]
    n = int(dur * SR); music = music[:n]
    tt = np.arange(n) / SR
    music *= np.clip(tt / .05, 0, 1)[:, None] * np.clip((dur - tt) / 3.0, 0, 1)[:, None]
    music = np.tanh(music * 1.1)
    return music / (np.abs(music).max() + 1e-9) * .89


def write_wav(path, x):
    x = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(x.shape[1] if x.ndim > 1 else 1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'bgm.wav'
    dur = float(sys.argv[2]) if len(sys.argv) > 2 else 96
    write_wav(out, make(dur)); print(out)
