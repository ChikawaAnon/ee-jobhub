# -*- coding: utf-8 -*-
"""公告正文快照：把匹配到库内企业的公告正文抓回来存档。

为什么：企业官网/就业网经常删旧公告，只存标题链接的话，笔试前想回看
「户口/专业要求/不招哪届」这些细节就失联了。存成全文后：
    1. 公告永久可查（data/articles.json，单文件全量）
    2. 支持全文搜索（/api/search，如搜「户口」直接命中提到户口的公告）

礼貌抓取：只抓「匹配到库内企业」的公告、单次刷新最多 10 篇、沿用全局限速。
"""
from __future__ import annotations

import re
from datetime import datetime

from .. import storage
from .base import fetch
from bs4 import BeautifulSoup

# 单次刷新最多快照篇数（控制刷新时长，其余公告下次可见时再抓）
CAP_PER_RUN = 10
TEXT_LIMIT = 8000


def load_archive() -> dict:
    return storage.load_archive()


def extract_text(html: str) -> str:
    """剥掉脚本样式后取正文纯文本，压掉多余空行，截断到 TEXT_LIMIT。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:TEXT_LIMIT]


def snapshot_events(matched_events: list[dict]) -> int:
    """抓取并归档公告正文。返回本次成功快照的篇数。

    matched_events：apply_events 返回的已匹配公告（含 company_id/company_name）
    """
    archive = storage.load_archive()
    saved = 0
    for ev in matched_events:
        if saved >= CAP_PER_RUN:
            break
        url = ev.get("url", "")
        if not url or url in archive:
            continue
        try:
            text = extract_text(fetch(url, timeout=15, retries=0))
        except Exception:  # noqa: BLE001 单篇失败不阻塞刷新
            continue
        if len(text) < 50:  # 太短说明没抓到正文（如纯 JS 页）
            continue
        archive[url] = {
            "title": ev.get("title", ""),
            "company_id": ev.get("company_id", ""),
            "company_name": ev.get("company_name", ""),
            "text": text,
            "fetched_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        saved += 1
    if saved:
        storage.save_archive(archive)
    return saved


def search(query: str, limit: int = 30) -> list[dict]:
    """公告全文搜索：标题或正文包含关键词即命中，返回带高亮片段的结果。"""
    if not query or not query.strip():
        return []
    q = query.strip()
    archive = storage.load_archive()
    out = []
    for url, art in archive.items():
        hay = (art.get("title", "") + "\n" + art.get("text", ""))
        pos = hay.find(q)
        if pos == -1:
            continue
        # 取命中位置前后各 80 字作为摘要片段
        start = max(0, pos - 80)
        snippet = hay[start:pos + len(q) + 80].replace("\n", " ")
        out.append({
            "url": url,
            "title": art.get("title", ""),
            "company": art.get("company_name", ""),
            "snippet": snippet,
            "fetched_at": art.get("fetched_at", ""),
        })
        if len(out) >= limit:
            break
    return out
