---
title: AI Engineering Simulation Assistant
emoji: ⚙️
sdk: streamlit
app_file: app.py
pinned: false
---

# ⚙️ AI Engineering Simulation Assistant

Describe an engineering problem in plain language → the AI extracts the parameters → scipy solvers compute the real numbers → charts + plain-English interpretation.

**The numbers are never guessed.** The LLM only turns your description into parameters; every value is computed by scipy solvers and cross-checked against verification baselines (MATLAB / ASME standard values).

🌐 **Bilingual UI** — English by default (submission/demo mode), switch to 中文 in the sidebar under "API Settings".

## 🚀 Live Demo

**https://www.modelscope.cn/studios/likedream/ai-sim-assistant**

Keys are pre-configured on the live demo, so AI parsing + SerpApi parameter lookup work out of the box.

## Scenarios (6, across four engineering domains)

| Scenario | Verification baseline |
|---|---|
| Pendulum (Dynamics) | MATLAB `simple_pendulum_cn.m` |
| Steel Quenching (Heat) | MATLAB `heat1d_explicit.m` (same FDM kernel) |
| Beam Deflection (Structural) | MATLAB `beam_deflection.m` |
| Pressure Vessel (Design) | ASME thin-wall standard value |
| RC Circuit (Electrical) | Analytical exact solution |
| Pipe Flow (Fluid) | ASME / engineering handbooks |

## Competition

DevNetwork [API + Cloud + AI] Hackathon 2026
