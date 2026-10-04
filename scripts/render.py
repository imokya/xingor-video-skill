"""Generic xingor-style renderer.

Run from the work dir (the one analyze.py filled) with its venv:
    .venv/bin/python <skill>/scripts/render.py test 1.5 12.3 30      # still frames -> test/t_<sec>.jpg
    .venv/bin/python <skill>/scripts/render.py test h0.5 h3.2        # hook stills (h = seconds into the hook)
    .venv/bin/python <skill>/scripts/render.py full ../成片_v1.mp4    # full video

The work dir must contain scenes.py defining:
    KEYWORDS = [...]           # words highlighted lime in subtitles
    def build_scenes(): ...    # list of components.Scene covering 0 .. video end, back to back
    EXTRA_SFX = [(t, kind, gain), ...]   # optional
    HOOK = dict(clips=[(s0, s1), ...], ...) # optional cold open played before the edit (see SKILL.md "Hook")
"""
import sys, os, json, math, subprocess, time, importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.getcwd())
import skia
import fx
from fx import *
import components as CP

FF = './ffmpeg'
SRC = 'source.mp4'
SR = 48000
META = json.load(open('meta.json'))
FPS = META['fps']
NSRC = META['frames']
CP.PERSON.update(META.get('person', {}))
AUDIO_ONLY = META.get('audio_only', False)

spec = importlib.util.spec_from_file_location('project_scenes', os.path.join(os.getcwd(), 'scenes.py'))
PROJ = importlib.util.module_from_spec(spec); spec.loader.exec_module(PROJ)

# visual theme: 'neon' (default, NEON LAB) or 'poetry-ink' (诗墨国风, see references/poetry-ink.md)
THEME = getattr(PROJ, 'THEME', 'neon')
INK = THEME in ('poetry-ink', 'ink')
import ink as IK

# ------------------------------------------------------------------ edit list: shrink long pauses
removed = set()
for s, e in json.load(open('silences.json')):
    if e - s >= 0.3:
        for i in range(int(math.ceil((s + .09) * FPS)), int(math.floor((e - .09) * FPS))):
            removed.add(i)
KEPT = np.array([i for i in range(NSRC) if i not in removed])


def out_time(st):
    return np.searchsorted(KEPT, st * FPS) / FPS


# ------------------------------------------------------------------ captions
PUNCT = set('，。、,.!?！？；;：: ')


def build_captions():
    segs = json.load(open('transcript.json'))
    lines = [l.strip() for l in open('captions.txt') if l.strip()]
    if len(lines) != len(segs):
        raise SystemExit(f'captions.txt has {len(lines)} lines but transcript has {len(segs)} segments — keep one line per segment')
    caps = []
    for k, (seg, txt) in enumerate(zip(segs, lines)):
        ct = []
        for w in seg['words']:
            chars = [ch for ch in w['w'] if ch not in PUNCT]
            for j in range(len(chars)):
                ct.append(w['s'] + (w['e'] - w['s']) * j / max(1, len(chars)))
        if not ct: ct = [seg['start']]
        chunks = [c for c in txt.split('|') if c.strip()]
        N = max(1, sum(len([c for c in ch if c not in PUNCT]) for ch in chunks))
        pos = 0; starts = []
        for ch in chunks:
            idx = min(len(ct) - 1, int(round(pos / N * len(ct))))
            starts.append(ct[idx] if pos else seg['start'])
            pos += len([c for c in ch if c not in PUNCT])
        nxt = segs[k + 1]['start'] if k + 1 < len(segs) else seg['end'] + 1
        for j, ch in enumerate(chunks):
            s1 = starts[j + 1] if j + 1 < len(chunks) else min(seg['end'] + .35, nxt)
            caps.append((starts[j] - .05, s1 - .02, ch.strip().rstrip('，。、,.')))
    return caps


KEYWORDS = sorted(getattr(PROJ, 'KEYWORDS', []), key=len, reverse=True)


def split_kw(s):
    out = []; i = 0; buf = ''
    while i < len(s):
        for kw in KEYWORDS:
            if s.startswith(kw, i):
                if buf: out.append((buf, False)); buf = ''
                out.append((kw, True)); i += len(kw); break
        else:
            buf += s[i]; i += 1
    if buf: out.append((buf, False))
    return out


def draw_caption(c, st, caps, min_start=-1e9):
    if INK: return IK.caption(c, st, caps, split_kw, min_start)
    for s0, s1, txt in caps:
        if s0 <= st < s1 and s0 >= min_start:
            p = eo(P(st, s0, .14))
            f = F('bold', 50)
            parts = split_kw(txt)
            total = sum(tw(p_, f) for p_, _ in parts)
            x = W / 2 - total / 2; y = H - 68 + 10 * (1 - p)
            for ptxt, hl in parts:
                text(c, ptxt, x, y, f, (0, 0, 0), .75 * p, glow=8)
                text(c, ptxt, x, y, f, (0, 0, 0), .85 * p, stroke=7)
                x += text(c, ptxt, x, y, f, LIME if hl else WHITE, p)
            return


# ------------------------------------------------------------------ hook (钩子 / cold open)
def norm_hook():
    """HOOK in scenes.py -> normalized dict, or None.
    clips: (s0, s1) = source seconds of the talking-head video, or ('broll.mp4', s0, s1[, gain]) = external footage
           with its own sound, or dicts with keys path/s0/s1/gain/text/text_t."""
    hk = getattr(PROJ, 'HOOK', None)
    if not hk: return None
    hk = dict(clips=list(hk)) if isinstance(hk, (list, tuple)) else dict(hk)
    clips = []
    for cl in hk.get('clips', []):
        if isinstance(cl, dict): d = dict(cl)
        elif isinstance(cl[0], str): d = dict(path=cl[0], s0=cl[1], s1=cl[2], gain=cl[3] if len(cl) > 3 else .8)
        else: d = dict(path=None, s0=cl[0], s1=cl[1])
        for k_, v_ in dict(path=None, gain=1.0, text=None, text_t=.2).items(): d.setdefault(k_, v_)
        d['n'] = max(1, int(round((d['s1'] - d['s0']) * FPS)))
        clips.append(d)
    if not clips: return None
    o = 0
    for d in clips: d['o0'] = o; o += d['n']
    hk.update(clips=clips, n=o, dur=o / FPS)
    for k_, v_ in dict(title='', title_t=.25, kicker='诗墨 · 精彩先览' if INK else 'HIGHLIGHT · 精彩预告', outro='正片开始').items():
        hk.setdefault(k_, v_)
    return hk


HOOK = norm_hook()


def hook_clip_at(hf):
    """hook frame index -> (clip index, clip, local seconds)"""
    for k, d in enumerate(HOOK['clips']):
        if hf < d['o0'] + d['n']: return k, d, (hf - d['o0']) / FPS
    d = HOOK['clips'][-1]; return len(HOOK['clips']) - 1, d, (d['n'] - 1) / FPS


def media_aspect(path):
    import re
    out = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    m = re.search(r'Video:.*?(\d{2,5})x(\d{2,5})', out)
    return int(m.group(1)) / int(m.group(2)) if m else W / H


def media_vf(d):
    """B-roll with the frame's shape is cover-cropped; a different shape (e.g. vertical phone footage) is fitted
    over a blurred, darkened copy of itself. d['fit'] = 'auto' | 'cover' | 'blur'."""
    fit = d.get('fit', 'auto')
    if fit == 'auto':
        fit = 'cover' if abs(media_aspect(d['path']) / (W / H) - 1) < .15 else 'blur'
    if fit == 'cover':
        return f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1'
    return (f'split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:2,eq=brightness=-0.12[bg];'
            f'[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS},setsar=1')


def hook_pipe(d, gray=False, start=0.0, nframes=None):
    path = SRC if d['path'] is None else d['path']
    if gray: path = 'matte.mkv'
    cmd = [FF, '-v', 'error', '-ss', f"{d['s0'] + start:.4f}", '-i', path]
    if d['path'] is not None: cmd += ['-vf', media_vf(d)]
    cmd += ['-frames:v', str(nframes or d['n']), '-f', 'rawvideo', '-pix_fmt', 'gray' if gray else 'rgb24', '-']
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)


def hook_frames():
    """yields (hook frame index, rgb frame, matte or None) for the whole hook"""
    hf = 0
    for d in HOOK['clips']:
        v = hook_pipe(d); m = hook_pipe(d, gray=True) if d['path'] is None else None
        fb = mb = None
        for j in range(d['n']):
            b = v.stdout.read(W * H * 3)
            if len(b) == W * H * 3: fb = b
            if m is not None:
                b2 = m.stdout.read(W * H)
                if len(b2) == W * H: mb = b2
            if fb is None: fb = bytes(W * H * 3)
            yield hf, np.frombuffer(fb, np.uint8).reshape(H, W, 3), (np.frombuffer(mb, np.uint8).reshape(H, W) if mb else None)
            hf += 1
        v.kill()
        if m is not None: m.kill()


def hook_frame_at(d, lt):
    v = hook_pipe(d, start=lt, nframes=1); fb = v.stdout.read(); v.wait()
    fr = np.frombuffer(fb[:W * H * 3], np.uint8).reshape(H, W, 3)
    mt = None
    if d['path'] is None:
        m = hook_pipe(d, gray=True, start=lt, nframes=1); mb = m.stdout.read(); m.wait()
        mt = np.frombuffer(mb[:W * H], np.uint8).reshape(H, W)
    return fr, mt


# ------------------------------------------------------------------ audio + synthesized sfx
def load_audio():
    raw = subprocess.run([FF, '-v', 'error', '-i', SRC, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def envelope(a):
    m = a.mean(1); hop = SR // 100; n = len(m) // hop
    r = np.sqrt((m[:n * hop].reshape(n, hop) ** 2).mean(1))
    r = np.convolve(r, np.ones(5) / 5, 'same')
    return r / (np.percentile(r, 98) + 1e-9)


RNG = np.random.RandomState(7)


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


def synth(kind, var=0):
    """var picks a variation (pitch / noise seed) for the poetry-ink sounds; neon sounds ignore it."""
    if INK: kind = IK.SFX_MAP.get(kind, kind)
    if kind in ('pluck', 'bell', 'drop', 'breeze', 'brush', 'seal', 'gliss', 'tear'):
        import ink as IK_
        return IK_.synth(kind, var)
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


def build_audio(a, sfx_list, sfx_gain=.22, bgm=None, bgm_gain=.12):
    spf = SR // FPS
    runs_ = []; s = KEPT[0]; p = s
    for i in KEPT[1:]:
        if i != p + 1: runs_.append((s, p)); s = i
        p = i
    runs_.append((s, p))
    fade = int(.008 * SR); pieces = []
    for s, e in runs_:
        seg = a[s * spf:(e + 1) * spf].copy()
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]; seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        pieces.append(seg)
    voice = np.concatenate(pieces)
    if not AUDIO_ONLY: voice = voice / (np.abs(voice).max() + 1e-9) * .89   # narration audio keeps its own level
    fx_ = np.zeros(len(voice) + SR * 2); cache = {}
    for n_, (st, kind, g) in enumerate(sfx_list):
        key = (kind, n_ % 5 if INK else 0)
        if key not in cache: cache[key] = synth(*key)
        x = cache[key]; ot = out_time(st) - {'whoosh': .3, 'riser': .2, 'breeze': .3, 'gliss': .4}.get(kind, 0)
        i0 = max(0, int(ot * SR)); x = x[:max(0, len(fx_) - i0)]; fx_[i0:i0 + len(x)] += x * g * sfx_gain
    mix = voice + fx_[:len(voice), None]
    if bgm and os.path.exists(bgm):
        raw = subprocess.run([FF, '-v', 'error', '-stream_loop', '-1', '-i', bgm, '-t', str(len(voice) / SR + 1), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'],
                             capture_output=True).stdout
        b = np.frombuffer(raw, np.float32).reshape(-1, 2)[:len(voice)]
        b = b / (np.abs(b).max() + 1e-9)
        env = np.abs(voice).mean(1); k = int(.3 * SR)
        env = np.convolve(env, np.ones(k) / k, 'same'); duck = 1 - .55 * np.clip(env / (env.max() * .25 + 1e-9), 0, 1)
        fo = np.ones(len(b)); n2 = min(len(b), 2 * SR); fo[-n2:] = np.linspace(1, 0, n2)
        mix[:len(b)] += b * (bgm_gain * duck[:len(b)] * fo)[:, None]
    if AUDIO_ONLY:   # only tame peaks the effects push over full scale; the voice itself is untouched
        pk = np.abs(mix).max()
        return (mix * (min(1.0, .98 / pk) if pk > 0 else 1)).astype(np.float32)
    return (np.tanh(mix * 1.05) / np.tanh(1.05)).astype(np.float32)


def build_hook_audio(a, sfx_gain=.22):
    """hook sound: the clips' own audio (same voice level as the body) + cut whooshes, title impacts and a riser into the edit"""
    spf = SR // FPS; fade = int(.012 * SR); pieces = []
    vk = .89 / (np.abs(a).max() + 1e-9)
    for d in HOOK['clips']:
        L = d['n'] * spf
        if d['path'] is None:
            i0 = int(round(d['s0'] * SR)); seg = a[i0:i0 + L].copy() * vk
        else:
            raw = subprocess.run([FF, '-v', 'error', '-ss', f"{d['s0']:.3f}", '-i', d['path'], '-t', f'{L / SR + .1:.3f}',
                                  '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
            seg = np.frombuffer(raw, np.float32).reshape(-1, 2)[:L].copy()
            if len(seg): seg *= .89 / (np.abs(seg).max() + 1e-9)
        if len(seg) < L: seg = np.concatenate([seg, np.zeros((L - len(seg), 2), np.float32)])
        seg *= d['gain']
        seg[:fade] *= np.linspace(0, 1, fade)[:, None]; seg[-fade:] *= np.linspace(1, 0, fade)[:, None]
        pieces.append(seg)
    mix = np.concatenate(pieces)
    sfx = [(HOOK['title_t'], 'impact', .9)] if HOOK['title'] else []
    for k, d in enumerate(HOOK['clips']):
        t0 = d['o0'] / FPS
        if k: sfx += [(t0 - .3, 'whoosh', .8), (t0, 'glitch', .45)]
        if d['text']:
            tts = d['text_t'] if isinstance(d['text_t'], (list, tuple)) else [d['text_t']]
            sfx += [(t0 + t_, 'impact', .9 if j == 0 else .6) for j, t_ in enumerate(tts)]
    sfx.append((HOOK['dur'] - 1.0, 'riser', .9))
    fx_ = np.zeros(len(mix) + SR * 2)
    for n_, (t, kind, g) in enumerate(sfx):
        x = synth(kind, n_); i0 = max(0, int(t * SR)); x = x[:max(0, len(fx_) - i0)]; fx_[i0:i0 + len(x)] += x * g * sfx_gain
    mix = mix + fx_[:len(mix), None]
    return (np.tanh(mix * 1.05) / np.tanh(1.05)).astype(np.float32)


# ------------------------------------------------------------------ video
x_ = np.arange(256) / 255
LUT = (np.stack([np.clip(x_ - .045 * np.sin(2 * np.pi * x_), 0, 1),
                 np.clip(x_ - .045 * np.sin(2 * np.pi * x_) + .004, 0, 1),
                 np.clip(x_ - .040 * np.sin(2 * np.pi * x_) + .018 * (1 - x_), 0, 1)], 1) * 255).astype(np.uint8)


def grade(fr):
    if INK: return IK.grade_np(fr)
    out = np.empty_like(fr)
    for k in range(3): out[..., k] = LUT[fr[..., k], k]
    return out


SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone)


def draw_img(c, img, xf, paint_=None):
    s, ox, oy = xf
    c.save(); c.translate(ox, oy); c.scale(s, s); c.drawImage(img, 0, 0, SAMP, paint_); c.restore()


def scene_at(scs, st):
    for sc in scs:
        if sc.t0 <= st < sc.t1: return sc
    return scs[-1]


class Ctx: pass


def draw_stack(c, sc, st, img, cutimg, ctx):
    """one scene: background (video / dark / paper) -> behind() -> rim + person cutout -> front()."""
    xf = sc.xf(st)
    if sc.mode == 'talk':
        sc.draw_bg(c, st, ctx)
    elif sc.mode == 'card':
        IK.ink_bg(c, st) if INK else dark_bg(c, st)
        s, ox, oy = xf
        r = 22 * (1 - s) / .38 + .01
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(ox, oy, W * s, H * s), r, r)
        c.drawRRect(rr, paint((0, 0, 0), .35 if INK else .6, blur=30))
        c.save(); c.clipRRect(rr, skia.ClipOp.kIntersect, True); draw_img(c, img, xf); c.restore()
    else:
        if sc.mode == 'full':
            draw_img(c, img, xf)
        else:
            sc.draw_bg(c, st, ctx) if hasattr(sc, 'draw_bg') else dark_bg(c, st)
            k = P(st, sc.t0, .35)
            if k < 1 and not INK: draw_img(c, img, xf, skia.Paint(Alphaf=1 - eo(k)))   # ink: the ink spread reveals it
        sc.behind(c, st, ctx)
        rim = sc.rim_amt(st)
        if rim > 0:
            rb = getattr(sc, 'rim_blur', 10)
            gp = skia.Paint(Alphaf=clamp(rim))
            gp.setImageFilter(skia.ImageFilters.ColorFilter(skia.ColorFilters.Blend(CI(getattr(sc, 'rim_rgb', LIME)), skia.BlendMode.kSrcIn),
                                                            skia.ImageFilters.Blur(rb, rb)))
            draw_img(c, cutimg(), xf, gp)
        draw_img(c, cutimg(), xf)
        tone = getattr(sc, 'ink_person', 0)
        if tone > 0:
            draw_img(c, cutimg(), xf, skia.Paint(Alphaf=clamp(tone), ColorFilter=IK.tone_filter()))
    sc.front(c, st, ctx)


_INKWIN = {}
_AMBIENT = ('breeze', 'gliss', 'whoosh', 'riser')


def ink_windows(scs):
    """poetry-ink page-turn windows, timed from the content: the turn waits until the old page's last line has
    been readable for 1.0 s (0.5 s after a seal), and tries to finish by the new page's first line (shrinking to
    0.7 s if the gap is tight). -> list aligned with scs: None or (start, end)."""
    if id(scs) in _INKWIN: return _INKWIN[id(scs)]
    if IK.TURN != 'ink':   # 'punch' / 'cut': no ink page turns
        _INKWIN[id(scs)] = [None] * len(scs); return _INKWIN[id(scs)]
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
    _INKWIN[id(scs)] = wins
    return wins


def ink_state(scs, st):
    """-> (prev, next|None, d, half, seed) while a page is turning (next=None: the cut has passed but the old
    page is still being read), else None."""
    wins = ink_windows(scs)
    for i in range(1, len(scs)):
        w = wins[i]
        if w is None: continue
        s0, s1 = w
        if s0 <= st < s1: return scs[i - 1], scs[i], st - (s0 + s1) / 2, (s1 - s0) / 2, i
        if scs[i].t0 <= st < s0: return scs[i - 1], None, 0, 0, i
    return None


def ink_freeze(scs, sc, st):
    """an outgoing page holds its final state (no end-of-scene fade) until the ink covers it."""
    k = scs.index(sc)
    if k + 1 < len(scs) and ink_windows(scs)[k + 1] is not None:
        return min(st, getattr(sc, 'hold_t', lambda: sc.t1 - .32)())
    return st


def render_frame(surface, st, ot, frame, matte, ctx):
    c = surface.getCanvas(); c.restoreToCount(1); c.resetMatrix(); c.clear(skia.ColorBLACK)
    sc = scene_at(ctx.scenes, st); xf = sc.xf(st)
    fr = grade(frame)
    img = skia.Image.fromarray(np.dstack([fr, np.full(fr.shape[:2], 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)
    cut = [None]

    def cutimg():
        if cut[0] is None:
            cut[0] = skia.Image.fromarray(np.ascontiguousarray(np.dstack([fr, matte])), colorType=skia.kRGBA_8888_ColorType,
                                          alphaType=skia.kUnpremul_AlphaType)
        return cut[0]

    ctx.img = img
    # per-frame head centre from the matte (smoothed), used by face-tracked crops
    ms = matte[:H // 2:8, ::8].astype(np.float32)
    tot = ms.sum()
    if tot > 500:
        hx = float((ms.sum(0) * np.arange(ms.shape[1])).sum() / tot * 8)
        ctx.head_x = hx if ctx.head_x is None else ctx.head_x * .85 + hx * .15
    elif ctx.head_x is None:
        ctx.head_x = CP.PERSON['head_x']
    tr = ink_state(ctx.scenes, st) if INK else None
    if tr and tr[1] is not None:
        prev, nx, d, half, seed = tr
        draw_stack(c, prev, ink_freeze(ctx.scenes, prev, st), img, cutimg, ctx)
        c.saveLayer(None, None)
        draw_stack(c, nx, st, img, cutimg, ctx)
        state, u = IK.ink_cover(c, d, half, seed)
        IK.ink_edge(c, state, u)
        c.restore()
    elif tr:
        sc = tr[0]
        draw_stack(c, sc, ink_freeze(ctx.scenes, sc, st), img, cutimg, ctx)
    elif INK and IK.TURN == 'punch':   # quick punch-in at each hard cut (smooth_in scenes do their own move)
        u = 1.0
        for nx in ctx.scenes[1:]:
            if 0 <= st - nx.t0 < .35 and not getattr(nx, 'smooth_in', False): u = (st - nx.t0) / .35
        if u < 1:
            s_ = lerp(1.06, 1.0, eo(u))
            c.save(); c.translate(W / 2, H / 2); c.scale(s_, s_); c.translate(-W / 2, -H / 2)
            draw_stack(c, sc, st, img, cutimg, ctx)
            c.restore()
            c.drawRect(skia.Rect.MakeWH(W, H), paint(IK.XUAN_L, .55 * (1 - u) ** 2))
        else:
            draw_stack(c, sc, st, img, cutimg, ctx)
    elif INK:
        draw_stack(c, sc, ink_freeze(ctx.scenes, sc, st), img, cutimg, ctx)
    else:
        draw_stack(c, sc, st, img, cutimg, ctx)
    if INK:
        IK.bottom_mist(c, .62 if sc.mode == 'full' else .9)
        draw_caption(c, st, ctx.captions)
        if HOOK: draw_hook_bridge(c, ot)
        c.drawRect(skia.Rect.MakeXYWH(0, 0, W * ot / ctx.dur, 3), paint(IK.ZHU, .75))
        if ot > ctx.dur - .8:
            c.drawRect(skia.Rect.MakeWH(W, H), paint(IK.XUAN, (ot - (ctx.dur - .8)) / .8))
        return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    for i, nx in enumerate(ctx.scenes[1:], 1):
        d = st - nx.t0
        if abs(d) < .3 and ctx.scenes[i - 1].mode != nx.mode and not getattr(nx, 'smooth_in', False):
            bx = lerp(-700, W + 300, eio((d + .3) / .6))
            pth = skia.Path(); pth.moveTo(bx, 0); pth.lineTo(bx + 340, 0); pth.lineTo(bx + 40, H); pth.lineTo(bx - 300, H); pth.close()
            c.drawPath(pth, paint(LIME, .95))
            p2 = skia.Path(); p2.moveTo(bx + 380, 0); p2.lineTo(bx + 420, 0); p2.lineTo(bx + 120, H); p2.lineTo(bx + 80, H); p2.close()
            c.drawPath(p2, paint(WHITE, .8))
    draw_caption(c, st, ctx.captions)
    if HOOK: draw_hook_bridge(c, ot)
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W * ot / ctx.dur, 4), paint(LIME, .9))
    if ot > ctx.dur - .5:
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0), (ot - (ctx.dur - .5)) / .5))
    out = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    for nx in ctx.scenes[1:]:
        d = abs(st - nx.t0)
        if d < .14 and not getattr(nx, 'smooth_in', False):
            rgb_glitch(out, 1 - d / .14, int(st * 100))
    if HOOK and ot < .14:
        rgb_glitch(out, 1 - ot / .14, int(ot * 1000) + 7)
    return out


def lime_wipe(c, d):
    """diagonal lime band; d = seconds relative to the cut (-.3 .. .3)"""
    bx = lerp(-700, W + 300, eio((d + .3) / .6))
    pth = skia.Path(); pth.moveTo(bx, 0); pth.lineTo(bx + 340, 0); pth.lineTo(bx + 40, H); pth.lineTo(bx - 300, H); pth.close()
    c.drawPath(pth, paint(LIME, .95))
    p2 = skia.Path(); p2.moveTo(bx + 380, 0); p2.lineTo(bx + 420, 0); p2.lineTo(bx + 120, H); p2.lineTo(bx + 80, H); p2.close()
    c.drawPath(p2, paint(WHITE, .8))


def rgb_glitch(out, g, seed):
    sh = int(24 * g)
    out[..., 0] = np.roll(out[..., 0], sh, 1); out[..., 2] = np.roll(out[..., 2], -sh, 1)
    r = np.random.RandomState(seed)
    for _ in range(int(6 * g)):
        y0 = r.randint(0, H - 60); hh = r.randint(8, 60)
        out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], r.randint(-80, 80), 1)


def render_hook_frame(surface, hf, frame, matte, ctx):
    """cold-open look: full frame push-ins, punch text behind the person, 精彩预告 HUD with the real source timecode,
    story-style segment bar, subtitles, glitch cuts between clips, lime wipe into the edit."""
    if INK: return render_hook_frame_ink(surface, hf, frame, matte, ctx)
    c = surface.getCanvas(); c.restoreToCount(1); c.resetMatrix(); c.clear(skia.ColorBLACK)
    k, d, lt = hook_clip_at(hf)
    ht = hf / FPS; cd = d['n'] / FPS
    pr = eio(lt / max(.1, cd))
    xf = CP.full_xf(lerp(1.04, 1.12, pr) if k % 2 == 0 else lerp(1.12, 1.05, pr))
    fr = grade(frame)
    img = skia.Image.fromarray(np.dstack([fr, np.full(fr.shape[:2], 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)
    draw_img(c, img, xf)
    txt, tt = (d['text'], d['text_t']) if d['text'] else ((HOOK['title'], HOOK['title_t']) if k == 0 else (None, 0))
    if txt:
        f = F('heavy', 230 if len(txt) <= 4 else 190)
        CP.slam_text(c, txt, 60, 640, f, lt, tt, WHITE, .97, stagger=.07)
        if lt > tt + .45:
            e = eo(P(lt, tt + .45, .6))
            text(c, txt, 60, 640 + f.getSize() * 1.1 * e, f, LIME, .5 * (1 - P(lt, tt + 1.25, .8)), stroke=2)
        if matte is not None:
            cut = skia.Image.fromarray(np.ascontiguousarray(np.dstack([fr, matte])), colorType=skia.kRGBA_8888_ColorType,
                                       alphaType=skia.kUnpremul_AlphaType)
            draw_img(c, cut, xf)
    vignette(c, .5)
    corners(c, 36, 36, W - 72, H - 72, 46, LIME, .9, 4)
    blink = 1 if int(ht * 2.5) % 2 == 0 else .3
    circle(c, 76, 96, 9, LIME, blink)
    text(c, HOOK['kicker'], 96, 104, F('mono', 22), WHITE, .95, spacing=2)
    if d['path'] is None:
        stc = d['s0'] + lt
        text(c, f'SRC {int(stc) // 60:02d}:{int(stc) % 60:02d}', W - 76, 104, F('mono', 22), LIME, .9, align='r', spacing=2)
    else:
        text(c, 'B-ROLL', W - 76, 104, F('mono', 22), LIME, .9, align='r', spacing=2)
    # story-style segment bar, one segment per clip
    x0, x1, gap = 76, W - 76, 10
    tot = HOOK['n']
    xx = x0
    for j, dj in enumerate(HOOK['clips']):
        wj = (x1 - x0 - gap * (len(HOOK['clips']) - 1)) * dj['n'] / tot
        rrect(c, xx, 56, wj, 6, 3, WHITE, .25)
        fill = 1 if j < k else (lt / cd if j == k else 0)
        if fill > 0: rrect(c, xx, 56, wj * fill, 6, 3, LIME, .95)
        xx += wj + gap
    if d['path'] is None:
        draw_caption(c, d['s0'] + lt, ctx.captions, min_start=d['s0'] - .15)
    if ht > HOOK['dur'] - .3:
        lime_wipe(c, ht - HOOK['dur'])
    out = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    if k and lt < .14:
        rgb_glitch(out, 1 - lt / .14, hf)
    return out


def render_hook_frame_ink(surface, hf, frame, matte, ctx):
    """poetry-ink cold open: slow push-ins, punch characters bleeding into a paper mist behind the person, a
    hairline frame, cinnabar dot + spaced kicker, the real source time, an ink segment rule, mist dissolves
    between clips, and a paper wash that floods the frame into the edit."""
    c = surface.getCanvas(); c.restoreToCount(1); c.resetMatrix(); c.clear(skia.ColorBLACK)
    k, d, lt = hook_clip_at(hf)
    ht = hf / FPS; cd = d['n'] / FPS
    pr = eio(lt / max(.1, cd))
    xf = CP.full_xf(lerp(1.04, 1.1, pr) if k % 2 == 0 else lerp(1.1, 1.05, pr))
    fr = grade(frame)
    img = skia.Image.fromarray(np.dstack([fr, np.full(fr.shape[:2], 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)
    txt, tt = (d['text'], d['text_t']) if d['text'] else ((HOOK['title'], HOOK['title_t']) if k == 0 else (None, 0))
    if d['path'] is not None:   # footage (e.g. the finished result): shown as a framed picture on paper, ungraded
        return render_hook_broll_ink(surface, c, k, d, lt, ht, cd, frame)
    if AUDIO_ONLY and d['path'] is None:   # narration only: a moonlit paper page (or the backdrop) carries the punch text
        if IK.BACKDROP:
            IK.backdrop_bg(c, ht)
        else:
            IK.ink_bg(c, ht)
            IK.moon(c, ht, W * .76, H * .2, min(W, H) * .1, 1.0, -2)
            IK.mountain_layer(c, [(W * .2, H * .1, W * .2), (W * .7, H * .14, W * .2)], H * .86, IK.QIAN, .5, 91, -50, W + 50, blur=3)
            IK.mist(c, ht, H * .78, H * .86, .6, 92, 3)
        sx0, sx1 = (IK.SAFE or (0, 1))
        cx_, sw_ = (sx0 + sx1) / 2 * W, (sx1 - sx0) * W
        if txt:   # 'line1|line2' with text_t=(t1, t2): lines appear in turn, stacked
            parts = txt.split('|'); tts = tt if isinstance(tt, (list, tuple)) else [tt + j * .8 for j in range(len(parts))]
            f = F('song', min(200, (sw_ - 140) / max(len(p_) for p_ in parts)))
            y0 = H * .45 - (len(parts) - 1) * f.getSize() * .65
            for j, (p_, t_) in enumerate(zip(parts, tts)):
                IK.ink_text(c, p_, cx_, y0 + j * f.getSize() * 1.3, f, lt, t_, IK.MO, .97, stagger=.08, dur=.7, align='c')
        txt = None
    else:
        draw_img(c, img, xf)
    if txt:
        IK.left_mist(c, lt, .85 * clamp((lt - tt + .5) / .5))
        f = F('song', 230 if len(txt) <= 4 else 190)
        IK.ink_bloom(c, 60 + f.getSize() * .5, 640 - f.getSize() * .35, lt, tt - .05, f.getSize() * .9, IK.MO, .2, seed=k)
        IK.ink_text(c, txt, 60, 640, f, lt, tt, IK.MO, .97, stagger=.1, dur=.9)
        if matte is not None:
            cut = skia.Image.fromarray(np.ascontiguousarray(np.dstack([fr, matte])), colorType=skia.kRGBA_8888_ColorType,
                                       alphaType=skia.kUnpremul_AlphaType)
            draw_img(c, cut, xf)
    # paper frame + top band so the HUD reads over any footage
    sh = skia.GradientShader.MakeLinear([(0, 0), (0, 170)], [CI(IK.XUAN_L, .7), CI(IK.XUAN_L, 0)])
    c.drawRect(skia.Rect.MakeWH(W, 170), skia.Paint(Shader=sh))
    rrect(c, 34, 34, W - 68, H - 68, 2, IK.MO, .3, stroke=1.2)
    circle(c, 82, 98, 7, IK.ZHU, .65 + .35 * math.sin(ht * 3))
    text(c, HOOK['kicker'], 102, 106, F('songb', 26), IK.MO, .95, spacing=8)
    if d['path'] is None:
        stc = d['s0'] + lt
        text(c, f'原片 {int(stc) // 60:02d}:{int(stc) % 60:02d}', W - 80, 106, F('songr', 24), IK.MO, .85, align='r', spacing=4)
    else:
        text(c, d.get('label') or '空镜 · B-ROLL', W - 80, 106, F('songr', 24), IK.MO, .85, align='r', spacing=4)
    x0, x1, gap = 80, W - 80, 14
    xx = x0
    for j, dj in enumerate(HOOK['clips']):
        wj = (x1 - x0 - gap * (len(HOOK['clips']) - 1)) * dj['n'] / HOOK['n']
        line(c, xx, 60, xx + wj, 60, IK.MO, .22, 2)
        fill = 1 if j < k else (lt / cd if j == k else 0)
        if fill > 0: line(c, xx, 60, xx + wj * fill, 60, IK.ZHU, .9, 2.5)
        xx += wj + gap
    IK.bottom_mist(c, .62)
    if d['path'] is None:
        draw_caption(c, d['s0'] + lt, ctx.captions, min_start=d['s0'] - .15)
    if k and lt < .45:   # mist dissolve between clips
        c.drawRect(skia.Rect.MakeWH(W, H), paint(IK.XUAN_L, .8 * (1 - eo(lt / .45))))
    if ht > HOOK['dur'] - .5:   # paper wash floods the frame into the edit
        u = (ht - (HOOK['dur'] - .5)) / .5
        c.drawPath(IK.blob_path(W / 2, H / 2, 2000 * eio(u) + 1, 3, .14, ht), paint(IK.XUAN_L, 1, blur=40))
    return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def render_hook_broll_ink(surface, c, k, d, lt, ht, cd, frame):
    """poetry-ink hook clip of external footage: the footage keeps its own look (it often has its own titles and
    subtitles), inset on xuan paper with a thin indigo frame and a slow push; HUD lives in the paper margins."""
    IK.ink_bg(c, ht)
    s_ = .86; fw, fh = W * s_, H * s_
    fx, fy = (W - fw) / 2, (H - fh) / 2 + 14
    img = skia.Image.fromarray(np.dstack([frame, np.full(frame.shape[:2], 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)
    z = lerp(1.0, 1.035, eio(lt / max(.1, cd))) if k % 2 == 0 else lerp(1.035, 1.0, eio(lt / max(.1, cd)))
    sw, sh = W / z, H / z
    c.drawRect(skia.Rect.MakeXYWH(fx + 6, fy + 18, fw - 12, fh - 6), paint((40, 40, 50), .22, blur=22))
    c.drawImageRect(img, skia.Rect.MakeXYWH((W - sw) / 2, (H - sh) / 2, sw, sh), skia.Rect.MakeXYWH(fx, fy, fw, fh), SAMP)
    c.drawRect(skia.Rect.MakeXYWH(fx - 10, fy - 10, fw + 20, fh + 20), paint(IK.MO, .45, stroke=1.4))
    circle(c, fx + 4, fy - 44, 6, IK.ZHU, .65 + .35 * math.sin(ht * 3))
    text(c, HOOK['kicker'], fx + 22, fy - 36, F('songb', 26), IK.MO, .95, spacing=8)
    text(c, d.get('label') or '空镜', fx + fw, fy - 36, F('songr', 24), IK.MO, .85, align='r', spacing=4)
    x0, x1, gap = fx, fx + fw, 14
    xx = x0; yb = fy + fh + 30
    for j, dj in enumerate(HOOK['clips']):
        wj = (x1 - x0 - gap * (len(HOOK['clips']) - 1)) * dj['n'] / HOOK['n']
        line(c, xx, yb, xx + wj, yb, IK.MO, .22, 2)
        fill = 1 if j < k else (lt / cd if j == k else 0)
        if fill > 0: line(c, xx, yb, xx + wj * fill, yb, IK.ZHU, .9, 2.5)
        xx += wj + gap
    if k and lt < .45:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(IK.XUAN_L, .8 * (1 - eo(lt / .45))))
    if ht > HOOK['dur'] - .5:
        u = (ht - (HOOK['dur'] - .5)) / .5
        c.drawPath(IK.blob_path(W / 2, H / 2, 2000 * eio(u) + 1, 3, .14, ht), paint(IK.XUAN_L, 1, blur=40))
    return surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)


def draw_hook_bridge(c, ot):
    """first second of the edit after a hook: second half of the lime wipe + the outro chip"""
    if INK:
        if ot < .6:   # the paper wash recedes as an opening ink hole
            c.save(); c.clipPath(IK.blob_path(W / 2, H / 2, 2000 * eio(ot / .6) + 1, 5, .14, ot), skia.ClipOp.kDifference, True)
            c.drawRect(skia.Rect.MakeWH(W, H), paint(IK.XUAN_L, 1 - eo(ot / .6) * .3))
            c.restore()
        if HOOK['outro'] and ot < 1.8:
            a = eo(P(ot, .25, .5)) * clamp((1.8 - ot) / .4)
            if a > 0:
                f = F('songb', 34); w_ = tw(HOOK['outro'], f) + 120
                rrect(c, W / 2 - w_ / 2, 92, w_, 64, 6, IK.XUAN_L, .92 * a)
                rrect(c, W / 2 - w_ / 2, 92, w_, 64, 6, IK.MO, .25 * a, stroke=1.2)
                IK.seal(c, '启', W / 2 - w_ / 2 + 36, 124, 36, ot, .3, a, seed=2)
                text(c, HOOK['outro'], W / 2 - w_ / 2 + 72, 136, f, IK.MO, a, spacing=6)
        return
    if ot < .3: lime_wipe(c, ot)
    if HOOK['outro'] and ot < 1.4:
        a = eob(P(ot, .12, .35)) * clamp((1.4 - ot) / .3)
        if a > 0:
            f = F('heavy', 40); w_ = tw(HOOK['outro'], f) + 110
            c.save(); c.translate(W / 2, 120); c.scale(lerp(.7, 1, a), lerp(.7, 1, a))
            rrect(c, -w_ / 2, -36, w_, 72, 36, LIME, a)
            CP.play_icon(c, -w_ / 2 + 38, 0, 20, INK, LIME, a)
            text(c, HOOK['outro'], -w_ / 2 + 72, 14, f, INK, a)
            c.restore()


def prep_grid(frame, matte, ctx):
    cs = ctx.cell; h, w = H // cs * cs, W // cs * cs
    ctx.lum_grid = frame.mean(2)[:h, :w].reshape(H // cs, cs, W // cs, cs).mean((1, 3)) / 255
    ctx.mask_grid = matte[:h, :w].reshape(H // cs, cs, W // cs, cs).mean((1, 3)) / 255


def make_ctx(env):
    ctx = Ctx()
    ctx.scenes = PROJ.build_scenes()
    end = NSRC / FPS
    ctx.scenes[-1].t1 = max(ctx.scenes[-1].t1, end)
    for a, b in zip(ctx.scenes, ctx.scenes[1:]):
        if abs(a.t1 - b.t0) > 1e-6:
            print(f'WARNING: gap/overlap between scenes at {a.t1} / {b.t0}')
    if INK and IK.TURN == 'ink':   # breeze on each page turn
        sfx = [(w[0] + .1, 'whoosh', .8) for w in ink_windows(ctx.scenes)[1:] if w]
    elif INK:
        sfx = [(sc.t0 - .1, 'whoosh', .8) for sc in ctx.scenes[1:] if not getattr(sc, 'smooth_in', False)]
    else:
        sfx = [(sc.t0 - .12, 'whoosh', .8) for sc in ctx.scenes[1:]]
    for sc in ctx.scenes: sfx += sc.events()
    sfx += list(getattr(PROJ, 'EXTRA_SFX', []))
    if HOOK: sfx.append((KEPT[0] / FPS, 'impact', .9))
    ctx.sfx = sfx
    ctx.captions = build_captions()
    ctx.n_frames = len(KEPT); ctx.dur = len(KEPT) / FPS; ctx.fps = FPS; ctx.cell = 15
    ctx.amp = lambda t: float(clamp(env[min(len(env) - 1, max(0, int(t * 100)))]))
    ctx._ot = 0
    ctx.head_x = None
    ctx.tc = lambda: f'00:{int(ctx._ot) // 60:02d}:{int(ctx._ot) % 60:02d}:{int(ctx._ot * FPS) % FPS:02d}'
    return ctx


def read_frame_at(path, i, gray=False):
    pf = 'gray' if gray else 'rgb24'
    raw = subprocess.run([FF, '-v', 'error', '-ss', f'{i / FPS:.4f}', '-i', path, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', pf, '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(H, W) if gray else np.frombuffer(raw, np.uint8).reshape(H, W, 3)


def main():
    a = load_audio(); env = envelope(a); ctx = make_ctx(env)
    surface = skia.Surface(W, H)
    mode = sys.argv[1]
    if mode == 'test':
        import PIL.Image as Image
        os.makedirs('test', exist_ok=True)
        for ts in sys.argv[2:]:
            if ts.startswith('h'):
                if not HOOK: raise SystemExit('no HOOK defined in scenes.py')
                hf = min(HOOK['n'] - 1, int(round(float(ts[1:]) * FPS)))
                k, d, lt = hook_clip_at(hf)
                fr, mt = hook_frame_at(d, lt)
                out = render_hook_frame(surface, hf, fr, mt, ctx)
                Image.fromarray(out[..., :3]).save(f'test/t_{ts}.jpg', quality=88)
                print('saved test/t_%s.jpg' % ts)
                continue
            st = float(ts); i = int(round(st * FPS))
            fr = read_frame_at(SRC, i); mt = read_frame_at('matte.mkv', i, True)
            prep_grid(fr, mt, ctx); ctx._ot = out_time(st); ctx.head_x = None
            out = render_frame(surface, st, out_time(st), fr, mt, ctx)
            Image.fromarray(out[..., :3]).save(f'test/t_{ts}.jpg', quality=88)
            print('saved test/t_%s.jpg' % ts)
        return
    out_path = sys.argv[2]
    bgm = None
    if '--bgm' in sys.argv: bgm = sys.argv[sys.argv.index('--bgm') + 1]
    mix = build_audio(a, ctx.sfx, bgm=bgm)
    if HOOK:
        mix = np.concatenate([build_hook_audio(a), mix])
        print(f"hook: {len(HOOK['clips'])} clip(s), {HOOK['dur']:.1f}s", flush=True)
    mix.tofile('mix.f32')
    dec = subprocess.Popen([FF, '-v', 'error', '-i', SRC, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    mdec = subprocess.Popen([FF, '-v', 'error', '-i', 'matte.mkv', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', 'mix.f32',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                            '-c:a', 'aac', '-b:a', '256k', '-shortest', out_path], stdin=subprocess.PIPE)
    keep = set(KEPT.tolist()); t0 = time.time(); n = 0
    if HOOK:
        for hf, fr, mt in hook_frames():
            enc.stdin.write(render_hook_frame(surface, hf, fr, mt, ctx).tobytes())
    for i in range(NSRC):
        fb = dec.stdout.read(W * H * 3); mb = mdec.stdout.read(W * H)
        if len(fb) < W * H * 3 or len(mb) < W * H: break
        if i not in keep: continue
        fr = np.frombuffer(fb, np.uint8).reshape(H, W, 3); mt = np.frombuffer(mb, np.uint8).reshape(H, W)
        st = i / FPS; ot = n / FPS; ctx._ot = ot
        if getattr(scene_at(ctx.scenes, st), 'needs_grid', False): prep_grid(fr, mt, ctx)
        enc.stdin.write(render_frame(surface, st, ot, fr, mt, ctx).tobytes()); n += 1
        if n % 200 == 0: print(f'{n}/{len(KEPT)}  {n / (time.time() - t0):.1f} fps', flush=True)
    enc.stdin.close(); enc.wait()
    print('done', n, 'frames ->', out_path, f'{time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
