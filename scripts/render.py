"""Generic xingor-style renderer.

Run from the work dir (the one analyze.py filled) with its venv:
    .venv/bin/python <skill>/scripts/render.py test 1.5 12.3 30      # still frames -> test/t_<sec>.jpg
    .venv/bin/python <skill>/scripts/render.py full ../成片_v1.mp4    # full video

The work dir must contain scenes.py defining:
    KEYWORDS = [...]           # words highlighted lime in subtitles
    def build_scenes(): ...    # list of components.Scene covering 0 .. video end, back to back
    EXTRA_SFX = [(t, kind, gain), ...]   # optional
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
CP.PERSON.update(META['person'])

spec = importlib.util.spec_from_file_location('project_scenes', os.path.join(os.getcwd(), 'scenes.py'))
PROJ = importlib.util.module_from_spec(spec); spec.loader.exec_module(PROJ)

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


def draw_caption(c, st, caps):
    for s0, s1, txt in caps:
        if s0 <= st < s1:
            p = eo(P(st, s0, .14))
            f = F('bold', 50)
            parts = split_kw(txt)
            total = sum(tw(p_, f) for p_, _ in parts)
            x = W / 2 - total / 2; y = 1012 + 10 * (1 - p)
            for ptxt, hl in parts:
                text(c, ptxt, x, y, f, (0, 0, 0), .75 * p, glow=8)
                text(c, ptxt, x, y, f, (0, 0, 0), .85 * p, stroke=7)
                x += text(c, ptxt, x, y, f, LIME if hl else WHITE, p)
            return


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


def synth(kind):
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
    voice = np.concatenate(pieces); voice = voice / (np.abs(voice).max() + 1e-9) * .89
    fx_ = np.zeros(len(voice) + SR * 2); cache = {}
    for st, kind, g in sfx_list:
        if kind not in cache: cache[kind] = synth(kind)
        x = cache[kind]; ot = out_time(st) - {'whoosh': .3, 'riser': .2}.get(kind, 0)
        i0 = max(0, int(ot * SR)); fx_[i0:i0 + len(x)] += x * g * sfx_gain
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
    return (np.tanh(mix * 1.05) / np.tanh(1.05)).astype(np.float32)


# ------------------------------------------------------------------ video
x_ = np.arange(256) / 255
LUT = (np.stack([np.clip(x_ - .045 * np.sin(2 * np.pi * x_), 0, 1),
                 np.clip(x_ - .045 * np.sin(2 * np.pi * x_) + .004, 0, 1),
                 np.clip(x_ - .040 * np.sin(2 * np.pi * x_) + .018 * (1 - x_), 0, 1)], 1) * 255).astype(np.uint8)


def grade(fr):
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


def render_frame(surface, st, ot, frame, matte, ctx):
    c = surface.getCanvas(); c.clear(skia.ColorBLACK)
    sc = scene_at(ctx.scenes, st); xf = sc.xf(st)
    fr = grade(frame)
    img = skia.Image.fromarray(np.dstack([fr, np.full(fr.shape[:2], 255, np.uint8)]), colorType=skia.kRGBA_8888_ColorType)
    cut = [None]

    def cutimg():
        if cut[0] is None:
            cut[0] = skia.Image.fromarray(np.ascontiguousarray(np.dstack([fr, matte])), colorType=skia.kRGBA_8888_ColorType,
                                          alphaType=skia.kUnpremul_AlphaType)
        return cut[0]

    if sc.mode == 'card':
        dark_bg(c, st)
        s, ox, oy = xf
        r = 22 * (1 - s) / .38 + .01
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(ox, oy, W * s, H * s), r, r)
        c.drawRRect(rr, paint((0, 0, 0), .6, blur=30))
        c.save(); c.clipRRect(rr, skia.ClipOp.kIntersect, True); draw_img(c, img, xf); c.restore()
    else:
        if sc.mode == 'full':
            draw_img(c, img, xf)
        else:
            dark_bg(c, st)
            k = P(st, sc.t0, .35)
            if k < 1: draw_img(c, img, xf, skia.Paint(Alphaf=1 - eo(k)))
        sc.behind(c, st, ctx)
        rim = sc.rim_amt(st)
        if rim > 0:
            gp = skia.Paint(Alphaf=clamp(rim))
            gp.setImageFilter(skia.ImageFilters.ColorFilter(skia.ColorFilters.Blend(CI(LIME), skia.BlendMode.kSrcIn), skia.ImageFilters.Blur(10, 10)))
            draw_img(c, cutimg(), xf, gp)
        draw_img(c, cutimg(), xf)
    sc.front(c, st, ctx)
    for i, nx in enumerate(ctx.scenes[1:], 1):
        d = st - nx.t0
        if abs(d) < .3 and ctx.scenes[i - 1].mode != nx.mode:
            bx = lerp(-700, W + 300, eio((d + .3) / .6))
            pth = skia.Path(); pth.moveTo(bx, 0); pth.lineTo(bx + 340, 0); pth.lineTo(bx + 40, H); pth.lineTo(bx - 300, H); pth.close()
            c.drawPath(pth, paint(LIME, .95))
            p2 = skia.Path(); p2.moveTo(bx + 380, 0); p2.lineTo(bx + 420, 0); p2.lineTo(bx + 120, H); p2.lineTo(bx + 80, H); p2.close()
            c.drawPath(p2, paint(WHITE, .8))
    draw_caption(c, st, ctx.captions)
    c.drawRect(skia.Rect.MakeXYWH(0, 0, W * ot / ctx.dur, 4), paint(LIME, .9))
    if ot > ctx.dur - .5:
        c.drawRect(skia.Rect.MakeWH(W, H), paint((0, 0, 0), (ot - (ctx.dur - .5)) / .5))
    out = surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)
    for nx in ctx.scenes[1:]:
        d = abs(st - nx.t0)
        if d < .14:
            g = 1 - d / .14; sh = int(24 * g)
            out[..., 0] = np.roll(out[..., 0], sh, 1); out[..., 2] = np.roll(out[..., 2], -sh, 1)
            r = np.random.RandomState(int(st * 100))
            for _ in range(int(6 * g)):
                y0 = r.randint(0, H - 60); hh = r.randint(8, 60)
                out[y0:y0 + hh] = np.roll(out[y0:y0 + hh], r.randint(-80, 80), 1)
    return out


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
    sfx = [(sc.t0 - .12, 'whoosh', .8) for sc in ctx.scenes[1:]]
    for sc in ctx.scenes: sfx += sc.events()
    sfx += list(getattr(PROJ, 'EXTRA_SFX', []))
    ctx.sfx = sfx
    ctx.captions = build_captions()
    ctx.n_frames = len(KEPT); ctx.dur = len(KEPT) / FPS; ctx.fps = FPS; ctx.cell = 15
    ctx.amp = lambda t: float(clamp(env[min(len(env) - 1, max(0, int(t * 100)))]))
    ctx._ot = 0
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
            st = float(ts); i = int(round(st * FPS))
            fr = read_frame_at(SRC, i); mt = read_frame_at('matte.mkv', i, True)
            prep_grid(fr, mt, ctx); ctx._ot = out_time(st)
            out = render_frame(surface, st, out_time(st), fr, mt, ctx)
            Image.fromarray(out[..., :3]).save(f'test/t_{ts}.jpg', quality=88)
            print('saved test/t_%s.jpg' % ts)
        return
    out_path = sys.argv[2]
    bgm = None
    if '--bgm' in sys.argv: bgm = sys.argv[sys.argv.index('--bgm') + 1]
    build_audio(a, ctx.sfx, bgm=bgm).tofile('mix.f32')
    dec = subprocess.Popen([FF, '-v', 'error', '-i', SRC, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    mdec = subprocess.Popen([FF, '-v', 'error', '-i', 'matte.mkv', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgba', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', 'mix.f32',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                            '-c:a', 'aac', '-b:a', '256k', '-shortest', out_path], stdin=subprocess.PIPE)
    keep = set(KEPT.tolist()); t0 = time.time(); n = 0
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
