# -*- coding: utf-8 -*-
"""电气秋招整合站 · FastAPI 入口（API + 静态前端托管）。

启动：uvicorn src.app:app --host 127.0.0.1 --port 8322
（start.bat 会自动完成；直接 `python -m src.app` 也可以）

架构速览（供开源阅读）：
    src/
      app.py          本文件：HTTP 接口层（查询/统计/手动维护/爬虫触发）
      schema.py       数据模型：字段清单、默认值、人工字段保护白名单、校验
      storage.py      存储层：companies.json 读写（原子写）、快照备份、收件箱
      build_seed.py   种子数据 → 主库生成器（合并人工修改与爬虫动态）
      seed/           人工精编的企业种子数据（按方向分文件）
      crawler/
        base.py       抓取与解析原语（限速/UA/公告链接抽取）
        sources.py    数据源适配器（配置驱动，见 data/sources.json）
        matching.py   公司名归一化与标题匹配
        autocapture.py 新企业自动收录（校招信号 → 自动建档）
        merge.py      合并编排（字段保护规则在这层执行）
        runner.py     刷新任务编排（后台线程、分源容错、进度上报）
    web/              前端（原生 HTML/CSS/JS，无构建步骤，兼容老内核）
    data/             companies.json 主库 + sources.json 数据源配置 + snapshots/ 快照

数据流：种子 --build_seed--> companies.json <--爬虫合并-- 数据源
                                    ↑
                            人工修正（manual_overrides 保护）
"""
from __future__ import annotations

import json
import os
import threading
import traceback
from datetime import date, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import digest, keywords, linkcheck, schema, storage
from . import auth as auth_mod
from .crawler import archive, runner

WEB_DIR = Path(__file__).resolve().parents[1] / "web"
AUTH_FILE = Path(__file__).resolve().parents[1] / "data" / "auth.json"


def _load_auth() -> auth_mod.AuthManager:
    """data/auth.json 配置了 salt + password_sha256 才启用写接口鉴权；
    缺省关闭（本机开发行为不变）。公网部署必须配置。"""
    try:
        d = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        return auth_mod.AuthManager(d.get("salt"), d.get("password_sha256"))
    except (OSError, json.JSONDecodeError):
        return auth_mod.AuthManager(None, None)


AUTH = _load_auth()


async def require_auth(request: Request) -> None:
    if not AUTH.enabled:
        return
    token = (request.headers.get("Authorization") or "")
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]
    if not AUTH.check(token):
        raise HTTPException(401, "需要登录")


def _client_ip(request: Request) -> str:
    xff = request.headers.get("X-Forwarded-For") or ""
    return xff.split(",")[0].strip() if xff else (request.client.host if request.client else "?")


def schedule_reexport() -> None:
    """写操作后自动重生公网静态页（仅服务器设置了 EE_PUBLIC_INDEX 时）。

    后台线程执行，失败不影响写操作本身；导出内部用原子替换防半截文件。
    """
    target = os.environ.get("EE_PUBLIC_INDEX")
    if not target:
        return

    def _job():
        try:
            from .export_static import export_to
            out = export_to(target)
            print(f"[reexport] public page updated -> {out}")
        except Exception:  # noqa: BLE001 重发布失败不影响主流程
            traceback.print_exc()

    threading.Thread(target=_job, daemon=True, name="reexport").start()


app = FastAPI(title="电气秋招整合站", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])


# ---------------- 页面 ----------------

_index_cache: tuple | None = None


def _index_html() -> bytes:
    """首页：CSS/JS 内联成单响应。

    公网明文链路对新建连接有较高概率 RST（连接建立后复用则稳定），
    首屏压成 1 个请求可大幅提高弱链路下的加载成功率；SW 命中后二次访问走缓存。
    """
    global _index_cache
    names = ("index.html", "style.css", "sha256.js", "app.js")
    key = tuple((WEB_DIR / n).stat().st_mtime_ns for n in names)
    if _index_cache and _index_cache[0] == key:
        return _index_cache[1]
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    css = (WEB_DIR / "style.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="static/style.css">',
                        "<style>\n" + css + "\n</style>", 1)
    for js in ("sha256.js", "app.js"):
        code = (WEB_DIR / js).read_text(encoding="utf-8")
        # 防御：JS 源码（含注释/字符串）中若出现脚本闭合标签会让 HTML 解析器
        # 提前截断内联脚本块；\/ 在字符串与正则中均等价于 /，注释里也无害
        code = code.replace("</script>", "<\\/script>")
        html = html.replace('<script src="static/' + js + '"></script>',
                            "<script>\n" + code + "\n</script>", 1)
    body = html.encode("utf-8")
    _index_cache = (key, body)
    return body


@app.get("/")
def index():
    return Response(content=_index_html(), media_type="text/html; charset=utf-8")


@app.get("/manifest.webmanifest")
def pwa_manifest():
    return FileResponse(WEB_DIR / "manifest.webmanifest",
                        media_type="application/manifest+json")


@app.get("/sw.js")
def pwa_sw():
    return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


# ---------------- 查询 ----------------

def _filtered(params) -> list[dict]:
    companies = storage.load_companies()
    q = (params.q or "").strip().lower()
    if q:
        def hit(c):
            hay = " ".join([c["name"], c.get("alias", ""), c.get("industry", ""),
                            c.get("desc", ""), c.get("sub", ""), " ".join(c.get("positions", [])),
                            " ".join(c.get("cities", [])), " ".join(c.get("tags", []))]).lower()
            return q in hay
        companies = [c for c in companies if hit(c)]
    if params.batch:
        companies = [c for c in companies if params.batch in c.get("batch", [])]
    if params.cat:
        companies = [c for c in companies if c["cat"] == params.cat]
    if params.sub:
        companies = [c for c in companies if c.get("sub") == params.sub]
    if params.status:
        companies = [c for c in companies if c.get("status") == params.status]
    if params.year:
        companies = [c for c in companies if c.get("year") == params.year]
    if params.city:
        companies = [c for c in companies if any(params.city in x for x in c.get("cities", []))]
    if params.tag:
        companies = [c for c in companies if params.tag in c.get("tags", [])]
    if params.only_pinned:
        companies = [c for c in companies if c.get("pinned")]
    if params.only_applied:
        companies = [c for c in companies if c.get("applied")]

    def days_left(c):
        try:
            d = datetime.strptime(c["deadline"], "%Y-%m-%d").date()
            return (d - date.today()).days
        except Exception:  # noqa: BLE001
            return 9999

    if params.sort == "deadline":
        companies.sort(key=lambda c: days_left(c))
    elif params.sort == "updated":
        companies.sort(key=lambda c: c.get("updated_at") or "", reverse=True)
    elif params.sort == "name":
        companies.sort(key=lambda c: c["name"])
    else:  # recommend：重点推荐 > 对口度 > 进行中 > 名称
        tag_rank = {"S级对口": 0, "高度相关": 1, "相关": 2, "延伸方向": 3}
        status_rank = {"进行中": 0, "即将截止": 1, "常年招聘": 2, "未开启": 3, "未知": 4, "已结束": 5}

        def rank(c):
            tags = c.get("tags", [])
            t = min((tag_rank[x] for x in tags if x in tag_rank), default=9)
            return (0 if c.get("pinned") else 1, t,
                    status_rank.get(c.get("status"), 9), c["name"])
        companies.sort(key=rank)
    return companies


class FilterParams(BaseModel):
    q: str = ""
    batch: str = ""
    cat: str = ""
    sub: str = ""
    status: str = ""
    city: str = ""
    year: str = ""
    tag: str = ""
    only_pinned: bool = False
    only_applied: bool = False
    sort: str = "recommend"


@app.get("/api/companies")
def api_companies(params: FilterParams = Depends()):
    companies = _filtered(params)
    # 附上链接体检结果，前端给失效入口标红
    lc = linkcheck.load().get("results", {})
    for c in companies:
        st = lc.get(c.get("apply_url", ""))
        if st:
            c["link_status"] = st.get("state")
    return {"companies": companies}


@app.get("/api/companies/{company_id}")
def api_company_detail(company_id: str):
    for c in storage.load_companies():
        if c["id"] == company_id:
            return c
    raise HTTPException(404, "企业不存在")


@app.get("/api/stats")
def api_stats():
    companies = storage.load_companies()
    today = date.today()

    def dl_days(c):
        try:
            return (datetime.strptime(c["deadline"], "%Y-%m-%d").date() - today).days
        except Exception:  # noqa: BLE001
            return 9999

    return {
        "total": len(companies),
        "hiring": sum(1 for c in companies if c.get("status") in ("进行中", "常年招聘")),
        "autumn": sum(1 for c in companies if "秋招" in c.get("batch", [])),
        "intern": sum(1 for c in companies if "实习" in c.get("batch", [])),
        "closing": sum(1 for c in companies if c.get("status") == "即将截止" or 0 <= dl_days(c) <= 14),
        "pinned": sum(1 for c in companies if c.get("pinned")),
    }


@app.get("/api/meta")
def api_meta():
    refresh = runner.get_status()
    cats = schema.CATS
    return {
        "cats": cats, "batches": schema.BATCHES, "statuses": schema.STATUSES,
        "years": schema.YEARS, "tags": schema.TAGS, "sorts": schema.SORTS,
        "refresh": refresh, "today": date.today().isoformat(),
        "cities": _all_cities(),
    }


def _all_cities() -> list[str]:
    cities = set()
    for c in storage.load_companies():
        for x in c.get("cities", []):
            cities.add(x)
    return sorted(cities)


# ---------------- 应用内登录（写接口鉴权；查询保持公开） ----------------

@app.get("/api/auth/check")
def api_auth_check(request: Request):
    token = (request.headers.get("Authorization") or "")
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]
    return {"enabled": AUTH.enabled, "ok": AUTH.check(token)}


@app.get("/api/auth/challenge")
def api_auth_challenge(request: Request):
    try:
        nonce = AUTH.new_challenge(_client_ip(request))
    except PermissionError as e:
        raise HTTPException(429, str(e))
    return {"nonce": nonce, "salt": AUTH.salt}


class LoginBody(BaseModel):
    nonce: str = ""
    resp: str = ""


@app.post("/api/auth/login")
def api_auth_login(body: LoginBody):
    token = AUTH.login(body.nonce, body.resp)
    if not token:
        raise HTTPException(401, "密码错误或挑战已过期，请重试")
    return {"token": token}


# ---------------- 手动维护（写接口，鉴权开启时需登录） ----------------

class NewCompany(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    cat: str
    sub: str
    ctype: str = "民企"
    industry: str = ""
    batch: list[str] = ["秋招"]
    cities: list[str] = []
    apply_url: str = ""
    official_site: str = ""
    salary_text: str = ""
    desc: str = ""
    ee_notes: str = ""
    source_url: str = ""


@app.post("/api/companies")
def api_add_company(body: NewCompany, _: None = Depends(require_auth)):
    err = schema.is_valid_new_company(body.model_dump())
    if err:
        raise HTTPException(400, err)
    companies = storage.load_companies()
    base = schema.slugify(body.name)
    cid = base
    n = 2
    while any(c["id"] == cid for c in companies):
        cid = f"{base}-{n}"
        n += 1
    rec = schema.normalize({
        "id": cid, "name": body.name.strip(), "cat": body.cat, "sub": body.sub,
        "ctype": body.ctype or "民企", "industry": body.industry,
        "batch": body.batch or ["秋招"], "cities": body.cities,
        "apply_url": body.apply_url.strip(), "official_site": body.official_site.strip(),
        "salary_text": body.salary_text, "desc": body.desc, "ee_notes": body.ee_notes,
        "tags": ["相关"],
    })
    rec["sources"] = [{"type": "manual", "url": body.source_url or body.apply_url,
                       "date": date.today().isoformat()}]
    rec["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    companies.append(rec)
    storage.save_companies(companies)
    schedule_reexport()
    return {"ok": True, "id": cid}


@app.delete("/api/companies/{company_id}")
def api_delete_company(company_id: str, _: None = Depends(require_auth)):
    companies = storage.load_companies()
    target = next((c for c in companies if c["id"] == company_id), None)
    if not target:
        raise HTTPException(404, "企业不存在")
    companies = [c for c in companies if c["id"] != company_id]
    storage.save_companies(companies)
    # 自动收录的企业删除时记入黑名单，否则下次刷新公告还在会被再次收录
    if target.get("auto_added"):
        from .crawler.matching import company_keys
        storage.add_blocked(company_keys(target))
    schedule_reexport()
    return {"ok": True}


class PatchBody(BaseModel):
    fields: dict


@app.patch("/api/companies/{company_id}")
def api_patch_company(company_id: str, body: PatchBody, _: None = Depends(require_auth)):
    companies = storage.load_companies()
    target = next((c for c in companies if c["id"] == company_id), None)
    if not target:
        raise HTTPException(404, "企业不存在")
    changed = []
    for key, value in body.fields.items():
        if key not in schema.MANUAL_FIELDS:
            raise HTTPException(400, f"字段 {key} 不允许修改")
        target[key] = value
        if key not in target.get("manual_overrides", []):
            changed.append(key)
    if changed:
        target.setdefault("manual_overrides", []).extend(changed)
    target["updated_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    storage.save_companies(companies)
    schedule_reexport()
    return {"ok": True}


# ---------------- 每日简报 ----------------

@app.get("/api/digest")
def api_digest():
    """返回最新一次每日简报（由计划任务/内置调度/手动 CLI 生成）。"""
    d = digest.load_latest()
    if not d:
        raise HTTPException(404, "还没有简报，点一次「更新数据」或等待定时任务即可生成")
    return d


# ---------------- 关键词订阅 / 公告全文搜索 / 链接体检 ----------------

@app.get("/api/keywords")
def api_keywords_get():
    return {"keywords": keywords.load_keywords()}


class KeywordsBody(BaseModel):
    keywords: list[str] = Field(default_factory=list, max_length=30)


@app.post("/api/keywords")
def api_keywords_set(body: KeywordsBody, _: None = Depends(require_auth)):
    saved = keywords.save_keywords(body.keywords)
    return {"ok": True, "keywords": saved,
            "note": "关键词在下次生成简报时生效"}


@app.get("/api/search")
def api_search(q: str = ""):
    """公告全文搜索：搜正文存档里的「户口/专业要求/xx届」等细节。"""
    return {"results": archive.search(q)}


@app.get("/api/linkcheck")
def api_linkcheck():
    """链接体检结果汇总：失效/疑似防爬清单 + 统计。"""
    d = linkcheck.load()
    results = d.get("results", {})
    name_by_url = {c.get("apply_url", ""): c["name"] for c in storage.load_companies()}
    dead, suspect, ok = [], [], 0
    for url, v in results.items():
        item = {"url": url, "company": name_by_url.get(url, ""),
                "state": v.get("state"), "status": v.get("status"),
                "note": v.get("note", "")}
        if v.get("state") == "dead":
            dead.append(item)
        elif v.get("state") == "suspect":
            suspect.append(item)
        else:
            ok += 1
    return {"last_run": d.get("last_run"), "running": d.get("running") or linkcheck.is_running(),
            "ok": ok, "dead": dead, "suspect": suspect, "total": len(results)}


@app.post("/api/linkcheck/run")
def api_linkcheck_run(_: None = Depends(require_auth)):
    ok, msg = linkcheck.start_manual(storage.load_companies())
    if not ok:
        raise HTTPException(409, msg)
    return {"ok": True}


# ---------------- 收件箱（爬虫未匹配动态） ----------------

@app.get("/api/inbox")
def api_inbox():
    return {"items": storage.load_inbox()}


@app.delete("/api/inbox")
def api_inbox_delete(url: str, _: None = Depends(require_auth)):
    items = [i for i in storage.load_inbox() if i.get("url") != url]
    storage.save_inbox(items)
    return {"ok": True}


# ---------------- 爬虫更新 ----------------

@app.post("/api/refresh")
def api_refresh(_: None = Depends(require_auth)):
    ok, msg = runner.start_refresh()
    if not ok:
        raise HTTPException(409, msg)
    return {"ok": True, "status": runner.get_status()}


@app.get("/api/refresh/status")
def api_refresh_status():
    return runner.get_status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8322)


# ---------------- 内置每日调度（电脑开机且服务运行时自动补跑当天更新） ----------------

def _daily_loop() -> None:
    """每 30 分钟检查一次：过了 DIGEST_HOUR 且今天还没生成简报，就跑一次更新。"""
    import time as _time
    _time.sleep(120)  # 等服务先起稳
    while True:
        try:
            latest = digest.load_latest() or {}
            gen_day = (latest.get("generated") or "")[:10]
            now = datetime.now()
            if (gen_day != now.strftime("%Y-%m-%d")
                    and now.hour >= digest.DIGEST_HOUR
                    and not runner.is_running()):
                before = storage.load_companies()
                summary = runner.run_sync()
                after = storage.load_companies()
                digest.save(digest.build(before, after, summary))
        except Exception:  # noqa: BLE001 调度失败不影响网站本身
            traceback.print_exc()
        _time.sleep(1800)


threading.Thread(target=_daily_loop, daemon=True, name="daily-scheduler").start()
