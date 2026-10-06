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
| `deck_numbers.json` | **Flat dict of the headline numbers for the deck.** v0.2 values plus `v01_*` comparisons. The only nested values are the `*_by_fv_enrolment` maps (keys `"0.2"` … `"0.9"`) and `fv_enrolment_grid`. Risk-assess p50/p95 are read from `app/server/latency.json`. |
| `sim_summary.json` | Headline run at π0 = 1/400, θ_red 0.75, green_below 0.15, 30% voice uptake. Includes the friction budget (overall and per scenario), catch rates per pattern, ₹ per 100k sessions, the alert-budget check, and Red precision against the prior. |
| `sim_threshold_sweep.json` | θ_red sweep (0.50–0.95) and green_below sweep (0.05–0.25), plus an auto-registry what-if. |
| `sim_sensitivity.json` | Prior (1/2000 … 1/100) × voice-check uptake (0 / 30 / 70%), plus `fv_enrolment`: Family Verify enrolment 0.2 / 0.35 / 0.5 / 0.7 / 0.9 with everything else fixed (same sessions; the 0.5 row is the headline run). |
| `sim_ablation.json` | Layers added cumulatively: context only → + claim (incl. the 3-tap checklist) → + out-of-band checks → + voice and ASR cues. |
| `sim_v01_baseline.json` | The v0.1 engine and simulator re-run unchanged from git, for the before/after comparison. |
| `chart_friction_funnel.svg`, `chart_catch_by_pattern.svg`, `chart_ablation.svg`, `chart_sensitivity.svg` | Deck charts (v0.2). |
| `chart_red_precision.svg` | Genuine holds per scam held against the prior, v0.1 vs v0.2. |
| `chart_threshold_tradeoff.svg` | Genuine and scam Red rates against θ_red, with the 0.25% budget line. |
| `chart_fv_enrolment.svg` | T1 Amber+ / T1 Red / weighted scam Red against Family Verify enrolment. |
| `chart_*_deck.svg` | Deck variants of ablation, friction_funnel, red_precision, catch_by_pattern and fv_enrolment: no in-chart title, all text ≥ 17 px, 14 px footnote, for placing about 420 px wide. |
| `sim_v02pre_baseline.json` | Snapshot of `deck_numbers.json` from the previous report (commit 36e6653: green 0.15, one-directional voice, Family Verify offered, checklist at Amber only); copied into `deck_numbers.json` as `v02pre_*`. |
| `sim_summary_calibrated.json` | The headline run with `voice.mode: calibrated` (measured band LRs). `deck_numbers.json` carries it as `calibrated_*`, plus `calibrated_realcall_*`, which uses real-call bona fide band rates (stress). |
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

Final changes (after the v0.2 review):
- **green_below 0.10 → 0.15:** meets the Pause & Verify budget (5.5% ≤ 6%), at a cost of about 1.4 pp of scam Amber+.
- **One-directional voice:** `voice_no_strong_evidence` LR 0.7 → 1.0, and every voice-band LR (assumed or measured) is floored at 1.0. The detector can raise suspicion, never lower it. With strict G2 it cannot create or remove a hold.
- **Simulator fix:** the voice step used to *overwrite* the checklist's cue answers with the ASR cues, which wiped checklist-derived holds whenever a voice check ran. ASR cues now add to the checklist answers. This alone raised weighted scam Red by about 3 pp (T3 most).

## Headline v0.1 → v0.2 pre → v0.2 final (π0 1/400, θ_red 0.75, green_below 0.15, 30% voice uptake, placeholder detector rates)

"v0.2 pre" is the previous report (36e6653). "Final" adds A19 (auto Family Verify, 90% not cancelled) and A20 (checklist whenever the context alone was Amber).

- **Genuine:** Pause & Verify 10.1 → 5.5 → 5.6% (budget ≤ 6%: met). Held 0.92 → 0.21 → 0.21% (budget ≤ 0.25%: met).
- **Scams held (Red):** T1 65 → 54 → 59%, T2 77 → 72 → 72%, T3 85 → 80.5 → 81%, weighted 77 → 71 → 73%. Amber+ stays about 95%.
- **Genuine holds per scam held:** 4.8 → 1.2 → 1.2 at 1/400. ₹ protected per ₹ delayed: 1.19 → 2.88 → 2.98.
- **FV enrolment 20 / 35 / 50 / 70 / 90%, T1 held:** offered 51 / 53 / 54 / 56 / 58% → auto-sent 53 / 56 / 59 / 62 / 66%.

## Voice detector: shadow (default deck numbers) vs calibrated

`ml/results/metrics.json` is used directly. Seen spoofs come from `test_seen_generators`, unseen from `test_phone_channels_heldout_generators`, and bona fide from `test_phone_channels`. Calibrated band LRs are 70.5 / 2.91 / 1.0 (floored).

Holds are identical in both modes: scams held 72.6%, genuine held 0.211%, Pause & Verify 5.63%. That follows from three rules: the voice check is only offered on Pause & Verify, LRs are ≥ 1, and strict G2 applies. Calibrated changes p, and keeps genuine final Amber 0.005 pp higher.

