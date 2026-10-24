# Android app brief (for Vamsi): build on site, 24–25 Oct

**Goal:** one Android app, installed on both phones, that makes the demo real instead of scripted:
the scam call rings **Phone A** (Varun's Redmi, the payer), the app *knows* a call is live and who it's from,
the payer pays, and **Phone B** (your Samsung, the "son") gets Family Verify as a **real notification**,
even with the screen locked. Detailed design: `app/MOBILE_PLAN.md`. Overall plan: `FINALE_PLAN.md`.

The risk API and web screens already work and are live: **https://api.humanslop.in** (API) and
**https://demo.humanslop.in** (web). The app is a thin native shell around them plus a few native plugins.

---

## 1. What to build (in this order, with time boxes)

| # | Piece | Box | Done when |
|---|---|---|---|
| 1 | **Capacitor shell** around `app/web`, built with `VITE_API=https://api.humanslop.in`. First launch: role picker "I'm paying" (DemoPay) / "I'm family" (Pehchaan Family) | 1 h | App opens the right screen on both phones |
| 2 | **Call state plugin** (Kotlin): `TelephonyCallback` (Android 12+) / `PhoneStateListener` fallback → state, number, start/end time; VoIP = `AudioManager.mode == MODE_IN_COMMUNICATION` | 1.5 h | The payer screen shows "call active · 0:14 · +91 80…" live |
| 3 | **On-device contact check:** `ContactsContract.PhoneLookup` on the caller number → `in_contacts: true/false`. Only the boolean leaves the phone | 0.5 h | Unknown caller shows "not in your contacts" |
| 4 | **Real call → risk check:** the payer's Pay sends the phone's real call context (§3) instead of the scenario's | 1 h | A real call from the Vobiz number produces a case with `caller_unknown` |
| 5 | **Family Verify notification** on Phone B: foreground service holding `wss://api.humanslop.in/ws/device/dev_rahul`; on `fv_request` post a high-priority notification with a full-screen intent → opens the relative screen | 1.5 h | Screen locked, app in background → notification → "No, that's not me" works |
| 6 | **`upi://` handoff** (stretch): intent filter `upi://pay` → parse `pa`, `pn`, `am` → Pehchaan check → "Continue in your UPI app" re-sends the intent excluding us. Fictional VPAs only, stop before any real payment | 1 h | Scanning a demo QR opens DemoPay first |
| 7 | Polish: app name "DemoPay" / "Pehchaan Family", icon, permission explainer screen, battery settings on both phones | 0.5 h | Clean install on both phones |

If a piece isn't working by the end of its box, ship without it: the web pages (`demo.humanslop.in/#/payer`,
`#/relative`) stay the fallback for every step.

## 2. Setup
- Android Studio + SDK 34, JDK 17, `npm i @capacitor/core @capacitor/cli @capacitor/android` in `app/web`,
  `npx cap init DemoPay in.humanslop.demopay --web-dir dist`, `npx cap add android`, then `npm run build && npx cap sync`.
- Gradle downloads 1–2 GB: use a phone hotspot if venue Wi-Fi is slow.
- Redmi (MIUI): Developer options → "Install via USB" + "USB debugging (Security settings)" (asks for a Mi account).
- Both phones: battery → "No restrictions" for the app, allow autostart, notifications on (Android 13+ asks).

## 3. API contract (all live on https://api.humanslop.in)

**Risk check at Pay:** `POST /v1/risk/assess`
```json
{
  "payer_id": "u_sunita",
  "payment": {"payee_vpa": "ariftraders@okdemo", "payee_name": "Arif Traders", "amount_inr": 50000},
  "call": {"state": "active", "number": "+918064260325", "channel": "pstn",
           "duration_sec": 35, "ended_sec_ago": null, "in_contacts": false}
}
```
- `call.state`: `active` | `ended` | `none`; `channel`: `pstn` | `whatsapp` | `voip`; for an ended call set
  `state: "ended"` and `ended_sec_ago` (the trigger window is 10 minutes, 60 minutes for amounts ≥ ₹50,000).
  Send the same `call.number` for every payment during one call: what was already sent during that call counts
  toward ₹10,000 (SPEC v0.3 split payments).
- **Tell the server when the call started** (SPEC v0.3, "same call = since it started"): send a live
  `duration_sec` (seconds since the call started, computed at the Pay tap; for an ended call, its length) or
  `started_at` (ISO 8601 with offset, from the call-state plugin). Prefer `duration_sec`: it doesn't depend on the
  phone's clock, and a `started_at` ahead of the server's clock is ignored. With neither, the server can only look
  back 60 minutes, so earlier payments in a long call drop out.
- **Report payments that went through.** A payment that opens no case (`case_id: null`: not triggered, or a silent
  Green) comes back with a `payment_ref`. After the UPI app confirms the debit, call
  `POST /v1/payments/{payment_ref}/sent` (`{"recorded": true}`; a repeat returns `{"recorded": false,
  "already": true}`, so retries are safe; an unknown ref is 404). Don't call it if the payer backs out or the PIN
  fails: only reported payments count toward the payee's history, the trusted bypass and the same-call total.
  A payment that opened a case is recorded by Pay / Continue (`POST /v1/cases/{case_id}/user-action`); no extra call.
- Then the claim: `POST /v1/risk/assess` with `{"case_id": "...", "claim": "family", "claim_target": "rel_rahul"}`.
  A family claim for an enrolled relative sends Family Verify automatically (check the response's
  `auto_family_verify`). Claims: `family`, `bank`, `upi_or_shop`, `authority`, `other`, `none`.
  If `auto_family_verify` is `{"skipped": "..."}`, no push went out (rate limit: 3 per payer, 5 per relative
  per hour): show that text, which tells the payer to call the relative's saved number. A manual
  `POST /v1/verify/family` over the limit returns 429 with the same text.
- Live updates for the payer: `wss://api.humanslop.in/ws/case/{case_id}`.

**Relative's phone (Phone B):**
- Register once: `POST /v1/devices/register` `{"device_id": "dev_rahul", "user_id": "rel_rahul", "public_key_b64": "..."}`
  (Ed25519; the web screen does this with tweetnacl and keeps the key in local storage).
- Listen: `wss://api.humanslop.in/ws/device/dev_rahul` → messages `fv_request` (`data` has `challenge_id`,
  `nonce`, the message to show), `fv_expired`, `fv_done`, `reset`. Missed while offline:
  `GET /v1/devices/dev_rahul/challenges`.
- Answer: `POST /v1/verify/family/{challenge_id}/respond` `{"answer": "yes"|"no", "device_id": "dev_rahul",
  "signature_b64": "..."}` where the signature is Ed25519 over the UTF-8 string
  **`pehchaan-fv|{challenge_id}|{nonce}|{answer}`**. The server rejects a bad signature (403).
- Simplest path: let the WebView's existing relative screen do the signing; the native service only posts the
  notification and opens the screen.

Seeded people (fictional): payer `u_sunita` (Sunita Sharma), son `rel_rahul` on device `dev_rahul`. Check the exact
ids with `GET /v1/demo/current` after loading T1 (`POST /v1/demo/scenario/T1`) if anything doesn't match.

## 4. Testing end to end
1. Varun loads T1 (or the jury panel) on the server.
2. Varun's laptop places the cloned-voice call to Phone A (`python -m realcall.dial attack ...`, Vobiz number
   +91 80 6426 0325, which is *not* in Phone A's contacts).
3. Phone A: the app shows the live call → Pay ₹50,000 → "Who asked?" → Family → Rahul.
4. Phone B (locked, app in background): notification → "No, that's not me" → Phone A shows the 30-minute hold.
5. Repeat with "Yes, it's me" → payment goes through.

## 5. Rules
- **Git:** branch `app-android` from `finale`. Add `app/android/` and the Capacitor config; keep server/engine
  changes out unless you tell Varun. First commit: a short "Android shell" paragraph in `SPEC.md` §7 (spec first).
  Commit often with clear messages; everything you write here is on-site work.
- **Never commit** keystores, signing keys, `.env`, phone numbers or `participants.yaml`.
- **Privacy:** contacts never leave the phone (only `in_contacts`); no call recording; fictional names on screens.
- **No Firebase/FCM** (needs a Google project billed to a card); the WebSocket service is enough.
- Permissions: `READ_PHONE_STATE`, `READ_CALL_LOG` (caller number on Android 10+), `READ_CONTACTS`,
  `POST_NOTIFICATIONS`, `FOREGROUND_SERVICE` + `FOREGROUND_SERVICE_DATA_SYNC` (Android 14), `USE_FULL_SCREEN_INTENT`.
  Sideloaded only (call-log access wouldn't pass Play review, and that's fine for the demo).
- Be ready to explain every part to a judge (rubric: "any member can walk a judge through it").
