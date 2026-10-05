# Simulator results (SPEC v0.2): assumption-driven projections

**These are not measurements.** They come from `engine/pehchaan/sim.py`, a generative model of *triggered* payment sessions: a payment during, or up to 10 min after, a call, to a new payee, above p95, or ≥ ₹10,000.

- The sessions run through the real Pehchaan fusion config (`engine/pehchaan/config.yaml`, v0.2.0).
- Every distribution is listed in `engine/sim_assumptions.yaml`, either cited to `research/` or labelled "team assumption".
- The vectorised engine in `sim.py` is tested against `pehchaan.fusion.assess`: identical tiers and p on 10,000 random plus 6,000 scenario-like signal sets.

```bash
cd engine && python -m pehchaan.sim                          # one command refreshes every file below (about 20 s)
cd engine && python -m pehchaan.sim --rebuild-v01-baseline   # also re-run the v0.1 engine from git (ac7620f)
cd engine && python -m pehchaan.sim --quick                  # smoke run
```

When `ml/results/metrics.json` appears, the next run uses its `band_rates` (spoof vs bona fide; held-out rows preferred) instead of the placeholders. The source used is recorded in `sim_summary.json` → `voice.band_rates_source` and in `deck_numbers.json`.

| File | What it is |
|---|---|
| `deck_numbers.json` | **Flat dict of the headline numbers for the deck.** v0.2 values plus `v01_*` comparisons. Risk-assess p50/p95 are read from `app/server/latency.json`. |
| `sim_summary.json` | Headline run at π0 = 1/400, θ_red 0.75, 30% voice uptake. Includes the friction budget (overall and per scenario), catch rates per pattern, ₹ per 100k sessions, the alert-budget check, and Red precision against the prior. |
| `sim_threshold_sweep.json` | θ_red sweep (0.50–0.95) and green_below sweep (0.05–0.25), plus an auto-registry what-if. |
| `sim_sensitivity.json` | Prior (1/2000 … 1/100) × voice-check uptake (0 / 30 / 70%). |
| `sim_ablation.json` | Layers added cumulatively: context only → + claim (incl. the 3-tap checklist) → + out-of-band checks → + voice and ASR cues. |
| `sim_v01_baseline.json` | The v0.1 engine and simulator re-run unchanged from git, for the before/after comparison. |
| `chart_friction_funnel.svg`, `chart_catch_by_pattern.svg`, `chart_ablation.svg`, `chart_sensitivity.svg` | Deck charts (v0.2). |
| `chart_red_precision.svg` | Genuine holds per scam held against the prior, v0.1 vs v0.2. |
| `chart_threshold_tradeoff.svg` | Genuine and scam Red rates against θ_red, with the 0.25% budget line. |
| `preview/*.png` | 1200 px layout previews (not for the deck). |

The SVGs are 600 units wide. Placed at about 600 px on a 1280×720 slide, every label is ≥ 12 px. Text stays as text (Space Grotesk / Inter / JetBrains Mono); inline the SVGs so they pick up the deck's `@font-face`.

## What changed in v0.2

The engine changes, all modelled in the simulator:
- **G7:** `fv_denied` and `bank_no_active_call` are a decisive floor.
- **User-reported checks:** `callback_denied` and `safeword_failed` are LR 30 and not decisive.
- **G1:** ignores trigger-implied evidence (`payee_new`, `amount_gt_*`).
- **G2 is strict.**
- **Registry:** `bank_active_call_1600` is a decisive positive. A bank that isn't integrated gives `bank_registry_unknown`.

Changes to the simulator itself:
- **Claim split:** "My bank" vs "UPI app, shop or delivery".
- **Named bank:** the user names a bank, and integration depends on whether it is their own bank.
- **3-tap checklist** for coached "no one" / "someone else" at Amber.
- **θ_red tuned to 0.75:** it meets the Red budget, stays within 1 pp of the best catch, and keeps the most headroom.

## Headline v0.1 → v0.2 (π0 1/400, 30% voice uptake, placeholder detector rates)

- **Genuine:** silent 42.0 → 41.8%. One-tap then pay 47.8 → 49.0%. Pause & Verify 10.1 → 9.2%. Final Amber 5.7 → 4.9%. **Held 0.92 → 0.24%** (budget ≤ 0.25%: met).
  - The Pause & Verify budget (≤ 6%) is **not met**. It is set by green_below, not θ_red; see `sim_threshold_sweep.json` → `green_rows`.
- **Scams held (Red):** T1 65 → 53%, T2 77 → 70%, T3 85 → 74%, weighted 77 → 68%. Amber+ stays about 96%.
- **Genuine holds per scam held:** 4.8 → 1.4 at 1/400, and 3.7 → 1.0 at the 1/1304 base-rate anchor. ₹ protected per ₹ delayed rises from 1.19 to 2.46.
- **Zero voice checks:** scams held 74 → 68%.
