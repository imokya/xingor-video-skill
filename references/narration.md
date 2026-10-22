# Narration · AI 配音 that sounds like a person

Applies to every style with a TTS voice-over (flat-review, showcase, documentary, a topic-only explainer). The tool is
`scripts/review/rv_tts.py`; its output (`vo.json` + `audio/vo_XX.wav`) feeds `rv_align.py` and any scenes timeline.

## TL;DR
```bash
python rv_tts.py vo/lines.txt vo/full --engine fish --voice <id> --speed 1.06 --para --verify
```
1. **Model `s2.1-pro`** (the default for Fish). It follows inline directions. `s1` ignores them and sometimes **reads them
   aloud** (a video opened with an audible "Interest…" from `(interested)`); the script strips directions for s1 / MiniMax.
2. **Write directions in short Chinese, inside the sentence, where the tone changes**: `[压低到耳语，像在说秘密] 那我们把格陵兰，挪到非洲旁边……`
3. **Synthesize a whole paragraph at once (`--para`)**, then cut it back into sentences. Per-line synthesis restarts the
   intonation on every line — that, more than the timbre, is what makes TTS sound like TTS.
4. **Verify (`--verify`)** — every clip is transcribed and compared with the script. Re-synthesize anything flagged.

## The script (`vo/lines.txt`)
- One sentence per line; `# 段落名` starts a paragraph (also the unit of `--para` synthesis and a 0.65 s pause in `rv_align`).
- Spoken, not written: short clauses, commas where you'd breathe, a few particles (居然、你看、这可不是、其实、对吧).
  Ask questions and answer them; talk to 「你」.
- Numbers as people say them where it matters (`十四倍`, `三千多公里`); keep years as digits (`1569年` reads fine).
- `vo.json` keeps `text` (directions removed — used for subtitles and alignment) and `tts` (the line as sent).

## Writing directions (s2 series)
- **Short and concrete, like a director talking to an actor** — tone + manner, 2–8 characters each:
  `[悬疑纪录片解说腔，低沉，制造悬念]` · `[轻笑，带点挑衅]` (produces an actual chuckle) · `[压低到耳语，像在说秘密]` ·
  `[猛然提高音量，非常震惊]` · `[放慢，一字一顿，严肃]` · `[神秘地笑，吊足胃口]` · `[恍然大悟]` · `[无奈地叹气]` ·
  `[讲故事的语气]` · `[语气一转，严肃]` · `[平静，娓娓道来]` · `[温柔]` · `[轻松，和观众互动]`.
- **Not sentences.** `[语气一转，凑近，像要说个秘密]` was spoken as words ("凑近想要说个秘密"); `[神秘地]` fixed it. If a
  direction reads like narration, the model may narrate it. `--verify` catches this.
- Put the direction **at the point where the tone changes**, not only at line start; it carries until the next one.
- **Dosage: drama at the hook, the re-hooks and the reveals; calm for the explanation.** A whole video in suspense voice
  sounds like a short-drama ad. Make an A/B (`--sample`) of the hook paragraph — current vs. stronger — and let the
  user choose before doing the full script.
- Drama lengthens lines (pauses, slower delivery): a hook paragraph went from ~16 s to ~20 s with heavy directions.
  Re-check the slots after any change of directions.

## How `--para` works
1. Lines between `#` markers are joined and synthesized in one request (cached in `<out>/para/<hash>.wav`; only edited
   paragraphs are re-synthesized).
2. faster-whisper (`--asr small`, word timestamps) maps the transcript's characters to time; a cut point is estimated from
   each sentence's share of the paragraph's characters, then **snapped to the longest pause within ±0.6 s** (sentences
   always end in a pause — a cut placed purely by character ratio once landed mid-phrase and dropped "可放回地球上").
3. Each sentence is trimmed of edge silence (keeps a short breath), faded 10 ms, saved as `vo_XX.wav`.
4. Place the clips on the timeline as usual; spacing between sentences comes from the timeline, the intonation from the
   paragraph.

## Verify — always
- `--verify` flags clips whose transcript is <0.8× or >1.25× the expected length, or that contain words from a direction.
- Homophone errors in the transcript (格林兰 / 默卡托 / 繁体) are ASR noise — ignore them. Missing words, extra words
  and spoken directions are real — fix the text or the direction and re-run (only that paragraph is re-synthesized).
- Watch the paragraph length: once a paragraph came back at 45 s instead of ~15 s (a garbled generation). Delete its file
  in `<out>/para/` and re-run.
- Fish's API occasionally drops the SSL connection; the script retries.

## Timing against the picture
- Keep a per-line start-time list (`times.json`) next to the picture timeline and check `start + dur < next start − 0.1 s`
  after every re-synthesis.
- If the picture is keyframed in its own "design time", don't move keyframes when the voice changes — remap time
  (piecewise-linear warp from output time to design time) so that each visual beat starts on its line.
- Long lines become several subtitle screens: split at punctuation, ≤16 characters per screen, each screen's duration
  proportional to its character count within the line.

## Mix
- Voice ~16 dB above the music while speaking (the user prefers light music; 13 dB still sounded loud) (duck the music around each line, 0.25 s before / 0.4 s after).
- Normalize the final mix to **−14 LUFS, true peak −1.5 dB** (`loudnorm=I=-14:TP=-1.5:LRA=11`) — at the −18 LUFS a raw
  mix tends to land on, the video plays noticeably quieter than its neighbours in the feed.
- Offer a version without music (voice + SFX only) so the user can add a track from the platform's licensed library.

## Voice & compliance
- Use generic voices or the user's own clone (Fish model id). Never clone celebrities or named creators.
- On 小红书 / 视频号, tick 「内容含 AI 生成」 for TTS narration.
- A real recording by the creator still beats any TTS for trust; if they record, `rv_align.py` aligns it the same way.
