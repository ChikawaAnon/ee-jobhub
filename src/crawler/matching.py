# -*- coding: utf-8 -*-
"""公司名匹配模块：把公告标题对应到库内企业。

原理：把企业名/别名做「去修饰」归一化（去掉 股份/有限/集团/公司/届别年份 等
通用词），然后在归一化后的标题里做包含匹配，命中关键词越长越可信。

示例：
    库内企业「国家电网」别名「国网」
    公告标题「国网江苏省电力有限公司2027年校园招聘」
    → 归一化标题包含「国网」 → 匹配成功
"""
from __future__ import annotations

# 归一化时剔除的通用修饰词（顺序无关，全部子串替换）
_STRIP = ("股份有限公司", "有限责任公司", "有限公司", "控股集团", "集团", "股份",
          "校园招聘", "秋季招聘", "春季招聘", "2027届", "2026届", "2027", "2026",
          "（", "）", "(", ")", "中国")


def normalize_text(s: str) -> str:
    """去掉企业名/标题里的通用修饰词，得到可比对的短键。"""
    for w in _STRIP:
        s = s.replace(w, "")
    return s


def company_keys(company: dict) -> list[str]:
    """取一个企业的全部可匹配短键（正式名 + 简称，长度≥2 才有效）。"""
    keys = []
    for raw in (company.get("name"), company.get("alias")):
        if not raw:
            continue
        k = normalize_text(raw)
        if len(k) >= 2:
            keys.append(k)
    return keys


def match_company(title: str, companies: list[dict]) -> dict | None:
    """标题 → 最佳匹配企业；多个命中时取关键词最长的那家（更具体）。"""
    norm_title = normalize_text(title)
    best, best_len = None, 0
    for c in companies:
        for k in company_keys(c):
            if k in norm_title and len(k) > best_len:
                best, best_len = c, len(k)
    return best
