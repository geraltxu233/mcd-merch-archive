"""
补官方图：把人工补录条目的官方产品图写入藏品库（image_url 存来源，image_local 存本地副本）。

官网图片有防盗链（无 Referer 返回 403），所以一律下载成本地副本，
档案页引用本地路径即可稳定显示。来源 URL 保留在 image_url 里，便于溯源。

用法：python 补官方图.py
"""

import sys
import json
import os
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "data", "藏品库.json")
IMG_DIR = os.path.join(ROOT, "视图", "图片")
HDR = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://www.mcdonalds.com.cn/",
}
BASE = "https://officiaweb-afd.mcdonalds.com.cn/public/upload/photo_db/"

# id -> (官方页, 官方产品图URL)
IMAGES = {
    "2025-09-30-toy-01": (
        "https://www.mcdonalds.com.cn/news/20250930-Wukong",
        BASE + "2025/09/30/202509301509356225.png",
    ),
    "2025-07-09-toy-01": (
        "https://www.mcdonalds.com.cn/news/20250709-BFF",
        BASE + "2025/07/10/202507101033279473.png",
    ),
    "2025-07-09-misc-01": (
        "https://www.mcdonalds.com.cn/news/20250709-BFF",
        BASE + "2025/07/10/202507101033288755.png",
    ),
    "2024-05-22-walkie-01": (
        "https://www.mcdonalds.com.cn/news/20240522-Childrens-day-2",
        BASE + "2024/05/22/202405221319151229.png",
    ),
    "2025-06-14-toy-01": (
        "https://www.mcdonalds.com.cn/news/20250611-Ultraman",
        BASE + "2025/06/11/202506111624459258.jpg",
    ),
    "2023-06-01-console-01": (
        "https://www.mcdonalds.com.cn/news/20230531-Childrens-Day",
        BASE + "2023/05/31/202305311630482411/202305311630482411.gif",
    ),
    "2025-04-03-toy-01": (
        "https://www.mcdonalds.com.cn/news/20250415-McD-Minecraft",
        BASE + "2025/04/17/202504171458314831.png",
    ),
    "2025-10-24-minecraft-01": (
        "https://www.mcdonalds.com.cn/news/20251022-programmers--day",
        BASE + "2025/10/22/202510221742348306.jpg",
    ),
}


def ext_of(url):
    path = url.split("?")[0]
    return os.path.splitext(path)[1] or ".png"


def main():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    os.makedirs(IMG_DIR, exist_ok=True)
    by_id = {it["id"]: it for it in db["藏品"]}

    for iid, (page, url) in IMAGES.items():
        it = by_id.get(iid)
        if not it:
            print(f"[跳过] 库中无此 id：{iid}")
            continue
        if it.get("image_local") and os.path.exists(os.path.join(ROOT, "视图", it["image_local"])):
            print(f"[跳过] {it['name']}（本地图已存在）")
            continue
        fn = f"{iid}{ext_of(url)}"
        local = os.path.join(IMG_DIR, fn)
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=40).read()
        except Exception as e:
            print(f"[失败] {iid} -> {e}")
            continue
        with open(local, "wb") as f:
            f.write(data)
        it["image_url"] = url
        it["image_local"] = f"图片/{fn}"
        note = it.get("source_raw", "")
        if page not in note:
            it["source_raw"] = note + f" 图片：官方页 {page}"
        print(f"[完成] {it['name']}  {len(data)//1024}KB  -> 视图/图片/{fn}")

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    print("藏品库已更新（image_url / image_local）。")


if __name__ == "__main__":
    main()
