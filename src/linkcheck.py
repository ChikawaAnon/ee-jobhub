# -*- coding: utf-8 -*-
"""链接健康检查：定期探测所有企业的官方投递入口是否还活着。

结果分三档：
    ok      —— 正常（2xx/3xx）
    suspect —— 疑似防爬（403/412/429/503，浏览器人工可达，不用慌）
    dead    —— 确认打不开（404/超时/DNS 失败），卡片会标红提醒修正

调度：每天定时任务里检查「距上次 ≥7 天」就跑一轮（周检）；
网页「🔗 链接体检」按钮可随时手动触发（后台线程，不阻塞网站）。

存储：data/linkcheck.json
    {"last_run": "...", "running": false,
     "results": {"https://...": {"state": "ok|suspect|dead", "status": 200,
                                 "note": "", "checked_at": "..."}}}
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime

import requests

from . import storage
from .crawler.base import HEADERS

LINKCHECK_PATH = storage.DATA_DIR / "linkcheck.json"
CHECK_INTERVAL_DAYS = 7
TIMEOUT = 8
# 疑似防爬/临时故障的 HTTP 状态码：链接本身大概率没坏
# 401/403/412/429=WAF 拦探测；5xx=源站错误；520-526=Cloudflare 源站类错误，多为临时不可用
SUSPECT_CODES = {401, 403, 412, 429, 500, 502, 503, 504, 520, 521, 522, 523, 526}

_lock = threading.Lock()
_manual_running = False


def load() -> dict:
    if not LINKCHECK_PATH.exists():
        return {"last_run": None, "running": False, "results": {}}
    return json.loads(LINKCHECK_PATH.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    LINKCHECK_PATH.parent.mkdir(parents=True, exist_ok=True)
    LINKCHECK_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                              encoding="utf-8")


def check_url(url: str) -> dict:
    """探测单个链接，返回 {state: ok|suspect|dead|invalid, status, note}。

    分类原则（宁可标黄不可误报红）：
        dead    仅限「明确打不开」：HTTP 4xx/5xx（非防爬码）、域名解析失败
        suspect 连接被重置/超时/证书异常——大概率是防爬或网络限制，浏览器人工可达
        invalid 链接本身格式有问题（混入了说明文字等）
    """
    if not url or not url.startswith(("http://", "https://")):
        return {"state": "invalid", "status": 0, "note": "无有效链接"}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT,
                            stream=True, allow_redirects=True)
        resp.close()
        code = resp.status_code
        if code < 400:
            return {"state": "ok", "status": code, "note": ""}
        if code in SUSPECT_CODES:
            return {"state": "suspect", "status": code, "note": "疑似防爬，浏览器人工可达"}
        return {"state": "dead", "status": code, "note": f"HTTP {code}"}
    except requests.exceptions.InvalidURL:
        return {"state": "invalid", "status": 0, "note": "链接含非 URL 字符，需修正"}
    except requests.exceptions.SSLError:
        return {"state": "suspect", "status": 0, "note": "证书异常，浏览器访问注意提示"}
    except requests.exceptions.Timeout:
        return {"state": "suspect", "status": 0, "note": "探测超时（可能防爬或网络限制）"}
    except requests.exceptions.ConnectionError as e:
        msg = str(e)
        if "getaddrinfo failed" in msg or "Name or service" in msg or "No address" in msg:
            return {"state": "dead", "status": 0, "note": "域名无法解析（可能已失效）"}
        return {"state": "suspect", "status": 0, "note": "连接被重置（可能防爬/仅校内网）"}
    except Exception as e:  # noqa: BLE001
        return {"state": "suspect", "status": 0, "note": type(e).__name__}


def run_all(companies: list[dict], progress_every: int = 20) -> dict:
    """全量检查（串行 + 0.3s 间隔，对源站友好）。边跑边落盘保留进度。"""
    global _manual_running
    data = load()
    data["running"] = True
    save(data)

    results = data.setdefault("results", {})
    urls = sorted({c.get("apply_url", "") for c in companies} - {""})
    fresh = {}
    for i, url in enumerate(urls, 1):
        fresh[url] = dict(check_url(url), checked_at=_now())
        if i % progress_every == 0:
            data["results"] = fresh
            save(data)
        time.sleep(0.3)

    data["results"] = fresh  # 整表替换：丢弃已不存在的旧条目，防止陈旧结果混入
    data["running"] = False
    data["last_run"] = _now()
    save(data)
    with _lock:
        _manual_running = False
    return data


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def is_running() -> bool:
    with _lock:
        return _manual_running


def start_manual(companies: list[dict]) -> tuple[bool, str]:
    """网页「立即检查」入口：起后台线程跑全量。"""
    global _manual_running
    with _lock:
        if _manual_running:
            return False, "检查已在进行中"
        _manual_running = True
    threading.Thread(target=run_all, args=(companies,), daemon=True).start()
    return True, "已开始检查"


def run_weekly_if_due(companies: list[dict]) -> bool:
    """每天定时任务里调用：距上次检查 ≥7 天才真正跑一轮。"""
    data = load()
    last = data.get("last_run") or ""
    try:
        due = (datetime.now() - datetime.strptime(last[:10], "%Y-%m-%d")).days \
            >= CHECK_INTERVAL_DAYS if last else True
    except ValueError:
        due = True
    if due and not is_running():
        run_all(companies)
        return True
    return False
