# Pehchaan voice-clone detector: results

All numbers are on held-out TEST data; calibration and band thresholds were fitted on DEV only.
FAR = clones accepted as real; FRR = real people flagged. EER in %. Channels are simulated unless marked real.

## Headline (all test clips, 5 channels pooled, one global threshold)

| Detector | EER | AUC | FRR @ FAR 5 % | FRR @ FAR 1 % | EER seen gens | EER held-out gens | ECE (test) |
|---|---|---|---|---|---|---|---|
| XLS-R+AASIST LA (off-the-shelf) | 34.3 | 0.715 | 79.7 | 97.7 | 36.8 | 32.6 | 0.124 |
| XLS-R+AASIST DF (off-the-shelf) | 39.8 | 0.652 | 84.5 | 97.0 | 43.6 | 37.1 | 0.156 |
| NII MMS-300M AntiDeepfake (off-the-shelf, NC) | 15.1 | 0.924 | 49.0 | 89.5 | 16.7 | 13.9 | 0.061 |
| Pehchaan fine-tuned XLS-R+AASIST | 4.8 | 0.989 | 4.6 | 18.1 | 2.7 | 6.0 | 0.048 |
| Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure) | 5.8 | 0.985 | 6.5 | 28.3 | 4.0 | 6.8 | 0.052 |
| Pehchaan v0 ablation (no team-speaker audio in training) | 7.3 | 0.976 | 15.7 | 52.8 | 4.9 | 8.9 | 0.066 |

## Key findings

1. **Off-the-shelf detectors collapse on Indian-language phone-channel clones.** XLS-R+AASIST LA: 0.3 % EER in-domain (ASVspoof 2019 LA) -> 34.3 % here; DF: 0.2 % -> 39.8 %. The strongest public model (NII, non-commercial) reaches 15.1 % but 30.7 % on speaker->mic replay.
2. **Fine-tuned: 4.8 % EER** (AUC 0.989, FRR 4.6 % at FAR 5 %). Seen generators 2.7 % vs held-out 6.0 % (2.2x gap). Best channel clean 3.1 %, worst replay 7.5 %. Hardest cells: deepgram on replay 18.5 %, parler on replay 16.0 %, seedvc on amr 13.5 %.
3. **Band LRs** (p >= 0.80 likely_synthetic, p <= 0.20 no_strong_evidence): held-out generators 56.9 / 3.51 / 0.094; phone channels + held-out generators 70.5 / 2.91 / 0.093.

## Honest failures and limits (why voice stays supporting evidence, SPEC G2/G3)

- **A real cellular call breaks every detector.** Genuine speech from one real S02-S01 call (dialer recording, 8 kHz): real_cellular 91.3 % of 23 chunks flagged, real_cellular_m4a 95.2 % of 21 chunks flagged by ours (NII: 95.7 %, 100.0 %). Simulated channels on the same speakers flag 0-2 % (replay ~9 %). Against real-call bona fide, LR(likely_synthetic) = 0.93 (no information). One call, two speakers: real networks do something our simulated codecs do not (adaptive AMR/EVS, network noise suppression/AGC, recorder app).
- A v2 model with extra telephony augmentation (designed after seeing the real-call failure; stopped at epoch 3/6 by a CUDA OOM) did not fix it (91.3 %, 95.2 % flagged) and is worse overall (5.8 % EER), so v1 is served.
- **A new real voice is harder than a new generator.** Team clones on simulated channels: S01 (trained speaker, unseen lines) 6.8 % EER, **held-out speaker S02 16.6 %** (NII: 10.3 %); Seed-VC clones of S02 25.2 %.
- Ablation without team audio (v0): 7.3 % EER overall, S02 27.0 %.
- Only two consented team speakers; gender not recorded for them. Telugu team audio exists only for S01 (Seed-VC Telugu clones).
- All channels except the one real call are simulated (G.711, AMR-NB 12.2k, Opus 16-24k + loss, loudspeaker->mic with synthetic RIRs).
- Shortcut risk: XTTS and F5-Hindi emit exact digital silence between words (see spectrograms); silence trimming and level normalisation are identical for real and fake, but inner gaps remain.
- Whisper QC (drop clones with CER > 0.5) covered hi/en dev/test and held-out clips only; te/ta clones were not QC'd.
- Calibration: ECE dev 0.003, seen test 0.011, held-out test 0.049; the test EER threshold sits far below the dev one (unseen material looks 'less synthetic').
- Non-commercial (NC) items: NII baseline weights (CC BY-NC-SA), IndicSynth spoofs, and the F5-TTS / XTTS-v2 / MMS-TTS generators; the SSL-AASIST init checkpoint has no stated weight licence (see DATA_CARD.md). IndicF5 and MLAAD audio stayed gated (403) and were not used.
- No A100/H100 ran (SageMaker p4d never got capacity; stopped unbilled), so one seed only and no multi-seed/ablation sweep.

Figures: `figures/det_baseline_vs_ours.svg`, `figures/eer_heatmap_generator_channel.svg`, `figures/heldout_gap_bars.svg` (PNG previews alongside), `figures/spectrogram_speakerA_*.png` (team speaker anonymised as Speaker A).


## EER by channel

| Detector | clean | pstn | amr | opus | replay |
|---|---|---|---|---|---|
| XLS-R+AASIST LA (off-the-shelf) | 27.1 | 29.1 | 32.6 | 28.9 | 37.9 |
| XLS-R+AASIST DF (off-the-shelf) | 25.4 | 36.7 | 40.2 | 34.9 | 46.8 |
| NII MMS-300M AntiDeepfake (off-the-shelf, NC) | 1.1 | 3.4 | 6.3 | 2.8 | 30.7 |
| Pehchaan fine-tuned XLS-R+AASIST | 3.1 | 4.1 | 4.6 | 3.4 | 7.5 |
| Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure) | 3.9 | 4.8 | 5.5 | 4.5 | 8.3 |
| Pehchaan v0 ablation (no team-speaker audio in training) | 5.0 | 7.1 | 8.3 | 5.5 | 9.8 |

## Held-out generators by channel (EER)

| Detector | clean | pstn | amr | opus | replay |
|---|---|---|---|---|---|
| XLS-R+AASIST LA (off-the-shelf) | 24.9 | 26.1 | 29.8 | 26.7 | 38.1 |
| XLS-R+AASIST DF (off-the-shelf) | 22.1 | 31.8 | 35.9 | 31.7 | 46.5 |
| NII MMS-300M AntiDeepfake (off-the-shelf, NC) | 0.6 | 2.6 | 5.3 | 2.2 | 27.2 |
| Pehchaan fine-tuned XLS-R+AASIST | 4.0 | 5.1 | 5.5 | 4.1 | 9.5 |
| Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure) | 4.7 | 5.9 | 6.6 | 5.3 | 9.8 |
| Pehchaan v0 ablation (no team-speaker audio in training) | 6.1 | 8.4 | 9.7 | 6.6 | 12.2 |

## Generator x channel EER: Pehchaan fine-tuned XLS-R+AASIST

| Generator | clean | pstn | amr | opus | replay |
|---|---|---|---|---|---|
| chatterbox | 2.9 | 6.2 | 9.2 | 4.1 | 6.6 |
| cosyvoice2 | 3.7 | 5.3 | 8.4 | 4.0 | 5.3 |
| deepgram | 8.1 | 9.2 | 9.1 | 7.7 | 18.5 |
| f5 | 4.0 | 2.7 | 4.8 | 4.0 | 5.3 |
| f5hi | 0.1 | 1.1 | 2.7 | 1.5 | 6.6 |
| indicsynth_freevc24 | 0.2 | 1.0 | 1.3 | 0.6 | 5.8 |
| kokoro | 0.1 | 1.6 | 1.9 | 0.4 | 5.8 |
| mms | 0.1 | 1.0 | 1.0 | 0.0 | 2.2 |
| openai | 0.3 | 0.6 | 1.2 | 0.3 | 3.2 |
| parler | 4.4 | 4.4 | 4.6 | 4.4 | 16.0 |
| sarvam | 0.5 | 2.8 | 3.3 | 1.4 | 7.7 |
| seedvc | 5.5 | 9.0 | 13.5 | 6.7 | 10.5 |
| xtts | 0.3 | 0.9 | 2.6 | 0.7 | 2.1 |

## Generator x channel EER: XLS-R+AASIST LA (off-the-shelf)

| Generator | clean | pstn | amr | opus | replay |
|---|---|---|---|---|---|
| chatterbox | 30.3 | 37.6 | 43.6 | 33.8 | 45.9 |
| cosyvoice2 | 34.1 | 40.1 | 47.4 | 43.4 | 40.8 |
| deepgram | 44.9 | 46.7 | 47.7 | 46.2 | 47.4 |
| f5 | 25.3 | 26.8 | 31.3 | 28.0 | 37.3 |
| f5hi | 13.1 | 17.1 | 23.7 | 19.1 | 32.1 |
| indicsynth_freevc24 | 52.2 | 54.9 | 57.6 | 50.4 | 49.1 |
| kokoro | 30.0 | 31.7 | 36.9 | 35.8 | 43.9 |
| mms | 12.5 | 21.0 | 26.2 | 20.4 | 27.6 |
| openai | 33.5 | 32.8 | 35.3 | 33.7 | 39.7 |
| parler | 20.9 | 22.5 | 23.8 | 25.0 | 37.8 |
| sarvam | 14.2 | 17.1 | 21.4 | 18.5 | 34.0 |
| seedvc | 9.7 | 12.2 | 18.1 | 17.6 | 32.2 |
| xtts | 16.3 | 21.4 | 22.5 | 19.7 | 34.5 |

## By language (EER)

- XLS-R+AASIST LA (off-the-shelf): en 31.5, hi 36.6, ta 30.6, te 44.4
- XLS-R+AASIST DF (off-the-shelf): en 39.2, hi 39.6, ta 35.4, te 50.2
- NII MMS-300M AntiDeepfake (off-the-shelf, NC): en 17.1, hi 13.3, ta 13.2, te 16.9
- Pehchaan fine-tuned XLS-R+AASIST: en 6.6, hi 3.1, ta 1.5, te 6.7
- Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure): en 6.8, hi 4.4, ta 1.4, te 8.3
- Pehchaan v0 ablation (no team-speaker audio in training): en 10.6, hi 6.7, ta 0.9, te 4.6

## Team speakers (consented; S02 held out) and real phone calls

- XLS-R+AASIST LA (off-the-shelf): team EER incl. real-call bona fide 46.3 (n_spoof 1115, n_bona 309); seen gens 48.5, held-out gens 46.0
  - simulated channels only: EER 43.0 (n_spoof 1115, n_bona 265); held-out gens 41.9; per generator chatterbox 60.0, cosyvoice2 83.0, f5 55.9, f5hi 23.5, seedvc 34.8, xtts 37.1
  - S01 (seen speaker, unseen lines): EER 32.2 (n_spoof 440, n_bona 90); held-out gens 31.4; per generator chatterbox 48.3, cosyvoice2 66.7, f5 40.0, f5hi 20.0, seedvc 20.4, xtts 32.2
  - S02 (held-out speaker): EER 49.1 (n_spoof 675, n_bona 175); held-out gens 49.0; per generator chatterbox 63.2, cosyvoice2 87.7, f5 60.6, f5hi 27.7, seedvc 43.0, xtts 43.2
  - real calls (bona fide only), share flagged at the dev EER threshold: real_cellular 100.0 % of 23, real_cellular_m4a 100.0 % of 21
- XLS-R+AASIST DF (off-the-shelf): team EER incl. real-call bona fide 45.6 (n_spoof 1115, n_bona 309); seen gens 52.4, held-out gens 43.0
  - simulated channels only: EER 43.0 (n_spoof 1115, n_bona 265); held-out gens 39.6; per generator chatterbox 61.6, cosyvoice2 67.0, f5 67.2, f5hi 35.6, seedvc 30.9, xtts 37.4
  - S01 (seen speaker, unseen lines): EER 34.3 (n_spoof 440, n_bona 90); held-out gens 33.3; per generator chatterbox 56.7, cosyvoice2 60.0, f5 50.0, f5hi 40.0, seedvc 23.3, xtts 20.0
  - S02 (held-out speaker): EER 48.1 (n_spoof 675, n_bona 175); held-out gens 44.0; per generator chatterbox 65.1, cosyvoice2 70.9, f5 70.9, f5hi 35.7, seedvc 37.1, xtts 40.3
  - real calls (bona fide only), share flagged at the dev EER threshold: real_cellular 100.0 % of 23, real_cellular_m4a 100.0 % of 21
- NII MMS-300M AntiDeepfake (off-the-shelf, NC): team EER incl. real-call bona fide 15.9 (n_spoof 1115, n_bona 309); seen gens 18.4, held-out gens 14.6
  - simulated channels only: EER 10.6 (n_spoof 1115, n_bona 265); held-out gens 8.9; per generator chatterbox 12.2, cosyvoice2 18.8, f5 17.3, f5hi 10.6, seedvc 7.5, xtts 7.1
  - S01 (seen speaker, unseen lines): EER 11.1 (n_spoof 440, n_bona 90); held-out gens 10.7; per generator chatterbox 12.5, cosyvoice2 26.7, f5 18.9, f5hi 11.1, seedvc 10.0, xtts 5.6
  - S02 (held-out speaker): EER 10.3 (n_spoof 675, n_bona 175); held-out gens 7.6; per generator chatterbox 12.0, cosyvoice2 16.9, f5 18.3, f5hi 10.8, seedvc 5.7, xtts 6.4
  - real calls (bona fide only), share flagged at the dev EER threshold: real_cellular 95.7 % of 23, real_cellular_m4a 100.0 % of 21
- Pehchaan fine-tuned XLS-R+AASIST: team EER incl. real-call bona fide 20.1 (n_spoof 1115, n_bona 309); seen gens 17.8, held-out gens 20.7
  - simulated channels only: EER 13.1 (n_spoof 1115, n_bona 265); held-out gens 15.1; per generator chatterbox 9.4, cosyvoice2 13.6, f5 13.6, f5hi 6.0, seedvc 17.4, xtts 3.6
  - S01 (seen speaker, unseen lines): EER 6.8 (n_spoof 440, n_bona 90); held-out gens 7.8; per generator chatterbox 3.3, cosyvoice2 2.2, f5 0.0, f5hi 0.0, seedvc 8.7, xtts 0.0
  - S02 (held-out speaker): EER 16.6 (n_spoof 675, n_bona 175); held-out gens 21.1; per generator chatterbox 14.4, cosyvoice2 16.6, f5 16.6, f5hi 7.4, seedvc 25.2, xtts 4.0
  - real calls (bona fide only), share flagged at the dev EER threshold: real_cellular 91.3 % of 23, real_cellular_m4a 95.2 % of 21
- Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure): team EER incl. real-call bona fide 18.6 (n_spoof 1115, n_bona 309); seen gens 17.1, held-out gens 20.4
  - simulated channels only: EER 12.8 (n_spoof 1115, n_bona 265); held-out gens 14.7; per generator chatterbox 8.3, cosyvoice2 17.7, f5 9.3, f5hi 6.2, seedvc 17.6, xtts 3.6
  - S01 (seen speaker, unseen lines): EER 7.7 (n_spoof 440, n_bona 90); held-out gens 7.8; per generator chatterbox 3.3, cosyvoice2 0.0, f5 0.0, f5hi 1.1, seedvc 10.0, xtts 1.1
  - S02 (held-out speaker): EER 16.6 (n_spoof 675, n_bona 175); held-out gens 21.7; per generator chatterbox 12.8, cosyvoice2 20.0, f5 10.8, f5hi 7.7, seedvc 25.7, xtts 4.0
  - real calls (bona fide only), share flagged at the dev EER threshold: real_cellular 91.3 % of 23, real_cellular_m4a 95.2 % of 21
- Pehchaan v0 ablation (no team-speaker audio in training): team EER incl. real-call bona fide 31.9 (n_spoof 1115, n_bona 309); seen gens 29.8, held-out gens 33.1
  - simulated channels only: EER 26.1 (n_spoof 1115, n_bona 265); held-out gens 27.6; per generator chatterbox 28.3, cosyvoice2 41.2, f5 28.3, f5hi 18.1, seedvc 27.2, xtts 9.4
  - S01 (seen speaker, unseen lines): EER 21.6 (n_spoof 440, n_bona 90); held-out gens 22.1; per generator chatterbox 22.5, cosyvoice2 33.3, f5 16.7, f5hi 13.3, seedvc 21.1, xtts 6.7
  - S02 (held-out speaker): EER 27.0 (n_spoof 675, n_bona 175); held-out gens 28.0; per generator chatterbox 28.6, cosyvoice2 43.1, f5 33.1, f5hi 18.5, seedvc 27.4, xtts 10.4
  - real calls (bona fide only), share flagged at the dev EER threshold: real_cellular 73.9 % of 23, real_cellular_m4a 90.5 % of 21

## Bands and measured likelihood ratios (Pehchaan detector)

Thresholds from dev: `no_strong_evidence` if p <= 0.200; `likely_synthetic` if p >= 0.800; otherwise `inconclusive`.
LR = P(band | clone) / P(band | real), on test, with 95 % bootstrap CI.

| Test slice | likely_synthetic | inconclusive | no_strong_evidence |
|---|---|---|---|
| test_all (n_spoof 11265, n_bona 7809) | 60.22 [50.87-73.40] | 2.63 [2.22-3.14] | 0.06 [0.06-0.07] |
| test_seen_generators (n_spoof 4765, n_bona 7809) | 64.80 [54.37-79.95] | 1.43 [1.17-1.80] | 0.02 [0.02-0.02] |
| test_heldout_generators (n_spoof 6500, n_bona 7809) | 56.86 [48.61-69.87] | 3.51 [2.99-4.22] | 0.09 [0.09-0.10] |
| test_phone_channels (n_spoof 9012, n_bona 6212) | 74.57 [61.72-93.53] | 2.21 [1.86-2.64] | 0.06 [0.06-0.07] |
| test_phone_channels_heldout_generators (n_spoof 5200, n_bona 6212) | 70.51 [58.56-89.59] | 2.91 [2.45-3.49] | 0.09 [0.09-0.10] |
| real_call_stress_heldout_clones_vs_real_call_bonafide (n_spoof 5200, n_bona 44) | 0.93 [0.85-1.02] | 1.37 [0.60-7.00] | 1.62 [0.71-8.47] |

FRR at the dev EER threshold (fairness slices):

- by_lang: bn 0.8 % (n=500), en 1.1 % (n=1350), gu 1.6 % (n=500), hi 2.4 % (n=1350), kn 0.0 % (n=500), mixed 46.1 % (n=89), ml 0.0 % (n=500), mr 0.4 % (n=500), ta 0.1 % (n=1250), te 5.9 % (n=1270)
- by_gender: female 0.4 % (n=3495), male 2.9 % (n=4005), mixed 93.2 % (n=44), unknown 2.6 % (n=265)
- by_source: fleurs 1.7 % (n=7500), team 15.5 % (n=309)

Band shares on test (fraction of clips in each band):

- spoof: likely_synthetic 88.3 %, no_strong_evidence 6.0 %, inconclusive 5.7 %
- bonafide: no_strong_evidence 96.4 %, inconclusive 2.1 %, likely_synthetic 1.5 %
- real_call_bonafide: likely_synthetic 90.9 %, no_strong_evidence 4.5 %, inconclusive 4.5 %

## In-domain sanity check (ASVspoof 2019 LA eval subset, English studio audio)

- XLS-R+AASIST LA (off-the-shelf): EER 0.3, AUC 1.000
- XLS-R+AASIST DF (off-the-shelf): EER 0.2, AUC 1.000
- NII MMS-300M AntiDeepfake (off-the-shelf, NC): EER 2.5, AUC 0.998
- Pehchaan fine-tuned XLS-R+AASIST: EER 1.3, AUC 0.998
- Pehchaan v2 (+ extra telephony augmentation; designed after seeing the real-call failure): EER 1.0, AUC 0.999

## Latency (10 s clip)

| Where | Device | What | median ms | p95 ms |
|---|---|---|---|---|
| EC2 g5.2xlarge, A10G, fp16, model only | NVIDIA A10G | model_forward_10s | 32.3 | 32.4 |
| EC2 g5.2xlarge CPU (8 vCPU), fp32, model only | x86_64 | model_forward_10s | 2626.1 | 2649.9 |
| laptop CPU (AMD Ryzen, 8 threads), int8 dynamic quant, full service path | AMD64 Family 25 Model 117 Stepping 2, AuthenticAMD | service_10s | 983.5 | 1026.3 |
| laptop RTX 4070 Laptop GPU, fp32 weights, full service path (VAD+SNR+watermark+model) | NVIDIA GeForce RTX 4070 Laptop GPU | service_10s | 338.8 | 357.0 |

## Perth watermark check (Chatterbox output)

```json
{
 "note": "Perth implicit watermark (resemble-perth); detection = get_watermark() >= 0.5",
 "chatterbox": {
  "amr": {
   "n": 57,
   "detected_rate": 0.2982,
   "mean_conf": 0.2982
  },
  "clean": {
   "n": 57,
   "detected_rate": 1.0,
   "mean_conf": 1.0
  },
  "opus": {
   "n": 57,
   "detected_rate": 1.0,
   "mean_conf": 1.0
  },
  "pstn": {
   "n": 57,
   "detected_rate": 1.0,
   "mean_conf": 1.0
  },
  "replay": {
   "n": 57,
   "detected_rate": 0.8772,
   "mean_conf": 0.8772
  }
 },
 "non_chatterbox": {
  "amr": {
   "n": 150,
   "detected_rate": 0.0,
   "mean_conf": 0.0
  },
  "clean": {
   "n": 150,
   "detected_rate": 0.0,
   "mean_conf": 0.0
  },
  "opus": {
   "n": 150,
   "detected_rate": 0.0067,
   "mean_conf": 0.0067
  },
  "pstn": {
   "n": 150,
   "detected_rate": 0.0,
   "mean_conf": 0.0
  },
  "replay": {
   "n": 150,
   "detected_rate": 0.0667,
   "mean_conf": 0.0667
  }
 }
}
```
