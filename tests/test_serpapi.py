"""SerpApi 多源交叉提取测试 —— 搜 → 提取候选值 → 共识 + 来源标注。

C5 深度工作流三段逻辑分别锁：
1. _extract_e / _extract_i：从真实片段样式提取候选值（含单位换算 mm⁴→m⁴）
2. _consensus：多源聚簇取中位数 + 支撑来源；无候选回退 None
3. lookup_beam_material：多查询汇总 → 共识 + 去重来源；API 失败抛错
"""
import pytest

from agent import serpapi


# ---------------- 提取：弹性模量 E ----------------

def test_extract_e_gpa():
    text = "The elastic modulus of structural steel is 200 GPa, Young's modulus 205 GPa."
    assert [v / 1e9 for v in serpapi._extract_e(text)] == [200.0, 205.0]


def test_extract_e_mpa_with_commas():
    text = "E = 200,000 MPa for grade 355 steel."
    assert [v / 1e9 for v in serpapi._extract_e(text)] == [200.0]


def test_extract_e_filters_other_materials():
    text = "Aluminum 70 GPa, steel 200 GPa, concrete 30 GPa."
    assert [v / 1e9 for v in serpapi._extract_e(text)] == [200.0]


def test_extract_e_no_match():
    assert serpapi._extract_e("nothing here") == []
    assert serpapi._extract_e("") == []


# ---------------- 提取：截面惯性矩 I ----------------

def test_extract_i_scientific_mm4():
    text = "IPE200 Ix = 5.7×10⁶ mm⁴"           # 5.7e6 mm⁴ = 5.7e-6 m⁴
    vals = serpapi._extract_i(text)
    assert len(vals) == 1
    assert abs(vals[0] - 5.7e-6) < 1e-12


def test_extract_i_direct_m4():
    assert serpapi._extract_i("moment of inertia I = 0.0005 m⁴") == [5e-4]


def test_extract_i_e_notation():
    assert serpapi._extract_i("second moment of area 5e-4 m4") == [5e-4]


def test_extract_i_cm4():
    assert serpapi._extract_i("I = 830 cm⁴") == [830e-8]


def test_extract_i_no_match():
    assert serpapi._extract_i("the width is 10 m and length 5 m") == []
    assert serpapi._extract_i("") == []


# ---------------- 共识：多源交叉 ----------------

def test_consensus_agrees_on_median():
    vals = [(200e9, {"title": "a", "link": "/a"}),
            (205e9, {"title": "b", "link": "/b"}),
            (193e9, {"title": "c", "link": "/c"})]
    med, srcs = serpapi._consensus(vals, 150e9, 260e9, 0.05)
    assert abs(med - 200e9) < 1e6                 # 三值都在 200±5% → 中位数
    assert len(srcs) == 3


def test_consensus_single_value_accepted():
    med, srcs = serpapi._consensus([(198e9, {"title": "x", "link": "/x"})], 150e9, 260e9, 0.05)
    assert med == 198e9 and len(srcs) == 1


def test_consensus_no_values_returns_none():
    assert serpapi._consensus([], 0, 1, 0.1) == (None, [])


def test_consensus_out_of_range_filtered():
    assert serpapi._consensus([(70e9, {"title": "a", "link": "/a"})], 150e9, 260e9, 0.05) == (None, [])


# ---------------- 完整工作流 ----------------

def test_lookup_beam_material_crosschecks_sources(monkeypatch):
    fake = [
        {"title": "Steel Modulus", "snippet": "structural steel elastic modulus is 200 GPa",
         "link": "https://ex.com/1"},
        {"title": "Young's modulus", "snippet": "A36 steel Young's modulus 200 GPa",
         "link": "https://ex.com/2"},
        {"title": "IPE section", "snippet": "IPE200 Ix = 5.7×10⁶ mm⁴",
         "link": "https://ex.com/3"},
        {"title": "noise", "snippet": "today's weather is warm", "link": "https://ex.com/4"},
    ]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    out = serpapi.lookup_beam_material(api_key="k")
    assert abs(out["E"] - 200e9) < 1e6
    assert len(out["E_sources"]) == 2
    assert abs(out["I"] - 5.7e-6) < 1e-12
    assert len(out["I_sources"]) == 1


def test_lookup_beam_material_no_consensus(monkeypatch):
    fake = [{"title": "a", "snippet": "nothing relevant here", "link": "/a"},
            {"title": "b", "snippet": "more noise", "link": "/b"}]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    out = serpapi.lookup_beam_material(api_key="k")
    assert out["E"] is None and out["I"] is None
    assert out["E_sources"] == [] and out["I_sources"] == []


def test_lookup_raises_without_key(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    with pytest.raises(ValueError):
        serpapi.lookup_beam_material(api_key=None)
