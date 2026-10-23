# Real-call findings (2026-10-17)

The served Round 1 detector (`pehchaan-xlsr-aasist-ft-v1`) was scored on consented tape calls over a real
Indian network: Vobiz number → Jio → Samsung M34 (D1) on speakerphone → laptop mic. Each tape mixes ~10 s
genuine items (S01, S02 team recordings) with content-matched clones of the same lines (XTTS-v2, F5,
F5-Hindi, CosyVoice2, Chatterbox, Seed-VC). Raw `p_synthetic` is reported because the service's quality gate
withholds most verdicts (see below). Nothing here has been trained on: this is the "before" measurement.

| Batch | Set-up | Calls | Items | QC ok | Median SNR | Genuine flagged (p ≥ 0.8) | Clones caught (p ≥ 0.8) | EER |
|---|---|---|---|---|---|---|---|---|
| B1 | phone at arm's length, quiet, items 3–9 s then ~10 s | 10 | 98 | 74 % | 14.8 dB | 3 % | 29 % | 34.2 % |
| B2 | phone 5 cm from mic, noisy room | 10 | 100 | 95 % | 25.4 dB | 4 % | 28 % | 27.4 % |
| B3 | 5 cm, quiet, hands-free (adb answer + speaker) | 21 | 210 | 100 % | 26.2 dB | **0 %** | **28 %** | **24.8 %** |
| All | | 41 | 378 QC-ok | | | | | 29.1 % |

Same detector on simulated channels: 4.8 % EER (Round 1). Two consented speakers, one handset, one carrier.

## What it means

1. **On real lines the problem is missed clones, not false alarms.** Genuine speech stayed at median
   p ≈ 0.001 for both speakers (0 of 105 flagged in B3). Clones drift towards "real": median p 0.31 and only
   28 % above 0.8. By generator (B3): Seed-VC 40 %, F5-Hindi 36 %, XTTS 28 %, CosyVoice2 25 %, F5 24 %,
   Chatterbox 18 %.
2. This differs from Round 1's single real call (genuine flagged 91–95 %). That was a dialer recording of
   two people talking; this is the speakerphone path the product actually uses. Both say the same thing:
   simulated codecs don't predict real-network behaviour.
3. **The service's quality gate (≥ 4 s speech, ≥ 10 dB SNR by Silero VAD) passes only 29 of 210 B3 clips**,
   even at 26 dB energy SNR. Silero under-detects narrowband speakerphone speech. Either the gate needs
   recalibrating on real captures, or the capture path needs to be closer (an in-app capture, not a laptop).
4. Capture matters as much as the model: arm's length cost about 10 dB of SNR and 9 EER points.

This supports the core design: voice stays a supporting clue (shadow mode, G2), and the decision rests on
verifying the person out of band.

## Method notes

- Alignment: start and end chirps by matched filter, drift-corrected; items placed by log-energy envelope
  correlation (median NCC ≈ 0.76). If speaker came on late and only one chirp is heard, ingest infers which
  one it was. The answer XML now waits 6 s before playing.
- QC: speech seconds and SNR are measured against the noise floor of the silent gaps between items.
- Dialer recordings: none. Samsung's auto-record never produced files on this phone
  (`settings system record_calls_automatically_on_off` stays 0).
- Splits are pre-registered (`protocol.py`): S02 and `sarvam_ivc` are test-only, everything else by call hash.
  Current QC-ok split: train 112, dev 30, test 236 items.

## Learned speakerphone channel (for retraining)

`learned_channel.py` estimates the real path's magnitude response, noise and SNR from aligned
(tape reference, real capture) pairs: **train-split calls only** (112 items, 24 calls), so test calls and S02
never shape it. Shape: −24 dB at 300 Hz and −36 dB at 200 Hz (small phone speaker), +7 dB resonance near 3 kHz,
cut-off above ~4 kHz; real noise bank 111 s; SNR 15–29 dB.

Validation: the same detector on 30 clean team pairs pushed through the learned channel catches **27 %** of
clones at p ≥ 0.8 (clean: median p 0.97) and flags **0 %** of genuine. The real calls showed 28 % and 0 %, so the
channel reproduces the failure and can turn the whole corpus into realistic training data (`--aug_set v3`).

## Retraining results (2026-10-19, g5.2xlarge, single seed, same v1 recipe, `infra/retrain_v3.sh`)

Real-call test split: 236 clips from 41 calls (S02 held-out speaker + S01 calls hashed to test), never trained on.
"Caught / flagged" use each model's EER threshold from the simulated test sample, applied unchanged to real calls.

| Model | Real-call EER | S02 EER | AUC | Clones caught | Genuine flagged | Sim EER | Sim held-out gens EER |
|---|---|---|---|---|---|---|---|
| v1 (Round 1, served) | 24.6 % | 21.7 % | 0.844 | 48 % | 3 % | 4.8 % | 18.1 % |
| B: + real-call clips | 9.3 % | 9.8 % | 0.963 | 69 % | 0 % | 5.7 % | 14.0 % |
| C: + learned channel | 18.6 % | 18.5 % | 0.907 | 67 % | 6 % | 5.7 % | 15.1 % |
| **A: both** | **6.8 %** | **8.7 %** | **0.988** | **75 %** | **0 %** | 6.1 % | 14.8 % |

Held-out generators stay hardest on real calls for A: Chatterbox 43 %, Seed-VC 62 % caught (XTTS 94 %, F5-Hindi 94 %,
CosyVoice2 88 %, F5 58 %). Caveats: one handset, carrier and room in both train and test; same script lines;
41 calls; one seed. Not yet shown: another handset (D2), live genuine callers, the gate (≥ 50 live calls).

## Held-out handset D2 (calls 19, 20 and 23 Oct 2026 IST, scored 23 Oct)

D2 (Redmi Note 12 Pro, Jio) was registered as a **test-only handset before any D2 data existed** (`protocol.py`),
so nothing from it shaped training, the learned channel or any threshold. Tape calls on speaker, laptop mic ~5 cm
away; scored on the laptop CPU with the same checkpoints (`infra/score_realcall_local.sh D2`); thresholds unchanged
(each model's simulated-test EER point). The pre-registered measure is **all QC-ok D2 test clips**; per-session rows
are shown so no session is picked.

| Session (IST) | How answered | Calls with QC-ok items | QC-ok / aligned | Median SNR |
|---|---|---|---|---|
| 19 Oct | by hand | 5 | 41 / 70 | 19.2 dB |
| 20 Oct | by hand, room got louder (stopped early) | 7 | 34 / 90 | 16.4 dB |
| 23 Oct | **unattended over adb** (`--auto-answer --lock-first`), quiet room | 20 | 199 / 230 | 16.7 dB |
| **all** | | **32** | **274** (138 genuine, 136 clones) | 16.9 dB |

(23 Oct includes one diagnostic call where speaker came on; the three earpiece-only diagnostic calls all failed QC.)

| Model | Session | Clips | EER | AUC | Clones caught | Genuine flagged |
|---|---|---|---|---|---|---|
| v1 (Round 1, served) | 19 Oct | 41 | 39.0 % | 0.667 | 15/21 | 9/20 |
| | 20 Oct | 34 | 44.1 % | 0.604 | 9/16 | 6/18 |
| | 23 Oct | 199 | 23.1 % | 0.818 | 29/99 | 1/100 |
| | **all** | **274** | **28.8 %** | **0.737** | **53/136 = 39 % (31–47 %)** | **16/138 = 12 % (7–18 %)** |
| A: learned channel + real-call clips | 19 Oct | 41 | 19.5 % | 0.933 | 20/21 | 7/20 |
| | 20 Oct | 34 | 17.7 % | 0.830 | 12/16 | 2/18 |
| | 23 Oct | 199 | 10.1 % | 0.971 | 83/99 | 2/100 |
| | **all** | **274** | **11.7 %** | **0.935** | **115/136 = 84.6 % (78–90 %)** | **11/138 = 8 % (5–14 %)** |

(95 % Wilson intervals. D1 test calls for reference: v1 24.6 % EER, 3 % flagged; A 6.8 % EER, 75 % caught, 0 % flagged.)

**Sarvam (`sarvam_ivc`, a commercial generator no model was trained on, test-only):** 12 clone items reached D2
QC-ok. **Both models caught 0/12** (95 % CI 0–24 %); median scores were far on the "genuine" side (A −6.2 vs threshold
−0.3; v1 −10.4 vs −2.5). Without Sarvam, A caught 115/124 of the other clones.

What it means:

1. **Model A's gain mostly transfers to a new handset, not fully.** EER 6.8 % on D1 → 11.7 % on D2; a few genuine
   clips are flagged (8 %) where D1 had none. A beats v1 on every metric. (A smaller 20 Oct estimate of 24 % genuine
   flagged came from 75 hand-answered clips and is superseded by the full set above.)
2. **Capture consistency matters as much as the model.** The hand-answered sessions flagged 9/38 genuine clips; the
   unattended session, with the same speaker route every call, flagged 2/100. An in-app capture path is the fix.
3. **A new commercial cloner beat both detectors on every clip.** This is the strongest evidence so far for the
   product rule: voice stays in shadow mode (G2), and the decision rests on Family Verify, the bank registry and the
   safe word.

Caveats: two speakers, one carrier, one room per session, one seed; sessions differ in conditions; Sarvam n = 12.
Still not shown: live genuine callers and the gate (≥ 50 live calls).

## Live system checks (20–23 Oct 2026)

Measured on the deployed demo (`api.` / `demo.humanslop.in`, EC2 c7i.large in ap-south-1) with two real phones.

- **Live attack call** (`dial attack`, Sarvam clone of consenting S02, Hindi T1 script, 17 s): 5/5 test calls to
  Phone A answered and played in full, normal hangup (20 Oct). Never recorded or ingested.
- **T1 with the live attack call** (20 Oct, Phone A = payer, Phone B = relative, both on the deployed URLs):
  case created at Pay 19:01:38 IST, auto Family Verify after the claim, "not me" on Phone B → Red hold (G7) at
  19:01:52: **14 s from Pay to hold** (server case timestamps).
- **T3 with a live attack call** (21 Oct, T3 script clip): Pay 00:28:55 → Red hold 00:28:59 IST, **4 s**; then reported.
- **Voice service on the deployed box** (2 vCPU, CPU int8): **3.1 s per 10 s clip** (4 runs, 3,086–3,143 ms), against
  1.1 s on the team laptop's CPU. Above the SPEC budget of 1.5 s; voice is shadow-only, so no decision waits on it.
