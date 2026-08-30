# -*- coding: utf-8 -*-
"""关键词订阅：用户关注的关键词（如 继保/南网/湛江），每日简报生成时
把命中的公告/企业置顶到「⭐ 命中你的关键词」栏目。

存储：data/keywords.json（服务端存，因为简报由定时任务在后台生成）
首次运行自动写入一组默认关键词。
"""
from __future__ import annotations

import json
from pathlib import Path

from . import storage

KEYWORDS_PATH = storage.DATA_DIR / "keywords.json"
DEFAULT_KEYWORDS = ["电气", "湛江", "南网", "继保", "汇川"]


def load_keywords() -> list[str]:
    if not KEYWORDS_PATH.exists():
        save_keywords(list(DEFAULT_KEYWORDS))
        return list(DEFAULT_KEYWORDS)
    try:
        return json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 文件损坏时回退默认值
        return list(DEFAULT_KEYWORDS)


def save_keywords(keywords: list[str]) -> list[str]:
    """清洗去重后保存，返回清洗结果。"""
    cleaned: list[str] = []
    for k in keywords:
        k = str(k).strip()
        if k and k not in cleaned:
            cleaned.append(k)
    KEYWORDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEYWORDS_PATH.write_text(json.dumps(cleaned, ensure_ascii=False, indent=1),
                             encoding="utf-8")
    return cleaned


def match(text: str, keywords: list[str]) -> list[str]:
    """返回 text 中命中的关键词列表（顺序与订阅顺序一致）。"""
    return [k for k in keywords if k and k in text]
