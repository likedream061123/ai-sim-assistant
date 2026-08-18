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
