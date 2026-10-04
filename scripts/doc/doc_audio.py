"""Mixkit 实录音效 / 背景音乐（Mixkit Free License：可商用、无需署名；音乐不得登记 Content ID）

  python doc_audio.py sfx                       # 下载默认音效包 -> sfx/<id>.wav（约 1 MB）
  python doc_audio.py sfx 790 788 2908          # 指定编号
  python doc_audio.py list-sfx whoosh impact    # 按分类列出音效（标题 | 编号）
  python doc_audio.py list-music cinematic ambient documentary mysterious
  python doc_audio.py music 188 614 184         # 下载候选配乐 -> music/<id>.mp3，并打分（选「不抢解说」的那首）

下载前先把清单（编号、名称、用途、大小）发给用户确认。
"""
import html, re, subprocess, sys, urllib.request, wave
from pathlib import Path

import numpy as np

UA = {"User-Agent": "Mozilla/5.0"}
# 默认音效包：编号 -> (名称, 典型用途)
DEFAULT_SFX = {
    790: ("Cinematic trailer riser", "开场光缝 / 揭晓前的推高"),
    788: ("Big cinematic impact", "主体亮相、片名落定的重击"),
    498: ("Deep heartbeat impact", "问号、悬念"),
    2350: ("Magic sparkle whoosh", "标签 / 光点飘入"),
    1143: ("Cinematic whoosh deep impact", "器物从景深飞出、卡片冲向镜头"),
    3120: ("Technology transition slide", "引线、雷达、HUD、数据卡"),
    1485: ("Metal hit woosh", "金属字 / 片名最后一个字"),
    1486: ("Cinematic tunnel reverb woosh", "转场、旋转木马"),
    3005: ("Light pop", "小卡片弹出、打字每个字"),
    2908: ("Movie trailer epic impact", "年份大字砸下（如 1986）"),
}


def ff():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def fetch(url, dst):
    dst.write_bytes(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())


def sfx(ids):
    Path("sfx").mkdir(exist_ok=True)
    for i in ids or DEFAULT_SFX:
        mp3, wav = Path(f"sfx/{i}.mp3"), Path(f"sfx/{i}.wav")
        if not wav.exists():
            fetch(f"https://assets.mixkit.co/active_storage/sfx/{i}/{i}-preview.mp3", mp3)
            subprocess.run([ff(), "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav)], check=True)
        print("sfx", i, DEFAULT_SFX.get(int(i), ("", ""))[0])


def listing(kind, tags):
    base = "free-sound-effects" if kind == "sfx" else "free-stock-music/tag"
    for t in tags:
        s = urllib.request.urlopen(urllib.request.Request(f"https://mixkit.co/{base}/{t}/", headers=UA), timeout=60).read().decode("utf8", "ignore")
        urls = re.findall(r'data-audio-player-preview-url-value="([^"]+)"', s)
        tit = re.findall(r'item-grid-card__title">\s*([^<]+?)\s*<', s)
        print("==", t)
        for a, u in list(zip(tit, urls))[:20]:
            print(f"  {html.unescape(a)} | {re.findall(r'/(\d+)', u)[-1]} | {u}")


def music(ids):
    """下载并打分：响度起伏小、人声频段（1–4 kHz）能量少、瞬态少的曲子最不抢解说"""
    Path("music").mkdir(exist_ok=True)
    print(f"{'id':>5} {'时长s':>6} {'响度起伏dB':>9} {'人声频段%':>9} {'瞬态/分':>7} {'低频%':>6}")
    for i in ids:
        mp3, wav = Path(f"music/{i}.mp3"), Path(f"music/{i}_22k.wav")
        if not mp3.exists():
            fetch(f"https://assets.mixkit.co/music/{i}/{i}.mp3", mp3)
        subprocess.run([ff(), "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", "22050", str(wav)], check=True)
        with wave.open(str(wav)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
        dur, seg = len(x) / sr, x[: int(min(len(x) / sr, 180) * sr)]
        hop = sr // 2
        db = 20 * np.log10(np.array([np.sqrt((seg[k:k + hop] ** 2).mean()) + 1e-9 for k in range(0, len(seg) - hop, hop)]))
        F = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        f = np.fft.rfftfreq(len(seg), 1 / sr)
        h2 = int(0.05 * sr)
        e = np.array([(seg[k:k + h2] ** 2).sum() for k in range(0, len(seg) - h2, h2)])
        on = ((e[1:] > e[:-1] * 4) & (e[1:] > np.percentile(e, 60))).sum() / (len(seg) / sr / 60)
        print(f"{i:>5} {dur:6.0f} {np.percentile(db, 90) - np.percentile(db, 10):9.1f} {F[(f > 1000) & (f < 4000)].sum() / F.sum() * 100:9.1f}"
              f" {on:7.0f} {F[f < 250].sum() / F.sum() * 100:6.1f}")
    print("选：时长 ≥ 片长、起伏 < 10 dB、人声频段 < 5%、瞬态少；低频 > 90% 的会发闷。")


if __name__ == "__main__":
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "sfx":
        sfx([int(a) for a in rest])
    elif cmd == "list-sfx":
        listing("sfx", rest)
    elif cmd == "list-music":
        listing("music", rest)
    elif cmd == "music":
        music([int(a) for a in rest])
