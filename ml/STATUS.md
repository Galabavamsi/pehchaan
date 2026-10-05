# ML status (Pehchaan voice provenance)

Last updated: 2026-10-06 05:40 IST

## BLOCKERS (need the user)

1. **HF token cannot download gated repos (403 GatedRepoError).** The token in `.env` is a *fine-grained* token for `galabavamsi`. Downloads of `ai4bharat/IndicF5`, `ai4bharat/indic-parler-tts`, `ai4bharat/IndicVoices` and `mueller91/MLAAD` are denied. Please either
   - open each page while logged in and click "Agree and access repository" (IndicF5, indic-parler-tts, IndicVoices, MLAAD), **and**
   - give the token the permission "Read access to contents of all public gated repos you can access" (Settings -> Access Tokens -> edit), or make a classic *read* token.
   Until then: Indic F5 cloning uses the ungated **SPRINGLab/F5-Hindi-24KHz** (CC-BY-4.0, IIT Madras); IndicSynth is ungated and is being downloaded.
2. **Keys stay on the laptop.** Copying `.env` (HF token / API keys) to the EC2 box was blocked by the Claude Code permission policy (credential exfiltration guard). So commercial TTS (Sarvam, OpenAI, Deepgram) runs **from the laptop** and only the audio is uploaded; gated HF files would be downloaded on the laptop and uploaded as files. If you want the GPU box/SageMaker to use the keys directly, you would have to allow it explicitly; not needed for Round 1.
3. **GPU capacity:** EC2 p4d / p4de / p5.4xlarge / g6e.2xlarge had no capacity in us-east-1 (all AZs) at 00:20 IST. Running on **g5.2xlarge (1x A10G 24 GB)**. SageMaker training in ap-southeast-1 (ml.p4d.24xlarge quota 1) is set up as the heavy-batch option.
4. Team recordings: S01 recording now; S02 later today (planned held-out speaker). Gemini dropped (no key).

## RESULTS SO FAR (05:40 IST, still preliminary; final numbers + figures land in results/ by ~09:00 IST)

Test set: 7,765 bona fide / 10,610 spoof clips (FLEURS hi/te/ta/en/+5, team S01 test lines + held-out speaker S02 + real call;
spoofs from 12 generators incl. 5 held-out), 5 simulated channels pooled, one global threshold.

| Detector | EER all | EER seen gens | EER held-out gens | AUC | FRR @ FAR 5 % | ECE |
|---|---|---|---|---|---|---|
| XLS-R+AASIST LA, off-the-shelf | 34.4 % | 36.7 % | 32.6 % | 0.71 | | 0.11 |
| NII MMS-300M AntiDeepfake, off-the-shelf (NC) | 15.1 % | 16.7 % | 13.8 % | 0.92 | | 0.06 |
| **Pehchaan fine-tuned (v1, with team S01 data)** | **4.6 %** | **2.8 %** | **5.9 %** | 0.989 | 4.3 % | 0.04 |

- Ours by channel: clean 2.9, PSTN 4.1, AMR-NB 4.7, Opus 3.4, speaker->mic replay 6.9 (EER %).
- Hardest held-out generators for ours: Deepgram 11.1 %, **Seed-VC voice conversion 10.1 %**, Chatterbox 6.1 %.
- **Biggest honest failure: a REAL cellular call.** Genuine speech from the S02-S01 phone call is put in `likely_synthetic`
  91 % of the time (simulated phone channels: 0-2 % on the same speakers). Measured on that call, LR(likely_synthetic)
  collapses to ~0.9 (no information). NII does the same (96-100 % flagged). So simulated codecs do not cover real network
  processing; voice must stay supporting evidence (G2) until we calibrate on real calls. A v2 run with richer telephony
  augmentation (low AMR modes, codec tandems, handset noise suppression/AGC, codec->speakerphone) is training now; it was
  designed after seeing this failure, so its real-call number will be labelled as such.

Note: S01 consent typo fixed by the lead (04:20 IST). Gender is unknown for team speakers.

## EARLY RESULTS (03:55 IST, preliminary; test = FLEURS bona fide + SynRef/commercial/IndicSynth spoofs, 5 simulated channels pooled; team audio not yet in this table)

Zero-shot (off-the-shelf) detectors, 7,500 bona fide / 9,020 spoof test clips:

| Detector | In-domain sanity (ASVspoof19 LA eval) | Our Indic test, pooled EER | AUC | clean | PSTN | AMR-NB | Opus | replay |
|---|---|---|---|---|---|---|---|---|
| XLS-R+AASIST (LA ckpt) | 0.27 % | **33.8 %** | 0.72 | 27.4 | 29.0 | 32.5 | 29.1 | 37.2 |
| XLS-R+AASIST (DF ckpt) | 0.20 % | **40.0 %** | 0.65 | 25.3 | 37.1 | 40.4 | 34.8 | 47.7 |
| NII MMS-300M AntiDeepfake (NC licence) | 2.5 % | **15.3 %** | 0.92 | 1.2 | 3.7 | 6.5 | 2.9 | 31.2 |

Notes: per-channel EERs are lower than the pooled EER because each channel shifts the score distribution, so one
global threshold (what a product must use) does worse than per-channel thresholds. NII is the strongest public model
but its weights are non-commercial, and it still fails on speaker->mic replay (31 %).
Fine-tuned run v0 (no team data yet): dev EER (seen generators) 28 % -> 1.6 % after one epoch; test numbers incl.
held-out generators pending (~05:00 IST).
Perth watermark (Chatterbox outputs): detected 100 % clean / PSTN / Opus, 88 % replay, **30 % after AMR-NB**;
false positives 0-0.7 % except 6.7 % on replay.

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
| i-06da2349859b52482 | g5.2xlarge | 1.212 | 2026-10-06 00:23 | running | | |
| SageMaker `pehchaan-ft-v1-1005-2241` (ap-southeast-1) | ml.p4d.24xlarge training, 8 runs in parallel (main, 2 extra seeds, no-channel-aug, no-RawBoost, init-DF, no-team, high-LR) + A100 latency; MaxRuntime 4 h, no warm pool | ~37-41 | submitted 04:11 | | | $0 while "waiting for capacity" |

EBS: 600 GB gp3 (6000 IOPS, 500 MB/s) ~ $2/day. Commercial TTS: < $5 total (est.).
Price reference: EC2 p4d.24xlarge $21.96/h; SageMaker ml.p4d.24xlarge ~ $37-41/h.

## Progress

- [x] Infra: key, SG, buckets, IAM, launch template, instance, idle watchdog (cron, 45 min)
- [x] Environments: det, f5, xtts, chatterbox, seedvc, cosy, misc (uv venvs, one per generator)
- [x] Public data: FLEURS hi/te/ta/en (train/dev/test) + mr/bn/kn/ml/gu (dev/test) = 19,634 bona fide clips; ASVspoof 2019 LA (subset manifest 13.6k)
- [x] Baselines load and are verified in-domain on ASVspoof19 LA eval subset: SSL-AASIST LA EER 0.27 %, SSL-AASIST DF EER 0.20 %, NII MMS-300M AntiDeepfake EER 2.5 %
- [x] Generator smoke tests pass (Whisper re-transcription checked): F5-TTS, F5-Hindi, XTTS-v2, Chatterbox-ML, CosyVoice2, Seed-VC, MMS-TTS, Kokoro
- [~] SynRef corpus (synthetic stock voices as references; no real person cloned): stock MMS 1040 + Kokoro 520 done; XTTS, F5, F5-Hindi, Chatterbox, CosyVoice2, Seed-VC running (ETA ~03:30 IST)
- [~] Commercial stock voices from the laptop: Sarvam 400, OpenAI 320, Deepgram 130 (running)
- [ ] IndicSynth subset (hi/te/ta) download
- [ ] Team recordings: segmentation + cloning (script ready: `data_prep/segment_team.py`)
- [ ] Channel simulation of the whole corpus; zero-shot baseline scoring (ETA first numbers ~05:00 IST)
- [ ] Fine-tune + calibration + bands
- [ ] Results + figures
- [ ] Serving
