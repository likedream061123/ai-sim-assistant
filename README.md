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

## What the AI does (judges' focus)

1. **Understands**: one sentence (Chinese or English) → detects the scenario + extracts parameters (few-shot)
2. **Recommends**: fills in the key parameters you didn't mention with engineering defaults, one click to accept
3. **Never computes**: every number comes from scipy solvers, cross-checked against MATLAB / ASME baselines
4. **Traceable**: the result panel marks every parameter as "you provided" vs "default used"; AI interpretation wraps up in plain language

## Live parameter lookup (SerpApi)

Five of the six scenarios search the web for real engineering values (steel-beam E/I, thermal diffusivity, pipe wall roughness, RC component values, pressure-vessel allowable stress), cross-checked across multiple sources into a consensus value. Missing key or network? It gracefully falls back to built-in typical values.

## Architecture

app.py (orchestration) → agent/llm.py (language → JSON) + agent/serpapi.py (parameter lookup) → engine/*.py (pure numerics) → charts + data + interpretation

## Tests

```bash
python -m pytest tests/ -v
```

190 unit tests + an AppTest smoke suite that drives the actual Streamlit UI in both languages.

## Competition

DevNetwork [API + Cloud + AI] Hackathon 2026 · submitted for SerpApi Best AI Use Case + Overall Winner
