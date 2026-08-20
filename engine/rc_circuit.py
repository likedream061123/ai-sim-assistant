"""RC 电路充放电 —— 一阶 RC 暂态（解析解）。

物理（教科书标准）: 电容经电阻被电压源充电，V_c(t) = V_s·(1 - e^(-t/τ))，τ = RC。
充到目标百分比 p 的时间 t = -τ·ln(1 - p/100)；工程惯例 5τ 视为「基本充满」(≈99.3%)。
放电对称：V_c(t) = V_0·e^(-t/τ)。

解析解，零迭代 —— 「数值永不猜」里教科书级的干净场景。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

DEFAULT_PARAMS = {
    "R": 1000.0,          # 电阻 [Ω]
    "C": 100e-6,          # 电容 [F]
    "V_s": 12.0,          # 源电压 [V]
    "charge_percent": 90.0,  # 充到多少百分比算「到达」[%]（<100）
}


def solve_rc(params: dict | None = None, plot: bool = True) -> dict:
    """充电暂态解析解：返回电压/电流曲线 + 关键数据。

    关键量：
    - τ = R·C 时间常数
    - t_charge = -τ·ln(1-p/100) 充到目标百分比的时间
    - v_5tau ≈ 0.993·V_s（5τ 工程「充满」）
    - i_peak = V_s/R 初始充电电流
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    R, C, Vs = p["R"], p["C"], p["V_s"]
    percent = min(float(p["charge_percent"]), 99.999)
    tau = R * C
    t_charge = -tau * np.log(1 - percent / 100.0)
    v_target = Vs * percent / 100.0
    v_5tau = Vs * (1 - np.exp(-5))
    i_peak = Vs / R

    t = np.linspace(0, 5 * tau, 400)
    v_curve = Vs * (1 - np.exp(-t / tau))
    i_curve = i_peak * np.exp(-t / tau)

    figs = []
    if plot:
        fig1 = plt.figure(figsize=(6, 4))
        plt.plot(t, v_curve, "b-", lw=1.8)
        plt.axvline(tau, color="gray", ls="--", lw=1)
        plt.axhline(v_target, color="r", ls="--", lw=1)
        plt.plot([t_charge], [v_target], "ro", ms=8, mfc="r")
        plt.xlabel("t (s)"); plt.ylabel("电容电压 Vc (V)")
        plt.title(f"RC 充电 | τ={tau:.3g}s，充到 {percent:.0f}% 需 {t_charge:.3g}s")
        plt.legend(["Vc(t)", f"τ = {tau:.3g}s", f"{percent:.0f}% = {v_target:.2f}V"],
                   loc="lower right")
        plt.grid()
        figs.append(fig1)

        fig2 = plt.figure(figsize=(6, 4))
        plt.plot(t, i_curve, "g-", lw=1.8)
        plt.xlabel("t (s)"); plt.ylabel("充电电流 i (A)")
        plt.title(f"充电电流衰减 | 初始峰值 {i_peak:.3g} A")
        plt.grid()
        figs.append(fig2)

    return {
        "figures": figs,
        "data": {
            "tau": float(tau),
            "t_charge": float(t_charge),
            "v_target": float(v_target),
            "v_5tau": float(v_5tau),
            "i_peak": float(i_peak),
            "charge_percent": float(percent),
            "params": {**p},
        },
    }


solve = solve_rc  # 统一接口别名（app.py 通过 .solve 调用）


if __name__ == "__main__":
    d = solve_rc()["data"]
    print(f"τ={d['tau']:.4g}s | 充到 90% 需 {d['t_charge']:.4g}s | 5τ 电压 {d['v_5tau']:.2f}V")
