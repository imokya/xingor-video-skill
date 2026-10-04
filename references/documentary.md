# documentary · 文物纪录片风格

The third look of this skill, for **script-driven explainer shorts about artifacts, history and places** (三星堆、敦煌、
藏经洞、富春山居图 …). Unlike NEON LAB and poetry-ink there is **no presenter video**: the input is a topic or a
script, the pictures come from open-licence photos, and the voice is synthesized. Output is 9:16 (1080×1920), with
an optional 3:4 (1080×1440, 小红书) version.

Everything lives in `SKILL_DIR/scripts/doc/`:
| file | does |
|---|---|
| `doc_core.py` | renderer core: timeline from `vo.json`, drawing kit, subtitles, 3:4 layout, audio mix, CLI |
| `doc_fetch.py` | Wikimedia Commons search / category / download (+ `img/credits.json`) / `素材授权.txt` |
| `doc_cutout.py` | rembg cutouts `img/x.jpg → cut/x.png` + a check sheet |
| `doc_tts.py` | MiniMax TTS, one wav per line + `vo.json`; voice samples |
| `doc_storyboard.py` | storyboard PNG pages for the user to approve |
| `doc_audio.py` | Mixkit SFX pack, SFX / music listings, music download + "doesn't fight the voice" scoring |

Full worked example: `references/example_documentary/scenes_sanxingdui.py` (27 lines, 2:53) — every shot is a
function you can copy.

Python deps (system python is fine): `pip install pillow numpy imageio-ffmpeg "rembg[cpu]"`. Fonts: macOS Songti SC.
TTS needs a `.env` (project dir or any parent) with `MINIMAX_API_KEY`, `MINIMAX_GROUP_ID`, `MINIMAX_REGION=cn|intl`.

---

## 1. The look in one breath
Deep bronze-teal darkness (`bg_grad`: #040607 → #162C2C), **gold** as the accent (GOLD #D9B26A, GOLD_HI #F6DC9A),
warm paper-white text (PAPER #F2E6CF), cinnabar (#B83428) only for seals and map dots.
- **Artifacts are cut out (rembg) and float** on the dark stage with a rim glow (`float_obj`, `rise_obj`, `rim_glow`),
  lit from above (`spot`), gently bobbing and turning in fake 3D (`persp`). This is the signature — it leaves room for
  animation around the object.
- **Photos that must keep their scene** (excavation photos, pits, hands close-ups, restoration labs, museum displays)
  become **cards**: rounded, gold-edged, shadowed, tilted in 3D (`card_img`, `put_card`), never full-frame.
- **Glass UI**: frosted glass cards / chips / stat cards (`glass`, `chip`, `stat_card`), gold leader lines with pulse
  dots (`leader`, `pulse_dot`), a slow rotating ring of tick marks behind the subject (`rings`), HUD corner brackets
  with a scan line and small location/time text (`hud`), god rays (`god_rays2`), dust/embers (`particles`).
- **Metal type**: gold-gradient Songti Black with a light sweep (`metal_put`); numbers tick up.
- **Text behind the artifact (打字在文物后面)**: huge characters typed one by one with a blinking cursor, drawn *before*
  the cutout so the object covers part of them (`type_behind`). Use it for the opening question and the title.
- Subtitles: Songti Bold 54 px, **always one line** — long sentences are split at punctuation into chunks timed by
  character count (`sub_chunks` / `draw_subs`).

## 2. Workflow (always confirm before rendering)
Project folder per topic, e.g. `~/Desktop/敦煌/三星堆/`. Run the tools from inside it.

1. **Condense the script** to 2–3 min: ~420–560 Chinese characters (≈3.9 chars/s plus pauses). Keep the author's
   structure and tone; merge repeats. Show the condensed text and **every factual change** (e.g. a pit-layer order you
   could not verify) and get approval. Save as `文案_精简版.txt`, one narration line per row (one line = one shot).
2. **Find pictures** (`doc_fetch.py search / category`). Prefer CC0 / public domain; CC BY / BY-SA need attribution.
   Look for: the most striking object (it opens the video), several angles of the hero object, clean museum shots
   on dark backgrounds (they cut out well), historic photos, maps/diagrams. Write `manifest.json`, then
   `doc_fetch.py get manifest.json`. Make a contact sheet and look at it.
3. **Cut out** the hero objects (`doc_cutout.py …`, then `--sheet`). Reject cutouts that drag in stands, cloth or glass —
   use those images as cards instead.
4. **Storyboard** (`storyboard.json` → `doc_storyboard.py`): one row per line — section, line, asset (`cut:name` /
   photo / null), what moves. Send the PNGs and **wait for "可以"**. Mention invented on-screen numbers and any
   illustrative (示意) animation.
5. **Voice** (`doc_tts.py 文案_精简版.txt --dict "词/(pin1)(yin1)"`). Add pronunciations for rare names (乐僔、纵目、
   殉葬…). Default voice `Chinese_deep_voiced_male_nv1`, model `speech-2.6-hd`, speed 0.95.
6. **Write the scenes file** (copy the example): `dc.init(".", lead, gap, tail, extra={i: pause})`, one shot function
   per line, `SHOTS = […]`, `sfx_events()`. `lt(i, "关键词")` gives the local time a word is spoken — trigger every
   visual on the spoken word.
7. **Stills first**: `python scenes.py --stills 3.4 15.2 …` (2 per shot) → contact sheet → fix → only then render.
   `--demo 25` renders just the opening for a style check when the look is new.
8. **SFX** (`doc_audio.py sfx`, after listing the pack to the user) and **music** (`doc_audio.py list-music …` →
   `doc_audio.py music ids…` → pick by the score) — download only after the user agrees.
9. **Render**: `python scenes.py --music music/188.mp3 --out ../成片.mp4`; 3:4: add `--ratio 3x4`.
   Then an upload copy: `ffmpeg -i 成片.mp4 -c:v libx264 -preset slow -crf 26 -c:a copy 上传版.mp4` (~55 MB for 3 min).
10. `doc_fetch.py credits --extra "音效：Mixkit …" --extra "配音：MiniMax …"` → `素材授权.txt`; offer a 小红书 caption.

## 3. Opening (the first 5 seconds decide everything)
- Open on the **single most striking object** (gold-foil bronze head, not a wide museum shot). No flash-cut montage —
  users found rapid flashing cheap.
- Pattern that worked: black → a horizontal gold **light slit** opens → the cutout is revealed by a top light sweeping
  down (`spot`) with god rays and a rotating ring → the question is **typed behind the object** (`type_behind`) on the
  spoken words → 2–3 glass "guess" chips float in → next line: the hero object flies out of depth with leader-line
  callouts and a measuring ruler → location radar + year counter cards → metal title typed behind the object.

## 4. Shot catalog: what the line says → what to build
| the line… | build | from the example |
|---|---|---|
| asks "what is this / where from" | cutout + typed question behind + guess chips | `v_shot_01` |
| names physical features | cutout + pulse dots + leader lines to glass cards + ruler | `v_shot_02` |
| place + age + name | radar card + year ticker card → `type_behind` title | `v_shot_03` |
| "why did they …" over many similar objects | 3D carousel of cutouts | `v_shot_04` |
| "the answer lies in what was found with it" | photo cards fanned like playing cards, one zooms in | `v_shot_05` |
| a size / height | cutout rises + vertical ruler counting up | `v_shot_06` |
| structure (layers, branches, count) | dimmed cutout + gold schematic lines drawn on the words + counter cards | `v_shot_08` |
| heaven / earth, belief | light pillar, rings top and bottom, metal 天 / 地 | `v_shot_09` |
| "the voices are gone" | tilted photo card + a sound wave flattening to a line | `v_shot_10` |
| three details in a row | three photo cards dealt one after another with captions | `v_shot_11` |
| an empty hand / a missing part | big card, gold rings traced around the gaps, glowing | `v_shot_12` |
| competing guesses | translucent 示意 outlines in the gap + small evidence card + 「存疑」 seal | `v_shot_13` |
| "the story is in how they were found" | cutouts fall into a glowing pit mouth | `v_shot_14` |
| a year / a discovery | metal year slams in + sepia photo card + mini site map (示意) | `v_shot_15` |
| lists items in a photo | slow pan inside a card + chips on each spoken item | `v_shot_16` |
| damage, ash, fire | card + cracks drawing in + embers / ash | `v_shot_17` |
| skill, material, labour | cutout turning + three stat cards | `v_shot_18` |
| a bare question | metal "？" slam + falling earth | `v_shot_19` |
| layers / stratigraphy | glass frame section, layers drop in on the words (示意) | `v_shot_20` |
| restoration | lab photo card → cutout cut into pieces that fly back together | `v_shot_23` |
| ending | silhouettes + stars → back to the first object → metal title + credits, fade | `v_shot_25–27` |

## 5. Sound
- **SFX are real recordings (Mixkit)**, never synthesized — users disliked synthetic booms. Align each sample's
  **peak** to the visual event (`sfx_events()` returns `(id, t, gain)`; `build_audio` aligns the peak). Typical gains
  0.2–0.6; typing = 3005 at 0.2 per character; the narration ducks SFX by ~4 dB.
- **Music**: pick by `doc_audio.py music` score — steady (<10 dB swing), little energy at 1–4 kHz (<5 %), few
  transients, longer than the film. Mix ≈ −13 dB under the voice, −6 dB more while someone speaks, EQ dips at
  1.2 / 2.5 kHz, 2 s fade-in, 4 s fade-out (all done by `build_audio(music=…)`). Ask before adding music; the default
  is voice + SFX only.
- You cannot listen: report loudness numbers (`volumedetect` / RMS per section) and ask the user to check by ear.

## 6. 3:4 (小红书)
`--ratio 3x4`: the 9:16 canvas is drawn as usual; the content band y 140–1520 is scaled to 900×1150 and centred
(80 px top margin) over a blurred, darkened copy of itself with feathered edges; subtitles are drawn directly on the
3:4 frame (top y 1268, ~90 px bottom margin); HUD small text moves to the two bottom corners so it never collides
with top titles. **Don't simply crop** the 9:16 frame — titles at the top and subtitles at the bottom get cut, and
users want white space above and below. Keep the HUD small text (users asked to keep it).

## 7. Pitfalls (all hit in practice)
- Wikimedia rate-limits non-standard thumbnail widths and originals (HTTP 429): request 1280 / 1920 / 3840 only.
- `cover()` float rounding can make a crop box negative → clamp with `max(0.0, …)` (already done in the core).
- Keep important content inside x 60–1020 and y 160–1500 on the 9:16 canvas (subtitles start at 1530).
- `type_behind` text must be drawn **before** the object; place it so the object covers only part (top of the word
  above the head, or the head covering the bottom third).
- Leave ≥ 0.3 s between a shot's start and its first trigger so the cross-fade (0.4 s) does not swallow it.
- Illustrative graphics (structure lines, sections, outlines, map positions) must say 示意 on screen.
- Numbers on screen that are not in the user's script (sizes, dates) must be listed in the report.
- Long renders: ~3 min for 3 min of 9:16 on 8 cores; render stills first.

## 8. Report back
Output paths (master + upload copy), duration, resolution; what changed since the last version; what you checked
(stills, stream info, loudness) and what you could not (sound by ear); invented / added numbers; 示意 graphics; licence
notes (CC BY / BY-SA need attribution → 素材授权.txt).
