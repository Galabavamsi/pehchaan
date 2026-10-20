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

## Held-out handset D2 (scored 2026-10-20, calls placed 2026-10-19)

D2 (Redmi Note 12 Pro, Jio) was registered as a **test-only handset before any D2 data existed** (`protocol.py`),
so nothing from it shaped training, the learned channel or any threshold. Five tape calls on 19 Oct 16:29–16:53
were answered by hand on speaker: 80 items aligned, **41 QC-ok (51 %)**, 20 genuine and 21 clones. Scored on the
laptop CPU with the same checkpoints (`infra/score_realcall_local.sh D2`); thresholds unchanged (each model's
simulated-test EER point). Median SNR of QC-ok items 19.2 dB (D1 test: 24.6 dB); room noise floor −60.7 dB
(D1: −61.8 dB), so the room matched the D1 sessions and the difference is the handset.

| Model | D2 EER | AUC | Clones caught | Genuine flagged | (D1 test, for reference) |
|---|---|---|---|---|---|
| v1 (Round 1, served) | 39.0 % | 0.667 | 15/21 = 71 % (95 % CI 50–86 %) | 9/20 = 45 % (26–66 %) | 24.6 % EER, 3 % flagged |
| **A: learned channel + real-call clips** | **19.5 %** | **0.933** | 20/21 = 95 % (77–99 %) | **7/20 = 35 % (18–57 %)** | 6.8 % EER, 0 % flagged |

What it means:

1. **Model A's gain does not transfer to a new handset.** EER roughly triples (6.8 % → 19.5 %), and a third of
   genuine speech is flagged, where D1 had none. The learned channel was fitted on D1 only; D2's speaker path
   (and its ~5 dB lower SNR) is different. A still beats v1 on every metric here.
2. **This is the false-alarm failure mode the gate exists to catch**, now on our own data: a detector that
   looks clean on the handset it was tuned around flags real people on another phone. Voice stays in shadow mode
   (G2); the decision rests on Family Verify, the bank registry and the safe word.

Caveats: 41 clips from 5 calls (wide intervals above), two speakers, one session, one seed; half the D2 items
failed QC. The 20 Oct follow-up session failed QC entirely (room floor −34 dB, Speaker on late) and is not in
these numbers. Still not shown: live genuine callers and the gate (≥ 50 live calls).
