"""
校验藏品库：必填字段、ID 唯一、来源标注、状态与 SI 完整性。

用法：python 校验藏品库.py
退出码：0 = 全部通过；1 = 存在问题
"""

import sys
import json
import os

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "藏品库.json")

REQUIRED = [
    "id", "name", "category", "nature", "release_date",
    "acquire_method", "acquisition_note", "status", "source",
    "first_seen", "last_updated",
]
VALID_SOURCE = {"mcp_calendar", "mcp_mall", "manual"}


def main():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)

    items = db.get("藏品", [])
    problems = []
    ids = {}

    for it in items:
        iid = it.get("id", "<无ID>")
        for field in REQUIRED:
            if it.get(field) in (None, "", []):
                problems.append(f"[{iid}] 必填字段为空：{field}")
        if it.get("source") not in VALID_SOURCE:
            problems.append(f"[{iid}] source 非法：{it.get('source')}")
        if not it.get("ext_key"):
            problems.append(f"[{iid}] 缺少 ext_key（去重键，否则重复采集会漏去重）")
        if it.get("si_score") is None:
            problems.append(f"[{iid}] SI 未计算")
        if it.get("source") == "manual" and not it.get("source_raw"):
            problems.append(f"[{iid}] 人工条目缺少 source_raw 溯源说明")
        ids[iid] = ids.get(iid, 0) + 1

    for iid, n in ids.items():
        if n > 1:
            problems.append(f"ID 重复 {n} 次：{iid}")

    # 统计
    src = {}
    cat = {}
    for it in items:
        src[it.get("source")] = src.get(it.get("source"), 0) + 1
        cat[it.get("category")] = cat.get(it.get("category"), 0) + 1

    print(f"藏品总数：{len(items)}")
    print(f"来源分布：{src}")
    print(f"品类分布：{cat}")

    if problems:
        print(f"\n发现 {len(problems)} 个问题：")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\n校验通过：字段完整、ID 唯一、来源合法。")


if __name__ == "__main__":
    main()
