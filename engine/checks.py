"""极端输入兜底 —— 各场景物理合法性前置校验。

在 engine 的 solve() 入口统一调 check_params(scenario, params)，对荒谬参数
（非正、越界、无传热温差等）抛 ValueError，消息按 i18n 当前语言生成。
app.render_result 已有 try/except，捕获后显示「计算失败：{err}」。

与 UI 的 number_input min/max 不同：那只是静态范围约束手动输入框，
AI 解析推荐值、历史载入、手动手打都可能越界 —— 这里兜住最后一层。
design.sensitivity/compare 内部已 try/except 包住 solve 调用，校验不误伤敏感性扫描。
"""
from __future__ import annotations

import i18n


def _v(x):
    """安全数值显示：数字用 :g 压缩，非数字（None/字符串）原样返回，避免 format 崩溃。"""
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return f"{x:g}"
    return x


def _msg(zh: str, en: str, *vals) -> tuple[str, str]:
    """模板 + 值 → (zh, en) 已格式化字符串。值统一过 _v 安全显示。"""
    args = [_v(v) for v in vals]
    return zh.format(*args), en.format(*args)


def _need(ok: bool, zh: str, en: str) -> None:
    """违规即抛 ValueError，消息按当前语言生成。"""
    if not ok:
        raise ValueError(en if i18n.LANG == "en" else zh)


# ---------------------------------------------------------------------------
# 各场景校验函数：参数 p 是 {**DEFAULT_PARAMS, **用户参数} 合并后的完整字典。
# 只校验真实物理合法性（非正/越界），不断言工程合理性（那是设计建议的职责）。
# ---------------------------------------------------------------------------

def _check_beam(p: dict) -> None:
    L, E, I, a = p.get("L"), p.get("E"), p.get("I"), p.get("a")
    _need(L is not None and L > 0, *_msg(
        "梁长 L 必须为正，当前 {} m",
        "Beam length L must be positive (got {} m)", L))
    _need(E is not None and E > 0, *_msg(
        "弹性模量 E 必须为正，当前 {} Pa",
        "Young's modulus E must be positive (got {} Pa)", E))
    _need(I is not None and I > 0, *_msg(
        "截面惯性矩 I 必须为正，当前 {} m⁴",
        "Moment of inertia I must be positive (got {} m⁴)", I))
    _need(a is not None and 0 < a < L, *_msg(
        "荷载位置 a 必须落在梁内（0 < a < L），当前 a={} m、L={} m",
        "Load position a must lie on the beam (0 < a < L), got a={} m, L={} m", a, L))


def _check_heat(p: dict) -> None:
    L, alpha, T0, Tw, Tt = p.get("L"), p.get("alpha"), p.get("T0"), p.get("T_wall"), p.get("T_target")
    _need(L is not None and L > 0, *_msg(
        "钢件半宽 L 必须为正，当前 {} m",
        "Half-width L must be positive (got {} m)", L))
    _need(alpha is not None and alpha > 0, *_msg(
        "热扩散系数 α 必须为正，当前 {} m²/s",
        "Thermal diffusivity α must be positive (got {} m²/s)", alpha))
    _need(T0 is not None and T0 != Tw, *_msg(
        "初始温度与表面温度相同，没有传热温差",
        "Initial and surface temperatures are identical — no driving temperature difference"))
    _need(Tt is not None and T0 is not None and Tw is not None
          and min(T0, Tw) < Tt < max(T0, Tw), *_msg(
        "目标温度 {} °C 必须在表面温度 {} °C 与初始温度 {} °C 之间",
        "Target temperature {} °C must lie between surface {} °C and initial {} °C",
        Tt, Tw, T0))


def _check_vessel(p: dict) -> None:
    P, D, sigma, t_given = p.get("P"), p.get("D"), p.get("sigma_allow"), p.get("t_given")
    _need(P is not None and P > 0, *_msg(
        "内压 P 必须为正，当前 {} Pa",
        "Internal pressure P must be positive (got {} Pa)", P))
    _need(D is not None and D > 0, *_msg(
        "内径 D 必须为正，当前 {} m",
        "Inner diameter D must be positive (got {} m)", D))
    _need(sigma is not None and sigma > 0, *_msg(
        "许用应力 σ 必须为正，当前 {} Pa",
        "Allowable stress σ must be positive (got {} Pa)", sigma))
    if t_given is not None:
        _need(t_given > 0, *_msg(
            "给定壁厚 t 必须为正，当前 {} m",
            "Given wall thickness t must be positive (got {} m)", t_given))


def _check_pendulum(p: dict) -> None:
    m, l, g, c, t_end = p.get("m"), p.get("l"), p.get("g"), p.get("c"), p.get("t_end")
    _need(m is not None and m > 0, *_msg(
        "摆锤质量 m 必须为正，当前 {} kg",
        "Bob mass m must be positive (got {} kg)", m))
    _need(l is not None and l > 0, *_msg(
        "摆长 l 必须为正，当前 {} m",
        "Pendulum length l must be positive (got {} m)", l))
    _need(g is not None and g > 0, *_msg(
        "重力加速度 g 必须为正，当前 {} m/s²",
        "Gravity g must be positive (got {} m/s²)", g))
    _need(c is None or c >= 0, *_msg(
        "阻尼系数 c 必须非负，当前 {} N·m·s/rad",
        "Damping coefficient c must be non-negative (got {} N·m·s/rad)", c))
    _need(t_end is None or t_end > 0, *_msg(
        "仿真时长必须为正，当前 {} s",
        "Simulation duration must be positive (got {} s)", t_end))


def _check_rc(p: dict) -> None:
    R, C, percent = p.get("R"), p.get("C"), p.get("charge_percent")
    _need(R is not None and R > 0, *_msg(
        "电阻 R 必须为正，当前 {} Ω",
        "Resistance R must be positive (got {} Ω)", R))
    _need(C is not None and C > 0, *_msg(
        "电容 C 必须为正，当前 {} F",
        "Capacitance C must be positive (got {} F)", C))
    _need(percent is not None and 0 < percent < 100, *_msg(
        "充电目标百分比必须在 0~100 之间，当前 {} %",
        "Target charge percent must be between 0 and 100 (got {} %)", percent))


def _check_pipe(p: dict) -> None:
    D, L, Q, rho, mu, eps = (p.get("D"), p.get("L"), p.get("Q"),
                             p.get("rho"), p.get("mu"), p.get("epsilon"))
    _need(D is not None and D > 0, *_msg(
        "管内径 D 必须为正，当前 {} m",
        "Pipe inner diameter D must be positive (got {} m)", D))
    _need(L is not None and L > 0, *_msg(
        "管长 L 必须为正，当前 {} m",
        "Pipe length L must be positive (got {} m)", L))
    _need(Q is not None and Q > 0, *_msg(
        "流量 Q 必须为正，当前 {} m³/s",
        "Flow rate Q must be positive (got {} m³/s)", Q))
    _need(rho is not None and rho > 0, *_msg(
        "流体密度 ρ 必须为正，当前 {} kg/m³",
        "Fluid density ρ must be positive (got {} kg/m³)", rho))
    _need(mu is not None and mu > 0, *_msg(
        "动力黏度 μ 必须为正，当前 {} Pa·s",
        "Dynamic viscosity μ must be positive (got {} Pa·s)", mu))
    _need(eps is not None and eps >= 0, *_msg(
        "粗糙度 ε 必须非负，当前 {} m",
        "Roughness ε must be non-negative (got {} m)", eps))


_CHECKERS = {
    "beam": _check_beam,
    "heat": _check_heat,
    "vessel": _check_vessel,
    "pendulum": _check_pendulum,
    "rc_circuit": _check_rc,
    "pipe_flow": _check_pipe,
}


def check_params(scenario: str, params: dict) -> None:
    """按场景校验物理参数合法性，违规抛 ValueError（消息已按当前语言）。"""
    fn = _CHECKERS.get(scenario)
    if fn is not None:
        fn(params or {})
