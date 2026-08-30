# -*- coding: utf-8 -*-
"""新企业自动收录模块：爬虫发现「库外新企业开始招聘」时自动建档上架。

触发门槛（宁可漏不可滥）：
    标题带校招信号 → 校招/校园招聘/秋招/春招/实习生/校园宣讲，或「20XX届」字样
    且能解析出带公司后缀（集团/股份/有限公司/公司）的企业名

建档信息全部来自公告标题（名称/批次/城市能推断多少算多少），
记录打上 auto_added 标记，前端显示「🤖 自动收录」徽章和删除按钮。
单次刷新上限 cap 家，防止一次性公告把列表刷爆。
"""
from __future__ import annotations

import re
from datetime import datetime

from ..schema import normalize, slugify
from .matching import company_keys

# 触发自动收录的标题信号词
AUTO_KEYWORDS = ("校招", "校园招聘", "秋招", "秋季校园", "春招", "春季校园", "实习生", "校园宣讲")
# 企业名形态：任意中英文组合 + 公司后缀（非贪婪，取最短完整匹配）
AUTO_NAME_RE = re.compile(r"([\u4e00-\u9fa5A-Za-z0-9·（）()]{2,24}?(?:集团|股份有限公司|有限公司|公司))")
# 广东省内地级市：用于从名称里剥前缀、从标题里猜工作城市
GD_CITIES = ("广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州", "江门", "湛江",
             "茂名", "阳江", "汕头", "潮州", "揭阳", "肇庆", "韶关", "清远", "云浮",
             "梅州", "汕尾", "河源")


def _is_campus_event(title: str) -> bool:
    """标题是否带校招/实习信号（一次性的社会岗位如「救生员XX公司」会被拦下）。"""
    if re.search(r"20\d{2}届", title):
        return True
    return any(k in title for k in AUTO_KEYWORDS)


def _extract_name(title: str) -> str | None:
    """从标题解析企业名；剥掉「广东/深圳」等地市前缀让卡片名更干净。"""
    m = AUTO_NAME_RE.search(title)
    if not m:
        return None
    name = m.group(1)
    for city in GD_CITIES:
        if name.startswith(city) and len(name) - len(city) >= 4:
            return name[len(city):]
    return name


def _infer_batch(title: str) -> list[str]:
    """从标题推断招聘批次（秋招/春招/实习），推断不出默认秋招。"""
    batch = []
    if any(k in title for k in ("秋招", "秋季")):
        batch.append("秋招")
    if any(k in title for k in ("春招", "春季")):
        batch.append("春招")
    if "实习" in title:
        batch.append("实习")
    return batch or ["秋招"]


def auto_create(companies: list[dict], unmatched: list[dict],
                blocked: set[str] | None = None, cap: int = 15) -> tuple[int, list[dict]]:
    """把带校招信号、匹配不到库内企业的新公告自动建档。

    参数：
        companies: 主库列表（原地追加新记录）
        unmatched: apply_events 后没匹配到企业的公告
        blocked: 用户删除过的企业短键集合（避免删了又自动加回来）
        cap: 单次刷新最多自动收录数量
    返回：
        (新增企业数, 仍然没处理掉的公告 → 交给收件箱)
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    today = now[:10]
    blocked = blocked or set()
    # 已存在企业的全部短键（含本轮刚建的），用于查重
    existing: set[str] = set()
    for c in companies:
        existing.update(company_keys(c))
    created = 0
    remaining: list[dict] = []
    for ev in unmatched:
        if created >= cap:
            remaining.append(ev)
            continue
        title = ev["title"]
        if not _is_campus_event(title):
            remaining.append(ev)
            continue
        name = _extract_name(title)
        if not name or len(name) < 3:
            remaining.append(ev)
            continue
        key = company_keys({"name": name})[0]
        if key in existing or key in blocked:
            continue
        cities = [city for city in GD_CITIES if city in title or city in name][:3]
        # id 唯一化：slug 冲突时追加 -2/-3
        base = slugify(name)
        cid, n = base, 2
        while any(c["id"] == cid for c in companies):
            cid = f"{base}-{n}"
            n += 1
        rec = normalize({
            "id": cid, "name": name, "cat": "general", "sub": "待分类",
            "ctype": "民企", "industry": "",
            "batch": _infer_batch(title), "status": "进行中",
            "positions": [], "cities": cities,
            "apply_url": ev["url"], "official_site": "",
            "desc": title,
            "ee_notes": "🤖 自动收录：信息来自就业网公告标题，点详情查看公告原文，用「修正」补充岗位/薪资/投递入口",
            "tags": ["自动收录"], "auto_added": True,
        })
        rec["sources"] = [{"type": "auto", "url": ev["url"], "date": today}]
        rec["news"] = [{"title": title, "url": ev["url"], "date": ev.get("date"),
                        "source": ev.get("source"), "fetched_at": now}]
        rec["last_crawl"] = now
        rec["updated_at"] = now
        companies.append(rec)
        existing.add(key)
        created += 1
    return created, remaining
