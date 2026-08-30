# -*- coding: utf-8 -*-
"""种子数据 → data/companies.json 生成器。

用法：python -m src.build_seed
默认保留 companies.json 中已有的人工修改（manual_overrides 非空的公司按字段合并），
加 --force 全量重建。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.schema import normalize  # noqa: E402
from src import storage  # noqa: E402
from src.seed import (  # noqa: E402
    equipment, ecosystem, general, grid, guangdong, newenergy, robotics, yuexi,
)
from src.seed.extra_tags import EXTRA_TAGS  # noqa: E402
from src.seed.verify import VERIFIED, VERIFIED_DATE  # noqa: E402


def apply_verified(records: list[dict]) -> None:
    for r in records:
        v = VERIFIED.get(r["id"])
        if not v:
            continue
        for key in ("apply_url", "official_site", "last_verified", "verify_note",
                    "salary_text", "cities"):
            if key in v:
                r[key] = v[key]
        r["sources"] = [{"type": "verified", "url": r["apply_url"],
                         "date": VERIFIED_DATE}] + r["sources"]


def apply_extra_tags(records: list[dict]) -> None:
    """补充标签（门槛不高/非标自动化等），已存在则跳过。"""
    for r in records:
        for t in EXTRA_TAGS.get(r["id"], []):
            if t not in r["tags"]:
                r["tags"].append(t)


def build(force: bool = False) -> int:
    raws = (grid.COMPANIES + equipment.COMPANIES + newenergy.COMPANIES
            + general.COMPANIES + guangdong.COMPANIES + robotics.COMPANIES
            + ecosystem.COMPANIES + yuexi.COMPANIES)
    records = [normalize(r) for r in raws]
    apply_verified(records)
    apply_extra_tags(records)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for r in records:
        r["updated_at"] = now

    if not force and storage.COMPANIES_PATH.exists():
        old = {c["id"]: c for c in storage.load_companies()}
        for r in records:
            prev = old.get(r["id"])
            if not prev:
                continue
            # 爬虫动态与人工修改永远保留（不管本次种子是否变化）
            r["news"] = prev.get("news", [])
            r["last_crawl"] = prev.get("last_crawl")
            if prev.get("manual_overrides"):
                for f in prev["manual_overrides"]:
                    if f in prev:
                        r[f] = prev[f]
                r["manual_overrides"] = prev["manual_overrides"]

    # 🤖 自动收录的企业不在种子里，重建时原样保留（否则每重建一次就丢一批）
    seed_ids = {r["id"] for r in records}
    if not force and storage.COMPANIES_PATH.exists():
        for prev in storage.load_companies():
            if prev.get("auto_added") and prev["id"] not in seed_ids:
                records.append(prev)

    # id 冲突检查
    ids = [r["id"] for r in records]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit("种子数据 id 重复: %s" % dup)

    storage.save_companies(records)
    print("seeded %d companies -> %s" % (len(records), storage.COMPANIES_PATH))
    return len(records)


if __name__ == "__main__":
    build(force="--force" in sys.argv)
