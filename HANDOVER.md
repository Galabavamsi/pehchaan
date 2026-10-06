# Pehchaan: context and handover (as of 2026-10-06, after Round 1 submission)

Read this first. Then read `SPEC.md` (the product contract) and skim `research/`.

---

## 1. What this is

- **Hackathon:** RAKSHAM – AI Cybersecurity Hackathon, organised by ARIES + DevClub (IIT Delhi) with Amazon and Learning Links Foundation. Prizes ₹4 L. ~2,350 teams registered, 30 go to the finale.
- **Team:** humanslop, IIT Bhilai.
  - **Galaba Vamsi**: lead; ML (voice detector) & backend; speaker S01 (Telugu, Hindi, English).
  - **Varun Rai**: product, app & user testing; speaker S02 (Hindi, English).
- **Track:** 01, Voice Cloning Fraud Detection.
- **Product:** **Pehchaan** (पहचान), "Verify the person, not the voice."
  - It is an SDK plus a risk API inside a bank or UPI app.
  - When someone pays a new or unusual payee during or ≤ 10 min after a call, it asks "Who asked you to pay?".
  - It then checks that claim through channels a cloned voice can't reach:
    - the relative's own registered phone (**Family Verify**, sent automatically);
    - the bank's live 1600-number call registry;
    - a family safe word.
  - Outcome is GO / PAUSE / HOLD (a 30-min cooling-off with a human release path), plus a signed evidence pack for 1930 / NCRP / Chakshu.
  - A clone detector exists, but the **voice score can never hold money**.
- **Status:**
  - The Round 1 PDF was **submitted on Unstop on 2026-10-06**.
  - The finale is **24–25 Oct 2026 at IIT Delhi**. Unstop lists 09:00 on the 24th to 20:00 on the 25th, about 35 h; the brief says "48 h". Results are pending.
  - Amazon pays finale travel; teams arrange their own accommodation.
- **Organisers:** team.ariesiitd@gmail.com · +91 7038703979 · +91 7058559569 · Unstop: https://unstop.com/competitions/raksham-ai-cybersecurity-hackathon-iit-delhi-1761331

### Scoring rubric (100)
| Criterion | Points |
|---|---|
| Problem fit | 20 |
| Architecture & detection logic | 20 |
| Differentiation | 15 |
| Feasibility / 48-h plan | 15 |
| Safety, privacy & responsible AI | 15 |
| Adoption & scale | 10 |
| Communication | 5 |

Only synthetic, public, consented or authorised data may be used, and all AI and third-party assets must be disclosed.

---

## 2. Key decisions, and why (don't re-litigate without new evidence)

1. **Track 01, not Track 02 or 03.**
   - Track 02 (UPI scam patterns) is the most crowded (~40–50% of teams), and the national systems already cover it (DoT FRI, RBI MuleHunter.ai).
   - Track 03's detectors are near-chance on real deepfakes.
   - Track 01 is the least crowded, has the strongest India evidence (Chakshu "impersonation as relative/friend" reports went from 258 to 19,564, 2024 → 2025), and is where the team's assets (GPUs, Sarvam, Bolna, Vapi, Deepgram) give it an edge.
2. **Verify the identity claim; don't trust audio forensics.** Detectors fail out of distribution, and our own data proved it (see §4).
3. **Explainable log-odds fusion with hard guardrails G1–G7, not a black-box model.**
   - Reasons are shown in Hindi and English, and the copy never accuses the user (G6).
   - Thresholds were tuned to an explicit alert budget.
4. **Positioned as the decision engine for RBI's proposed APP controls.** The RBI discussion paper of 9 Apr 2026 proposes a 1-hour lag above ₹10k, trusted-person approval for users aged 70+, and a kill switch. Pehchaan decides *when* to apply them instead of slowing everything.
5. **The voice detector runs in shadow mode.**
   - On one real cellular call, **every detector (ours too) flagged 91–95% of genuine speech as fake**; the measured likelihood ratio on real-call genuine speech was 0.93.
   - The score is therefore logged for analysts but has LR 1 in decisions until it passes a gate: ≤ 5% false flags on ≥ 50 consented real calls.
   - Watermark hits stay active (positive-only).
6. **SPEC v0.2 guardrails**, which came out of the simulator critique:
   - **G7:** the relative's signed "not me", or the bank's "we're not calling", gives HOLD always.
   - User-reported failed checks (callback, safe word) are advisory, LR 30.
   - **G1** excludes trigger-implied evidence (new payee, amount) and voice.
   - **Strict G2:** voice can never create a HOLD.
   - The bank claim is split into "My bank" vs "UPI app / shop".
   - A miss on a non-integrated bank's registry counts as "unknown".
   - Auto Family Verify.
   - The cue checklist is shown for a coached "no one".
7. **Only consented voices were cloned.** Public datasets are used only as genuine speech or as published spoof sets.

---

## 3. Where everything is

**Repo:** private, https://github.com/Galabavamsi/pehchaan (branch `master`). Local copy: `D:\hackathons\amazon-raksham\`.

| Path | What |
|---|---|
| `SPEC.md` | **The source of truth** for product and detection logic (v0.2 + shadow mode). Change it first. |
| `research/*.md` | Cited research: Track 01/03, India fraud statistics + Track 02 landscape, competition intel. Every slide statistic traces back here. |
| `submission/humanslop_Pehchaan_RAKSHAM_Round1.pdf` | **The submitted PDF**: 23 pages = 10 pitch slides + 3 architecture pages + appendix A1–A7. Gitignored; regenerate with the deck build below. |
| `deck/` | Deck source: `slides.src.html`, `styles.css`, `vendor/wires.js` (rough.js connectors and rough-notation), `fragments/`, `build.py`. |
| `engine/pehchaan/` | Fusion engine: `config.yaml` (every LR, with its basis), `fusion.py` (G1–G7), `explain.py` (EN/HI copy), `evidence.py` (hash chain + Ed25519 + NCRP/Chakshu pre-fill), `sim.py` (simulator). Tests are in `engine/tests/`. |
| `engine/results/` | `deck_numbers.json` (**every simulator number quoted in the deck**), sim JSONs, SVG charts (`*_deck.svg` are the large-font versions). |
| `app/server/` | FastAPI risk API (SPEC §7 contracts, mocked adapters for FRI, suspect registry, bank registry). |
| `app/web/` | React + Vite demo: payer phone, relative phone, analyst console, split view. |
| `app/screenshots/` | 15 deck screenshots plus `shoot.py`. |
| `app/README.md`, `app/NOTES.md` | Run commands, the finale demo script, design decisions A1–A23. |
| `ml/` | Corpus generation, channel simulation, training, evaluation, serving. `results/SUMMARY.md`, `results/metrics.json` and `results/figures/` hold the results; `DATA_CARD.md` has every dataset and model with its licence; `STATUS.md` is the run log. |
| `ml/serve/` | `POST /v1/voice/score` service. Weights are gitignored, in `ml/serve/weights/` and S3. |
| `data/recording-kit/` | Recording scripts plus the consent form (PDF/MD) used for S01 and S02. |
| `data/raw/recordings/` | **Team audio + consent screenshots. Gitignored, never commit or share.** |
| `tools/export_session.py` | Exports and redacts the Claude Code session transcript into `session-export/` (gitignored). |
| `.env` | API keys (HF_TOKEN, SARVAM, OPENAI, DEEPGRAM; GEMINI is unused). **Gitignored, never paste or commit.** Policy keeps keys on the laptop, never on cloud boxes. |

---

## 4. Numbers to quote (and their sources)

Check them against the files before reusing: `ml/results/metrics.json` (measured) and `engine/results/deck_numbers.json` (simulated).

**Measured: detector** (test set of 7,809 genuine / 11,265 cloned clips; 13 generators, 6 held out; held-out speaker S02; 5 simulated channels; one global threshold)

| Detector | EER, all | EER, unseen generators |
|---|---|---|
| Off-the-shelf XLS-R+AASIST | 34.3% (vs **0.27%** on its own ASVspoof 2019 benchmark) | 32.6% |
| Best public model, NII MMS-300M (non-commercial) | 15.1% | 13.9% |
| **Ours (fine-tuned)** | **4.8%** (AUC 0.989, ECE 0.048) | **6.0%** |

- **Generator split:**
  - Held out (never in training): Seed-VC, Chatterbox, Indic Parler-TTS, Sarvam Bulbul, OpenAI TTS, Deepgram Aura.
  - Seen: XTTS-v2, F5-TTS, F5-Hindi, CosyVoice2, MMS-TTS, Kokoro, IndicSynth.
- **Off-the-shelf model by language:** Telugu 44.4%.
- **Ours, weakest spots:** worst channel is speaker → mic at 7.5%; the held-out speaker S02 reaches 16.6% (S01 6.8%).
- **Real cellular call:** 91–95% of genuine chunks flagged by ours, 96–100% by NII → hence shadow mode.
- **Perth watermark:** detected in 100% of clean / PSTN / Opus clips, 88% replay, **30% after AMR-NB**.
- **Latency for a 10 s clip:** 32 ms model-only (A10G); 0.34 s end-to-end (RTX 4070); 0.98 s on CPU (int8). Risk assessment p95 3.8 ms in-process.
- **Tests:** engine 85/85, server 27/27.

**Simulated:** an assumption-driven projection at prior 1/400 (base-rate anchor ≈ 1/1300); distributions in `engine/sim_assumptions.yaml`.

| Measure | v0.1 | v0.2 final |
|---|---|---|
| Genuine triggered payments paused | 10.1% | **5.6%** (budget ≤ 6%) |
| Genuine triggered payments held | 0.92% | **0.21%** (budget ≤ 0.25%) |
| Scams paused / held | 96% / 77% | **95% / 73%** |
| Genuine holds per scam held | 4.8 | **1.2** |
| ₹ protected per ₹ delayed | 1.19 | **2.98** |

- **Held by scam pattern:** T1 (cloned relative) 59%, T2 (fake bank) 72%, T3 (digital arrest) 81%.
- **Family Verify enrolment 20% → 90%:** T1 held goes 53% → 66%.
- **Ablation (held, cumulative):** context only 0% → + claim 60% → + out-of-band checks 69% → + voice capture (script cues, not the detector) 73%. Shadow and calibrated voice modes give identical holds.

---

## 5. How to run

```bash
# Deck → PDF + PNG previews + a raster audit of every page
python deck/build.py                  # writes deck/out/deck.pdf, deck/out/slide_NN.png
# Engine tests + simulator (regenerates engine/results/*, deck_numbers.json, charts)
cd engine && python -m pytest -q && python -m pehchaan.sim
# Demo (see app/README.md for exact commands): API on :8400, web on :5173
# Voice-score service (laptop GPU or CPU): see ml/README.md and ml/serve/
```

Toolchain: Windows 11, Git Bash, Python 3.12, Node 24, Playwright Chromium, gh CLI (account Galabavamsi), Firecrawl CLI (~8k credits left), AWS MCP.

---

## 6. Cloud state (AWS account owned by the user; signed in through the AWS MCP as **root**. Switch to an IAM user plus MFA)

**Current state:**
- **Running:** nothing. No instances, SageMaker jobs, endpoints or Elastic IPs in us-east-1 or ap-southeast-1.
- **Kept:**
  - **AMI `ami-02d874e711bfbc4e4`** "pehchaan-ml-2026-10-06" (us-east-1). It contains every generator and detector environment.
  - Launch template `pehchaan-ml`, security group `pehchaan-ml-ssh` (SSH limited to one IP; **update it to the new IP**), key pair `pehchaan-ml` (private key at `ml/infra/pehchaan-ml`, gitignored), IAM roles `pehchaan-ml-ec2` and `pehchaan-sagemaker-exec`.
- **S3:** `pehchaan-ml-<acct>-use1` and `pehchaan-ml-<acct>-apse1`.
  - Private, encrypted and versioned.
  - **They auto-delete everything on 31 Dec 2026**, the consent promise.
  - They hold the recordings, the corpus and the trained model `models/pehchaan-xlsr-aasist-ft-v1/`.

**Quotas and costs:**
- **EC2 quotas:** On-Demand P = 96 vCPU and G = 8 vCPU in us-east-1, though large-GPU capacity was unavailable on 6 Oct.
- **SageMaker training quotas:** ml.p4d.24xlarge = 1 and ml.p4de.24xlarge = 1 in ap-southeast-1; also g6e endpoint quota.
- **Spend:** Round 1 cost about $15–20 of the $10k credits. Holding costs are now about $2–10/month (AMI snapshot + S3).
- **Relaunch:** start from launch template `pehchaan-ml` with the AMI above (g5.2xlarge, A10G), and keep the idle watchdog.

---

## 7. Accounts, credits, people

- **YC student deals (all redeemed):**
  - AWS $10k
  - Deepgram $15k
  - Firecrawl 10k
  - OpenAI $1k
  - Anthropic
  - Google $2k (**not set up; avoid**, the user's GCP bills a real card)
  - Sarvam AI
  - Bolna AI
  - Vapi
  - Tavus
  - sync.
  - Razorpay
  - Supabase
  - Langfuse $600
  - Respan
  - AgentMail
  - Browser Use
  - Roboflow
  - Blaxel
  - Gumloop
  - Greptile
  - Azure for Startups
- **Other compute:** Lightning AI B300 (not used yet).
- **Hugging Face:** a fine-grained token with gated access accepted for IndicF5, indic-parler-tts, IndicVoices and MLAAD. MLAAD and IndicF5 audio still returned 403 to the ML pipeline.
- **Consent:**
  - S01 and S02 signed digitally (WhatsApp-message consent; screenshots in `data/raw/recordings/`).
  - It covers cloning for this hackathon only, no public release, and deletion by 31 Dec 2026. Withdrawal is honoured within 7 days.

---

## 8. Open items / next steps

**Before the finale (if shortlisted):**
1. **Close the real-call gap** (the biggest technical risk and the finale's headline).
   - Collect 100+ consented calls over real networks via Bolna/Vapi or plain cellular/WhatsApp, genuine and clone (team voices only).
   - Retrain, then report the real-call false-flag rate before and after.
   - Promote voice to "calibrated" mode only if it passes the gate.
2. **Android shell (Kotlin or Flutter):** read real call state and VoIP audio mode, call the AWS risk API, and run Family Verify on a second real phone.
3. **Live attack demo:** a Vapi/Bolna agent with a consented cloned teammate voice calls a real phone, ending in PAUSE → auto Family Verify → "No" → HOLD. The demo script is in `app/README.md`.
4. **Bank "are we calling you?" registry:** mock it on Amazon Connect outbound. Note that Amazon Connect **Voice ID was retired on 20 May 2026**, and **Amazon Fraud Detector is closed to new customers**; don't cite either as available.
5. **Comprehension test** with 5 consented elders/volunteers (Hindi + 1 regional language).
6. **Security hygiene:** create an IAM user, enable root MFA, update the SG IP, and decide about the repo's visibility. It contains the account ID, bucket names and SG IP in `ml/`; scrub them before making it public.

**Hackathon side:**
- Watch Unstop/email for results.
- The finale is a 35–48 h build; the hour-by-hour plan is on deck slide 10.

**Known weak spots (be ready for judges' questions):**
- T1 holds are only 59%, because they depend on family-circle enrolment and uptake.
- The likelihood ratios are assumptions until shadow-mode calibration.
- Only 2 speakers and 1 real call.
- The simulator isn't real-world validation.
- Some generators emit digital silence between words (a shortcut risk).
- Several model weights are non-commercial (listed in `ml/DATA_CARD.md` and appendix A7).

---

## 9. Gotchas learned

- **Deck rendering:**
  - Avoid CSS/SVG filters and box-shadow; Chromium rasterises them in the PDF.
  - Inline SVG (not `<img>`) is needed for page fonts.
  - Absolutely positioned diagram nodes need `.dia .node.jn/.an { position:absolute }`.
  - Lanes need `z-index:-1` so wires show.
- **Shell:**
  - Complex Python heredocs with quotes can break the shell wrapper; write a temporary `.py` file instead.
  - The Windows console needs `PYTHONIOENCODING=utf-8` for Hugging Face CLI emoji.
- **Data hygiene:**
  - Don't copy `.env` to cloud boxes; Claude Code policy blocks it. Generate commercial TTS locally.
  - Real phone-network audio ≠ simulated codecs (AMR-WB/EVS, noise suppression and AGC aren't simulated).
- **AWS:** the MCP sometimes drops tools mid-session ("Unknown tool"); re-run ToolSearch `select:` to reload.

---

## 10. Starting a new Claude Code session

Paste this:

> "Read `D:\hackathons\amazon-raksham\HANDOVER.md` and `SPEC.md`. We're team humanslop (Pehchaan, RAKSHAM Track 01). Round 1 is submitted. Next goal: [finale prep: close the real-call gap / Android shell / live demo]."

Memory notes for this project also exist under `~/.claude/projects/D--hackathons-amazon-raksham/memory/`: raksham-hackathon, user-assets-raksham and pehchaan-status.
