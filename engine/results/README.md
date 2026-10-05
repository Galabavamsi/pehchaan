# Simulator results: assumption-driven projections

**These are not measurements.** They come from `engine/pehchaan/sim.py`, a generative model of *triggered* payment sessions (a payment during, or up to 10 min after, a call, to a new payee / above p95 / ≥ ₹10,000). The sessions run through the real Pehchaan fusion config (`engine/pehchaan/config.yaml`). Every distribution is listed in `engine/sim_assumptions.yaml`, either cited to `research/` or labelled "team assumption". Change an assumption and rerun to update everything.

```bash
cd engine && python -m pehchaan.sim            # full run, ~3 s: 100k genuine + 30k per scam pattern, seed 20261006
cd engine && python -m pehchaan.sim --quick    # smoke run
python -m pehchaan.sim --prior 0.00077 --voice-uptake 0   # any single scenario
```

| File | What it is |
|---|---|
| `sim_summary.json` | Headline run at the SPEC default prior 1/400 with 30% voice-check uptake. Contains the friction budget for genuine sessions (overall and per scenario), catch rates per scam pattern, ₹ protected vs ₹ delayed per 100k triggered sessions, the base-rate prior anchor, and a clearly labelled national-scale illustration. |
| `sim_sensitivity.json` | Prior sweep (1/2000 … 1/100) × voice-check uptake (0 / 30 / 70%). The same sessions are re-scored each time (common random numbers). |
| `sim_ablation.json` | Layers added cumulatively: context only → + one-tap claim → + out-of-band checks → + voice check. |
| `chart_friction_funnel.svg` | Funnel of genuine payments: silent → one-tap question → Pause & Verify → held. |
| `chart_catch_by_pattern.svg` | Paused and held rates for T1/T2/T3, compared with genuine payments. |
| `chart_ablation.svg` | What each layer adds. |
| `chart_sensitivity.svg` | Scam holds against the prior for each voice-check uptake, plus genuine friction against the prior. |
| `preview/*.png` | 1200 px previews used for the layout check (not for the deck). |

The SVGs are 600 units wide. Place them at about 600 px on a 1280×720 slide and every label is ≥ 12 px. Text stays as text, in Space Grotesk, Inter or JetBrains Mono. Inline the SVGs so they pick up the deck's `@font-face`.

## Headline (prior 1/400, 30% voice uptake, placeholder detector rates)

- **Genuine sessions:** 42% pass with no screen at all and 48% answer one tap then pay. 10.1% see Pause & Verify; 3.6% of sessions are then cleared by a check. 5.7% end at Amber and **0.92% are held**.
- **Scams reaching Pause & Verify / held:**
  - T1 cloned relative: 96% / 65%.
  - T2 fake bank official: 94% / 77%.
  - T3 digital-arrest hybrid: 99% / 85%.
  - Weighted across patterns: 96% / 77%; 74% are expected to be stopped once user behaviour is applied.
- **Ablation (scam held / genuine paused):**
  - Context only: 27% / 3.8%.
  - + claim: 68% / 10%.
  - + out-of-band checks: 74% / 10%.
  - + voice check: 77% / 10%.
- **With zero voice checks**, 74% of scams are still held at 1/400. At 1/2000 the figure is 48%.
- **Prior anchor:** public base rates give about **1/1300** (see `base_rate_anchor`). The SPEC default 1/400 therefore overstates genuine friction.

## Assumptions that matter most

1. Prior and mix: 1/400 by default. Scam mix is T1 20% / T2 45% / T3 35%, informed by Chakshu 2025 category counts.
2. Family Verify: half of families are in the Pehchaan circle. 50–70% of users tap the check. A real relative denies 70% of the time when impersonated.
3. Bank outbound-call registry covers 70% of claimed banks. 15% of genuine bank calls do not yet come from 1600 numbers.
4. Coached victims answer "no one" or "someone else" 15–25% of the time.
5. Voice-check uptake is 30%. Detector band rates are **placeholders**; half the scam audio comes from generators the detector has never seen.
6. After a Red hold, 20% of coerced victims pay anyway (5% when the amount is ≥ ₹50k and needs analyst review). After an Amber, 40% of scam victims cancel.
