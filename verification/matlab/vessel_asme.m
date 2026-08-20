% vessel_asme.m — ASME thin-wall pressure vessel wall thickness (verification baseline)
% Same formula as engine/vessel.py:  t = P·D/(2·σ)  (hoop-stress dominant)
% Defaults: P=1 MPa, D=1 m, σ=100 MPa
% Baseline:  t = 5.00 mm (analytic, zero error)
% Run:  matlab -batch vessel_asme
clear; clc;

P = 1e6; D = 1.0; sigma = 100e6;
t = P * D / (2 * sigma);
fprintf('t_req = %.4f mm\n', t*1000);
