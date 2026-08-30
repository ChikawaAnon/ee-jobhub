# -*- coding: utf-8 -*-
"""数据模型与字段保护规则。

字段分三类：
- MANUAL_FIELDS：人工维护字段，爬虫永不覆盖（有 manual_overrides 标记或种子已填）
- CRAWLABLE_FIELDS：爬虫可更新的字段
- SYSTEM_FIELDS：系统自动维护
"""
from __future__ import annotations

from datetime import datetime

CATS = {
    "grid": {
        "label": "电网/发电/设计院",
        "subs": ["电网", "发电集团", "核电", "地方能源", "设计院"],
    },
    "equipment": {
        "label": "电气设备/工控",
        "subs": ["输配电设备", "二次设备/继保", "工控/传动", "发电设备", "电源设备", "外企电气"],
    },
    "newenergy": {
        "label": "新能源/车企/电池",
        "subs": ["电池", "光伏", "风电", "逆变器/储能", "车企"],
    },
    "general": {
        "label": "泛工科延伸",
        "subs": ["ICT硬件", "医疗器械", "家电", "轨交", "石化钢铁", "半导体/面板", "高端制造", "机器人/具身智能", "待分类"],
    },
}

BATCHES = ["秋招", "春招", "实习", "社招"]
STATUSES = ["进行中", "即将截止", "未开启", "已结束", "常年招聘", "未知"]
YEARS = ["2027届", "2028届", "2026届"]
TAGS = ["S级对口", "高度相关", "相关", "延伸方向", "门槛不高", "非标自动化",
        "广东有岗", "本科友好", "央国企", "外企", "重点推荐", "自动收录"]
SORTS = {"recommend": "推荐优先", "deadline": "截止优先", "updated": "最近更新", "name": "名称"}

MANUAL_FIELDS = [
    "alias", "batch", "status", "positions", "position_details", "apply_url",
    "official_site", "cities", "start_date", "deadline", "deadline_note",
    "salary_text", "salary_structure", "salary_source", "desc", "ee_notes",
    "tags", "pinned",
]
CRAWLABLE_FIELDS = ["news", "last_crawl"]
SYSTEM_FIELDS = ["id", "name", "cat", "sub", "ctype", "industry", "sources",
                 "last_verified", "verify_note", "auto_added", "manual_overrides",
                 "year", "updated_at"]

ALL_FIELDS = MANUAL_FIELDS + CRAWLABLE_FIELDS + SYSTEM_FIELDS

DEFAULTS = {
    "alias": "",
    "batch": ["秋招"],
    "status": "未知",
    "year": "2027届",
    "positions": [],
    "position_details": [],
    "cities": [],
    "start_date": None,
    "deadline": None,
    "deadline_note": "",
    "salary_text": "",
    "salary_structure": "",
    "salary_source": "公开渠道聚合，仅供参考",
    "desc": "",
    "ee_notes": "",
    "tags": [],
    "pinned": False,
    "sources": [],
    "last_verified": None,
    "verify_note": "",
    "auto_added": False,
    "manual_overrides": [],
    "news": [],
    "last_crawl": None,
}


def normalize(raw: dict) -> dict:
    """补齐默认字段并做基本清洗，返回完整记录。"""
    out = dict(DEFAULTS)
    out.update({k: v for k, v in raw.items() if k in ALL_FIELDS})
    for list_field in ("batch", "positions", "position_details", "cities", "tags",
                       "sources", "manual_overrides", "news"):
        if not isinstance(out[list_field], list):
            out[list_field] = []
    if out["status"] not in STATUSES:
        out["status"] = "未知"
    if not out["sources"]:
        out["sources"] = [{"type": "seed", "url": raw.get("apply_url", ""),
                           "date": datetime.now().strftime("%Y-%m-%d")}]
    return out


def is_valid_new_company(body: dict) -> str | None:
    """手动提交上新校验，返回错误信息或 None。"""
    if not body.get("name") or len(body["name"].strip()) < 2:
        return "企业名称必填（至少 2 个字）"
    if body.get("cat") not in CATS:
        return "请选择正确的企业方向"
    subs = CATS[body["cat"]]["subs"]
    if body.get("sub") not in subs:
        return "请选择正确的子类"
    url = body.get("apply_url", "").strip()
    if url and not url.startswith(("http://", "https://")):
        return "投递入口必须是 http(s) 链接"
    return None


def slugify(name: str) -> str:
    import hashlib
    import re
    ascii_part = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    if len(ascii_part) >= 2:
        return ascii_part[:40]
    return "c-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
