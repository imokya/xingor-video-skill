# creative-coding · 代码艺术科普片

A **2–3 min narrated science explainer whose every picture is drawn by code** — a browser 2D canvas, rendered frame by
frame. No presenter, no stock footage. The look is "artistic creative coding": text that behaves like a material
(seeds, a dragon, a vortex, chalk, sand), changing worlds per chapter, crisp type and almost no glow. First made for
《AI 其实不知道自己下一个字要说什么》(3:4, 165 s, Oct 2026) after ~10 rounds of feedback; everything below is what the
user approved or rejected. Example: `references/example_explainer/` (`film.js` is the whole film, `lines.txt` the
script, `music.py` the score).

| file (`scripts/web/`) | does |
|---|---|
| `package.json` | `cd scripts/web && npm install` once (Playwright; browsers via `npx playwright install chromium-headless-shell` if missing) |
| `util.js` | `mulberry32`, `clamp01`, `smooth`, `keys` (eased keyframes), `lerpKeys` (time warp) |
| `browser.mjs` | launches chrome-headless-shell (`--use-angle=metal`) and opens `http://localhost:$PORT/$PAGE?still=1` |
| `render_film.mjs` | `<out.mp4> [from s] [to s]` — frame-exact export, JPEG frames piped into ffmpeg; `--total` prints the frame count |
| `render_par.sh` | **parallel render**: `PAGE=film.html ./render_par.sh out.mp4 4` — N browsers on N chunks, lossless concat, checks the frame count |
| `shot.mjs` | `<prefix> <s...>` — stills at given times (12 warm-up frames each) for review |
| `cover.mjs` | `out.png` — calls `window.renderCover()` in the same page, so the cover reuses the film's motifs |
| `mix.py` | voice + music, music ducked under every line, loudnorm −14 LUFS / TP −1.5 |

Narration: `review/rv_tts.py --para --verify` (Fish s2.1-pro) — read `references/narration.md`.

## Workflow
1. **Script** — 30–40 short spoken lines, `#` paragraphs per chapter (`lines.txt`). Explain like to a complete beginner:
   one everyday example carried through the film (here 「今天天气真 ＿」), every term introduced by what it does
   ("可以调的旋钮，叫参数"). Hook in the first line, a question as the last line.
2. **Voice first, picture second** — synthesize, verify, write `vo/times.json` (start second per line). The picture is
   keyframed on these times; each chapter is a function `sX(t)` drawn in its own time window.
3. **Page** — `film.html` + one ES module: `renderFrame(n)` draws time `t = n / 60` from scratch.
   `SECTIONS = [[fn, start, end, shift], …]`; overlapping windows cross-fade (or iris, see below); `shift` moves a
   chapter in time without touching its keyframes. Serve the folder with `python3 -m http.server 5180`.
4. **Stills, not renders, while iterating** — `node shot.mjs out/fb/x 9.8 11.4 12.6` then `hstack` them into one image
   and look. When the user gives timestamps of the *final* video, they are output time (same as film time if nothing
   was shifted). Render the full film only when a round of changes is done.
5. **Render** — `./render_par.sh out/video.mp4 4` (≈ 1 min 50 s for 165 s at 60 fps vs ≈ 8 min single-process), then
   `python mix.py out/video.mp4 out/main.mp4 bgm.wav`, then append the creator's follow clip (uncropped, its audio
   loudnormed to −14).
6. **Before publishing** — contact sheet of the whole film (`ffmpeg -i f.mp4 -vf "fps=1/5,scale=216:288,tile=9x4"
   -frames:v 1 sheet.jpg`), check loudness (`loudnorm=print_format=summary` → about −14 LUFS), cover, title, 发布文案.

## Determinism (or parallel render and stills break)
- Never `Math.random()` / `Date.now()` in drawing. Use `hash(i)` or `mulberry32(seed)` created once at load.
- Everything is a function of `t`. A lazy cache is fine only if any frame order gives the same result (stills render
  frames out of order; parallel chunks start mid-film). Offscreen canvases for static materials (paper, chalkboard)
  are cached once.
- `await` all data at module top (`vo.json`, `times.json`, even the film's own source for the ending) before
  `window.ready = true`.

## Look — the rules that came out of the feedback
**Layout (3:4 1080×1440)**: title zone 180–330, main picture 380–1150, subtitles at y≈1262 (PingFang 44, ≤14 chars per
screen, split at punctuation, screen time ∝ characters). Nothing ever overlaps — check every busy moment with a still.
Sentences ≤ ~840 px wide (a 14-character sentence at 72 px was "太宽"; 60 px fits).

**One material per chapter** (borrowed from a viral explainer, then made our own): 深青荧光夜 (hook) · 方格纸 + 墨水
(examples, charts) · 暖黑 + 金尘 (history, scale, 3D) · 黑板粉笔 (reasoning) · 深靛夜色 + 月白字 + 琥珀点缀
(problems, tips — the user called this "字体和字幕都很舒服"). Never a red background, never pink. Subtitles: white with
dark stroke on dark worlds, ink with cream stroke on paper.

**Type**: Songti SC for titles, per-character blur-in that ends sharp; numbers in Didot drawn as a gold hairline
outline first (`setLineDash` on `strokeText`) and then filled; Menlo for code. Text is always crisp.

**Glow**: almost none. Big radial halos and shadowBlur on text were rejected twice ("光晕不好看"). Allowed: tiny glow on
points of light only (flower centres, fireflies, a seed glyph), `shadowBlur ≤ 10`.

**Never**
- particle text — letters or dots assembling into a word/number looked blurry and "不高级" (both times);
- copying the reference's motif — characters turning into butterflies was "太相似了"; keep the *feeling*
  (dark fluorescent, organic, delicate), invent the *mechanism*;
- static cards (an archive card with a stamp), an empty shot while the voice talks (a blank blackboard), lines drawn
  across text, a hard cut between two worlds, a layout that jumps when a section changes.

**Always**
- something moves at every line; no frame static for more than ~1.5 s. A slow camera (orbit, push-in `scale 1→1.06`)
  keeps even text scenes alive;
- in 3D, **near = big and bright, far = small and dim** (`fog(d) = clamp01((d − 0.4) / 0.9)` on words, stars and a
  faint perspective grid floor) and keep the camera moving so depth reads;
- hand over between worlds with a **motif**: an iris that opens from the dandelion's centre; the sentence the dragon
  wrote slides up and shrinks into the chart instead of being redrawn;
- the motif explains the idea, not just decorates it.

## Motifs that worked (all in `film.js`)
| idea | motif |
|---|---|
| "every step picks the next character" (hook) | a fluorescent **dandelion whose seeds are characters**; seeds fly up one by one to spell the answer, two losing candidate seeds drift near each slot and away; a gust blows the whole head (and the sentence) into the night |
| 文字接龙 | a **dragon of characters** swimming on a Lissajous path, glyphs spaced by **arc length** (spacing by parameter clumps them in the turns), head in red; its first five characters drop into 「今天天气真＿」 |
| sampling | ink-filled bars with a **wobbling liquid surface**; a red pen tip **bounces between candidates, slowing down**, and stops on one; the chosen glyph flies along an arc into the blank leaving ink dots |
| Shannon 1951 | Didot outline-drawn year; a **telegraph tape** typing a sentence, under each letter a column of dots = guesses needed (wrong guesses flash above the head, struck out); "一猜就中" lights all single dots; the AI part speeds the tape up |
| learning from text | text streams on **log spirals** into a rotating **sphere made of characters** |
| embeddings | words in 3D, clusters as **constellations** (no halos); at the focus, other words fly outward and become star dust; 男人→女人 / 国王→女王 arrows plus dashed sides form a **parallelogram** while the camera orbits |
| attention | chalk with **falling chalk dust**; a chalk dot **hops back** from 「她」 to 「小红」; 「她」 rises above the sentence and **threads drop from above** to every earlier character (never across text), dots flowing along them, weights shown by size/brightness |
| hallucination | the fabricated answer **crumbles into sand** left to right and blows away |
| tips | **line-drawn icons** stroked in progress (magnifier, speech bubble with ?, checkbox) in circles with a ripple, joined by a dotted line |
| ending | text falls and grows into a gold garden with fireflies (the user's favourite beat); **the film's own source code scrolls** behind 「// 本片画面，大部分由代码生成」 |

## Ending and voice details
- Disclose it near the end: a line like 「对了，这条视频的画面，大部分都是用代码生成的。」 — good for trust and a hook
  for the creative-coding crowd.
- The last line is a question with a rising, friendly tone: 「评论区，说说看？」 — 「评论区说说。」 sounded like an
  order. Generate 2–3 takes of a line that must sound right and drop any take that reads a direction aloud.

## Cover (3:4)
`window.renderCover()` in the film module, rendered with `cover.mjs`:
- the film's strongest motif (here the dandelion being blown, seeds carrying characters), seeds spaced so none touch
  and none touch the edge;
- title in the upper middle with **size hierarchy** — the key words biggest (「不知道」 210 px, 「下一个字」 92 px, the
  rest 54–78 px); same wording as the post title;
- optional faint background of the film's own code: ≤ 7.5 % opacity, fading downwards and further behind the title,
  code-only lines (no Chinese comments);
- one focal element that links picture and title (a brighter seed carrying 「好」 drifting to a cursor after the
  title) — then read the cover aloud: 「要说什么｜好」 can read as 「说什么好」; decide if that is wanted.

## Speed
- `render_par.sh` with N = 4 on an M-series Mac: 5× CPU, ~4.4× faster. Chunks start on keyframes, so `-c copy` concat
  is seamless; the script compares the frame count with `TOTAL_FRAMES`.
- Iterate with `shot.mjs` (seconds) and render once per round. A full render that is already outdated can be killed.
- Heavy per-frame work: hundreds of `fillText` calls with changing fonts, `shadowBlur`, `filter: blur()`. Cache static
  layers in offscreen canvases; keep `shadowBlur` to small points.
