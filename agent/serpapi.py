"""SerpApi 参数搜索: 用真实工程参数辅助计算。

场景: 用户说"钢结构横梁"但没给 E/I —— 用 SerpApi 搜真实材料参数。
M3 深度集成: SerpApi 是产品工作流一环，不是装饰。

C5 深度工作流: 搜 → 从片段提取候选值 → 多源交叉共识 → 预填 + 来源标注。
搜索/提取/共识任何一环失败，调用方回退内置典型值（不阻塞用户）。
"""
from __future__ import annotations

import os
import re

import numpy as np
import requests


def search(query: str, api_key: str | None = None, num: int = 3) -> list[dict]:
    """搜索并返回前 num 条结果 [{title, snippet, link}]。缺 key 抛 ValueError。"""
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        raise ValueError("缺少 SERPAPI_KEY（环境变量或参数）")
    resp = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": key, "num": num},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": it.get("title", ""), "snippet": it.get("snippet", ""), "link": it.get("link", "")}
        for it in data.get("organic_results", [])[:num]
    ]


# ---------------------------------------------------------------------------
# 多源交叉提取（C5）
# ---------------------------------------------------------------------------

def _extract_e(text: str) -> list[float]:
    """从文本提取弹性模量候选值（钢 E 常见 150~260 GPa），返回 [Pa, ...]。

    识别两种写法：`200 GPa` / `205GPa`，以及 `200,000 MPa`。
    范围外的（铝 70 GPa 等）剔除，避免不同材料污染共识。
    """
    out = []
    for m in re.finditer(r"(\d{2,3}(?:\.\d+)?)\s*(?:G\s*Pa|GPa)", text, re.I):
        v = float(m.group(1))
        if 150 <= v <= 260:
            out.append(v * 1e9)
    for m in re.finditer(r"(\d{1,3}(?:,\d{3}){1,2}(?:\.\d+)?)\s*MPa", text, re.I):
        v = float(m.group(1).replace(",", ""))
        if 150_000 <= v <= 260_000:
            out.append(v * 1e6)
    return out


def _extract_i(text: str) -> list[float]:
    """从文本提取截面惯性矩候选值（常见 1e-8 ~ 1e-2 m⁴），返回 [m⁴, ...]。

    识别 m⁴ / cm⁴ / mm⁴ 三种单位（mm⁴ 转 1e-12、cm⁴ 转 1e-8），科学计数与
    直接小数都吃：`5.7×10⁶ mm⁴`、`0.0005 m⁴`、`5e-4 m4`、`830 cm⁴`。
    """
    out = []
    mult = {"mm": 1e-12, "cm": 1e-8, "m": 1.0}
    # 片段里常见上标写法（5.7×10⁶ mm⁴），先归一化成普通数字再匹配
    text = text.translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-"))
    # 科学计数：5.7×10⁶ mm⁴ / 5e-4 m^4
    for m in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(?:[×x*]\s*)?10\s*\^?\s*([-+−]?\d+)\s*(mm|cm|m)\s*\^?\s*4",
        text, re.I):
        v = float(m.group(1)) * 10.0 ** int(m.group(2)) * mult[m.group(3).lower()]
        if 1e-8 <= v <= 1e-2:
            out.append(v)
    # 直接小数/科学记法：0.0005 m⁴ / 5e-04 m4
    for m in re.finditer(
        r"(\d+(?:\.\d+)?(?:[eE][-+−]?\d+)?)\s*(mm|cm|m)\s*\^?\s*4", text, re.I):
        v = float(m.group(1)) * mult[m.group(2).lower()]
        if 1e-8 <= v <= 1e-2:
            out.append(v)
    return out


def _consensus(values: list[tuple[float, dict]], lo: float, hi: float,
               tol: float) -> tuple[float, list[dict]]:
    """多源交叉：值落在 [lo, hi]，按相对容差 tol 聚簇，取最大簇中位数。

    返回 (共识值, 支撑来源列表)；无任何候选返回 (None, [])。
    多个来源给出接近值 → 可信；只有孤值也接受（来源列表至少一条）。
    """
    vals = [(v, src) for v, src in values if lo <= v <= hi]
    if not vals:
        return None, []
    # 以每个候选为锚聚簇，取成员最多的簇（并列取第一个）
    best_anchor = vals[0][0]
    best_len = -1
    for v, _ in vals:
        n = sum(1 for vs, _ in vals if abs(vs - v) <= tol * v)
        if n > best_len:
            best_len, best_anchor = n, v
    cluster = [vs for vs, _ in vals if abs(vs - best_anchor) <= tol * best_anchor]
    med = float(np.median(cluster))
    srcs = [s for vs, s in vals if abs(vs - med) <= tol * med]
    return med, srcs


def lookup_beam_material(api_key: str | None = None, num: int = 5) -> dict:
    """搜索钢梁典型 E/I 并多源交叉，返回共识值与支撑来源。

    返回 {"E": float|None, "I": float|None,
          "E_sources": [{"title","link"}, ...], "I_sources": [...]}。
    提取不到共识值 → 对应字段为 None（调用方回退内置典型值）。
    网络/API 失败直接抛异常（调用方 try/except 回退）。
    """
    results: list[dict] = []
    for q in ("steel structural beam elastic modulus GPa",
              "steel I-beam section moment of inertia m^4"):
        results.extend(search(q, api_key=api_key, num=num))

    E_hits, I_hits = [], []
    for r in results:
        text = f"{r['title']} {r['snippet']}"
        src = {"title": r["title"], "link": r["link"]}
        for v in _extract_e(text):
            E_hits.append((v, src))
        for v in _extract_i(text):
            I_hits.append((v, src))

    E, E_srcs = _consensus(E_hits, 150e9, 260e9, 0.05)
    I, I_srcs = _consensus(I_hits, 1e-8, 1e-2, 0.15)

    def dedup(srcs):
        seen, out = set(), []
        for s in srcs:
            if s["link"] and s["link"] not in seen:
                seen.add(s["link"])
                out.append(s)
        return out

    return {"E": E, "I": I,
            "E_sources": dedup(E_srcs), "I_sources": dedup(I_srcs)}
