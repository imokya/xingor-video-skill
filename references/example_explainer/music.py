"""《AI 其实不知道自己下一个字要说什么》配乐：112 BPM 纯合成电子乐（无采样），section() 按画面分段，
    重音 / whoosh / tick 卡在画面节拍上。python music.py bgm.wav
"""
import sys, wave
import numpy as np
from scipy.signal import butter, lfilter, fftconvolve

SR = 48000
DUR = 165.6
N = int(DUR * SR)
rng = np.random.RandomState(3)
BPM = 112; B = 60 / BPM
NOTE = lambda m: 440.0 * 2 ** ((m - 69) / 12)

def lp(x, fc, o=2): b, a = butter(o, min(fc / (SR / 2), 0.99)); return lfilter(b, a, x)
def hp(x, fc, o=2): b, a = butter(o, min(fc / (SR / 2), 0.99), 'high'); return lfilter(b, a, x)
def bp(x, f1, f2): b, a = butter(2, [f1 / (SR / 2), f2 / (SR / 2)], 'band'); return lfilter(b, a, x)
def place(buf, x, t0, g=1.0):
    i = int(t0 * SR); j = min(N, i + len(x))
    if 0 <= i < N: buf[i:j] += x[:j - i] * g
def env(n, a, r):
    e = np.ones(n); ai, ri = int(a * SR), int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e
tt_ = lambda d: np.arange(int(d * SR)) / SR

# ---------- 音色 ----------
def kick():  t = tt_(0.45); return np.sin(2 * np.pi * np.cumsum(45 + 110 * np.exp(-t * 28)) / SR) * np.exp(-t * 7)
def clap():  t = tt_(0.25); return bp(rng.randn(len(t)), 1100, 4200) * np.exp(-t * 18)
def hat(o=False): t = tt_(0.25 if o else 0.06); return hp(rng.randn(len(t)), 7000) * np.exp(-t * (10 if o else 70))
def pluck(f, d=0.35): t = tt_(d); return lp(2 * ((t * f) % 1) - 1, 2600) * np.exp(-t * 11)
def bell(f): t = tt_(2.0); return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-t * 6)) * np.exp(-t * 2.4)
def boom(): t = tt_(2.6); return np.sin(2 * np.pi * np.cumsum(36 + 50 * np.exp(-t * 5)) / SR) * np.exp(-t * 1.6)
def crash(): t = tt_(2.4); return hp(rng.randn(len(t)), 4000) * np.exp(-t * 2.2)
def riser(d): t = tt_(d); x = rng.randn(len(t)); return lp(x, 4000) * (t / d) ** 2.2
def snare(): t = tt_(0.18); return (bp(rng.randn(len(t)), 900, 5000) + 0.4 * np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 20)

# 和弦（低音, 上声部）：Bm  G  D  A  —— 史诗感的 i-VI-III-VII
CH = [(35, [62, 66, 69, 73]), (31, [59, 62, 67, 71]), (38, [62, 66, 69, 74]), (33, [61, 64, 69, 73])]

drums = np.zeros(N); bass = np.zeros(N); pad = np.zeros(N); arp = np.zeros(N); fx = np.zeros(N); duck = np.ones(N)

def section(t0, t1, kick_on=True, clap_on=False, hats=0, bass_on=False, arp_rate=0, vol=1.0, pad_lp=1800):
    """从 t0 起按节拍网格铺一段（每段重新对齐节拍，保证 drop 卡在 t0）"""
    nb = int((t1 - t0) / B)
    for k in range(nb):
        t = t0 + k * B; bar = k // 4; ch = CH[bar % 4]
        if kick_on: place(drums, kick(), t, 0.9 * vol); i = int(t * SR); duck[i:i + int(0.22 * SR)] = np.minimum(duck[i:i + int(0.22 * SR)], np.linspace(0.35, 1, int(0.22 * SR)))
        if clap_on and k % 2 == 1: place(drums, clap(), t, 0.35 * vol)
        if hats: place(drums, hat(), t + B / 2, 0.16 * vol)
        if hats > 1: place(drums, hat(), t + B / 4, 0.07 * vol); place(drums, hat(), t + 3 * B / 4, 0.07 * vol)
        if bass_on:
            for h in (0, 0.5): place(bass, pluck(NOTE(ch[0] + 12), 0.3), t + h * B, 0.32 * vol)
        if arp_rate:
            for s in range(arp_rate):
                n = ch[1][(k * arp_rate + s) % 4] + (12 if (k + s) % 3 == 0 else 0)
                place(arp, pluck(NOTE(n + 12), 0.25), t + s * B / arp_rate, 0.07 * vol)
        if k % 4 == 0:   # 每小节一个长音铺底
            d = 4 * B + 1.2; t_ = tt_(d); x = np.zeros(len(t_))
            for m in ch[1]:
                for det in (-0.07, 0.06): x += 2 * ((t_ * NOTE(m + det)) % 1) - 1
            place(pad, lp(x / 8, pad_lp) * env(len(t_), 0.4, 1.0), t, 0.5 * vol)
            place(bass, np.sin(2 * np.pi * NOTE(ch[0]) * t_) * env(len(t_), 0.05, 0.8), t, 0.28 * vol)

# ---------- 段落（AI 接龙片 3:4，153.5 s）----------
section(0.0, 8.0, kick_on=False, hats=1, vol=0.5, pad_lp=900)              # 钩子
section(8.0, 21.0, hats=1, bass_on=True, arp_rate=2, vol=0.72)             # 文字接龙
section(21.0, 38.6, kick_on=False, vol=0.55, pad_lp=1200)                  # 香农档案：留白
section(38.6, 51.0, clap_on=True, hats=1, bass_on=True, arp_rate=4, vol=0.78)   # 学习
section(51.0, 55.4, hats=1, bass_on=True, vol=0.65)                        # 参数：蓄力
section(55.4, 65.0, clap_on=True, hats=2, bass_on=True, arp_rate=4, vol=0.85)   # 1750 亿 drop
section(65.0, 79.2, kick_on=False, vol=0.58, pad_lp=1300)                  # 星系：留白
section(79.2, 82.0, clap_on=True, hats=1, bass_on=True, vol=0.8)           # 平行箭头揭晓
section(82.0, 108.0, hats=1, bass_on=True, arp_rate=2, vol=0.7)            # 注意力
section(108.0, 124.0, clap_on=True, hats=1, bass_on=True, arp_rate=2, vol=0.75) # 温度
section(124.0, 135.4, hats=1, bass_on=True, vol=0.58, pad_lp=800)          # 胡说：压低
section(135.4, 149.8, hats=1, bass_on=True, arp_rate=2, vol=0.7)           # 三招
section(149.8, 164.6, kick_on=False, vol=0.6, pad_lp=1400)                 # 结尾
place(fx, riser(2.2), 5.8, 0.2); place(fx, riser(2.6), 52.8, 0.22); place(fx, riser(2.4), 76.8, 0.22)
for h in [8.0, 23.0, 55.4, 79.2, 96.6, 102.8, 130.3, 152.6]: place(fx, boom(), h, 0.85); place(fx, crash(), h, 0.16)
for t0, t1 in [(21.4, 38.2), (65.3, 78.8), (150.2, 160.2)]:
    t = t0; k = 0
    while t < t1: place(arp, bell(NOTE(CH[int((t - t0) / (4 * B)) % 4][1][k % 4] + 12)), t, 0.14); t += 0.53; k += 1
t_ = tt_(4.5); x = sum(2 * ((t_ * NOTE(m)) % 1) - 1 for m in [50, 57, 62, 66, 69])
place(pad, lp(x / 6, 1600) * env(len(t_), 0.8, 3.0), 156.6, 0.6)
# ---------- 音效（新时间轴）----------
def whoosh(d=1.3):
    t = tt_(d); x = rng.randn(len(t)); return lp(x, 2500) * np.sin(np.pi * t / d) ** 2
def glitchfx(d=0.6):
    n = int(d * SR); x = np.sign(np.sin(2 * np.pi * np.cumsum(rng.choice([180, 360, 720, 1440], n) / SR))) * 0.5
    return x * (rng.rand(n) > 0.35) * np.exp(-np.arange(n) / SR * 3)
def tick(f=1800): t = tt_(0.12); return np.sin(2 * np.pi * f * t) * np.exp(-t * 40)
def drop(d=1.0): t = tt_(d); return np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 3) + 80) / SR) * np.exp(-t * 2.5)
for w in [0.2, 7.6, 20.8, 38.4, 50.6, 64.8, 81.6, 107.8, 123.6, 135.0, 149.4]: place(fx, whoosh(), w - 0.2, 0.3)
place(fx, glitchfx(), 3.3, 0.16)
for k in [0.6, 1.02, 1.44, 1.86, 2.28, 14.2, 16.2, 17.6, 26.7, 112.0, 116.0, 138.4, 141.6, 144.8]: place(fx, tick(), k, 0.3); place(fx, tick(2400), k + 0.07, 0.22)
place(fx, drop(), 112.0, 0.2); place(fx, riser(1.4), 3.4, 0.25)
import os
mix = fx * 0.9 if os.environ.get('SFX_ONLY') else drums + (bass + pad * 0.6) * duck + arp + fx   # SFX_ONLY=1：只出音效（给平台曲库配乐用）
ir = rng.randn(int(2.0 * SR)) * np.exp(-np.arange(int(2.0 * SR)) / SR * 3)
L = mix + fftconvolve(arp + pad * 0.3, ir)[:N] * 0.03; R = mix + fftconvolve(arp + pad * 0.3, np.roll(ir, 777))[:N] * 0.03
st = np.stack([L, R], 1) * env(N, 0.3, 3.0)[:, None]
st /= np.abs(st).max() / (0.6 if os.environ.get('SFX_ONLY') else 0.9)
with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('ok', DUR)
