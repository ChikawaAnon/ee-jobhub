# -*- coding: utf-8 -*-
"""JSON 文件存储：线程安全的加载/保存/快照。"""
from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
COMPANIES_PATH = DATA_DIR / "companies.json"
SOURCES_PATH = DATA_DIR / "sources.json"
INBOX_PATH = DATA_DIR / "inbox.json"
BLOCKED_PATH = DATA_DIR / "blocked.json"
ARCHIVE_PATH = DATA_DIR / "articles.json"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
SNAPSHOT_KEEP = 20

_LOCK = threading.RLock()


def _atomic_write(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def load_companies() -> list[dict]:
    with _LOCK:
        if not COMPANIES_PATH.exists():
            return []
        return json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))


def save_companies(companies: list[dict]) -> None:
    with _LOCK:
        companies.sort(key=lambda c: c["id"])
        _atomic_write(COMPANIES_PATH, companies)


def load_sources_config() -> dict:
    if not SOURCES_PATH.exists():
        return {"sources": []}
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def load_inbox() -> list[dict]:
    with _LOCK:
        if not INBOX_PATH.exists():
            return []
        return json.loads(INBOX_PATH.read_text(encoding="utf-8"))


def save_inbox(items: list[dict]) -> None:
    with _LOCK:
        _atomic_write(INBOX_PATH, items[:200])


def load_blocked() -> list[str]:
    """被用户删掉的自动收录企业短键列表：阻止爬虫再次自动收录同名企业。"""
    with _LOCK:
        if not BLOCKED_PATH.exists():
            return []
        return json.loads(BLOCKED_PATH.read_text(encoding="utf-8"))


def add_blocked(keys: list[str]) -> None:
    with _LOCK:
        blocked = set(load_blocked()) | set(keys)
        _atomic_write(BLOCKED_PATH, sorted(blocked))


def load_archive() -> dict:
    """公告正文档案：{url: {title, company_id, company_name, text, fetched_at}}。"""
    with _LOCK:
        if not ARCHIVE_PATH.exists():
            return {}
        return json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))


def save_archive(archive: dict) -> None:
    with _LOCK:
        _atomic_write(ARCHIVE_PATH, archive)


def snapshot() -> str | None:
    """更新前备份主库，返回快照文件名。保留最近 SNAPSHOT_KEEP 份。"""
    with _LOCK:
        if not COMPANIES_PATH.exists():
            return None
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        name = "companies-%s.json" % datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(COMPANIES_PATH, SNAPSHOT_DIR / name)
        olds = sorted(SNAPSHOT_DIR.glob("companies-*.json"))
        for old in olds[:-SNAPSHOT_KEEP]:
            old.unlink(missing_ok=True)
        return name
