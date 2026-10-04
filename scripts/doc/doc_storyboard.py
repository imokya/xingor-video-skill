"""分镜确认表：storyboard.json -> 分镜确认_1.png, _2.png …（给用户确认后再配音 / 渲染）

  python doc_storyboard.py storyboard.json [--title 《三星堆》] [--meta "9:16 竖屏 · 约2分50秒"] [--rows 12]

storyboard.json: [["段落", "旁白原句", "素材", "画面说明"], ...]
  素材: "cut:<name>"（抠图，深色底展示） | "<name>"（img/ 里的照片） | null（纯动画）
"""
import json, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SONG = "/System/Library/Fonts/Supplemental/Songti.ttc"


def F(size, idx=1):
    return ImageFont.truetype(SONG, size, index=idx)


def opt(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def thumb(spec, w=160, h=284):
    t = Image.new("RGB", (w, h), (12, 26, 28))
    if not spec:
        ImageDraw.Draw(t).text((w // 2, h // 2), "动画", font=F(34), fill=(217, 178, 106), anchor="mm")
        return t
    if spec.startswith("cut:"):
        c = Image.open(f"cut/{spec[4:]}.png").convert("RGBA")
        c = c.crop(c.getchannel("A").getbbox())
        c.thumbnail((w - 16, h - 40))
        t.paste(c, ((w - c.width) // 2, (h - c.height) // 2), c)
        return t
    im = Image.open(f"img/{spec}.jpg").convert("RGB")
    bg = im.copy()
    bg.thumbnail((w * 4, h * 4))
    bg = bg.resize((w, h)).filter(ImageFilter.GaussianBlur(8))
    t.paste(Image.eval(bg, lambda v: int(v * 0.45)), (0, 0))
    fg = im.copy()
    fg.thumbnail((w - 12, h - 60))
    t.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    return t


def wrap(d, txt, size, maxw):
    f, out, cur = F(size), [], ""
    for ch in txt:
        if d.textlength(cur + ch, font=f) > maxw:
            out.append(cur)
            cur = ch
        else:
            cur += ch
    return out + [cur]


def main():
    sb = json.loads(Path(sys.argv[1]).read_text())
    title, meta, rows = opt("--title", "分镜"), opt("--meta", "9:16 竖屏"), int(opt("--rows", 12))
    W, RH = 1500, 300
    pages = (len(sb) + rows - 1) // rows
    for p in range(pages):
        part = sb[p * rows:(p + 1) * rows]
        img = Image.new("RGB", (W, 90 + RH * len(part)), (246, 240, 228))
        d = ImageDraw.Draw(img)
        d.text((40, 28), f"{title} 分镜确认表（{p + 1}/{pages}） · {meta}", font=F(32), fill=(60, 30, 20))
        for i, (sec, line, spec, note) in enumerate(part):
            y, n = 90 + i * RH, p * rows + i + 1
            d.rectangle((20, y, W - 20, y + RH - 12), fill=(255, 252, 245), outline=(220, 205, 180))
            d.text((44, y + 20), f"{n:02d}", font=F(44), fill=(184, 52, 40))
            d.text((44, y + 76), sec, font=F(26), fill=(120, 90, 60))
            img.paste(thumb(spec), (150, y + 4))
            ty = y + 22
            for ln in wrap(d, line, 34, 1110):
                d.text((340, ty), ln, font=F(34), fill=(30, 20, 14))
                ty += 48
            ty += 8
            for ln in wrap(d, "画面：" + note, 26, 1110):
                d.text((340, ty), ln, font=F(26), fill=(110, 80, 55))
                ty += 38
            if spec:
                d.text((340, y + RH - 50), ("抠图：" + spec[4:]) if spec.startswith("cut:") else f"照片卡：{spec}", font=F(20), fill=(160, 140, 120))
        img.save(f"分镜确认_{p + 1}.png")
        print(f"-> 分镜确认_{p + 1}.png")


if __name__ == "__main__":
    main()
