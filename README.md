# ⚙️ AI Engineering Simulation Assistant

Describe an engineering problem in plain language → the AI extracts the parameters → scipy solvers compute the real numbers → charts + plain-English interpretation.

**The numbers are never guessed.** The LLM only turns your description into parameters; every value is computed by scipy solvers and cross-checked against verification baselines (MATLAB / ASME standard values).

🌐 **Bilingual UI** — English by default (submission/demo mode), switch to 中文 in the sidebar under "API Settings".

## 🚀 Live Demo

**[https://ai-sim-assistant-9bbndox8o9sxkm4avdxhpk.streamlit.app/](https://ai-sim-assistant-9bbndox8o9sxkm4avdxhpk.streamlit.app/)** — deployed on Streamlit Community Cloud. Works fully without any API key (manual mode + built-in offline NL matcher); with keys in the app's "API Settings" you get AI parsing + live SerpApi parameter lookup.

## Scenarios (6, across four engineering domains)

| Scenario | Verification baseline |
|---|---|
| Pendulum (Dynamics) | MATLAB `simple_pendulum_cn.m` |
| Steel Quenching (Heat) | MATLAB `heat1d_explicit.m` (same FDM kernel) |
| Beam Deflection (Structural) | MATLAB `beam_deflection.m` |
| Pressure Vessel (Design) | ASME thin-wall standard value |
| RC Charging (Electronics) | Textbook analytic V=Vs(1-e^(-t/τ)); 90% in 0.230 s |
| Pipe Pressure Drop (Fluids) | Darcy-Weisbach + Colebrook; laminar branch 0% error vs Poiseuille |

## Tech Stack

Streamlit · numpy/scipy/matplotlib · LLM (OpenAI-compatible, multiple providers) · SerpApi

## Quick Start

```bash
pip install -r requirements.txt
DEEPSEEK_API_KEY=xxx streamlit run app.py
```

**Runs without any API key**: Manual input mode is fully functional (no AI calls). With a key, AI parsing + plain-language interpretation turn on. Keys can be typed in the sidebar "API Settings" (remembered locally on your machine), or injected via environment variables:

| Provider | Env var | Default model |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | deepseek-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini |
| Zhipu GLM | `ZHIPU_API_KEY` | glm-4-flash |
| Qwen | `DASHSCOPE_API_KEY` | qwen-plus |
| Kimi | `MOONSHOT_API_KEY` | moonshot-v1-8k |
| SiliconFlow | `SILICONFLOW_API_KEY` | deepseek-ai/DeepSeek-V3 |

## What the AI does (judges' focus)

1. **Understands**: one sentence (Chinese or English) → detects the scenario + extracts parameters (few-shot)
2. **Recommends**: fills in the key parameters you didn't mention with engineering defaults, one click to accept
3. **Never computes**: every number comes from scipy solvers, cross-checked against MATLAB / ASME baselines
4. **Traceable**: the result panel marks every parameter as "you provided" vs "default used"; AI interpretation wraps up in plain language

## Live parameter lookup (SerpApi) — the AI doesn't guess materials either

For five of the six scenarios, one click searches the web for **real engineering values** instead of relying on built-in defaults: steel-beam E/I, steel/aluminum/copper thermal diffusivity, pipe wall roughness, RC component values, and pressure-vessel allowable stress. SerpApi results are **cross-checked across multiple sources into a consensus value** (outliers filtered by each material's physical range), then prefilled with the source links shown. Missing key or network? It gracefully falls back to built-in typical values — the demo never breaks.

## Architecture

app.py (orchestration) → agent/llm.py (language → JSON) + agent/serpapi.py (parameter lookup) → engine/*.py (pure numerics) → charts + data + interpretation

## Tests

```bash
python -m pytest tests/ -v
```

184 unit tests (parameter extractors, six engine kernels, E2E, offline fallback) + an AppTest smoke suite that drives the actual Streamlit UI in both languages — CI runs them on every push.

## Competition

DevNetwork [API + Cloud + AI] Hackathon 2026 · submitted for SerpApi Best AI Use Case + Overall Winner
