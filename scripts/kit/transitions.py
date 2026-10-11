"""Page turns shared by every look.

glitch      rgb_glitch(out, g, seed)               post-process RGB split + slice shifts (numpy frame)
wipe        lime_wipe(c, d, color, edge)           diagonal colour band across a cut
ink         ink_cover(...) + ink_edge(..., color)  ink spreading from drops, the new page clearing from its centre
timing      ink_windows / ink_state / ink_freeze   content-aware turn timing: a page holds until its last line was
                                                   readable, then turns (used by the 'ink' turn mode)
"""
import math
import numpy as np
import skia
from fx import W, H, paint, LIME, WHITE
from kit.motion import clamp, eio, lerp
from kit.noise import _img, _blur, _fbm, _ss

SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)
_FIELD = {}


def _cover_field(seed):
    """ink-spread field for one page turn, at 1/3 resolution: several drops landing one after another, each
    spreading like real diffusion (fast, then slowing), on a domain-warped distance so the edge grows tendrils."""
    key = ('cover', seed, W, H)
    if key not in _FIELD:
        w, h = W // 3, H // 3; S = max(w, h)
        r = np.random.RandomState(seed + 500)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        wx = _fbm(w, h, seed + 510, S * .35) * S * .22          # domain warp -> 墨丝 tendrils
        wy = _fbm(w, h, seed + 520, S * .35) * S * .22
        X, Y = xx + wx, yy + wy
        ox, oy = [(.3, .3), (.7, .28), (.5, .5), (.3, .72), (.7, .7)][seed % 5]
        drops = [(ox * w, oy * h, 0.0)]
        for k in range(3):   # later, smaller drops nearby and further out
            ang = r.uniform(0, 6.28); dist = r.uniform(.18, .42) * S
            drops.append((ox * w + math.cos(ang) * dist, oy * h + math.sin(ang) * dist, r.uniform(.12, .32)))
        A = np.full((h, w), 9.0, np.float32)
        for dx, dy, delay in drops:
            dd = np.hypot(X - dx, Y - dy) / S
            A = np.minimum(A, delay + dd ** 1.6 * 1.25)               # radius ~ t^(1/1.6): fast, then slowing
        A += _fbm(w, h, seed + 530, S * .06, 3) * .07               # fine fibrous edge
        A = (A - A.min()) / (np.percentile(A, 99.7) - A.min())
        tex = np.clip(_fbm(w, h, seed + 540, S * .18) + .5, 0, 1)    # cloudy ink density
        tex2 = np.clip(_fbm(w, h, seed + 550, S * .05, 3) + .5, 0, 1)
        _FIELD[key] = (A, tex, tex2)
    return _FIELD[key]


def ink_cover(c, d, dur, seed, origin=None):
    """page turn, inside a saveLayer holding the incoming scene: mask it to where the ink has already cleared.
    d = seconds relative to the cut (-dur .. dur). Returns (state, u) for ink_edge."""
    u = clamp((d + dur) / (2 * dur))
    A, tex, tex2 = _cover_field(seed)
    T = 1.32 * eio(u) - .02
    reveal = _ss(T - .3 - A + .12 * (tex - .5), .22)       # the new page clears out of the ink centre
    c.drawImageRect(_img(_blur(reveal, 1.5), WHITE), skia.Rect.MakeWH(W, H), SAMP, skia.Paint(BlendMode=skia.BlendMode.kDstIn))
    return (A, tex, tex2, T, reveal), u


def ink_edge(c, st, u, color):
    """the ink itself: a cloudy indigo wash spreading ahead of the reveal, densest at its rim (ink pools at the
    edge as it dries), with wispy fibres; it thins out as the new page clears."""
    A, tex, tex2, T, reveal = st
    x = T - A
    cov = _ss(x + .015 * (tex2 - .5), .05)
    rim = np.exp(-((x - .035) / .045) ** 2)
    dens = cov * (.3 + .5 * tex ** 1.3 + .2 * tex2) + rim * (.12 + .22 * tex2)
    dens *= (1 - reveal) ** 1.4
    fade = clamp((1 - u) / .15)                            # nothing left once the page has turned
    c.drawImageRect(_img(_blur(np.clip(dens * .88 * fade, 0, 1), 1.6), color), skia.Rect.MakeWH(W, H), SAMP, skia.Paint())


def lime_wipe(c, d, color=LIME, edge=WHITE):
    """diagonal lime band; d = seconds relative to the cut (-.3 .. .3)"""
    bx = lerp(-700, W + 300, eio((d + .3) / .6))
    pth = skia.Path(); pth.moveTo(bx, 0); pth.lineTo(bx + 340, 0); pth.lineTo(bx + 40, H); pth.lineTo(bx - 300, H); pth.close()
    c.drawPath(pth, paint(color, .95))
    p2 = skia.Path(); p2.moveTo(bx + 380, 0); p2.lineTo(bx + 420, 0); p2.lineTo(bx + 120, H); p2.lineTo(bx + 80, H); p2.close()
    c.drawPath(p2, paint(edge, .8))


def rgb_glitch(out, g, seed):
    sh = int(24 * g)
    out[..., 0] = np.roll(out[..., 0], sh, 1); out[..., 2] = np.roll(out[..., 2], -sh, 1)
    r = np.random.RandomState(seed)
    for _ in range(int(6 * g)):
        y0 = r.randint(0, H - 60); hh = r.randint(8, 60)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], r.randint(-80, 80), 1)


_INKWIN = {}
_AMBIENT = ('breeze', 'gliss', 'whoosh', 'riser')


def ink_windows(scs, turn):
    """poetry-ink page-turn windows, timed from the content: the turn waits until the old page's last line has
    been readable for 1.0 s (0.5 s after a seal), and tries to finish by the new page's first line (shrinking to
    0.7 s if the gap is tight). -> list aligned with scs: None or (start, end)."""
    if (id(scs), turn) in _INKWIN: return _INKWIN[(id(scs), turn)]
    if turn != 'ink':   # 'punch' / 'cut': no ink page turns
        _INKWIN[(id(scs), turn)] = [None] * len(scs); return _INKWIN[(id(scs), turn)]
    ev = lambda sc: [(t, k) for t, k, g in sc.events() if t > sc.t0 + .2 and k not in _AMBIENT]
    wins = [None]
    for i, nx in enumerate(scs[1:], 1):
        pv = scs[i - 1]
        if getattr(nx, 'smooth_in', False):
            wins.append(None); continue
        ready = max([t + (.5 if k == 'seal' else 1.0) for t, k in ev(pv)] + [pv.t0 + 1.0, getattr(pv, 'ready_t', lambda: 0)()])
        first = min([t for t, k in ev(nx)] + [nx.t0 + .8])
        start = max(ready, nx.t0 - .9)
        D = 1.0
        if start + D > first + .15: D = max(.7, first + .15 - start)
        start = min(start, nx.t1 - D - .2)
        wins.append((start, start + D))
    _INKWIN[(id(scs), turn)] = wins
    return wins


def ink_state(scs, st, turn):
    """-> (prev, next|None, d, half, seed) while a page is turning (next=None: the cut has passed but the old
    page is still being read), else None."""
    wins = ink_windows(scs, turn)
    for i in range(1, len(scs)):
        w = wins[i]
        if w is None: continue
        s0, s1 = w
        if s0 <= st < s1: return scs[i - 1], scs[i], st - (s0 + s1) / 2, (s1 - s0) / 2, i
        if scs[i].t0 <= st < s0: return scs[i - 1], None, 0, 0, i
    return None


def ink_freeze(scs, sc, st, turn):
    """an outgoing page holds its final state (no end-of-scene fade) until the ink covers it."""
    k = scs.index(sc)
    if k + 1 < len(scs) and ink_windows(scs, turn)[k + 1] is not None:
        return min(st, getattr(sc, 'hold_t', lambda: sc.t1 - .32)())
    return st
