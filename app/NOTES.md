# Implementation notes and SPEC proposals

**Status (SPEC v0.2):** the coordinator adopted proposals B1, B2, B3, B4, B6 and B7 below into SPEC v0.2; the engine, server, web and simulator now implement them (config v0.2.0).
- B5 (precision of Red) is addressed by tuning θ_red with the simulator. See `engine/results/sim_threshold_sweep.json` and `deck_numbers.json`.
- Section A2 is superseded by strict G2, A3 by the v0.2 rules in A13, and A4 by G7.
- **Final v0.2 tuning (coordinator decision, for SPEC.md):**
  - `tiers.green_below` **0.15** (was 0.10). θ_red stays **0.75**. At π0 = 1/400 this meets both budgets: genuine Pause & Verify 5.5% (≤ 6%) and genuine Red 0.21% (≤ 0.25%). Scam Amber+ drops 96.3 → 95.0% (T1 96.2 → 92.9%).
  - **Voice is one-directional.** `voice_no_strong_evidence` LR **1.0** (was 0.7), and `voice.lr_floor: 1.0` floors every voice-band LR, assumed or measured, at 1.0. The config refuses to load an assumed voice-band LR below 1.0. Deck line: "the detector can raise suspicion, never lower it", because detectors miss unseen generators. With strict G2 the detector band can lift Green → Amber but never create or remove a hold (A18).
  - New sensitivity: Family Verify enrolment (A19).

The SPEC is implemented as written. The prototype has to make some choices the SPEC leaves open; they are listed in section A. Section B lists changes we recommend the SPEC adopt. Section C covers the contract with the ML teammate. None of these edits SPEC.md.

## A. Interpretations made in the prototype

1. **When the claim question is asked** (`tiers.ask_claim_at_or_above: 0.01`). SPEC says the question is "asked only when the trigger fires". We skip it when context alone is clearly benign (stage-1 p < 1%, e.g. a saved domestic caller and a small new payee). This is what keeps L1 at zero screens.
   - Every other triggered payment gets the one-tap question. T2's strongest signals (`claim_bank`, `bank_claim_not_1600`) only exist after the claim, and T2's stage-1 p is about 0.07.
2. **G2.** We read "V alone can never push above Amber" as: V never counts as one of the two corroborating families in G1(a). Voice can still add log-odds; it cannot be the reason a payment is held.
3. **G4 conflicts.** When a decisive positive and a decisive negative are both present (e.g. `fv_confirmed` + `callback_denied`), G4 is not applied and the case is scored normally. The note `G4 not applied` is shown.
4. **G5** does not apply when a decisive out-of-band negative is present.
5. **G3** is applied by the engine. The server passes the detector's raw band, so the console shows the G3 downgrade explicitly instead of hiding it inside the voice service.
6. **Exclusive groups.** `fri_*`, `amount_gt_p95/p99`, `payee_flagged_*`, the voice bands and each O-check keep only their strongest member, so nothing double counts.
7. **Voice floor (superseded: voice is now one-directional, see the status note and A18).** Every voice-band LR is floored at 1.0 (`voice.lr_floor`), so "sounds real" is neutral and measured data can never make any band reassuring. Unseen generators are the realistic case.
8. **Privacy of silent Greens.** A triggered payment that clears silently creates no case. Only an anonymous counter is kept (SPEC 5). Cases exist only once the customer has interacted.
9. **Family Verify message.** It shows an amount band (exact only for round figures, otherwise "about ₹X") and the payee name. The relative never sees the caller number or any history.
10. **Hold release.** Below ₹50,000, a positive out-of-band check lets the customer release the hold. At ₹50,000 or more, an analyst must release it, even after a positive check. Expiry never auto-sends.
11. **Report pre-fill.**
    - The Chakshu medium and category values are copied from the live form (sancharsaathi.gov.in/sfc, checked 2026-10-06).
    - The NCRP field labels follow the public NCRP user manual and acknowledgement slips. Verify them against the live form before production.
12. **Demo clock.** `PEHCHAAN_DEMO_TIME=HH:MM` shifts the server clock for screenshots. Clients count down against the `X-Server-Now` header, so the timers stay correct.

13. **v0.2 rule ordering in `fusion.assess`.** G3, then G7, then G5, then G4, then G1, then strict G2.
    - G7 (`fv_denied`, `bank_no_active_call`) beats a trusted payee and a decisive positive.
    - A decisive positive together with a user-reported negative (`callback_denied`, `safeword_failed`) gets no Green override. The result is at least Amber, with the note "G4 not applied".
14. **How G1(a) counts families.** Each family's ln-LR is recomputed without the trigger-implied codes (`payee_new`, `amount_gt_*`) and clipped to the cap. V never counts.
    - User-reported negatives (LR 30) can still be the O family in G1(a). They are strong evidence, just not a floor.
15. **The named bank.**
    - "My bank" opens a bank picker. The demo has Bharat Demo Bank (integrated) and "Another bank" (not integrated).
    - If no bank is named, or the named bank is not integrated, the registry lookup returns `bank_registry_unknown` (LR 1). The UI then shows that reason with "hang up and call the official number".
16. **Cue checklist.** It is offered for `claim_none` / `claim_other` when the tier is Amber.
    - It is sent as `cues[]` plus `checklist_done`. "None of these" closes it without adding signals.
17. **Cancel-primary.** After a user-reported negative, the Amber screen shows Cancel as the saffron primary button with "Cancel is the safer choice", and the claim checks lose their primary styling.
18. **What "voice never creates or removes a hold" covers.**
    - It covers the detector band and the watermark (family V): LRs are ≥ 1, G1 never counts V, and strict G2 caps a V-tipped Red at Amber. The engine and simulator tests check this (`test_v02.py`, `test_voice_is_one_directional_in_the_flow`).
    - It does not cover the script cues the ASR hears in the same audio (family S: secrecy, OTP, arrest threat). Those are ordinary evidence and can qualify a Red through G1. In the simulator, this is the whole of the voice layer's +3.4 pp of scam holds and +0.014 pp of genuine holds.
    - In the product flow the voice check is only offered on the Pause & Verify screen. So in practice the band's Green → Amber lift appears only through the API, not in the simulated flow.
    - Simulator bug fixed with this change: the voice step used to overwrite the checklist cue answers with the ASR cues instead of adding to them. That wiped checklist-derived holds whenever a voice check ran, and is why the previous report showed voice slightly lowering scam holds.
19. **Family Verify enrolment sensitivity.** `fv.enrolled` is set to 0.2 / 0.35 / 0.5 / 0.7 / 0.9 in every scenario, regenerating the same sessions from the same seed (`sim_sensitivity.json` → `fv_enrolment`, `chart_fv_enrolment.svg`, `deck_numbers.json` → `t1_red_pct_by_fv_enrolment`).
    - T1 held goes 51 → 58% and weighted scam held 71 → 73%. T1 Amber+ is flat at 93%, and genuine friction is flat.
    - The ceiling is uptake, not enrolment. Even at 90% enrolment, only 34% of T1 victims run Family Verify (assumed 50% uptake, because "police took his phone").
    - What-if, not in the deck numbers: with Family Verify sent by default after "Family member" (uptake 0.9), T1 held is 59% at 50% enrolment and 66% at 90%.
    - Proposal: send Family Verify automatically when the payer names an enrolled relative, rather than offering it as an option.
20. **Green 0.15 and coached "No one" on T1.** T1's demo context (stage-1 p 0.158) answered "No one" (LR 0.8) falls to p 0.13 and now proceeds Green. That is the accepted Amber+ cost. "Someone else" (LR 1.0) stays Amber with the checklist. The checklist demo and screenshot 13 therefore use T3 (digital arrest), where coaching to say "no one" is the pattern itself.
    - Possible follow-up: show the checklist whenever stage-1 context was Amber and the answer is "No one", even if the claim drops p below green_below.

## B. Proposed SPEC changes (product-logic weak spots). B1–B4, B6 and B7 were adopted in v0.2

From the simulator (`engine/results/`, assumption-driven) and from building the flows:

1. **`fv_denied` should be a hard Red floor.**
   - With a known, non-trusted payee and no amount flag, `claim_family + fv_denied` gives p ≈ 0.53. That is Amber, so "Continue anyway" is offered after the real relative has said "not me".
   - Proposal: a decisive O-negative forces Red regardless of p (or set the O cap and LR so that it does).
2. **The payment-context family qualifies for G1 too easily.** `payee_new × amount_gt_p95 = 4.5 ≥ 3`, and those are the very conditions that fire the trigger. So "two independent families" often means "context plus anything".
   - Proposal: require that at least one of the two G1(a) families is not P, or raise P's G1 threshold.
3. **Bank-claim false holds dominate genuine Red** (0.92% of genuine sessions end Red).
   - Genuine bank calls not yet on the 1600 series go Red right after the claim.
   - Merchant and UPI-app calls answered as "Bank or UPI app" pick up `bank_claim_not_1600`, then `bank_no_active_call`.
   - Proposals:
     - split the option into "My bank" and "UPI app or shop";
     - run the registry only against the bank actually named;
     - treat `bank_active_call_1600` as a decisive positive under G4;
     - treat a registry miss for a bank that isn't integrated as "unknown", not `bank_no_active_call`.
4. **User-reported checks are treated as decisive.** `callback_denied` and `safeword_failed` come from the user's own tap. A mis-tap or a panicked safe word is then decisive, and out-of-band checks double genuine Red (0.42% → 0.85% in the simulator).
   - Proposal: user-reported negatives count as strong (LR 30), but not decisive for G1(b). Only device-signed `fv_denied` and the registry are decisive.
5. **Precision of Red at the default prior.** At π0 = 1/400, 4.8 genuine holds occur per scam held, and ₹ protected is only 1.19× the genuine ₹ delayed. At the base-rate-derived π0 ≈ 1/1300 it is 3.7 per scam.
   - The deck should present Red as a 30-minute *pause with a human path*, not a block, and lead with the out-of-band checks that resolve most of these.
6. **Voice can still tip p over 0.6** when two other families qualify (detector false positives on noisy elderly lines).
   - Proposal: if removing V would drop the tier below Red, cap at Amber (a strict G2).
7. **Coached "No one" answers.** 15–25% of coached victims answering "No one" (assumed) still lose the claim signal.
   - The tap checklist (secrecy, OTP, arrest threat) is implemented in the API as `cues[]` but not in the UI yet. Consider showing it for `claim_none` / `claim_other` when context is Amber.

## C. ML contract for measured voice LRs

Set `voice.lr_source: ../../ml/results/metrics.json` in `engine/pehchaan/config.yaml`. That one line switches the engine from assumed to measured voice LRs. The loader looks anywhere in the JSON for either shape:

```json
{"model_version": "xlsr-aasist-…", "held_out": {"band_rates": {
  "spoof":    {"likely_synthetic": 0.55, "inconclusive": 0.30, "no_strong_evidence": 0.15},
  "bonafide": {"likely_synthetic": 0.05, "inconclusive": 0.20, "no_strong_evidence": 0.75}}}}
```

or `{"band_lr": {"likely_synthetic": 7.1, "inconclusive": 1.0, "no_strong_evidence": 0.4}}`.

- Paths containing `held_out` are preferred.
- Band thresholds are p ≥ 0.70 for `likely_synthetic` and p < 0.30 for `no_strong_evidence`, plus the quality gate (speech ≥ 4 s and SNR ≥ 10 dB).
- The simulator reads the same file automatically.
- The live service plugs in through `VOICE_SERVICE_URL`. Expected response: `{p_synthetic, band, quality{speech_sec, snr_db, ok}, watermark{detected, scheme}, model_version, latency_ms}`.
