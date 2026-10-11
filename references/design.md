# Design a look for this content

Use this when the user **does not name a style**. Don't reach for a preset: design a theme from the content, choose
components from the shared library by what each sentence does, and design new components when nothing fits.
Named styles (NEON LAB, 水墨诗词, 文物纪录片, 撞色测评) are references here — borrow their best moves, not their identity.

## 1. Read the content → a one-line brief
Before any colour, write down (for yourself, or show the user if they want to steer):
- **subject** — what it is about, in concrete nouns (茶, 一款 App, 健身计划, 宋代瓷器)
- **audience & platform** — who watches, where (小红书 3:4, 抖音 9:16, B站 16:9)
- **emotion** — calm / warm / playful / serious / urgent / reverent / nostalgic
- **energy** — speech rate and edit density (from the transcript: syllables per second, punch words)
- **material** — presenter video? narration only? footage, screenshots, products to show?

Example: *"入门茶科普，给 25 岁上班族，小红书 3:4，安静温和，语速慢，只有旁白和几张茶具照片。"*

## 2. Content character → what is allowed (hard rule)
Colour is not the only thing that carries meaning: **components, effects and transitions have a cultural character, and
re-colouring does not change it.** Seals (印章, 壹贰叁 numerals), ink bleed, torn xuan paper, brush strokes, petals,
landscapes and vertical verse read as 古风 / 传统文化 in any colour; HUD, scan lines, halftone and glitch read as tech.
Decide the content's character first, then use only what fits it:

| character | content | components | turns | sound |
|---|---|---|---|---|
| traditional | 古风 / 诗词 / 传统文化 / 国学 / 茶道 / 书法 | the ink family (`Ink*`, `P*`, `TornText`, `PoemColumn`, `TalkCard(theme='ink')`) | `ink`, `cut` | acoustic |
| tech | 科技 / AI / 编程 / 数码 / 游戏 | NEON family + neutral blocks | `glitch`, `wipe`, `iris`, `punch`, `cut` | electronic |
| playful | 亲子 / 美食 / 宠物 / vlog / 开箱 | neutral blocks (+ `FloatTags`, `Checklist`, `CTA`) | `iris`, `wipe`, `punch`, `cut` | electronic |
| cinematic | 纪录 / 历史叙事 / 自然 / 旅行 / 人物故事 | neutral blocks, `MetalTitle` sparingly | `cut` | either, quiet |
| editorial | 知识科普 / 读书 / 职场 / 财经 / 观点 | neutral blocks | `wipe`, `iris`, `cut` | electronic, quiet |

`scripts/kit/fit.py` holds the full map (every component, turn and small effect tagged) and is what `director.py`
uses: `FIT.character(text, topic)`, `FIT.components_for(role, character, presenter=…)`, `FIT.turns_for(character)`.
If the role has no fitting component (e.g. a number in a 古风 video), **design one in the content's own language**
(a dated seal, a vertical figure in Songti) instead of borrowing one from another character.

## 3. Brief → theme decisions
| decision | how to choose | values |
|---|---|---|
| **seed colour** | the subject's own colour: tea green, roast brown, sea blue, lacquer red, blossom pink, money green. If the subject has none, the emotion's colour | any hex |
| **mood** | light pages for warm / calm / editorial / lifestyle; dark for tech-night / cinematic / sport / luxury | `light` / `dark` |
| **voice** (type) | literary (宋体) for culture, reading, reflection; hand (行楷 / 楷体) for romance, poetry, craft; modern (兰亭黑 / 苹方) for most topics; techno (condensed + mono) for tech-heavy, games, data | `literary` / `hand` / `modern` / `techno` |
| **tempo** | from energy: calm ≈ slow speech, few cuts; snappy ≈ fast speech, many punchlines | `calm` / `medium` / `snappy` |
| **turn** (page turn) | must fit the character (table above): `ink` only for traditional; tech → `glitch` / `wipe` / `iris`; playful → `iris`; editorial → `wipe`; cinematic → `cut`. If the footage you show already has its own turns, use `cut` (never stack two) | `ink` / `iris` / `wipe` / `glitch` / `punch` / `cut` |
| **sound** | acoustic (string, bell, water, brush) for traditional; electronic (whoosh, pop, impact) otherwise | `ink` / `neon` |

```python
import kit.theme as KT
THEME = KT.design('茶事', '#7A8B5C', 'light', voice='literary', tempo='calm', turn='ink', sfx='ink')
```
`KT.design` builds every colour role from the seed and pushes each text pair to WCAG contrast (ink ≥ 7:1, muted ≥ 4.5:1,
accent ≥ 3:1). Override any role if the brief needs it: `accent='#E07A2E'`, or `THEME.with_(accent=…)`.

**Check before rendering anything:**
```bash
.venv/bin/python SKILL_DIR/scripts/kit/preview.py swatch.png      # look at it; the contrast report is printed too
```
One loud colour only (the accent). If the swatch feels generic, change the seed or the voice, not just the lightness.

**Shortcut:** `.venv/bin/python SKILL_DIR/scripts/director.py [--topic "…"]` drafts 2–3 theme candidates from the
transcript plus a scene plan (`draft_scenes.py`). Treat it as a starting point and judge it against the brief.

## 4. Sentences → components
Give every sentence a role, then take the first component that fits the character
(`FIT.components_for(role, character, presenter=…)` lists them best first):

| role (what the sentence does) | traditional | tech | playful / editorial / cinematic |
|---|---|---|---|
| opening / theme | `InkCover`, `PCover` | `TitleCard`, `Intro`, `MetalTitle` | `TitleCard` (`MetalTitle` cinematic) |
| short strong claim | `InkBehind`, `TornText`, `PBig`, `PTorn` | `TypeBehind`, `BehindText`, `SplitWord` | `TypeBehind`, `BehindText`, `TitleCard` |
| a number / data | design one (dated seal, vertical figure) | `BigStat`, `DataCards` | `BigStat` |
| a list / steps | `InkList`, `PWords` | `ListSteps`, `Steps`, `Checklist` | `ListSteps` (`Checklist` / `FloatTags` playful) |
| a comparison | `TornText` / `PTorn` (cover → text) | `CompareTable`, `Compare`, `SplitHalftone` | `CompareTable` |
| a quotation / verse | `PoemColumn`, `PPoem` | `PunchHeadline`, `TypeBehind` | `TypeBehind`, `TitleCard` |
| a question / thesis | `InkBehind`, `TalkCard(theme='ink')` | `TalkCard(theme='dark'/'paper')`, `PunchHeadline` | `TalkCard(theme='paper')` |
| a prompt / what to type | `InkPrompt` | `PromptPage` | `PromptPage` (editorial) |
| a product / screen / footage | `InkShowcase`, `InkScroll` | `Callouts`, `Analyze` | `Callouts` |
| a process / chain | `InkLandscape`, `PRoute` | `Pipeline`, `ListSteps`, `SkillCore` | `ListSteps` |
| call to action | `InkEnd`, `PEnd` | `EndCard`, `CTA` | `EndCard` |

Where they live: `scripts/components.py` (NEON family), `scripts/ink.py` (paper family + `P*` layouts + showcase),
`scripts/kit/blocks.py` (theme-neutral: `TitleCard`, `BigStat`, `CompareTable`, `PromptPage`, `TypeBehind`,
`MetalTitle`, `Callouts`, `ListSteps`, `EndCard`, and primitives). Read a template's docstring before using it.

Rhythm: change scene every 3–6 s for snappy, 4–9 s for calm; alternate full-frame and page scenes; trigger visuals on
the spoken word (≈0.05 s before it); put boundaries in the gaps between sentences.

## 5. Nothing fits → design a component
When the content wants something the library doesn't have (a recipe card, a map pin, a chat thread, a before/after
slider…), write a `Scene` subclass in the project's `scenes.py`:
- take colours from the theme (`th = KT.ACTIVE`; `th.ink`, `th.accent`, `th.surface`…), fonts from roles
  (`F(th.font('head'), 80)`), and durations from `th.dur` — never hard-code a palette
- build from primitives first: `kit.blocks` (kinetic_word, typewriter, counter, glass, pointer, input_box, table, iris,
  hud, rings…), `fx` (text, chip, glass, glow_path…), `ink` (ink_text, seal, brush_stroke, torn_rect, paper_card…)
- override `behind()` (between background and presenter) / `front()` (on top), and `events()` for its sounds
- check stills at the busiest moment like any other scene

**Fold good new ones back in:** if a new component worked and would be useful again, move it into
`scripts/kit/blocks.py` with a docstring (what it shows, its parameters), add it to the table above, and mention it in
your report. That is how the library grows.

## 6. Taste rules (learned from the user — keep them)
- Colours, effects and transitions follow the content's character (§2): ink only for 古风诗词 / 传统文化, never for tech.
- Ink spreading is for page turns only; don't layer a second transition style over footage that has its own.
- Show footage whole (no cropping or zoom-for-impact); cover its burned-in subtitles with a soft band instead.
- No shaking, punching or bouncing just to look energetic; motion should suit the content.
- Text must be readable before anything covers it: a page holds until its last line was readable (~1 s).
- Credits, small labels and seals sit on a clean patch of paper / surface — never on top of decoration.
- Keep visuals in sync with the voice; slow entrances must not lag the words.
- Big background characters / decoration go to the side, never behind the main text.
- One accent colour; everything else is ink in different strengths.

## 7. Report the design
Tell the user, in a few lines: the brief, the theme (seed, mood, voice, tempo, turn, sound — and why), which components
carried which parts, any component you designed new (and whether you folded it into the library). Offer the swatch.
