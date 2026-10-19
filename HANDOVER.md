# Pehchaan: handover (as of 20 Oct 2026, finale on 24–25 Oct)

Read this first, then `TASKS.md` (what's left, day by day, and the final checklist), then `SPEC.md` (the
product contract). `CLAUDE.md` is the short version for Claude Code sessions.

---

## 1. What this is

- **Hackathon:** RAKSHAM, an AI cybersecurity hackathon by ARIES + DevClub (IIT Delhi) with Amazon and Learning
  Links Foundation. Prizes ₹4 L. 4,723 registrations; we are **in the top 30**.
- **Finale:** IIT Delhi, **24 Oct 09:00–19:00 and 25 Oct 09:00–19:00 IST**. No overnight stay on campus. Amazon
  pays travel; we arrange accommodation. Organisers: team.ariesiitd@gmail.com · +91 7038703979 · +91 7058559569.
- **Team humanslop (IIT Bhilai):**
  - **Galaba Vamsi (S01):** ML and backend.
  - **Varun Rai (S02):** product, app, user testing; taking over as lead from 20 Oct.
- **Track 01: voice-cloning fraud detection.** Product **Pehchaan** (पहचान), "Verify the person, not the voice."
  - It is an SDK plus a risk API inside a bank or UPI app.
  - When someone pays a new or unusual payee during or ≤ 10 min after a call, it asks *"Who asked you to pay?"*.
  - It then checks that claim through channels a clone can't reach:
    - **Family Verify**: the relative's own phone, sent automatically;
    - the bank's live "are we calling you?" registry;
    - a family safe word.
  - Outcome: **GO / PAUSE / HOLD** (a 30-min cooling-off with a human release path), plus a signed evidence
    pack for 1930 / NCRP / Chakshu.
  - A clone detector exists, but **voice can never hold money** (guardrail G2). It runs in **shadow mode**
    until it passes a real-call gate.

### Rubric (100)
Problem fit 20 · architecture & detection 20 · differentiation 15 · feasibility 15 · safety/privacy/responsible
AI 15 · adoption 10 · communication 5. Only synthetic, public, consented or authorised data. Disclose all AI and
third-party assets.

---

## 2. Where we are (20 Oct)

| Area | State |
|---|---|
| Spec, engine, simulator | ✅ done (Round 1) |
| Risk API + React demo (3 surfaces) | ✅ works locally; ❌ not deployed yet |
| Voice detector v1 | ✅ served locally (`ml/serve`), 4.8 % EER simulated |
| Real-call pipeline (`ml/realcall`) | ✅ built; 48 real calls to D1; hands-free on Samsung |
| Retrained model A (real-call data + learned channel) | ✅ real-call EER 6.8 % (v1: 24.6 %); weights in S3; ❌ not served |
| D2 (Redmi) held-out handset test | ⚠️ ~7 calls; adb can answer but can't turn on speaker → answer by hand |
| Live genuine volunteer calls (the gate) | ❌ not started; consent forms needed |
| Deployment on humanslop.in | ❌ only `calls.humanslop.in` (tunnel to a laptop) |
| Live attack call + Family Verify on a real 2nd phone | ❌ not built yet; this is the finale headline |
| Deck update for the finale | ❌ |

What to do next, in order, is in **`TASKS.md`**.

---

## 3. Key decisions (don't re-litigate without new evidence)

1. **Track 01, not Track 02 or 03.**
   - Track 02 (UPI scams) is the most crowded and already covered by national systems.
   - Track 03's detectors are near chance.
   - Track 01 has the strongest India evidence: Chakshu "impersonating a relative" reports went from 258 to
     19,564, 2024 → 2025.
2. **Verify the identity claim; don't trust audio forensics.** Detectors fail out of distribution, and our own
   data proved it twice (Round 1's real call, and this week's 48 calls).
3. **Explainable log-odds fusion with hard guardrails G1–G7**, not a black box. Reasons are shown in
   Hindi/English, and the copy never accuses the user (G6).
4. **Positioned as the decision engine for RBI's proposed APP-fraud controls** (discussion paper, 9 Apr 2026:
   1-hour lag above ₹10k, trusted-person approval for users 70+). Pehchaan decides *when* to apply them.
5. **Voice stays in shadow mode** (LR 1 in decisions) until it passes the **gate**: ≤ 5 % false flags on ≥ 50
   live genuine calls from held-out callers (`ml/realcall/protocol.py`). Watermark hits stay active.
6. **Only consented voices are cloned.** The code enforces it: `ml/realcall/consent.py` refuses to dial,
   record or clone anyone without a consent evidence file.
7. **Splits are pre-registered** in `ml/realcall/protocol.py`:
   - S02 and `sarvam_ivc` are test-only;
   - D2 is a test-only handset, set before any D2 data existed.
   Change it only with a dated note, never after looking at test results.

---

## 4. Repo map (`github.com/Galabavamsi/pehchaan`, private)

| Path | What |
|---|---|
| `TASKS.md` | **Done / to do / on-site plan / final checklist.** Keep it current. |
| `SPEC.md` | Product and detection logic (v0.2 + shadow mode). Change it first. |
| `CLAUDE.md` | Context and rules for Claude Code sessions |
| `research/*.md` | Cited research; every deck statistic traces back here |
| `deck/` | Deck source (`slides.src.html`, `build.py`). `python deck/build.py` builds `deck/out/deck.pdf` |
| `engine/pehchaan/` | Fusion engine (`config.yaml` holds every LR with its basis), guardrails, EN/HI copy, evidence pack, simulator |
| `engine/results/deck_numbers.json` | Every simulator number quoted in the deck |
| `app/server/` | FastAPI risk API (SPEC §7, mocked FRI / suspect registry / bank registry), SQLite, WebSockets |
| `app/web/` | React + Vite demo: payer phone, relative phone, analyst console, split view. Demo script: `app/README.md` |
| `ml/` | Corpus, channel simulation, training (`train/finetune.py`), evaluation, serving (`serve/`). `ml/README.md`, `ml/STATUS.md`, `ml/DATA_CARD.md` |
| `ml/realcall/` | **Real-call collection, the learned channel, staging, comparison.** README, FINDINGS.md |
| `ml/infra/` | GPU box scripts: `sync_up.sh`, `retrain_v3.sh`, `ssh_config`, `user_data.sh` |
| `data/recording-kit/` | Recording scripts; consent forms (`CONSENT_FORM` for cloning, `CONSENT_LIVE_CALLS.md` for recording only) |
| `data/raw/` | **Gitignored. Team audio and consent evidence.** Never commit or share. |

Branches: `master` (Round 1) and `realcall-collection` (everything since the shortlist; open PR to master).

---

## 5. Numbers to quote, and where they come from

Always re-check against the source files before putting a number on a slide.

**Simulated (Round 1, `ml/results/metrics.json`).** Test set: 7,809 genuine / 11,265 cloned clips, 13 generators
(6 held out), held-out speaker S02, 5 simulated channels.

| Detector | EER, all | EER, unseen generators |
|---|---|---|
| Off-the-shelf XLS-R+AASIST | 34.3 % (0.27 % on its own ASVspoof benchmark) | 32.6 % |
| Best public model (NII, non-commercial) | 15.1 % | 13.9 % |
| **Ours v1** | **4.8 %** | **6.0 %** |

**Real calls (this week, `ml/realcall/FINDINGS.md`).** 236 held-out test clips from 41 calls (Vobiz → Jio →
Samsung on speakerphone → laptop mic).

| Model | Real-call EER | Held-out speaker S02 | Clones caught | Genuine flagged | Simulated EER |
|---|---|---|---|---|---|
| v1 (served today) | 24.6 % | 21.7 % | 48 % | 3 % | 4.8 % |
| **Model A** (learned channel + real-call clips) | **6.8 %** | **8.7 %** | **75 %** | **0 %** | 6.1 % |

**Learned channel validation:** clean clones pushed through it are caught 27 % of the time, against 28 % on
real calls, so it reproduces the real failure.

**Caveats (say them before judges ask):**
- one handset, carrier and room; single seed; same script lines;
- 41 calls; the gate isn't met yet (no live genuine calls);
- held-out generators are still the weakest (Chatterbox 43 %, Seed-VC 62 % caught).

**Simulator** (`engine/results/deck_numbers.json`, at a prior of 1/400): genuine triggered payments 5.6 % paused,
0.21 % held; scams 95 % paused, 73 % held; 1.2 genuine holds per scam held; ₹2.98 protected per ₹1 delayed.

**Latency:** risk decision p95 3.8 ms in-process; voice score 0.34 s on GPU, 0.98 s on CPU (int8) for 10 s audio.

---

## 6. Setup on a new laptop (Windows; Varun)

1. **Tools:** Python 3.12, Node 20+, Git, gh CLI, AWS CLI v2, ffmpeg, cloudflared, Android platform-tools (adb).
2. **Get the code:**
   ```bash
   gh repo clone Galabavamsi/pehchaan
   ```
   Then `git switch realcall-collection`, or `master` once the PR is merged.
3. **Secrets and private files** (gitignored; Galaba gives them to you directly):
   - `.env` in the repo root: `VOBIZ_AUTH_ID`, `VOBIZ_AUTH_TOKEN`, `SARVAM_API_KEY`, `DEEPGRAM_API_KEY`,
     `OPENAI_API_KEY`, `HF_TOKEN`, `CLOUDFLARE_API_TOKEN`;
   - `ml/realcall/participants.yaml`, `ml/realcall/config.yaml`;
   - `ml/infra/pehchaan-ml` (the SSH key for the GPU box);
   - the Cloudflare tunnel files from `%USERPROFILE%\.cloudflared\` (`cert.pem`, `fe923565-…json`, `config.yml`);
     put them in yours and fix the credentials path in `config.yml`;
   - `data/raw/` (consent evidence and team recordings, 20 MB).
4. **Python packages:**
   ```bash
   pip install -r app/server/requirements.txt -r ml/serve/requirements.txt -r ml/realcall/requirements.txt
   ```
   Then install the engine as a package:
   ```bash
   pip install -e engine
   ```
5. **Web app:**
   ```bash
   cd app/web && npm install
   ```
6. **Model weights and data from S3** (all large files live in S3, not git):
   - v1 serving weights: `s3://pehchaan-ml-301745146083-use1/models/pehchaan-xlsr-aasist-ft-v1/weights/`
     → `ml/serve/weights/`;
   - model A: `…/runs/ours_v3_rc/best.pt` (also `ours_v1_rc`, `ours_v3`, `ours_v1`);
   - real-call working folder (captures, segments, tapes, ledger, manifests, reports, retrain scores), 883 MB:
     ```bash
     aws s3 sync s3://pehchaan-ml-301745146083-use1/work/realcall_laptop ml/realcall/work
     ```
     The ledger and manifest store the original laptop's absolute paths, so point them at your checkout once
     (run from `ml/`):
     ```bash
     python -m realcall.relocate
     ```
   - staged training bundle: `…/work/realcall`; retrain scores: `…/work/scores_rc`.
7. **AWS:** you use the account's **root** login (Galaba's decision, 20 Oct). Run `aws configure` with a root
   access key or use the console. Region `ap-south-1` (Mumbai) for deployment; GPU work lives in `us-east-1`.
8. **Check everything works:**
   ```bash
   cd engine && python -m pytest -q
   ```
   ```bash
   cd app/server && python -m pytest -q
   ```
   ```bash
   cd ml && python -m pytest -q realcall/tests
   ```

---

## 7. How to run things

**Demo (local).** API on :8400, web on :5173. Open http://127.0.0.1:5173/#/demo (split view),
`#/payer?scenario=T1`, `#/relative`, `#/console`.
```bash
cd app/server && python -m uvicorn pehchaan_api.main:app --port 8400
```
```bash
cd app/web && npm run dev
```

**Voice service (v1), local CPU:**
```bash
cd ml && PEHCHAAN_DEVICE=cpu python -m uvicorn serve.app:app --port 8500
```
Point the API at it with `VOICE_SERVICE_URL=http://127.0.0.1:8500`.

**Real-call session.** Full details are in `ml/realcall/README.md`. Run from `ml/`:
```bash
python -m realcall.server
```
```bash
cloudflared tunnel run pehchaan
```
```bash
python -m realcall.capture session --device D1 --seconds 3600
```
```bash
python -m realcall.dial tape --device D1 --n 20 --auto-answer
```
```bash
python -m realcall.ingest
```
```bash
python -m realcall.compare_models
```
- Run the server and the tunnel in separate terminals.
- Phone set-up: 5 cm from the laptop mic, full volume, quiet room. Unlocked, plugged in, USB debugging on,
  "Stay awake" on.
- **Hands-free works on the Samsung (D1) only.** On the Redmi (D2) answer by hand and tap Speaker yourself.

**Retraining on the GPU box (about $3).**
1. Launch from AMI `ami-02d874e711bfbc4e4` with launch template `pehchaan-ml` (`g5.2xlarge`, us-east-1).
2. **Swap the security group to `pehchaan-ml-ssh`**: the template attaches `default`, and SSH times out.
3. Put the new IP in `ml/infra/ssh_config`.
4. Run `bash ml/infra/sync_up.sh` (the box stops itself at the end):
   ```bash
   ssh -F ml/infra/ssh_config pehchaan "nohup bash ~/pehchaan/ml/infra/retrain_v3.sh > ~/logs/retrain_v3.log 2>&1 &"
   ```
5. Results go to S3 under `work/scores_rc` and `runs/`.

**Deck:**
```bash
python deck/build.py
```

---

## 8. Known weak spots (be ready for judges)

- Real-call evidence covers **one handset and one carrier**; D2 and live callers aren't done yet. The gate is unmet.
- T1 (cloned relative) holds are 59 % in simulation and depend on Family Verify enrolment (20 % → 90 %
  enrolment raises it from 53 % to 66 %).
- Likelihood ratios are assumptions until shadow-mode calibration on real traffic.
- Only 2 cloned speakers so far; volunteers V01–V05 are pending consent forms.
- Some generators emit digital silence between words (shortcut risk; trimming is identical for real and fake).
- Several model weights are non-commercial (`ml/DATA_CARD.md`, appendix A7).
- Speakerphone capture is degraded: the service's quality gate passes only ~14 % of laptop-mic clips. An in-app
  capture would be better.

---

## 9. Accounts, cloud and infrastructure

| What | Where / state |
|---|---|
| AWS account | `301745146083`. Currently used as root; Business Support+ ($101 in Oct, paid by credits). Credits ≈ $10k. |
| S3 | `pehchaan-ml-301745146083-use1` (models, runs, corpus, real-call data under `work/realcall`, scores) and `…-apse1`. Private, encrypted, **auto-delete on 31 Dec 2026** (consent promise). |
| GPU | AMI `ami-02d874e711bfbc4e4`, launch template `pehchaan-ml`, SG `pehchaan-ml-ssh` (SSH from one IP: update it), key `pehchaan-ml`. Instance `i-0fa3f0f58693b173e` is **stopped and kept** (Galaba's decision, 20 Oct): its 600 GB disk (≈ $48/month) still holds the corpus, envs and runs, so retraining can restart without re-staging. |
| Quotas (us-east-1) | On-demand G/VT 96 vCPU, P 128 vCPU; SageMaker p5.4xlarge ×2, p5.48xlarge ×1, p4d ×1, g6e.12xlarge ×2. Pending: SageMaker g5.2xlarge ×4, g5.12xlarge ×3 (replied 19 Oct), p5.48xlarge in Mumbai. |
| Other instances in the account | **Not Pehchaan. Paused (stopped) on 20 Oct** at Galaba's request, both with Elastic IPs so their addresses survive: `urumi-vps` `i-03f0fb3c44dba37de` (t3.large, 13.207.251.41, serves `*.urumi.humanslop.in`) and `t9984-speech-recorder` `i-030f4cdcddd8dce47` (t4g.small, 3.109.169.75), both in ap-south-1. Restart with `aws ec2 start-instances --region ap-south-1 --instance-ids <id>`. The m7i.8xlarge in us-east-1 no longer exists. |
| Cloudflare | `humanslop.in` DNS. Tunnel `pehchaan` (id `fe923565…`, credentials in `~/.cloudflared/` on Galaba's laptop) → `calls.humanslop.in`. Other records (jalsakshi, charter, urumi, mail) belong to other projects: **don't touch**. |
| Vobiz | Number +91 80 6426 0325, KYC-verified, 1 call/s, 3 concurrent. Keys in `.env`. Check the balance in the console. |
| Sarvam | API key in `.env` (≈ $1,000 credits). Voice cloning via `realcall/sarvam_clone.py` (not run yet). |
| Phones | **D1** Samsung M34 (Jio, Galaba), hands-free works. **D2** Redmi Note 12 Pro 5G (Jio, Varun, Google Phone app), test-only, adb can't switch on speaker. Numbers are in `participants.yaml` (never in git). |
| Other credits | Deepgram $15k, OpenAI $1k, Firecrawl, Bolna, Vapi, Langfuse, etc. (YC student deals). Google/GCP bills a real card: avoid. |

**Consent:**
- S01 and S02 signed digitally for cloning (hackathon only, no public release, deletion by 31 Dec 2026,
  withdrawal within 7 days).
- Volunteers must sign `CONSENT_LIVE_CALLS.md` (recording only) or `CONSENT_FORM` (cloning) before
  `participants.yaml` lets the code use them.

---

## 10. Gotchas

- **Windows shell:**
  - Long inline Python heredocs with quotes break the Bash wrapper; write a temporary `.py` file instead.
  - Set `PYTHONIOENCODING=utf-8` for Hindi/Telugu output.
  - Python writes CRLF on Windows; git normalises it, so `git status` may list files with only line-ending
    changes (`git diff --ignore-cr-at-eol` shows the real ones).
- **AWS MCP connector** drops tools mid-session ("Unknown tool"). Reload it, or use the AWS CLI.
- **Launch template** attaches the `default` SG; swap to `pehchaan-ml-ssh` or SSH times out.
- **Deck rendering:**
  - No CSS/SVG filters or box-shadow.
  - Inline SVG for fonts.
  - Diagram nodes need `position:absolute`.
- **Real calls:**
  - The tape plays 6 s after answer, so speaker must be on before the start chirp. Ingest recovers if only the
    end chirp is heard.
  - Laptop at arm's length loses ~10 dB SNR.
  - Samsung auto-record never produced files.
- **Simulated codecs ≠ real networks**; that's the whole point of `ml/realcall`.
- **Don't copy `.env` to cloud boxes.** Placing calls and making Sarvam clones stay on a laptop.

---

## 11. Starting a Claude Code session

Paste this:

> Read `HANDOVER.md`, `TASKS.md` and `CLAUDE.md` in this repo. We're team humanslop (Pehchaan, RAKSHAM Track 01,
> finale 24–25 Oct). Next task: <pick from TASKS.md>.
