"""配音 + 配乐混音：旁白处自动压低配乐，响度标准化到 −14 LUFS，再封装进视频
    python mix.py <video.mp4> <out.mp4> [bgm.wav] [--vo vo/full] [--times vo/times.json]
vo/full/vo.json 来自 review/rv_tts.py；times.json 是每句的开始秒数（与画面时间轴对齐）。
"""
import argparse, json, subprocess, wave
import numpy as np

SR = 48000
def read(p):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-f', 's16le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.int16).reshape(-1, 2).astype(np.float32) / 32768

ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('out'); ap.add_argument('bgm', nargs='?', default='bgm.wav')
ap.add_argument('--vo', default='vo/full'); ap.add_argument('--times', default='vo/times.json'); a = ap.parse_args()
bgm = read(a.bgm); N = len(bgm); vo = np.zeros_like(bgm); duck = np.zeros(N)
for t, it in zip(json.load(open(a.times)), json.load(open(a.vo + '/vo.json'))):
    x = read(a.vo + '/' + it['file']); i = int(t * SR); j = min(N, i + len(x))
    vo[i:j] += x[:j - i]; duck[max(0, i - int(0.25 * SR)):min(N, j + int(0.4 * SR))] = 1   # 提前 0.25 s 压、结束后 0.4 s 回
k = int(0.3 * SR); duck = np.convolve(duck, np.ones(k) / k, 'same')
mix = bgm * (1 - 0.55 * duck)[:, None] + vo * 1.05
mix /= max(1, np.abs(mix).max() / 0.95)
with wave.open('mix.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-i', 'mix.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11',
                '-c:a', 'aac', '-ar', '48000', '-b:a', '256k', '-shortest', a.out], check=True)
print('ok', a.out)
