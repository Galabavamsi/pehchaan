# ML status (Pehchaan voice provenance)

> **Record: Round 1 ML status, 6 Oct 2026.** Later detector results are in `ml/realcall/FINDINGS.md`.

Last updated: 2026-10-06 06:25 IST. **Round-1 ML work is complete; the GPU instance is STOPPED (not terminated).**

## BLOCKERS (need the user)

1. **HF gated audio still 403 for IndicF5 and MLAAD (checked 05:40 IST from the laptop).** `ai4bharat/IndicF5` -> GatedRepoError; `mueller91/MLAAD` README downloads but every `fake/*/*.wav` returns GatedRepoError (so the token can list but not read). `ai4bharat/indic-parler-tts` works and is used as an extra held-out generator. Script ready for when MLAAD opens: `data_prep/fetch_mlaad.py` (15 Indic MLAAD systems incl. IndicF5 outputs, test-only).
2. **Keys stay on the laptop.** Copying `.env` (HF token / API keys) to the EC2 box was not allowed: keys never leave the laptop. So commercial TTS (Sarvam, OpenAI, Deepgram) runs **from the laptop** and only the audio is uploaded; gated HF files would be downloaded on the laptop and uploaded as files. If you want the GPU box/SageMaker to use the keys directly, you would have to allow it explicitly; not needed for Round 1.
3. **GPU capacity:** EC2 p4d / p4de / p5.4xlarge / g6e.2xlarge had no capacity in us-east-1 (all AZs) at 00:20 IST. Running on **g5.2xlarge (1x A10G 24 GB)**. SageMaker training in ap-southeast-1 (ml.p4d.24xlarge quota 1) is set up as the heavy-batch option.
4. Gemini dropped (no key). SageMaker p4d job never got capacity (pending 04:11-06:00 IST) and was stopped unbilled ($0), so there are no A100 numbers and no multi-seed sweep.

## FINAL RESULTS (06:20 IST) - see `results/SUMMARY.md`, `results/metrics.json`, `results/figures/`

Test: 7,809 bona fide / 11,265 spoof clips (5 simulated channels + 44 real-call chunks), 13 generators (6 held out:
Seed-VC, Chatterbox, Sarvam, OpenAI, Deepgram, Indic Parler-TTS), held-out speaker S02. One global threshold.

| Detector | EER all | seen gens | held-out gens | AUC | FRR @ FAR 5 % | ECE |
|---|---|---|---|---|---|---|
| XLS-R+AASIST LA, off-the-shelf (0.27 % in-domain) | 34.3 % | 36.8 % | 32.6 % | 0.715 | 79.7 % | 0.124 |
| XLS-R+AASIST DF, off-the-shelf (0.20 % in-domain) | 39.8 % | 43.6 % | 37.1 % | 0.652 | 84.5 % | 0.156 |
| NII MMS-300M AntiDeepfake (NC) | 15.1 % | 16.7 % | 13.9 % | 0.924 | 49.0 % | 0.061 |
| **Pehchaan v1 (served)** | **4.8 %** | **2.7 %** | **6.0 %** | 0.989 | 4.6 % | 0.048 |
| Pehchaan v2 telephony-aug (post-hoc, OOM at ep 3/6) | 5.8 % | 4.0 % | 6.8 % | 0.985 | 6.5 % | 0.052 |
| Pehchaan v0 (no team audio) | 7.3 % | 4.9 % | 8.9 % | 0.976 | 15.7 % | 0.066 |

- Ours by channel: clean 3.1, Opus 3.4, PSTN 4.1, AMR-NB 4.6, replay 7.5. Hardest: Deepgram/replay 18.5, Parler/replay 16.0, Seed-VC/AMR 13.5.
- Band LRs (p>=0.8 / between / p<=0.2): held-out generators 56.9 / 3.51 / 0.094; phone + held-out 70.5 / 2.91 / 0.093.
- **Real cellular call: 91 % (wav) / 95 % (m4a) of genuine chunks flagged (NII 96-100 %, XLS-R 100 %); LR(likely_synthetic) = 0.93.** v2 did not fix it.
- **Held-out speaker S02 (team clones, simulated channels): ours 16.6 % EER vs NII 10.3 %**; S01 6.8 %.
- Latency (10 s): A10G fp16 model 32 ms; g5 CPU fp32 model 2.6 s; laptop service path CPU int8 0.98 s, RTX 4070 339 ms.
- Perth watermark: 100 % clean/PSTN/Opus, 88 % replay, 30 % AMR-NB; FP 0-0.7 % (6.7 % replay).
- Serving: `serve/` runs on CPU and GPU with v1 weights (`serve/weights/`, gitignored; S3 `models/pehchaan-xlsr-aasist-ft-v1/`).
- Spectrogram fix: train-split lines previously fell back to clean audio in the "amr" panel; now the channel is applied.

## AWS resources I created (all tagged Project=pehchaan)

| Resource | ID |
|---|---|
| Key pair (us-east-1) | `pehchaan-ml` (key-088fe7c1862ab164d); private key `ml/infra/pehchaan-ml` (gitignored) |
| Security group | `sg-023ef8c13605cbc8b` `pehchaan-ml-ssh`, SSH 22 from 103.147.138.252/32 only |
| S3 bucket us-east-1 | `pehchaan-ml-301745146083-use1` (private, BPA on, SSE-S3, versioning) |
| S3 bucket ap-southeast-1 | `pehchaan-ml-301745146083-apse1` (private, BPA on, SSE-S3, versioning) - SageMaker job I/O |
| IAM role / instance profile | `pehchaan-ml-ec2` (S3 access to the two pehchaan buckets only) |
| IAM role | `pehchaan-sagemaker-exec` (two pehchaan buckets + ECR pull + CloudWatch Logs) |
| Launch template | `lt-075d93f2e06074c0b` `pehchaan-ml` (DLAMI PyTorch 2.7 Ubuntu 22.04, 600 GB gp3 encrypted, IMDSv2 required, shutdown=stop, idle watchdog in user-data) |
| Instance | `i-06da2349859b52482` g5.2xlarge us-east-1b, IP 52.91.206.100 |

## Instance / job log and cost

| Resource | Type | $/h | Start (IST) | Stop (IST) | Hours | Est. cost |
|---|---|---|---|---|---|---|
| i-06da2349859b52482 | g5.2xlarge | 1.212 | 2026-10-06 00:23 | 2026-10-06 06:22 (stopped, not terminated) | 5.98 | $7.25 |
| SageMaker `pehchaan-ft-v1-1005-2241` (ap-southeast-1) | ml.p4d.24xlarge training, 8 runs in parallel (main, 2 extra seeds, no-channel-aug, no-RawBoost, init-DF, no-team, high-LR) + A100 latency; MaxRuntime 4 h, no warm pool | ~37-41 | submitted 04:11 | stopped 06:00 (never left "waiting for capacity") | 0 billable | $0 |

EBS: 600 GB gp3 (6000 IOPS, 500 MB/s) ~ $2.6/day, keeps accruing while the instance is stopped (delete the volume after Round 1 if not needed). S3: ~25 GB in `pehchaan-ml-301745146083-use1` (corpus audio, manifests, scores, checkpoints, model) + 15.5 GB staging in the apse1 bucket, ~ $1/month. Commercial TTS: < $5 total (est.). **Round-1 total so far ~ $15-20 of the $1,500 budget.**
Price reference: EC2 p4d.24xlarge $21.96/h; SageMaker ml.p4d.24xlarge ~ $37-41/h.

## Progress

- [x] Infra, envs, public data, baselines (verified in-domain)
- [x] SynRef corpus, commercial stock voices (laptop), IndicSynth subset, Indic Parler-TTS (extra held-out)
- [x] Team S01/S02 segmentation (consent verified) + clones (F5, F5-Hindi, XTTS, CosyVoice2, Chatterbox, Seed-VC incl. Telugu)
- [x] Channel simulation, zero-shot scoring, fine-tune v0/v1/v2, calibration, bands, LRs
- [x] results/metrics.json, results/SUMMARY.md, figures (SVG + PNG), spectrograms
- [x] Serving (`POST /v1/voice/score`) tested on laptop CPU and GPU with v1 weights
- [ ] Not done: IndicF5 / MLAAD (gated 403), A100/H100 latency + multi-seed (no SageMaker capacity), real-call calibration (needs more real calls)
