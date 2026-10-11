"""Themes: every colour, font, motion and sound choice a look needs, as named tokens.

A Theme is what the agent designs for a project when the user doesn't ask for a named style: derive it from the
content (subject, mood, audience), not from a preset. Presets are references and what a named style asks for.

    import kit.theme as KT
    th = KT.design('茶事', seed='#7A8B5C', mood='light', voice='literary', tempo='calm', turn='ink')
    print(KT.report(th))          # contrast of every text/background pair (WCAG)
    THEME = th                    # in scenes.py (a Theme, a preset name, or a dict of overrides)

Colour roles
    bg       page background            surface  lighter panels, cards, halos behind small text
    ink      main text                  muted    secondary text, credits
    accent   the ONE loud colour (keywords, seals, active states)
    accent2  quiet secondary colour     wash     pale tint for big decorative shapes / ghost text
    line     hairlines and rules
Type roles (keys of fx.FAM): display, head, body, label, num, hand
Motion: tempo (calm / medium / snappy -> entrance durations), enter ('fade' / 'rise' / 'pop' / 'slide')
Chrome: turn ('ink' | 'glitch' | 'wipe' | 'punch' | 'cut'), sfx ('neon' | 'ink'), background ('paper' | 'dark' | 'plain')
"""
import colorsys
from dataclasses import dataclass, field, replace as _replace


@dataclass
class Theme:
    name: str
    family: str                  # which built-in chrome a renderer uses: 'neon', 'ink', or 'custom'
    bg: tuple
    surface: tuple
    ink: tuple
    muted: tuple
    accent: tuple
    accent2: tuple
    wash: tuple
    line: tuple
    fonts: dict = field(default_factory=dict)
    tempo: str = 'medium'
    enter: str = 'rise'
    turn: str = 'cut'
    sfx: str = 'neon'
    background: str = 'plain'
    note: str = ''

    def font(self, role):
        return self.fonts.get(role) or FONT_VOICES['modern'][role]

    @property
    def dur(self):
        """base entrance duration in seconds for this tempo."""
        return {'calm': .9, 'medium': .5, 'snappy': .32}.get(self.tempo, .5)

    def with_(self, **kw):
        return _replace(self, **kw)


# ---------------------------------------------------------------- colour maths
def hex_rgb(h):
    h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_hex(c):
    return '#%02X%02X%02X' % tuple(int(round(v)) for v in c)


def _lin(v):
    v /= 255; return v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4


def luminance(c):
    r, g, b = (_lin(v) for v in c); return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + .05) / (min(la, lb) + .05)


def hls(c):
    return colorsys.rgb_to_hls(*(v / 255 for v in c))


def from_hls(h, l, s):
    return tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(h % 1, max(0, min(1, l)), max(0, min(1, s))))


def mix(a, b, k):
    return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


def _accent(h, l, s, bg, darker):
    """the loud colour: stays in the seed's hue family (dull seeds get saturated, never swapped for the complement);
    hues that turn muddy when darkened for contrast (yellows) rotate toward orange instead."""
    s = max(s, .62)
    for shift in (0, -.025, -.05, -.075, -.1):
        c = _push(from_hls(h + shift, l, s), bg, 3.0, darker)
        if not darker or hls(c)[1] >= .4 or not (.09 < h % 1 < .2): return c
    return c


def _push(c, against, target, darker):
    """move c's lightness away from `against` until contrast >= target (keeps hue and saturation)."""
    h, l, s = hls(c)
    for _ in range(60):
        if contrast(c, against) >= target: break
        l += -.012 if darker else .012
        c = from_hls(h, l, s)
    return c


# ---------------------------------------------------------------- type voices (fx.FAM keys)
FONT_VOICES = {
    'modern':   dict(display='heavy', head='heavy', body='bold', label='med', num='num', hand='heavy'),     # 兰亭黑 / 苹方
    'techno':   dict(display='disp', head='heavy', body='bold', label='mono', num='num', hand='disp'),      # Avenir Condensed / Menlo
    'literary': dict(display='song', head='song', body='songb', label='songr', num='songb', hand='kai'),    # 宋体
    'hand':     dict(display='xing', head='song', body='songb', label='kair', num='songb', hand='xing'),    # 行楷 / 楷体
}

# ---------------------------------------------------------------- presets (exact values of the built-in looks)
PRESETS = {
    'neon': Theme('neon', 'neon', bg=(5, 7, 13), surface=(24, 30, 46), ink=(255, 255, 255), muted=(150, 158, 175),
                  accent=(198, 255, 46), accent2=(64, 120, 255), wash=(150, 92, 255), line=(64, 120, 255),
                  fonts=FONT_VOICES['techno'], tempo='snappy', enter='pop', turn='glitch', sfx='neon', background='dark',
                  note='NEON LAB: deep ink + acid lime, glitch / lime-wipe cuts'),
    'poetry-ink': Theme('poetry-ink', 'ink', bg=(241, 238, 230), surface=(248, 246, 240), ink=(22, 44, 96), muted=(100, 104, 114),
                        accent=(200, 70, 40), accent2=(92, 112, 148), wash=(170, 181, 200), line=(92, 112, 148),
                        fonts=FONT_VOICES['literary'], tempo='calm', enter='fade', turn='ink', sfx='ink', background='paper',
                        note='诗墨国风: xuan paper, indigo ink, one cinnabar accent, ink-spread page turns'),
    'bronze': Theme('bronze', 'custom', bg=(12, 26, 28), surface=(28, 46, 46), ink=(240, 230, 210), muted=(150, 160, 150),
                    accent=(232, 196, 120), accent2=(120, 170, 150), wash=(60, 90, 84), line=(232, 196, 120),
                    fonts=FONT_VOICES['literary'], tempo='calm', enter='fade', turn='cut', sfx='neon', background='dark',
                    note='文物纪录片 palette (rendered by scripts/doc): dark bronze stage, gold'),
    'flat': Theme('flat', 'custom', bg=(241, 237, 228), surface=(255, 255, 255), ink=(16, 16, 18), muted=(70, 70, 76),
                  accent=(238, 75, 58), accent2=(44, 46, 232), wash=(225, 220, 210), line=(16, 16, 18),
                  fonts=FONT_VOICES['modern'], tempo='snappy', enter='slide', turn='cut', sfx='neon', background='plain',
                  note='撞色测评 palette (rendered by scripts/review): black / cream / coral / electric blue blocks'),
}
ACTIVE = PRESETS['neon']     # the theme of the current render (render.py sets it); kit.blocks reads it
ALIASES = {'ink': 'poetry-ink', '诗墨': 'poetry-ink', 'neon-lab': 'neon', 'documentary': 'bronze', 'flat-review': 'flat'}


def resolve(spec):
    """THEME in scenes.py -> Theme. Accepts a Theme, a preset name, or a dict ({'base': 'neon', 'accent': '#FF6A3D', …})."""
    if isinstance(spec, Theme): return spec
    if spec is None: return PRESETS['neon']
    if isinstance(spec, str): return PRESETS[ALIASES.get(spec, spec)]
    d = dict(spec); base = resolve(d.pop('base', 'neon'))
    d = {k: (hex_rgb(v) if isinstance(v, str) and v.startswith('#') else v) for k, v in d.items()}
    return base.with_(**d)


# ---------------------------------------------------------------- designer
def design(name, seed, mood='light', accent=None, voice='modern', tempo='medium', enter='rise', turn='cut',
           sfx=None, background=None, family='custom', note=''):
    """A complete theme from one seed colour (the subject's own colour: tea green, ocean blue, brick red…).

    mood 'light' = pale tinted page, dark ink;  'dark' = deep tinted page, light ink.
    accent: the one loud colour; default = the seed pushed to full strength, or its complement when the seed is dull.
    Every text pair is pushed to WCAG contrast: ink >= 7:1 and muted >= 4.5:1 on bg, accent >= 3:1 (large text)."""
    seed = hex_rgb(seed) if isinstance(seed, str) else tuple(seed)
    h, l, s = hls(seed)
    if mood == 'dark':
        bg = from_hls(h, .07, min(.45, s * .6 + .1)); surface = from_hls(h, .13, min(.4, s * .5 + .08))
        ink = from_hls(h, .95, .12); muted = from_hls(h, .72, .14)
        acc = hex_rgb(accent) if isinstance(accent, str) else (accent or _accent(h, .6, max(s, .8), bg, False))
        acc2 = from_hls(h + .08, .55, .45); wash = from_hls(h, .22, .35); line = from_hls(h, .35, .3)
        darker = False
    else:
        bg = from_hls(h, .945, min(.3, s * .35 + .06)); surface = from_hls(h, .985, min(.25, s * .3 + .04))
        ink = from_hls(h, .16, min(.55, s * .6 + .15)); muted = from_hls(h, .42, .1)
        acc = hex_rgb(accent) if isinstance(accent, str) else (accent or _accent(h, .47, max(s, .7), bg, True))
        acc2 = from_hls(h + .06, .5, .32); wash = mix(from_hls(h, .7, .3), bg, .45); line = mix(ink, bg, .72)
        darker = True
    ink = _push(ink, bg, 7.0, darker); muted = _push(muted, bg, 4.5, darker); acc = _push(acc, bg, 3.0, darker)
    return Theme(name, family, bg=bg, surface=surface, ink=ink, muted=muted, accent=acc, accent2=acc2, wash=wash, line=line,
                 fonts=dict(FONT_VOICES.get(voice, FONT_VOICES['modern'])), tempo=tempo, enter=enter, turn=turn,
                 sfx=sfx or ('ink' if voice in ('literary', 'hand') else 'neon'),
                 background=background or ('dark' if mood == 'dark' else 'paper'), note=note)


def report(th):
    """contrast table for the text/background pairs that matter; lines marked !! fail."""
    rows = [('ink / bg', th.ink, th.bg, 7.0), ('muted / bg', th.muted, th.bg, 4.5), ('accent / bg', th.accent, th.bg, 3.0),
            ('ink / surface', th.ink, th.surface, 7.0), ('accent / surface', th.accent, th.surface, 3.0)]
    out = [f'{th.name} ({th.family}, {th.tempo}, turn={th.turn}, sfx={th.sfx}, voice={th.font("display")})']
    for label, a, b, need in rows:
        r = contrast(a, b)
        out.append(f'  {"ok" if r >= need else "!!"} {label:17s} {r:5.2f}:1  (need {need}:1)  {rgb_hex(a)} on {rgb_hex(b)}')
    return '\n'.join(out)
