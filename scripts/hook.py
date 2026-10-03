"""Find hook (钩子 / cold-open) candidates in an analyzed talking-head video.

Run from the work dir after analyze.py:
    .venv/bin/python <skill>/scripts/hook.py [--top 12] [--budget 8]

Scores every window of 1-3 consecutive transcript segments on
  - loudness relative to the whole video (excited delivery),
  - speech rate (energy),
  - punch / curiosity cue words (其实, 竟然, 最, 免费, 秘密 ...), questions, exclamations and numbers,
and penalizes windows inside the opening seconds (they play again right after the hook), filler starts
and long pauses inside the window.

Prints a ranked table, writes hook_candidates.json and a suggested `HOOK = dict(...)` block whose
total length fits a budget derived from the video length (override with --budget seconds).
The scores only shortlist; pick the final clips by reading them (see SKILL.md, "Hook").
"""
import json, re, argparse, wave, os
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--top', type=int, default=12)
ap.add_argument('--budget', type=float, default=None, help='total hook seconds (default: from video length)')
ap.add_argument('--min', dest='min_len', type=float, default=1.8)
ap.add_argument('--max', dest='max_len', type=float, default=9.0)
args = ap.parse_args()

segs = json.load(open('transcript.json'))
meta = json.load(open('meta.json'))
DUR = meta['frames'] / meta['fps']

# loudness envelope (10ms hop) from the 16k analysis wav
w = wave.open('audio16k.wav')
a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
hop = 160
n = len(a) // hop
rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1))
db = 20 * np.log10(rms + 1e-6)
voiced = db > np.percentile(db, 50) - 15
ref = np.median(db[voiced]) if voiced.any() else -30.0
spread = (np.percentile(db[voiced], 90) - ref + 1e-6) if voiced.any() else 6.0


def loud(s0, s1):
    i0, i1 = int(s0 * 100), max(int(s0 * 100) + 1, int(s1 * 100))
    v = db[i0:i1][voiced[i0:i1]]
    return float((np.percentile(v, 75) - ref) / spread) if len(v) else -1.0


CUES = {
    3: ['竟然', '居然', '没想到', '秘密', '真相', '千万', '绝对', '震惊', '爆款', '爆火', '翻倍', '免费', '一键', '直接', '其实'],
    2: ['关键', '生动', '惊艳', '低很多', '搞定', '成功', '重点', '核心', '简单', '只需要', '只要', '不需要', '不用', '根本', '马上', '立刻', '效果', '结果',
        '赚', '省', '成本', '为什么', '怎么', '你知道', '注意', '一定', '不是', '而是', '全部', '自动', '神器', '火', '本地'],
    1: ['今天', '教', '方法', '技巧', '真的', '非常', '特别', '超级', '完全'],
}
SUPER = re.compile(r'最(?![后近初终])')          # 最好/最强, not 最后/最近
CTA = ('三连', '关注', '点赞', '订阅', '评论区', '留言', '转发', '收藏', '下期', '再见')
FILLER = ('嗯', '啊', '那个', '然后', '就是', '所以', '那么', '好', '对')
NUM = re.compile(r'(\d+(\.\d+)?|[一二两三四五六七八九十百千万]+)(%|倍|秒|分钟|小时|天|块|元|个|次|步|万|亿)')


def text_of(ss):
    return ''.join(s['text'].strip() for s in ss)


def cue_score(t):
    sc = 0.0; hits = []
    for wgt, words in CUES.items():
        for wd in words:
            if wd in t:
                sc += wgt; hits.append(wd)
    if SUPER.search(t): sc += 2; hits.append('最')
    if any(m.group(1) != '一' for m in NUM.finditer(t)): sc += 2; hits.append('#num')
    if re.search('[?？]', t): sc += 2; hits.append('?')
    if re.search('[!！]', t): sc += 1.5; hits.append('!')
    return min(sc, 9) / 9, hits


def bounds(ss):
    ws = [wd for s in ss for wd in s['words']] or [{'s': ss[0]['start'], 'e': ss[-1]['end']}]
    s0 = max(0.0, ws[0]['s'] - .08)
    s1 = ws[-1]['e'] + .15
    return s0, min(s1, DUR)


def max_gap(ss):
    ws = [wd for s in ss for wd in s['words']]
    return max([b['s'] - a_['e'] for a_, b in zip(ws, ws[1:])] or [0])


cands = []
for i in range(len(segs)):
    for k in (1, 2, 3):
        ss = segs[i:i + k]
        if len(ss) < k: break
        s0, s1 = bounds(ss)
        d = s1 - s0
        if d < args.min_len or d > args.max_len: continue
        t = text_of(ss)
        chars = len(re.sub(r'[\s，。、,.!?！？；;：:]', '', t))
        if chars < 5: continue
        L = loud(s0, s1)
        rate = chars / max(d, .1)
        cs, hits = cue_score(t)
        score = 1.6 * cs + .9 * L + .25 * np.clip((rate - 4) / 3, -1, 1)
        if s0 < min(4.0, DUR * .08): score -= .8          # opening lines play again right after the hook
        if t.startswith(FILLER): score -= .3
        if any(x in t for x in CTA): score -= 1.2           # calls to action are not hooks
        if s1 > DUR * .92: score -= .4                      # closing lines rarely tease
        if max_gap(ss) > .9: score -= .4                   # a long pause inside reads as dead air
        if 2.5 <= d <= 6.5: score += .2                    # sweet spot for a single hook clip
        cands.append(dict(s0=round(s0, 2), s1=round(s1, 2), dur=round(d, 2), score=round(float(score), 3),
                          loud=round(L, 2), rate=round(rate, 1), cues=hits, text=t, segs=[i, i + k - 1]))

cands.sort(key=lambda c: -c['score'])

# budget from video length: short clips get a short tease, long videos a longer cold open
if args.budget: budget = args.budget
elif DUR < 40: budget = 3.5
elif DUR < 75: budget = 6
elif DUR < 180: budget = 10
elif DUR < 600: budget = 20
else: budget = 32
max_clips = 1 if budget <= 4 else 2 if budget <= 8 else 3 if budget <= 20 else 4

picked = []
for c in cands:
    if len(picked) >= max_clips: break
    if any(not (c['s1'] <= p['s0'] or c['s0'] >= p['s1']) for p in picked): continue
    if sum(p['dur'] for p in picked) + c['dur'] > budget * 1.25: continue
    picked.append(c)

json.dump(dict(duration=round(DUR, 2), budget=budget, candidates=cands[:40], suggested=picked),
          open('hook_candidates.json', 'w'), ensure_ascii=False, indent=1)

print(f'video {DUR:.1f}s → hook budget ≈ {budget:g}s, up to {max_clips} clip(s)\n')
print(' rank  score   time            dur   loud  cues                text')
for r, c in enumerate(cands[:args.top], 1):
    print(f' {r:>4}  {c["score"]:5.2f}  {c["s0"]:6.2f}-{c["s1"]:6.2f}  {c["dur"]:4.1f}s {c["loud"]:5.2f}  {",".join(c["cues"])[:18]:18s}  {c["text"][:40]}')
print('\nsuggested (strongest first; reorder for the story you want):')
print('HOOK = dict(')
print('    clips=[')
for c in picked:
    print(f'        ({c["s0"]}, {c["s1"]}),  # {c["text"][:40]}')
print('    ],')
print("    title='',            # 2-6 char punch shown behind the person on the first clip ('' = none)")
print("    kicker='HIGHLIGHT · 精彩预告',")
print("    outro='正片开始',")
print(')')
