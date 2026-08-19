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


def test_small_L_early_exit_same_result():
    """L 小 + tmax 大时提前终止：目标时间与全跑一致（L=0.02 实测 34.90s），且不拖慢。"""
    import time
    t0 = time.perf_counter()
    res = solve_heat({"L": 0.02, "tmax": 3600.0}, plot=False)
    wall = time.perf_counter() - t0
    t = res["data"]["t_center_target"]
    assert t is not None
    assert abs(t - 34.9) < 0.5             # 与全跑基准一致（原值 34.9017）
    assert wall < 2.0                      # 原实现 L=0.02 要 ~10s，提前终止后应 <2s
    assert res["data"]["steady_reached"]   # 充分冷却后应判稳态


def test_large_L_not_reached_runs_full():
    """L 大、中心到不了目标时照常跑满，不提前 break（L=0.5 → t_center_target=None）。"""
    res = solve_heat({"L": 0.5, "tmax": 3600.0}, plot=False)
    d = res["data"]
    assert d["t_center_target"] is None
    assert not d["steady_reached"]
