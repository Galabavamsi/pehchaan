# Pehchaan: finale task list and checklist

**Finale:** RAKSHAM, IIT Delhi. On site **24 Oct 09:00 – 19:00** and **25 Oct 09:00 – 19:00 IST**. We can't stay on
campus overnight. Results are announced on 25 Oct around 20:00.

**Rule for this list: everything is built and tested before 24 Oct.** On site we only validate, polish, rehearse
and present. Orientation, mentor rounds, food and travel take most of the 20 hours. Nothing on site should be the
first time we try something.

Owners: **G** = Galaba, **V** = Varun. Tick boxes as you go and commit this file.

---

## 🎯 Goals

1. **Win the finale.** Rubric (100): problem fit 20 · architecture & detection 20 · differentiation 15 ·
   feasibility 15 · safety/privacy/responsible AI 15 · adoption 10 · communication 5.
2. **Show judges, live:** a cloned-voice call reaches a real phone → the payer taps Pay → Pehchaan asks
   "Who asked you to pay?" → **Family Verify on a second real phone** → "not me" → HOLD → signed report.
   Then the same set-up with the real person → one tap → paid.
3. **Show honest numbers:** on real phone calls, the detector went from 24.6 % to 6.8 % EER after retraining on
   real-call data. We still don't let voice decide ("verify the person, not the voice").
4. **Show it's real:** deployed on `humanslop.in`, consent and privacy visible everywhere.

---

## ✅ Already done

### Round 1 (by 6 Oct)
- [x] Track 01 chosen; product spec `SPEC.md` v0.2 (guardrails G1–G7, voice in shadow mode)
- [x] 23-page Round 1 PDF submitted (deck source in `deck/`, build with `python deck/build.py`)
- [x] Fusion engine and simulator (`engine/`, 85 tests): genuine 5.6 % paused / 0.21 % held, scams 95 % / 73 %
- [x] Risk API (FastAPI, `app/server`, 27 tests) and React demo (`app/web`): payer phone, relative phone, analyst
      console, split view; 4-minute demo script in `app/README.md`
- [x] Voice detector v1: 4.8 % EER on simulated phone channels (34 % for the off-the-shelf model); serving
      `POST /v1/voice/score` (`ml/serve`)
- [x] Consented recordings of S01 (Galaba) and S02 (Varun) plus clones from 13 generators

### Since the shortlist (16–20 Oct)
- [x] Real-call pipeline `ml/realcall/` (consent registry, tapes, Vobiz dialer, webhook server, laptop capture,
      ingest/QC, gate report, Sarvam clone script, S3 staging, adb hands-free answering). See its README.
- [x] Vobiz number +91 80 6426 0325 (KYC-verified). Cloudflare tunnel `pehchaan` → `calls.humanslop.in`.
- [x] 48 real tape calls to D1 (Samsung M34, Jio). Finding: genuine never flagged; v1 misses most clones.
- [x] Learned speakerphone channel (`learned_channel.py`) reproduces the real-call failure in simulation.
- [x] Retraining, model A (`s3://…/runs/ours_v3_rc`): real-call EER 24.6 % → 6.8 %, held-out speaker S02
      21.7 % → 8.7 %, clones caught 48 % → 75 %, genuine flagged 0 %. Details: `ml/realcall/FINDINGS.md`.
- [x] AWS quotas: most approved; justification replies sent on the two pending g5 cases.
- [x] Volunteers V01–V05 listed in `participants.yaml` (signed forms not yet saved, so the code still blocks them).

---

## 🔧 To do before 24 Oct, day by day

### Mon 20 Oct (evening): handover and access
- [ ] **G:** add Varun as a GitHub collaborator; merge this PR into `master`
- [ ] **G:** share keys with Varun **privately** (never in git): `.env` (Vobiz, Sarvam, Deepgram, OpenAI, HF,
      Cloudflare), the `ml/infra/pehchaan-ml` SSH key, `participants.yaml`, `config.yaml`, the consent files
      in `data/raw/`
- [ ] **G:** create an AWS IAM user for Varun (admin, MFA), or keep the AWS work on Galaba's laptop
- [ ] **V:** clone, set up (`HANDOVER.md` §6), run all tests green
- [ ] **G:** decide on the stopped GPU instance `i-0fa3f0f58693b173e` (600 GB disk ≈ $48/month; everything is
      in S3), then terminate it
- [ ] **G:** downgrade AWS Business Support+ to Basic if not needed (console, root)

### Tue 21 Oct: deployment and the live attack call
- [ ] **Deploy the backend** to AWS Mumbai (ap-south-1): one EC2 (c7i.large) with Docker Compose running the
      risk API, voice service (model v1 now; model A only if promoted) and Caddy; `api.humanslop.in`
- [ ] **Deploy the web demo** to S3 + CloudFront (or Cloudflare Pages); `demo.humanslop.in`, built with
      `VITE_API=https://api.humanslop.in`
- [ ] Health check from a phone on mobile data (not Wi-Fi)
- [ ] **Live attack call:** a Vobiz call to Phone A speaking a consented Varun clone (Sarvam clone, made with
      `python -m realcall.sarvam_clone` or the existing team clones). Script: "accident, send ₹50,000".
      Test 5 times.
- [ ] Decide Phone A and Phone B (the payer and the "real son"). Both charged, unlocked, notifications on.

### Wed 22 Oct: Family Verify on a real second phone, and evidence
- [ ] **Family Verify on Phone B:** the relative page `#/relative` opened on Phone B via
      `demo.humanslop.in`, updating live over WebSocket. Optional: a push or SMS link.
- [ ] **Payer flow on Phone A:** `#/payer` on Phone A (a web "DemoPay"). An Android shell reading real call
      state only if there's time.
- [ ] Full flow end to end on the deployed URLs, 3 times: T1 (clone → HOLD), L2 (real son → paid), T2, T3
- [ ] **D2 held-out handset test:** about 20 tape calls to Varun's Redmi, **answered by hand on speaker**
      (adb speaker doesn't work on the Redmi), then score v1 vs model A (`python -m realcall.compare_models`)
- [ ] **Live genuine calls:** volunteers V01–V05 sign `data/recording-kit/CONSENT_LIVE_CALLS.md` (or the
      cloning form if they agree to cloning), saved to `data/raw/consent/V0x.png`. Each makes 5–10 one-minute
      live calls (`python -m realcall.capture live …`). Aim for 50 live calls for the gate.
- [ ] Sarvam clone headline: tape calls with `sarvam_ivc` clones (a generator never trained on), scored the same way

### Thu 23 Oct: deck, rehearsal, backups, travel
- [ ] **Deck update** (`deck/slides.src.html`):
  - the real-call results table from `FINDINGS.md`
  - the learned-channel story
  - honest caveats: one handset, single seed, gate not met
  - the live-demo flow slide
  - the consent slide
- [ ] Decide: promote model A to the served API, or keep v1 in shadow mode. Model A needs a threshold and
      calibration pass on dev before promoting.
- [ ] **Record a backup video** of the full demo (screen recording + phone camera)
- [ ] Rehearse the 4-minute demo + pitch **3 times** with a timer; prepare answers to the "known weak spots" in
      `HANDOVER.md` §8
- [ ] Print or save offline: deck PDF, backup video, demo script, numbers sheet
- [ ] Top up the Vobiz balance; check that `calls.humanslop.in` runs off-laptop (deployed) or the tunnel runs as
      a Windows service
- [ ] Pack (see the final checklist) and travel to Delhi; book accommodation near IIT Delhi

---

## 🏁 On site: 24 Oct (09:00 – 19:00)

| Time | What | Notes |
|---|---|---|
| 09:00–11:00 | Arrive, register, orientation | Bring ID, team details |
| 11:00–12:00 | **Smoke test on venue network** | Phone A/B on mobile data; laptop on a phone hotspot if campus Wi-Fi blocks things; `api.`/`demo.` health; one T1 run |
| 12:00–13:00 | Lunch | |
| 13:00–16:00 | Polish: app copy, any judge or mentor feedback, deck tweaks | No new features. Only fixes. |
| 16:00–17:30 | Full rehearsal ×2 on venue network | Note anything flaky; switch to the backup video if needed |
| 17:30–19:00 | Mentor rounds and buffer; commit and push everything | Leave by 19:00 |
| Evening (hotel) | Light fixes only, rehearse the pitch out loud, sleep | No risky deploys at night |

## 🏁 On site: 25 Oct (09:00 – 19:00)

| Time | What | Notes |
|---|---|---|
| 09:00–10:00 | Re-check: deployment health, phones charged, Vobiz balance | |
| 10:00–12:00 | Final rehearsal ×2; freeze code and deck by 12:00 | After the freeze: no changes except fixing a broken demo |
| 12:00–13:00 | Lunch | |
| 13:00–19:00 | Judging / presentations (as scheduled) | Live demo first; backup video ready on the laptop |
| ~20:00 | Results | |

---

## 📋 Final checklist (tick on 23 Oct night, re-check 24 Oct morning)

**Product**
- [ ] `api.humanslop.in` and `demo.humanslop.in` live; checked from a phone on mobile data
- [ ] Live attack call works 3/3; T1 → HOLD and L2 → paid both work on the deployed system
- [ ] Family Verify works on Phone B over the internet (not localhost)
- [ ] Backup video of the full demo on the laptop **and** a phone (offline)

**Evidence**
- [ ] Deck numbers match `ml/realcall/FINDINGS.md` and `engine/results/deck_numbers.json`
- [ ] Real-call results slide with caveats; consent slide; disclosures updated
- [ ] D2 (held-out handset) and live-call numbers added if collected; otherwise stated as not yet done

**Safety and consent**
- [ ] A consent form is saved for every voice cloned or recorded (`data/raw/consent/`, `data/raw/recordings/`)
- [ ] Only consented voices in any demo; fictional names, banks and UPI IDs on all screens
- [ ] No keys or phone numbers in the repo or deck; `.env` only on the demo laptop

**Kit**
- [ ] Laptop + charger, Phone A + Phone B + chargers, USB data cables, power bank, extension board
- [ ] Mobile hotspot with data (campus Wi-Fi may block calls or ports)
- [ ] Vobiz balance topped up; AWS budget alert on; GPU instances stopped
- [ ] IDs, college ID cards, registration confirmation, hotel booking
- [ ] Repo: everything merged to `master`, pushed; `git status` clean on the demo laptop
