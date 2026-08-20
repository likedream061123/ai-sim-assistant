"""设计辅助模块测试 —— 敏感性分析的物理方向/量级 + 超限建议逻辑。

物理基准（用于断言校准）：
    beam    v ∝ P·L³/(E·I) → I/E −20%（±10% 中心差分）、P +20%、L 影响最大
    heat    t ∝ L²/α       → L +40%、α −20%，L 主导
    vessel  t ∝ P·D/σ      → P/D +20%、σ −20%
    pendulum T ∝ √(l/g)    → l +10%+、g −10%，m 几乎为 0（反直觉亮点）
"""
import matplotlib

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
import matplotlib.pyplot as plt

import pytest

import i18n
from engine import design
from engine import beam, heat, vessel, pendulum, pipe_flow, rc_circuit


@pytest.fixture(autouse=True)
def _zh_lang():
    """建议文案走中文分支断言（英文分支由 tests/smoke_app.py 的 en 冒烟覆盖）。"""
    i18n.set_lang("zh")


def _rows(scenario, module, params):
    return dict(design.sensitivity(module.solve, scenario, params))


def test_beam_directions():
    rows = _rows("beam", beam, beam.DEFAULT_PARAMS)
    assert rows["I"] < 0                  # 惯性矩越大挠度越小
    assert rows["E"] < 0
    assert rows["P"] > 0                  # 荷载越大挠度越大
    assert rows["L"] > rows["P"]          # 跨度是挠度的第一影响因素


def test_beam_span_most_sensitive():
    rows = _rows("beam", beam, beam.DEFAULT_PARAMS)
    assert rows["L"] > 45                 # v∝L³ 区间，±10% 跨度 → 挠度 ~+50%


def test_vessel_linear_scaling():
    rows = _rows("vessel", vessel, vessel.DEFAULT_PARAMS)
    assert abs(rows["P"] - 20) < 2        # t ∝ P 正比
    assert abs(rows["D"] - 20) < 2
    assert abs(rows["sigma_allow"] + 20) < 2   # t ∝ 1/σ 反比


def test_heat_span_dominant():
    rows = _rows("heat", heat, heat.DEFAULT_PARAMS)
    assert abs(rows["L"] - 40) < 5        # t ∝ L²
    assert abs(rows["alpha"] + 20) < 3    # t ∝ 1/α
    assert rows["L"] > rows["alpha"]      # 几何尺寸主导，物理直觉成立


def test_pendulum_mass_irrelevant():
    rows = _rows("pendulum", pendulum, pendulum.DEFAULT_PARAMS)
    assert abs(rows["m"]) < 3             # 质量对周期几乎无影响（反直觉亮点）
    assert rows["l"] > 10                 # 摆长决定周期 T∝√l


def test_sensitivity_returns_sorted_desc():
    rows = design.sensitivity(beam.solve, "beam", beam.DEFAULT_PARAMS)
    assert rows == sorted(rows, key=lambda r: -abs(r[1]))


def test_plot_sensitivity_returns_fig():
    rows = design.sensitivity(beam.solve, "beam", beam.DEFAULT_PARAMS)
    fig = design.plot_sensitivity(rows, "beam")
    assert fig is not None
    plt.close(fig)


def test_advice_beam_over_limit():
    d = beam.solve({"P": 2e5, "I": 1e-5})["data"]
    assert not d["within_limit"]
    adv = design.advice("beam", d)
    assert adv is not None
    assert adv["adjust"]["I"] > 1e-5      # 建议加大惯性矩
    assert "25%" in adv["message"]        # 留裕量逻辑存在


def test_advice_beam_ok_none():
    d = beam.solve()["data"]
    assert d["within_limit"]
    assert design.advice("beam", d) is None


def test_advice_heat_not_reached():
    d = heat.solve({"T_wall": 20, "tmax": 60})["data"]
    assert d["t_center_target"] is None
    adv = design.advice("heat", d)
    assert adv is not None
    assert "L" in adv["adjust"]           # 建议减小半宽加快冷却


def test_advice_vessel_and_pendulum_none():
    assert design.advice("vessel", vessel.solve()["data"]) is None
    assert design.advice("pendulum", pendulum.solve()["data"]) is None


def test_advice_vessel_over_limit():
    """校核模式：给定壁厚太薄 → 建议加厚到 t_req×1.25。"""
    d = vessel.solve({"P": 1e6, "D": 1.0, "sigma_allow": 100e6, "t_given": 0.002})["data"]
    assert d["safe"] is False            # 2mm 壁厚 < 所需 5mm
    adv = design.advice("vessel", d)
    assert adv is not None
    assert adv["adjust"]["t_given"] > 0.005    # 建议加厚到 > 所需壁厚
    assert "许用" in adv["message"]


def test_advice_vessel_safe_none():
    """未校核（无 t_given）时不给建议，只做敏感性。"""
    d = vessel.solve({"P": 1e6, "D": 1.0, "sigma_allow": 100e6})["data"]
    assert d["t_given"] is None          # 未校核
    assert design.advice("vessel", d) is None


# ---- 参数对比 compare() / plot_compare() ----

def test_compare_beam_I_monotonic_decreasing():
    """I 增大 → 挠度减小（v ∝ 1/I），4 倍 I 应带来明显挠度差。"""
    rows = design.compare(beam.solve, "beam", beam.DEFAULT_PARAMS, "I",
                          [1e-5, 5e-5, 1e-4, 5e-4])
    assert len(rows) == 4
    outs = [y for _, y in rows]
    assert outs == sorted(outs, reverse=True)
    assert outs[0] > outs[-1] * 3        # 实测 50×，留裕量断言


def test_compare_beam_L_increasing():
    """L 增大 → 挠度增大（v ∝ L³）。"""
    rows = design.compare(beam.solve, "beam", beam.DEFAULT_PARAMS, "L", [2, 3, 4, 5])
    outs = [y for _, y in rows]
    assert outs == sorted(outs)
    assert outs[-1] > outs[0] * 8        # 实测 ~18×，留裕量断言


def test_compare_rows_sorted_ascending():
    """输入乱序也按参数值升序返回（fragment 采样是升序，但函数自身保证）。"""
    rows = design.compare(vessel.solve, "vessel", vessel.DEFAULT_PARAMS, "P",
                          [2e6, 1e6, 3e6, 0.5e6])
    vals = [v for v, _ in rows]
    assert vals == sorted(vals)


def test_compare_vessel_linear():
    """t ∝ P：P 翻倍 → 所需壁厚翻倍（对比曲线最直白的线性亮点）。"""
    rows = design.compare(vessel.solve, "vessel", vessel.DEFAULT_PARAMS, "P", [1e6, 2e6, 3e6])
    ys = [y for _, y in rows]
    assert abs(ys[1] - 2 * ys[0]) < 1e-6
    assert abs(ys[2] - 3 * ys[0]) < 1e-6


def test_plot_compare_returns_fig_with_current():
    """当前值落在采样范围内 → 曲线 + 红点，返回 fig。"""
    rows = design.compare(beam.solve, "beam", beam.DEFAULT_PARAMS, "I", [1e-5, 5e-5, 1e-4])
    fig = design.plot_compare(rows, "beam", "I", 5e-5)
    assert fig is not None
    plt.close(fig)


def test_plot_compare_none_too_few():
    """采样点不足 → 返回 None（UI 兜底提示），不炸。"""
    rows = design.compare(beam.solve, "beam", beam.DEFAULT_PARAMS, "I", [1e-5])
    assert len(rows) < 2
    assert design.plot_compare(rows, "beam", "I", 1e-5) is None


def test_plot_compare_current_outside_range():
    """当前值在采样范围外 → 不画红点、不崩，正常返回 fig。"""
    rows = design.compare(beam.solve, "beam", beam.DEFAULT_PARAMS, "I", [1e-5, 5e-5, 1e-4])
    fig = design.plot_compare(rows, "beam", "I", 1e-2)
    assert fig is not None
    plt.close(fig)


# ---- 新场景（RC 电路 / 管道压降）----

def test_pipe_sensitivity_laminar_analytic():
    """层流段 dp=128μLQ/(πD⁴)：Q/L +20%，D 变化反向且影响最大（∝D⁻⁴），ε 无关。"""
    p = {**pipe_flow.DEFAULT_PARAMS, "Q": 1e-5, "D": 0.01, "L": 10.0}
    rows = _rows("pipe_flow", pipe_flow, p)
    assert abs(rows["Q"] - 20) < 2          # dp ∝ Q（线性）
    assert abs(rows["L"] - 20) < 2          # dp ∝ L（线性）
    assert rows["D"] < -70                   # dp ∝ 1/D⁴，D 增大压降锐减
    assert abs(rows["D"]) > rows["Q"]       # 管径是压降第一影响因素
    assert abs(rows["epsilon"]) < 1e-6      # 层流摩擦与粗糙度无关


def test_rc_sensitivity_tau_driven():
    """t_charge ∝ RC：R/C +20%，V_s 不影响充电时长。"""
    rows = _rows("rc_circuit", rc_circuit, rc_circuit.DEFAULT_PARAMS)
    assert abs(rows["R"] - 20) < 2
    assert abs(rows["C"] - 20) < 2
    assert abs(rows["V_s"]) < 1e-6


def test_advice_pipe_velocity_too_fast():
    """流速超 3 m/s → 建议加大管径 +25%，压回经济区间。"""
    d = pipe_flow.solve({"Q": 20 / 3600.0, "D": 0.02})["data"]
    assert d["v"] > 3
    adv = design.advice("pipe_flow", d)
    assert adv is not None
    assert adv["adjust"]["D"] > 0.02
    assert "流速" in adv["message"]


def test_advice_pipe_velocity_too_slow():
    """流速 <0.5 m/s → 建议收小管径。"""
    d = pipe_flow.solve({"Q": 1e-4, "D": 0.5})["data"]
    assert d["v"] < 0.5
    adv = design.advice("pipe_flow", d)
    assert adv is not None
    assert adv["adjust"]["D"] < 0.5


def test_advice_pipe_ok_none():
    """经济流速区间（1~3 m/s）内不打扰，只做敏感性。"""
    d = pipe_flow.solve()["data"]
    assert 1.0 <= d["v"] <= 3.0
    assert design.advice("pipe_flow", d) is None


def test_advice_rc_none():
    """RC 无超限概念 → 不给建议。"""
    assert design.advice("rc_circuit", rc_circuit.solve()["data"]) is None
