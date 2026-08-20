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


# ---------------- 提取：管道绝对粗糙度 ε ----------------

def test_extract_roughness_mm():
    text = "commercial steel pipe absolute roughness 0.045 mm"
    assert [v * 1e3 for v in serpapi._extract_roughness(text)] == [0.045]


def test_extract_roughness_microns():
    text = "steel pipe roughness 45 µm"
    assert abs(serpapi._extract_roughness(text)[0] - 45e-6) < 1e-12


def test_extract_roughness_um_spelling():
    assert abs(serpapi._extract_roughness("roughness 45 um")[0] - 45e-6) < 1e-12


def test_extract_roughness_filters_other_pipes():
    # 混凝土管 1.5 mm 在钢管范围外 → 剔除，避免跨管材污染
    assert serpapi._extract_roughness("concrete pipe roughness 1.5 mm") == []


# ---------------- 提取：材料热扩散系数 α ----------------

def test_extract_diffusivity_scientific():
    text = "thermal diffusivity of steel 1.17e-5 m2/s"
    vals = serpapi._extract_diffusivity(text)
    assert len(vals) == 1
    assert abs(vals[0] - 1.17e-5) < 1e-9


def test_extract_diffusivity_superscript():
    text = "α = 1.17×10⁻⁵ m²/s"
    vals = serpapi._extract_diffusivity(text)
    assert abs(vals[0] - 1.17e-5) < 1e-9


def test_extract_diffusivity_mm2_per_s():
    text = "steel thermal diffusivity 11.7 mm2/s"     # 11.7 mm²/s = 1.17e-5 m²/s
    vals = serpapi._extract_diffusivity(text)
    assert abs(vals[0] - 1.17e-5) < 1e-9


def test_extract_diffusivity_range_filters_aluminum():
    # 钢范围 [5e-6, 5e-5]：铝 8.4e-5 应被剔除，只留钢值
    text = "aluminum 84e-6 m2/s steel 1.17e-5 m2/s"
    vals = serpapi._extract_diffusivity(text, 5e-6, 5e-5)
    assert len(vals) == 1 and abs(vals[0] - 1.17e-5) < 1e-9


# ---------------- 提取：电阻 R / 电容 C ----------------

def test_extract_resistance_kohm():
    assert abs(serpapi._extract_resistance("typical value 10 kΩ resistor")[0] - 10e3) < 1e-6


def test_extract_resistance_plain_ohm():
    assert serpapi._extract_resistance("1000 Ω") == [1000.0]


def test_extract_resistance_megaohm():
    assert abs(serpapi._extract_resistance("1 MΩ")[0] - 1e6) < 1e-6


def test_extract_capacitance_microfarad():
    assert abs(serpapi._extract_capacitance("common value 100 µF capacitor")[0] - 100e-6) < 1e-12


def test_extract_capacitance_uf_spelling():
    assert abs(serpapi._extract_capacitance("10 uF")[0] - 10e-6) < 1e-12


def test_extract_capacitance_millifarad():
    assert abs(serpapi._extract_capacitance("1 mF")[0] - 1e-3) < 1e-12


def test_extract_capacitance_word():
    assert abs(serpapi._extract_capacitance("100 microfarad")[0] - 100e-6) < 1e-12


# ---------------- 完整工作流：三场景查参 ----------------

def test_lookup_pipe_roughness_crosschecks(monkeypatch):
    fake = [
        {"title": "Roughness", "snippet": "commercial steel pipe absolute roughness 0.045 mm",
         "link": "https://ex.com/p1"},
        {"title": "Moody", "snippet": "steel pipe roughness 45 µm typical",
         "link": "https://ex.com/p2"},
        {"title": "noise", "snippet": "pipe length 100 m", "link": "https://ex.com/p3"},
    ]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    out = serpapi.lookup_pipe_roughness(api_key="k")
    assert abs(out["epsilon"] - 45e-6) < 1e-9
    assert len(out["epsilon_sources"]) >= 1


def test_lookup_heat_material_crosschecks(monkeypatch):
    fake = [
        {"title": "Diff", "snippet": "thermal diffusivity of steel 1.17e-5 m2/s",
         "link": "https://ex.com/h1"},
        {"title": "Thermo", "snippet": "steel α = 1.17×10⁻⁵ m²/s",
         "link": "https://ex.com/h2"},
    ]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    out = serpapi.lookup_heat_material(api_key="k")
    assert abs(out["alpha"] - 1.17e-5) < 1e-9
    assert len(out["alpha_sources"]) == 2


def test_lookup_heat_material_aluminum_range(monkeypatch):
    fake = [{"title": "a", "snippet": "aluminum thermal diffusivity 8.4e-5 m2/s",
             "link": "https://ex.com/a1"},
            {"title": "b", "snippet": "aluminum 8.5e-5 m2/s", "link": "https://ex.com/a2"}]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    out = serpapi.lookup_heat_material(api_key="k", material="aluminum")
    assert abs(out["alpha"] - 8.45e-5) < 1e-8
    assert len(out["alpha_sources"]) == 2


def test_lookup_rc_components_crosschecks(monkeypatch):
    fake = [
        {"title": "timer", "snippet": "use a 10 kΩ resistor and 100 µF capacitor for a 1 s timer",
         "link": "https://ex.com/r1"},
        {"title": "555", "snippet": "typical 555 values: 10 kOhm, 100 uF",
         "link": "https://ex.com/r2"},
    ]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    out = serpapi.lookup_rc_components(api_key="k")
    assert abs(out["R"] - 10e3) < 1e-6
    assert abs(out["C"] - 100e-6) < 1e-12


def test_lookup_new_scenarios_no_consensus(monkeypatch):
    fake = [{"title": "a", "snippet": "nothing relevant here", "link": "/a"},
            {"title": "b", "snippet": "more noise", "link": "/b"}]
    monkeypatch.setattr(serpapi, "search", lambda q, api_key=None, num=5: fake)
    assert serpapi.lookup_pipe_roughness(api_key="k")["epsilon"] is None
    assert serpapi.lookup_heat_material(api_key="k")["alpha"] is None
    r = serpapi.lookup_rc_components(api_key="k")
    assert r["R"] is None and r["C"] is None
    assert r["R_sources"] == [] and r["C_sources"] == []
