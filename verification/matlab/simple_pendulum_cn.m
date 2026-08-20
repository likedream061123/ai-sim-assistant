% simple_pendulum_cn.m — Large-angle pendulum period (verification baseline)
% Same physics as engine/pendulum.py:  thdd = -(g/l)sin(th) - (c/m·l²)·thd
% Defaults: l=1 m, m=1 kg, g=9.81 m/s², c=0, released from θ₀=120°
% Baseline:  T ≈ 2.252 s  (large angle; period ratio ~1.12 → slower than small-angle 2.006 s)
% Run:  matlab -batch simple_pendulum_cn
clear; clc;

l = 1.0; m = 1.0; g = 9.81; c = 0.0;
th0 = deg2rad(120.0); w0 = 0.0;

f = @(t, y) [y(2); -(g/l)*sin(y(1)) - (c/(m*l^2))*y(2)];
[t, y] = ode45(f, [0 20.0], [th0; w0]);
th = y(:,1);

% Period = twice the mean interval between successive zero crossings (half-period each)
signs = th(1:end-1) .* th(2:end);
t_cross = t(find(signs < 0));
T0 = 2*pi*sqrt(l/g);
if numel(t_cross) >= 2
    T = 2 * mean(diff(t_cross));
else
    T = NaN;
end
fprintf('T_num     = %.4f s\n', T);
fprintf('T0_small  = %.4f s\n', T0);
fprintf('T_ratio   = %.4f\n', T / T0);
