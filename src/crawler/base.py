# -*- coding: utf-8 -*-
"""爬虫基础能力：限速抓取、链接抽取。仅抓公开页面，标准 UA，不绕任何访问控制。"""
from __future__ import annotations

import re
import time

import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}

# 抓取间隔（秒），对源站友好
MIN_INTERVAL = 2.0
_last_request_at = [0.0]

SKIP_HREF = ("javascript:", "mailto:", "tel:", "#", ".css", ".js", ".jpg", ".png", ".ico", ".zip")
TITLE_KEYWORDS = ("招聘", "宣讲", "公告", "双选", "校招", "实习", "秋招", "春招", "网申", "投递")
# jysd 等就业平台语义明确的栏目路径：链接本身就是公司公告，不依赖标题关键词
HREF_TRUSTED = ("/campus/view/", "/teachin/view/", "/jobfair/view/")
TITLE_PREFIX_STRIP = ("已举办", "未开始", "进行中", "即将开始", "已结束")
DATE_RE = re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})")


def _rate_limit() -> None:
    wait = MIN_INTERVAL - (time.time() - _last_request_at[0])
    if wait > 0:
        time.sleep(wait)
    _last_request_at[0] = time.time()


def fetch(url: str, timeout: int = 15, retries: int = 1) -> str:
    """抓取页面文本，失败重试；不做任何验证码/登录绕过。"""
    last_err: Exception | None = None
    for _ in range(retries + 1):
        _rate_limit()
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            last_err = RuntimeError("HTTP %s" % resp.status_code)
        except Exception as e:  # noqa: BLE001
            last_err = e
        time.sleep(1.5)
    raise RuntimeError("fetch failed: %s (%s)" % (url, last_err))


def extract_links(html: str, base_url: str) -> list[dict]:
    """抽取页面中的公告链接：标题含招聘类关键词，或属于平台语义明确的栏目路径。"""
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "html.parser")
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.lower().startswith(SKIP_HREF):
            continue
        title = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        for prefix in TITLE_PREFIX_STRIP:
            if title.startswith(prefix):
                title = title[len(prefix):]
        if len(title) < 8:
            continue
        url = urljoin(base_url, href)
        trusted = any(path in url for path in HREF_TRUSTED)
        if not trusted and not any(k in title for k in TITLE_KEYWORDS):
            continue
        if url in seen:
            continue
        seen.add(url)
        ctx = a.find_parent(["li", "tr", "div", "td"])
        date = None
        if ctx:
            m = DATE_RE.search(ctx.get_text(" ", strip=True))
            if m:
                date = "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
        out.append({"title": title[:120], "url": url, "date": date})
    return out


def guess_date_from_title(title: str) -> str | None:
    m = DATE_RE.search(title)
    if m:
        return "%s-%02d-%02d" % (m.group(1), int(m.group(2)), int(m.group(3)))
    return None
