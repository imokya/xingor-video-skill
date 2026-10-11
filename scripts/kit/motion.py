"""Easing and timing, shared by every look. All times are seconds."""
import math


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def P(t, t0, d=0.4):
    """normalized progress of an animation starting at t0 lasting d."""
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def eo(x):  # ease out cubic
    x = clamp(x); return 1 - (1 - x) ** 3


def eio(x):
    x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def eob(x, s=1.9):  # ease out back
    x = clamp(x); return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def eexp(x):
    x = clamp(x); return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def window(t, t0, t1, fi=0.25, fo=0.25):
    """1 inside [t0,t1] with fades."""
    return clamp(min((t - t0) / fi if fi else 1, (t1 - t) / fo if fo else 1))


def lerp(a, b, x):
    return a + (b - a) * x


def spring(x):
    """damped spring 0->1 with a small overshoot; feels 'physical' for card moves."""
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - math.exp(-6.5 * x) * math.cos(8.0 * x) * (1 - .25 * x)
