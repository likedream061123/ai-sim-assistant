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
