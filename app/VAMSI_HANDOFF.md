# Vamsi: end-to-end handover of the app (night of 24 → 25 Oct)

From now until the **09:00 code freeze** you own the app end to end: build, quality gate, both phones, live
tests on the deployed system, the backup video, and the report back. Varun owns the detector results (the overnight
v5 run), the deck and the pitch. Ask Varun before changing anything outside `app/android`, `app/web` or this file.

Branch: **`finale`** on `VARUN3WARE/pehchaan` (commit `2aff0c8` or later). Your `app-android` branch is merged into
it, and `api.humanslop.in` / `demo.humanslop.in` already run the merged code.

## 0. Deadlines (official agenda, 25 Oct)

| Time | Session | What you must have done |
|---|---|---|
| **07:00** | (us) | Report back (§9) with the quality gate and the test matrix filled in |
| 08:00–09:00 | Day 2 reporting | Both phones charged, on the merged build, set up (§6) |
| **09:00–11:00** | **Code freeze and verification (plagiarism check)** | Last commit pushed by **08:30**. Be able to explain your code (§11) |
| 11:00–14:00 | Preliminary judging (Stage 1) | Working prototype (25), alert and response with safeguards running (15), delivery vs plan (15) |
| 15:00–16:30 | Grand jury presentations (Stage 2) | The live user journey on the two phones (25) |

## 1. Get the code

```bash
git fetch https://github.com/VARUN3WARE/pehchaan.git finale
git checkout -B finale FETCH_HEAD
git log --oneline -3          # must include "Merge Vamsi's Android app (upstream/app-android) into finale"
```
Commit your fixes on top of `finale` and push them to your fork (or open a PR into `VARUN3WARE:finale`). Tell Varun
the commit id. Don't rewrite history and don't commit to `master`.

## 2. Toolchain (versions the build needs)

| Tool | Version | Note |
|---|---|---|
| Node | **≥ 22** | Capacitor CLI 8.5.3 refuses Node 20 for `cap sync` (the web build itself runs on 20) |
| JDK | **21** | Android Studio's bundled JBR is fine (`JAVA_HOME=<android-studio>/jbr`); JDK 11 fails with AGP 8.13 |
| Android SDK | platform **36**, build-tools **36** | compile/target 36, min 24 |
| Gradle / AGP / Kotlin | 8.14.3 (wrapper) / 8.13.0 / 2.2.20 | downloaded by the wrapper on first build |
| Python | 3.11+ venv | only for the quality gate (§5). Setup: `HANDOVER.md` §6 |

## 2b. Demo change: the scam pays the CALLER's own number (25 Oct)

The live attack call now does what the real "cloned relative" scam does: when the payer asks *where* to send the
money, the cloned son says **"send it to this same number I'm calling from, on any UPI app"** — not a separate UPI ID.
This is cleaner for the demo and ties three things together: the number on the payer's phone, the payee they pay, and
the person Family Verify checks.

What this needs on the app side (please align DemoPay for the T1 run):
- In the T1 / attack flow, the **payee is the caller's number** (a UPI number payee, e.g. `+91XXXXXXXXXX@upi` style or a
  "pay to mobile number" entry), shown as a **new payee** so the trigger fires. Keep it fictional on screen.
- So the on-screen story reads: caller's number rings → the son says "pay this number" → the payer starts a payment
  **to that same number** → Pehchaan asks "who asked you to pay?" → Family → the real relative's phone → "not me" →
  HOLD. The number paid, the number that called, and the verified person are all the one contact.
- The genuine path (L2) is unchanged: the real relative says "yes, it's me" → paid.
- If wiring the caller's number as the payee is fiddly before the freeze, keep the existing fictional payee for the app
  and let the **call audio** carry the "pay this number" line — the defense (claim → verify → HOLD) is identical either
  way. Tell Varun which you did so the narration matches.

The live-call side is already done (`ml/realcall/agent.py` `ScriptCard.pay_to_caller`, default on); this section is only
about keeping DemoPay's payee consistent with it.

## 3. What changed around your code in the merge

Your 11 commits are in, unchanged except where they met our changes from the same day:
- **`PayerPhone.tsx`** (DemoPay pays through it):
  - Inside the app, the phone's own call is sent, exactly as you wrote it, with rehearsal mode respected.
  - On the web, the scenario's call is sent, with its duration kept live.
  - The seconds from Pay to "sent" are shown on the sent screen (our false-positive drill).
  - The call pill also shows ended calls.
  - The "Who asked?" subtitle follows the real call's state: "during a call" while active, "soon after a call" once ended.
- **`i18n.ts`:** all your strings are kept. Your combined "during or just after a call" line became the two lines above.
- **Theme:** blue palette with bolder graphics; DemoPay picks it up.
- **Server (SPEC v0.3).** Your app meets these through `PayerPhone`, so no code is needed. Know them, because judges probe them:
  - **Payments count once confirmed.** An assessment without a case returns a `payment_ref`, and the PIN screen confirms it (`POST /v1/payments/{ref}/sent`).
  - **Split payments add up.** Payments to a payee first paid during this call are summed.
  - **Large amounts:** at ₹50k or more, the "after the call" window is 60 minutes.
  - **A circle member's saved number** calling still gets the "Who asked?" question.
  - **Family Verify rate limit:** 3 per payer and 5 per relative per hour. Past that, nothing is sent; the payer sees a toast: "Call <name> on their saved number instead".
  - **Device re-binding:** refused (`409`) while a Family Verify challenge is pending for that relative.
  - **Voice hits:** go to the analyst as "Needs review", never into the payer's decision (G2).
- **The second payer, Rahul (`u_rahul`):** it's live. The server seeds people only on a fresh database or when a scenario is loaded. Loading any scenario from `#/demo` reseeds people and **keeps registered devices**.

## 4. Build and install

```bash
cd app/web && npm ci
VITE_API=https://api.humanslop.in npm run build        # the API URL is baked in at build time; it is not a key
npx cap sync android                                    # Node >= 22
cd ../android && ./gradlew assembleDebug                # or Run from Android Studio
adb -s <serial> install -r app/build/outputs/apk/debug/app-debug.apk    # once per phone (adb devices for serials)
```
- **Signing:** your build keeps your debug key, so `install -r` upgrades in place and keeps each phone's setup and Family Verify keys. Installing a build signed by another machine needs `adb uninstall in.humanslop.demopay` first. That wipes the app's data, so run Setup again (§6), and only while no Family Verify challenge is pending (409).
- **Is it the merged build?** Three signs:
  - DemoPay's home has the navy "Scan QR" card.
  - "Who asked?" says "during a call" on an active call and "soon after a call" after hanging up.
  - The sent screen shows the seconds it took.

## 5. Quality gate (all must pass before you install for the night)

| # | Check | Command (from the repo root unless noted) | Pass |
|---|---|---|---|
| Q1 | Engine | `cd engine && python -m pytest -q` | 87 passed |
| Q2 | Risk API | `cd app/server && python -m pytest -q` then `git checkout app/server/latency.json` (the test rewrites it) | 41 passed |
| Q3 | Real-call pipeline | `cd ml && python -m pytest -q realcall/tests` | 18 passed |
| Q4 | Web types | `cd app/web && npm run typecheck` | no output |
| Q5 | Web build | `cd app/web && VITE_API=https://api.humanslop.in npm run build` | "built", no errors (the chunk-size warning is fine) |
| Q6 | Android unit tests | `cd app/android && ./gradlew testDebugUnitTest` | BUILD SUCCESSFUL |
| Q7 | Android lint | `cd app/android && ./gradlew lintDebug` | no errors; report at `app/build/reports/lint-results-debug.html`. Fix errors, list the warnings you left |
| Q8 | No secrets in the APK | first command below | `0` |
| Q9 | Right API baked in | second command below | ≥ 1 |
| Q10 | Live API is up | `curl -s https://api.humanslop.in/v1/health` | `"ok":true` |

```bash
APK=app/android/app/build/outputs/apk/debug/app-debug.apk
unzip -p "$APK" 'assets/public/assets/*.js' | grep -c -E 'sk-[A-Za-z0-9]{20}|api-subscription-key|VOBIZ_AUTH|HF_TOKEN|BEGIN (RSA|OPENSSH)'   # Q8: 0
unzip -p "$APK" 'assets/public/assets/*.js' | grep -c 'https://api.humanslop.in'                                                     # Q9: >= 1
```

## 6. Phone setup (both phones, tonight and again at 08:00)

| Setting | Payer phone (Sunita) | Relative phone (Rahul) |
|---|---|---|
| App role and Setup | payer, Setup from the status notification | relative, Setup from the status notification |
| Permissions | phone state, call log, contacts, notifications, camera (QR) | notifications, full-screen alerts |
| Battery | unrestricted; Xiaomi: Settings → Apps → DemoPay → **Autostart on** | same |
| Network | **mobile data**, not venue Wi-Fi | same |
| Sound | ringer and media volume up, Do Not Disturb **off** | same, so the Family Verify alert is heard |
| Screen | timeout 10 min, brightness high (projector camera) | same |
| Rehearsal mode | on while the team rehearses with saved numbers; **off** for the real demo unless the caller is saved on the phone | n/a |
| Charge | 100% at 08:00, power bank on the table | same |

## 7. Live end-to-end test matrix (deployed API, mobile data)

Run each once tonight and note the result. Then re-run 1 and 2 at 08:00 to confirm.

| # | Run | Expected |
|---|---|---|
| 1 | **T1:** the attack call reaches the payer phone (Varun dials it from the laptop), then Pay ₹50,000 to a new payee → "Who asked?" → Family → Rahul | Family Verify on the relative phone, **even locked** → "No, that's not me" → **HOLD** (red) → case and evidence pack in the console (`demo.humanslop.in/#/console`) |
| 2 | **L2:** the real Rahul calls → the same payment → "Yes, it's me" | Paid; the sent screen shows the seconds |
| 3 | During one call, ₹9,000 then ₹9,000 to the same new payee | The second one is not silently green |
| 4 | Hang up, then pay ₹60,000 to a new payee within the hour | Still asked, with the "soon after a call" subtitle |
| 5 | The caller is Rahul's saved number; pay a new payee during that call | The question is still asked |
| 6 | Four Family Verify requests from one payer within an hour | The 4th isn't sent; the toast says "Call Rahul on their saved number instead" |
| 7 | Rehearsal mode on | Saved callers are treated as unknown, and the screens say rehearsal mode is on |
| 8 | Mobile data off and on while waiting for Family Verify | Recovers without a reload |
| 9 | Swipe DemoPay away on the relative phone, then send Family Verify | The notification still arrives |
| 10 | QR: open `demo.humanslop.in/#/qr` on the laptop, scan a card with DemoPay | The payee resolves; the payment flow runs |
| 11 | Hindi mode on both phones | All "Who asked?" and Family Verify text in Hindi |
| 12 | Screenshot on the PIN screen | Blocked (FLAG_SECURE) |
| 13 | Projector check | Real phone numbers masked on every screen |
| 14 | Web fallback: `demo.humanslop.in/#/payer` and `#/relative` in each phone's browser | Both work; this is the plan B if the app fails on stage |

## 8. Backup video (on the "never cut" list; tonight, after runs 1 and 2 pass)
- 3–4 minutes:
  - **T1:** attack call → Pay → "Who asked?" → Family Verify on the second phone → "not me" → HOLD → evidence pack.
  - **L2:** "Yes, it's me" → paid.
- Film both phones with a **camera** (or a second phone) and screen-record the laptop console. FLAG_SECURE makes the PIN screen black in a phone's own screen recording, so the PIN step needs the camera shot.
- Save it on the laptop **and** on a phone, offline. Name it `pehchaan_backup_demo.mp4`.

## 9. Report back to Varun by 07:00 (paste this filled in)

```
Build: finale @ <commit>  APK built on <machine>  Node <v>  JDK <v>
Quality gate: Q1 _ Q2 _ Q3 _ Q4 _ Q5 _ Q6 _ Q7 _ (lint warnings left: _) Q8 _ Q9 _ Q10 _
Phones: payer = <model>, relative = <model>, both on build <commit>, set up per §6: yes/no
Matrix: 1 _ (HOLD after _ s)  2 _ (paid after _ s)  3 _  4 _  5 _  6 _  7 _  8 _  9 _  10 _  11 _  12 _  13 _  14 _
Failures and what I changed: ...
Backup video: saved at <path> (laptop) and <phone>: yes/no
upi:// handoff to the user's own UPI app: built / not built
Comprehension test: n people, median seconds to decide _, explained the reason back: _/n  (or: not done, because ...)
```

## 10. Comprehension test (a Round 1 promise; do it if you can find 5 people by 08:30)
1. Before starting, each person agrees verbally. Record nothing; only write down the answers.
2. Show the Pause & Verify screen (T1 at "Who asked?") on a phone and say: "You're paying ₹50,000 to someone your son asked for on the phone."
3. Note the **seconds until they choose**.
4. Ask: "Why did the app stop you?" Mark pass if they say it in their own words.
5. Send Varun: n, the median seconds, and passes out of n. If you can't do it, we report it as cut and say why.

## 11. Be ready to explain (09:00 verification; Stage 1 "any member can walk a judge through it")
Three minutes on each. Explain your own code from the code, not from slides.
- **Your Android SDK:**
  - how the call state is read, and what happens with VoIP calls;
  - what the contact check sends (only "saved: yes/no");
  - how Family Verify reaches a locked phone (foreground service, full-screen intent);
  - FLAG_SECURE, rehearsal mode, number masking;
  - what leaves the phone (the "What left this phone" panel).
- **The risk engine (Varun's, know the shape):**
  - the trigger is a payment during or just after a call to a new or unusual payee;
  - "Who asked?" → a claim-specific out-of-band check (Family Verify, the bank's 1600 registry, a safe word) → explainable log-odds with guardrails G1–G7 → GO / PAUSE / HOLD, with a human release path;
  - voice never holds money.
- **The detector:**
  - shadow mode;
  - real calls 24.6% → 6.8% EER after retraining on real calls;
  - it still misses Sarvam clones of a speaker it never saw;
  - the overnight v5 run tests whether many-speaker data or the NII backbone fixes that, and the result is reported whichever way it lands.
- **The attack call:**
  - a Vobiz two-way stream; the cloned "son" (consented voice only) hears her, transcribes, and replies in the clone voice;
  - since tonight it also speaks the moment she answers, fills the wait with short fillers, and drops the rest of a reply when she talks over him;
  - never recorded.

## 12. Two answers I need from you
1. Is the **`upi://` handoff to the user's own UPI app** built, or does DemoPay only open `upi:` links and QR codes itself? Slide 10 promised the handoff; if it isn't built, we say "cut" and why.
2. The comprehension test (§10): done or not, with the numbers.

## 13. Rules (unchanged)
- Consented voices only; fictional names, banks and UPI IDs on every screen.
- Keys only in the repo-root `.env`, never in the APK, a commit or a screenshot.
- No new features tonight: fixes only, each its own commit. **Nothing after 09:00.**
- Commit with your own git identity. Push by 08:30 and tell Varun.
