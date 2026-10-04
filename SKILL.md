---
name: xingor-video-skill
description: Turn a raw talking-head / 口播 video into a finished 16:9 edit in the "xingor" style — the person is cut out so huge kinetic text sits BEHIND them, slick MG / demo animations (pipelines, step lists, data cards, halftone split, skill-core), dark "neon lab" scenes with a lime rim-lit cutout, word-synced subtitles with keyword highlights, an automatic hook / 钩子 cold open cut from the best moments, glitch/lime-wipe transitions, pause trimming and synthesized sound effects. Use this whenever the user hands over a 口播/talking-head/数字人/vlog-to-camera video and asks to 剪辑, 加特效, 加字幕, 做动效, make it look like a tech-YouTuber / 科技博主 video, put text behind the person (文字在人物背后), add MG动画/演示动画, wants a 钩子/开头精彩片段/预告 cut from the video, or says "用 xingor 风格 / xingor-video-skill". Also use it when they want to re-edit or tweak a video made with this style. It has a second look, poetry-ink (诗墨国风): xuan paper, indigo Songti/Kaiti type, cinnabar seals, ink-spread page turns, vertical poems, torn paper and guqin-like sounds — use it only when the request says 水墨诗词 (or names poetry-ink); otherwise use the default NEON LAB look.
---

# xingor-video-skill

A complete, script-driven pipeline: **analyze → pick a hook → plan scenes → write `scenes.py` → test frames → full render**.
Everything runs locally in Python: faster-whisper for ASR, RobustVideoMatting for the person matte, skia for drawing, and ffmpeg (via imageio-ffmpeg) for encoding. No editing app is needed.

`SKILL_DIR` below means the directory containing this file.

## Style in one breath ("NEON LAB")
Deep ink background (#05070D), **acid lime #C6FF2E** as the only loud accent, electric blue/violet as quiet secondaries, white text.
- Big text uses Lantinghei SC Heavy for Chinese and Avenir Next Condensed Heavy Italic for Latin. Body text is PingFang SC; HUD labels are Menlo caps.
- Alternate between two kinds of scene:
  - **full-frame scenes**: the real video, gentle zooms, and text either behind the person or on a shaded left side.
  - **dark scenes**: the person is cut out, shrunk to the right, rim-lit in lime, with a demo animation on the left.
- A third look, the **口播小窗 (TalkCard)**: the presenter sits in a vertical rounded "ON AIR" card that springs in, or shrinks out of the full frame, and moves between slots, next to big headlines on a light paper page (or the dark background). Use it for calm explanatory chapters.
- Every visual is triggered by the exact word that is spoken, not by sentence starts.
- Videos open with a **hook (钩子)**: a few seconds to a few tens of seconds of the best moments, cut from the talking-head video itself (optionally with B-roll such as the finished result), played before the edit starts.

Read `references/style-guide.md` before planning. It has the rules (palette, safe zones, timing, what to avoid) and the scene catalog that maps "what is being said" to "which template".

## Choose the style first
| the request / content | style | set in scenes.py | read | start from |
|---|---|---|---|---|
| default; tech, product, AI, fast-paced, "科技感" | **NEON LAB** | nothing (`THEME = 'neon'`) | `references/style-guide.md` | `references/example_project/scenes.py` |
| the request says **水墨诗词** (or names poetry-ink) | **poetry-ink · 诗墨国风** | `THEME = 'poetry-ink'` and `from ink import *` | `references/poetry-ink.md` | `references/example_project/scenes_poetry_ink.py` |

Anything else — including other Chinese-style wording like 国风 or 中国风 — uses NEON LAB unless the user asks for 水墨诗词. Don't mix the two template families in one video (`TalkCard` works in both: `theme='ink'`).

**poetry-ink in one breath**: xuan paper (#F1EEE6), indigo ink (#162C60) Songti Black headlines, a single cinnabar accent (#C84628) for seals, dots, short brush strokes and subtitle keywords. Pale dry-brush ghost characters bleed off the edges; a cut-corner paper card, embossed ripples, orbit hairlines and halftone dots frame the layout (like a 国风 PPT cover). The person stands on the paper like the scholar in a scroll, with mist rising around the waist. Motion is slow and natural — characters bleed into the paper, landscapes wash in, mist drifts, a skiff glides, petals fall, seals stamp — and every cut dissolves through spreading ink. Sounds are a plucked pentatonic string, a temple bell, water drops, breeze and brush. Big words can also arrive as **torn paper (大字撕纸)**: a deckle-edged sheet tears open to reveal stippled characters, or each character slaps in on its own torn scrap. Templates (in `scripts/ink.py`): `InkCover`, `InkBehind`, `TornText`, `PoemColumn`, `InkLandscape`, `InkList`, `InkEnd`, plus `TalkCard(theme='ink')`. The rest of the workflow below is identical; poetry-ink scenes are fewer and longer (4–9 s).

## Workflow

### 1. Setup (once per machine/work dir)
```bash
bash SKILL_DIR/scripts/setup.sh <project>/work
```
This creates `.venv` (torch, faster-whisper, skia-python, imageio-ffmpeg), links `./ffmpeg`, and downloads the RVM model (~15 MB). macOS fonts are assumed (PingFang, Lantinghei, Avenir Next Condensed, DIN Condensed, Menlo). On other OSes, map `FAM` in `scripts/fx.py` to fonts that exist there.

### 2. Analyze the input (run inside the work dir)
```bash
cd <project>/work && .venv/bin/python SKILL_DIR/scripts/analyze.py "../input.mp4"
```
This takes about 3–5 minutes for a 90-second clip and produces:
- `source.mp4`, normalized to 1920×1080 and 25/30 fps.
- `transcript.json` with word timestamps.
- `captions.txt`, a draft with one line per segment.
- `silences.json` with the detected pauses.
- `matte.mkv`, the per-frame person alpha.
- `meta.json` with fps, frame count, and the auto-detected person anchor (`head_x`, `head_top`, `face_y`, body edges).
- `sheet.jpg`, a contact sheet of the source.

If the source is vertical, ask the user before letterboxing it into 16:9, or render at its own shape with `--size`.

**Other aspect ratios / narration audio.** `--size WxH` sets the canvas (e.g. `1080x1440` for 3:4, `1080x1920` for 9:16); it is stored in `meta.json` and every script follows it. If the input is audio only (mp3/wav/m4a — a 配音 / 旁白 / 口播音频 with no picture), analyze.py makes a blank paper source and an empty matte; there is no presenter, so build the edit only from scenes that don't show one — in poetry-ink the `P*` paper layouts (`PCover`, `PRoute`, `PTorn`, `PPoem`, `PWords`, `PBig`, `PEnd`), which are laid out relative to the canvas. The hook then shows its punch text on a moonlit page. Example: `references/example_project/scenes_poetry_ink_portrait.py` (36 s narration, 3:4).
```bash
.venv/bin/python SKILL_DIR/scripts/analyze.py "../narration.mp3" --size 1080x1440
```

If the user gives a **reference video**, make a contact sheet of it, for example:
```bash
./ffmpeg -i ref.mp4 -vf "fps=1/2,scale=480:-1,tile=5x8" -frames:v 1 ref_sheet.jpg
```
Look at it for ideas about pacing and density, but keep this skill's own look. Users explicitly want "像它的感觉，但不要抄" — the same feel without copying.

### 3. Fix captions
Look at `sheet.jpg` and read the transcript. Then edit `captions.txt`:
- Keep **exactly one line per transcript segment**. The renderer aligns chunk timing through the segments.
- Fix ASR errors, especially brand names (e.g. 黑Gen → HeyGen, minimax → MiniMax).
- Insert `|` to split a line into on-screen chunks of at most ~16 Chinese characters, breaking at natural pauses.
- Drop end punctuation.

### 4. Plan the edit
Write a short scene plan, either for yourself or for the user if they want to review it. Give each sentence a time range (source seconds) and a template from the catalog. Then choose trigger times from `transcript.json` word timestamps:
```bash
.venv/bin/python -c "import json;[print(' '.join(f\"{w['w'].strip()}@{w['s']:.2f}\" for w in s['words'])) for s in json.load(open('transcript.json'))]"
```
Rhythm rules that make this style work:
- Change scene roughly every 3–6 seconds.
- Alternate full ↔ dark, and never use more than 2 dark scenes in a row.
- Use behind-text for punchlines and full-frame overlays for lists.
- Put scene boundaries in the gaps between segments.
- Make the last scene end at or after the video end; the renderer extends it automatically.

### 4b. Pick the hook (钩子 / cold open)
Do this for every talking-head video of about 30 seconds or more, unless the user says no hook. Short-video viewers decide in the first 2–3 seconds, so the best moment goes first and the edit follows.

Shortlist candidates:
```bash
.venv/bin/python SKILL_DIR/scripts/hook.py            # --budget 12 to override the length
```
`hook.py` ranks windows of 1–3 transcript segments by loudness, speech rate, punch/curiosity words (其实/竟然/最/免费/不需要…), questions and numbers. It penalizes the opening lines (they play again right after the hook), calls to action and dead air. It also proposes a total length from the video length:

| video | hook budget | clips |
|---|---|---|
| < 40 s | ~3–4 s | 1 |
| 40–75 s | ~5–8 s | 1–2 |
| 75 s – 3 min | ~8–15 s | 2–3 |
| 3–10 min | ~15–25 s | 2–4 |
| > 10 min | ~25–40 s | 3–4 |

The scores only shortlist. Read the candidates and choose like an editor:
- **The payoff or the strongest claim**: the result ("效果还是挺生动的"), a surprising fact, a number, a contrarian line ("不需要充值积分"), or a question that opens a curiosity gap.
- **Self-contained**: it must make sense without context. Drop lines that start with 所以/然后/这个 or point back to something ("像刚才那样").
- **Tease, don't tell**: show what and how good, not the full how. Never use the CTA or the final summary.
- **Order for impact**: the most striking clip first, and end on a line that makes viewers want the explanation. Clips may be reordered freely and come from anywhere in the video.
- **Clean cuts**: start ~0.08 s before the first word and end ~0.15 s after the last (`hook.py` already snaps to word timestamps). Cut on sentence ends, not mid-phrase.
- **B-roll beats the talking head** when there is a visible result (generated video, product demo, before/after). Put it first, with its own sound, and then let the speaker's line land on it.

Declare it in `scenes.py`:
```python
HOOK = dict(
    clips=[
        ('../result.mp4', 0.0, 2.6, .8),               # B-roll: path, in, out, volume (its own sound)
        dict(s0=31.22, s1=33.91, text='挺生动', text_t=.9),   # source seconds + punch text behind the person
        (36.70, 41.21),                                 # plain source clip
    ],
    title='',                      # punch for the first clip if it has no text of its own
    kicker='HIGHLIGHT · 精彩预告',   # top-left HUD
    outro='正片开始',                # chip shown as the edit starts ('' = none)
)
```
- Source clips play the original audio at the same level as the edit. Their subtitles come from `captions.txt`, and their own matte keeps punch text behind the person.
- B-roll is cover-cropped when its shape matches the frame. Otherwise (e.g. vertical phone footage) it is fitted over a blurred copy of itself; force this with `fit='cover'|'blur'` in the dict form. B-roll has no matte, so its text sits in front.
- The renderer adds the teaser look: corner brackets, a blinking `kicker`, the **real source timecode** (`SRC 00:31`), a story-style segment bar, glitch cuts with whooshes, impacts on punch text, a riser into a lime wipe, and an impact plus the `outro` chip as the edit begins. Scene times stay in source seconds; the hook is simply prepended.
- `--bgm` runs under the edit only, so the hook keeps its original sound.

Check hook stills with `h`-prefixed times (seconds into the hook): `render.py test h0.5 h3.0 h7.8`.

### 5. Write `scenes.py` in the work dir
Start from `SKILL_DIR/references/example_project/scenes.py` (NEON LAB) or `scenes_poetry_ink.py` (poetry-ink, with `THEME = 'poetry-ink'`; templates and drawing helpers are in `SKILL_DIR/scripts/ink.py`). Each is a complete 93-second example built only from templates, with every sentence commented above its scene.

Use `from components import *`. Templates live in `SKILL_DIR/scripts/components.py`; each template's docstring lists its parameters. Required pieces:
- `KEYWORDS`: terms highlighted in lime in the subtitles.
- `build_scenes()`: returns the scenes back to back from 0 to the end.
- `EXTRA_SFX` (optional): `[(t, kind, gain)]`.
- `HOOK` (optional, but use it by default; see 4b): the cold open played before the edit.

Every template registers its own sound effects. Scene-boundary whooshes are added automatically.

When no template fits, write a custom `Scene` subclass in the project's `scenes.py`. Overriding `xf / behind / front` is enough. `references/example_project/raw_custom_scenes.py` has the original hand-written versions of every template; they are good starting points for variations. Drawing helpers live in `fx.py`: `text`, `glass`, `chip`, `hud_label`, `wave_bars`, `corners`, `glow_path`, `partial_path`, `dark_bg`, and easing helpers `P/eo/eob/eio/eexp/window`.

What goes where:
- `behind()` draws between the background and the person cutout. That is where text "behind the person" goes.
- `front()` draws on top of the person.
- Subtitles, the progress hairline, transitions and the end fade are added by the renderer.

### 6. Test frames, then look at them
```bash
.venv/bin/python SKILL_DIR/scripts/render.py test 2.5 5.8 12.3 ...   # pick 1–2 times per scene, at the busiest moment
.venv/bin/python SKILL_DIR/scripts/montage.py test/m.jpg test/t_2.5.jpg test/t_5.8.jpg ...
```
Include 2–3 hook stills (`h0.5 h3.2 …`): one per clip, at the moment its punch text lands.

Look at the montages and fix the following before the full render. A test frame takes about 1 second; a full render takes about 3 minutes, so iterate on stills.
- Overlap with the subtitles (y > 900 is reserved for them).
- Text hidden by the head when it should only be *partly* tucked behind.
- Glyphs that render as boxes. The renderer falls back from Menlo/DIN/Avenir to PingFang for CJK, but symbols such as ✓ ▶ ⇆ have no glyph. Draw them with `check_mark`/`play_icon` instead.
- Cards running into the cutout (keep left-side content x < 1100 in dark scenes).
- poetry-ink: ink characters must sit on paper (mist or a scroll scene), vertical columns must stay above y 900, and check a frame in the middle of a cut (e.g. `t0 - 0.1`) to see the ink spread.

### 7. Full render
```bash
.venv/bin/python SKILL_DIR/scripts/render.py full ../成片_v1.mp4 [--bgm music.mp3]
```
This renders at about 13 fps on an M1 Pro. Run it in the background. To check the result, make a contact sheet of the output and run `volumedetect`. With `--bgm`, the music loops, ducks under the voice, and fades out at the end.

Version outputs as `_v1`, `_v2`, and so on, and tell the user which one is new and what changed.

## Honesty in on-screen numbers
Data cards and HUD readouts look like facts. Use real values wherever possible (the frame count, scene/caption/sfx counts from `ctx`, numbers the speaker actually says). When you add a decorative figure (e.g. "+95%", "MATCH 99.7%"), tell the user in your summary so they can remove it.

## What to report back
Give the output path, duration and resolution. Then list:
- the hook: each clip's source range and line (or the B-roll file), its length, and why it was chosen;
- the scene list, as a short table: time → template → what is shown;
- what you could verify (stills, streams, loudness) and what you couldn't (you can't watch or listen in real time);
- invented numbers;
- poetry-ink: which on-screen lines/verses you wrote yourself (never attribute them to a real poet) and which are real quotes checked against the transcript;
- missing pieces such as BGM.

Also give the one-line re-render command.
