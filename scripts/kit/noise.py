"""Organic textures shared by every look: smooth value noise, fractal noise, diffusion arrival maps, blob outlines,
and a helper that turns an alpha array into a tinted skia image."""
import math
import numpy as np
import skia


def _noise(w, h, cx, cy, seed):
    """smooth value noise in [-.5, .5]; cx/cy = feature size in px (cx >> cy gives horizontal fibres)."""
    from PIL import Image
    r = np.random.RandomState(seed)
    sm = (r.rand(h // cy + 3, w // cx + 3) * 255).astype(np.uint8)
    im = Image.fromarray(sm).resize(((w // cx + 3) * cx, (h // cy + 3) * cy), Image.BICUBIC)
    return np.asarray(im, np.float32)[cy:cy + h, cx:cx + w] / 255 - .5


def _fbm(w, h, seed, base, octaves=4):
    """fractal noise in about [-.5, .5]; base = largest feature size in px."""
    out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0.0
    for o in range(octaves):
        cs = max(2, int(base / 2 ** o))
        out += _noise(w, h, cs, cs, seed + o * 13) * amp; tot += amp; amp *= .55
    return out / tot


def _blur(a, r):
    from PIL import Image, ImageFilter
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im, np.float32) / 255


def _arrival(h, w, seeds, seed, rough=.2):
    """ink arrival time in px: distance from the drop points (x, y, radius) + paper-fibre noise."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.full((h, w), 1e9, np.float32)
    for sx, sy, r0 in seeds:
        d = np.minimum(d, np.hypot(xx - sx, yy - sy) - r0)
    d = np.maximum(d, 0)
    S = max(h, w)
    n = (_noise(w, h, max(2, S // 5), max(2, S // 5), seed) + _noise(w, h, max(2, S // 16), max(2, S // 16), seed + 1) * .6
         + _noise(w, h, max(2, S // 45), max(2, S // 45), seed + 2) * .45)
    return d + n * rough * S, n


def _img(alpha, rgb):
    arr = np.empty(alpha.shape + (4,), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = rgb
    arr[..., 3] = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    return skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kUnpremul_AlphaType)


def _ss(x, w):
    x = np.clip(x / w, 0, 1); return x * x * (3 - 2 * x)


def blob_path(cx, cy, R, seed=0, rough=.12, t=0.0, n=120):
    """organic ink-spread outline."""
    r = np.random.RandomState(seed)
    ks = [3, 5, 7, 11, 17]; ph = r.rand(len(ks)) * 6.28
    pth = skia.Path()
    for i in range(n + 1):
        th = i / n * 2 * math.pi
        rr = R * (1 + sum(rough / (1 + j * .6) * math.sin(k * th + ph[j] + t * .5) for j, k in enumerate(ks)))
        x, y = cx + rr * math.cos(th), cy + rr * math.sin(th)
        if i == 0: pth.moveTo(x, y)
        else: pth.lineTo(x, y)
    pth.close()
    return pth
