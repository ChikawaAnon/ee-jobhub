# -*- coding: utf-8 -*-
"""种子数据条目构造助手。只写与默认值不同的字段，保持种子文件精简。"""
from __future__ import annotations


def S(id: str, name: str, cat: str, sub: str, ctype: str, industry: str, **kw) -> dict:
    rec = {
        "id": id,
        "name": name,
        "cat": cat,
        "sub": sub,
        "ctype": ctype,
        "industry": industry,
    }
    for k, v in kw.items():
        if v not in (None, "", []):
            rec[k] = v
    return rec
