"""
把某官网新闻页的图片拼成带编号的索引图，便于一次性选定产品主图。

背景：官网图片的位置与正文不对应，代码难以判断哪张是产品图；把页面前 N 张图
拼成一张索引图后人工挑选，是唯一可靠的办法。

用法：python 图片索引图.py <新闻页URL> <输出图片路径> [最多张数，默认12]
依赖：Pillow（官网图有防盗链，必须带 Referer）
"""

import sys
import re
import io
import os
import urllib.request
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.mcdonalds.com.cn/",
}
IMG_RE = re.compile(r'<img[^>]*?src="(https://officiaweb-afd\.mcdonalds\.com\.cn/public/upload/photo_db/[^"]+)"')


def get(u):
    return urllib.request.urlopen(urllib.request.Request(u, headers=HDR), timeout=30).read()


def main():
    if len(sys.argv) < 3:
        print("用法：python 图片索引图.py <新闻页URL> <输出图片路径> [最多张数]")
        return
    page, out = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 12

    html = get(page).decode("utf-8", "ignore")
    urls = list(dict.fromkeys(IMG_RE.findall(html)))[:limit]

    cols, cell = 4, 320
    rows = (len(urls) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 40)), (20, 16, 14))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
    except Exception:
        font = ImageFont.load_default()

    for i, u in enumerate(urls):
        try:
            im = Image.open(io.BytesIO(get(u))).convert("RGB")
        except Exception as e:
            print(f"[跳过] #{i+1} {u.split('/')[-1]} -> {e}")
            continue
        im.thumbnail((cell - 16, cell - 16))
        r, c = divmod(i, cols)
        base_y = r * (cell + 40)
        sheet.paste(im, (c * cell + (cell - im.width) // 2, base_y + 36 + max(0, (cell - 36 - im.height) // 2)))
        draw.text((c * cell + 12, base_y + 4), f"#{i+1}", fill=(255, 199, 44), font=font)
        print(f"#{i+1}  {u.split('/')[-1]}  ({im.width}x{im.height})")

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    sheet.save(out)
    print("索引图：", out)


if __name__ == "__main__":
    main()
