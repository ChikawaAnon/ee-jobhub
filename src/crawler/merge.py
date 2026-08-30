# -*- coding: utf-8 -*-
"""爬取结果合并编排：公告事件 → 库内企业（news）/ 新企业（autocapture）/ 收件箱。

字段保护核心规则：爬虫只追加 news 与 last_crawl，
绝不碰薪资/投递链接/电气备注/重点推荐等人工维护字段。
"""
from __future__ import annotations

from datetime import datetime

from .matching import match_company

# 每家企业最多保留的动态条数
NEWS_LIMIT = 12


def apply_events(companies: list[dict], events: list[dict]) -> tuple[list[dict], list[dict]]:
    """把公告事件合并到企业库（原地修改 companies）。

    返回 (已匹配公告列表, 未匹配公告列表)：
        已匹配公告附带 company_id/company_name，供正文快照（archive）使用；
        未匹配公告交给 autocapture / 收件箱。
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    matched_events: list[dict] = []
    unmatched: list[dict] = []
    for ev in events:
        company = match_company(ev["title"], companies)
        if not company:
            unmatched.append(ev)
            continue
        news = company.setdefault("news", [])
        # 同一公告按 URL 去重
        if any(n.get("url") == ev["url"] for n in news):
            continue
        news.insert(0, {
            "title": ev["title"], "url": ev["url"],
            "date": ev.get("date"), "source": ev.get("source"),
            "fetched_at": now,
        })
        del news[NEWS_LIMIT:]
        company["last_crawl"] = now
        matched_events.append({**ev, "company_id": company["id"],
                               "company_name": company["name"]})
    return matched_events, unmatched
