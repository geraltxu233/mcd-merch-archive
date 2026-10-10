"""
优化藏品图：把 视图/图片/ 下的图片等比缩放到最大宽度 900px 并重编码，减小体积。
（GIF 保留原样，避免破坏动图。）同步更新藏品库的 image_local 路径。

用法：python 优化藏品图.py
依赖：Pillow
"""

import sys
import json
import os
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "藏品库.json")
IMG_DIR = os.path.join(ROOT, "视图", "图片")
MAX_W = 900
QUALITY = 85


def main():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    by_id = {it["id"]: it for it in db["藏品"]}

    total_before = total_after = 0
    for fn in sorted(os.listdir(IMG_DIR)):
        path = os.path.join(IMG_DIR, fn)
        size_before = os.path.getsize(path)
        total_before += size_before
        stem, ext = os.path.splitext(fn)
        ext = ext.lower()

        if ext == ".gif":
            total_after += size_before
            print(f"[跳过] {fn}（动图，保持原样 {size_before//1024}KB）")
            continue

        im = Image.open(path)
        if im.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", im.size, (255, 255, 255))
            im = im.convert("RGBA")
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")

        if im.width > MAX_W:
            h = round(im.height * MAX_W / im.width)
            im = im.resize((MAX_W, h), Image.LANCZOS)

        new_name = stem + ".jpg"
        new_path = os.path.join(IMG_DIR, new_name)
        im.save(new_path, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        if new_path != path:
            os.remove(path)

        size_after = os.path.getsize(new_path)
        total_after += size_after
        if stem in by_id:
            by_id[stem]["image_local"] = f"图片/{new_name}"
        print(f"[优化] {fn}  {size_before//1024}KB -> {size_after//1024}KB  ({im.width}x{im.height})")

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"\n合计：{total_before/1024/1024:.2f}MB -> {total_after/1024/1024:.2f}MB")
    print("藏品库 image_local 已同步。")


if __name__ == "__main__":
    main()
