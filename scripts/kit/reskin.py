"""Re-skin every built-in template with a designed Theme.

The NEON templates (components.py) and the paper / ink templates (ink.py) look up their colours and fonts as module
names at draw time; apply() rebinds those names to the theme's tokens, regenerates the cached paper texture and maps
the template fonts onto the theme's type voice. Presets never call it, so their output is untouched.

    light themes  -> the paper family reads best (ink.py: InkBehind, TornText, PoemColumn, InkShowcase, P* layouts…)
    dark themes   -> the NEON family reads best (components.py: BehindText, Pipeline, Steps, DataCards, CTA…)
"""
import kit.theme as KT


def _on(accent, cands):
    """the candidate colour that reads best ON the accent (text on accent chips)."""
    return max(cands, key=lambda c: KT.contrast(c, accent))


def _swap(mod, table):
    """colours captured at import time (class attributes like `rgb = MO`, defaults like `seal(rgb=ZHU)`) -> theme."""
    def fix_fn(f):
        if getattr(f, '__defaults__', None):
            f.__defaults__ = tuple(table.get(d, d) if isinstance(d, tuple) else d for d in f.__defaults__)
    for obj in list(vars(mod).values()):
        if getattr(obj, '__module__', None) != mod.__name__: continue
        if isinstance(obj, type):
            for k, v in list(vars(obj).items()):
                if isinstance(v, tuple) and v in table: setattr(obj, k, table[v])
                elif callable(v): fix_fn(v)
        elif callable(obj):
            fix_fn(obj)


def apply(th):
    if th.family != 'custom':
        return
    import fx, components as CP, ink as IK
    ink0, neon0 = KT.PRESETS['poetry-ink'], KT.PRESETS['neon']
    on_acc = _on(th.accent, [th.bg, th.surface, th.ink])
    ink_table = {ink0.bg: th.bg, ink0.surface: th.surface, ink0.ink: th.ink, ink0.accent2: th.accent2, ink0.wash: th.wash,
                 ink0.accent: th.accent, ink0.muted: th.muted}
    neon_table = {neon0.accent: th.accent, neon0.accent2: th.accent2, neon0.wash: th.wash, neon0.muted: th.muted,
                  (5, 7, 13): on_acc,
                  (244, 244, 240): th.bg, (16, 18, 22): th.ink, (128, 132, 140): th.muted}
    _swap(IK, ink_table)
    _swap(fx, neon_table)
    _swap(CP, {**neon_table, **ink_table})
    # paper / ink family
    IK.XUAN, IK.XUAN_L, IK.MO, IK.DAI, IK.QIAN, IK.ZHU, IK.HUI = th.bg, th.surface, th.ink, th.accent2, th.wash, th.accent, th.muted
    IK._TEX.pop('paper', None)
    IK.PAPER_STYLE = th.background
    IK.TURN = th.turn
    # NEON family (names were copied into each module by `from fx import *`)
    neon = dict(LIME=th.accent, BLUE=th.accent2, VIOLET=th.wash, GREY=th.muted, INK=on_acc)
    for mod in (fx, CP, IK):
        for k, v in neon.items():
            setattr(mod, k, v)
    fx.DARK_BG = (th.surface, KT.mix(th.surface, th.bg, .6), th.bg)
    # TalkCard's paper / ink variants
    CP.PAPER, CP.PAPER_INK, CP.PAPER_GREY = th.bg, th.ink, th.muted
    CP.INK_MO, CP.INK_ZHU, CP.INK_HUI, CP.INK_PAPER = th.ink, th.accent, th.muted, th.surface
    # type voice: template font kinds -> the theme's roles
    r = th.font
    fx.FONT_ALIAS.clear()
    fx.FONT_ALIAS.update(song=r('head'), songb=r('body'), songr=r('label'), kai=r('hand'), kair=r('hand'), xing=r('display'),
                         heavy=r('head'), disp=r('display'), dispu=r('display'), bold=r('body'), mono=r('label'),
                         monor=r('label'), num=r('num'))
    fx._fonts.clear()
