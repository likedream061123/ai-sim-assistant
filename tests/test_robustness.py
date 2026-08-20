"""极端输入兜底测试 —— 荒谬参数优雅报错不崩。

引擎 solve() 入口统一调 engine.checks.check_params()：非正、越界、无传热温差等
物理不合法参数抛 ValueError（消息按 i18n 当前语言生成），app.render_result 的
try/except 捕获后显示「计算失败：{err}」。同时验证「合法但极端」的参数不误伤。

锁三点：
1. 6 场景的荒谬参数全部抛 ValueError（而非 NaN/挂死/静默）
2. 合法极端参数（大摆角、薄壁、小流量等）正常出数
3. 错误消息随语言切换（zh/en）
"""
import pytest

import i18n
from engine import beam, heat, vessel, pendulum, rc_circuit, pipe_flow


@pytest.fixture(autouse=True)
def _zh_lang():
    i18n.set_lang("zh")
    yield


def _raises(solver, params):
    with pytest.raises(ValueError):
        solver(params)


# ---------------------------------------------------------------------------
# 荒谬参数 → ValueError
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"L": 0}, {"L": -1},          # 梁长非正
    {"E": 0}, {"I": 0},           # 刚度参数为零 → 除零
    {"a": 0}, {"a": 4.0}, {"a": 5.0},   # 荷载不在梁内（a==L / a>L / a==0）
])
def test_beam_rejects_invalid(bad):
    _raises(beam.solve, bad)


@pytest.mark.parametrize("bad", [
    {"L": 0}, {"alpha": 0},              # 半宽/热扩散非正
    {"T0": 20, "T_wall": 20},            # 无传热温差
    {"T0": 800, "T_wall": 20, "T_target": 900},  # 目标在初温之上（冷却场景不可能）
    {"T0": 800, "T_wall": 20, "T_target": 20},   # 目标==壁温（渐近永达不到）
    {"T0": 20, "T_wall": 800, "T_target": 10},   # 加热场景目标在初温之下（无法实现）
    {"T0": 20, "T_wall": 800, "T_target": 900},  # 加热场景目标超过介质温度
])
def test_heat_rejects_invalid(bad):
    _raises(heat.solve, bad)


@pytest.mark.parametrize("bad", [
    {"P": 0}, {"P": -1e6}, {"D": 0}, {"sigma_allow": 0},
    {"t_given": 0}, {"t_given": -0.1},
])
def test_vessel_rejects_invalid(bad):
    _raises(vessel.solve, bad)


@pytest.mark.parametrize("bad", [
    {"l": 0}, {"m": 0}, {"g": 0},     # 质量/摆长/重力非正 → 除零
    {"c": -1},                        # 负阻尼 → 能量发散
    {"t_end": 0}, {"t_end": -10},     # 仿真时长非正
])
def test_pendulum_rejects_invalid(bad):
    _raises(pendulum.solve, bad)


@pytest.mark.parametrize("bad", [
    {"R": 0}, {"C": 0}, {"C": -1e-6},
    {"charge_percent": 0}, {"charge_percent": 100}, {"charge_percent": 150},
])
def test_rc_rejects_invalid(bad):
    _raises(rc_circuit.solve, bad)


@pytest.mark.parametrize("bad", [
    {"D": 0}, {"L": 0}, {"L": -1}, {"Q": 0}, {"Q": -1e-3},
    {"mu": 0}, {"epsilon": -1e-6},
])
def test_pipe_rejects_invalid(bad):
    _raises(pipe_flow.solve, bad)


# ---------------------------------------------------------------------------
# 合法但极端 → 正常出数，不误伤
# ---------------------------------------------------------------------------

def test_beam_extreme_but_valid():
    d = beam.solve({"L": 100.0, "P": 10.0, "a": 1.0}, plot=False)["data"]
    assert 0 <= d["v_max_mm"] < 1.0          # 长梁小载 → 挠度极小但有限
    d2 = beam.solve({"L": 4.0, "a": 3.999}, plot=False)["data"]
    assert d2["v_max_mm"] >= 0


def test_heat_target_close_to_wall_valid():
    d = heat.solve({"T0": 800, "T_wall": 20, "T_target": 25}, plot=False)["data"]
    assert d["t_center_target"] is not None and d["t_center_target"] > 0


def test_heat_heating_direction_valid():
    # 反向工况：从 20°C 加热到 800°C 介质中，目标 500°C
    d = heat.solve({"T0": 20, "T_wall": 800, "T_target": 500}, plot=False)["data"]
    assert d["t_center_target"] is not None and d["t_center_target"] > 0


def test_pendulum_large_angle_valid():
    d = pendulum.solve({"th0_deg": 500.0}, plot=False)["data"]   # 远超小角度假设仍可解
    assert d["T_num"] is not None and d["T_num"] > 0


def test_rc_tiny_tau_valid():
    d = rc_circuit.solve({"R": 1.0, "C": 1e-6, "charge_percent": 50}, plot=False)["data"]
    assert d["t_charge"] > 0


def test_pipe_tiny_flow_laminar_valid():
    d = pipe_flow.solve({"Q": 1e-6, "D": 0.05}, plot=False)["data"]
    assert d["Re"] < 2300 and d["dp_kPa"] >= 0     # 层流、压降极小不崩


# ---------------------------------------------------------------------------
# 语言切换：消息随当前语言
# ---------------------------------------------------------------------------

def test_message_follows_language():
    i18n.set_lang("en")
    try:
        with pytest.raises(ValueError) as e:
            beam.solve({"L": 0})
        assert "must be positive" in str(e.value)
    finally:
        i18n.set_lang("zh")


def test_message_includes_param_value_zh():
    with pytest.raises(ValueError) as e:
        rc_circuit.solve({"C": -1e-6})
    msg = str(e.value)
    assert "电容" in msg and "-1e-06" in msg


def test_unknown_scenario_is_noop():
    """未注册场景不抛错（防御性：新引擎接入前不误伤）。"""
    from engine.checks import check_params
    check_params("future_scenario", {"x": 0})   # 应静默通过
