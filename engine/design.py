"""设计辅助模块 —— 参数敏感性分析 + 超限自动建议。

在 4 个数值引擎之上加一层「设计师视角」，让产品从「算一下」变成「帮你做决定」：
1. sensitivity():    对每个物理参数 ±10% 扫描，量化「改变哪个参数对结果影响最大」
2. plot_sensitivity(): tornado 图（matplotlib）
3. advice():         超限/未达标时给调整建议 + 可一键应用的重算参数

不侵入引擎（引擎只负责算），本层只读引擎的 solve() 接口。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

# 每场景敏感性规格：参与扫描的物理参数（白名单，排除数值离散/仿真控制键
# 如 heat 的 N/r/tmax —— 它们不反映真实设计决策）+ 目标输出键 + 输出中文名。
SENSITIVITY_SPEC = {
    "pendulum": {
        "params": ["m", "l", "g", "c"],
        "key_out": "T_num",
        "label": "摆动周期 T",
        "unit": "s",
    },
    "heat": {
        "params": ["L", "T0", "T_wall", "alpha", "T_target"],
        "key_out": "t_center_target",
        "label": "冷却到目标温度时间",
        "unit": "s",
    },
    "beam": {
        "params": ["L", "P", "a", "E", "I"],
        "key_out": "v_max_mm",
        "label": "最大挠度",
        "unit": "mm",
    },
    "vessel": {
        "params": ["P", "D", "sigma_allow"],
        "key_out": "t_req_mm",
        "label": "所需壁厚",
        "unit": "mm",
    },
}


# 参数中文名（对比曲线/轴标签用）。英文键对齐各引擎 DEFAULT_PARAMS。
PARAM_LABELS = {
    "pendulum": {"m": "质量 m", "l": "摆长 l", "g": "重力加速度 g", "c": "阻尼系数 c",
                 "th0_deg": "初始角度 θ₀", "w0": "初始角速度 ω₀", "t_end": "仿真时长"},
    "heat": {"L": "钢件半宽 L", "T0": "初始温度 T₀", "T_wall": "介质温度 T_wall",
             "alpha": "热扩散系数 α", "T_target": "目标温度 T_target"},
    "beam": {"L": "梁长 L", "P": "集中荷载 P", "a": "荷载距左端 a", "E": "弹性模量 E", "I": "惯性矩 I"},
    "vessel": {"P": "内压 P", "D": "内径 D", "sigma_allow": "许用应力 σ", "t_given": "给定壁厚 t"},
}


def compare(engine_solve, scenario: str, params: dict, param_name: str, values: list) -> list:
    """对参数 param_name 取 values 各值扫描目标输出，返回 [(值, 输出), ...] 按值升序。

    与 sensitivity() 复用 SENSITIVITY_SPEC 的目标键/中文名，做的是同一层「设计师视角」：
    敏感性回答「哪个参数影响最大」，对比回答「这个参数从 A 调到 B，结果怎么变」。
    单个值求解失败（该参数组合物理上无解）跳过，不中断整体扫描。
    """
    spec = SENSITIVITY_SPEC[scenario]
    rows = []
    for v in values:
        try:
            out = engine_solve({**params, param_name: float(v)}, plot=False)["data"].get(spec["key_out"])
        except Exception:
            out = None
        if out is not None:
            rows.append((float(v), float(out)))
    rows.sort(key=lambda r: r[0])
    return rows


def plot_compare(rows: list, scenario: str, param_name: str, current_value: float | None) -> plt.Figure | None:
    """对比曲线：横轴 = 参数取值，纵轴 = 目标输出；当前值画红点。

    rows=[(参数值, 输出), ...]。当前值落在采样范围内才画红点（曲线示意插值），
    在范围外说明当前值不在对比窗口内，不误导。
    参数跨度 >2 数量级时自动切对数轴（如惯性矩 I 1e-8~1 线性会挤成一条）。
    """
    if len(rows) < 2:
        return None
    spec = SENSITIVITY_SPEC[scenario]
    label = PARAM_LABELS.get(scenario, {}).get(param_name, param_name)
    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(xs, ys, "-", color="#3D7BFF", lw=2, marker="o", ms=4, mfc="white", mec="#3D7BFF")
    if current_value is not None and min(xs) <= current_value <= max(xs):
        cy = float(np.interp(current_value, xs, ys))
        ax.plot([current_value], [cy], "o", ms=11, mfc="#E5484D", mec="white", mew=1.5,
                label=f"当前值 = {current_value:.3g}")
        ax.legend(loc="best", frameon=False)
    if min(xs) > 0 and max(xs) / min(xs) > 100:
        ax.set_xscale("log")
    ax.set_xlabel(label, fontsize=10)
    ax.set_ylabel(f"{spec['label']}（{spec['unit']}）", fontsize=10)
    ax.set_title(f"参数对比 | {label} 变化 → {spec['label']}", fontsize=11)
    ax.tick_params(colors="#2A3550")
    ax.grid(True, color="#F0F0EB", linewidth=0.6)
    fig.tight_layout()
    return fig


def sensitivity(engine_solve, scenario: str, params: dict, delta: float = 0.10) -> list:
    """扫描每个物理参数 ±delta，返回 [(参数名, 输出变化百分比), ...] 按影响降序。

    engine_solve: 可调用对象，engine.solve(params, plot=False) -> {"figures","data"}
    pct 含义：该参数从 -delta 变到 +delta 时目标输出变化多少%。
        负值 = 增大该参数会使输出减小（如梁的 I：惯性矩越大挠度越小）。
    中心差分（±两侧取均值）；一侧求解异常时退化为单侧差分。
    """
    spec = SENSITIVITY_SPEC[scenario]

    def run(p):
        try:
            val = engine_solve(p, plot=False)["data"].get(spec["key_out"])
        except Exception:
            val = None
        return None if val is None else float(val)

    base = run(dict(params))
    if base is None or base == 0:
        return []

    rows = []
    for name in spec["params"]:
        v = params.get(name)
        if not isinstance(v, (int, float)) or v == 0 or np.isnan(v):
            continue
        plo = {**params, name: v * (1 - delta)}
        phi = {**params, name: v * (1 + delta)}
        ylo, yhi = run(plo), run(phi)
        if ylo is not None and yhi is not None:
            pct = (yhi - ylo) / abs(base) * 100.0
        elif yhi is not None:
            pct = (yhi - base) / abs(base) * 100.0
        elif ylo is not None:
            pct = (base - ylo) / abs(base) * 100.0
        else:
            continue
        rows.append((name, pct))
    rows.sort(key=lambda r: -abs(r[1]))
    return rows


def plot_sensitivity(rows: list, scenario: str) -> plt.Figure | None:
    """Tornado 图：横条按影响排序，正影响向右（主题蓝）、负影响向左（浅蓝）。"""
    spec = SENSITIVITY_SPEC[scenario]
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(7, max(2.2, 0.55 * len(rows))))
    names = [r[0] for r in rows]
    pcts = [r[1] for r in rows]
    pos = np.arange(len(rows))
    bars = ax.barh(pos, pcts, height=0.6,
                   color=["#3D7BFF" if p >= 0 else "#7F97D9" for p in pcts])
    for p, bar in zip(pcts, bars):
        ax.text(p + (0.5 if p >= 0 else -0.5), bar.get_y() + bar.get_height() / 2,
                f"{p:+.0f}%", va="center",
                ha="left" if p >= 0 else "right", color="#DCE6FF", fontsize=9)
    ax.axvline(0, color="#2A3550", lw=1)
    ax.set_yticks(pos)
    ax.set_yticklabels(names, fontsize=10)
    ax.set_xlabel(f"该参数 ±10% 时「{spec['label']}」的变化 (%)", fontsize=9)
    ax.set_title(f"参数敏感性 | 改变谁影响最大？（{spec['label']}）", fontsize=11)
    ax.tick_params(colors="#9FB4FF")
    for spine in ax.spines.values():
        spine.set_edgecolor("#2A3550")
    ax.grid(True, axis="x", color="#1C2A4A", linewidth=0.6)
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def advice(scenario: str, data: dict) -> dict | None:
    """超限/未达标时给调整建议。

    返回 {"message": 建议文本, "adjust": {参数: 新值}, "label": 按钮文案} 或 None。
    adjust 供「一键应用」按钮直接并入参数重算。
    无超限概念的场景（vessel/pendulum）返回 None —— 只做敏感性分析。
    """
    params = data.get("params") or {}

    if scenario == "beam":
        if not data.get("within_limit", True):
            v_max, v_allow = data["v_max"], data["v_allow"]
            I = params.get("I", 5e-4)
            need = I * v_max / v_allow * 1.25   # v ∝ 1/I，反推所需 I + 25% 裕量
            return {
                "message": (
                    f"最大挠度 {data['v_max_mm']:.1f} mm 超过许用 {v_allow * 1000:.1f} mm"
                    f"（L/360）。挠度与截面惯性矩成反比：把 I 从 {I:.3g} m⁴"
                    f" 加大到约 {need:.3g} m⁴（{need / I:.1f}×，留 25% 裕量），即可回到限内。"
                ),
                "adjust": {"I": float(need)},
                "label": f"I → {need:.3g} m⁴ 并重算",
            }
        return None

    if scenario == "heat":
        if data.get("t_center_target") is None:
            L = params.get("L", 0.1)
            return {
                "message": (
                    "仿真时长内中心温度未降到目标。冷却时间约与半宽 L² 成正比、"
                    "随介质温度 T_wall 升高而缩短 —— 减小 L 或提高 T_wall 都能显著加快。"
                ),
                "adjust": {"L": float(L * 0.8)},
                "label": f"L → {L * 0.8:.3g} m 并重算",
            }
        return None

    if scenario == "vessel":
        # 校核模式：给定壁厚但实际应力超许用 → 建议加厚
        if data.get("safe") is False:
            t_given = data.get("t_given")
            if t_given:
                t_req = data["t_req"]
                need = t_req * 1.25
                return {
                    "message": (
                        f"给定壁厚 {t_given * 1000:.1f} mm 下实际应力 "
                        f"{data['sigma_actual'] / 1e6:.0f} MPa，超过许用 "
                        f"{data['sigma_allow'] / 1e6:.0f} MPa。ASME 所需壁厚 "
                        f"{data['t_req_mm']:.1f} mm —— 建议加厚到 {need * 1000:.1f} mm"
                        f"（留 25% 裕量）即安全。"
                    ),
                    "adjust": {"t_given": float(need)},
                    "label": f"t → {need * 1000:.1f} mm 并重算",
                }
        return None

    return None
