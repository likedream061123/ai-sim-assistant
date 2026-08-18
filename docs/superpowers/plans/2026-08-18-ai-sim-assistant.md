# AI 工程仿真助手 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 参赛作品「AI 工程仿真助手」：用户用中文描述工程问题 → AI 解析参数 → scipy 数值求解 → 图表 + 大白话解读。4 个工程场景（单摆/钢件冷却/钢梁挠度/压力容器壁厚）。

**Architecture:** Streamlit 单进程编排层（app.py）+ 纯计算引擎层（engine/，每场景一模块，统一 `solve(params)->{"figures","data"}` 接口）+ AI 解析层（agent/，DeepSeek 中文→JSON）。引擎零 LLM/界面依赖、可独立测试；数值全部对照验证基准（MATLAB 脚本 / ASME 标准值）。

**Tech Stack:** Python 3.10+, Streamlit, numpy, scipy, matplotlib, openai（DeepSeek 兼容接口）, requests（SerpApi）, pytest。

## Global Constraints

- 引擎模块（engine/*.py）**禁止** import streamlit / openai / requests —— 只做数值计算 + matplotlib 画图。
- 统一引擎接口：`solve(params: dict) -> {"figures": list[plt.Figure], "data": dict}`。`data` 只含 JSON 可序列化的标量/简单类型，供 app 展示与 AI 解读。
- 验证基准（写进测试断言，必须精确）：单摆 T0=2π√(l/g)（pendulum.py 已验）；梁 v_max=1.2265e-4 m（L=4,P=1e4,a=1.5,E=200e9,I=5e-4）；热 t_center_target≈872.5s（实测，断言区间 600-1200）；容器 t_req=P·D/(2σ)。
- API key 从环境变量读：`DEEPSEEK_API_KEY`、`SERPAPI_KEY`。测试用 mock，**不**真调 API。
- 全部中文注释、中文 UI。
- 场景封顶 4 个；压力容器（vessel）时间不够可砍（删 engine/vessel.py + app.py 对应分支 + tests/test_vessel.py）。
- 每任务结束 commit 一次。

---

### Task 1 (M1): 项目脚手架与依赖

**Files:**
- Create: `requirements.txt`
- Create: `engine/__init__.py`
- Create: `agent/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Consumes: 无（engine/pendulum.py 已存在）
- Produces: 可 import 的包结构 `engine.*`、`agent.*`；pytest 可运行

- [ ] **Step 1: 写 requirements.txt**

```text
streamlit>=1.30
numpy
scipy
matplotlib
openai
requests
pytest
```

- [ ] **Step 2: 建包结构**

创建空文件 `engine/__init__.py`、`agent/__init__.py`、`tests/__init__.py`。`tests/conftest.py` 内容（把项目根加进 sys.path）：

```python
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

- [ ] **Step 3: 验证导入**

Run: `PYTHONIOENCODING=utf-8 python -c "import engine.pendulum, matplotlib.pyplot; import pytest; print('ok')"`
Expected: 输出 `ok`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt engine/__init__.py agent/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: 项目脚手架 + 依赖"
```

---

### Task 2 (M1): 单摆绘图 + 统一 solve 接口

**Files:**
- Modify: `engine/pendulum.py`
- Create: `tests/test_pendulum.py`

**Interfaces:**
- Consumes: `solve_pendulum(th0_deg, w0, t_span, params, max_step) -> {"t","th_deg","omega","energy","params"}`、`period_checks(th0_deg, params)`（已存在）
- Produces: `engine.pendulum.solve(params) -> {"figures", "data"}`（4 图 + 关键数据）

- [ ] **Step 1: 写失败测试** `tests/test_pendulum.py`

```python
import numpy as np
from engine.pendulum import solve, solve_pendulum


def test_solve_returns_four_figures():
    res = solve({"th0_deg": 120.0})
    assert len(res["figures"]) == 4


def test_solve_data_has_checks():
    res = solve({"th0_deg": 120.0})
    assert res["data"]["T_num"] > 0
    assert res["data"]["T_ratio"] > 1.0   # 大角度周期变长


def test_undamped_energy_conservation():
    res = solve_pendulum(th0_deg=120.0, params={"c": 0.0})
    drift = (res["energy"].max() - res["energy"].min()) / res["energy"][0]
    assert drift < 1e-4
```

- [ ] **Step 2: 跑测试验证失败**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_pendulum.py -v`
Expected: 3 个 FAIL，报 `cannot import name 'solve'`

- [ ] **Step 3: 实现** —— `engine/pendulum.py` 顶部 import 区加一行：

```python
import matplotlib.pyplot as plt
```

文件末尾追加：

```python
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
```

- [ ] **Step 4: 跑测试验证通过**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_pendulum.py -v`
Expected: 3 个 PASS

- [ ] **Step 5: Commit**

```bash
git add engine/pendulum.py tests/test_pendulum.py
git commit -m "feat(engine): 单摆统一 solve 接口 + 4 图绘图"
```

---

### Task 3 (M1): app.py 骨架 + 单摆手动模式

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `engine.pendulum.solve(params)`
- Produces: 可 `streamlit run app.py` 的单摆页面（手动表单 → 图 + 数据）

- [ ] **Step 1: 写 app.py**（先只做单摆手动模式，四场景 Task 7 扩展）

```python
"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。"""
import streamlit as st
import engine.pendulum

st.set_page_config(page_title="AI 工程仿真助手", page_icon="⚙️")
st.title("⚙️ AI 工程仿真助手")
st.caption("工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。")

scenario = "pendulum"  # 暂固定单摆，Task 7 换下拉
c1, c2, c3 = st.columns(3)
th0 = c1.number_input("初始角度 θ₀ (°)", 0.0, 180.0, 120.0)
w0 = c2.number_input("初始角速度 ω₀ (rad/s)", 0.0, 20.0, 0.0)
t_end = c3.number_input("时长 (s)", 1.0, 60.0, 20.0)

if st.button("计算", type="primary"):
    res = engine.pendulum.solve({"th0_deg": th0, "w0": w0, "t_end": t_end})
    for fig in res["figures"]:
        st.pyplot(fig)
    st.subheader("关键数据")
    d = res["data"]
    st.write(f"- **周期 T（数值）**: {d['T_num']:.3f} s")
    st.write(f"- **小角度理论周期**: {d['T0_small']:.3f} s")
    st.write(f"- **周期比 T/T0**: {d['T_ratio']:.3f}（>1 说明大角度使周期变长）")
    st.write(f"- **初始能量 E0**: {d['E0']:.2f} J → 终点 {d['E_end']:.2f} J")
```

- [ ] **Step 2: 手动验收**

Run: `streamlit run app.py` → 浏览器 http://localhost:8501
Expected: 参数表单，点「计算」出 4 张单摆图 + 关键数据，T_num≈2.25s 与 MATLAB 一致。
Manual（Streamlit UI 不单测，验收 = 能跑、图能出、数字合理）。

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(app): Streamlit 单摆页面（手动表单 → 图+数据）"
```

### Task 4 (M2): 钢件冷却引擎

**Files:**
- Create: `engine/heat.py`
- Create: `tests/test_heat.py`

**Interfaces:**
- Consumes: 无
- Produces: `engine.heat.solve(params) -> {"figures": [...], "data": {...}}`；`engine.heat.DEFAULT_PARAMS`

**物理模型：** 一维热扩散 du/dt=α·d²u/dx²，无内热源。钢件半宽 L，x=0 中心（对称 Neumann 反射），x=L 表面（Dirichlet 恒温 T_wall，模拟泡淬火介质立即冷却）。初始均匀 T0，求中心降到 T_target 的时间。差分内核对照 MATLAB `heat1d_explicit.m`（显式格式，r<0.5 稳定）。

- [ ] **Step 1: 写失败测试** `tests/test_heat.py`

```python
import numpy as np
from engine.heat import solve_heat


def test_center_temperature_decreases():
    res = solve_heat({"tmax": 200.0})
    d = res["data"]
    assert d["T_center"][0] > d["T_center"][-1]


def test_center_tends_to_wall_temp():
    res = solve_heat({"tmax": 3600.0})
    d = res["data"]
    assert d["T_center"][-1] < 30.0          # 长时趋近壁温 20°C


def test_target_time_reasonable():
    res = solve_heat()
    t = res["data"]["t_center_target"]
    assert t is not None
    assert 600.0 < t < 1200.0                # 实测 872.5s


def test_returns_two_figures():
    res = solve_heat()
    assert len(res["figures"]) == 2
```

- [ ] **Step 2: 跑测试验证失败**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_heat.py -v`
Expected: FAIL，报 `ModuleNotFoundError: No module named 'engine.heat'`

- [ ] **Step 3: 实现** `engine/heat.py`

```python
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


def solve_heat(params: dict | None = None) -> dict:
    """显式差分求解钢件冷却，返回中心温度曲线 + 冷却到目标温度的时间。

    返回 {"figures": [温度分布快照, 中心温度曲线], "data": {...}}。
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
    U_snap, t_snap = [u.copy()], [0.0]

    for n in range(1, nstep + 1):
        # 左 Neumann 反射（中心对称），右 Dirichlet 固定（表面恒温）
        uext = np.concatenate(([u[1]], u, [Tw]))
        lap = uext[2:] - 2 * uext[1:-1] + uext[:-2]
        u = u + r * lap
        u[-1] = Tw
        if n % plot_interval == 0:
            U_snap.append(u.copy())
            t_snap.append(n * dt)
        if t_center_target is None and u[0] <= Tt:
            t_center_target = n * dt
        if n % 100 == 0:
            T_center.append(float(u[0]))
            t_arr.append(n * dt)

    steady_reached = abs(float(u[-1] - u[0])) < 1e-6   # 全场趋同（壁温）

    fig1 = plt.figure(figsize=(6, 4))
    for k in range(len(U_snap)):
        plt.plot(x, U_snap[k], label=f"t={t_snap[k]:.0f}s")
    plt.xlabel("x (m, 0=中心)"); plt.ylabel("T (°C)")
    plt.title("钢件冷却：温度分布快照"); plt.legend(); plt.grid()

    fig2 = plt.figure(figsize=(6, 4))
    plt.plot(t_arr, T_center, "b-", lw=1.8)
    plt.axhline(Tt, color="r", ls="--", lw=1, label=f"T_target={Tt:.0f}°C")
    plt.xlabel("t (s)"); plt.ylabel("中心温度 (°C)")
    plt.title("钢件中心冷却曲线"); plt.legend(); plt.grid()

    return {
        "figures": [fig1, fig2],
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
```

- [ ] **Step 4: 跑测试验证通过**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_heat.py -v`
Expected: 4 个 PASS（t_center_target≈872.5s 落在断言区间）

- [ ] **Step 5: Commit**

```bash
git add engine/heat.py tests/test_heat.py
git commit -m "feat(engine): 钢件冷却引擎（显式差分，中心冷却时间）"
```

### Task 5 (M2): 钢梁挠度引擎

**Files:**
- Create: `engine/beam.py`
- Create: `tests/test_beam.py`

**Interfaces:**
- Consumes: 无
- Produces: `engine.beam.solve(params) -> {"figures": [挠度曲线, 弯矩图], "data": {...}}`

**物理模型（对照 MATLAB `beam_deflection.m` 符号推导）：** 简支梁长 L，距左端 a 处集中力 P，E 弹性模量、I 惯性矩。挠度向下为正。两段公式 v1(0≤x≤a)、v2(a≤x≤L)；弯矩 M1=P·b·x/L、M2=P·a·(L-x)/L（b=L-a）。

- [ ] **Step 1: 写失败测试** `tests/test_beam.py`

```python
import numpy as np
from engine.beam import solve_beam


def test_vmax_matches_matlab():
    d = solve_beam()["data"]
    assert abs(d["v_max"] - 1.2265e-4) < 1e-6   # MATLAB 符号法结果（L=4,P=1e4,a=1.5）


def test_mmax_at_load_point():
    d = solve_beam()["data"]
    assert abs(d["M_max"] - 9375.0) < 1.0        # P*a*b/L = 10000*1.5*2.5/4


def test_zero_deflection_at_ends():
    L, P, a, E, I = 4.0, 10000.0, 1.5, 200e9, 5e-4
    b = L - a
    assert P * b * 0 / (6 * E * I * L) * (L * L - b * b - 0) == 0.0   # v1(0)=0
    v2L = P * b / (6 * E * I * L) * ((L / b) * b ** 3 + (L * L - b * b) * L - L ** 3)
    assert abs(v2L) < 1e-12                                            # v2(L)=0


def test_within_limit_flag():
    d = solve_beam()["data"]
    assert d["within_limit"] is True            # 0.123mm << L/360=11.1mm
```

- [ ] **Step 2: 跑测试验证失败**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_beam.py -v`
Expected: FAIL，报 `ModuleNotFoundError: No module named 'engine.beam'`

- [ ] **Step 3: 实现** `engine/beam.py`

```python
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

DEFAULT_PARAMS = {
    "L": 4.0,         # 梁长 [m]
    "P": 10000.0,     # 集中荷载 [N]
    "a": 1.5,         # 荷载距左端距离 [m]
    "E": 200e9,       # 弹性模量 [Pa]（钢 200 GPa）
    "I": 5e-4,        # 截面惯性矩 [m^4]
}


def solve_beam(params: dict | None = None) -> dict:
    """数值求最大挠度/弯矩，返回挠度曲线 + 弯矩图 + 关键数据。"""
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

    fig1 = plt.figure(figsize=(6, 4))
    plt.plot(xx, vv * 1000, "b-", lw=1.8)
    plt.plot(x_max, v_max * 1000, "ro", ms=8, mfc="r")
    plt.xlabel("x (m)"); plt.ylabel("挠度 v(x) (mm, 向下为正)")
    plt.title(f"钢梁挠度 | 最大 {v_max*1000:.3f} mm @ x={x_max:.3f} m")
    plt.grid()

    fig2 = plt.figure(figsize=(6, 4))
    plt.plot(xx, Mm, "r-", lw=1.8)
    plt.xlabel("x (m)"); plt.ylabel("弯矩 M(x) (N·m)")
    plt.title(f"弯矩图 | 最大 |M| = {M_max:.0f} N·m @ x={x_Mmax:.3f} m")
    plt.grid()

    return {
        "figures": [fig1, fig2],
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
```

- [ ] **Step 4: 跑测试验证通过**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_beam.py -v`
Expected: 4 个 PASS

- [ ] **Step 5: Commit**

```bash
git add engine/beam.py tests/test_beam.py
git commit -m "feat(engine): 钢梁挠度引擎（两段公式 + 弯矩图）"
```

### Task 6 (M2): 压力容器壁厚引擎

**Files:**
- Create: `engine/vessel.py`
- Create: `tests/test_vessel.py`

**Interfaces:**
- Consumes: 无
- Produces: `engine.vessel.solve(params) -> {"figures": [壁厚-压力曲线], "data": {...}}`

**物理（ASME 薄壁容器）：** 环向应力主导，所需壁厚 t=P·D/(2·σ_allow)。校核模式：给定壁厚 t，实际应力 σ=P·D/(2t)，σ≤σ_allow 安全。

- [ ] **Step 1: 写失败测试** `tests/test_vessel.py`

```python
import numpy as np
from engine.vessel import solve_vessel


def test_thickness_standard_value():
    d = solve_vessel({"P": 1e6, "D": 1.0, "sigma_allow": 100e6})["data"]
    assert abs(d["t_req"] - 0.005) < 1e-8   # ASME 薄壁公式标准值 5mm


def test_thickness_linear_in_pressure():
    t1 = solve_vessel({"P": 1e6, "D": 1.0, "sigma_allow": 100e6})["data"]["t_req"]
    t2 = solve_vessel({"P": 2e6, "D": 1.0, "sigma_allow": 100e6})["data"]["t_req"]
    assert abs(t2 - 2 * t1) < 1e-12


def test_check_given_thickness():
    d = solve_vessel({"P": 1e6, "D": 1.0, "sigma_allow": 100e6, "t_given": 0.01})["data"]
    assert abs(d["sigma_actual"] - 5e7) < 1.0
    assert d["safe"] is True
```

- [ ] **Step 2: 跑测试验证失败**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_vessel.py -v`
Expected: FAIL，报 `ModuleNotFoundError: No module named 'engine.vessel'`

- [ ] **Step 3: 实现** `engine/vessel.py`

```python
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


def solve_vessel(params: dict | None = None) -> dict:
    """求所需壁厚 + 可选校核给定壁厚，返回壁厚-压力曲线 + 关键数据。"""
    p = {**DEFAULT_PARAMS, **(params or {})}
    P, D, sigma = p["P"], p["D"], p["sigma_allow"]
    t_req = P * D / (2 * sigma)
    t_given = p.get("t_given")
    sigma_actual = P * D / (2 * t_given) if t_given else None
    safe = sigma_actual is not None and sigma_actual <= sigma

    P_arr = np.linspace(0.5 * P, 1.5 * P, 50)
    t_arr = P_arr * D / (2 * sigma)

    fig = plt.figure(figsize=(6, 4))
    plt.plot(P_arr / 1e6, t_arr * 1000, "b-", lw=1.8)
    plt.plot(P / 1e6, t_req * 1000, "ro", ms=8, mfc="r")
    plt.xlabel("内压 P (MPa)"); plt.ylabel("所需壁厚 t (mm)")
    plt.title(f"薄壁圆筒壁厚 | 当前 P={P/1e6:.2f} MPa → t={t_req*1000:.2f} mm")
    plt.grid()

    return {
        "figures": [fig],
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
```

- [ ] **Step 4: 跑测试验证通过**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_vessel.py -v`
Expected: 3 个 PASS

- [ ] **Step 5: Commit**

```bash
git add engine/vessel.py tests/test_vessel.py
git commit -m "feat(engine): 压力容器壁厚引擎（ASME 薄壁公式 + 校核）"
```

### Task 7 (M2): app.py 四场景渲染（统一路由）

**Files:**
- Modify: `app.py`（整体替换为四场景版）

**Interfaces:**
- Consumes: `engine.{pendulum,heat,beam,vessel}.solve(params)`
- Produces: 四场景下拉 + 每场景参数表单 → 图 + 数据

- [ ] **Step 1: 替换 app.py**（Streamlit UI 不单测，直接实现 + 手动验收）

```python
"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。"""
import streamlit as st
import engine.pendulum, engine.heat, engine.beam, engine.vessel

SCENARIOS = {
    "单摆 (动力学)": "pendulum",
    "钢件冷却 (热处理)": "heat",
    "钢梁挠度 (结构校核)": "beam",
    "压力容器壁厚 (设计)": "vessel",
}
ENGINES = {
    "pendulum": engine.pendulum,
    "heat": engine.heat,
    "beam": engine.beam,
    "vessel": engine.vessel,
}

st.set_page_config(page_title="AI 工程仿真助手", page_icon="⚙️")
st.title("⚙️ AI 工程仿真助手")
st.caption("工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。")


def render_result(scenario: str, params: dict):
    try:
        res = ENGINES[scenario].solve(params)
    except Exception as e:
        st.error(f"计算失败：{e}")
        return
    for fig in res["figures"]:
        st.pyplot(fig)
    st.subheader("关键数据")
    for k, v in res["data"].items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            st.write(f"- **{k}**: {v}")


scenario_label = st.selectbox("场景", list(SCENARIOS))
scenario = SCENARIOS[scenario_label]
params = {}

if scenario == "pendulum":
    c1, c2, c3 = st.columns(3)
    params["th0_deg"] = c1.number_input("初始角度 θ₀ (°)", 0.0, 180.0, 120.0)
    params["w0"] = c2.number_input("初始角速度 ω₀ (rad/s)", 0.0, 20.0, 0.0)
    params["t_end"] = c3.number_input("时长 (s)", 1.0, 60.0, 20.0)
elif scenario == "heat":
    c1, c2, c3 = st.columns(3)
    params["L"] = c1.number_input("钢件半宽 (m)", 0.01, 1.0, 0.1, format="%.3f")
    params["T0"] = c2.number_input("初始温度 (°C)", 100.0, 1500.0, 800.0)
    params["T_wall"] = c3.number_input("介质温度 (°C)", 0.0, 500.0, 20.0)
    params["T_target"] = st.number_input("目标温度 (°C)", 0.0, 1500.0, 100.0)
elif scenario == "beam":
    c1, c2, c3 = st.columns(3)
    params["L"] = c1.number_input("梁长 (m)", 0.1, 20.0, 4.0)
    params["P"] = c2.number_input("集中荷载 (N)", 100.0, 1e6, 10000.0, format="%.0f")
    params["a"] = c3.number_input("荷载距左端 (m)", 0.1, 19.9, 1.5)
    c4, c5 = st.columns(2)
    params["E"] = c4.number_input("弹性模量 E (Pa)", 1e9, 1e12, 200e9, format="%.3g")
    params["I"] = c5.number_input("惯性矩 I (m4)", 1e-8, 1.0, 5e-4, format="%.3g")
elif scenario == "vessel":
    c1, c2, c3 = st.columns(3)
    params["P"] = c1.number_input("内压 (Pa)", 1e4, 1e8, 1e6, format="%.3g")
    params["D"] = c2.number_input("内径 (m)", 0.1, 10.0, 1.0)
    params["sigma_allow"] = c3.number_input("许用应力 (Pa)", 1e7, 1e9, 100e6, format="%.3g")

if st.button("计算", type="primary"):
    render_result(scenario, params)
```

- [ ] **Step 2: 手动验收**

Run: `streamlit run app.py`
Expected: 下拉切 4 个场景，各填参数点「计算」都能出图 + 数据（单摆 4 图、钢件冷却 2 图、钢梁 2 图、压力容器 1 图）。

- [ ] **Step 3: 回归引擎测试**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/ -v`
Expected: 全部 PASS（pendulum 3 + heat 4 + beam 4 + vessel 3）

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat(app): 四场景统一路由 + 每场景参数表单"
```

### Task 8 (M3): LLM 解析层 + 自然语言接入

**Files:**
- Create: `agent/llm.py`
- Create: `tests/test_llm.py`
- Modify: `app.py`（替换为含双模式 + AI 解读的最终版）

**Interfaces:**
- Consumes: `engine.*.solve(params)`（Task 2/4/5/6）
- Produces: `agent.llm.parse_query(text) -> {"scenario": str, "params": dict}`（不识别/解析失败抛 `ValueError`）；`agent.llm.explain(scenario, data) -> str`

**要点：** LLM 只做"人话→参数"，数值永远交给引擎。测试全部 mock `_client`，**不真调 API**。API key 从环境变量 `DEEPSEEK_API_KEY` 读。

- [ ] **Step 1: 写失败测试** `tests/test_llm.py`

```python
import pytest
from unittest.mock import patch, Mock
from agent import llm


def test_parse_query_pendulum():
    fake = Mock()
    fake.choices[0].message.content = '{"scenario":"pendulum","params":{"th0_deg":120}}'
    with patch("agent.llm._client") as m:
        m.return_value.chat.completions.create.return_value = fake
        r = llm.parse_query("一个初始角度120度的单摆")
    assert r["scenario"] == "pendulum"
    assert r["params"]["th0_deg"] == 120


def test_parse_query_unknown_scenario_raises():
    fake = Mock()
    fake.choices[0].message.content = '{"scenario":"rocket","params":{}}'
    with patch("agent.llm._client") as m:
        m.return_value.chat.completions.create.return_value = fake
        with pytest.raises(ValueError):
            llm.parse_query("火箭发射")


def test_explain_returns_text():
    fake = Mock()
    fake.choices[0].message.content = "结果合理。"
    with patch("agent.llm._client") as m:
        m.return_value.chat.completions.create.return_value = fake
        out = llm.explain("beam", {"v_max": 1e-4})
    assert isinstance(out, str) and len(out) > 0
```

- [ ] **Step 2: 跑测试验证失败**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_llm.py -v`
Expected: FAIL，报 `ModuleNotFoundError: No module named 'agent.llm'`

- [ ] **Step 3: 实现** `agent/llm.py`

```python
"""DeepSeek 解析层: 中文工程问题 → 结构化 JSON。

只做"人话→参数"翻译，不做任何计算。数值交给引擎。
LLM 输出结构化 JSON，解析失败或不识别场景抛 ValueError（app 层兜底手动表单）。
"""
from __future__ import annotations

import json
import os
from openai import OpenAI

SCENARIOS = ("pendulum", "heat", "beam", "vessel")
BASE_URL = "https://api.deepseek.com"


def _client(api_key: str | None = None) -> OpenAI:
    key = api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("缺少 DEEPSEEK_API_KEY（环境变量或参数）")
    return OpenAI(api_key=key, base_url=BASE_URL)


def parse_query(text: str, api_key: str | None = None) -> dict:
    """把一句中文工程问题解析为 {"scenario": ..., "params": {...}}。

    失败/不识别场景时抛 ValueError。
    """
    sys_prompt = (
        "你是工程计算参数解析器。用户用中文描述一个工程问题，你识别场景并提取参数，只输出 JSON。\n"
        "场景只能是: pendulum(单摆/摆) heat(钢件冷却/热处理/降温) beam(梁/挠度/弯曲) vessel(压力容器/壁厚)。\n"
        "参数用 camelCase，沿用字段名: \n"
        "  pendulum: th0_deg(初始角度度) w0(初始角速度) t_end(时长) m l g c\n"
        "  heat: L(半宽m) T0(初始°C) T_wall(介质°C) T_target(目标°C) alpha\n"
        "  beam: L(梁长m) P(荷载N) a(距左端m) E(弹性模量Pa) I(惯性矩m^4)\n"
        "  vessel: P(内压Pa) D(内径m) sigma_allow(许用应力Pa) t_given(给定壁厚m)\n"
        "只填用户明确提到的参数，缺的不要编造。单位换算: MPa→Pa 乘1e6，mm→m 除1000，kN→N 乘1000，GPa→Pa 乘1e9。\n"
        '输出格式: {"scenario": "...", "params": {...}}'
    )
    try:
        resp = _client(api_key).chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": text}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        data = json.loads(resp.choices[0].message.content)
        if data.get("scenario") not in SCENARIOS:
            raise ValueError(f"场景不识别: {data.get('scenario')}")
        return data
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"解析失败: {e}") from e


def explain(scenario: str, data: dict, api_key: str | None = None) -> str:
    """对计算结果生成 ≤80 字大白话解读（结果区展示）。"""
    sys_prompt = (
        "你是工程仿真助手，用不超过80字的大白话解释一次计算的结果。"
        "面向非专业用户，说清楚'结果是什么、合理吗、要注意什么'。"
    )
    try:
        resp = _client(api_key).chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": f"场景={scenario}，关键数据={json.dumps(data, ensure_ascii=False)}"}],
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception:
        return "（AI 解读暂不可用，请直接看数据和图）"
```

- [ ] **Step 4: 跑测试验证通过**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_llm.py -v`
Expected: 3 个 PASS（全 mock，不需要真 key）

- [ ] **Step 5: 替换 app.py 为最终版**（双模式 + AI 解读；无 SerpApi 按钮，Task 9 加）

```python
"""AI 工程仿真助手 —— Streamlit 主入口（编排层）。

架构: 输入 → (可选) LLM 解析 → 引擎计算 → 图+数据+解读。
引擎只管算，本文件只管串。手动表单是解析失败的兜底。
"""
import streamlit as st
import engine.pendulum, engine.heat, engine.beam, engine.vessel
from agent import llm

SCENARIOS = {
    "单摆 (动力学)": "pendulum",
    "钢件冷却 (热处理)": "heat",
    "钢梁挠度 (结构校核)": "beam",
    "压力容器壁厚 (设计)": "vessel",
}
ENGINES = {
    "pendulum": engine.pendulum,
    "heat": engine.heat,
    "beam": engine.beam,
    "vessel": engine.vessel,
}

st.set_page_config(page_title="AI 工程仿真助手", page_icon="⚙️")
st.title("⚙️ AI 工程仿真助手")
st.caption("工程问题一句话 → AI 解析 → 数值真算 → 图表 + 大白话解读。数值永不猜。")


def render_result(scenario: str, params: dict, note: str = ""):
    if note:
        st.info(note)
    try:
        res = ENGINES[scenario].solve(params)
    except Exception as e:
        st.error(f"计算失败：{e}")
        return
    for fig in res["figures"]:
        st.pyplot(fig)
    st.subheader("关键数据")
    for k, v in res["data"].items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            st.write(f"- **{k}**: {v}")
    try:
        simple = {k: v for k, v in res["data"].items()
                  if isinstance(v, (int, float, str, bool)) or v is None}
        with st.spinner("生成解读…"):
            text = llm.explain(scenario, simple)
        st.subheader("AI 解读")
        st.write(text)
    except Exception:
        pass


mode = st.radio("输入方式", ["自然语言（AI 解析）", "手动输入"], horizontal=True)

if mode == "自然语言（AI 解析）":
    text = st.text_area(
        "描述你的工程问题", height=90,
        placeholder="例：一根4米长的简支钢梁，距左端1.5米处承受10kN集中力，最大挠度多少？",
    )
    if st.button("解析并计算", type="primary"):
        try:
            parsed = llm.parse_query(text)
            st.success(f"识别场景：{parsed['scenario']}")
            render_result(parsed["scenario"], parsed.get("params", {}))
        except ValueError as e:
            st.warning(f"{e} —— 请改用手动输入。")

else:
    scenario_label = st.selectbox("场景", list(SCENARIOS))
    scenario = SCENARIOS[scenario_label]
    params = {}
    if scenario == "pendulum":
        c1, c2, c3 = st.columns(3)
        params["th0_deg"] = c1.number_input("初始角度 θ₀ (°)", 0.0, 180.0, 120.0)
        params["w0"] = c2.number_input("初始角速度 ω₀ (rad/s)", 0.0, 20.0, 0.0)
        params["t_end"] = c3.number_input("时长 (s)", 1.0, 60.0, 20.0)
    elif scenario == "heat":
        c1, c2, c3 = st.columns(3)
        params["L"] = c1.number_input("钢件半宽 (m)", 0.01, 1.0, 0.1, format="%.3f")
        params["T0"] = c2.number_input("初始温度 (°C)", 100.0, 1500.0, 800.0)
        params["T_wall"] = c3.number_input("介质温度 (°C)", 0.0, 500.0, 20.0)
        params["T_target"] = st.number_input("目标温度 (°C)", 0.0, 1500.0, 100.0)
    elif scenario == "beam":
        c1, c2, c3 = st.columns(3)
        params["L"] = c1.number_input("梁长 (m)", 0.1, 20.0, 4.0)
        params["P"] = c2.number_input("集中荷载 (N)", 100.0, 1e6, 10000.0, format="%.0f")
        params["a"] = c3.number_input("荷载距左端 (m)", 0.1, 19.9, 1.5)
        c4, c5 = st.columns(2)
        params["E"] = c4.number_input("弹性模量 E (Pa)", 1e9, 1e12, 200e9, format="%.3g")
        params["I"] = c5.number_input("惯性矩 I (m4)", 1e-8, 1.0, 5e-4, format="%.3g")
    elif scenario == "vessel":
        c1, c2, c3 = st.columns(3)
        params["P"] = c1.number_input("内压 (Pa)", 1e4, 1e8, 1e6, format="%.3g")
        params["D"] = c2.number_input("内径 (m)", 0.1, 10.0, 1.0)
        params["sigma_allow"] = c3.number_input("许用应力 (Pa)", 1e7, 1e9, 100e6, format="%.3g")
    if st.button("计算", type="primary"):
        render_result(scenario, params)
```

- [ ] **Step 6: 手动验收**

Run: `PYTHONIOENCODING=utf-8 DEEPSEEK_API_KEY=<你的key> streamlit run app.py`
Expected: 自然语言模式输入"一根4米长的简支钢梁，距左端1.5米处承受10kN集中力，最大挠度多少？"→ 识别 beam → 出图+数据+解读。手动模式照常。
（真调 API 只在手动验收时用一次；测试始终 mock。）

- [ ] **Step 7: Commit**

```bash
git add agent/llm.py tests/test_llm.py app.py
git commit -m "feat(agent): DeepSeek 解析层 + app 自然语言模式 + AI 解读"
```

### Task 9 (M3): SerpApi 参数搜索集成

**Files:**
- Create: `agent/serpapi.py`
- Create: `tests/test_serpapi.py`
- Modify: `app.py`（beam 分支加「查参数」按钮）

**Interfaces:**
- Consumes: 无
- Produces: `agent.serpapi.search(query, api_key=None, num=3) -> list[{"title","snippet","link"}]`（缺 key 抛 `ValueError`）

**要点：** M3 深度集成 —— SerpApi 是产品工作流一环（用户说"钢结构横梁"但没给 E/I，产品替用户去查真实参数）。测试 mock `requests.get`，不真调 API。key 从环境变量 `SERPAPI_KEY` 读。

- [ ] **Step 1: 写失败测试** `tests/test_serpapi.py`

```python
import os
from unittest.mock import patch, Mock
from agent import serpapi


def test_search_returns_results():
    fake = Mock()
    fake.raise_for_status = Mock()
    fake.json.return_value = {
        "organic_results": [
            {"title": "Steel elastic modulus", "snippet": "E = 200 GPa", "link": "https://x"},
        ]
    }
    with patch("agent.serpapi.requests.get", return_value=fake) as m:
        out = serpapi.search("steel elastic modulus")
    assert out[0]["title"] == "Steel elastic modulus"
    m.assert_called_once()


def test_search_requires_key():
    with patch.dict(os.environ, {"SERPAPI_KEY": ""}, clear=False):
        try:
            serpapi.search("steel", api_key=None)
            assert False, "should have raised"
        except ValueError as e:
            assert "SERPAPI_KEY" in str(e)
```

- [ ] **Step 2: 跑测试验证失败**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_serpapi.py -v`
Expected: FAIL，报 `ModuleNotFoundError: No module named 'agent.serpapi'`

- [ ] **Step 3: 实现** `agent/serpapi.py`

```python
"""SerpApi 参数搜索: 用真实工程参数辅助计算。

场景: 用户说"钢结构横梁"但没给 E/I —— 用 SerpApi 搜真实材料参数。
M3 深度集成: SerpApi 是产品工作流一环，不是装饰。
"""
from __future__ import annotations

import os
import requests


def search(query: str, api_key: str | None = None, num: int = 3) -> list[dict]:
    """搜索并返回前 num 条结果 [{title, snippet, link}]。缺 key 抛 ValueError。"""
    key = api_key or os.environ.get("SERPAPI_KEY")
    if not key:
        raise ValueError("缺少 SERPAPI_KEY（环境变量或参数）")
    resp = requests.get(
        "https://serpapi.com/search.json",
        params={"engine": "google", "q": query, "api_key": key, "num": num},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": it.get("title", ""), "snippet": it.get("snippet", ""), "link": it.get("link", "")}
        for it in data.get("organic_results", [])[:num]
    ]
```

- [ ] **Step 4: 跑测试验证通过**

Run: `PYTHONIOENCODING=utf-8 python -m pytest tests/test_serpapi.py -v`
Expected: 2 个 PASS（全 mock，不需要真 key）

- [ ] **Step 5: 改 app.py 的 beam 分支加「查参数」按钮**

在 `app.py` 的 `elif scenario == "beam":` 分支内，`params["I"] = c5.number_input("惯性矩 I (m4)", 1e-8, 1.0, 5e-4, format="%.3g")` 这一行之后，插入：

```python
        if st.button("🔍 SerpApi 查钢梁典型参数"):
            try:
                from agent import serpapi
                info = serpapi.search("standard steel I-beam elastic modulus moment of inertia")
                st.write("查到：", info[:2])
                params.setdefault("E", 200e9)
                params.setdefault("I", 5e-4)
            except Exception as e:
                st.error(f"SerpApi 查询失败：{e}")
```

- [ ] **Step 6: 手动验收**

Run: `PYTHONIOENCODING=utf-8 SERPAPI_KEY=<你的key> streamlit run app.py`
Expected: 切到「钢梁挠度」场景点「🔍 SerpApi 查钢梁典型参数」→ 显示查到的参数条目，E/I 自动填入。

- [ ] **Step 7: Commit**

```bash
git add agent/serpapi.py tests/test_serpapi.py app.py
git commit -m "feat(agent): SerpApi 参数搜索 + 梁场景查参数按钮"
```

---

### Task 10 (M4): README + Demo 脚本 + 提交检查

**Files:**
- Create: `README.md`
- Create: `docs/demo_script.md`

**Interfaces:**
- Consumes: 全部已完成模块
- Produces: 可提交的成品（README + 录屏脚本 + 干净 git 状态）

- [ ] **Step 1: 写 README.md**

```markdown
# ⚙️ AI 工程仿真助手

一句话工程问题 → AI 解析 → 数值真算（scipy）→ 图表 + 大白话解读。

**数值永不猜**：LLM 只负责把中文翻译成参数，所有数值由 scipy 求解器计算，并对照验证基准（MATLAB / ASME 标准值）。

## 场景（4 个，工程味）

| 场景 | 验证基准 |
|---|---|
| 单摆（动力学） | MATLAB `simple_pendulum_cn.m` |
| 钢件冷却（热处理） | MATLAB `heat1d_explicit.m`（同差分内核） |
| 钢梁挠度（结构校核） | MATLAB `beam_deflection.m` |
| 压力容器壁厚（设计） | ASME 薄壁公式标准值 |

## 技术栈

Streamlit · numpy/scipy/matplotlib · DeepSeek（OpenAI 兼容）· SerpApi

## 快速开始

```bash
pip install -r requirements.txt
DEEPSEEK_API_KEY=xxx streamlit run app.py
```

## 架构

app.py（编排）→ agent/llm.py（中文→JSON）+ agent/serpapi.py（查参）→ engine/*.py（纯数值）→ 图 + 数据 + 解读

## 测试

```bash
python -m pytest tests/ -v
```

## 参赛

DevNetwork [API + Cloud + AI] Hackathon 2026 · 投 SerpApi Best AI Use Case + Overall Winner
```

- [ ] **Step 2: 写 Demo 录屏脚本** `docs/demo_script.md`

```markdown
# Demo 录屏脚本（≤2 分钟）

[0:00-0:10] 开场：一句"这是 AI 工程仿真助手：说一句工程问题，它真算给你看。"
[0:10-0:40] 单摆：输入"一个初始角度120度的单摆，看看周期和能量" → 识别 → 4 图 + 周期比>1（大角度变慢）
[0:40-1:00] 钢件冷却：输入"800度钢件表面泡冷水，中心到100度要多久" → 冷却曲线 + 约872秒
[1:00-1:25] 钢梁 + SerpApi：输入"钢结构横梁，4米，距左端1.5米10kN" → 点 SerpApi 查参数 → 挠度 + 超限判断
[1:25-1:45] 压力容器快闪：一句"还能算壁厚"，展示场景库可扩展
[1:45-2:00] 收尾：核心卖点三连——"AI 负责听懂、数值负责算对、参数负责溯源"
```

- [ ] **Step 3: 提交前检查清单**

```bash
# 1. 全部测试过
PYTHONIOENCODING=utf-8 python -m pytest tests/ -v
# 预期: pendulum 3 + heat 4 + beam 4 + vessel 3 + llm 3 + serpapi 2 = 19 PASS

# 2. App 能启动
streamlit run app.py

# 3. git 状态干净 + 推远程
git status          # 工作区干净
git push origin main
```

手动核对：
- [ ] 自然语言输入能识别 4 个场景各一次
- [ ] 解析失败时提示改手动输入（不崩溃）
- [ ] demo 视频录好（≤2 分钟，对照 demo_script.md）
- [ ] Devpost 提交页 submit-to/29242 填作品名 + demo 链接 + README
- [ ] 提交流程：GitHub 仓库链接 + demo 视频（可放 YouTube/网盘）

- [ ] **Step 4: Commit**

```bash
git add README.md docs/demo_script.md
git commit -m "docs: README + demo 录屏脚本 + 提交检查清单"
```

---

## 完成标准（对照 spec）

- [ ] 4 个引擎全部对照验证基准通过（单摆/MATLAB、热/MATLAB 内核、梁/MATLAB、容器/ASME）
- [ ] 统一接口 `solve(params) -> {"figures","data"}` 全场景一致
- [ ] 自然语言 → AI 解析 → 数值真算 → 图+数据+解读 全链路可跑
- [ ] SerpApi 深度集成（查真实参数）
- [ ] 测试 19 个 PASS；demo ≤2 分钟；9/4 前提交成功
