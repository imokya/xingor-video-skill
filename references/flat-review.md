# flat-review · 撞色测评

A **voice-over product review with no presenter on camera**: app screenshots, generated results and data become flat colour-block scenes driven by a word-synced narration. Made for 小红书 (3:4) and 视频号 (6:7), 2–4 minutes. First used for the "Muse 实测" episode (`references/example_review/`).

Everything lives in `scripts/review/` and runs with the work-dir venv (`.venv/bin/python`, needs numpy, pillow, faster-whisper, imageio-ffmpeg — `setup.sh` installs them). No skia, no matting.

| script | does |
|---|---|
| `rv_tts.py` | per-line TTS → `audio/vo_XX.wav` + `vo.json` (Fish Audio or MiniMax; skips unchanged lines) |
| `rv_align.py` | joins the lines with pauses → `vo_track.wav`, word timestamps → `timeline.json` (hook: `--hook` → `words.json`), checks every line against the script |
| `rv_core.py` | all drawing / sound components (`from rv_core import *` in scenes.py) |
| `rv_render.py` | renders `scenes.py` → mp4 (3:4, or `--67` for 6:7), mixes voice + SFX + hook + BGM, appends the outro clip; `still` mode for test frames |
| `rv_cover.py` | the matching cover (3:4 / 6:7 / 4:3) |

## Look in one breath
- **Palette**: flat full-bleed blocks that rotate scene by scene — ink black `#101012`, cream `#F1EDE4`, coral `#EE4B3A`, electric blue `#2C2EE8`. No gradients, no glow, **no lime/green** (users disliked it). Coral is the accent on cream/black/blue; on coral the accent is black or cream.
- **Type**: Lantinghei Heavy for Chinese headlines, stretched ×1.12 and sliding in letter by letter with horizontal motion blur and a squash-and-settle; Arial Black for Latin words (ASCII only); Baskerville italic for a thin English line opposite the headline; Menlo caps for HUD labels; PingFang for subtitles and chips. Every headline ends with a **coloured dot**.
- **Transitions**: a circle irises out to the next block colour with a violet/cyan fringe — from the centre, from below, or from the previous headline's dot. Hard cut (`'cut'`) only for a punchline.
- **HUD**: corner brackets, brand + label top-left, chapter `02 — CODE` top-right, timecode + task boxes `■■□□□ 2/5` + progress line at the bottom (6:7 keeps only the line).
- **Subtitles**: one chunk per comma phrase, centred near the bottom, keywords on a coral (or black) pill.
- Motion only on the spoken word: every element is triggered by `at(line, '字')`.

## Workflow
1. **Script** — one sentence per line in `vo/lines.txt` (B 站 review voice: plain, a bit funny, real flaws, no ad slogans). Markers: `# 段落名` starts a new section (0.65 s pause), `#gap 1.25` puts a longer pause before the next line (room for a sound-effect gag). Hook sentence in `vo/hook.txt`. Get the script approved before any TTS.
2. **Voice** — `rv_tts.py vo/lines.txt vo/full --engine fish --voice <id> --speed 1.1` (or `--engine minimax --voice … --emotion happy`). Offer 4–6 samples first (`--sample`). Rules learned the hard way:
   - Use generic style voices or the user's own clone. **Skip celebrity / named-creator clones** in public voice libraries — they impersonate real people.
   - Fish API credit is separate from the website's membership credit (HTTP 402 → user tops up at fish.audio/app/developers).
   - MiniMax `surprised` can make some voices sound flat or down; when in doubt use `happy` everywhere.
3. **Align** — `rv_align.py vo/lines.txt vo/full` and `rv_align.py vo/hook.txt vo/hook --hook`. Uses **whisper medium** with the script as prompt; `small` hallucinated whole lines. Every mismatch is printed — fix before rendering (full-width `Ｉ` for commas is auto-fixed).
4. **Scenes** — copy `references/example_review/scenes_muse.py` and rewrite the scene functions. Call `setup(timeline, assets, avatar, brand, label, tasks, keywords)` first. Then:
   - `SEGS = [(start, bg, fg, chapter, task_no, scene_fn, origin)]` — origin `'c'` centre / `'b'` bottom / `'dot'` / `'cut'`.
   - `HOOK = Hook(...)` (beats of label + tilted result cards, a finale function, a sting title).
   - `sfx(fx)` for pops / typing / hits / sound clips, `extra_audio(vo, sr)` to mix a clip's own sound, `OUTRO`, `BGM`, `BGM_BED`.
5. **Test stills** — `rv_render.py scenes.py test/s still h1.0 h5.5 12.3 …` (one per segment at ~80% of its length, plus hook beats). Look at a montage; check both ratios (`--67`).
6. **Render** — `rv_render.py scenes.py 成片_小红书.mp4` and `… 成片_视频号.mp4 --67` (≈ real-time ×1.5 on an M1; run in background).
7. **Cover** — `rv_cover.py --image <hero> --t1 … --t2 … --ratio 3x4|6x7|4x3`. Keep the cover tag neutral (not "XX 自己生成的" ad tone).

## Scene catalog (content → component)
| what is said | component |
|---|---|
| section opener / punch word | `title(frame, t, '五个任务', at(i,'五'), fg)`; swap with `t_out=` for a second headline in the same scene |
| "I asked it to …" | `inputbox(...)` types the **real prompt from the screenshot** (truncate long ones with ……), send-button press, optional attachment thumbnail |
| it is working | `avatar(...)` + status `chip` that changes on the spoken word |
| comparison / specs | `table(cols, rows)` — numbers count up, best cell highlighted; values copied from the screenshot |
| show the real result | `img_card` rising from below + `pointer` + `chip` call-outs on the spoken words |
| a web page | `browser(...)` scrolls through stacked page screenshots on the words |
| look closer / a flaw | `zoom_card` pushes into a region; `ring` circles the defect |
| punchline / 包袱 | setup line + `#gap` in the script + hard `'cut'` segment: image slams in with shake, `fx.clip(...)` for the sound, big ASCII word ("What?") |
| a generated video | flip a card from the reference image to `video_at(...)`, then side-by-side with "=" |
| steps / pipeline | numbered `chip`s with arrows, lit one by one |
| a number (quota, %) | `big_number` + the settings screenshot card |
| verdict list | coral check circles + `check` |
| no support / missing | outlined boxes + `strike` |
| CTA | avatar + `inputbox` typing the question + `title('评论区见')` |

## Pitfalls (all hit in the Muse episode)
- `at(i, '书')` finds the **first** 书 — in "看书…书里的字" use `at(i, '书', 1)`. Always check the trigger lands on the intended word.
- Full-width `？` in Arial Black renders as a box; Menlo/Baskerville have no CJK — Chinese only in heavy/bold/med.
- Long headlines overflow at 200 px: `title()` shrinks automatically, but `word()` doesn't — size it yourself (≈ chars × size × 1.15 + 86 < 1010).
- Scenes whose headline waits for a late keyword leave 1–2 s of empty colour: show an early title (`ls(i)+.15`, `t_out=` the keyword).
- Chips under a 640-px card collide with subtitles (y ≥ 1232): keep call-outs inside the card or above y 1180.
- 6:7 crops 90 px top and bottom — keep content between y 150 and 1200, check `--67` stills.
- Keep music ~20 dB under the voice (`BGM_BED = -14`, plus −6 dB ducking while speaking); the first try at −20 was too quiet to notice.
- Compliance on 小红书 / 视频号: tick 「内容含 AI 生成」 for TTS voice and AI images; for overseas apps describe results only — no how-to-access, no links.

## What to report back
Output paths, duration, both ratios; the scene table; which on-screen phrases are paraphrases vs. quotes of the real prompts/screens; what you checked (stills, alignment mismatches = 0, loudness) and what you couldn't (listening, timing feel).
