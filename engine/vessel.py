"""压力容器壁厚 —— 薄壁圆筒（环向应力主导）。

ASME 薄壁容器公式: t = P*D/(2*sigma_allow)
    t: 所需壁厚 [m], P: 内压 [Pa], D: 内径 [m], sigma_allow: 许用应力 [Pa]
校核模式: 给定壁厚 t，实际应力 sigma = P*D/(2*t)，sigma <= sigma_allow 安全。
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

DEFAULT_PARAMS = {
    "P": 1e6,             # 内压 [Pa]
    "D": 1.0,             # 内径 [m]
    "sigma_allow": 100e6, # 许用应力 [Pa]
    "t_given": None,      # 校核用给定壁厚 [m]（None=只求所需壁厚）
}


def solve_vessel(params: dict | None = None, plot: bool = True) -> dict:
    """求所需壁厚 + 可选校核给定壁厚，返回壁厚-压力曲线 + 关键数据。

    plot=False 时跳过 matplotlib 画图（供敏感性扫描提速）。
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    P, D, sigma = p["P"], p["D"], p["sigma_allow"]
    t_req = P * D / (2 * sigma)
    t_given = p.get("t_given")
    sigma_actual = P * D / (2 * t_given) if t_given else None
    safe = sigma_actual is not None and sigma_actual <= sigma

    P_arr = np.linspace(0.5 * P, 1.5 * P, 50)
    t_arr = P_arr * D / (2 * sigma)

    figs = []
    if plot:
        fig = plt.figure(figsize=(6, 4))
        plt.plot(P_arr / 1e6, t_arr * 1000, "b-", lw=1.8)
        plt.plot(P / 1e6, t_req * 1000, "ro", ms=8, mfc="r")
        plt.xlabel("内压 P (MPa)"); plt.ylabel("所需壁厚 t (mm)")
        plt.title(f"薄壁圆筒壁厚 | 当前 P={P/1e6:.2f} MPa → t={t_req*1000:.2f} mm")
        plt.grid()
        figs.append(fig)

    return {
        "figures": figs,
        "data": {
            "t_req": float(t_req), "t_req_mm": float(t_req * 1000),
            "P": float(P), "D": float(D), "sigma_allow": float(sigma),
            "t_given": t_given,
            "sigma_actual": float(sigma_actual) if sigma_actual is not None else None,
            "safe": safe,
        },
    }


solve = solve_vessel  # 统一接口别名（app.py 通过 .solve 调用）


if __name__ == "__main__":
    d = solve_vessel()["data"]
    print(f"t_req={d['t_req']:.6f} m ({d['t_req_mm']:.3f} mm)")
