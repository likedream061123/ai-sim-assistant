import numpy as np
from engine.pipe_flow import solve_pipe, colebrook_friction


def test_laminar_matches_poiseuille():
    """层流段 f=64/Re，压降应精确等于 Hagen-Poiseuille 解析解 ΔP=128μLQ/(πD⁴)。"""
    d = solve_pipe({"Q": 1e-5, "D": 0.01, "L": 10.0})["data"]
    assert d["Re"] < 2300
    assert d["flow_type"] == "层流"
    dp_ana = 128 * 1e-3 * 10.0 * 1e-5 / (np.pi * 0.01 ** 4)
    assert abs(d["dp"] - dp_ana) / dp_ana < 1e-6
    assert abs(d["f"] - 64.0 / d["Re"]) < 1e-9


def test_default_turbulent():
    d = solve_pipe()["data"]
    assert d["Re"] > 4000
    assert d["flow_type"] == "湍流"
    assert 0.01 < d["f"] < 0.05


def test_colebrook_moody_reference():
    """Moody 图参考点：Re=1e5, ε/D=0.0009 → f≈0.022。"""
    assert abs(colebrook_friction(1e5, 0.0009) - 0.022) < 0.003


def test_dp_quadratic_like_with_Q():
    """湍流段流量翻倍，压降约翻 4 倍（∝v²，f 略随 Re 降 → 3~4.5 区间）。"""
    base = solve_pipe({"Q": 20.0 / 3600.0, "D": 0.05, "L": 10.0})["data"]
    dbl = solve_pipe({"Q": 40.0 / 3600.0, "D": 0.05, "L": 10.0})["data"]
    ratio = dbl["dp"] / base["dp"]
    assert 3.0 < ratio < 4.5


def test_dp_linear_in_L():
    d1 = solve_pipe({"L": 10.0})["data"]
    d2 = solve_pipe({"L": 20.0})["data"]
    assert abs(d2["dp"] / d1["dp"] - 2.0) < 1e-6


def test_returns_two_figures():
    assert len(solve_pipe()["figures"]) == 2
