"""单摆（Simple Pendulum）数值仿真求解器 —— scipy 版。

由 MATLAB 版 simple_pendulum_cn.m 翻译而来（2026-08-08 MATLABLi 原作）。

物理方程（力矩平衡）:
    m*l^2*thdd + c*thd + m*g*l*sin(th) = u(t)
    - m*l^2*thdd  惯性力矩（thdd = 角加速度）
    - c*thd       阻尼力矩（thd = 角速度, c = 阻尼系数）
    - m*g*l*sin(th)  重力恢复力矩
    - u(t)        外加驱动力矩（默认 0 = 自由摆动）

本模块是"计算引擎"：只负责数值求解 + 返回数据，不画图。
画图/前端由上层（app/）负责。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# 默认物理参数（与 MATLAB 版一致）
DEFAULT_PARAMS: dict = {
    "m": 1.0,     # 摆锤质量 [kg]
    "l": 1.0,     # 摆长 [m]
    "g": 9.81,    # 重力加速度 [m/s^2]
    "c": 0.08,    # 阻尼系数 [N*m*s/rad]
}


def pendulum_deriv(t: float, y: list[float], p: dict) -> list[float]:
    """运动方程右端：返回 [角速度; 角加速度]。

    t 未用到但保留（solve_ivp 约定传参）。y = [theta(rad), omega(rad/s)]。
    """
    th, w = y
    u = 0.0  # 无外加驱动力矩
    thdd = (u - p["c"] * w - p["m"] * p["g"] * p["l"] * np.sin(th)) / (p["m"] * p["l"] ** 2)
    return [w, thdd]


def solve_pendulum(
    th0_deg: float = 120.0,
    w0: float = 0.0,
    t_span: tuple[float, float] = (0.0, 20.0),
    params: dict | None = None,
    max_step: float = 0.02,
) -> dict:
    """数值求解单摆，返回轨迹数据。

    参数:
        th0_deg: 初始摆角 [度]
        w0:      初始角速度 [rad/s]
        t_span:  (t_start, t_end)
        params:  覆盖默认物理参数（如 {"c": 0} 表示无阻尼）
        max_step: 求解最大步长（越小越精细）

    返回:
        {"t": np.ndarray, "th_deg": np.ndarray, "omega": np.ndarray,
         "energy": np.ndarray, "params": dict}
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    x0 = [np.deg2rad(th0_deg), w0]
    sol = solve_ivp(
        pendulum_deriv,
        t_span,
        x0,
        args=(p,),
        rtol=1e-9,
        atol=1e-11,
        max_step=max_step,
    )
    th = sol.y[0]          # 摆角 [rad]
    w = sol.y[1]           # 角速度 [rad/s]
    # 机械能 E = 动能 + 势能（势能零点在最低点 th=0）
    E = 0.5 * p["m"] * p["l"] ** 2 * w**2 + p["m"] * p["g"] * p["l"] * (1 - np.cos(th))
    return {
        "t": sol.t,
        "th_deg": np.rad2deg(th),
        "omega": w,
        "energy": E,
        "params": p,
    }


def _positive_peak_idx(th: np.ndarray) -> np.ndarray:
    """找正波峰索引（斜率正变负且角度>0）。"""
    dth = np.diff(th)
    return np.where((dth[:-1] > 0) & (dth[1:] < 0) & (th[1:-1] > 0))[0] + 1


def period_checks(th0_deg: float = 120.0, params: dict | None = None) -> dict:
    """跑一遍并返回物理验证指标（对齐 MATLAB 版的数值验证块）。

    返回:
        {
          "T0_small": 小角度线性周期 2*pi*sqrt(l/g),
          "T_num":    数值周期（正波峰平均间隔）,
          "T_series": 大角度周期级数近似 T0*(1 + th0^2/16 + 11*th0^4/3072),
          "T_ratio":  T_num/T0 (>1 说明大角度使周期变长),
          "E0":       初始机械能 [J],
          "E_end":    终点机械能 [J]（有阻尼应衰减）,
          "undamped_drift": 无阻尼能量相对漂移 (≈0 = 守恒),
        }
    """
    p = {**DEFAULT_PARAMS, **(params or {})}
    res = solve_pendulum(th0_deg=th0_deg, params=p)
    th = np.deg2rad(res["th_deg"])

    # 1) 小角度线性周期
    T0 = 2 * np.pi * np.sqrt(p["l"] / p["g"])

    # 2) 数值周期：正波峰平均间隔
    pk = _positive_peak_idx(th)
    T_num = float(np.mean(np.diff(res["t"][pk]))) if pk.size >= 2 else None

    # 3) 大角度周期级数近似（保留到 4 阶）
    th0 = np.deg2rad(th0_deg)
    T_series = T0 * (1 + th0**2 / 16 + 11 * th0**4 / 3072)

    # 4) 能量衰减（有阻尼）与守恒（无阻尼）
    E0, E_end = float(res["energy"][0]), float(res["energy"][-1])

    p0 = {**p, "c": 0.0}  # 无阻尼对比
    res0 = solve_pendulum(th0_deg=th0_deg, params=p0)
    drift = float((res0["energy"].max() - res0["energy"].min()) / res0["energy"][0])
    pk0 = _positive_peak_idx(np.deg2rad(res0["th_deg"]))
    T_num0 = float(np.mean(np.diff(res0["t"][pk0]))) if pk0.size >= 2 else None

    return {
        "T0_small": float(T0),
        "T_num": T_num,
        "T_series": float(T_series),
        "T_ratio": float(T_num / T0) if T_num else None,
        "E0": E0,
        "E_end": E_end,
        "undamped_drift": drift,
        "undamped_T_num": T_num0,
    }


if __name__ == "__main__":
    import json

    print("---- single pendulum (scipy) checks ----")
    checks = period_checks(th0_deg=120.0)
    print(json.dumps(checks, indent=2))


def plot_pendulum(result: dict) -> list:
    """由 solve_pendulum 结果绘制 4 张图：摆角/角速度/相平面/能量。"""
    t = result["t"]
    th = result["th_deg"]
    w = result["omega"]
    E = result["energy"]
    fig1 = plt.figure(figsize=(6, 4))
    plt.plot(t, th, lw=1.5)
    plt.xlabel("t (s)"); plt.ylabel("θ (deg)"); plt.title("摆角 - 时间"); plt.grid()
    fig2 = plt.figure(figsize=(6, 4))
    plt.plot(t, w, lw=1.5)
    plt.xlabel("t (s)"); plt.ylabel("ω (rad/s)"); plt.title("角速度 - 时间"); plt.grid()
    fig3 = plt.figure(figsize=(6, 4))
    plt.plot(th, w, lw=1.2)
    plt.xlabel("θ (deg)"); plt.ylabel("ω (rad/s)"); plt.title("相平面"); plt.grid()
    fig4 = plt.figure(figsize=(6, 4))
    plt.plot(t, E, lw=1.5)
    plt.xlabel("t (s)"); plt.ylabel("E (J)"); plt.title("机械能 - 时间"); plt.grid()
    return [fig1, fig2, fig3, fig4]


def solve(params: dict | None = None) -> dict:
    """统一引擎接口：solve(params) -> {"figures": [...], "data": {...}}。

    物理键（m/l/g/c）交给求解器；控制键（th0_deg/w0/t_end）单独处理。
    """
    p = params or {}
    th0 = p.get("th0_deg", 120.0)
    w0 = p.get("w0", 0.0)
    t_end = p.get("t_end", 20.0)
    phys = {k: v for k, v in p.items() if k in DEFAULT_PARAMS}
    res = solve_pendulum(th0_deg=th0, w0=w0, t_span=(0.0, t_end), params=phys)
    figs = plot_pendulum(res)
    ck = period_checks(th0_deg=th0, params=phys)
    data = {
        "T_num": ck["T_num"],
        "T0_small": ck["T0_small"],
        "T_ratio": ck["T_ratio"],
        "E0": ck["E0"],
        "E_end": ck["E_end"],
        "th0_deg": th0,
        "params": res["params"],
    }
    return {"figures": figs, "data": data}
