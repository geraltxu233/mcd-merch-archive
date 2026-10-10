"""
合并人工补录队列进藏品库（按 ext_key 去重）。

用法：python 合并补录.py
"""

import sys
import json
import os
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE_PATH = os.path.join(ROOT, "data", "人工补录队列.json")
DB_PATH = os.path.join(ROOT, "data", "藏品库.json")


def main():
    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue = json.load(f)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")
    existing = {it.get("ext_key") for it in db["藏品"] if it.get("ext_key")}
    existing_ids = {it["id"] for it in db["藏品"]}

    added = []
    for c in queue.get("条目", []):
        if c["ext_key"] in existing:
            print(f"跳过（已存在）：{c['name']}")
            continue
        if c["id"] in existing_ids:
            print(f"跳过（ID 冲突）：{c['name']} -> {c['id']}")
            continue
        c.setdefault("si_score", None)
        c.setdefault("si_breakdown", None)
        c["first_seen"] = today
        c["last_updated"] = today
        db["藏品"].append(c)
        existing.add(c["ext_key"])
        existing_ids.add(c["id"])
        added.append(c["name"])

    if added:
        db["_meta"]["最后更新"] = today
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\n已并入 {len(added)} 条：")
        for n in added:
            print("  + " + n)
    else:
        print("\n无新增条目。")


if __name__ == "__main__":
    main()
