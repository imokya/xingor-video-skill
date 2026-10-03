---
name: xingor-video-skill
description: Turn a raw talking-head / 口播 video into a finished 16:9 edit in the "xingor" style — the person is cut out so huge kinetic text sits BEHIND them, slick MG / demo animations (pipelines, step lists, data cards, halftone split, skill-core), dark "neon lab" scenes with a lime rim-lit cutout, word-synced subtitles with keyword highlights, glitch/lime-wipe transitions, pause trimming and synthesized sound effects. Use this whenever the user hands over a 口播/talking-head/数字人/vlog-to-camera video and asks to 剪辑, 加特效, 加字幕, 做动效, make it look like a tech-YouTuber / 科技博主 video, put text behind the person (文字在人物背后), add MG动画/演示动画, or says "用 xingor 风格 / xingor-video-skill". Also use it when they want to re-edit or tweak a video made with this style.
---

# xingor-video-skill

A complete, script-driven pipeline: **analyze → plan scenes → write `scenes.py` → test frames → full render**.
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

Read `references/style-guide.md` before planning. It has the rules (palette, safe zones, timing, what to avoid) and the scene catalog that maps "what is being said" to "which template".

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

If the source is vertical, ask the user before letterboxing it into 16:9. The style is designed for landscape.

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

### 5. Write `scenes.py` in the work dir
Start from `SKILL_DIR/references/example_project/scenes.py`. It is a complete 93-second example built only from templates, with every sentence commented above its scene.

Use `from components import *`. Templates live in `SKILL_DIR/scripts/components.py`; each template's docstring lists its parameters. Required pieces:
- `KEYWORDS`: terms highlighted in lime in the subtitles.
- `build_scenes()`: returns the scenes back to back from 0 to the end.
- `EXTRA_SFX` (optional): `[(t, kind, gain)]`.

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
Look at the montages and fix the following before the full render. A test frame takes about 1 second; a full render takes about 3 minutes, so iterate on stills.
- Overlap with the subtitles (y > 900 is reserved for them).
- Text hidden by the head when it should only be *partly* tucked behind.
- Glyphs that render as boxes. The renderer falls back from Menlo/DIN/Avenir to PingFang for CJK, but symbols such as ✓ ▶ ⇆ have no glyph. Draw them with `check_mark`/`play_icon` instead.
- Cards running into the cutout (keep left-side content x < 1100 in dark scenes).

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
- the scene list, as a short table: time → template → what is shown;
- what you could verify (stills, streams, loudness) and what you couldn't (you can't watch or listen in real time);
- invented numbers;
- missing pieces such as BGM.

Also give the one-line re-render command.
