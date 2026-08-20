% rc_charging.m — First-order RC charging transient (verification baseline, textbook analytic)
% Same as engine/rc_circuit.py:  Vc(t)=Vs·(1-e^(-t/τ)), τ=RC
%   time to reach p%:  t = -τ·ln(1-p/100)
% Defaults: R=1 kΩ, C=100 μF, Vs=12 V, target 90%
% Baseline:  τ=0.1 s, 90% in 0.2303 s, 5τ voltage 11.92 V
% Run:  matlab -batch rc_charging
clear; clc;

R = 1000; C = 100e-6; Vs = 12.0; p = 90.0;
tau = R*C;
t_charge = -tau * log(1 - p/100);
v_target = Vs * p/100;
v_5tau = Vs * (1 - exp(-5));
fprintf('tau      = %.4f s\n', tau);
fprintf('t_charge = %.4f s\n', t_charge);
fprintf('v_target = %.2f V\n', v_target);
fprintf('v_5tau   = %.2f V\n', v_5tau);
