"""
计算稀缺度指数 SI，并回写藏品库。

规则来源：M1数据结构_藏品库与冷启动清单.md 第五节、第六节
- status：不用 MCP 字段，按时间窗自判
- SI = (限量*0.3 + 门槛*0.2 + 窗口*0.2 + 售罄*0.2 + IP*0.1) * 20

用法：
    python 计算稀缺度.py                 # 用系统当前时间
    python 计算稀缺度.py --now 2026-10-10T12:30:00   # 指定基准时间（保证可复现）
"""

import sys
import json
import os
import argparse
from datetime import datetime, timedelta

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "藏品库.json")

WEIGHTS = {"限量": 0.30, "门槛": 0.20, "窗口": 0.20, "售罄": 0.20, "IP": 0.10}

# IP 强度关键词表（可维护；命中即取对应分，未命中且有联名取 3，自有 IP 取 2，无取 1）
IP_TOP = ["Nike", "迪士尼", "Disney", "宝可梦", "Pokemon", "可口可乐", "Coca"]
IP_KNOWN = ["我的世界", "Minecraft", "罗技", "Logitech"]


def parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def judge_status(item, now):
    """按时间窗自判状态。window 缺失时以 release_date 兜底。"""
    if item.get("soldout_observed"):
        return "售罄"
    ws = parse_dt(item.get("window_start")) or parse_dt(item.get("release_date"))
    we = parse_dt(item.get("window_end"))
    if ws is None and we is None:
        return "未知"
    if ws and now < ws:
        return "预热"
    if we and now > we:
        return "已结束"
    if we:
        return "在售"
    # 只有起始时间、无结束时间：以 90 天为默认在售窗口
    if ws and (now - ws) > timedelta(days=90):
        return "已结束"
    return "在售"


def score_limited(item):
    n = item.get("limited_count")
    if isinstance(n, (int, float)):
        if n < 100:
            return 5
        if n < 1000:
            return 4
        if n < 10000:
            return 3
        return 2
    t = item.get("limited_text") or ""
    if "限量" in t or "限购" in t or "售罄" in t:
        return 3
    return 1


def score_threshold(item):
    c = item.get("acquire_cost")
    u = item.get("acquire_cost_unit")
    if not isinstance(c, (int, float)):
        return 1
    if u == "cny":
        if c >= 100:
            return 5
        if c >= 50:
            return 4
        if c >= 30:
            return 3
        return 2
    if u == "points":
        if c >= 5000:
            return 5
        if c >= 1000:
            return 4
        if c >= 500:
            return 3
        return 2
    return 1


def score_window(item):
    ws = parse_dt(item.get("window_start"))
    we = parse_dt(item.get("window_end"))
    if not ws or not we:
        return 2  # 数据不足，给中性偏低分
    hours = (we - ws).total_seconds() / 3600
    if hours <= 24:
        return 5
    if hours <= 72:
        return 4
    if hours <= 168:
        return 3
    if hours <= 672:
        return 2
    return 1


def score_soldout(status):
    return {"售罄": 5, "已结束": 3, "在售": 2, "预热": 1}.get(status, 2)


def score_ip(item):
    ip = item.get("ip_collab") or ""
    if any(k in ip for k in IP_TOP):
        return 5
    if any(k in ip for k in IP_KNOWN):
        return 4
    if ip:
        return 3
    if item.get("nature") == "自有IP":
        return 2
    return 1


def compute(item, now):
    status = judge_status(item, now)
    item["status"] = status
    breakdown = {
        "限量": score_limited(item),
        "门槛": score_threshold(item),
        "窗口": score_window(item),
        "售罄": score_soldout(status),
        "IP": score_ip(item),
    }
    si = sum(breakdown[k] * WEIGHTS[k] for k in WEIGHTS) * 20
    item["si_breakdown"] = breakdown
    item["si_score"] = round(si, 1)
    return item


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", default=None, help="基准时间 ISO 格式，默认取系统时间")
    args = ap.parse_args()
    now = parse_dt(args.now) if args.now else datetime.now()

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    for item in db["藏品"]:
        compute(item, now)
        item["last_updated"] = now.strftime("%Y-%m-%d")

    db["_meta"]["最后更新"] = now.strftime("%Y-%m-%d")

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print(f"基准时间：{now}")
    print(f"已计算 {len(db['藏品'])} 条藏品\n")
    print(f"{'藏品':<34}{'状态':<8}{'SI':<8}明细")
    print("-" * 78)
    for item in sorted(db["藏品"], key=lambda x: -(x["si_score"] or 0)):
        b = item["si_breakdown"]
        detail = " ".join(f"{k}{v}" for k, v in b.items())
        print(f"{item['name'][:32]:<34}{item['status']:<8}{item['si_score']:<8}{detail}")


if __name__ == "__main__":
    main()
