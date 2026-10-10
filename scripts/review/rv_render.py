"""flat-review 渲染器
  python rv_render.py scenes.py 成片.mp4            # 3:4（1080×1440，小红书）
  python rv_render.py scenes.py 成片.mp4 --67       # 6:7（1080×1260，视频号）：上下各裁 90，HUD 内收
  python rv_render.py scenes.py test/s still 12.3 h2.0 ...   # 静帧（正片秒数；h 开头 = 钩子里的秒数）
场景文件需要定义：SEGS（段落表）、DUR（=TL.dur）；可选 HOOK（rv_core.Hook）、sfx(fx)、extra_audio(vo, sr)、
OUTRO（片尾 mp4）、BGM（音乐文件）、BGM_BED（默认 -14）、VO_TRACK（默认 timeline 同目录 vo_track.wav）
"""
import importlib.util, os, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rv_core as R

args = sys.argv[1:]
crop = 0
if '--67' in args: args.remove('--67'); crop = 90
R.set_crop(crop)
spec = importlib.util.spec_from_file_location('scenes', args[0]); S = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(os.path.abspath(args[0]))); spec.loader.exec_module(S)
out = args[1]
HOOK = getattr(S, 'HOOK', None); HD = HOOK.dur if HOOK else 0.0
DUR = R.TL.dur

def frame_at(t):
    return HOOK.render(t) if (HOOK and t < HD) else R.render_segments(S.SEGS, t - HD, DUR)

def cropped(im):
    return im.crop((0, crop, R.W, R.H - crop)) if crop else im

if len(args) > 2 and args[2] == 'still':
    for ts in args[3:]:
        im = HOOK.render(float(ts[1:])) if ts.startswith('h') else R.render_segments(S.SEGS, float(ts), DUR)
        cropped(im).save(f'{out}_{ts}.png')
    sys.exit()

# ---------- 声音 ----------
sr = R.SR
vt = getattr(S, 'VO_TRACK', os.path.join(os.path.dirname(R.TL_PATH) if hasattr(R, 'TL_PATH') else '.', 'vo_track.wav'))
vo = R.pcm(vt, sr)
vo = R.loud(vo)
if hasattr(S, 'extra_audio'): vo = S.extra_audio(vo, sr)
fx = R.Sfx(DUR, sr)
for seg in S.SEGS[1:]:
    if seg[6] != 'cut': fx.whoosh(seg[0] - .1)
if hasattr(S, 'sfx'): S.sfx(fx)
s = fx.out[:len(vo)]
main = np.clip(vo + np.pad(s, (0, len(vo) - len(s))) * .5, -1, 1)
audio = np.concatenate([HOOK.audio(sr), main]) if HOOK else main
bgm = getattr(S, 'BGM', None)
if bgm: audio = R.mix_bgm(audio, bgm, outro=0, bed=getattr(S, 'BGM_BED', -14.0), hook=HD, sr=sr)
aud = out[:-4] + '_audio.wav'
with wave.open(aud, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())

# ---------- 画面 ----------
CH = R.H - 2 * crop
outro = getattr(S, 'OUTRO', None)
body = out[:-4] + '_body.mp4' if outro else out
p = subprocess.Popen([R.FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{R.W}x{CH}', '-r', str(R.FPS),
                      '-i', '-', '-i', aud, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium',
                      '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', body], stdin=subprocess.PIPE)
n = int((HD + DUR) * R.FPS)
for i in range(n):
    p.stdin.write(cropped(frame_at(i / R.FPS)).tobytes())
    if i % 300 == 0: print(i, '/', n, flush=True)
p.stdin.close(); p.wait(); os.remove(aud)
if outro:
    cf = f'crop=1080:{CH}:0:{crop},' if crop else ''
    subprocess.run([R.FF, '-v', 'error', '-y', '-i', body, '-i', outro, '-filter_complex',
                    f'[1:v]scale=1080:1440,{cf}fps={R.FPS},setsar=1,format=yuv420p[fv];[1:a]aresample={sr},pan=mono|c0=0.5*c0+0.5*c1[fa];'
                    '[0:v][0:a][fv][fa]concat=n=2:v=1:a=1[v][a]', '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-crf', '17',
                    '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    os.remove(body)
print('done', out, round(HD + DUR, 2), 's')
