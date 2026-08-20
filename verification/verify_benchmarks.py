"""验证基准对照表 —— 「数值永不猜」的可复现证明。

跑:  python verification/verify_benchmarks.py

每个场景用引擎默认参数求解，对照 MATLAB / ASME / 教科书基准，断言误差在容差内。
MATLAB 基准来源: verification/matlab/*.m（可独立复跑，基准值由此生成）。
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine import beam, heat, vessel, pendulum, pipe_flow, rc_circuit

# (场景名, 引擎模块, 输出键, 基准值, 容差, 基准来源)
BENCHMARKS = [
    ("单摆（动力学）", pendulum, "T_num", 2.252, 0.01, "MATLAB simple_pendulum_cn.m"),
    ("钢件冷却（热处理）", heat, "t_center_target", 872.5, 10.0, "MATLAB heat1d_explicit.m"),
    ("钢梁挠度（结构）", beam, "v_max_mm", 0.1227, 0.005, "MATLAB beam_deflection.m (0.1226, <0.1%)"),
    ("压力容器壁厚（设计）", vessel, "t_req_mm", 5.00, 0.01, "ASME 薄壁 t=PD/(2σ)"),
    ("RC 充电（电学）", rc_circuit, "t_charge", 0.2303, 0.001, "教科书解析解 V=Vs(1-e^(-t/τ))"),
    ("管道压降（流体）", pipe_flow, "dp_kPa", 169.4, 2.0, "Darcy-Weisbach + Colebrook"),
]


def main() -> int:
    import matplotlib
    matplotlib.use("Agg")

    ok = True
    rows = []
    for name, mod, key, ref, tol, src in BENCHMARKS:
        data = mod.solve(plot=False)["data"]
        val = float(data[key])
        err = abs(val - ref)
        rows.append((name, val, ref, err, err <= tol, src))
        ok = ok and err <= tol

    w = max(len(r[0]) for r in rows)
    print(f"{'场景':<{w}} {'引擎输出':>14} {'基准':>12} {'误差':>10}  结论")
    print("-" * 78)
    for name, val, ref, err, passed, src in rows:
        print(f"{name:<{w}} {val:>14.4g} {ref:>12.4g} {err:>9.2e}  "
              f"{'PASS' if passed else 'FAIL'}   ({src})")
    print("-" * 78)
    if ok:
        print("全部通过 ✓  引擎输出与验证基准一致 —— 数值永不猜。")
    else:
        print("存在未通过项 ✗  请检查对应引擎或基准。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
