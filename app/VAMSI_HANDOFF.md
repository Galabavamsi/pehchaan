# Vamsi: handoff for the night of 24 → 25 Oct

Written 24 Oct, 23:45 IST, by Varun. Branch: **`finale`** on `VARUN3WARE/pehchaan` (commit `b6f921c` or later).
Your `app-android` branch is merged into it. The live API (`api.humanslop.in`) and web demo (`demo.humanslop.in`) are
redeployed from it.

## The day, per the official agenda

| When (25 Oct) | What | What it means for us |
|---|---|---|
| Tonight | Get the merged app on both phones, run the test matrix, record the backup video | Everything below |
| 08:00–09:00 | Day 2 reporting | Phones charged, both apps on the merged build |
| **09:00–11:00** | **Code freeze and verification (plagiarism check)** | Nothing is committed after 09:00. Push your last commit by **08:30**. Each of us must explain our own code (see "Be ready to explain") |
| 11:00–14:00 | Preliminary judging (Stage 1: working prototype 25, **kit spot-check 30**, own engineering 15, alert and response 15, delivery vs plan 15) | Your app is the "working prototype" and the "on-device safeguards" |
| 15:00–16:30 | Grand jury final presentations (Stage 2: live user journey 25, adversarial 20, problem 20, deployability 15, communication 10, responsible AI 10) | Live demo on the two phones |

## 1. What changed around your code in the merge

Your 11 commits are in, unchanged except where they met our changes from the same day:

- **`PayerPhone.tsx`** (DemoPay pays through it):
  - Inside the app, the phone's own call is sent, exactly as you wrote it, with rehearsal mode respected.
  - On the web, the scenario's call is sent, with its duration kept live.
  - The time from Pay to "sent" is measured and shown on the sent screen. This is our false-positive drill: a genuine payer gets through in N seconds.
  - The call pill shows ended calls too ("call ended N min ago").
  - The "Who asked?" subtitle follows the real call's state: "during a call" while active, "soon after a call" once ended.
- **`i18n.ts`:** all your new strings are kept. Your merged "during or just after a call" line was replaced by the two separate lines above.
- **Theme:** the whole web demo moved to a blue palette with bolder graphics. DemoPay picks it up; it renders correctly, but check it on the phones.
- **Server, SPEC v0.3.** Your app meets these through `PayerPhone`, so no code is needed. Know them, because judges will poke at them:
  - **Payments count once confirmed.** An assessment without a case returns a `payment_ref`, and the PIN screen confirms it (`POST /v1/payments/{ref}/sent`).
  - **Split payments add up.** Payments made during one call are summed, so ₹9,000 + ₹9,000 to a payee first paid during the call can't stay silently green.
  - **Large amounts:** at ₹50k or more, the "after the call" window is 60 minutes.
  - **A circle member's saved number** calling still gets the "Who asked?" question.
  - **Family Verify rate limit:** 3 per payer and 5 per relative per hour. The 4th answers `429 "Too many Family Verify requests in the last hour. Call <name> on their saved number instead."`, which shows as an error line, not a crash.
  - **Device re-binding:** refused (`409`) while a Family Verify challenge is pending for that relative. Don't reinstall or re-register a phone in the middle of a run.
  - **Voice hits:** go to the analyst as "Needs review", never into the payer's decision (shadow mode, G2).
- **Your second payer, Rahul (`u_rahul`):** it's on the live API now. The server seeds people only on a fresh database or when a scenario is loaded, so I loaded T1 once at 23:40. Loading any scenario from the demo page reseeds people and **keeps registered devices**.

## 2. Get the merged app on both phones (pick one)

**A. Build on your machine (recommended: keeps your signing key, no uninstall)**
```bash
git fetch https://github.com/VARUN3WARE/pehchaan.git finale && git checkout FETCH_HEAD   # or add the remote
cd app/web && npm ci && VITE_API=https://api.humanslop.in npm run build && npx cap sync android   # Node >= 22
# then Android Studio: open app/android, Run on each phone (or: cd app/android && ./gradlew installDebug)
```

**B. Use the APK built on Varun's laptop:** `app/android/app/build/outputs/apk/debug/app-debug.apk`. It's signed with Varun's debug key, so the phone must uninstall your build first. Uninstalling wipes the app's data, including the device's Family Verify registration.
```bash
adb uninstall in.humanslop.demopay && adb install app-debug.apk
```
Then run Setup again on each phone, while no Family Verify challenge is pending. Otherwise the 409 above blocks re-registration.

## 3. Test matrix on the live API (both phones, mobile data, not Wi-Fi)

Note pass/fail and the seconds for each, and send them to Varun. They go into FINDINGS ("Live system checks") and onto the slides.

| # | Run | Expected |
|---|---|---|
| 1 | **T1:** the attack call reaches Phone A (Varun dials it), then Pay ₹50,000 to a new payee → "Who asked?" → Family → Rahul | Family Verify notification on Phone B, **even with the screen locked** → "No, that's not me" → **HOLD** (red) → the case and evidence pack in the console |
| 2 | **L2:** the real Rahul calls → the same payment → "Yes, it's me" | Paid; the sent screen shows the seconds it took |
| 3 | During one call, ₹9,000 then ₹9,000 to the same new payee | The second payment is not silently green |
| 4 | Hang up, then pay ₹60,000 to a new payee within the hour | Still asked, with the "soon after a call" subtitle |
| 5 | The caller is Rahul's saved number; pay a new payee during that call | The question is still asked |
| 6 | Four Family Verify requests within an hour from one payer | The 4th isn't sent; a toast says "Call Rahul on their saved number instead" |
| 7 | Rehearsal mode on | Saved callers are treated as unknown, and the screens say rehearsal mode is on |
| 8 | Mobile data off and on while waiting for Family Verify | Recovers (your retries) |
| 9 | Screenshot on the PIN screen | Blocked (FLAG_SECURE) |
| 10 | Projector check | Real numbers are masked on every screen |

## 4. Backup video (on the "never cut" list)
3–4 minutes. A screen recording of the laptop console, plus a phone camera on both phones:
1. T1 from the attack call to HOLD and the evidence pack.
2. L2 from "Yes, it's me" to paid.

Save it on the laptop **and** on a phone, offline. Make it tonight once runs 1 and 2 pass.

## 5. Be ready to explain (09:00 verification, and Stage 1 "any member can walk a judge through it")
Three minutes on each. Explain your own code from the code itself, not from slides.
- **Your Android SDK:**
  - how the call state is read, and what happens with VoIP calls;
  - what the contact check sends (only "saved: yes/no", never the contacts);
  - how Family Verify reaches the locked phone;
  - FLAG_SECURE, rehearsal mode, number masking;
  - what leaves the phone (the "What left this phone" panel).
- **The risk engine (Varun's, know the shape):**
  - the trigger fires on a payment during or just after a call to a new or unusual payee;
  - "Who asked?" → a claim-specific out-of-band check (Family Verify, the bank's 1600 registry, a safe word) → explainable log-odds with guardrails G1–G7 → GO / PAUSE / HOLD, with a human release path;
  - voice never holds money.
- **The detector:**
  - shadow mode;
  - real calls 24.6% → 6.8% EER after retraining on real calls;
  - what it still misses: Sarvam clones of a speaker it never saw;
  - the overnight run (v5) tests whether many-speaker data or the NII backbone fixes that, and the result is reported whichever way it lands.
- **The attack call:** a Vobiz two-way stream. The cloned "son" (consented voice only) hears her, transcribes her, and replies through the clone. Since tonight it also speaks the moment she answers, fills the wait with short fillers instead of silence, and drops the rest of a reply when she talks over him. It's never recorded.

## 6. Two answers I need from you (for the delivery slide)
1. Is the **`upi://` handoff to the user's own UPI app** built, or does DemoPay only open `upi:` links and QR codes itself? Slide 10 promised the handoff. If it isn't built, we say "cut, and why".
2. Can you run the **comprehension test**? It's a Round 1 promise, still not done. 5 people, 2 minutes each, on the Pause & Verify screen: time to decide, and "why did it stop you?". Consent first, no recording, only the answers noted. If you can't do it by 08:30, we mark it cut.

## 7. Rules (unchanged)
- Consented voices only; fictional names, banks and UPI IDs on every screen.
- Keys only in the repo-root `.env`, never in the APK or a commit. `VITE_API` is a URL, not a key.
- No new features tonight: fixes only. Nothing after 09:00.
- Commit with your own git identity, push to your branch or open a PR into `finale` by 08:30, and tell Varun.
