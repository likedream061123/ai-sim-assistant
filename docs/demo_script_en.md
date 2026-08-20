# Demo Script (screen recording, ≤2 min)

Main thread: **the AI not only understands — it gives you a plan.** Three acts: "parse + recommend", "live parameter lookup + over-limit check", "one-click apply the suggestion".

[0:00-0:10] **Opening**: "This is the AI Engineering Simulation Assistant: describe an engineering problem in one sentence, it computes the real numbers and even proposes a solution."

[0:10-0:35] **Pendulum · AI parsing**
Tap the sample card "A 1 m pendulum released from 120°, show its period and energy" → detected → 4 charts + period ratio >1 (large-angle slowdown).

[0:35-0:55] **Steel quenching · suggestion**
Type "800 °C steel dropped into cold water, how long until the center cools to 100 °C?" (half-width deliberately omitted) → the AI asks for the missing parameter + prefills a recommended value → click "Compute with these parameters" → cooling curve + ~872 s.

[0:55-1:20] **Beam · SerpApi lookup + over-limit check**
Type "a 4 m steel beam, 10 kN at 1.5 m from the left end" → click "Look up typical steel-beam values (SerpApi)" → deflection + L/360 over-limit verdict.

[1:20-1:45] **Pressure vessel · one-click apply**
Type "1 MPa internal pressure, 1 m inner diameter, 100 MPa allowable stress — is a 2 mm wall thick enough?" → verdict: no (needs ~5 mm) → switch to Manual mode → click "⚡ Apply" to thicken → auto-recompute passes (the AI doesn't just compute, it proposes the fix).

[1:45-2:05] **Closing**: three selling points — "the AI understands (parameters), the math is right (scipy + MATLAB baselines), the parameters are traceable (sources marked in the result panel)". Open "📦 Export": JSON/CSV take all the data away. Final coverage line — "from a pendulum to a water pipe: 6 scenarios across four engineering domains". Mention the sidebar lets you switch DeepSeek / OpenAI / Zhipu / Qwen / Kimi / SiliconFlow.
