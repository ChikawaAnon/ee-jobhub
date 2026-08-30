# -*- coding: utf-8 -*-
"""每日增量简报：对比一次刷新前后的库内变化，生成给毕业生看的日报。

简报四个栏目：
    🆕 新开招企业      —— 刷新后新出现的企业（自动收录的）
    📰 已收录企业新动态 —— 库内企业挂上的新公告
    ⏰ 14 天内截止     —— 快到截止日期的，按剩余天数排序
    📥 收件箱待处理    —— 没匹配上、需要人工看一眼的

存储：data/digest/latest.json（最新一份，网页「今日简报」读它）
      data/digest/history/（按日期归档，保留最近 30 份）
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from . import keywords, storage

DIGEST_DIR = storage.DATA_DIR / "digest"
DIGEST_HOUR = 8          # 每天 8 点后允许自动更新（计划任务和服务内置调度共用）
HISTORY_KEEP = 30


def load_latest() -> dict | None:
    path = DIGEST_DIR / "latest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save(d: dict) -> None:
    """写最新一份 + 按日期归档，历史超量自动清理。"""
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    (DIGEST_DIR / "latest.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    history = DIGEST_DIR / "history"
    history.mkdir(exist_ok=True)
    day = (d.get("generated") or datetime.now().strftime("%Y-%m-%d"))[:10]
    (history / f"daily-{day}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    olds = sorted(history.glob("daily-*.json"))
    for old in olds[:-HISTORY_KEEP]:
        old.unlink(missing_ok=True)


def build(before: list[dict], after: list[dict], summary: dict) -> dict:
    """对比刷新前后的企业库，生成结构化简报。

    before/after：本次刷新前后的企业库列表
    summary：     runner.run_sync() 的返回值
    """
    # 🆕 新开招企业：本轮新出现且是自动收录的
    before_ids = {c["id"] for c in before}
    new_companies = []
    for c in after:
        if c["id"] in before_ids or not c.get("auto_added"):
            continue
        first = (c.get("news") or [{}])[0]
        new_companies.append({"name": c["name"], "title": first.get("title", ""),
                              "url": first.get("url", "")})

    # 📰 库内企业新动态：逐家对比公告 URL 集合的差集
    before_urls = {c["id"]: {n.get("url") for n in c.get("news", [])} for c in before}
    new_news = []
    for c in after:
        old = before_urls.get(c["id"], set())
        for n in c.get("news", []):
            if n.get("url") and n["url"] not in old:
                new_news.append({"company": c["name"], "title": n["title"],
                                 "url": n["url"]})

    # ⏰ 14 天内截止
    today = date.today()
    closing = []
    for c in after:
        dl = c.get("deadline")
        if not dl:
            continue
        try:
            days = (datetime.strptime(dl, "%Y-%m-%d").date() - today).days
        except ValueError:
            continue
        if 0 <= days <= 14:
            closing.append({"name": c["name"], "deadline": dl,
                            "days": days, "url": c.get("apply_url", "")})
    closing.sort(key=lambda x: x["days"])

    fetched = sum(r["count"] for r in summary.get("results", []) if r.get("ok"))

    # ⭐ 关键词订阅：新企业/新动态命中订阅词的，置顶到简报最上方
    kws = keywords.load_keywords()
    starred = []
    for c in new_companies:
        hits = keywords.match(c["name"] + " " + c["title"], kws)
        if hits:
            starred.append({**c, "kind": "🆕 新企业", "hits": hits})
    for n in new_news:
        hits = keywords.match(n["title"] + " " + n["company"], kws)
        if hits:
            starred.append({**n, "kind": "📰 动态", "hits": hits})

    return {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stats": {"fetched": fetched,
                  "matched": summary.get("matched", 0),
                  "auto_added": summary.get("auto_added", 0),
                  "inbox_new": summary.get("inbox_new", 0)},
        "keywords": kws,
        "starred": starred,
        "new_companies": new_companies,
        "new_news": new_news[:40],
        "closing": closing,
    }
