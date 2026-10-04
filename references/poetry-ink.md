# poetry-ink · 诗墨国风 — style guide & scene catalog

The second look of this skill. It replaces NEON LAB's loud lime/glitch language with xuan paper, indigo ink,
a single cinnabar accent and slow, natural ink-wash motion. Use it when the user asks for 水墨 / 诗词 / 国风 /
中国风 / 古风 / 东方美学 / 诗意 / "poetry-ink", or when the content itself is poetic, cultural or contemplative
(诗词赏析, 传统文化, 茶, 书法, 旅行随笔, 读书分享…).

Turn it on with one line in the project's `scenes.py`:
```python
from components import *
from ink import *
THEME = 'poetry-ink'
```
The renderer then switches: video grade (soft, desaturated, paper-lifted), subtitles (indigo Songti on a paper
halo, keywords in cinnabar), transitions (every cut dissolves through spreading ink instead of glitch / lime
wipe), the hook look, the sound palette, the progress hairline (thin cinnabar) and the end fade (to paper).

## Contents
1. Palette & type
2. Canvas, layers, the person
3. Motion language (水墨动画)
4. Sound
5. Scene catalog
6. Rhythm & structure
7. Poetry: accuracy and taste
8. Pitfalls

---

## 1. Palette & type
| token | rgb | use |
|---|---|---|
| XUAN | (241,238,230) | 宣纸 paper background (procedural texture: blotches, fibres, aged edges) |
| XUAN_L | (248,246,240) | lighter paper: cards, halos, mist, caption halo |
| MO | (22,44,96) | 青黛 indigo ink: headlines, captions, poems |
| DAI | (92,112,148) | 淡墨 diluted ink: ghost characters, near hills, hairlines |
| QIAN | (170,181,200) | pale wash: far mountains, moon rim |
| ZHU | (200,70,40) | 朱砂 cinnabar: seals, dots, short brush strokes, keywords — **the only warm accent** |
| HUI | (100,104,114) | grey notes, authors, labels |

Cinnabar is precious: one seal, one dot, one stroke, keywords. Never fill large areas with it (the setting sun
in `InkLandscape` is the one exception). Everything else is ink in different dilutions — 墨分五色.

Fonts (`F(kind, size)`):
- `song` Songti SC Black: headlines (100–120px), behind text (200–260px), ghost characters (450–500px)
- `songb` Songti SC Bold: subtitles (48px), spaced sub lines (30px), chips
- `songr` Songti SC Regular: letter-spaced labels and vertical mottos (22–26px, spacing 6–9)
- `kai` / `kair` Kaiti SC: poems (80–90px vertical), seals, farewell lines
- `xing` Xingkai SC (行楷): calligraphic punch words — use sparingly, 2–4 characters, ≥220px

Letter-spacing is part of the look: small text is always spaced (`spacing=6..9`). Latin inside Songti is fine
("AI", "GPT").

## 2. Canvas, layers, the person
- 1920×1080. **y > 900 belongs to subtitles**. A paper mist rises from the bottom in every scene, which also
  hides where the cutout is cropped (人物下半身隐入云雾).
- Three modes:
  - `full` — the real video, softly graded. Ink type needs paper behind it: `InkBehind` lays a left paper mist
    (`left_mist`) and the characters bleed in behind the person.
  - `scroll` — the ink "dark scene": the person is cut out, scaled to ~0.74 at the right (head x≈1540), with a
    soft paper halo, standing on xuan paper like the scholar in a scroll painting. Content lives at
    x 110–1150, y 150–860. `ink_person=0..1` turns the cutout into an indigo duotone (人物水墨化); keep it
    ≤0.5 for faces unless the user wants a stylised look.
  - `talk` — `TalkCard(theme='ink')`: the presenter in a paper card with a cinnabar-dot name pill,
    Songti headlines with cinnabar `[highlights]`, paper chips with a cinnabar tick.
- Composition follows the reference cover: big pale ghost characters bleeding off two opposite edges, a thin
  orbit hairline, halftone dot fields, a cut-corner paper card with a soft shadow, an embossed ripple, a
  landscape tucked into the card's lower right, a vertical motto with a seal near the card's right edge, a
  small spaced corner motto top-right. 留白: leave at least a third of the frame quiet.

## 3. Motion language (水墨动画)
Slow and natural. Typical durations are 2–3× NEON's; nothing bounces, nothing flashes.
- **Ink is for the page turns.** Every cut is a 水墨晕开 page turn: a few drops land one after another, each
  spreads fast then slows (like real diffusion) along a domain-warped field that grows tendrils (墨丝), the
  ink is cloudy and slightly denser at its rim, and the new page clears out of the ink's centre. Turns are
  timed from the content (`render.ink_windows`): a page holds, fully visible, until its last line has been
  readable for 1.0 s (0.5 s after a seal; a scene can define `ready_t()`), then the turn runs 0.7–1.0 s and
  tries to finish by the next page's first line. Leave ~1 s between a scene's last trigger and the next
  scene's first trigger where the narration allows.
- **Text stays clean and on time**: characters fade in with a slight rise and a short soft-focus
  (`INK_TEXT='fade'`, default); readable within ~0.4 s of their trigger. `INK_TEXT='diffuse'` makes them soak
  in like ink instead (slower: only for a deliberate, slow poem moment). `INK_BLOOM=True` re-enables ink drops
  behind punch words. Set these in scenes.py: `import ink; ink.INK_TEXT = 'diffuse'`.
- **Wash reveal** (`wash_mask`): landscapes appear left → right behind a soft edge, 2.5–3.2 s.
- **Ink drop** (`ink_bloom`): off by default (`INK_BLOOM`).
- **Seal** (`seal`): stamps down from 1.5× in 0.35 s — the only quick move, and it lands a beat (with `seal`
  sound). One or two per scene at most.
- **Brush stroke** (`brush_stroke`): bristled, tapered, dry-edged; draws on in ~0.6 s. Cinnabar for accents,
  diluted ink for rules.
- **Torn paper** (`TornText`, `torn_rect`, `torn_points`, `paper_piece`): ragged deckle edges with a white
  fibrous rim and a soft shadow. The sheet slides in (0.7 s), the cover tears along a ragged line and the two
  halves peel apart (0.75 s, `tear` sound); scraps slap in from 1.35× with a slight spin, 0.16 s apart. Use
  1–2 torn moments per video; it is the loudest move this style has.
- **Print textures**: `dry(c, 'brush')` gives 飞白 streaks, `dry(c, 'stipple')` a worn rubbing/letterpress
  stipple (as on the reference's 苏轼); both work on ghost characters (`ghost(..., tex='stipple')`).
- **Ambient life**: drifting mist bands, a skiff gliding, birds crossing, embossed ripples breathing, the
  moon/sun rising, petals falling (`petals=` on scroll scenes; 6–12 normally, ~20 for the ending).
- Hook clips dissolve through mist; the hook ends in a paper flood that opens onto the edit, with a paper chip + seal showing the `outro` text.
- Trigger on the spoken word (≈0.05 s before it). Put scene boundaries in the gaps between sentences: the page turn happens just before the boundary.

## 4. Sound
Synthesized, gentle, acoustic-ish (in `ink.py`); the NEON names are remapped automatically:
| NEON | poetry-ink | what it is |
|---|---|---|
| whoosh | `breeze` | soft wind, every scene boundary |
| pop | `pluck` | Karplus–Strong string on a D pentatonic note (古琴-ish); varies per event |
| impact | `bell` | 磬 / small temple bell, inharmonic partials + room |
| swish | `brush` | dry brush on paper |
| riser | `gliss` | rising breeze + a four-note pentatonic run |
| glitch | `drop` | water drop |
| — | `seal` | soft wooden press for seals |
| — | `tear` | paper tearing: fibre snaps over a dry rustle |

Templates register their own. Use `EXTRA_SFX` for more. A guqin / guzheng / flute BGM via `--bgm` suits this
style best; ask the user for one if they have it.

## 5. Scene catalog: what is said → which template
| When the speaker… | Template | Mode |
|---|---|---|
| opens the video / states the theme | `InkCover` (the reference cover, animated) | scroll |
| delivers a short, strong line / punchline | `InkBehind` (ink bleeding in behind the person; `font='xing'` for calligraphy) | full |
| a punchline that should *land physically* / a reveal / 揭晓 / a name or title | `TornText` (大字撕纸: `style='sheet'` torn sheet tears open to reveal stippled characters; `style='scraps'` one torn scrap per character, collage) | full |
| quotes a poem, a saying, an old line | `PoemColumn` (竖排 verses, moon, mountains, author + seal) | scroll |
| describes a scene, a journey, a mood, "the big picture" | `InkLandscape` (山水 wash-in, sun, skiff, birds, headline) | scroll |
| lists steps / points / methods | `InkList` (壹 贰 叁 seals, Songti items, dry-brush rules) | scroll |
| asks a question / explains calmly | `TalkCard(theme='ink', …)` | talk |
| shows the finished result / talks about footage while it plays | `InkShowcase` (footage large on paper, presenter in a round face-tracked avatar, headline + tags in the margin, typed prompt strip; chain with `smooth_in=True` so the footage plays on uninterrupted; crops the footage's own subtitles) | talk |
| "you just saw this video" — footage beside the presenter | `InkScroll` (footage plays inside an unrolling hanging scroll on the left) | full |
| reads out a prompt / a sentence to type | `InkPrompt` (steps + 信笺 letter paper written character by character in step with the speech) | scroll |
| ends / asks for comments / follow | `InkEnd` (ink drop, big line, chips, seal, vertical farewell, petals) | scroll |

Each template's docstring in `scripts/ink.py` lists its parameters. Building blocks for custom scenes:
`torn_rect, torn_points, paper_piece, stipple_img, ink_bg, mist, bottom_mist, left_mist, ink_text, ink_vtext, ghost, ink_label, ink_title, seal, brush_stroke,
ink_bloom, blob_path, paper_card, chamfer, wash_mask, mountain_layer, landscape, boat, birds, water, ripples,
orbit, dot_grid, PETALS`. Subclass `ScrollScene` for paper scenes (override `behind`/`front`, call
`self.ambient(c, t)` at the end of `front` for petals) or `Scene` for full-frame ones.

```python
InkCover(0, 6.5, lines=[(0.5, '一段口播'), (1.1, '一卷水墨'), (1.7, '一首诗')], sub=(2.6, '诗墨国风 / AI 视觉剪辑'),
         ghost=('诗', '韵'), vertical=('让想法被看见', '让表达更有诗意'), seal='雅', corner=('AI 赋能表达', '水墨传递诗意'))
InkBehind(6.5, 9.7, text='不亲手', text_t=7.1, seal=('墨', 8.4), sub=(8.6, '剪辑 · 动效'))
TornText(57.8, 63.1, text='真人亦可', text_t=59.6, seal=('真', 61.9), sub=(60.8, '实拍一样处理'))      # tears open
TornText(75.7, 82.4, text='交给AI', text_t=80.5, style='scraps')                                      # collage
PoemColumn(9.7, 18.7, lines=[(10.0, 12.0, '床前明月光'), (13.2, 15.0, '疑是地上霜')], author=(17.0, '李白 · 静夜思'), seal=(17.9, '太白'))
InkLandscape(21.0, 30.4, lines=[(21.6, '万般画面'), (22.6, '自成山水')], sub=(25.0, '节奏 · 排版 · 动画'))
TalkCard(30.4, 38.8, theme='ink', label='阿星 · 口播', hud='卷二 · 判断', path=[(30.4, 'full'), (30.45, 'right')],
         kicker='何处需要什么', lines=[(30.8, '大字 · [图片]')], items=[(35.0, '自行判断')])
InkList(38.8, 57.8, label='方法 · 沉淀', title='一套可复用的 skill', items=[(41.0, '理解内容', '读懂每一句'), …])
InkEnd(86.6, 93.4, big=(91.7, '评论区见'), items=[(87.5, '流程')], seal=(92.4, '关注'), farewell=(88.0, '山水有相逢'))
```
A full worked example: `references/example_project/scenes_poetry_ink.py`. Presenter explaining a finished video (theme text behind the person first, then footage + round avatar, hook = clips of the footage with its own sound): `scenes_poetry_ink_presenter_showcase.py`.

Presenter + finished footage — taste notes from user feedback: keep it calm and poetic. Use `ink.TURN = 'cut'`
(the footage already has ink page turns; never stack a second ink layer on it), `InkShowcase(layout='full',
crop=None)` so the footage is shown whole (its own subtitle line is covered by a soft paper band that carries ours),
`side='column'` (one vertical inscription at the top right: a 4-character headline + 1–2-character keyword columns),
and `motion=False` (no zoom bumps, push-ins, springs or slams). The presenter's full shot easing into the round
avatar (`avatar_in='full'`) is the only transition; the ending eases the avatar larger (`avatar_big`) beside a
`cta` card while the footage fades to paper.

Hook clips of external footage (`dict(path=..., s0, s1, gain, label='成片 · …')`) are shown as a framed picture on paper, ungraded, so the footage keeps its own titles; the HUD sits in the margins.

### 5b. Paper layouts — no presenter, any aspect (narration audio, 3:4, 9:16)
For `analyze.py narration.mp3 --size 1080x1440` (or whenever the person should not appear). All positions are
fractions of W/H. The content stays fully visible through each cut and the ink spread covers it, so pages never
dip to empty.
| When the narration… | Template |
|---|---|
| opens / names the subject | `PCover` (stippled ghost chars, torn sidebar with a vertical label, card with title / sub / dates, landscape, corner motto, seal) |
| moves through places or stages | `PRoute` (ink route down the page, stops bloom in on their words, a skiff travels to the latest stop) |
| turns one thing into another (困境 → 乐趣, before → after) | `PTorn` (a torn sheet printed with `cover` tears open to reveal `text`) |
| quotes verses | `PPoem` (centred vertical columns, `bg='river'` cliffs + waves or `bg='moon'`, ghost char, author + seal) |
| lists images / key words | `PWords` (lead line struck through, head line, words landing on torn scraps in a 2-column grid) |
| a big emotional line | `PBig` (two centred lines over a huge stippled character, ink drop, seal) |
| closes | `PEnd` (lead line, ink rain on the storm word, big answer words with cinnabar strokes, a vertical quote + source + seal) |
Example: `references/example_project/scenes_poetry_ink_portrait.py` (苏轼简介, 36 s, 3:4).

**Painted backdrop.** If the user supplies an ink painting, the usual use is the cover only, as a faded background:
```python
PCover(0, 4.4, ..., backdrop='../bg.png', fade=.42, safe=(0, .62))   # per page; the next page turn inks it away
```
To use it on every page instead:
```python
import ink
ink.BACKDROP = '../bg.png'   # cover-fit, drifts very slowly and continuously across pages, mist over it
ink.SAFE = (0, .62)          # P* content is laid out inside this horizontal band; keep the painting's subject outside it
ink.VEIL = .6                # paper veil over SAFE so type stays readable on the painting
```
Look at the image first and set SAFE to the empty side (the figure / main subject must stay clear). On a backdrop
the generated hills, water and landscapes switch off automatically; moon, ghost characters, seals and torn
paper stay. Page turns spread ink over the same painting, so only the text changes.

## 6. Rhythm & structure
- Slower than NEON: change scene every **4–9 s**. Let paper scenes breathe.
- Alternate `full` ↔ `scroll`/`talk`, but two paper scenes in a row are fine (a scroll unrolling).
- Typical 90 s: InkCover → InkBehind → PoemColumn or InkLandscape → TalkCard(ink) → InkBehind → InkList →
  InkBehind → InkEnd. That is about 8–12 scenes, not NEON's 15–18.
- Hook: same rules as SKILL.md 4b. Punch text in the hook is Songti indigo bleeding in behind the person; keep
  it 2–4 characters, ideally a 4-character phrase (四字).

## 7. Poetry: accuracy and taste
- When the speaker quotes a real poem, put **exactly** those words on screen, checked against the
  transcript. Do not "improve" classical text.
- When you write decorative lines yourself (headlines, mottos, `PoemColumn` verses that paraphrase the
  speaker), keep them original and **never attribute them to a real poet**; use the speaker's name or none.
  Tell the user which lines you wrote.
- Prefer 四字 / 五言 / 七言 rhythm for headlines and mottos; parallel pairs (对仗) for `vertical` and `corner`.
- Seal text is 1–4 characters: a theme word (雅, 诗, 墨, 韵), the speaker's name, or 关注 for the ending.

## 8. Pitfalls
- Ink type directly on busy video is unreadable; always keep `left_mist` (InkBehind does) or use a scroll scene.
- Don't mix NEON templates (lime, Menlo HUD, glitch) into a poetry-ink project. `TalkCard(theme='ink')` is the
  shared one.
- `TornText` sheet: keep the word ≤ 5 characters at 230px; the tear runs through the middle of the word, so
  set `text_t` on the keyword itself — the reveal *is* the beat.
- `xing` (行楷) glyphs are wide and irregular; check that the last character still tucks behind the head.
- Vertical text: keep columns ≤ 7 characters at 84px so they stay above y 900.
- Large `ink_person` values make faces look grey/ill; default 0, try 0.3–0.5 for a painterly look.
- Paper scenes are bright: if the source video is dark, the cuts will feel jumpy — prefer more `scroll`
  scenes and fewer `full` ones.
