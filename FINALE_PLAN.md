# Pehchaan: finale plan (on site, 24–25 Oct 2026)

> **Record: the on-site plan written on 24 Oct 2026.** Its results are in `ml/realcall/FINDINGS.md` (on-site sections) and `RED_TEAM.md`; the current state is in `README.md`.

Written 24 Oct, 11:30 IST, against the **Round 2 judging rubric** (`Final Rubric.pdf`). Research behind it:
`reports/Pehchaan finale models and positioning.md`. Repo state at the start of on-site work:
`e6370a5` (declared at check-in) → `87602a9` (Varun's work from 20–23 Oct, labelled as pre-check-in) → on-site
commits from 24 Oct.

**Ground rules**
- Every slide and every Q&A answer keeps the split honest: declared base, pre-check-in work, on-site work. If the
  organisers have not approved the 20–23 Oct work, treat it as "rebuild on site" (the research report lists what).
- Every number on a slide traces to `ml/results/metrics.json`, `ml/realcall/FINDINGS.md` or
  `engine/results/deck_numbers.json`; never round in our favour; any new test gets a dated protocol note first.
- Consent rules unchanged: clone or record only consenting team members; fictional names on screens.
- GPU costs real money (g5.2xlarge ≈ $1.21/h): start it only when the run is ready, stop it when idle.

## Status, 24 Oct afternoon (branch `finale`)

| Done on site | Commit |
|---|---|
| A1 decode any format, A2 whole-clip window scoring, detector panel in the voice service | `9c7560a` |
| A3 detector bench `#/bench` (every detector side by side, fused verdict, CSV, failure cases) | `b82bc55` |
| D2 + C3: longer window for large amounts, split payments, Family Verify rate limit (SPEC v0.3) | `52d2b05` |
| B1 jury builds their own case on `#/demo` ("Your case") | `7a02ae7` |
| D1 red-team matrix run through the live pipeline, 16 attacks + 4 declared (`RED_TEAM.md`), and the four fixes it led to | `aa77d95` |
| Closing-demo tooling: `realcall.live_clone` consent / record / clone / purge | `ffffe65` |
| B2 voice hits → analyst Needs review (shadow only); C1 privacy panel from each case's records; no-audio-on-disk test | `db520cf` |
| C2 false-positive drill timers (payer: seconds to sent; analyst: seconds to outcome) | `845ba4e` |
| Deck: red-team slide, built-on-site + delivery slide (12 pitch pages); problem slide's numbers checked at source | `f711e97`, `5cbf770` |

| Next | Owner |
|---|---|
| A7 clone-vs-detect results (running on the laptop) → FINDINGS on-site section + `#/benchmark` page | Varun |
| Rehearse the live-clone closing demo with a teammate (commands in §2b) | Varun |
| Deploy: add an SSH rule for the venue IP to the `pehchaan-demo` security group, then `bash deploy/push.sh pehchaan-demo` | Varun |
| Open the next PR to Galabavamsi/pehchaan (`finale` is ahead of PR #4 with no conflicts) | Varun |
| D3 red-team round with mentors (use `RED_TEAM.md` and "Your case") | both |
| B4 Android app from `app/ANDROID_BRIEF.md` (now documents the v0.3 API behaviour) | Vamsi |
| F deployability slide; slide 10 refresh; the deck's simulator numbers are v0.2 (SPEC §4 note) unless `sim.py` is re-run with v0.3 | Varun |

---

## 1. What the new rubric rewards, and our move

### Stage 1: shortlist 30 → 10 (we must pass this first)

| Criterion | Weight | A "5" needs | Our gap today | Our move |
|---|---|---|---|---|
| 1. Working prototype | 25 | Runs live end to end **on inputs the judge picks**: input → detection → alert/action | Scenarios are buttons; voice upload is WAV-only | Jury control panel (§2 B1) + any-input detector bench (§2 A3) + the Android app (Vamsi) |
| 2. Spot-check results and measured accuracy | **30** | Gets most **kit samples** right; error rates incl. false positives on never-trained data; names failure cases | Service scores only the first 12 s, single window, WAV/FLAC/OGG only; no batch tool; no "failure cases" view | Workstream A: decode anything, score the whole clip in windows, batch bench, stronger fused model, fresh never-trained test, named failures |
| 3. Own engineering contribution | 15 | Substantial code written **during the finale** (fine-tuning, fused signals, custom pipeline); any member can explain it | Everything so far predates the finale | All of §2 is on-site code; each of us rehearses a 3-minute walkthrough of every part |
| 4. Alert and response flow, as built | 15 | A person sees a clear alert and acts; safeguards **running** (on-device processing, no raw data kept, human review) | Safeguards exist but aren't *shown* | Privacy proof panel, timed false-positive drill, analyst review in the demo (§2 C) |
| 5. Delivery against Round 1 plan | 15 | Built what the 48-hour plan promised, or cut deliberately and can say why | No delivery table | One slide: promised → delivered / cut + reason (§3) |

### Stage 2: final presentations

| Criterion | Weight | A "5" needs | Our move |
|---|---|---|---|
| 1. Problem and user | 20 | Specific user + threat scenario grounded in how Indian UPI fraud happens; how victims get hurt | Persona (Sunita, 58, son "Rahul" abroad) + the four primary numbers from the research report |
| 2. Deployability and scale | 15 | Concrete path into a bank/UPI app/law enforcement; who runs it, what it costs, what a pilot needs | One slide: owner, integration, cost per assessment, pilot shape, rules already in force (§2 F) |
| 3. Communication and Q&A | 10 | Clear, on time, direct, including "we don't know" | Q&A sheet, 3 timed rehearsals |
| 4. Live user journey | 25 | Works live on a realistic scenario **the jury can vary**; attack → alert → action → review/report | Jury control panel + real call + two real phones; never a video unless live fails |
| 5. Adversarial robustness | 20 | Shows how an attacker would evade it, what it misses, what we'd change | Red-team matrix + 2 cheap mitigations built on site + a live red-team round (§2 D) |
| 6. Responsible AI and mistakes | 10 | A genuine user flagged by mistake gets through, and how fast; alert says why; privacy running | Timed false-positive drill; reasons on every alert; privacy panel (§2 C) |

**Decision we recommend (no SPEC change needed):** voice stays out of money decisions (G2, shadow mode), but a
"likely synthetic" score raises an **analyst review alert** in the console. That gives Stage 1 a real
input → detection → alert → human action path, without accusing the payer (G6) or holding money on a clue.

---

## 2. Workstreams, in order of score per hour

### A. Spot-check kit readiness (Stage 1 #2, 30 points). Owner: Varun now, GPU part with Galaba

| # | Task | Est. | Done when |
|---|---|---|---|
| A1 | **Decode anything:** ffmpeg fallback in `ml/serve/app.py` (mp3, m4a/aac, opus, webm, wav, stereo, any rate) → mono 16 kHz; web upload accepts `audio/*` | 1 h | A test feeds one file of each format |
| A2 | **Score the whole clip:** VAD, 4 s windows with 2 s hop, aggregate log-odds (mean and max reported); return the per-window timeline. Keep the quality gate (G3) | 1.5 h | A 40 s clip returns ~19 windows and one call-level score |
| A3 | **Detector bench `#/bench`:** drag in one or many files or record from the mic → per file: verdict, calibrated p, quality, window chart, model, latency; batch table; optional labels → accuracy and false-positive rate; CSV export; a "known failure cases" box | 2.5 h | A judge drops a folder and sees a table plus summary |
| A4 | **Stronger model (GPU):** (1) fuse v1 + model A + NII MMS-300M by z-normalised average, weights fitted on dev only; (2) if time, re-initialise from AntiDeepfake MMS-300M with the model A recipe. Promote only if it beats model A on dev; report test as it lands | 2–5 GPU h | `metrics.json` / FINDINGS updated, single seed stated |
| A5 | **Fresh never-trained test (on site):** dated protocol note first; new clones from generators absent from training (stock voices, or consenting team voices only) + fresh genuine speech (consenting people, and public CC data not in training); score with the served model | 2 h, evening | FINDINGS on-site section: EER, false-positive rate, n, Wilson CI, failure cases |
| A6 | **Threshold and failure cases:** a single decision threshold from dev for kit verdicts; failure list on the bench (short clips, unseen commercial cloners, music/noise, heavy phone codecs) | 0.5 h | Bench shows threshold and failure list |
| A7 | **Clone-vs-detect benchmark** (method from ClonEval, arXiv:2504.20581): for every cloner in our consented corpus, *how convincing* = cosine similarity of WavLM speaker embeddings (`microsoft/wavlm-base-plus-sv`, 16 kHz) between the clone and the real speaker; *how detectable* = catch rate and false-positive rate for **every detector side by side** (off-the-shelf XLS-R+AASIST, NII MMS-300M, ours v1, ours A, fused), clean and phone conditions, held-out cloners marked. Outputs: a leaderboard table, a scatter (similarity vs. catch rate, one dot per cloner per detector), and on `#/bench` every model scoring the judge's file in parallel | 3 h (CPU, laptop) | `ml/results/clone_vs_detect.json` + bench page; numbers in FINDINGS on-site section |

### B. Live end-to-end journey (Stage 1 #1 = 25, Stage 2 #4 = 25)

| # | Task | Owner | Est. |
|---|---|---|---|
| B1 | **Jury control panel** on `#/demo`: amount, caller (saved / unknown / international / 1600), call state (on call / ended N min ago), claim, payee name, relative's answer (yes / no / no reply). Builds a case live instead of a fixed scenario | Varun | 2 h |
| B2 | **Voice into the case:** any bench file or live mic clip can be attached to the current case → voice check → analyst review alert (shadow for money decisions) | Varun | 1 h |
| B3 | **Live attack call** from the laptop to Phone A (declared Vobiz tape dialer; consented clone lines), then the payment flow on Phone A and Family Verify on Phone B | Varun + Vamsi | 1 h rehearsal |
| B4 | **Android app** (Capacitor shell + Kotlin plugins: real call state, on-device contact check, Family Verify notification, `upi://` handoff, relative's key in Android Keystore). Plan: `app/MOBILE_PLAN.md` | **Vamsi** | rest of day 1 |

### C. Alert, response and safeguards running (Stage 1 #4 = 15, Stage 2 #6 = 10). Owner: Varun

| # | Task | Est. |
|---|---|---|
| C1 | **Privacy proof panel** in the console: audio scored in memory and dropped (`audio_retained: false`, plus a test that no audio file is written), contacts matched on device (app), every analyst access logged (exists), holds released only by a human or a positive check | 1 h |
| C2 | **Timed false-positive drill:** genuine son → "Yes, it's me" → paid; relative doesn't answer → callback / safe word → released; analyst release. Show the seconds on screen | 1 h |
| C3 | **Family Verify rate limit** (per payer and per relative) and a waiting period for newly enrolled relative devices | 1 h |

### D. Adversarial robustness (Stage 2 #5 = 20)

| # | Task | Owner | Est. |
|---|---|---|---|
| D1 | **Red-team matrix** (~12 rows: evasion → what happens today → what it misses → what we'd change): coached "no one", split payments under ₹10k, waiting past the 10-min window, WhatsApp call, scammer adds themselves to the family circle, SIM-swapped relative, spam Family Verify, new cloner beats the detector, screen-share/remote app, spoofed 1600 number, attacker coaches the real relative, payer pays from another app | Varun | 1 h |
| D2 | **Two mitigations built on site:** (1) cumulative amount across payments during one call (defeats splitting under ₹10k); (2) longer post-call window for large amounts. SPEC first, LRs tagged "assumed" | Varun | 1.5 h |
| D3 | **Live red-team round** with mentors at the 17:30 slot; log every attempt and outcome | both | 30 min |

### E. Delivery against the Round 1 plan (Stage 1 #5 = 15). Owner: Varun (slide)

| Round 1 promise (slide 10) | Status to report |
|---|---|
| Android shell reading real call state and VoIP mode | On site (B4) |
| Live attack line: Vapi/Bolna agent in a consented cloned voice; streaming voice + cue check | Vobiz call with a consented clone (deterministic, no third-party agent); **cut:** live voice agent and streaming ASR cues (privacy and time; tap checklist instead) |
| Family Verify on a second real phone (push + signed challenge) | On site (web + app notification) |
| Bank "are we calling you?" registry on Amazon Connect | Mocked registry endpoint; **cut:** Amazon Connect (cost and time); integration contract shown |
| 100+ consented calls → retrain → before/after + one brand-new generator | Declared: retrain 24.6% → 6.8% EER on real calls; fresh never-trained test on site (A5) |
| Comprehension test, 5 volunteers | On site (evening or morning) |
| Metrics dashboard, offline fallback, backup video, rehearsal ×3 | Bench + console; laptop-only fallback; video; rehearsals |

### F. Deployability and scale (Stage 2 #2 = 15). Owner: Varun (slide)
Owner: the bank's or TPAP's fraud-risk team. Integration: SDK in the app + risk API in the bank's VPC (ap-south-1).
Cost: risk assessment is CPU-only and milliseconds per call; voice is optional (show estimates labelled as estimates).
Pilot: one bank or TPAP, opted-in users 60+ and their families, 2–3 months shadow first, then PAUSE, then HOLD.
Legal basis already in force: RBI Authentication Directions 2025 (risk-based extra checks) and the 2026 digital
payment security controls; RBI's April 2026 APP paper as upside. Law-enforcement output: NCRP / 1930 / Chakshu pre-fill.

### G–H. Problem slide, communication
Persona + the four primary numbers (research report §"Four primary numbers"), drop the "76×" ratio, add them to
`deck_numbers.json` with sources (note: `sim.py` rewrites that file; add after the final simulator run).
Q&A sheet with honest "we don't know" answers; three timed rehearsals.

---

## 2b. Closing demo: clone a consenting judge, live (optional, high impact)

The judge reads a short passage, we clone their voice in front of them, a call in their cloned voice asks for money,
and Pehchaan still stops the payment because it asks the real "son's" phone.

| Step | Time |
|---|---|
| Judge reads the consent summary and signs the cloning consent form (photo saved as evidence, registered as a participant, e.g. `J01`) | 1 min |
| Record 30–60 s of the judge reading a set passage on the laptop mic (Sarvam needs only ~10 s; extra lets us pick the cleanest 10–15 s) | 1 min |
| Create the cloned voice (Sarvam instant cloning API) and synthesise a 15 s scam line | ~10–20 s |
| Show the **ClonEval similarity** of the clone to their real voice, and **every detector's score in parallel** | ~10 s |
| Place the call to **Phone A** (a team phone) and play it on speaker | ~30 s |
| Pay → "Who asked?" → Family Verify on Phone B → "Not me" → HOLD | ~30 s |
| **Delete the cloned voice and the recording on screen** (`sarvam_clone --delete-voices`, then remove the files) | 10 s |

Total ≈ **3 minutes**. For comparison, ElevenLabs instant cloning needs ≥ 10 s (1–2 min recommended); Sarvam's own
flow records ~10 s. Both require the speaker's consent.

**Non-negotiable rules** (CLAUDE.md consent rules, and they're also good theatre):
- Only with the judge's **explicit, signed** consent, registered before any cloning (`consent.py` refuses otherwise).
  If they hesitate, use a teammate's consented clone instead; never pressure.
- The call goes **only to a team phone** (or the judge's own phone if they ask). **Never call the judge's real family**
  or anyone who hasn't agreed; "show how your family could be cheated" is shown on our phones, not on theirs.
- The script is role-play; nothing is kept: delete the voice at Sarvam and the recording right after, on screen.
- Rehearse it twice with a teammate first; fallback = the pre-made consented clone.

**Commands** (laptop, from `ml/`; the Sarvam key never leaves the laptop; calls need `pehchaan-calls` and
`pehchaan-tunnel` running):
```bash
python -m realcall.live_clone consent J01 --form ~/Pictures/J01_form.jpg   # refuses without the form photo
python -m realcall.live_clone record J01 --seconds 40                      # prints a neutral passage to read
python -m realcall.live_clone clone J01 --lang hi --say "Mummy, main hoon. Accident ho gaya, phone police ke paas hai. Papa ko mat batana, abhi ₹50,000 is account mein bhejo."
python -m realcall.dial attack --device A --speaker J01 --clip <clip printed by clone>
python -m realcall.live_clone purge J01                                    # on screen: voice at Sarvam + every file
```
`clone` prints the time taken and the ClonEval similarity to their real voice; drop the clip and `ref.wav` into
`#/bench` for every detector's verdict. `purge` also withdraws the consent; only the signed form is kept.

## 3. Timeline

| When | Varun | Vamsi | GPU |
|---|---|---|---|
| **24 Oct, now → 13:00** | A1, A2 (decode + windows) | Android Studio, Capacitor shell on both phones | Decide; if yes, start the fusion scoring run |
| **13:00 → 16:00** | A3 bench, B1 jury panel, B2 | B4: call state + contact check → risk API | Fusion / re-init run |
| **16:00 → 17:30** | C1–C3, D2; first full run on phones | B4: Family Verify notification | Score on dev |
| **17:30 → 19:00** | D3 red-team round, B3 live call rehearsal | integrate app with the demo | Stop GPU if idle |
| **Evening (hotel)** | A5 fresh test, D1 matrix, E/F/G slides | B4: `upi://` handoff, polish | Overnight run only if worth it |
| **25 Oct 09:00 → 12:00** | Deck rebuilt, backup video, rehearsals ×2, freeze 12:00 | App freeze, rehearsals | Stopped |

Ask the organisers early **when the Stage 1 spot-check happens**: if it's on day 1, A1–A3 come before everything else.

**Cut order if behind:** A4 re-init run → D2 second mitigation → `upi://` handoff → A5 new-cloner part.
**Never cut:** A1–A3 (kit), B1 + B3 (live journey), C2 (false-positive drill), the delivery table, backup video.

## 4. Decisions for the team
1. Voice alerts go to analyst review only (recommended above), or voice may also raise PAUSE for the payer (needs a SPEC change and conflicts with G6 copy rules)?
2. GPU: start the A10G for A4 (≈ $1.21/h, budget ~$10)?
3. ~~Laptop or server~~ **Decided 24 Oct: the live demo runs on the server** (`demo.` / `api.humanslop.in`). Running
   all detectors in parallel there needs more memory than the 4 GB box (v1 alone settles at ~1 GB): either upsize
   (e.g. c7i.2xlarge, 16 GB) or run the multi-model bench on the laptop and keep the server on the fused model.
4. Push: this rewritten history goes to a **new** branch on your fork (no force-push needed); delete the old `finale-prep` branch there later if you want.
