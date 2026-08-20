# Devpost Submission Copy (English)

Copy these sections into your Devpost submission. The app UI, README, and demo script are all English-by-default for the judging panel.

---

## Project name

AI Engineering Simulation Assistant

## Tagline

Describe an engineering problem in plain language — the AI extracts the parameters, scipy solvers compute the real numbers, charts + plain-English interpretation follow.

## Elevator pitch (short description)

An engineer-facing tool where **the numbers are never guessed**. You type "a 4 m steel beam, 10 kN at 1.5 m — what's the max deflection?" The LLM only *understands* the question and extracts parameters; scipy solvers do the actual math, cross-checked against MATLAB / ASME baselines. Missing a parameter? The AI proposes an engineering default and you accept it in one click. Over the limit? It tells you which parameter to change and applies the fix for you. Every number is traceable to its source.

## Inspiration

Every engineering student knows the struggle: you type a textbook problem into ChatGPT and it confidently returns a plausible-looking answer that's subtly wrong — because the LLM "reasons" about numbers instead of computing them. The core insight: **separate language from math.** Let an LLM do what it's great at (understanding intent, extracting parameters, explaining results) and let scipy do what it's great at (actual numerical simulation). The result is a tool that talks like a TA and computes like a solver.

## What it does

- **Natural-language engineering questions** → scenario + parameter extraction (6 scenarios across dynamics, heat transfer, structures, fluids, electronics).
- **Real computation, zero guessing**: steel beam deflection, steel quenching heat transfer, pressure-vessel wall thickness, RC charging, pipe pressure drop — all solved by numpy/scipy with analytic or standard baselines (MATLAB kernels, ASME thin-wall formula, Darcy-Weisbach).
- **Engineering judgement built in**: sensitivity analysis shows which parameter moves your result most; over-limit checks propose a concrete fix (thicker wall, bigger inertia, larger pipe) and apply it with one click.
- **Traceability**: every parameter is labelled "you provided" vs "engineering default" in the results panel; full JSON/CSV export; a verification section states the MATLAB/ASME baseline for each scenario.
- **Live parameter lookup via SerpApi**: for the steel-beam scenario it searches the web, cross-checks multiple sources into a consensus value, prefills the inputs and marks the sources in a results panel; if the key or network is missing it falls back to built-in typical values, so the demo never breaks.
- **Works without an API key**: no network, no key — the natural-language pipeline still runs on a built-in offline matcher, so judges can try it live even with no connectivity.
- **Bilingual UI**: English by default for the judging panel, Chinese available in the sidebar.

## How we built it

Streamlit frontend orchestrating a pipeline: an OpenAI-compatible LLM layer (DeepSeek / OpenAI / Zhipu / Qwen / Kimi / SiliconFlow — all interchangeable) with a Chinese few-shot prompt that outputs strict JSON; a SerpApi agent for real-world parameter lookup; six pure-numerical engines (numpy/scipy/matplotlib); a design-helper layer that runs ±10% sensitivity sweeps and generates fix suggestions. Every engine ships with a verification baseline traced to MATLAB scripts or standard analytic solutions, surfaced in the UI.

## Challenges we ran into

- **Fast heat-transfer solves**: the explicit finite-difference quench solver could take ~40 s on thin parts; added an early-termination criterion once the center cools below target (216× speedup) so the UI stays snappy.
- **f-string i18n**: translation of string templates with embedded numbers forced a move from f-strings to a template-translate-and-format layer, keeping every chart label and advice message bilingual without touching the numerics.

## Accomplishments that we're proud of

- The "sensitivity tornado" — a real designer's view: change inertia I ±10% and see the deflection swing, so users learn *which* parameter matters instead of blind trial-and-error.
- The whole product is testable headlessly: 154 unit tests + an AppTest smoke suite that drives the actual Streamlit UI (manual mode, natural-language mode with mocked LLM, history, export, SerpApi lookup, extreme-input guard) in both languages.

## What we learned

Putting a narrow, well-scoped LLM between a human and a solver is a sweet spot: the model's hallucination risk is bounded to *parameter extraction* (where it's excellent), while the math — the part that must be right — stays fully deterministic and verifiable.

## What's next

More scenarios (trusses, transient circuits, fluid networks), pluggable verification notebooks per engine, and multi-turn conversation where the assistant iterates on parameters with the user.

## Built with

Streamlit · Python · scipy · numpy · matplotlib · SerpApi · DeepSeek · OpenAI · Anthropic-compatible LLM APIs · GitHub Actions (CI)
