import numpy as np
from engine.rc_circuit import solve_rc


def test_tau_equals_rc():
    d = solve_rc({"R": 2000.0, "C": 50e-6})["data"]
    assert abs(d["tau"] - 0.1) < 1e-9


def test_charge_90_time_is_analytic():
    """充到 90% 时间 = -τ·ln(0.1)；默认 R=1kΩ C=100μF → τ=0.1s。"""
    d = solve_rc()["data"]
    assert abs(d["t_charge"] - 0.1 * np.log(10)) < 1e-6


def test_charge_63pct_about_one_tau():
    d = solve_rc({"charge_percent": 63.2})["data"]
    assert abs(d["t_charge"] - 0.1) < 1e-3


def test_5tau_voltage_nearly_full():
    d = solve_rc()["data"]
    assert abs(d["v_5tau"] - 12.0 * (1 - np.exp(-5))) < 1e-9
    assert d["v_5tau"] > d["v_target"]   # 5τ 电压必高于 90% 目标


def test_peak_current_v_over_r():
    d = solve_rc()["data"]
    assert abs(d["i_peak"] - 12.0 / 1000.0) < 1e-12


def test_returns_two_figures():
    assert len(solve_rc()["figures"]) == 2
