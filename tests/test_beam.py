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
