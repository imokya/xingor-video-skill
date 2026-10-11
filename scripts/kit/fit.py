"""Content fit: which components, transitions and effects suit which kind of content.

Re-colouring does not change what a component *means*: seals, ink bleed, torn xuan paper and vertical verse read as
古风 / 传统文化 in any colour; HUD, scan lines and glitch read as tech. Pick the content's character first, then only use
what fits it.

characters
    traditional  古风 / 诗词 / 传统文化 / 国学 / 茶道 / 书法          -> the ink family, ink turns, acoustic sound
    tech         科技 / AI / 编程 / 数码 / 游戏 / 科幻                -> NEON family + neutral blocks, glitch / wipe / iris / punch
    playful      亲子 / 美食 / 宠物 / 生活 vlog / 开箱                 -> neutral blocks, iris / wipe / punch, bright colour
    cinematic    纪录 / 历史叙事 / 自然 / 旅行 / 人物故事              -> neutral blocks, slow cuts, metal / glass sparingly
    editorial    知识科普 / 读书 / 职场 / 财经 / 观点                  -> neutral blocks, clean cuts / wipes

    import kit.fit as FIT
    ch = FIT.character(transcript_text, topic)          # e.g. 'tech'
    FIT.components_for('list', ch, presenter=True)      # ['ListSteps', 'Steps', 'Checklist']
    FIT.fits('InkList', 'tech')                          # False
"""
import re

ALL = ('traditional', 'tech', 'playful', 'cinematic', 'editorial')
NON_TRAD = ('tech', 'playful', 'cinematic', 'editorial')

# name -> (characters it fits, contexts it works in: 'presenter' = over / beside a talking head, 'narration' = no presenter)
COMPONENTS = {
    # neutral blocks (kit/blocks.py) — any theme, no cultural flavour
    'TitleCard':    (NON_TRAD, ('presenter', 'narration')),
    'TypeBehind':   (('tech', 'editorial', 'cinematic'), ('presenter',)),
    'BigStat':      (NON_TRAD, ('presenter', 'narration')),
    'CompareTable': (('tech', 'editorial', 'playful'), ('presenter', 'narration')),
    'PromptPage':   (('tech', 'editorial'), ('presenter', 'narration')),
    'Callouts':     (('tech', 'editorial', 'playful'), ('presenter', 'narration')),
    'ListSteps':    (NON_TRAD, ('presenter', 'narration')),
    'EndCard':      (NON_TRAD, ('presenter', 'narration')),
    'MetalTitle':   (('tech', 'cinematic'), ('presenter', 'narration')),
    'TalkCard':     (NON_TRAD, ('presenter',)),           # theme='paper' / 'dark'; theme='ink' is traditional
    'LogoCloud':    (('tech', 'playful', 'editorial'), ('presenter', 'narration')),
    'LogoDrop':     (('tech', 'playful', 'editorial'), ('presenter', 'narration')),
    'CardWall':     (('tech', 'editorial', 'cinematic'), ('presenter', 'narration')),
    'WallPrompt':   (('tech', 'editorial'), ('presenter', 'narration')),
    # NEON family (components.py) — tech flavour (HUD, glow, halftone, scanning)
    'BehindText':   (('tech', 'playful', 'editorial', 'cinematic'), ('presenter',)),
    'SplitWord':    (('tech', 'playful', 'editorial'), ('presenter',)),
    'PunchHeadline': (('tech', 'editorial', 'playful'), ('presenter',)),
    'FloatTags':    (('tech', 'playful'), ('presenter',)),
    'Intro':        (('tech',), ('presenter',)),
    'Checklist':    (('tech', 'playful'), ('presenter',)),
    'SwapSymbol':   (('tech', 'playful'), ('presenter',)),
    'SplitHalftone': (('tech',), ('presenter',)),
    'MatteReveal':  (('tech',), ('presenter',)),
    'Compare':      (('tech', 'editorial'), ('presenter',)),
    'CTA':          (('tech', 'playful'), ('presenter',)),
    'Pipeline':     (('tech',), ('presenter',)),
    'Steps':        (('tech',), ('presenter',)),
    'DataCards':    (('tech',), ('presenter',)),
    'SkillCore':    (('tech',), ('presenter',)),
    'Analyze':      (('tech',), ('presenter',)),
    'ThisVideo':    (('tech', 'editorial'), ('presenter',)),
    # ink family (ink.py) — 古风 / 传统文化 only, whatever the colours
    'InkCover':     (('traditional',), ('presenter',)),
    'InkBehind':    (('traditional',), ('presenter',)),
    'TornText':     (('traditional',), ('presenter',)),
    'PoemColumn':   (('traditional',), ('presenter',)),
    'InkLandscape': (('traditional',), ('presenter',)),
    'InkList':      (('traditional',), ('presenter',)),
    'InkEnd':       (('traditional',), ('presenter',)),
    'InkPrompt':    (('traditional',), ('presenter',)),
    'InkScroll':    (('traditional',), ('presenter',)),
    'InkShowcase':  (('traditional',), ('presenter',)),
    'PCover':       (('traditional',), ('narration',)),
    'PRoute':       (('traditional',), ('narration',)),
    'PTorn':        (('traditional',), ('narration',)),
    'PPoem':        (('traditional',), ('narration',)),
    'PWords':       (('traditional',), ('narration',)),
    'PBig':         (('traditional',), ('narration',)),
    'PEnd':         (('traditional',), ('narration',)),
}

TURNS = {
    'ink':    ('traditional',),
    'glitch': ('tech',),
    'punch':  ('tech', 'playful'),
    'iris':   ('playful', 'tech', 'editorial'),
    'wipe':   ('tech', 'playful', 'editorial'),
    'cut':    ALL,
}
SOUNDS = {'ink': ('traditional', 'cinematic'), 'neon': NON_TRAD}
EFFECTS = {   # small effects to build new components from
    'seal / brush stroke / torn paper / ink drop / ink bleed / petals / landscape / vertical verse': ('traditional',),
    'mist / slow fade': ('traditional', 'cinematic', 'editorial'),
    'HUD / scan line / glitch / halftone / glow rim': ('tech',),
    'metal type / rings / glass': ('tech', 'cinematic'),
    'kinetic slide + end dot / typewriter / counter / table / input box / pointer': NON_TRAD,
    'app tiles / logo cloud / logo pile / screenshot wall / prompt pill → brand dot': ('tech', 'playful', 'editorial'),
}

# what a sentence does -> candidate components, best first (filtered by fit and context in components_for)
ROLES = {
    'opening':  ['InkCover', 'PCover', 'TitleCard', 'Intro', 'MetalTitle'],
    'emphasis': ['InkBehind', 'TornText', 'PBig', 'PTorn', 'TypeBehind', 'BehindText', 'SplitWord', 'TitleCard'],
    'number':   ['BigStat', 'DataCards'],
    'list':     ['InkList', 'PWords', 'ListSteps', 'Steps', 'Checklist', 'FloatTags'],
    'compare':  ['TornText', 'PTorn', 'CompareTable', 'Compare', 'SplitHalftone', 'SwapSymbol'],
    'quote':    ['PoemColumn', 'PPoem', 'InkBehind', 'PunchHeadline', 'TypeBehind', 'TitleCard'],
    'question': ['TalkCard', 'PunchHeadline', 'TitleCard', 'InkBehind', 'PBig'],
    'prompt':   ['InkPrompt', 'PromptPage', 'WallPrompt'],
    'product':  ['InkShowcase', 'InkScroll', 'Callouts', 'Analyze', 'CardWall'],
    'tools':    ['LogoCloud', 'LogoDrop', 'FloatTags'],         # a roundup of apps / tools / brands
    'showcase': ['InkScroll', 'InkShowcase', 'CardWall', 'Callouts'],   # many screens / works at once
    'process':  ['InkLandscape', 'PRoute', 'Pipeline', 'ListSteps', 'SkillCore', 'Steps'],
    'cta':      ['InkEnd', 'PEnd', 'EndCard', 'CTA', 'WallPrompt'],
    'explain':  ['TalkCard', 'InkLandscape', 'PWords', 'TitleCard', 'ListSteps'],
}

_KEYS = {
    'traditional': r'诗|词|古风|古代|朝代|唐|宋|元|明|清|汉|传统|国风|国学|文化|书法|茶|禅|水墨|非遗|典籍|苏轼|李白|杜甫|节气|戏曲',
    'tech': r'AI|人工智能|科技|代码|编程|模型|算法|数码|手机|电脑|软件|App|app|skill|Skill|自动|芯片|机器人|工具|插件|提示词',
    'playful': r'宝宝|孩子|萌|宠物|猫|狗|美食|好吃|探店|vlog|开箱|搞笑|零食|玩具',
    'cinematic': r'纪录|故事|人生|命运|宇宙|自然|海洋|山川|旅行|远方|历史上|那一年',
    'editorial': r'读书|知识|学习|职场|财经|理财|方法|科普|观点|效率|习惯|成长',
}


def character(text, topic=''):
    """the content's character from its words (topic counts triple). Ties and no match -> 'editorial'."""
    blob = (topic or '') * 3 + (text or '')
    scores = {k: len(re.findall(rx, blob)) for k, rx in _KEYS.items()}
    best = max(scores, key=lambda k: (scores[k], k == 'editorial'))
    return best if scores[best] else 'editorial'


def fits(name, ch, context=None):
    chars, ctxs = COMPONENTS.get(name, (ALL, ('presenter', 'narration')))
    return ch in chars and (context is None or context in ctxs)


def components_for(role, ch, presenter=True):
    ctx = 'presenter' if presenter else 'narration'
    return [n for n in ROLES.get(role, ROLES['explain']) if fits(n, ch, ctx)]


def turns_for(ch):
    return [t for t, chars in TURNS.items() if ch in chars]


def sound_for(ch):
    return 'ink' if ch in SOUNDS['ink'] and ch == 'traditional' else 'neon'
