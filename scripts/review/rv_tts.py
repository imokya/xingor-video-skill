"""配音（Fish Audio / MiniMax）：文案一行一句 -> <out>/audio/vo_XX.wav（44.1k 单声道）+ <out>/vo.json
  python rv_tts.py vo/lines.txt vo/full --engine fish --voice <模型ID> [--speed 1.06] --para --verify   # 推荐
  python rv_tts.py vo/lines.txt vo/full --engine fish --voice <模型ID>                                   # 逐句合成
  python rv_tts.py vo/lines.txt vo/full --engine minimax --voice Chinese_calm_streamer_nv1 --speed 1.15 --emotion happy
  python rv_tts.py vo/hook.txt vo/hook ...                 # 钩子那一句
  python rv_tts.py --sample "试读一段" --engine fish --voice A --voice B ...   # 出试听 -> 配音试听/
文案里以 # 开头的行是段落/停顿标记（不念）。已合成且文本/音色/语速/情绪/模型没变的句子会跳过（改一句只重配那一句）。

语气指令（Fish s2 系列）：在句中要变语气的位置写中文短指令，如「[压低声音，神秘地] 那我们把它挪过去……」。
  - 默认模型 s2.1-pro。s1 不认指令，还可能把它念出来，所以 s1 / MiniMax 会自动去掉指令再合成。
  - vo.json 里 text = 去掉指令的纯文本（字幕、rv_align 对齐用），tts = 原文（含指令）。
--para：按「# 段落」整段合成（句间语调连贯，最像真人），再用 faster-whisper 词时间戳 + 句间最长停顿切回逐句。
        段落音频按内容缓存在 <out>/para/，改一段只重配那一段。--asr small|medium 选识别模型（默认 small，只用来找切点）。
--verify：合成后逐句转写核对，标出把指令念出来、漏字或多字的句子。详见 references/narration.md。
密钥读 .env（当前目录或上级）：FISH_API_KEY；或 MINIMAX_API_KEY、MINIMAX_GROUP_ID、MINIMAX_REGION=cn|intl
音色：只用通用风格音色或用户本人的克隆，不要用名人 / 真实博主的声音克隆。
"""
import hashlib, json, os, re, subprocess, sys, time, urllib.request, wave
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def load_env():
    for d in [Path.cwd(), *Path.cwd().parents]:
        f = d / '.env'
        if f.exists():
            for line in f.read_text().splitlines():
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip())
            return
load_env()

def opt(name, default=None, many=False):
    vals = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == name]
    return vals if many else (vals[0] if vals else default)

ENGINE = opt('--engine', 'fish'); SPEED = float(opt('--speed', '1.0')); EMO = opt('--emotion')
MODEL = opt('--model', 's2.1-pro' if ENGINE == 'fish' else 'speech-2.6-hd')
TAGS = ENGINE == 'fish' and MODEL.startswith('s2')          # 只有 s2 系列认行内语气指令
plain = lambda s: re.sub(r'\[[^\]]*\]', '', s).strip()      # 去掉 [指令]
chars = lambda s: re.sub(r'[\W_]', '', plain(s))            # 只留汉字 / 字母 / 数字，用来数字数
say = lambda s: s if TAGS else plain(s)

def tts_fish(text, voice, fmt='mp3'):
    body = {'text': text, 'reference_id': voice, 'format': fmt, 'mp3_bitrate': 192, 'normalize': True, 'latency': 'normal'}
    if SPEED != 1.0: body['prosody'] = {'speed': SPEED, 'volume': 0}
    req = urllib.request.Request('https://api.fish.audio/v1/tts', data=json.dumps(body).encode(), headers={
        'Authorization': 'Bearer ' + os.environ['FISH_API_KEY'], 'Content-Type': 'application/json', 'model': MODEL})
    for k in range(6):
        try: return urllib.request.urlopen(req, timeout=300).read()
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(10); continue
            msg = e.read()[:300]
            if e.code == 402: raise SystemExit('Fish API 额度不足：API 额度和网站积分分开算，去 fish.audio/app/developers 充值')
            raise SystemExit(f'Fish 错误 {e.code}: {msg}')
        except (urllib.error.URLError, ConnectionError) as e:   # 偶发 SSL 断连
            print('网络重试', e, flush=True); time.sleep(3 + k * 2)
    raise SystemExit('Fish 重试失败')

def tts_minimax(text, voice, fmt='mp3'):
    host = 'https://api.minimaxi.com' if os.environ.get('MINIMAX_REGION', 'cn') == 'cn' else 'https://api.minimax.io'
    vs = {'voice_id': voice, 'speed': SPEED, 'vol': 1, 'pitch': 0}
    if EMO: vs['emotion'] = EMO
    body = {'model': MODEL, 'text': text, 'stream': False, 'voice_setting': vs,
            'audio_setting': {'sample_rate': 44100, 'format': fmt, 'channel': 1}}
    req = urllib.request.Request(f"{host}/v1/t2a_v2?GroupId={os.environ.get('MINIMAX_GROUP_ID', '')}", data=json.dumps(body).encode(),
                                 headers={'Authorization': f"Bearer {os.environ['MINIMAX_API_KEY']}", 'Content-Type': 'application/json'})
    for _ in range(8):
        d = json.load(urllib.request.urlopen(req, timeout=300))
        if d['base_resp']['status_code'] != 1002: break
        time.sleep(15)
    if d['base_resp']['status_code'] != 0: raise SystemExit(f"MiniMax 错误：{d['base_resp']}")
    return bytes.fromhex(d['data']['audio'])

TTS = tts_fish if ENGINE == 'fish' else tts_minimax

def to_wav(data, dst):
    from rv_core import FF
    tmp = dst.with_suffix('.tmp.mp3'); tmp.write_bytes(data)
    subprocess.run([FF, '-v', 'error', '-y', '-i', str(tmp), '-ac', '1', '-ar', '44100', str(dst)], check=True); tmp.unlink()

def load_mono(path, sr=44100):
    import numpy as np
    from rv_core import FF
    out = subprocess.run([FF, '-v', 'error', '-i', str(path), '-f', 's16le', '-ac', '1', '-ar', str(sr), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.int16).astype(np.float32) / 32768

def save_wav(path, x, sr=44100):
    import numpy as np
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

_asr = None
def asr():
    global _asr
    if _asr is None:
        from faster_whisper import WhisperModel
        _asr = WhisperModel(opt('--asr', 'small'), device='cpu', compute_type='int8')
    return _asr

def to16k(a):
    import numpy as np
    return np.interp(np.arange(0, len(a), 44100 / 16000), np.arange(len(a)), a).astype(np.float32)

if '--sample' in sys.argv:
    Path('配音试听').mkdir(exist_ok=True)
    for v in opt('--voice', many=True):
        Path(f"配音试听/{ENGINE}_{v.replace(' ', '_')[:40]}.mp3").write_bytes(TTS(say(opt('--sample')), v)); print('ok', v); time.sleep(1)
    sys.exit()

src, out = Path(sys.argv[1]), Path(sys.argv[2])
VOICE = opt('--voice') or sys.exit('需要 --voice')
paras, cur = [], []
for raw in src.read_text().splitlines():
    l = raw.strip()
    if not l: continue
    if l.startswith('#'):
        if cur: paras.append(cur); cur = []
        continue
    cur.append(l)
if cur: paras.append(cur)
lines = [l for p in paras for l in p]
(out / 'audio').mkdir(parents=True, exist_ok=True)
vj = out / 'vo.json'
old = {x.get('tts', x['text']): x for x in json.loads(vj.read_text())} if vj.exists() else {}
meta = {'voice': VOICE, 'speed': SPEED, 'engine': ENGINE, 'emotion': EMO, 'model': MODEL}
res = []

def item(raw, fn, dur, **kw):
    return {'text': plain(raw), 'tts': raw, 'file': fn, 'dur': round(dur, 3), **meta, **kw}

if '--para' in sys.argv:
    # ---------- 整段合成 → 逐句切开 ----------
    import numpy as np
    SR = 44100; (out / 'para').mkdir(exist_ok=True)
    idx = 0
    for P in paras:
        text = ' '.join(say(s) for s in P)
        h = hashlib.md5(json.dumps([text, meta], ensure_ascii=False).encode()).hexdigest()[:10]
        fns = [f'audio/vo_{idx + k:02d}.wav' for k in range(len(P))]
        if all(old.get(s, {}).get('para') == h and old[s]['file'] == fns[k] and (out / fns[k]).exists() for k, s in enumerate(P)):
            res += [old[s] for s in P]; idx += len(P); continue
        pf = out / 'para' / f'{h}.wav'
        if not pf.exists(): to_wav(TTS(text, VOICE), pf)
        a = load_mono(pf, SR)
        segs, _ = asr().transcribe(to16k(a), language='zh', word_timestamps=True)
        tc = []   # 转写里每个字的起止时间
        for s in segs:
            for w in s.words:
                cs = re.sub(r'[\W_]', '', w.word)
                for k in range(len(cs)): tc.append((w.start + (w.end - w.start) * k / len(cs), w.start + (w.end - w.start) * (k + 1) / len(cs)))
        env = np.convolve(np.abs(a), np.ones(int(.03 * SR)) / int(.03 * SR), 'same')
        quiet_th = max(.006, np.percentile(env, 20))
        target = [len(chars(s)) for s in P]; tot = sum(target); bounds, acc = [0.0], 0
        for n in target[:-1]:
            # 按字数比例估一个切点，再吸到前后 0.6 s 内最长的那段停顿中间（句间一定有停顿）
            acc += n; ci = min(len(tc) - 1, max(0, round(acc / tot * len(tc)) - 1)) if tc else 0
            est = (tc[ci][1] + tc[min(len(tc) - 1, ci + 1)][0]) / 2 if tc else acc / tot * len(a) / SR
            lo, hi = max(0, int((est - .6) * SR)), min(len(a) - 1, int((est + .6) * SR))
            best, bs, run, rs = 0, None, 0, 0
            for q, quiet in enumerate(env[lo:hi] < quiet_th):
                if quiet: run += 1; rs = rs if run > 1 else q
                else: run = 0
                if run > best: best, bs = run, rs
            bounds.append((lo + (bs + best // 2 if bs is not None else int(np.argmin(env[lo:hi])))) / SR)
        bounds.append(len(a) / SR)
        for k, s in enumerate(P):
            x = a[int(bounds[k] * SR):int(bounds[k + 1] * SR)].copy()
            nz = np.where(np.abs(x) > .01)[0]                         # 去首尾静音，留一点气口
            if len(nz): x = x[max(0, nz[0] - int(.03 * SR)):nz[-1] + int(.08 * SR)]
            f = int(.01 * SR); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
            save_wav(out / fns[k], x, SR)
            res.append(item(s, fns[k], len(x) / SR, para=h)); print(idx + k, round(len(x) / SR, 2), plain(s), flush=True)
        idx += len(P)
        vj.write_text(json.dumps(res, ensure_ascii=False, indent=1))
else:
    # ---------- 逐句合成 ----------
    for i, raw in enumerate(lines):
        dst = out / 'audio' / f'vo_{i:02d}.wav'
        o = old.get(raw)
        if o and o['file'] == f'audio/{dst.name}' and dst.exists() and all(o.get(k) == v for k, v in meta.items()) and 'para' not in o:
            res.append(o); continue
        to_wav(TTS(say(raw), VOICE), dst)
        with wave.open(str(dst)) as w: dur = w.getnframes() / w.getframerate()
        res.append(item(raw, f'audio/{dst.name}', dur)); print(i, round(dur, 2), plain(raw), flush=True)
        vj.write_text(json.dumps(res, ensure_ascii=False, indent=1)); time.sleep(.5)
vj.write_text(json.dumps(res, ensure_ascii=False, indent=1))
print('total', round(sum(x['dur'] for x in res), 1), 's')

if '--verify' in sys.argv:
    # ---------- 逐句转写核对 ----------
    bad = 0
    for i, x in enumerate(res):
        got = re.sub(r'[\W_]', '', ''.join(s.text for s in asr().transcribe(to16k(load_mono(out / x['file'])), language='zh')[0]))
        want = chars(x['text']); tags = ''.join(re.findall(r'\[([^\]]*)\]', x.get('tts', '')))
        leaked = [w for w in re.findall(r'[一-鿿]{2,}', tags) if w in got and w not in want]   # 指令被念出来
        ratio = len(got) / max(1, len(want))
        if leaked or not .8 <= ratio <= 1.25:
            bad += 1; print(f'⚠ {i:02d} 字数比 {ratio:.2f}' + (f' 念出了指令：{leaked}' if leaked else '') + f'\n   原文：{x["text"]}\n   转写：{got}')
    print('核对完毕：' + ('全部通过' if not bad else f'{bad} 句要检查（同音错字可忽略，漏字 / 多字 / 念出指令要重配）'))
