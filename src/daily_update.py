# -*- coding: utf-8 -*-
"""每日定时更新入口：抓取 → 入库 → 生成增量简报。

触发方式（二选一即可，先到先得，简报当天只生成一份）：
    1. Windows 计划任务：每天 08:00 调用本模块（见 daily_task.bat，
       注册命令：schtasks /Create /SC DAILY /ST 08:00 ...）
    2. 网站后端内置守护线程（src/app.py）：服务运行中且当天 8 点后
       尚未生成简报时自动补跑

微信推送暂未接入；简报在网页右上角「📋 今日简报」查看。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import digest, linkcheck, storage  # noqa: E402
from src.crawler import runner  # noqa: E402


def main() -> None:
    before = storage.load_companies()
    summary = runner.run_sync()
    after = storage.load_companies()
    d = digest.build(before, after, summary)
    digest.save(d)
    s = d["stats"]
    print(f"[daily] 抓取 {s['fetched']} 条 | 匹配 {s['matched']} | "
          f"新企业 {s['auto_added']} | 收件箱 +{s['inbox_new']} | "
          f"简报 → data/digest/latest.json")
    # 链接健康周检：距上次 ≥7 天才真正跑
    if linkcheck.run_weekly_if_due(after):
        lc = linkcheck.load()
        dead = sum(1 for v in lc.get("results", {}).values() if v.get("state") == "dead")
        print(f"[daily] 链接周检完成：发现 {dead} 个疑似失效入口（详见网页「链接体检」）")


if __name__ == "__main__":
    main()
