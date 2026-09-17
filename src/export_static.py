# -*- coding: utf-8 -*-
"""把当前数据导出为单文件只读静态页（公网部署 / 离线分享共用）。

用法：
    python -m src.export_static --out /path/to/index.html

导出规则与网页「离线完整版」（web/app.js buildOfflineHTML）一致：
内嵌 window.STATIC_DATA、替换 /static/style.css 与 /static/app.js 外链。
导出页无后端能力，body.static 会隐藏「更新数据 / 提交上新 / 收件箱」等
后端入口；仅依赖服务器数据/接口的三个按钮额外用 CSS 隐藏。

默认只写到 data/digest/public_index.html，覆盖公网文件必须显式传 --out，
避免误覆盖。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.schema import BATCHES, CATS, SORTS, STATUSES, TAGS, YEARS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

# 公网只读页没有后端，全文搜索/链接体检/简报这三个按钮依赖服务器数据或长耗时接口
HIDE_BUTTONS_CSS = (
    "body.static #btn-digest, body.static #btn-search, "
    "body.static #btn-linkcheck { display: none !important; }"
)

CSS_LINK = '<link rel="stylesheet" href="static/style.css">'
JS_TAG = '<script src="static/app.js"></script>'


def export_to(out_path: str, data_path: str | None = None, stamp: str | None = None) -> Path:
    """供编程调用（如写入接口后自动重发布）。返回输出路径，自检失败抛 SystemExit。"""
    data_file = Path(data_path) if data_path else ROOT / "data" / "companies.json"
    companies = json.loads(data_file.read_text(encoding="utf-8"))
    stamp = stamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    html = build_html(companies, stamp)
    err = verify(html)
    if err:
        raise SystemExit("导出自检未通过：" + err)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 原子替换：避免与每日 cron 导出并发时写出半截文件
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(html, encoding="utf-8")
    tmp.replace(out)
    return out


def build_html(companies: list, stamp: str) -> str:
    # applied 是个人投递标记，不进公开分享页
    public_companies = [{k: v for k, v in c.items() if k != "applied"} for c in companies]
    payload = {
        "generated": stamp,
        "meta": {
            "cats": CATS,
            "batches": BATCHES,
            "statuses": STATUSES,
            "years": YEARS,
            "tags": TAGS,
            "sorts": SORTS,
        },
        "companies": public_companies,
    }
    # JSON 里 </  全转义，防止数据里的字符串提前闭合脚本块
    data_js = "window.STATIC_DATA=" + json.dumps(
        payload, ensure_ascii=False).replace("</", "<\\/") + ";"
    # 内嵌 app.js 源码含 </script> 字面量，必须转义（与前端 escScript 同规则）
    js = re.sub(r"</script>", r"<\\/script>", (WEB / "app.js").read_text(encoding="utf-8"),
                flags=re.IGNORECASE)
    css = (WEB / "style.css").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")

    if CSS_LINK not in html:
        raise SystemExit("css link not found in web/index.html")
    if JS_TAG not in html:
        raise SystemExit("js tag not found in web/index.html")
    # 离线分享页是纯只读快照，不需要登录脚本（sha256.js），直接剔除保持单文件自包含
    html = html.replace('<script src="static/sha256.js"></script>', "", 1)
    html = html.replace(CSS_LINK, "<style>\n" + css + "\n</style>", 1)
    html = html.replace(
        JS_TAG,
        "<script>\n" + data_js + "\n</script>\n<script>\n" + js + "\n</script>",
        1,
    )
    head_close = "</head>"
    if head_close in html:
        html = html.replace(head_close, "<style>" + HIDE_BUTTONS_CSS + "</style>" + head_close, 1)
    return html


def verify(html: str) -> str | None:
    """导出自检，返回错误说明或 None。"""
    if "window.STATIC_DATA=" not in html:
        return "数据块缺失"
    if "<script src=" in html:
        return "外链脚本未替换干净"
    closers = re.findall(r"</script>", html, flags=re.IGNORECASE)
    if len(closers) != 2:
        return f"脚本块数量异常（{len(closers)}，应为 2）"
    if HIDE_BUTTONS_CSS not in html:
        return "隐藏按钮 CSS 缺失"
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="导出单文件只读静态页")
    ap.add_argument("--out", default=str(ROOT / "data" / "digest" / "public_index.html"),
                    help="输出路径（默认 data/digest/public_index.html）")
    ap.add_argument("--data", default=str(ROOT / "data" / "companies.json"),
                    help="企业数据文件（默认 data/companies.json）")
    args = ap.parse_args()

    out = export_to(args.out, args.data)
    # 溯源信息：重新读一次数据统计家数
    companies = json.loads(Path(args.data).read_text(encoding="utf-8"))
    print(f"[export] {len(companies)} 家企业 -> {out} "
          f"({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
