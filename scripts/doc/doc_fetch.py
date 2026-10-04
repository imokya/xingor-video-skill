"""Wikimedia Commons 素材：搜索 / 下载 / 出处

  python doc_fetch.py search "Sanxingdui bronze mask" "三星堆 神树"     # 列出 尺寸 · 授权 · 文件名
  python doc_fetch.py category "Category:Sanxingdui Museum"            # 列出分类下的文件
  python doc_fetch.py get manifest.json                                # 按清单下载到 img/，记录 img/credits.json
  python doc_fetch.py credits [--extra "配音：…" ...]                    # 生成 素材授权.txt

manifest.json:  {"mask_front": ["File title.jpg", 3840], "scroll": ["卷.jpg", "orig"], ...}
宽度只用 Wikimedia 标准缩略图尺寸（1280 / 1920 / 3840），否则会被限流（HTTP 429）；"orig" 取原图（容易 429，尽量少用）。
"""
import io, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "DocumentaryShort/1.0 (personal educational video)"}
IMG = Path("img")


def api(**p):
    p.update(format="json")
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(p)
    for i in range(6):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
        except Exception:
            time.sleep(5 * (i + 1))
    raise SystemExit("Commons API 请求失败")


def strip(h):
    return re.sub(r"<[^>]+>", "", h or "").strip()


def show(pages):
    for p in pages:
        ii = p.get("imageinfo", [{}])[0]
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "?")
        print(f'  {ii.get("width")}x{ii.get("height")}\t{lic}\t{p["title"]}')


def search(qs):
    for q in qs:
        print("==", q)
        d = api(action="query", generator="search", gsrsearch=q, gsrnamespace=6, gsrlimit=20, prop="imageinfo",
                iiprop="size|extmetadata", iiextmetadatafilter="LicenseShortName")
        show(d.get("query", {}).get("pages", {}).values())
        time.sleep(2)


def category(cats):
    for c in cats:
        print("==", c)
        d = api(action="query", generator="categorymembers", gcmtitle=c, gcmtype="file", gcmlimit=200, prop="imageinfo",
                iiprop="size|extmetadata", iiextmetadatafilter="LicenseShortName")
        pages = sorted(d.get("query", {}).get("pages", {}).values(), key=lambda p: -p["imageinfo"][0]["width"] * p["imageinfo"][0]["height"])
        show(pages)
        sub = api(action="query", list="categorymembers", cmtitle=c, cmtype="subcat", cmlimit=200)
        for s in sub["query"]["categorymembers"]:
            print("  [子分类]", s["title"])
        time.sleep(2)


def get(manifest):
    IMG.mkdir(exist_ok=True)
    cred_p = IMG / "credits.json"
    credits = json.loads(cred_p.read_text()) if cred_p.exists() else {}
    for name, (title, mode) in json.loads(Path(manifest).read_text()).items():
        dst = IMG / f"{name}.jpg"
        if dst.exists() and name in credits:
            continue
        w = 1280 if mode == "orig" else int(mode)
        d = api(action="query", titles="File:" + title, prop="imageinfo", iiprop="url|size|extmetadata", iiurlwidth=w)
        ii = next(iter(d["query"]["pages"].values()))["imageinfo"][0]
        m = ii.get("extmetadata", {})
        credits[name] = {"file": title, "page": ii["descriptionurl"], "artist": strip(m.get("Artist", {}).get("value")),
                         "license": m.get("LicenseShortName", {}).get("value", ""), "size": [ii["width"], ii["height"]]}
        url = ii["url"] if mode == "orig" or ii["width"] <= w else ii["thumburl"]
        err = None
        for i in range(5):
            try:
                data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()
                from PIL import Image
                im = Image.open(io.BytesIO(data))
                (im.convert("RGB").save(dst, quality=92) if im.format != "JPEG" else dst.write_bytes(data))
                break
            except Exception as e:
                err = e; time.sleep(10 * (i + 1))
        print("OK " if dst.exists() else f"FAILED {err} ", name, ii["width"], "x", ii["height"], credits[name]["license"], flush=True)
        cred_p.write_text(json.dumps(credits, ensure_ascii=False, indent=1))
        time.sleep(2)


def write_credits(extra):
    c = json.loads((IMG / "credits.json").read_text())
    L = ["图片来源（Wikimedia Commons）", ""]
    for k, v in c.items():
        L.append(f"· {v['file']} —— {(v['artist'] or '佚名')[:80]} —— {v['license']}\n  {v['page']}")
    L += [""] + extra
    Path("素材授权.txt").write_text("\n".join(L))
    print("-> 素材授权.txt")


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "search":
        search(args)
    elif cmd == "category":
        category(args)
    elif cmd == "get":
        get(args[0])
    elif cmd == "credits":
        write_credits([args[i + 1] for i, a in enumerate(args) if a == "--extra"])
