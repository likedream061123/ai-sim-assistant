"""管道沿程压降 —— Darcy-Weisbach + Colebrook 摩擦系数。

物理（流体力学标准）: ΔP = f·(L/D)·(ρv²/2)，v = Q/A，A = πD²/4。
流态判据: Re = ρvD/μ。
- Re < 2300 层流: f = 64/Re（可化出解析解 ΔP = 128μLQ/(πD⁴)，Hagen-Poiseuille）
- Re > 4000 湍流: f 解 Colebrook 隐式方程 1/√f = -2·log10(ε/(3.7D) + 2.51/(Re√f))
- 过渡区 2300~4000: 按湍流公式近似（工程惯例）

摩擦系数用不动点迭代求解（初值 f=0.02，Colebrook 收敛快）。默认水介质。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from i18n import tr, trf

DEFAULT_PARAMS = {
    "Q": 20.0 / 3600.0,   # 体积流量 [m³/s]（默认 20 m³/h）
    "D": 0.05,            # 管内径 [m]
    "L": 100.0,           # 管长 [m]
    "epsilon": 45e-6,     # 绝对粗糙度 [m]（钢管 ≈ 0.045 mm）
    "rho": 1000.0,        # 流体密度 [kg/m³]（水）
    "mu": 1e-3,           # 动力黏度 [Pa·s]（水 20°C）
}


def colebrook_friction(Re: float, eps_D: float,
                       max_iter: int = 80, tol: float = 1e-10) -> float:
    """解 Colebrook 隐式方程（湍流段）返回摩擦系数 f。"""
    f = 0.02
    for _ in range(max_iter):
        f_new = 1.0 / (-2.0 * np.log10(eps_D / 3.7 + 2.51 / (Re * np.sqrt(f)))) ** 2
        if abs(f_new - f) < tol:
            return f_new
        f = f_new
    return f


def solve_pipe(params: dict | None = None, plot: bool = True) -> dict:
    """求流速/雷诺数/摩擦系数/沿程压降，返回压降曲线 + 关键数据。"""
    p = {**DEFAULT_PARAMS, **(params or {})}
    Q, D, L, eps = p["Q"], p["D"], p["L"], p["epsilon"]
    rho, mu = p["rho"], p["mu"]
    A = np.pi * D ** 2 / 4
    v = Q / A
    Re = rho * v * D / mu
    eps_D = eps / D

    if Re < 2300:
        f = 64.0 / Re
        flow_type = "层流"
    else:
        f = colebrook_friction(Re, eps_D)
        flow_type = "过渡区(按湍流估算)" if Re < 4000 else "湍流"
    dp = f * (L / D) * (rho * v * v / 2.0)
    head = dp / (rho * 9.81)          # 水柱高度 [m]

    figs = []
    if plot:
        # 图1：沿程累计压降（线性）
        xx = np.linspace(0, L, 200)
        fig1 = plt.figure(figsize=(6, 4))
        plt.plot(xx, (xx / L) * dp / 1000.0, "b-", lw=1.8)
        plt.plot([L], [dp / 1000.0], "ro", ms=8, mfc="r")
        plt.xlabel(tr("沿程距离 x (m)")); plt.ylabel(tr("累计压降 (kPa)"))
        plt.title(trf("沿程压降 | 总 {0:.2f} kPa（{1:.0f} Pa）", dp / 1000.0, dp))
        plt.grid()
        figs.append(fig1)

        # 图2：压降随流量（湍流段 ≈ 二次关系，工程直觉「流量翻倍压降翻四倍」）
        qs = np.linspace(0.5 * Q, 1.5 * Q, 40)
        dps = []
        for q in qs:
            vv = q / A
            rre = rho * vv * D / mu
            ff = 64.0 / rre if rre < 2300 else colebrook_friction(rre, eps_D)
            dps.append(ff * (L / D) * (rho * vv * vv / 2.0))
        fig2 = plt.figure(figsize=(6, 4))
        plt.plot(qs * 3600.0, np.array(dps) / 1000.0, "r-", lw=1.8)
        plt.plot([Q * 3600.0], [dp / 1000.0], "ro", ms=8, mfc="r")
        plt.xlabel(tr("流量 Q (m³/h)")); plt.ylabel(tr("压降 (kPa)"))
        plt.title(trf("压降随流量 | Q={0:.1f} m³/h → {1:.2f} kPa", Q * 3600.0, dp / 1000.0))
        plt.grid()
        figs.append(fig2)

    return {
        "figures": figs,
        "data": {
            "v": float(v),
            "Re": float(Re),
            "f": float(f),
            "dp": float(dp),
            "dp_kPa": float(dp / 1000.0),
            "head_loss": float(head),
            "flow_type": flow_type,
            "params": {**p},
        },
    }


solve = solve_pipe  # 统一接口别名（app.py 通过 .solve 调用）


if __name__ == "__main__":
    d = solve_pipe()["data"]
    print(f"v={d['v']:.2f} m/s | Re={d['Re']:.0f} ({d['flow_type']}) | "
          f"f={d['f']:.4f} | ΔP={d['dp_kPa']:.2f} kPa")
