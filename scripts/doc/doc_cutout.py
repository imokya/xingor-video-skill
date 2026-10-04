"""文物抠图：img/<name>.jpg -> cut/<name>.png（rembg · isnet-general-use）

  pip install "rembg[cpu]"          # 首次运行会下载模型（约 170 MB）
  python doc_cutout.py gold_mask mask_front tree_full   # 名字不带扩展名
  python doc_cutout.py --sheet                           # 所有抠图铺在深色底上出检查图 cut/_sheet.jpg

抠完一定看检查图：展柜、底座、红布、玻璃反光有时会被一起抠进来（例如象牙连着展台），这类改用照片卡片。
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def cutout(names):
    from rembg import new_session, remove
    sess = new_session("isnet-general-use")
    Path("cut").mkdir(exist_ok=True)
    for n in names:
        im = Image.open(f"img/{n}.jpg").convert("RGB")
        im.thumbnail((1600, 1600))
        remove(im, session=sess).save(f"cut/{n}.png")
        print("cut", n, flush=True)


def sheet():
    tiles = []
    for p in sorted(Path("cut").glob("*.png")):
        im = Image.open(p).convert("RGBA")
        bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
        im = im.crop(bb) if bb else im
        im.thumbnail((300, 380))
        bg = Image.new("RGBA", (320, 420), (20, 40, 42, 255))
        bg.alpha_composite(im, ((320 - im.width) // 2, (400 - im.height) // 2))
        tiles.append((p.stem, bg))
    cols = 6
    out = Image.new("RGB", (cols * 320, max(1, (len(tiles) + cols - 1) // cols) * 440), (0, 0, 0))
    d = ImageDraw.Draw(out)
    for i, (n, t) in enumerate(tiles):
        x, y = (i % cols) * 320, (i // cols) * 440
        out.paste(t.convert("RGB"), (x, y)); d.text((x + 6, y + 422), n, fill=(255, 230, 120))
    out.save("cut/_sheet.jpg", quality=85)
    print("-> cut/_sheet.jpg")


if __name__ == "__main__":
    sheet() if "--sheet" in sys.argv else cutout(sys.argv[1:])
