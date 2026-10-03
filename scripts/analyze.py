"""Analyze a talking-head video. Run from the work dir with its venv:

    .venv/bin/python <skill>/scripts/analyze.py <input_video> [--model medium] [--lang zh]

Produces in the current dir:
  source.mp4       normalized 1920x1080, integer fps, 48k audio (letterboxed if not 16:9)
  audio16k.wav     for ASR
  transcript.json  whisper segments with word timestamps
  captions.txt     one line per segment -> EDIT THIS (fix terms, add '|' chunk breaks)
  silences.json    pauses >= 0.3s (render trims them to ~0.18s)
  matte.mkv        per-frame person alpha (RobustVideoMatting)
  meta.json        fps, frame count, person anchor (head x, head top, face y)
  sheet.jpg        contact sheet of the source
"""
import sys, os, json, subprocess, argparse
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('video')
ap.add_argument('--model', default='medium')
ap.add_argument('--lang', default='zh')
ap.add_argument('--skip', default='', help='comma list of steps to skip: prep,asr,matte')
args = ap.parse_args()
skip = set(args.skip.split(','))
FF = './ffmpeg'
W, H = 1920, 1080


def probe_fps(path):
    out = subprocess.run([FF, '-hide_banner', '-i', path], capture_output=True, text=True).stderr
    import re
    m = re.search(r'(\d+(?:\.\d+)?) fps', out)
    return float(m.group(1)) if m else 25.0


# ---------------- prep
if 'prep' not in skip:
    fps = probe_fps(args.video)
    fps = 30 if fps > 27 else 25
    vf = f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={fps},setsar=1'
    subprocess.run([FF, '-v', 'error', '-y', '-i', args.video, '-vf', vf, '-c:v', 'libx264', '-crf', '14', '-preset', 'fast',
                    '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2', 'source.mp4'], check=True)
    subprocess.run([FF, '-v', 'error', '-y', '-i', 'source.mp4', '-vn', '-ac', '1', '-ar', '16000', 'audio16k.wav'], check=True)
    subprocess.run([FF, '-v', 'error', '-y', '-i', 'source.mp4', '-vf', 'fps=1/4,scale=384:-1,tile=5x5', '-frames:v', '1', 'sheet.jpg'])
    print('prep done, fps', fps)
else:
    fps = int(round(probe_fps('source.mp4')))

# ---------------- ASR
if 'asr' not in skip:
    from faster_whisper import WhisperModel
    m = WhisperModel(args.model, device='cpu', compute_type='int8')
    prompt = '以下是普通话的句子，使用简体中文。' if args.lang == 'zh' else None
    segs, _ = m.transcribe('audio16k.wav', language=args.lang, word_timestamps=True, initial_prompt=prompt)
    out = []
    for s in segs:
        out.append({'start': s.start, 'end': s.end, 'text': s.text,
                    'words': [{'s': w.start, 'e': w.end, 'w': w.word} for w in s.words]})
        print(f'{s.start:6.2f}-{s.end:6.2f} {s.text}', flush=True)
    json.dump(out, open('transcript.json', 'w'), ensure_ascii=False, indent=1)
    with open('captions.txt', 'w') as f:
        for s in out:
            f.write(s['text'].strip().rstrip('。.') + '\n')
    # silences
    import wave
    w = wave.open('audio16k.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    rms = np.sqrt(np.convolve(a ** 2, np.ones(400) / 400, 'same')[::160])
    db = 20 * np.log10(rms + 1e-9); thr = np.percentile(db, 50) - 25
    sil = db < thr; res = []; i = 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]: j += 1
            if (j - i) * .01 >= .3: res.append((i * .01, j * .01))
            i = j
        else: i += 1
    json.dump(res, open('silences.json', 'w'))
    print('silences', res)

# ---------------- matte
if 'matte' not in skip:
    import torch
    sys.path.insert(0, 'models/RobustVideoMatting-master')
    from model import MattingNetwork
    dev = 'mps' if torch.backends.mps.is_available() else ('cuda' if torch.cuda.is_available() else 'cpu')
    net = MattingNetwork('mobilenetv3').eval().to(dev)
    net.load_state_dict(torch.load('models/rvm_mobilenetv3.pth', map_location='cpu'))
    dec = subprocess.Popen([FF, '-v', 'error', '-i', 'source.mp4', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'gray', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                            '-c:v', 'ffv1', 'matte.mkv'], stdin=subprocess.PIPE)
    rec = [None] * 4; n = 0; acc = np.zeros((H, W), np.float64)
    with torch.no_grad():
        while True:
            b = dec.stdout.read(W * H * 3)
            if len(b) < W * H * 3: break
            x = torch.from_numpy(np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()).to(dev).permute(2, 0, 1).float().div(255)[None]
            fgr, pha, *rec = net(x, *rec, downsample_ratio=0.4)
            al = (pha[0, 0].clamp(0, 1) * 255).byte().cpu().numpy()
            enc.stdin.write(al.tobytes()); n += 1
            if n % 10 == 0: acc += al / 255
            if n % 250 == 0: print('matte', n, flush=True)
    enc.stdin.close(); enc.wait()
    # person anchor from average matte
    avg = acc / max(1, n // 10)
    rows = np.where(avg.max(1) > .5)[0]
    head_top = int(rows[0]) if len(rows) else 80
    band = avg[head_top:head_top + 250]
    cols = band.sum(0)
    head_x = int((cols * np.arange(W)).sum() / max(cols.sum(), 1))
    face_y = int(head_top + 0.33 * (H - head_top))
    bottom_rows = avg[H - 40:H].mean(0) > .5
    bx = np.where(bottom_rows)[0]
    meta = {'fps': fps, 'frames': n, 'person': {'head_x': head_x, 'head_top': head_top, 'face_y': face_y,
                                                 'body_left': int(bx[0]) if len(bx) else 500, 'body_right': int(bx[-1]) if len(bx) else 1400}}
    json.dump(meta, open('meta.json', 'w'), indent=1)
    print('meta', meta)
