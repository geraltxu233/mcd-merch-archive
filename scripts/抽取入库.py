"""
从采集快照抽取结构化藏品条目，并合并入库（按 ext_key 去重）。

半自动设计：脚本负责正则抽取，抽取结果落 data/抽取候选.json 供人工确认；
加 --apply 才真正写入藏品库；已存在（ext_key 相同）的条目不覆盖人工校对过的内容。

用法：
    python 抽取入库.py            # 只抽取，写候选文件，不改库
    python 抽取入库.py --apply     # 抽取并合并入库
"""

import sys
import re
import json
import os
import glob
import argparse
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP_DIR = os.path.join(ROOT, "data", "采集快照")
DB_PATH = os.path.join(ROOT, "data", "藏品库.json")
CAND_PATH = os.path.join(ROOT, "data", "抽取候选.json")

CAT_KEYWORDS = [
    ("帽子", ["棒球帽", "帽子", "渔夫帽"]),
    ("徽章", ["徽章", "吧唧", "胸针"]),
    ("丝巾", ["丝巾", "围巾"]),
    ("鞋袜", ["球鞋", "运动鞋", "鞋"]),
    ("包袋", ["背包", "挎包", "包袋", "手提包"]),
    ("游戏机", ["游戏机", "掌机"]),
    ("玩具", ["玩具", "玩偶", "毛绒"]),
    ("家居", ["杯子", "马克杯", "抱枕", "摆件"]),
]

SLUG = {
    "帽子": "hat", "徽章": "badge", "丝巾": "scarf", "鞋袜": "shoes",
    "包袋": "bag", "游戏机": "console", "玩具": "toy", "家居": "home", "其他": "misc",
}


def guess_category(text):
    for cat, kws in CAT_KEYWORDS:
        if any(k in text for k in kws):
            return cat
    return "其他"


def parse_calendar(entry):
    """活动日历：从自由文案抽取。"""
    text = entry.get("原文", "").replace("\\n", "\n")
    date = entry.get("活动日期", "")
    title = (entry.get("活动标题") or "").strip()
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # 类目判定：优先看「主产品行」（含麦当劳的行，否则首行），避免被文案里的对比词误伤
    priority = next((ln for ln in lines if "麦当劳" in ln), lines[0] if lines else "")
    category = guess_category(priority)
    if category == "其他":
        category = guess_category(text)

    # 产品名：优先取含「麦当劳」的行，否则取标题
    name = None
    for ln in lines:
        if "麦当劳" in ln:
            name = ln
            break
    if not name:
        prod = next((ln for ln in lines if guess_category(ln) == category), lines[0] if lines else title)
        name = f"{title} {prod}".strip() if title and "X" in title else prod

    # 加价购金额 / 积分
    cost, unit = None, None
    m = re.search(r"加\s*([\d.]+)\s*元", text)
    if m:
        cost, unit = float(m.group(1)), "cny"

    # 限量
    limited_text = None
    limited_count = None
    m = re.search(r"限量[^\n！!。]*", text)
    if m:
        limited_text = m.group(0).strip()
        d = re.search(r"(\d+)\s*(万|份|套|对|个|枚|件|名)", limited_text)
        if d:
            n = int(d.group(1))
            if d.group(2) == "万":
                n *= 10000
            limited_count = n

    # 开售时间
    window_start = None
    m = re.search(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})\s*开售", text)
    if m and date:
        year = date[:4]
        window_start = f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}T{int(m.group(3)):02d}:{m.group(4)}:00"

    return {
        "ext_key": f"calendar:{date}:{category}",
        "name": name,
        "category": category,
        "nature": "联名款" if "X" in title or "联名" in text else "自有IP",
        "ip_collab": title.split("X")[-1].strip() if "X" in title else None,
        "release_date": date,
        "acquire_method": "加价购" if unit == "cny" else "消费赠送",
        "acquire_cost": cost,
        "acquire_cost_unit": unit,
        "acquisition_note": text.replace("\n", "，"),
        "limited_text": limited_text,
        "limited_count": limited_count,
        "window_start": window_start,
        "window_end": None,
        "soldout_observed": False,
        "image_url": None,
        "source": "mcp_calendar",
        "source_raw": text,
        "tags": [],
    }


def parse_mall(entry):
    """积分商城：字段已结构化，直接映射。"""
    name = entry.get("spuName", "")
    category = guess_category(entry.get("catName", "") + name)
    up = entry.get("upTime") or ""
    selling = entry.get("selling") or ""
    point = entry.get("point")

    limited_text = None
    limited_count = None
    m = re.search(r"限量\s*(\d+)\s*份", selling)
    if m:
        limited_count = int(m.group(1))
        limited_text = m.group(0)
    else:
        m = re.search(r"限量[^\n！!。]*", selling)
        if m:
            limited_text = m.group(0).strip()

    return {
        "ext_key": f"mall:{entry.get('spuId')}",
        "name": name,
        "category": category,
        "nature": "联名款" if re.search(r"[A-Za-z]{2,}", name) else "自有IP",
        "ip_collab": None,
        "release_date": up[:10] if up else None,
        "acquire_method": "积分兑换",
        "acquire_cost": int(point) if str(point).isdigit() else None,
        "acquire_cost_unit": "points",
        "acquisition_note": selling,
        "limited_text": limited_text,
        "limited_count": limited_count,
        "window_start": up.replace(" ", "T") if up else None,
        "window_end": (entry.get("downTime") or "").replace(" ", "T") or None,
        "soldout_observed": entry.get("status") == 3,
        "image_url": entry.get("spuImage"),
        "source": "mcp_mall",
        "source_raw": selling,
        "tags": [],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="合并入库")
    args = ap.parse_args()

    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    items = db["藏品"]
    existing_keys = {it.get("ext_key") for it in items if it.get("ext_key")}

    candidates = []
    for path in sorted(glob.glob(os.path.join(SNAP_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            snap = json.load(f)
        tool = snap.get("来源工具", "")
        for e in snap.get("条目", []):
            if "campaign-calendar" in tool:
                candidates.append(parse_calendar(e))
            elif "mall-points-products" in tool:
                candidates.append(parse_mall(e))

    new_items = []
    for c in candidates:
        c["_状态"] = "已存在" if c["ext_key"] in existing_keys else "新增"
        if c["_状态"] == "新增":
            new_items.append(c)

    os.makedirs(os.path.dirname(CAND_PATH), exist_ok=True)
    with open(CAND_PATH, "w", encoding="utf-8") as f:
        json.dump({"抽取时间": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                   "候选": candidates}, f, ensure_ascii=False, indent=2)

    print(f"快照抽取候选 {len(candidates)} 条：")
    print(f"{'状态':<6}{'ext_key':<34}{'名称':<30}{'金额/积分':<10}{'限量'}")
    print("-" * 96)
    for c in candidates:
        cost = f"{c['acquire_cost']}{'元' if c['acquire_cost_unit']=='cny' else '分'}" if c['acquire_cost'] else "-"
        print(f"{c['_状态']:<6}{c['ext_key']:<34}{(c['name'] or '')[:26]:<30}{cost:<10}{c['limited_text'] or '-'}")

    if args.apply:
        if not new_items:
            print("\n无新增条目，藏品库未变更（去重生效）。")
        else:
            for c in new_items:
                c.pop("_状态", None)
                cat = c["category"]
                same = [it for it in items if it["release_date"] == c["release_date"]
                        and it["category"] == cat and it["source"] == c["source"]]
                seq = len(same) + 1
                c["id"] = f"{c['release_date']}-{SLUG.get(cat, 'misc')}-{seq:02d}"
                c["si_score"] = None
                c["si_breakdown"] = None
                c["first_seen"] = datetime.now().strftime("%Y-%m-%d")
                c["last_updated"] = datetime.now().strftime("%Y-%m-%d")
                items.append(c)
            db["_meta"]["最后更新"] = datetime.now().strftime("%Y-%m-%d")
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            print(f"\n已新增 {len(new_items)} 条并写回藏品库。")
    else:
        print("\n（未加 --apply，仅生成 data/抽取候选.json，藏品库未变更）")


if __name__ == "__main__":
    main()
