# -*- coding: utf-8 -*-
"""刷新任务编排：抓取 → 匹配 → 自动收录 → 收件箱 → 入库。

run_sync() 是唯一的刷新核心，三种入口共用：
    1. 网页「更新数据」按钮 → start_refresh() 后台线程
    2. Windows 计划任务     → daily_update.py 命令行
    3. 服务内置每日调度     → app.py 守护线程（开机补跑）

状态字典 _state 只服务于网页按钮的进度查询，定时入口不依赖它。
"""
from __future__ import annotations

import threading
import time
import traceback
from datetime import datetime

from .. import storage
from . import archive, sources
from .autocapture import auto_create
from .merge import apply_events

_state_lock = threading.Lock()
_state: dict = {"running": False, "started_at": None, "finished_at": None,
                "snapshot": None, "results": [], "matched": 0,
                "auto_added": 0, "inbox_new": 0}


def get_status() -> dict:
    with _state_lock:
        return dict(_state)


def is_running() -> bool:
    with _state_lock:
        return _state["running"]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def run_sync() -> dict:
    """同步执行一次完整刷新并入库，返回摘要（含分源结果与新收录企业名单）。"""
    # 更新前快照，任何一步翻车都能回滚
    snapshot = storage.snapshot()
    before_ids = {c["id"] for c in storage.load_companies()}

    cfg = storage.load_sources_config()
    all_events: list[dict] = []
    results: list[dict] = []
    for source in cfg.get("sources", []):
        t0 = time.time()
        item = {"id": source["id"], "name": source.get("name", source["id"]),
                "enabled": bool(source.get("enabled")), "ok": None,
                "count": 0, "error": "", "ms": 0}
        if not source.get("enabled"):
            item["error"] = "未启用"
            results.append(item)
            continue
        try:
            events = sources.run_source(source)
            item["ok"] = True
            item["count"] = len(events)
            all_events.extend(events)
        except Exception as e:  # noqa: BLE001 单源失败不影响其他源
            item["ok"] = False
            item["error"] = str(e)[:200]
            traceback.print_exc()
        item["ms"] = int((time.time() - t0) * 1000)
        results.append(item)

    companies = storage.load_companies()
    # 四段式处理：匹配库内企业 → 新企业自动收录 → 正文快照 → 剩余进收件箱
    matched_events, unmatched = apply_events(companies, all_events)
    auto_n, unmatched = auto_create(companies, unmatched,
                                    blocked=set(storage.load_blocked()))
    archived = archive.snapshot_events(matched_events)

    inbox = storage.load_inbox()
    known_urls = {i.get("url") for i in inbox}
    inbox_new = 0
    for ev in unmatched:
        if ev["url"] in known_urls:
            continue
        inbox.insert(0, {"title": ev["title"], "url": ev["url"],
                         "date": ev.get("date"), "source": ev.get("source"),
                         "fetched_at": _now()})
        inbox_new += 1
    storage.save_inbox(inbox)
    storage.save_companies(companies)

    # 本轮新出现的企业（供每日简报「新开招企业」栏目）
    auto_names = [c["name"] for c in companies
                  if c["id"] not in before_ids and c.get("auto_added")]
    return {"snapshot": snapshot, "results": results,
            "matched": len(matched_events), "archived": archived,
            "auto_added": auto_n, "auto_names": auto_names, "inbox_new": inbox_new}


def _worker() -> None:
    """网页按钮的后台线程包装：跑 run_sync 并把摘要写进状态字典。"""
    try:
        summary = run_sync()
        with _state_lock:
            _state.update({"results": summary["results"],
                           "matched": summary["matched"],
                           "auto_added": summary["auto_added"],
                           "inbox_new": summary["inbox_new"],
                           "snapshot": summary["snapshot"]})
    finally:
        with _state_lock:
            _state["running"] = False
            _state["finished_at"] = _now()


def start_refresh() -> tuple[bool, str]:
    """网页按钮入口：起后台线程跑一次刷新（同一时间只允许一个任务）。"""
    with _state_lock:
        if _state["running"]:
            return False, "已有更新任务在运行"
        _state.update({"running": True, "started_at": _now(), "finished_at": None,
                       "results": [], "matched": 0, "auto_added": 0,
                       "inbox_new": 0, "snapshot": None})
    threading.Thread(target=_worker, daemon=True).start()
    return True, "已开始更新"
