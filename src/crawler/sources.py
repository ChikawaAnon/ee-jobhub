# -*- coding: utf-8 -*-
"""数据源适配器：按 data/sources.json 配置驱动，每源独立容错。

当前默认启用本校就业网（静态页面可解析）。其余源因 JS 渲染/反爬默认关闭，
配置里改 enabled 即可开启；全部失败不影响已有数据。
"""
from __future__ import annotations

from .base import extract_links, fetch, guess_date_from_title


def run_html_list(source: dict) -> list[dict]:
    """通用静态公告列表抓取：base + paths，抽取含招聘关键词的链接。"""
    cfg = source.get("config", {})
    base = cfg.get("base", "").rstrip("/")
    paths = cfg.get("paths", ["/"])
    limit = int(cfg.get("max_items", 40))
    events: list[dict] = []
    for path in paths:
        try:
            html = fetch(base + path)
        except Exception as e:  # noqa: BLE001
            if not events:
                raise
            continue
        for item in extract_links(html, base + path)[:limit]:
            item["date"] = item.get("date") or guess_date_from_title(item["title"])
            item["source"] = source["id"]
            events.append(item)
    return events


ADAPTERS = {
    "html_list": run_html_list,
}


def run_source(source: dict) -> list[dict]:
    kind = source.get("type", "html_list")
    adapter = ADAPTERS.get(kind)
    if not adapter:
        raise RuntimeError("未知数据源类型: %s" % kind)
    return adapter(source)
