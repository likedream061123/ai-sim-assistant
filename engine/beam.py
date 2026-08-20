"""钢梁挠度 —— 简支梁集中荷载（静力）。

物理（对照 MATLAB beam_deflection.m 符号推导）: 简支梁长 L，距左端 a 处受集中力 P，
弹性模量 E，截面惯性矩 I。挠度向下为正。
    v1(x) = P*b*x/(6*E*I*L) * (L^2 - b^2 - x^2)                0<=x<=a
    v2(x) = P*b/(6*E*I*L) * ((L/b)(x-a)^3 + (L^2-b^2)x - x^3)   a<=x<=L
弯矩: M1(x)=P*b*x/L, M2(x)=P*a*(L-x)/L
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from i18n import tr, trf

DEFAULT_PARAMS = {
    "L": 4.0,         # 梁长 [m]
    "P": 10000.0,     # 集中荷载 [N]
    "a": 1.5,         # 荷载距左端距离 [m]
    "E": 200e9,       # 弹性模量 [Pa]（钢 200 GPa）
    "I": 5e-4,        # 截面惯性矩 [m^4]
}


def solve_beam(params: dict | None = None, plot: bool = True) -> dict:
    """数值求最大挠度/弯矩，返回挠度曲线 + 弯矩图 + 关键数据。

    plot=False 时跳过 matplotlib 画图（供敏感性扫描等批量调用提速）。
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    L, P, a, E, I = p["L"], p["P"], p["a"], p["E"], p["I"]
    b = L - a
    xx = np.linspace(0, L, 4001)

    def v1(x):
        return P * b * x / (6 * E * I * L) * (L * L - b * b - x * x)

    def v2(x):
        return P * b / (6 * E * I * L) * ((L / b) * (x - a) ** 3 + (L * L - b * b) * x - x ** 3)

    vv = np.where(xx <= a, v1(xx), v2(xx))
    i_max = int(np.argmax(vv))
    v_max, x_max = float(vv[i_max]), float(xx[i_max])

    def M1(x):
        return P * b * x / L

    def M2(x):
        return P * a * (L - x) / L

    Mm = np.where(xx <= a, M1(xx), M2(xx))
    M_max = float(np.max(np.abs(Mm)))
    x_Mmax = float(xx[int(np.argmax(np.abs(Mm)))])

    v_allow = L / 360.0               # 许用挠度 L/360
    within_limit = v_max <= v_allow
    R_A, R_B = P * b / L, P * a / L   # 支反力

    figs = []
    if plot:
        fig1 = plt.figure(figsize=(6, 4))
        plt.plot(xx, vv * 1000, "b-", lw=1.8)
        plt.plot(x_max, v_max * 1000, "ro", ms=8, mfc="r")
        plt.xlabel(tr("x (m)")); plt.ylabel(tr("挠度 v(x) (mm, 向下为正)"))
        plt.title(trf("钢梁挠度 | 最大 {0:.3f} mm @ x={1:.3f} m", v_max * 1000, x_max))
        plt.grid()
        figs.append(fig1)

        fig2 = plt.figure(figsize=(6, 4))
        plt.plot(xx, Mm, "r-", lw=1.8)
        plt.xlabel(tr("x (m)")); plt.ylabel(tr("弯矩 M(x) (N·m)"))
        plt.title(trf("弯矩图 | 最大 |M| = {0:.0f} N·m @ x={1:.3f} m", M_max, x_Mmax))
        plt.grid()
        figs.append(fig2)

    return {
        "figures": figs,
        "data": {
            "v_max": v_max, "x_max": x_max, "v_max_mm": v_max * 1000,
            "M_max": M_max, "x_Mmax": x_Mmax,
            "v_allow": v_allow, "within_limit": bool(within_limit),
            "R_A": R_A, "R_B": R_B, "params": p,
        },
    }


solve = solve_beam  # 统一接口别名（app.py 通过 .solve 调用）


if __name__ == "__main__":
    d = solve_beam()["data"]
    print(f"v_max={d['v_max']:.3e} m ({d['v_max_mm']:.4f} mm) x_max={d['x_max']:.4f} m")
    print(f"M_max={d['M_max']:.0f} N·m 超限? {not d['within_limit']}")
