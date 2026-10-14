# showcase · 作品宣传片

A **promo built from footage that already exists**: your past outputs, travel clips, renders, screen recordings, plus a
narration. No presenter needed. First made for the xingor-video-skill launch (16:9 and 3:4, ~100 s, Fish voice);
the 3:4 cut is `references/example_showcase/scenes_promo_3x4.py`, the cover `example_showcase/cover_xhs.py`.
Reusable pieces: `scripts/kit/showcase.py` (`from kit.showcase import *`) and `scripts/kit/music.py`.

## Look that was approved (after rejecting neon-green, ultra-minimal and pixel-dot looks)
- **Black + one ice accent.** Near-black `#09090B`, white text, a single ice blue `#9EC4FF`; per-chapter tints only in
  the background glow (gold for documentary, vermilion for poetry). Film grain + vignette on every frame.
- **Type:** PingFang Light/Regular for Chinese body, Avenir Next Regular / UltraLight for Latin. The wordmark is thin,
  tracked and filled with a white → ice → mist gradient. Heavy Lantinghei only for hook headlines and the cover.
- **Rounded everything:** cards r≈22, pills, glass panels with a 1 px gradient edge. Reflections clipped to the same
  rounded corners.
- **Motion kept from the energetic version:** letters slide/rise in, cards spring in, data streams with travelling
  dots, rotating tick rings, push-blur (zoom-through) transitions, a glitch only where the globe comes in.
- **Balance:** “简约但不无聊”. Users called a pure wordmark “too minimal” and a full-white final title “plain”; they also
  called footage-filled letters “messy” (the footage colour merges with the background). The fix that worked: thin
  gradient letters, a 0.15 s clip flash as each letter lands, and something that keeps moving under the title.

## Structure that worked (≈100 s)
| beat | how |
|---|---|
| 0–1.3 s **prompt** | an AI composer panel (glass, sweeping edge light, header `xingor · 新建视频任务`, toolbar chips) types the one-line request; send button presses + ripples; light streak |
| 1.3–5 s **wall** | a tilted wall of real output stills; the camera pans and one card per beat pops forward and plays (label + big title); the most unique result (travel route) takes the full frame last |
| 5–7 s **claim** | 你只说一句话 / 剩下的，交给它剪 |
| 7–12 s **title** | `timeline_title`: a timeline panel; the playhead reaches each clip → its letter lands; playhead, timecode and waveform keep running |
| 12–47 s **hero feature first** | the strongest, most visual feature right after the title (here: the travel-route animation, two legs, real footage between legs as 3D cards) |
| then | inputs → skill core → output; the pipeline as numbered steps; numbers (5 / 44 / 3) count up; one chapter per style with its real output as 3D cards; a 3D carousel with a fly-through; the long component list on `tilted_list`; install (`git clone` typed in a terminal) + three example prompts; end card |
| tail | the creator's 关注 / follow clip, **never cropped** (fit, centred on black) |

## Footage rules (each one was a bug report)
- **Probe before you place.** `clip_info()` for duration and *display* size: phone files carry rotation side-data
  (a `1080x1920` stream can be landscape). Never let a clip run past its end (it shows a blank / freeze) — start
  earlier or slow it (`speed=.6`).
- **No black frames.** Sample candidate start times with `pick_start()`; documentary sources have long dark passages.
- **Crop the junk:** window frames, gradients, player toolbars, mouse cursors, hands holding phones (`crop=`).
  A recording with a baked-in cursor should not be used on a cover.
- **Vertical clips are cards, not letterboxes.** `vcard()` flips them in as 3D cards; three portrait clips fan out.
- **Light cards:** turn `sweep=False` and `amb=False` on paper / white footage — the light sweep washes text out.

## Layout rules
- **Safe area:** titles and cards between ~9 % from the top and the subtitle band (bottom ~10 %). Run
  `safe_overlay()` on a montage of stills for every scene before a full render; check text-over-card overlaps.
- **3:4 is a re-layout, not a crop.** Every scene goes top-to-bottom: chapter title on top, cards below, rows become
  columns, 6-column grids become 3, carousels get a smaller radius. Re-render travel legs at `"size": [1080, 1440]`
  (the travel camera scales its focal length for portrait automatically). Subtitles ~46 px on 3:4.
- **Long lists:** never a wall of 44 readable chips — use `tilted_list` (perspective plane scrolling away).
- **Fit every string** to its box (`fit_font`); Chinese UI everywhere except brand names, URLs and commands.

## Sound and voice
- Narration per line with Fish Audio (the user's own voice model); place each line by design time, duck the music
  ~55 % under it. Brand names the TTS cannot read: write them phonetically in the TTS text only (`xingor` → `星哥儿`),
  keep the real spelling in the subtitles.
- `kit/music.py` makes a 120 BPM bed with sections (`intro / groove / full / break / build / outro`) and risers into
  given hit times — set the hits on the chapter cuts. Synth SFX from `kit/sfx.py` on every card / letter landing.

## Covers (小红书 3:4)
Tilted wall of real output frames on top; a huge bold hook (`一句话 / 剪出大片`, the second line on an accent block);
the product name as a strong *second* layer in thin tracked type right above the hook; 2 numbers beside it; a footer
with platforms and styles. The hook sells the click, the name must still be readable at a glance.

## Process
Iterate on stills (`test` times at the busiest moment of each scene, montage them), then render; send one-line
style frames before a full render when the look changes. Render 3:4 and 16:9 from separate scene files that share
the kit. Report what was checked (stills, loudness) and what was not (real-time playback).
