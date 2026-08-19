"""钢件冷却 —— 一维瞬态传热（显式有限差分）。

物理: 一维热扩散 du/dt = alpha * d2u/dx2，无内热源。
模型: 钢件半宽 L，中心 x=0（对称 Neumann 反射），表面 x=L（Dirichlet 恒温 T_wall，
模拟泡在淬火介质中表面立即冷却）。初始均匀高温 T0，求中心降到 T_target 的时间。

差分内核对照 MATLAB heat1d_explicit.m（显式格式，r<0.5 稳定）。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

DEFAULT_PARAMS = {
    "L": 0.1,          # 钢件半宽/半径 [m]（对称模型取半）
    "T0": 800.0,       # 初始温度 [°C]
    "T_wall": 20.0,    # 表面温度（淬火介质）[°C]
    "alpha": 1.17e-5,  # 热扩散系数（钢）[m^2/s]
    "T_target": 100.0, # 目标温度 [°C]（中心降到该值）
    "N": 100,          # 格点数
    "r": 0.4,          # 扩散数（<0.5 稳定）
    "tmax": 3600.0,    # 最大模拟时间 [s]
}


def solve_heat(params: dict | None = None, plot: bool = True) -> dict:
    """显式差分求解钢件冷却，返回中心温度曲线 + 冷却到目标温度的时间。

    返回 {"figures": [温度分布快照, 中心温度曲线], "data": {...}}。
    plot=False 时跳过画图与快照累积（供敏感性扫描提速）。
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    L, N = p["L"], p["N"]
    alpha, T0, Tw, Tt = p["alpha"], p["T0"], p["T_wall"], p["T_target"]
    r, tmax = p["r"], p["tmax"]

    dx = L / (N - 1)
    dt = r * dx ** 2 / alpha
    nstep = int(tmax / dt)
    x = np.linspace(0, L, N)
    u = np.full(N, T0)

    t_center_target = None
    T_center, t_arr = [], []
    nplot = 6
    plot_interval = max(1, nstep // (nplot - 1))
    U_snap, t_snap = ([u.copy()], [0.0]) if plot else (None, None)

    for n in range(1, nstep + 1):
        # 左 Neumann 反射（中心对称），右 Dirichlet 固定（表面恒温）
        uext = np.concatenate(([u[1]], u, [Tw]))
        lap = uext[2:] - 2 * uext[1:-1] + uext[:-2]
        u = u + r * lap
        u[-1] = Tw
        if plot and n % plot_interval == 0:
            U_snap.append(u.copy())
            t_snap.append(n * dt)
        if t_center_target is None and u[0] <= Tt:
            t_center_target = n * dt
        if n % 100 == 0:
            T_center.append(float(u[0]))
            t_arr.append(n * dt)
            # 提前终止：中心已到目标、且温降走完 99%（中心趋近壁温）就收尾。
            # L 小 + tmax 大时 nstep 可达上千万步，若空转跑满全程极慢（L=0.01 实测 ~40s）。
            # 只对「中心已降到目标温度」的工况生效，中心到不了目标时照常跑满。
            if t_center_target is not None and u[0] - Tw <= 0.01 * (T0 - Tw):
                break

    # 全场趋同（壁温）——「充分冷却」语义，与提前终止判据一致
    steady_reached = abs(float(u[-1] - u[0])) < 0.01 * abs(T0 - Tw)

    figs = []
    if plot:
        fig1 = plt.figure(figsize=(6, 4))
        for k in range(len(U_snap)):
            plt.plot(x, U_snap[k], label=f"t={t_snap[k]:.0f}s")
        plt.xlabel("x (m, 0=中心)"); plt.ylabel("T (°C)")
        plt.title("钢件冷却：温度分布快照"); plt.legend(); plt.grid()
        figs.append(fig1)

        fig2 = plt.figure(figsize=(6, 4))
        plt.plot(t_arr, T_center, "b-", lw=1.8)
        plt.axhline(Tt, color="r", ls="--", lw=1, label=f"T_target={Tt:.0f}°C")
        plt.xlabel("t (s)"); plt.ylabel("中心温度 (°C)")
        plt.title("钢件中心冷却曲线"); plt.legend(); plt.grid()
        figs.append(fig2)

    return {
        "figures": figs,
        "data": {
            "t_center_target": t_center_target,
            "T_center": np.array(T_center),
            "t_arr": np.array(t_arr),
            "x": x,
            "U_snap": U_snap,
            "t_snap": t_snap,
            "steady_reached": bool(steady_reached),
            "dt": dt,
        },
    }


solve = solve_heat  # 统一接口别名（app.py 通过 .solve 调用）


if __name__ == "__main__":
    d = solve_heat()["data"]
    print(f"中心降到 100°C: {d['t_center_target']:.1f}s | 稳态达到: {d['steady_reached']}")
