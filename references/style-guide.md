# xingor style guide & scene catalog

## Contents
1. Palette & type
2. Canvas, safe zones, the person
3. Motion language
4. Sound
5. Scene catalog (content → template)
5b. TalkCard (口播小窗)
6. Pitfalls

---

## 1. Palette & type
| token | rgb | use |
|---|---|---|
| INK | (5,7,13) | text on lime chips, dark fills |
| LIME | (198,255,46) | the only loud accent: highlights, rim light, strokes, active states, keywords |
| BLUE | (64,120,255) | secondary data (bars, tracks, halftone background) |
| VIOLET | (150,92,255) | tertiary (one-off accents, audio track) |
| WHITE / GREY(150,158,175) | | main / secondary text |

One accent at a time. If everything is lime, nothing is. Behind-text is usually WHITE with a lime outline echo; use LIME fill for the 1–2 biggest punchlines (e.g. "放到身后", "评论区见").

Fonts (`F(kind, size)` in fx.py):
- `heavy` Lantinghei SC Heavy: Chinese display (behind text 210–300px, titles 52–58px, chips 34–40px)
- `disp` Avenir Next Condensed Heavy Italic: Latin display ("OPUS 5.5", "SKILL", "∞")
- `bold`/`med`: PingFang SC: subtitles (50px), descriptions (22–28px)
- `mono` Menlo Bold: HUD labels in CAPS with a small lime square (`hud_label`), e.g. `PIPELINE · 01`
- `num` DIN Condensed: counters, big numbers, step indices

## 2. Canvas, safe zones, the person
- 1920×1080. **y > 900 belongs to subtitles**; keep content above it.
- The person anchor is auto-detected (`PERSON` in components.py; from meta.json). For a centered talking head the head sits around x≈head_x±200, y≈head_top..head_top+500.
- **Full-frame scenes**: content lives on the left (x 60–700) on top of `side_shade`, or *behind* the person. Small props can go top-right (x>1450).
- **Behind text**: start around x=60 and let the last 1–2 characters tuck behind the head or shoulder. The word must stay readable; partial occlusion is the effect, not hiding. `SplitWord` puts two words either side of the head instead.
- **Dark scenes**: the cutout is scaled to 0.72–0.8 with the head at x≈1500–1560, anchored to the bottom edge. Content panels go in x 80–1100, y 230–880. Section title: HUD label at y 150 plus a heavy 58px title at y 220.
- Zoom: full scenes alternate 1.0 / 1.04–1.12, with slow pushes inside a scene. Never zoom below 1.0 in full mode, because it exposes the frame edges.

## 3. Motion language
- Entrances: `eob` (back-out overshoot) for chips and cards, `eo` (cubic out) for slides and lines, `eexp` for counters and progress. Typical duration 0.35–0.5s.
- Kinetic text: `slam_text`. Characters drop in with a stagger of 0.05–0.09s and scale 1.6→1.
- Exits: scene-level `window()` fades of about 0.25s. Don't animate exits individually.
- Ambient life: everything visible should keep moving a little (waveforms driven by the real voice level `ctx.amp(t)`, orbiting dots, scanning lines, particles in `dark_bg`). Static frames read as cheap.
- Transitions are automatic: a 0.28s RGB-split glitch at every boundary, plus a lime diagonal wipe when the mode changes (full↔dark↔card). The dark scene's person also animates from the full-frame position to the right (`enter_from`).
- Trigger on the **keyword's** timestamp, about 0.05–0.1s before it. A scene starts slightly before its sentence.

## 4. Sound
Synthesized in render.py, at about −13 dB under the voice:
- `whoosh`: every scene boundary (automatic)
- `pop`: chips, cards, steps
- `impact`: behind-text slams, the core reveal
- `swish`: strike-throughs
- `riser`: scans, reveals, progress fills
- `glitch`: halftone/digital moments

Templates register their own. Add extras through `EXTRA_SFX`. Pass `--bgm file` for music; it is ducked automatically.

## 5. Scene catalog: what is said → which template

| When the speaker… | Template | Mode |
|---|---|---|
| opens / introduces themselves | `Intro` (face brackets, REC HUD, optional voice card) | full |
| makes a short, strong claim / punchline | `BehindText` | full |
| names a product/model/brand | `SplitWord` ("OPUS" \| "5.5") | full |
| lists things that were (not) done | `Checklist` + strike + verdict chip | full |
| teases "the interesting part / here's the key" | `PunchHeadline` (push-in + marker highlight) | full |
| enumerates kinds of things (大字/图片/动画/音效) | `FloatTags` (behind word + props around the person) | full |
| "not just once / again and again" | `SwapSymbol` (×1 → ∞) | full |
| contrasts two versions (数字人 vs 真人, before/after) | `SplitHalftone` | full |
| explains cutouts / layering / "behind me" | `MatteReveal` | full |
| compares slow manual vs fast automated | `Compare` | full |
| ends / asks for comments / follow | `CTA` | full |
| describes a tool chain A → B → C | `Pipeline` (≤3 nodes) | dark |
| analyses references / studies examples | `Analyze` (cards → scan → rows → auto timeline) | dark |
| packages / abstracts into a reusable thing | `SkillCore` (modules converge → core → emits copies) | dark |
| walks through a process of 3–6 steps | `Steps` | dark |
| mentions numbers, data, key points | `DataCards` (counter / bars / highlight / ring) | dark |
| "this very video was made this way" | `ThisVideo` (card + real timeline of the edit) | card |
| asks a question / states a thesis / explains calmly with a headline | `TalkCard` (口播小窗: presenter in a vertical card + headline/chips beside it) | talk |
| a longer explanation where the person should stay visible next to the visuals | `TalkCard` with a `path` that moves the card (right → left → bubble) as the beats change | talk |

Typical 90s structure: Intro → 2–3 full scenes → a dark explainer → a full punchline → a dark explainer → … → ThisVideo/Compare → CTA. That gives about 15–18 scenes.

New ideas are welcome. Write a custom Scene when the content suggests something better (a code snippet typing in, a map, a chat bubble…), but keep the palette, fonts and motion language.

## 5b. TalkCard (口播小窗) — the editorial card look
One persistent card holds the talking head. It **pops in with a spring**, or **shrinks out of the full frame** (`path=[(t0,'full'), (t0+.05,'right')]` — the move is the transition, so no glitch or wipe is applied). It then **morphs and moves** between slots on later beats: `right`, `left`, `center`, `wide`, `bubble`, `bubble_l`, or any `(cx, cy, w, h, r)`.
- The crop follows the face (per-frame head x from the matte) and zooms in as the card gets smaller. A bubble shows just the face with a white (paper) or lime (dark) ring.
- An `ON AIR · 名字` pill with a pulsing lime dot sits top-left of the card and fades out when the card is small.
- `theme='paper'`: light editorial page (#F4F4F0, faint 80px grid, soft floor) with ink headlines. Highlighted words `[like this]` get a **lime marker stroke** behind ink text, which is the paper equivalent of lime text. Chips are white cards with soft shadows.
- `theme='dark'`: same card over `dark_bg`, with highlighted words in lime text and glass chips.
- Built-in content: `kicker` (small spaced label, e.g. `Q · 产品的第一步`), `lines=[(t, '先做[完整]产品'), …]` (heavy 100px, up to 3 lines), `items=[(t, text)]` (chips), `hud='// 01 — 方法'` (top-left code label with timecode on the right). Content sits on the side away from the card.
- For custom demos next to the card (a seesaw, a chart, a mock window), subclass and override `content(c, t, ctx, card)`. `card = (x, y, w, h, r)` is the current card rect, so you can keep clear of it.
- Use paper scenes as a **contrast block**: 2–4 consecutive paper TalkCards form a calm "explain" chapter between loud dark/full chapters. Don't flip paper ↔ dark every scene.
- Moving the card between beats (`right` → `left` → `bubble`) reads as a camera move and keeps a long explanation alive without changing scene.

```python
TalkCard(48.6, 57.8, theme='paper', label='ON AIR · 阿星', hud='// 04 — 新口播',
         path=[(48.6, 'full'), (48.65, 'right'), (51.9, 'left'), (55.5, 'bubble')],
         kicker='Q · 只要一段口播', lines=[(48.9, '[理解]内容'), (51.95, '拆出[画面]')],
         items=[(53.8, '文字'), (54.6, '动画'), (55.9, '节奏'), (56.4, '音效')])
```

## 6. Pitfalls
- `captions.txt` must keep one line per transcript segment, or render aborts.
- Menlo/DIN/Avenir have no CJK. `text()` falls back to PingFang automatically, but ✓ ▶ ⇆ ① may still be missing. Draw icons with `check_mark` / `play_icon`. ①②③ do render in PingFang.
- Don't put lime text on the light background of the real video without a shade or chip behind it.
- Behind-text that sits wholly on the background (never overlapping the person) loses the effect; move it closer to the head.
- If the speaker moves a lot, the static `PERSON` anchor is approximate. Check the test frames at several times.
- Scene times are *source* seconds. Pause trimming shifts output time by up to ~0.3s per cut; the renderer maps it, so never hand-convert.
