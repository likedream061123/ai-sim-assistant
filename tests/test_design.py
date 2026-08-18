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

from engine import design
from engine import beam, heat, vessel, pendulum


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
