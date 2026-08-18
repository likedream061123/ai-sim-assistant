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
