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


def _dedup(srcs: list[dict]) -> list[dict]:
    """按 link 去重支撑来源（同一页面可能被多次匹配）。"""
    seen, out = set(), []
    for s in srcs:
        if s["link"] and s["link"] not in seen:
            seen.add(s["link"])
            out.append(s)
    return out


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

    return {"E": E, "I": I,
            "E_sources": _dedup(E_srcs), "I_sources": _dedup(I_srcs)}


# ---------------------------------------------------------------------------
# 管道绝对粗糙度（pipe_flow 的 ε）
# ---------------------------------------------------------------------------

def _extract_roughness(text: str) -> list[float]:
    """从文本提取绝对粗糙度候选值 [m]（钢管 ε 常见 0.015~0.2 mm）。

    识别毫米（`0.045 mm`）与微米（`45 µm` / `45 um` / `45 microns`）两种写法。
    范围外（混凝土、铸铁管等数量级差异大）剔除，避免跨管材污染共识。
    """
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*mm\b", text, re.I):
        v = float(m.group(1)) * 1e-3
        if 1e-5 <= v <= 5e-4:
            out.append(v)
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:µm|μm|um)\b|(\d+(?:\.\d+)?)\s*microns?\b",
                         text, re.I):
        v = float(m.group(1) or m.group(2)) * 1e-6
        if 1e-5 <= v <= 5e-4:
            out.append(v)
    return out


def lookup_pipe_roughness(api_key: str | None = None, num: int = 5,
                          material: str = "steel") -> dict:
    """搜索管道绝对粗糙度并多源交叉，返回 {"epsilon", "epsilon_sources"}。"""
    results: list[dict] = []
    for q in (f"{material} pipe absolute roughness epsilon mm",
              "commercial steel pipe roughness mm"):
        results.extend(search(q, api_key=api_key, num=num))
    hits = []
    for r in results:
        text = f"{r['title']} {r['snippet']}"
        src = {"title": r["title"], "link": r["link"]}
        for v in _extract_roughness(text):
            hits.append((v, src))
    eps, eps_srcs = _consensus(hits, 1e-5, 5e-4, 0.3)
    return {"epsilon": eps, "epsilon_sources": _dedup(eps_srcs)}


# ---------------------------------------------------------------------------
# 材料热扩散系数（heat 的 α）
# ---------------------------------------------------------------------------

def _extract_diffusivity(text: str, lo: float = 5e-6, hi: float = 5e-5) -> list[float]:
    """从文本提取热扩散系数候选值 [m²/s]（钢 α 常见 ~1.17e-5）。

    识别三种写法：`1.17×10⁻⁵ m²/s`（上标归一化）、`1.17e-5 m2/s`、
    `11.7 mm²/s`（mm²/s 转 m²/s 乘 1e-6，钢常见写法）。范围按材料过滤防污染。
    """
    text = text.translate(str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+"))
    out = []
    # 10 的幂：1.17×10⁻⁵ m²/s / 1.17x10-5 m2/s
    for m in re.finditer(
        r"(\d+(?:\.\d+)?)\s*(?:[×x*]\s*)?10\s*\^?\s*([-+−]?\d+)\s*m\s*\^?\s*2\s*/?\s*s\b",
        text, re.I):
        v = float(m.group(1)) * 10.0 ** int(m.group(2))
        if lo <= v <= hi:
            out.append(v)
    # 直接科学记法：1.17e-5 m2/s
    for m in re.finditer(r"(\d+(?:\.\d+)?e[-+−]?\d+)\s*m\s*\^?\s*2\s*/?\s*s\b", text, re.I):
        v = float(m.group(1))
        if lo <= v <= hi:
            out.append(v)
    # 毫米平方：11.7 mm²/s / 11.7 mm^2/s
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*mm\s*\^?\s*2\s*/?\s*s\b", text, re.I):
        v = float(m.group(1)) * 1e-6
        if lo <= v <= hi:
            out.append(v)
    return out


def lookup_heat_material(api_key: str | None = None, num: int = 5,
                         material: str = "steel") -> dict:
    """搜索某材料热扩散系数并多源交叉，返回 {"alpha", "alpha_sources"}。

    material 决定提取范围（钢/铝/铜热扩散差一个量级，跨材料聚簇会失真），
    只认已收录材料，未收录回退钢的范围。
    """
    ranges = {"steel": (5e-6, 5e-5), "aluminum": (3e-5, 2e-4), "copper": (5e-5, 3e-4)}
    lo, hi = ranges.get(str(material).lower(), ranges["steel"])
    results: list[dict] = []
    for q in (f"thermal diffusivity of {material} m2/s",
              f"{material} thermal diffusivity m^2/s"):
        results.extend(search(q, api_key=api_key, num=num))
    hits = []
    for r in results:
        text = f"{r['title']} {r['snippet']}"
        src = {"title": r["title"], "link": r["link"]}
        for v in _extract_diffusivity(text, lo, hi):
            hits.append((v, src))
    alpha, alpha_srcs = _consensus(hits, lo, hi, 0.1)
    return {"alpha": alpha, "alpha_sources": _dedup(alpha_srcs)}


# ---------------------------------------------------------------------------
# RC 常用元件值（rc_circuit 的 R / C）
# ---------------------------------------------------------------------------

def _extract_resistance(text: str) -> list[float]:
    """从文本提取电阻候选值 [Ω]（常见 10 Ω ~ 1 MΩ）。识别 kΩ / kOhm / MΩ 前缀。"""
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([kKmM])?\s*(?:Ω|Ohm|ohm|Ω)", text):
        v = float(m.group(1)) * {"k": 1e3, "K": 1e3, "M": 1e6, "m": 1e3}.get(m.group(2) or "", 1.0)
        if 10.0 <= v <= 1e6:
            out.append(v)
    return out


def _extract_capacitance(text: str) -> list[float]:
    """从文本提取电容候选值 [F]（常见 nF ~ mF）。识别 µF / uF / mF / microfarad。"""
    out = []
    mult = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3}
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([pnµmμu])?\s*F\b", text, re.I):
        unit = (m.group(2) or "").lower()
        v = float(m.group(1)) * mult.get(unit, 1.0)
        if 1e-9 <= v <= 1e-2:
            out.append(v)
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*microfarads?\b", text, re.I):
        v = float(m.group(1)) * 1e-6
        if 1e-9 <= v <= 1e-2:
            out.append(v)
    return out


def lookup_rc_components(api_key: str | None = None, num: int = 5) -> dict:
    """搜索 RC 电路常用元件值并多源交叉，返回 {"R","C","R_sources","C_sources"}。"""
    results: list[dict] = []
    for q in ("RC timing circuit common resistor value kOhm",
              "RC timer typical capacitor value microfarad"):
        results.extend(search(q, api_key=api_key, num=num))
    R_hits, C_hits = [], []
    for r in results:
        text = f"{r['title']} {r['snippet']}"
        src = {"title": r["title"], "link": r["link"]}
        for v in _extract_resistance(text):
            R_hits.append((v, src))
        for v in _extract_capacitance(text):
            C_hits.append((v, src))
    R, R_srcs = _consensus(R_hits, 10.0, 1e6, 0.2)
    C, C_srcs = _consensus(C_hits, 1e-9, 1e-2, 0.2)
    return {"R": R, "C": C,
            "R_sources": _dedup(R_srcs), "C_sources": _dedup(C_srcs)}



# ---------------------------------------------------------------------------
# 材料许用应力（vessel 的 sigma_allow）
# ---------------------------------------------------------------------------

def _extract_allowable_stress(text: str) -> list[float]:
    """从文本提取许用应力候选值 [Pa]（ASME 碳钢容器常见 50~200 MPa）。

    先找所有「数字+单位」候选，再检查该数字前方文本是否含 allowable/design/
    working/许用 上下文——屈服强度、抗拉强度等无上下文值（通常高一档）自然剔除，
    避免污染共识。支持 MPa / ksi / psi / N/mm²。
    """
    mult = {"mpa": 1e6, "ksi": 6.894757e6, "psi": 6894.757, "n/mm2": 1e6, "n/mm²": 1e6}
    out = []
    for m in re.finditer(
        r"(\d[\d,]*(?:\.\d+)?)\s*(MPa|ksi|psi|N/mm2|N/mm²)", text, re.I):
        v = float(m.group(1).replace(",", "")) * mult.get(m.group(2).lower(), 1.0)
        if not (30e6 <= v <= 400e6):
            continue
        pre = text[max(0, m.start() - 60):m.start()]
        if re.search(r"allowable|design|working|许用|许可", pre, re.I):
            out.append(v)
    return out


def lookup_vessel_material(api_key: str | None = None, num: int = 5,
                           material: str = "carbon steel") -> dict:
    """搜索某容器材料许用应力并多源交叉，返回 {"sigma_allow", "sigma_allow_sources"}。"""
    results: list[dict] = []
    for q in (f"{material} allowable stress MPa",
              "pressure vessel material allowable stress MPa"):
        results.extend(search(q, api_key=api_key, num=num))
    hits = []
    for r in results:
        text = f"{r['title']} {r['snippet']}"
        src = {"title": r["title"], "link": r["link"]}
        for v in _extract_allowable_stress(text):
            hits.append((v, src))
    sig, sig_srcs = _consensus(hits, 30e6, 400e6, 0.2)
    return {"sigma_allow": sig, "sigma_allow_sources": _dedup(sig_srcs)}
