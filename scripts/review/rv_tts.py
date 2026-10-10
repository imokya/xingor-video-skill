"""逐句配音（Fish Audio / MiniMax）：文案一行一句 -> <out>/audio/vo_XX.wav（44.1k 单声道）+ <out>/vo.json
  python rv_tts.py vo/lines.txt vo/full --engine fish --voice <模型ID> [--speed 1.1]
  python rv_tts.py vo/lines.txt vo/full --engine minimax --voice Chinese_calm_streamer_nv1 --speed 1.15 --emotion happy
  python rv_tts.py vo/hook.txt vo/hook ...                 # 钩子那一句
  python rv_tts.py --sample "试读一段" --engine fish --voice A --voice B ...   # 出试听 -> 配音试听/
文案里以 # 开头的行是段落/停顿标记（不念）。已合成且文本/音色/语速/情绪没变的句子会跳过（改一句只重配那一句）。
密钥读 .env（当前目录或上级）：FISH_API_KEY；或 MINIMAX_API_KEY、MINIMAX_GROUP_ID、MINIMAX_REGION=cn|intl
音色：只用通用风格音色或用户本人的克隆，不要用名人 / 真实博主的声音克隆。
"""
import json, os, subprocess, sys, time, urllib.request, wave
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

def tts_fish(text, voice, fmt='mp3'):
    body = {'text': text, 'reference_id': voice, 'format': fmt, 'mp3_bitrate': 192, 'normalize': True, 'latency': 'normal'}
    if SPEED != 1.0: body['prosody'] = {'speed': SPEED, 'volume': 0}
    req = urllib.request.Request('https://api.fish.audio/v1/tts', data=json.dumps(body).encode(), headers={
        'Authorization': 'Bearer ' + os.environ['FISH_API_KEY'], 'Content-Type': 'application/json', 'model': opt('--model', 's1')})
    for _ in range(6):
        try: return urllib.request.urlopen(req, timeout=300).read()
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(10); continue
            msg = e.read()[:300]
            if e.code == 402: raise SystemExit('Fish API 额度不足：API 额度和网站积分分开算，去 fish.audio/app/developers 充值')
            raise SystemExit(f'Fish 错误 {e.code}: {msg}')
    raise SystemExit('Fish 限流重试失败')

def tts_minimax(text, voice, fmt='mp3'):
    host = 'https://api.minimaxi.com' if os.environ.get('MINIMAX_REGION', 'cn') == 'cn' else 'https://api.minimax.io'
    vs = {'voice_id': voice, 'speed': SPEED, 'vol': 1, 'pitch': 0}
    if EMO: vs['emotion'] = EMO
    body = {'model': opt('--model', 'speech-2.6-hd'), 'text': text, 'stream': False, 'voice_setting': vs,
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

if '--sample' in sys.argv:
    Path('配音试听').mkdir(exist_ok=True)
    for v in opt('--voice', many=True):
        Path(f"配音试听/{ENGINE}_{v.replace(' ', '_')[:40]}.mp3").write_bytes(TTS(opt('--sample'), v)); print('ok', v); time.sleep(1)
    sys.exit()

src, out = Path(sys.argv[1]), Path(sys.argv[2])
VOICE = opt('--voice') or sys.exit('需要 --voice')
lines = [l.strip() for l in src.read_text().splitlines() if l.strip() and not l.strip().startswith('#')]
(out / 'audio').mkdir(parents=True, exist_ok=True)
vj = out / 'vo.json'
old = {x['text']: x for x in json.loads(vj.read_text())} if vj.exists() else {}
res = []
for i, text in enumerate(lines):
    dst = out / 'audio' / f'vo_{i:02d}.wav'
    o = old.get(text)
    if o and o['file'] == f'audio/{dst.name}' and dst.exists() and o.get('voice') == VOICE and o.get('speed') == SPEED \
            and o.get('engine') == ENGINE and o.get('emotion') == EMO:
        res.append(o); continue
    to_wav(TTS(text, VOICE), dst)
    with wave.open(str(dst)) as w: dur = w.getnframes() / w.getframerate()
    res.append({'text': text, 'file': f'audio/{dst.name}', 'dur': round(dur, 3), 'voice': VOICE, 'speed': SPEED, 'engine': ENGINE, 'emotion': EMO})
    print(i, round(dur, 2), text, flush=True)
    vj.write_text(json.dumps(res, ensure_ascii=False, indent=1)); time.sleep(.5)
vj.write_text(json.dumps(res, ensure_ascii=False, indent=1))
print('total', round(sum(x['dur'] for x in res), 1), 's')
