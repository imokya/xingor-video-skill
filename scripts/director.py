"""First draft of a designed look: theme candidates + a scene plan, from the transcript. Run in the work dir:

    .venv/bin/python SKILL_DIR/scripts/director.py [--topic "关于茶的入门科普"] [--out draft_scenes.py]

It reads transcript.json (+ meta.json) and writes draft_scenes.py:
  - 2–3 theme candidates (kit.theme.design calls) derived from the subject, with contrast reports
  - each sentence's role (opening / emphasis / number / list / compare / quote / question / prompt / product / cta /
    explain), grouped into scenes, each with a suggested component from the shared library and the trigger word
It is a draft for the agent to judge and edit — not a finished edit. See references/design.md.
"""
import argparse, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit.theme as KT
import kit.fit as FIT

# ---------------------------------------------------------------- subject -> theme seeds (starting points, not rules)
SUBJECTS = [
    # keywords, seed, mood, voice, tempo, turn, note
    (('茶', '茶叶', '茶道', '品茶'), '#7A8B5C', 'light', 'literary', 'calm', 'ink', '茶青 tea green on pale paper'),
    (('咖啡', '拿铁', '烘焙'), '#6F4E37', 'light', 'modern', 'medium', 'cut', 'roast brown, warm orange accent'),
    (('海', '海洋', '潜水', '深海'), '#1E6091', 'dark', 'modern', 'medium', 'wipe', 'deep sea blue'),
    (('AI', '人工智能', '模型', '代码', '编程', '科技', 'skill', 'Skill', '工具', '效率'), '#2F5DFF', 'light', 'modern', 'snappy', 'iris', 'clear tech blue'),
    (('赛博', '未来', '元宇宙', '游戏'), '#7B2FF7', 'dark', 'techno', 'snappy', 'glitch', 'neon violet'),
    (('健身', '运动', '跑步', '训练', '减脂'), '#FF4D2E', 'dark', 'modern', 'snappy', 'punch', 'energetic red-orange'),
    (('美食', '做饭', '菜', '餐', '烘焙'), '#E4572E', 'light', 'modern', 'medium', 'cut', 'appetite tomato red'),
    (('旅行', '旅游', '城市', '风景', '自驾'), '#2A9D8F', 'light', 'modern', 'medium', 'wipe', 'travel teal'),
    (('孩子', '宝宝', '儿童', '亲子', '母婴'), '#FFB000', 'light', 'modern', 'snappy', 'iris', 'sunny orange'),
    (('理财', '投资', '财经', '基金', '股票', '收入'), '#0B6E4F', 'light', 'modern', 'medium', 'cut', 'money green'),
    (('历史', '朝代', '古代', '文化', '传统', '非遗'), '#8C2F1B', 'light', 'literary', 'calm', 'ink', 'lacquer red on paper'),
    (('春', '花', '樱花', '浪漫', '恋爱'), '#E8A0B4', 'light', 'hand', 'calm', 'cut', 'blossom pink, calligraphy'),
    (('夜', '星空', '宇宙', '天文'), '#4B3FD6', 'dark', 'techno', 'calm', 'cut', 'night indigo'),
    (('健康', '医疗', '睡眠', '心理'), '#2BB3A3', 'light', 'modern', 'calm', 'cut', 'calm mint'),
    (('时尚', '穿搭', '美妆', '护肤'), '#D6336C', 'light', 'modern', 'snappy', 'wipe', 'fashion rose'),
    (('读书', '学习', '教育', '考试', '知识'), '#3D5A80', 'light', 'literary', 'medium', 'cut', 'ink blue for study'),
    (('汽车', '电车', '驾驶'), '#D32F2F', 'dark', 'modern', 'snappy', 'wipe', 'racing red'),
]
FALLBACK = ('#3D5A80', 'light', 'modern', 'medium', 'cut', 'neutral ink blue (no strong subject colour found)')

# ---------------------------------------------------------------- sentence roles
ROLE_RULES = [
    ('cta', r'评论区|关注|点赞|留言|私信|收藏|转发|链接|下期见'),
    ('prompt', r'告诉\s*AI|提示词|输入|对它说|只需要说|跟它说|prompt'),
    ('quote', r'[《「“"]|曰|古人云|有句话|说过'),
    ('compare', r'vs|VS|对比|相比|比起|而不是|不是.{0,8}而是|以前.{0,12}现在|手动.{0,8}自动'),
    ('number', r'\d|[一二三四五六七八九十百千万两几]+\s*(个|种|步|倍|秒|分钟|小时|天|年|%|成|元|块|万|亿|次|条|帧)'),
    ('list', r'首先|第一|其次|然后|接下来|最后|以及|还有|[^、]+、[^、]+、'),
    ('question', r'[？?]|为什么|怎么|如何|是不是|吗$|呢$|什么'),
    ('product', r'App|app|软件|界面|截图|网站|功能|按钮|页面|插件'),
    ('emphasis', r'其实|竟然|居然|最|关键|重点|一定|千万|真正|根本|核心'),
]

STOP = set('的了是在我你他她它们这那和与就也都还又很把被给让对从到为着过一个一些这个那个什么怎么可以已经因为所以但是如果然后其实非常就是'.split() + list('的了是在我你他她它这那和与就也都还又很把被给让对从到为着过'))


def role_of(text, i, n):
    if i == 0: return 'opening'
    for role, rx in ROLE_RULES:
        if re.search(rx, text): return role
    return 'emphasis' if len(re.sub(r'\W', '', text)) <= 9 else 'explain'


def trigger(seg, role):
    """(word, time) to trigger the visual on: a number for 'number', the word after 其实/最 for emphasis, else the
    longest content word."""
    words = [(w['w'].strip(), w['s']) for w in seg['words'] if w['w'].strip()]
    if not words: return ('', seg['start'])
    if role == 'number':
        for w, s in words:
            if re.search(r'\d|[一二三四五六七八九十百千万两]', w): return (w, s)
    if role == 'emphasis':
        for k, (w, s) in enumerate(words[:-1]):
            if re.search(r'其实|竟然|最|关键|重点|真正', w): return (words[k + 1][0], words[k + 1][1])
    cand = [(w, s) for w, s in words if w not in STOP and len(re.sub(r'\W', '', w)) >= 2]
    return max(cand, key=lambda x: len(x[0])) if cand else words[0]


def themes_for(text, topic, ch):
    blob = (topic or '') * 3 + text
    scores = []
    for kws, seed, mood, voice, tempo, turn, note in SUBJECTS:
        n = sum(blob.count(k) for k in kws)
        if n: scores.append((n, (seed, mood, voice, tempo, turn, note, kws[0])))
    scores.sort(key=lambda x: -x[0])
    picks = [s for _, s in scores[:2]] or [FALLBACK + ('通用',)]
    out = []   # (name, theme, design-kwargs) — turn and sound are corrected to fit the content's character
    ok_turns = FIT.turns_for(ch)
    for seed, mood, voice, tempo, turn, note, name in picks:
        if turn not in ok_turns: turn = ok_turns[0] if ch != 'traditional' else 'ink'
        if ch != 'traditional' and voice == 'hand' and name not in ('春',): voice = 'modern'
        kw = dict(seed=seed, mood=mood, voice=voice, tempo=tempo, turn=turn, sfx=FIT.sound_for(ch), note=note)
        out.append((name, KT.design(name, **kw), kw))
    base_name, base, bkw = out[0]   # a contrasting alternative: same seed, opposite mood
    kw = dict(bkw, mood='dark' if bkw['mood'] == 'light' else 'light', voice='modern', note='opposite mood of the first candidate')
    out.append((base_name + '·' + kw['mood'], KT.design(base_name + '·' + kw['mood'], **kw), kw))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--topic', default='')
    ap.add_argument('--out', default='draft_scenes.py')
    args = ap.parse_args()
    segs = json.load(open('transcript.json'))
    meta = json.load(open('meta.json')) if os.path.exists('meta.json') else {}
    narration = meta.get('audio_only', False)
    caps = [l.strip() for l in open('captions.txt')] if os.path.exists('captions.txt') else [s['text'] for s in segs]
    text = ''.join(caps)
    ch = FIT.character(text, args.topic)
    themes = themes_for(text, args.topic, ch)

    # roles + grouping into scenes (3–8 s; a role change or a long scene starts a new one)
    rows = []
    for i, s in enumerate(segs):
        cap = caps[i] if i < len(caps) else s['text']
        r = role_of(cap, i, len(segs))
        rows.append(dict(i=i, t0=s['start'], t1=s['end'], text=cap.replace('|', ''), role=r, trig=trigger(s, r)))
    scenes = []
    for r in rows:
        if scenes and (scenes[-1]['role'] == r['role'] or r['role'] in ('explain',)) and r['t1'] - scenes[-1]['t0'] < 8:
            scenes[-1]['rows'].append(r); scenes[-1]['t1'] = r['t1']
        else:
            scenes.append(dict(role=r['role'], t0=r['t0'], t1=r['t1'], rows=[r]))
    for a, b in zip(scenes, scenes[1:]):   # boundaries in the gaps
        mid = round((a['t1'] + b['t0']) / 2, 2); a['t1'] = b['t0'] = mid
    scenes[0]['t0'] = 0.0

    L = ['"""DRAFT from director.py — judge and edit before rendering (references/design.md).',
         f'{"narration only (no presenter)" if narration else "presenter video"}; {len(scenes)} scenes; '
         f'content character: {ch} — only components / turns that fit it are suggested (scripts/kit/fit.py).', '"""',
         'from components import *', 'from ink import *', 'from kit.blocks import *', 'import kit.theme as KT', '',
         '# ---- theme candidates (pick one, or design your own from the content; check KT.report and a swatch)']
    for k, (name, th, kw) in enumerate(themes):
        L.append(f"{'' if k == 0 else '# '}THEME = KT.design({name!r}, {kw['seed']!r}, {kw['mood']!r}, voice={kw['voice']!r}, "
                 f"tempo={kw['tempo']!r}, turn={kw['turn']!r}, sfx={kw['sfx']!r})   # {kw['note']}")
    L += ['', "KEYWORDS = " + repr([w for w, _ in Counter(r['trig'][0] for r in rows if len(r['trig'][0]) >= 2).most_common(12)]), '', '',
          'def build_scenes():', '    return [']
    for sc in scenes:
        r0 = sc['rows'][0]; word, wt = r0['trig']
        for r in sc['rows']: L.append(f"        # [{r['role']}] {r['text']}")
        sug = FIT.components_for(sc['role'], ch, presenter=not narration)
        L.append(f"        # suggested ({ch}): {' / '.join(sug[:4]) or 'design a new component'}   trigger: {word!r} @ {wt:.2f}")
        if ch == 'traditional':
            ph = (f"PBig({sc['t0']:.2f}, {sc['t1']:.2f}, lines=[({wt:.2f}, {word!r})])" if narration else
                  f"InkBehind({sc['t0']:.2f}, {sc['t1']:.2f}, text={word!r}, text_t={wt:.2f})")
        else:
            ph = f"TitleCard({sc['t0']:.2f}, {sc['t1']:.2f}, title=({wt:.2f}, {word!r}))"
        L.append(f"        {ph},   # placeholder — replace with the suggested component")
    L += ['    ]', '']
    open(args.out, 'w').write('\n'.join(L))

    print('theme candidates:')
    for name, th, kw in themes: print('  ' + KT.report(th).replace('\n', '\n  '))
    print(f'\ncontent character: {ch}  (fitting turns: {", ".join(FIT.turns_for(ch))}; sound: {FIT.sound_for(ch)})')
    print(f'{len(scenes)} scenes ({"narration" if narration else "presenter"}):')
    for sc in scenes:
        sug = ' / '.join(FIT.components_for(sc['role'], ch, presenter=not narration)[:3]) or 'design new'
        print(f"  {sc['t0']:6.2f}-{sc['t1']:6.2f}  {sc['role']:8s} -> {sug:40s} | {sc['rows'][0]['text'][:28]}")
    print(f'\nwrote {args.out}')


if __name__ == '__main__':
    main()
