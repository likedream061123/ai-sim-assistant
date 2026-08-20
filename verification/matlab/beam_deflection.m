% beam_deflection.m — Simply-supported beam with point load (verification baseline)
% Same physics as engine/beam.py: simply-supported span L, point load P at distance a from left support
%   v1(x) = P·b·x/(6EI·L)·(L²-b²-x²)                       0≤x≤a
%   v2(x) = P·b/(6EI·L)·((L/b)(x-a)³ + (L²-b²)x - x³)       a≤x≤L
% Defaults: L=4 m, P=10 kN, a=1.5 m, E=200 GPa, I=5e-4 m⁴
% Baseline:  v_max ≈ 0.1226 mm @ x ≈ 1.86 m
% Run:  matlab -batch beam_deflection
clear; clc;

L = 4.0; P = 10000.0; a = 1.5; E = 200e9; I = 5e-4;
b = L - a;

xx = linspace(0, L, 4001);
v = zeros(size(xx));
for i = 1:numel(xx)
    x = xx(i);
    if x <= a
        v(i) = P*b*x/(6*E*I*L) * (L^2 - b^2 - x^2);
    else
        v(i) = P*b/(6*E*I*L) * ((L/b)*(x-a)^3 + (L^2 - b^2)*x - x^3);
    end
end
[vmax, imax] = max(v);
fprintf('v_max = %.4f mm @ x = %.3f m\n', vmax*1000, xx(imax));
