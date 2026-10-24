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

## On site, 24 Oct 2026: clone-vs-detect benchmark, scored the way the bench scores

`ml/eval/clone_vs_detect.py` measures how convincing each cloner is (ClonEval speaker similarity with WavLM x-vectors)
and how often each detector catches it, on three sets: the consented corpus (S01, S02 genuine lines and content-matched
clones), the same files through the simulated AMR-NB codec, and the 510 pre-registered real-call test clips.
Run 14:14–16:19 IST on 24 Oct through the voice service (`--service`, CPU int8,
`pehchaan-xlsr-aasist-ft-v1+819e67f7f86e`). Results are in `ml/results/clone_vs_detect.json`, which `#/benchmark` reads.

**Why it was re-scored.** A first run earlier today (never committed) scored clips differently from the detector bench
(`#/bench`, `serve/panel.py`):
- at most 8 windows per clip, with mostly silent windows kept;
- NII on each clip's first 16 s only;
- v1 from its training checkpoint rather than the served export;
- real-call v1 and A from their stored scores.

The voice service, the bench and the benchmark now share one scoring plan, `ml/common/scoring.py`. On 5 clips the service
and the benchmark gave the same v1 score to 4 decimals. Speaker similarity uses no detector and is carried over from the
first run.

**The pre-registered real-call numbers above are unchanged.** The benchmark's real-call rows are its own scoring of the
same clips. Its stored-score rows (the last three tables) reproduce the pre-registered D1 and D2 figures exactly.

Every table below is printed by
`cd ml && python eval/clone_vs_detect.py --tables --compare realcall/work/bench/clone_vs_detect_old_scoring.json`;
none is typed by hand. Each detector keeps its own threshold (its EER point on the simulated test sample), unchanged.

**First run vs the bench's scoring** (same clips and thresholds; the first run scored at most 8 windows per clip with silence kept, NII on each clip's first 16 s only and v1 from its training checkpoint, and took real-call v1 and A from their stored scores):

| Condition | Detector | Genuine flagged, first run | Genuine flagged, bench scoring | Clones caught, first run | Clones caught, bench scoring |
|---|---|---|---|---|---|
| Clean | v1 | 44/124 = 35.5 % | 44/124 = 35.5 % | 221/357 = 61.9 % | 228/357 = 63.9 % |
| Clean | A | 40/124 = 32.3 % | 40/124 = 32.3 % | 221/357 = 61.9 % | 226/357 = 63.3 % |
| Clean | NII | 41/124 = 33.1 % | 41/124 = 33.1 % | 354/357 = 99.2 % | 354/357 = 99.2 % |
| Clean | LA (off the shelf) | 89/124 = 71.8 % | 85/124 = 68.5 % | 224/357 = 62.7 % | 217/357 = 60.8 % |
| Clean | Fused A+NII+v1 | 44/124 = 35.5 % | 44/124 = 35.5 % | 271/357 = 75.9 % | 269/357 = 75.4 % |
| AMR-NB | v1 | 45/124 = 36.3 % | 43/124 = 34.7 % | 206/357 = 57.7 % | 208/357 = 58.3 % |
| AMR-NB | A | 30/124 = 24.2 % | 30/124 = 24.2 % | 183/357 = 51.3 % | 184/357 = 51.5 % |
| AMR-NB | NII | 68/124 = 54.8 % | 68/124 = 54.8 % | 354/357 = 99.2 % | 354/357 = 99.2 % |
| AMR-NB | LA (off the shelf) | 108/124 = 87.1 % | 107/124 = 86.3 % | 280/357 = 78.4 % | 273/357 = 76.5 % |
| AMR-NB | Fused A+NII+v1 | 43/124 = 34.7 % | 43/124 = 34.7 % | 235/357 = 65.8 % | 233/357 = 65.3 % |
| Real calls | v1 | 20/256 = 7.8 % | 24/256 = 9.4 % | 110/254 = 43.3 % | 95/254 = 37.4 % |
| Real calls | A | 11/256 = 4.3 % | 13/256 = 5.1 % | 204/254 = 80.3 % | 170/254 = 66.9 % |
| Real calls | NII | 146/256 = 57.0 % | 146/256 = 57.0 % | 120/254 = 47.2 % | 122/254 = 48.0 % |
| Real calls | LA (off the shelf) | 182/256 = 71.1 % | 189/256 = 73.8 % | 204/254 = 80.3 % | 201/254 = 79.1 % |
| Real calls | Fused A+NII+v1 | 11/256 = 4.3 % | 12/256 = 4.7 % | 152/254 = 59.8 % | 127/254 = 50.0 % |

**Clean audio**, all speakers (481 clips, 2.44 windows per clip on average):

| Cloner | Similarity | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|---|
| Sarvam instant cloning (never trained on) | 0.943 | 0/71 = 0.0 % | 0/71 = 0.0 % | 71/71 = 100.0 % | 23/71 = 32.4 % | 0/71 = 0.0 % |
| F5-TTS | 0.942 | 20/26 = 76.9 % | 22/26 = 84.6 % | 23/26 = 88.5 % | 4/26 = 15.4 % | 21/26 = 80.8 % |
| CosyVoice2 | 0.938 | 16/26 = 61.5 % | 17/26 = 65.4 % | 26/26 = 100.0 % | 2/26 = 7.7 % | 20/26 = 76.9 % |
| Chatterbox (never trained on) | 0.932 | 40/50 = 80.0 % | 45/50 = 90.0 % | 50/50 = 100.0 % | 18/50 = 36.0 % | 50/50 = 100.0 % |
| F5-TTS Hindi | 0.915 | 23/24 = 95.8 % | 24/24 = 100.0 % | 24/24 = 100.0 % | 19/24 = 79.2 % | 24/24 = 100.0 % |
| Seed-VC (never trained on) | 0.890 | 79/110 = 71.8 % | 69/110 = 62.7 % | 110/110 = 100.0 % | 106/110 = 96.4 % | 104/110 = 94.5 % |
| XTTS-v2 | 0.845 | 50/50 = 100.0 % | 49/50 = 98.0 % | 50/50 = 100.0 % | 45/50 = 90.0 % | 50/50 = 100.0 % |
| **All clones** (95 % CI) | – | 228/357 = 63.9 % (58–69 %) | 226/357 = 63.3 % (58–69 %) | 354/357 = 99.2 % (97–100 %) | 217/357 = 60.8 % (55–66 %) | 269/357 = 75.4 % (70–80 %) |
| **Genuine flagged** (95 % CI) | 0.936 (ceiling) | 44/124 = 35.5 % (27–45 %) | 40/124 = 32.3 % (24–41 %) | 41/124 = 33.1 % (25–42 %) | 85/124 = 68.5 % (59–77 %) | 44/124 = 35.5 % (27–45 %) |

*Clarification, 24 Oct evening:* the genuine row is two kinds of recording. 44 of S02's 79 genuine clips
(`team_S02-S01_Ecellular_*`) are dialer recordings captured from the network side of a real cellular call; the
other 80 (S01 45, S02 35) are direct microphone recordings. Every v1, A and NII flag on genuine clean audio is one of
the 44 dialer clips (v1 44/44, A 40/44, NII 41/44); the 80 direct recordings were flagged 0/80 by each. Off the shelf
(LA) flags both kinds (direct 41/80, dialer 44/44). So the clean-audio false flags describe call audio recorded on the
network side, not microphone recordings. Counts from the per-clip cache
`ml/realcall/work/bench_v2/clean__panel.csv` with each detector's panel threshold (`serve/panel_config.json`).

Clean audio, held-out speaker S02 only:

| Cloner | Similarity | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|---|
| Sarvam instant cloning (never trained on) | 0.943 | 0/30 = 0.0 % | 0/30 = 0.0 % | 30/30 = 100.0 % | 18/30 = 60.0 % | 0/30 = 0.0 % |
| F5-TTS | 0.942 | 7/13 = 53.8 % | 9/13 = 69.2 % | 10/13 = 76.9 % | 0/13 = 0.0 % | 8/13 = 61.5 % |
| CosyVoice2 | 0.938 | 5/13 = 38.5 % | 5/13 = 38.5 % | 13/13 = 100.0 % | 0/13 = 0.0 % | 7/13 = 53.8 % |
| Chatterbox (never trained on) | 0.932 | 18/26 = 69.2 % | 22/26 = 84.6 % | 26/26 = 100.0 % | 12/26 = 46.2 % | 26/26 = 100.0 % |
| F5-TTS Hindi | 0.915 | 12/13 = 92.3 % | 13/13 = 100.0 % | 13/13 = 100.0 % | 11/13 = 84.6 % | 13/13 = 100.0 % |
| Seed-VC (never trained on) | 0.890 | 31/50 = 62.0 % | 24/50 = 48.0 % | 50/50 = 100.0 % | 47/50 = 94.0 % | 44/50 = 88.0 % |
| XTTS-v2 | 0.845 | 26/26 = 100.0 % | 25/26 = 96.2 % | 26/26 = 100.0 % | 22/26 = 84.6 % | 26/26 = 100.0 % |
| **All clones** (95 % CI) | – | 99/171 = 57.9 % (50–66 %) | 98/171 = 57.3 % (49–65 %) | 168/171 = 98.2 % (94–100 %) | 110/171 = 64.3 % (56–72 %) | 124/171 = 72.5 % (65–79 %) |
| **Genuine flagged** (95 % CI) | 0.936 (ceiling) | 44/79 = 55.7 % (44–67 %) | 40/79 = 50.6 % (39–62 %) | 41/79 = 51.9 % (41–63 %) | 71/79 = 89.9 % (81–95 %) | 44/79 = 55.7 % (44–67 %) |

**AMR-NB phone codec (simulated)**, all speakers (481 clips, 2.44 windows per clip on average):

| Cloner | Similarity | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|---|
| Sarvam instant cloning (never trained on) | 0.943 | 0/71 = 0.0 % | 0/71 = 0.0 % | 71/71 = 100.0 % | 42/71 = 59.2 % | 0/71 = 0.0 % |
| F5-TTS | 0.942 | 23/26 = 88.5 % | 20/26 = 76.9 % | 26/26 = 100.0 % | 16/26 = 61.5 % | 25/26 = 96.2 % |
| CosyVoice2 | 0.938 | 13/26 = 50.0 % | 14/26 = 53.8 % | 24/26 = 92.3 % | 5/26 = 19.2 % | 18/26 = 69.2 % |
| Chatterbox (never trained on) | 0.932 | 35/50 = 70.0 % | 36/50 = 72.0 % | 49/50 = 98.0 % | 33/50 = 66.0 % | 40/50 = 80.0 % |
| F5-TTS Hindi | 0.915 | 23/24 = 95.8 % | 20/24 = 83.3 % | 24/24 = 100.0 % | 22/24 = 91.7 % | 24/24 = 100.0 % |
| Seed-VC (never trained on) | 0.890 | 64/110 = 58.2 % | 48/110 = 43.6 % | 110/110 = 100.0 % | 107/110 = 97.3 % | 76/110 = 69.1 % |
| XTTS-v2 | 0.845 | 50/50 = 100.0 % | 46/50 = 92.0 % | 50/50 = 100.0 % | 48/50 = 96.0 % | 50/50 = 100.0 % |
| **All clones** (95 % CI) | – | 208/357 = 58.3 % (53–64 %) | 184/357 = 51.5 % (46–57 %) | 354/357 = 99.2 % (97–100 %) | 273/357 = 76.5 % (71–81 %) | 233/357 = 65.3 % (60–71 %) |
| **Genuine flagged** (95 % CI) | 0.936 (ceiling) | 43/124 = 34.7 % (26–44 %) | 30/124 = 24.2 % (17–33 %) | 68/124 = 54.8 % (46–64 %) | 107/124 = 86.3 % (79–92 %) | 43/124 = 34.7 % (26–44 %) |

AMR-NB phone codec (simulated), held-out speaker S02 only:

| Cloner | Similarity | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|---|
| Sarvam instant cloning (never trained on) | 0.943 | 0/30 = 0.0 % | 0/30 = 0.0 % | 30/30 = 100.0 % | 18/30 = 60.0 % | 0/30 = 0.0 % |
| F5-TTS | 0.942 | 10/13 = 76.9 % | 7/13 = 53.8 % | 13/13 = 100.0 % | 5/13 = 38.5 % | 12/13 = 92.3 % |
| CosyVoice2 | 0.938 | 0/13 = 0.0 % | 1/13 = 7.7 % | 12/13 = 92.3 % | 1/13 = 7.7 % | 5/13 = 38.5 % |
| Chatterbox (never trained on) | 0.932 | 16/26 = 61.5 % | 15/26 = 57.7 % | 26/26 = 100.0 % | 17/26 = 65.4 % | 17/26 = 65.4 % |
| F5-TTS Hindi | 0.915 | 12/13 = 92.3 % | 9/13 = 69.2 % | 13/13 = 100.0 % | 13/13 = 100.0 % | 13/13 = 100.0 % |
| Seed-VC (never trained on) | 0.890 | 22/50 = 44.0 % | 13/50 = 26.0 % | 50/50 = 100.0 % | 47/50 = 94.0 % | 27/50 = 54.0 % |
| XTTS-v2 | 0.845 | 26/26 = 100.0 % | 22/26 = 84.6 % | 26/26 = 100.0 % | 24/26 = 92.3 % | 26/26 = 100.0 % |
| **All clones** (95 % CI) | – | 86/171 = 50.3 % (42–58 %) | 67/171 = 39.2 % (32–47 %) | 170/171 = 99.4 % (96–100 %) | 125/171 = 73.1 % (65–80 %) | 100/171 = 58.5 % (50–66 %) |
| **Genuine flagged** (95 % CI) | 0.936 (ceiling) | 43/79 = 54.4 % (43–65 %) | 30/79 = 38.0 % (28–49 %) | 58/79 = 73.4 % (62–82 %) | 76/79 = 96.2 % (89–99 %) | 43/79 = 54.4 % (43–65 %) |

**Real phone calls**, pre-registered test clips, the benchmark's own scoring (510 clips, 3.16 windows per clip on average):

| Cloner | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|
| Sarvam instant cloning (never trained on) | 0/12 = 0.0 % | 0/12 = 0.0 % | 11/12 = 91.7 % | 0/12 = 0.0 % | 0/12 = 0.0 % |
| F5-TTS | 14/48 = 29.2 % | 24/48 = 50.0 % | 20/48 = 41.7 % | 41/48 = 85.4 % | 16/48 = 33.3 % |
| CosyVoice2 | 8/32 = 25.0 % | 23/32 = 71.9 % | 10/32 = 31.2 % | 27/32 = 84.4 % | 13/32 = 40.6 % |
| Chatterbox (never trained on) | 14/39 = 35.9 % | 24/39 = 61.5 % | 13/39 = 33.3 % | 36/39 = 92.3 % | 19/39 = 48.7 % |
| F5-TTS Hindi | 17/36 = 47.2 % | 32/36 = 88.9 % | 9/36 = 25.0 % | 26/36 = 72.2 % | 21/36 = 58.3 % |
| Seed-VC (never trained on) | 14/35 = 40.0 % | 21/35 = 60.0 % | 15/35 = 42.9 % | 28/35 = 80.0 % | 15/35 = 42.9 % |
| XTTS-v2 | 28/52 = 53.8 % | 46/52 = 88.5 % | 44/52 = 84.6 % | 43/52 = 82.7 % | 43/52 = 82.7 % |
| **All clones** (95 % CI) | 95/254 = 37.4 % (31–44 %) | 170/254 = 66.9 % (60–73 %) | 122/254 = 48.0 % (41–55 %) | 201/254 = 79.1 % (73–84 %) | 127/254 = 50.0 % (43–57 %) |
| **Genuine flagged** (95 % CI) | 24/256 = 9.4 % (6–14 %) | 13/256 = 5.1 % (2–9 %) | 146/256 = 57.0 % (50–63 %) | 189/256 = 73.8 % (68–79 %) | 12/256 = 4.7 % (2–9 %) |

Real calls, handset D1 only:

| Cloner | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|
| F5-TTS | 5/26 = 19.2 % | 10/26 = 38.5 % | 15/26 = 57.7 % | 25/26 = 96.2 % | 7/26 = 26.9 % |
| CosyVoice2 | 5/16 = 31.2 % | 11/16 = 68.8 % | 9/16 = 56.2 % | 16/16 = 100.0 % | 7/16 = 43.8 % |
| Chatterbox (never trained on) | 1/14 = 7.1 % | 5/14 = 35.7 % | 8/14 = 57.1 % | 14/14 = 100.0 % | 4/14 = 28.6 % |
| F5-TTS Hindi | 10/17 = 58.8 % | 14/17 = 82.4 % | 7/17 = 41.2 % | 17/17 = 100.0 % | 11/17 = 64.7 % |
| Seed-VC (never trained on) | 7/13 = 53.8 % | 8/13 = 61.5 % | 9/13 = 69.2 % | 13/13 = 100.0 % | 8/13 = 61.5 % |
| XTTS-v2 | 20/32 = 62.5 % | 28/32 = 87.5 % | 27/32 = 84.4 % | 29/32 = 90.6 % | 27/32 = 84.4 % |
| **All clones** (95 % CI) | 48/118 = 40.7 % (32–50 %) | 76/118 = 64.4 % (55–73 %) | 75/118 = 63.6 % (54–72 %) | 114/118 = 96.6 % (91–99 %) | 64/118 = 54.2 % (45–63 %) |
| **Genuine flagged** (95 % CI) | 5/118 = 4.2 % (1–10 %) | 1/118 = 0.8 % (0–5 %) | 97/118 = 82.2 % (74–89 %) | 106/118 = 89.8 % (83–95 %) | 3/118 = 2.5 % (0–8 %) |

Real calls, handset D2 only:

| Cloner | v1 | A | NII | LA (off the shelf) | Fused A+NII+v1 |
|---|---|---|---|---|---|
| Sarvam instant cloning (never trained on) | 0/12 = 0.0 % | 0/12 = 0.0 % | 11/12 = 91.7 % | 0/12 = 0.0 % | 0/12 = 0.0 % |
| F5-TTS | 9/22 = 40.9 % | 14/22 = 63.6 % | 5/22 = 22.7 % | 16/22 = 72.7 % | 9/22 = 40.9 % |
| CosyVoice2 | 3/16 = 18.8 % | 12/16 = 75.0 % | 1/16 = 6.2 % | 11/16 = 68.8 % | 6/16 = 37.5 % |
| Chatterbox (never trained on) | 13/25 = 52.0 % | 19/25 = 76.0 % | 5/25 = 20.0 % | 22/25 = 88.0 % | 15/25 = 60.0 % |
| F5-TTS Hindi | 7/19 = 36.8 % | 18/19 = 94.7 % | 2/19 = 10.5 % | 9/19 = 47.4 % | 10/19 = 52.6 % |
| Seed-VC (never trained on) | 7/22 = 31.8 % | 13/22 = 59.1 % | 6/22 = 27.3 % | 15/22 = 68.2 % | 7/22 = 31.8 % |
| XTTS-v2 | 8/20 = 40.0 % | 18/20 = 90.0 % | 17/20 = 85.0 % | 14/20 = 70.0 % | 16/20 = 80.0 % |
| **All clones** (95 % CI) | 47/136 = 34.6 % (27–43 %) | 94/136 = 69.1 % (60–77 %) | 47/136 = 34.6 % (27–43 %) | 87/136 = 64.0 % (55–72 %) | 63/136 = 46.3 % (38–55 %) |
| **Genuine flagged** (95 % CI) | 19/138 = 13.8 % (8–21 %) | 12/138 = 8.7 % (5–15 %) | 49/138 = 35.5 % (28–44 %) | 83/138 = 60.1 % (51–68 %) | 9/138 = 6.5 % (3–12 %) |

Same clips, v1 and A from their **stored scores** (the pre-registered numbers' source; full precision, up to 8 windows, silence kept):

| Cloner | v1 | A |
|---|---|---|
| Sarvam instant cloning (never trained on) | 0/12 = 0.0 % | 0/12 = 0.0 % |
| F5-TTS | 17/48 = 35.4 % | 33/48 = 68.8 % |
| CosyVoice2 | 10/32 = 31.2 % | 29/32 = 90.6 % |
| Chatterbox (never trained on) | 21/39 = 53.8 % | 31/39 = 79.5 % |
| F5-TTS Hindi | 16/36 = 44.4 % | 35/36 = 97.2 % |
| Seed-VC (never trained on) | 14/35 = 40.0 % | 26/35 = 74.3 % |
| XTTS-v2 | 32/52 = 61.5 % | 50/52 = 96.2 % |
| **All clones** (95 % CI) | 110/254 = 43.3 % (37–50 %) | 204/254 = 80.3 % (74–85 %) |
| **Genuine flagged** (95 % CI) | 20/256 = 7.8 % (5–12 %) | 11/256 = 4.3 % (2–8 %) |

Stored scores, handset D1 only:

| Cloner | v1 | A |
|---|---|---|
| F5-TTS | 6/26 = 23.1 % | 15/26 = 57.7 % |
| CosyVoice2 | 5/16 = 31.2 % | 14/16 = 87.5 % |
| Chatterbox (never trained on) | 4/14 = 28.6 % | 6/14 = 42.9 % |
| F5-TTS Hindi | 12/17 = 70.6 % | 16/17 = 94.1 % |
| Seed-VC (never trained on) | 7/13 = 53.8 % | 8/13 = 61.5 % |
| XTTS-v2 | 23/32 = 71.9 % | 30/32 = 93.8 % |
| **All clones** (95 % CI) | 57/118 = 48.3 % (39–58 %) | 89/118 = 75.4 % (66–83 %) |
| **Genuine flagged** (95 % CI) | 4/118 = 3.4 % (1–9 %) | 0/118 = 0.0 % (0–4 %) |

Stored scores, handset D2 only:

| Cloner | v1 | A |
|---|---|---|
| Sarvam instant cloning (never trained on) | 0/12 = 0.0 % | 0/12 = 0.0 % |
| F5-TTS | 11/22 = 50.0 % | 18/22 = 81.8 % |
| CosyVoice2 | 5/16 = 31.2 % | 15/16 = 93.8 % |
| Chatterbox (never trained on) | 17/25 = 68.0 % | 25/25 = 100.0 % |
| F5-TTS Hindi | 4/19 = 21.1 % | 19/19 = 100.0 % |
| Seed-VC (never trained on) | 7/22 = 31.8 % | 18/22 = 81.8 % |
| XTTS-v2 | 9/20 = 45.0 % | 20/20 = 100.0 % |
| **All clones** (95 % CI) | 53/136 = 39.0 % (31–48 %) | 115/136 = 84.6 % (77–90 %) |
| **Genuine flagged** (95 % CI) | 16/138 = 11.6 % (7–19 %) | 11/138 = 8.0 % (4–14 %) |

What it means:

1. **Dropping silent windows didn't change the false flags on the corpus.** In both runs, A, NII and the fused verdict
   flag the same number of genuine clips on clean audio and through the codec. So does v1 on clean audio; only v1 on the
   codec and LA moved. On clean audio, every v1, A, NII and fused flag on genuine corpus audio is S02's: the all-speaker and
   S02-only genuine rows have the same counts. Through the codec the same holds for v1, A and the fused verdict. S02's
   genuine corpus recordings drive those rates, not silence. On real calls, v1, A and the fused verdict flag far less
   genuine speech (24, 13 and 12 of 256).
2. **On real calls, the bench's scoring catches fewer clones than the stored scores the pre-registered numbers come
   from.**
   - A: 170/254 against 204/254. v1: 95/254 against 110/254.
   - The fused verdict catches 127/254. The first run, which used the stored v1 and A scores, caught 152/254.
   - Genuine flags rise slightly: A 13 against 11 of 256.

   The two scorings differ in two ways: int8 weights against full precision, and which windows count (Silero-filtered,
   against up to 8 with silence kept). This run doesn't separate the two. Silero under-detects narrowband speakerphone
   speech (point 3 at the top), so dropping "silent" windows may be dropping speech. The pre-registered numbers stand for
   the models; the bench's serving path catches fewer of these real-call clones.
3. **The most convincing cloner is the one our models miss.** Sarvam instant cloning has the highest speaker similarity
   (0.943, above the 0.936 a real recording reaches against the same speaker's others). v1, A and the fused verdict
   catch none of it in any condition. Only NII catches it, and NII also flags a third of genuine clean audio and over
   half of genuine real-call audio at its threshold.
4. **Off-the-shelf LA flags most genuine speech** through the codec and on real calls (107/124, 189/256): unusable
   as is.

The conclusion is the same as before: the voice detector stays a shadow-mode clue (G2), and the decision rests on
verifying the person out of band.

Caveats:
- Two consenting speakers, content-matched script lines, one run, CPU int8.
- Thresholds come from the simulated sample and are applied unchanged; the codec is simulated.
- Per-cloner n is 12–110, so single rows have wide intervals. The pooled rows carry 95 % Wilson intervals, rounded
  outwards.
- The first run's JSON stays with its per-clip scores in `ml/realcall/work/bench/` (gitignored, with the audio).

## On site, 24 Oct 2026: paid-API retrain (A2, A2-ivc), single seed

**What changed** (dated protocol notes in `common/protocol.py` and `realcall/protocol.py`, written before any clip existed):
- **Training data:** paid-API stock voices, generated by `gen/run_api.py build2`.
  - Sarvam Bulbul v3: 3,000 clips. Bulbul v4 Flash: 1,500. OpenAI gpt-4o-mini-tts: 1,500. Deepgram Aura-2: 1,200.
  - Each voice reads FLEURS sentences of its own split. Voices are split by person, and every voice behind the old
    held-out commercial clips is test-only.
- **Language balance:** 2,800 FLEURS bona fide clips (400 each for bn, gu, kn, ml, mr, pa, od), so a language with
  spoofs but no bona fide speech can't become a spoof cue.
- **Sarvam IVC:** for A2-ivc only, 200 Sarvam IVC clones of S01. Sarvam IVC entered training on 24 Oct, after its 0/12
  result, so A2-ivc's Sarvam IVC results are labelled "seen cloner, unseen speaker (S02)". v1 and A keep their 0/12.
- **Recipe:** model A's, with the same weighting, so the new engines get about 22% of the synthetic spoof sampling mass.
- **Run:** `infra/retrain_v4.sh` on a g5.2xlarge, about 36 min per model. A (`ours_v3_rc`) is unchanged.

| Model | Fixed dev set EER (n = 4,025, same rows for all) | Simulated test sample EER (A's 6,000) | New engines, unseen voices: caught (6,000 = 1,200 clips × 5 channels) |
|---|---|---|---|
| A (current) | 2.86 % | 6.12 % | 91.1 % (Deepgram 60.2 %, OpenAI 99.7 %, Sarvam v3 98.0 %, v4 Flash 93.4 %) |
| A2: + paid-API stock voices | 2.29 % | 4.62 % | 95.9 % (81.1 %, 99.8 %, 99.1 %, 97.2 %) |
| A2-ivc: + S01 Sarvam clones | **2.04 %** | 4.73 % | 96.3 % (83.6 %, 100 %, 99.0 %, 97.1 %) |

**How these were measured:**
- **Threshold:** each model's own EER point on the simulated test sample, as for A's published numbers.
- **New-engine column:** this is "seen engine, unseen voices". These four engines were held-out generators until today,
  so their old test clips are no longer never-trained for A2/A2-ivc.
- **Scope:** all three columns use synthetic audio (clean plus simulated channels).

**Real phone calls, the deciding test (scored 24 Oct, 19:19).** The 510 real-call test clips (D1 + held-out handset
D2), the same set as above, were scored on the GPU for A and both candidates. A's scores match its published CPU scores
(correlation 0.99999) and reproduce its D2 numbers exactly. Each model uses its own deployed threshold.

| Held-out handset D2 (274 clips, 32 calls) | EER | AUC | Clones caught | Genuine flagged | Sarvam IVC caught, S01 / S02 |
|---|---|---|---|---|---|
| A (current) | **11.7 %** | **0.935** | 115/136 = 84.6 % (78–90 %) | 11/138 = 8.0 % (5–14 %) | 0/5 / 0/7 |
| A2 | 13.9 % | 0.923 | 110/136 = 80.9 % (73–87 %) | 10/138 = 7.2 % (4–13 %) | 0/5 / 0/7 |
| A2-ivc | 13.1 % | 0.928 | 120/136 = 88.2 % (82–93 %) | 18/138 = 13.0 % (8–20 %) | 5/5 (seen speaker and cloner) / **0/7** |

On all 510 real-call test clips (D1 + D2):
- **EER:** A 11.0 %, A2 12.5 %, A2-ivc 12.5 %.
- **Clones caught:** A 80 %, A2 73 %, A2-ivc 81 %.
- **Genuine flagged:** A 4 %, A2 4 %, A2-ivc 7 %.

What it means:
1. **Synthetic gains don't transfer.** The retrain improved every synthetic test (fixed dev 2.86 % → 2.04–2.29 %; new
   engines 91.1 % → 95.9–96.3 %), but **not real phone calls**: A stays the best on D2. The differences between models
   on real calls are within the confidence intervals, so "no improvement" is the safe reading, not "worse".
2. **Sarvam IVC training doesn't generalise to a new speaker.** A2-ivc caught the 5 Sarvam clones of S01, the speaker
   it trained on, and **none of the 7 Sarvam clones of S02**, the unseen speaker. Its extra catches on D2 are exactly
   those 5 S01 clips (non-Sarvam clones: 115/124, the same as A), and it wrongly flags 7 more genuine clips.
3. **Decision:** model A stays the served and panel model; A2 and A2-ivc are not promoted. The checkpoints stay in S3
   (`runs/ours_a2`, `runs/ours_a2_ivc`) for further work. A commercial cloner on a new person's voice still beats every
   detector we have, which is why Pehchaan never lets the voice score decide.

Reproduce: `ml/realcall/work/retrain_v4/d2cmp` (scores from S3 `work/scores_v4`, plus the labelled real-call manifest),
then `python -m realcall.compare_models --dir realcall/work/retrain_v4/d2cmp --name retrain_v4 --device D2` and
`python -m eval.compare_v4 --dir realcall/work/retrain_v4/d2cmp`.

## On site, 25 Oct 2026 (night): generalisation run v5, single seed

**What changed** (protocol note "v5" in `common/protocol.py`, written 24 Oct evening before any IndicVoices clip was
downloaded or cloned, but *after* we had seen every model miss S02's Sarvam clones, so every result here is a
follow-up to that miss, not a blind test):
- **Many speakers:** ai4bharat/IndicVoices Hindi (CC-BY-4.0), raw field recordings. 600 speakers selected from 1,591
  eligible, split by person: 438 train, 52 dev, 110 test; 1,800 target utterances (3.5 h). Each target has
  content-matched XTTS-v2 and F5-Hindi clones of the same speaker (141 clones dropped for duration, 3 not generated).
  XTTS-v2 and F5-Hindi stay seen cloners, so the IndicVoices test rows measure "seen cloner, unseen speaker".
- **Never-trained engines:** a larger MLAAD test set, 200 clips per (language, system), clean and through the AMR
  channel: 3,000 clips per condition.
- **Candidates** (model A's recipe, seed 0): **n1** = NII MMS-300M AntiDeepfake initialisation + the A2 data;
  **a3** = A's initialisation + the A2 data + IndicVoices; **n3** = NII initialisation + the A2 data + IndicVoices.
  NII-initialised weights inherit CC-BY-NC-SA-4.0 (research and education only). Sarvam IVC is never trained.
- **Run:** `infra/retrain_v5.sh` on a g5.2xlarge, 24 Oct 22:27 → 25 Oct 02:24 IST, status SUCCESS; the box stopped
  itself. Weights in S3 `runs/ours_n1`, `runs/ours_a3`, `runs/ours_n3`; scores in `work/scores_v5`.
- **Threshold:** each model's own EER point on the fixed simulated test sample (6,000 clips), as for A.

**Promotion check and real phone calls** (the 510 pre-registered real-call test clips, D1 + held-out handset D2; 95 %
Wilson intervals):

| Model | Fixed dev EER (n = 4,025) | Real-call EER | S02 EER | Genuine flagged | Clones caught | Sarvam IVC caught, S01 / S02 |
|---|---|---|---|---|---|---|
| A (current) | 2.86 % | 11.0 % | 13.5 % | 11/256 = 4.3 % (2.4–7.5 %) | 204/254 = 80.3 % (75.0–84.7 %) | 0/5 / 0/7 |
| NII zero-shot | 17.99 % | 51.2 % | 55.6 % | 144/256 = 56.3 % (50.1–62.2 %) | 133/254 = 52.4 % (46.2–58.4 %) | 5/5 / 5/7 |
| n1: NII init | 1.29 % | 11.4 % | 16.1 % | 9/256 = 3.5 % (1.9–6.5 %) | 186/254 = 73.2 % (67.5–78.3 %) | 0/5 / 0/7 |
| a3: + IndicVoices | 2.68 % | 10.6 % | 12.2 % | 9/256 = 3.5 % (1.9–6.5 %) | 203/254 = 79.9 % (74.6–84.4 %) | 0/5 / 0/7 |
| **n3: NII init + IndicVoices** | 2.04 % | **7.8 %** | **10.3 %** | **3/256 = 1.2 % (0.4–3.4 %)** | 190/254 = 74.8 % (69.1–79.7 %) | 0/5 / 0/7 |

**Generalisation tests** (synthetic and clean audio; A was not scored on these sets in this run):

| Model | Unseen IndicVoices speakers (110), EER over 5 channels | … genuine flagged | MLAAD clean: caught (AUC) | MLAAD AMR: caught (AUC) | Paid-API unseen voices caught | Clean bench, Sarvam IVC: S01 AUC, caught / S02 AUC, caught |
|---|---|---|---|---|---|---|
| A (current) | – | – | – | – | 5,465/6,000 = 91.1 % | – |
| NII zero-shot | 11.8 % | 376/1,650 | 2,742/3,000 = 91.4 % (0.977) | 2,859/3,000 = 95.3 % (0.950) | 4,892/6,000 = 81.5 % | 1.000, 41/41 / 0.743, 30/30 |
| n1 | 5.3 % | 49/1,650 | 2,839/3,000 = 94.6 % (0.997) | 2,830/3,000 = 94.3 % (0.992) | 5,764/6,000 = 96.1 % | 1.000, 24/41 / 0.531, 18/30 |
| a3 | 7.5 % | 40/1,650 | 2,357/3,000 = 78.6 % (0.985) | 2,370/3,000 = 79.0 % (0.983) | 5,692/6,000 = 94.9 % | 0.989, 0/41 / 0.397, 0/30 |
| n3 | **2.2 %** | **10/1,650** | 2,718/3,000 = 90.6 % (**0.999**) | 2,672/3,000 = 89.1 % (0.995) | 5,699/6,000 = 95.0 % | 1.000, 34/41 / 0.724, 12/30 |

MLAAD AUCs are against unseen IndicVoices genuine speech on the same channel. After the AMR channel, n3 catches
2/41 (S01) and 1/30 (S02) Sarvam clones on the bench. Direct microphone recordings of S01 and S02 are flagged 0/80 by
n1, a3 and n3; S02's network-side dialer recordings are flagged 18/44 by n3.

What it means:
1. **Promotion check:** all three candidates beat A on the fixed dev set (n1 1.29 %, n3 2.04 %, a3 2.68 %, A 2.86 %).
   The pre-registered rule says a candidate replaces A only if it beats A on dev; it does not say how to choose
   between several that do. By dev alone, n1 is the lowest.
2. **Real calls:** n3 is the first model to improve on A on real phone calls: EER 7.8 % against 11.0 %, and it
   flags 3 genuine clips where A flags 11 (intervals 0.4–3.4 % and 2.4–7.5 %, which overlap slightly). At its
   threshold it catches fewer clones (74.8 % against 80.3 %; intervals overlap). Neither the backbone alone (n1) nor
   the extra speakers alone (a3) improves on A; the combination does. Caveat: four models (three candidates and NII
   zero-shot) were compared on the same test set, so the best of them is an optimistic pick; single seed.
3. **Sarvam IVC on an unseen speaker still beats every fine-tuned model over the phone:** 0/12 on real calls for
   A, n1, a3 and n3. On clean audio n3 separates S02's Sarvam clones better than n1 or a3 (AUC 0.724) but catches
   12/30 at its threshold, and 1/30 after AMR. NII zero-shot catches them only while flagging 56 % of genuine calls.
4. **Unseen speakers:** n3 reaches 2.2 % EER on 110 IndicVoices speakers it never heard (seen cloners), flagging
   10 of 1,650 genuine clips.
5. **Decision (25 Oct, 02:50 IST, Varun): n3 is the reference detector**, the model we quote and show in the laptop
   detector bench, with the selection caveat above (dated note in `common/protocol.py`). Voice stays in shadow mode
   (the live-caller gate is not run), the deployed server keeps v1, and n3 inherits CC-BY-NC-SA-4.0 (research and
   education only).

Reproduce: `aws s3 sync s3://pehchaan-ml-301745146083-use1/work/scores_v5 ml/realcall/work/retrain_v5/scores` and
`aws s3 cp s3://pehchaan-ml-301745146083-use1/work/manifests/iv_test.csv ml/realcall/work/retrain_v5/scores/`, then
`cd ml && python -m eval.compare_v5` (writes `realcall/work/reports/retrain_v5.json`, the source of every number above).
