# Demo Script (screen recording, ≤2 min)

Main thread: **the AI not only understands — the numbers are never guessed.** Four acts: "parse + recommend", "live parameter lookup + over-limit check", "one-click apply the suggestion", and the verification card proving every result was computed, not guessed.

[0:00-0:10] **Opening**: "This is the AI Engineering Simulation Assistant: describe an engineering problem in one sentence, it extracts the parameters, scipy computes the real numbers — and a verification card shows each result against a MATLAB or ASME baseline."

[0:10-0:35] **Pendulum · AI parsing + verification card**
Tap the sample card "A 1 m pendulum released from 120°, show its period and energy" → detected → 4 charts + period ratio 1.123. Point to the verification card: **Physics check — 1.123 > 1 ✓ Physically consistent** (large-angle period lengthens, exactly as physics predicts).

[0:35-0:55] **Steel quenching · suggestion**
Type "800 °C steel dropped into cold water, how long until the center cools to 100 °C?" (half-width deliberately omitted) → the AI asks for the missing parameter + prefills a recommended value → click "Compute with these parameters" → cooling curve + ~872 s, same explicit FDM core as MATLAB.

[0:55-1:20] **Beam · SerpApi lookup + over-limit check + verification card**
Type "a 4 m steel beam, 10 kN at 1.5 m from the left end" → click "Look up typical steel-beam values (SerpApi)" → deflection 0.1226 mm. Point to the verification card: **deviation ≈ 0.0% ✓ vs the MATLAB analytic baseline** — the solver landed on the published answer. Then the L/360 over-limit verdict.

[1:20-1:45] **Pressure vessel · one-click apply**
Type "1 MPa internal pressure, 1 m inner diameter, 100 MPa allowable stress — is a 2 mm wall thick enough?" → verdict: no (needs ~5 mm) → switch to Manual mode → click "⚡ Apply" to thicken → auto-recompute passes (the AI doesn't just compute, it proposes the fix).

[1:45-2:05] **Closing** — three selling points: "the AI understands (parameters), the math is right (scipy + MATLAB/ASME baselines), the parameters are traceable (every one marked 'you provided' vs 'default', sources shown)". Open "🔗 Reproduce this result": one copy-paste link carries the exact scenario + parameters, so a judge can recompute the same numbers on any device. Open "📦 Export": JSON/CSV take all data away. Final coverage line — "from a pendulum to a water pipe: 6 scenarios across four engineering domains", and the sidebar swaps DeepSeek / OpenAI / Zhipu / Qwen / Kimi / SiliconFlow.
