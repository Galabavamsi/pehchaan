# ML status (Pehchaan voice provenance)

Last updated: 2026-10-06 00:30 IST

## BLOCKERS (need the user)

1. **No `.env` yet** (`D:/hackathons/amazon-raksham/.env` missing). Sarvam / OpenAI / Gemini / Deepgram stock-voice generation is skipped until keys appear. I re-check periodically.
2. **No Hugging Face token on this laptop.** Gated repos need a token from an account that has accepted their terms:
   - `ai4bharat/IndicF5` (MIT, gated "accept terms") -- core Indic cloner.
   - `vdivyasharma/IndicSynth` (CC-BY-NC-4.0, gated) -- public Indic spoof set.
   - Please run `huggingface-cli login` on the laptop (or put `HF_TOKEN=...` in `.env`) after accepting the terms on those two pages. Until then I use ungated alternatives and note it.
3. **GPU capacity:** p4d.24xlarge (all AZs), p4de.24xlarge, p5.4xlarge (all AZs) and g6e.2xlarge (all AZs) returned `InsufficientInstanceCapacity` at 00:20 IST. Running on **g5.2xlarge (1x A10G 24 GB)** instead; I retry P capacity periodically. Not blocking, just slower.
4. **Team recordings not in `data/raw/recordings/` yet** (expected ~12:00 IST). Pipelines are being built and tested on synthetic stock-voice references meanwhile.

## AWS resources I created (all tagged Project=pehchaan, us-east-1)

| Resource | ID |
|---|---|
| Key pair | `pehchaan-ml` (key-088fe7c1862ab164d); private key `ml/infra/pehchaan-ml` (gitignored) |
| Security group | `sg-023ef8c13605cbc8b` `pehchaan-ml-ssh`, SSH 22 from 103.147.138.252/32 only |
| S3 bucket | `pehchaan-ml-301745146083-use1` (private, BPA on, SSE-S3, versioning) |
| IAM role / instance profile | `pehchaan-ml-ec2` (S3 access to that bucket only) |
| Launch template | `lt-075d93f2e06074c0b` `pehchaan-ml` (DLAMI PyTorch 2.7 Ubuntu 22.04 ami-012ba162b9cd2729c, 600 GB gp3 encrypted, IMDSv2 required, shutdown=stop, idle watchdog in user-data) |
| Instance | `i-06da2349859b52482` g5.2xlarge us-east-1b, IP 52.91.206.100 |

## Instance log and cost

| Instance | Type | $/h (on-demand) | Start (IST) | Stop (IST) | Hours | Est. cost |
|---|---|---|---|---|---|---|
| i-06da2349859b52482 | g5.2xlarge | 1.212 | 2026-10-06 00:23 | running | | |

EBS: 600 GB gp3 (6000 IOPS, 500 MB/s) ~ $0.08/GB-month + IOPS/throughput extras ~ $2/day.
Price reference: p4d.24xlarge = $21.96/h (AWS Price List API, 2026-10-06).

## Progress

- [x] Infra: key, SG, bucket, IAM, launch template, instance
- [ ] Environments per generator
- [ ] Public data
- [ ] Zero-shot baselines
- [ ] Generators
- [ ] Channel simulation
- [ ] Fine-tune + calibration
- [ ] Results + figures
- [ ] Serving
