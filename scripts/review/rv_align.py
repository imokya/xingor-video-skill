"""拼配音轨 + 逐句字级对齐 -> <dir>/timeline.json + <dir>/vo_track.wav（钩子用 --hook -> words.json）
  python rv_align.py vo/lines.txt vo/full
  python rv_align.py vo/hook.txt vo/hook --hook
文案标记：「# 任意说明」= 下一句是新段落（前面停 0.65 s）；「#gap 1.25」= 下一句前停 1.25 s（给音效/包袱留位置）。
普通句间停 0.3 s，第一句前 0.4 s。用 faster-whisper medium + 原文做提示（small 会胡乱识别），逐句核对原文，对不上会列出来。
需要 faster-whisper（work/.venv）。
"""
import json, re, sys, wave
import numpy as np
from pathlib import Path

src, D = Path(sys.argv[1]), Path(sys.argv[2])
HOOK = '--hook' in sys.argv
norm = lambda s: re.sub(r'[^\w]', '', s).replace('_', '')
vo = json.loads((D / 'vo.json').read_text())

gaps, nxt = [], None
first = True
for raw in src.read_text().splitlines():
    l = raw.strip()
    if not l: continue
    if l.startswith('#gap'): nxt = float(l.split()[1]); continue
    if l.startswith('#'):
        if not first: nxt = nxt or .65
        continue
    gaps.append(nxt if nxt is not None else (.4 if first else .3)); nxt = None; first = False
assert len(gaps) == len(vo), f'文案 {len(gaps)} 句，vo.json {len(vo)} 句：先跑 rv_tts.py'

from faster_whisper import WhisperModel
model = WhisperModel('medium', device='cpu', compute_type='int8')

def words_of(path, text, offset):
    segs, _ = model.transcribe(str(path), language='zh', word_timestamps=True, initial_prompt=text)
    ws = []
    for s in segs:
        for w in s.words:
            t = w.word.strip().replace('Ｉ', '，')          # whisper 偶尔把逗号认成全角 I
            ws.append(dict(w=t, s=round(offset + float(w.start), 3), e=round(offset + float(w.end), 3)))
    return ws

if HOOK:
    ws = words_of(D / vo[0]['file'], vo[0]['text'], 0)
    (D / 'words.json').write_text(json.dumps(ws, ensure_ascii=False))
    ok = norm(''.join(w['w'] for w in ws)) == norm(vo[0]['text'])
    print('hook', '一致' if ok else '对不上：' + ''.join(w['w'] for w in ws)); sys.exit()

chunks, lines, t, sr = [], [], 0.0, None
for i, x in enumerate(vo):
    with wave.open(str(D / x['file'])) as w:
        sr = sr or w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    chunks += [np.zeros(int(gaps[i] * sr), np.int16), a]; t += gaps[i]
    ws = words_of(D / x['file'], x['text'], t)
    lines.append(dict(text=x['text'], s=round(t, 3), e=round(t + len(a) / sr, 3), words=ws))
    t += len(a) / sr
chunks.append(np.zeros(int(1.0 * sr), np.int16))
track = np.concatenate(chunks)
with wave.open(str(D / 'vo_track.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(track.tobytes())
(D / 'timeline.json').write_text(json.dumps(dict(dur=round(len(track) / sr, 3), lines=lines), ensure_ascii=False, indent=1))
bad = [i for i, l in enumerate(lines) if norm(l['text']) != norm(''.join(w['w'] for w in l['words']))]
print('dur', round(len(track) / sr, 2), 's | 句数', len(lines), '| 对不上的句子', bad or '无')
for i in bad: print(f'  {i} 原文：{lines[i]["text"]}\n     识别：{"".join(w["w"] for w in lines[i]["words"])}')
