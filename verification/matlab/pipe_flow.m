% pipe_flow.m — Pipe pressure drop, Darcy-Weisbach + Colebrook friction (verification baseline)
% Same as engine/pipe_flow.py:  ΔP = f·(L/D)·(ρv²/2),  v = Q/A,  A = πD²/4
%   laminar (Re<2300): f = 64/Re   |   turbulent: f solves Colebrook (fixed-point, init 0.02)
% Defaults: water, D=50 mm, Q=20 m³/h, L=100 m, ε=45 μm
% Baseline:  v ≈ 2.83 m/s, Re ≈ 1.41e5, f ≈ 0.0212, ΔP ≈ 169 kPa
% Run:  matlab -batch pipe_flow
clear; clc;

Q = 20.0/3600.0; D = 0.05; L = 100.0; eps = 45e-6;
rho = 1000.0; mu = 1e-3;

A = pi*D^2/4; v = Q/A;
Re = rho*v*D/mu;
eps_D = eps/D;

if Re < 2300
    f = 64/Re;
else
    f = 0.02;
    for k = 1:80
        fnew = 1 / (-2*log10(eps_D/3.7 + 2.51/(Re*sqrt(f))))^2;
        if abs(fnew - f) < 1e-10, f = fnew; break; end
        f = fnew;
    end
end
dp = f * (L/D) * (rho*v^2/2);
fprintf('v    = %.3f m/s\n', v);
fprintf('Re   = %.1f\n', Re);
fprintf('f    = %.4f\n', f);
fprintf('dP   = %.2f kPa\n', dp/1000);
