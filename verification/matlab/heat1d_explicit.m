% heat1d_explicit.m — 1-D transient heat conduction, explicit finite difference (verification baseline)
% Same FDM kernel as engine/heat.py: left Neumann reflection (center symmetry) + right Dirichlet (wall at fixed temp)
% Defaults: half-width 0.1 m, initial 800 °C, wall 20 °C, α=1.17e-5 m²/s, target center 100 °C
% Baseline:  center reaches 100 °C at ~873 s
% Run:  matlab -batch heat1d_explicit
clear; clc;

L = 0.1; T0 = 800.0; Tw = 20.0; alpha = 1.17e-5; Tt = 100.0;
N = 100; r = 0.4; tmax = 3600.0;

dx = L / (N - 1);
dt = r * dx^2 / alpha;
nstep = floor(tmax / dt);
u = ones(1, N) * T0;

t_center_target = NaN;
for n = 1:nstep
    uext = [u(2), u, Tw];                       % left reflection + right fixed wall
    lap = uext(3:end) - 2*uext(2:end-1) + uext(1:end-2);
    u = u + r * lap;
    u(end) = Tw;
    if isnan(t_center_target) && u(1) <= Tt
        t_center_target = n * dt;
    end
    if ~isnan(t_center_target) && (u(1) - Tw) <= 0.01*(T0 - Tw)
        break;                                  % early termination (matches Python)
    end
end
fprintf('t_center_target = %.1f s\n', t_center_target);
