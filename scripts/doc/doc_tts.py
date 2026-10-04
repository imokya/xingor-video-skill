"""MiniMax 逐句配音：文案（一行一句）-> audio/vo_XX.wav + vo.json（每句时长，渲染时间轴用）

  python doc_tts.py 文案_精简版.txt [--voice Chinese_deep_voiced_male_nv1] [--model speech-2.6-hd] [--speed 0.95]
                    [--dict "纵目/(zong4)(mu4)" --dict "古蜀/(gu3)(shu3)"]
  python doc_tts.py --sample "试读的一段话" --voice A --voice B ...    # 出几版试听 -> 配音试听/

需要 .env（项目目录或任意上级目录）：MINIMAX_API_KEY、MINIMAX_GROUP_ID、MINIMAX_REGION=cn|intl
已合成过且文本未变的句子会跳过（改一句只重配那一句）。限流（1002）会自动等待重试。
"""
import json, os, sys, time, urllib.request, wave
from pathlib import Path


def load_env():
    p = Path.cwd()
    for d in [p, *p.parents]:
        f = d / ".env"
        if f.exists():
            for line in f.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            return
    raise SystemExit("找不到 .env（需要 MINIMAX_API_KEY / MINIMAX_GROUP_ID）")


def opt(name, default=None, many=False):
    vals = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == name]
    return vals if many else (vals[0] if vals else default)


def tts(text, voice, model, speed, tones, fmt="wav"):
    host = "https://api.minimaxi.com" if os.environ.get("MINIMAX_REGION", "cn") == "cn" else "https://api.minimax.io"
    body = {"model": model, "text": text, "stream": False,
            "voice_setting": {"voice_id": voice, "speed": speed, "vol": 1, "pitch": 0},
            "audio_setting": {"sample_rate": 44100, "format": fmt, "channel": 1}}
    if tones:
        body["pronunciation_dict"] = {"tone": tones}
    req = urllib.request.Request(f"{host}/v1/t2a_v2?GroupId={os.environ['MINIMAX_GROUP_ID']}", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {os.environ['MINIMAX_API_KEY']}", "Content-Type": "application/json"})
    for _ in range(8):
        d = json.load(urllib.request.urlopen(req, timeout=300))
        if d["base_resp"]["status_code"] != 1002:
            break
        time.sleep(15)
    if d["base_resp"]["status_code"] != 0:
        raise SystemExit(f"MiniMax 错误：{d['base_resp']}")
    return bytes.fromhex(d["data"]["audio"])


def main():
    load_env()
    voice = opt("--voice", "Chinese_deep_voiced_male_nv1")
    model = opt("--model", "speech-2.6-hd")
    speed = float(opt("--speed", "0.95"))
    tones = opt("--dict", many=True)
    if "--sample" in sys.argv:
        Path("配音试听").mkdir(exist_ok=True)
        for v in opt("--voice", many=True) or [voice]:
            Path(f"配音试听/{v.replace(' ', '_')}.mp3").write_bytes(tts(opt("--sample"), v, model, speed, tones, "mp3"))
            print("ok", v)
            time.sleep(2)
        return
    lines = [l.strip() for l in Path(sys.argv[1]).read_text().splitlines() if l.strip()]
    Path("audio").mkdir(exist_ok=True)
    old = {x["text"]: x for x in json.loads(Path("vo.json").read_text())} if Path("vo.json").exists() else {}
    out = []
    for i, text in enumerate(lines):
        dst = Path("audio") / f"vo_{i:02d}.wav"
        if text in old and dst.exists() and old[text]["file"] == str(dst):
            out.append(old[text])
            continue
        dst.write_bytes(tts(text, voice, model, speed, tones))
        with wave.open(str(dst)) as w:
            dur = w.getnframes() / w.getframerate()
        out.append({"text": text, "file": str(dst), "dur": round(dur, 3)})
        print(i, round(dur, 2), text, flush=True)
        Path("vo.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
        time.sleep(2)
    Path("vo.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print("total", round(sum(x["dur"] for x in out), 1), "s")


if __name__ == "__main__":
    main()
