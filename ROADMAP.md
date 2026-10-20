# Pehchaan: status and roadmap to the finale (updated 20 Oct 2026, 19:15 IST)

`TASKS.md` is still the master checklist. This file is a **verified snapshot**: what works right now, and what's
left, in order. Finale: IIT Delhi, 24–25 Oct.

Legend: ✅ done and checked · 🟡 partly done · ❌ not started · ⏸ deliberately deferred

---

## 1. Where we are

| Piece | State | Evidence |
|---|---|---|
| Spec, engine + simulator, risk API, React demo | ✅ | Tests: engine 85, API 27, realcall 9 (`.venv`, Python 3.12) |
| **Live demo on the internet** | ✅ | `https://demo.humanslop.in` + `https://api.humanslop.in` (EC2 `pehchaan-demo`, Caddy TLS). See `deploy/README.md` |
| **Full live run on real phones** | ✅ | 20 Oct 19:01: clone call rang Phone A → Pay → "Rahul" → auto Family Verify on Phone B → "not me" → **Red hold (G7) 14 s after Pay** → Cancel and report. L2, T2, T3 also run on the phones |
| Live attack call (`dial attack`, Sarvam clone of S02) | 🟡 | **2 of 5** test calls done, both clean (answered, 17 s clip played, normal hangup) |
| Voice detector v1 | ✅ served (shadow) | Real scores on the server; ~3.1 s per 10 s clip on 2 vCPU (laptop 1.1 s; SPEC budget 1.5 s) |
| Model A (real-call EER 24.6 % → 6.8 %) | 🟡 | Reproduced on this laptop; weights in S3; not served (doesn't need to be: voice is shadow-only) |
| D2 held-out handset test | ❌ | ~7 calls so far; needs ~20 more |
| Sarvam held-out-generator tapes | ❌ | Sarvam voice for S02 exists now; no tape calls yet |
| Live genuine calls → the gate | ⏸ | Waiting on volunteer consent screenshots (Varun's call, 20 Oct). Code blocks V01–V05 until then |
| Deck (Round 1, 23 slides) | ❌ | No real-call results, consent or live-demo slide yet |
| Backup video, rehearsal | ❌ | |
| Git | ❌ | **Nothing from 20 Oct is committed yet** |

---

## 2. Left today: data tasks (do these while both phones are here)

Run everything from `ml/` with the venv (`../.venv/bin/python`). The call server and tunnel must be running
(`calls.humanslop.in/healthz`). Phone A = D2 = Varun's Redmi: **answer by hand and tap Speaker** (adb can't).

### D1. Attack calls 3–5 (≈ 3 min) 🟡
```bash
python -m realcall.dial attack --device A --speaker S02 --clip realcall/work/src/attack/t1_S02.wav --n 3
```
Answer each one. Done when 5/5 played cleanly.

### D2. Make the Sarvam clones first (≈ 10 min, uses Sarvam credits) ❌
Sarvam is a generator no model was trained on (`sarvam_ivc`, test-only in `protocol.py`). Cloning every scripted
line for S01 and S02 *before* the D2 calls means one session tests a held-out handset **and** a held-out generator.
```bash
python -m realcall.sarvam_clone --speakers S01 S02
```
Check that `realcall/work/src/clone/sarvam_ivc/` fills up, then `python -m realcall.dial check` (tape sources).

### D3. D2 held-out handset session: ~20 tape calls (≈ 45 min) ❌
Set-up: Redmi **5 cm from the laptop mic**, full volume, quiet room, plugged in, screen on.
```bash
python -m realcall.capture session --device D2 --seconds 3600
```
```bash
python -m realcall.dial tape --device D2 --n 20
```
- Run the two commands in separate terminals.
- Each tape waits 6 s after you answer: **tap Speaker before the start chirp**.
- After the first call, run `python -m realcall.ingest` once and check QC is "ok" before doing the other 19.

### D4. Score D2 with v1 and model A, on the laptop CPU (≈ 30 min) ❌
- Download model A (1.26 GB): `aws s3 cp s3://pehchaan-ml-301745146083-use1/runs/ours_v3_rc/best.pt …`
- `python -m realcall.ingest`, then score the new real-call rows with v1 and model A (`eval/score.py`,
  `ckpt:` detector) into `realcall/work/retrain_v3/scores/real__ours_v1.csv` / `real__ours_v3_rc.csv`, and run
  `python -m realcall.compare_models`. **Claude scripts this step once the calls are in.**
- Write the result into `ml/realcall/FINDINGS.md` with the date. The deck quotes only from there.
- Protocol: D2 and `sarvam_ivc` are pre-registered test-only. No threshold changes after seeing these numbers.

### D5. Live genuine calls → the gate ⏸
Deferred until the WhatsApp consent screenshots are saved as `data/raw/consent/V0x.png`. Then each volunteer
makes 5–10 one-minute calls (`python -m realcall.capture live --device D2 --caller V0x --route cellular`).
Target ≥ 50. **If not done by 23 Oct, the deck says "gate not yet met"**, and voice stays in shadow mode either way.

### D6. Small checks
- [ ] Confirm one run with both phones **on mobile data, not Wi-Fi** (the venue may have no usable Wi-Fi)
- [ ] Listen to `t1_S02.wav` on the projector speakers once (volume, clarity)

---

## 3. Left this week

### Before anything else
- [ ] **Commit and push** today's work (deploy files, attack mode, docs). Nothing is committed yet
- [ ] Run the tunnel + call server as a background service (they currently live inside a Claude session)
- [ ] Decide on voice latency: c7i.xlarge (~+$2.5/day) roughly halves 3.1 s; or leave it (voice never decides)

### Wed 22 Oct
- [ ] Finish D2–D4 if not done tonight; update `FINDINGS.md`
- [ ] Full run ×3 with the attack call, both phones on mobile data; note every glitch, fix only blockers
- [ ] Optional: 5-person hallway test of the Pause & Verify screen (SPEC §8 V3): time to decide + "did you
      understand why?"

### Thu 23 Oct
- [ ] **Deck** (`deck/slides.src.html`): real-call table + learned channel (`FINDINGS.md`), D2/Sarvam numbers if
      collected, caveats (one carrier, single seed, gate not met), consent slide, live-demo flow slide,
      deployed latency (3.1 s on 2 vCPU, not the laptop's 0.98 s). Every number traced to its source file
- [ ] **Backup video** of the full run (screen recording + phone camera), on the laptop **and** a phone
- [ ] Rehearse the 4-min demo + pitch **3×** with a timer; answers to `HANDOVER.md` §8
- [ ] Vobiz top-up; GPU box stopped; `git status` clean; pack (both phones + chargers, hotspot); travel

### 24–25 Oct: on site
Follow `TASKS.md`: smoke test on the venue network first, no new features, freeze 25 Oct 12:00.

### After the finale
- [ ] Stop `pehchaan-demo` (and release its Elastic IP when no longer needed); delete the Sarvam voices
      (`python -m realcall.sarvam_clone --delete-voices`); data deletion by 31 Dec 2026 as promised in the consent forms

---

## 4. Cut list (drop from the top if behind)
1. Hallway test
2. Sarvam headline tapes (D2 of §2)
3. Model A scoring of D2 (keep v1-only numbers, say so)
4. D2 handset test (slide says "not yet done")
5. Live genuine calls (slide says "gate not yet met")

**Never cut:** the live demo URLs, Family Verify on a real Phone B, the attack call (or its recording in the backup
video), the real-call slide with caveats, consent evidence for every voice used.

## 5. Decided on 20 Oct
- Phone A = Varun's Redmi (registered as device `A`, same handset as D2); Phone B = Paritosh for rehearsals
  (web page only: not recorded, not cloned).
- Live call = prerecorded consented Sarvam clone of S02 via Vobiz (`dial attack`), not a live voice agent.
- Volunteers V01–V05: recording-only consent by WhatsApp reply (`clone: false`); screenshots added later.
- Deployed voice service = real v1 on CPU, shadow mode.

## 6. Running right now (Varun's laptop)
- Real-call server (`python -m realcall.server`, port 8600) and `cloudflared tunnel run pehchaan`: started from this
  Claude session, so they stop when it ends. Only one machine may run the tunnel.
- Demo server `pehchaan-demo` (3.109.40.69): Caddy + API + voice, `restart: unless-stopped`.
