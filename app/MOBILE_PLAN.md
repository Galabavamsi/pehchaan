# Pehchaan on real phones: plan for the on-site mobile build

Status: **plan** (21 Oct 2026). Build on site at the finale (24 Oct); see §7 for what to prepare before travel.
`SPEC.md` §7 gets the SDK/shell section before any code (spec-first rule).

## 0. What the judges should see

Today the phones run web pages and the "call" on screen comes from a scenario button. The app makes it real:

1. The cloned-voice scam call (`dial attack`) rings **Phone A** (Varun's Redmi). While it's live, the DemoPay app
   already knows: *call active · 0:14 · number not in your contacts*. No scenario button anywhere.
2. She opens DemoPay and pays ₹50,000. Pehchaan's check uses the **real call metadata from the phone**.
3. "Who asked you to pay?" → Rahul → Family Verify arrives on **Phone B** (Vamsi's Samsung) as a real Android
   notification, even with the screen locked and the app closed.
4. "No, that's not me" → hold → signed report. The bank console on the projector updates live.
5. Bonus: scan a UPI QR / tap a `upi://pay` link → Pehchaan checks it **before** the user's UPI app opens
   (§3.4): "sits in front of any UPI app".

## 1. What already exists (reuse, don't rebuild)

| Piece | Where | Reuse |
|---|---|---|
| Payer, relative, console screens | `app/web/src/PayerPhone.tsx`, `RelativePhone.tsx`, `Console.tsx` | Load them in the app's WebView unchanged |
| Real call context in the API | `POST /v1/risk/assess` takes `call: {state, number, channel, duration_sec, ended_sec_ago, in_contacts}` | The native layer just fills it in |
| Family Verify signing | Ed25519 keypair in the relative page (tweetnacl), `POST /v1/devices/register`, `/respond` | Keep for the demo |
| Live updates | WebSockets `/ws/case`, `/ws/device/{id}`, `/ws/console` | Native notification listens on `/ws/device/{id}` |
| Bank outbound-call registry | `adapters.py` mock, `start_call()` / `active_call()` | Expose one endpoint for the "genuine bank call" demo (§4) |
| Live deployment | `api.` / `demo.humanslop.in` (TLS, WebSockets) | The app points at it |

## 2. Approach: Capacitor shell around the existing web app (recommended)

| Option | Effort on site | Real call state | Push to Phone B | Verdict |
|---|---|---|---|---|
| Web pages only (today) | 0 | ✗ | only while the page is open | the fallback |
| **Capacitor (WebView) + small Kotlin plugins** | ~5–6 h | ✓ | ✓ local notification from a foreground service | **use this** |
| React Native / Expo | rewrite UI | needs native module anyway | ✓ | no |
| Native Kotlin app | rewrite everything | ✓ | ✓ | no time |

**One APK, two roles** chosen on first launch ("I'm paying" → DemoPay with Pehchaan; "I'm family" → Pehchaan
Family). One build, installed on both phones. Name and icon must be fictional ("DemoPay", no real bank/UPI brand).

## 3. Native pieces (Kotlin, as Capacitor plugins)

### 3.1 Call state → `call` context (the headline)
- `TelephonyCallback.CallStateListener` (Android 12+) with `PhoneStateListener` fallback; permissions
  `READ_PHONE_STATE` + `READ_CALL_LOG` (needed to get the number on Android 10+).
- Track `state` (ringing/active/ended), call start, end → `duration_sec`, `ended_sec_ago` (SPEC: ≤ 10 min window).
- VoIP: `AudioManager.getMode() == MODE_IN_COMMUNICATION` → `channel: "voip"` (WhatsApp calls show up this way;
  we can't tell which app, and don't need to).
- Plugin event `callChanged` → the web layer shows the call pill and sends `call` with `/v1/risk/assess`.

### 3.2 On-device contact check
- `ContactsContract.PhoneLookup` on the caller number → `in_contacts: true/false`. Contacts never leave the phone
  (SPEC §6); only the boolean goes to the API.

### 3.3 Family Verify notification on Phone B
- Foreground service (type `dataSync`) holding the WebSocket `/ws/device/{device_id}`; on `fv_request` post a
  high-priority notification with a full-screen intent → opens the relative screen on the challenge.
- **No Firebase/FCM**: it needs a Google project, and Google bills a real card (HANDOVER §9). The WebSocket service
  is enough for two phones on mobile data.
- MIUI/Samsung battery savers kill background services: set the app to "No restrictions"/autostart on both phones.

### 3.4 "In front of any UPI app": `upi://` interception
- Intent filter `ACTION_VIEW`, scheme `upi`, host `pay`. Any UPI QR or payment link then offers DemoPay in the
  chooser; DemoPay parses `pa`, `pn`, `am` and runs the Pehchaan check first.
- On GO: "Continue in your UPI app" re-dispatches the same intent through a chooser that excludes DemoPay.
  **Demo only with fictional VPAs** (`ariftraders@okdemo`); stop at the handoff screen, never complete a real payment.
- Message for judges: a bank or TPAP integrates the SDK properly; this shows the same check can sit in front of
  UPI links and QR codes without changing NPCI rails.

### 3.5 Not for this build
Device keys in Android Keystore (production: P-256/Ed25519 in hardware), on-device ASR, call-audio capture.

## 4. Server changes (small; write them into SPEC.md §7 first)

1. **Live mode for the payer app**: assess with `payer_id` (seeded `u_sunita`), the typed payment and the phone's
   real `call`, no scenario. Check what the scenario seeding sets up (relative circle, payer history) and keep that
   seeded at start-up so a real-call case behaves like T1.
2. **Bank dialer endpoint** (`POST /v1/bank/calls`, demo key) wrapping `BankRegistry.start_call()`: a "bank agent"
   page registers "Bharat Demo Bank is calling this customer now". Then the genuine-bank path (registry confirms →
   Green) can be shown with a real call. Production story: an **Amazon Connect** outbound contact flow (Lambda)
   writes to this registry, which fits the Amazon sponsorship. Decide whether the call comes from the Vobiz number
   (not 1600-series, so `bank_claim_not_1600` would fire) or present it as "registry wins over number format".
3. Expected signals with a real call: the Vobiz number is Indian, so `caller_international` won't fire (T1 used
   +44); `caller_unknown` will. Auto Family Verify and the G7 hold on "not me" don't depend on that, so the outcome
   is the same; only the reasons list changes. Re-run the simulator only if LRs change (they shouldn't).

## 5. Other ways to show the integration with UPI / payment layers

1. **"Where Pehchaan sits" slide**: payer app (TPAP/PSP, Pehchaan SDK) → Pehchaan risk API (bank/PSP cloud,
   ap-south-1) → *before* UPI PIN → NPCI UPI switch → remitter bank → beneficiary bank. Inputs: DoT FRI/DIP, I4C
   suspect registry, bank outbound-call registry, PSP mule scores. Outputs: hold/release, NCRP/1930/Chakshu pack.
   Nothing changes in NPCI rails; it's a pre-authorisation check.
2. **SDK code card** (~10 lines, Kotlin): `Pehchaan.assess(payment, callContext)` → `when (result.tier)`. Shows
   how little a bank changes. Use the real plugin API from §3 so it's not slideware.
3. **RBI APP-fraud controls** (discussion paper, 9 Apr 2026): our HOLD is the "1-hour lag", Family Verify is the
   "trusted-person approval". Pehchaan decides *when* to apply them.
4. **Bank analyst console + evidence pack** (exists): the bank's side of the same case.
5. **Relatives without the app**: Family Verify link by SMS/WhatsApp to `/#/relative` (mention, don't build).
6. **Amazon Connect** (optional): see §4.2.

## 6. Demo flow with the app (replaces scenario buttons for T1)

| Step | Phone A (Redmi, DemoPay) | Phone B (Samsung, Family) | Projector |
|---|---|---|---|
| 1 | `dial attack` rings; call pill appears live | idle, screen locked | console |
| 2 | after hang-up (≤ 10 min): Pay ₹50,000 to Arif Traders | | new case, Amber |
| 3 | "Who asked?" → Family → Rahul | **notification** "Mummy needs you" | awaiting verification |
| 4 | | "No, that's not me" | Red, G7 |
| 5 | 30-min hold → Cancel and report | | evidence pack |

L2 for real: Vamsi calls Varun from his own number (not in contacts, "Rahul's new number"), Varun pays Rahul,
Vamsi taps "Yes, it's me" → paid. T2/T3 stay as scenario buttons.

## 7. Build plan and risks

`TASKS.md` says nothing on site should be the first time we try it. Building on site is our choice, so prepare
the slow, risky parts **before travel** (≈ 2 h):

- [ ] Android Studio + SDK 34 + JDK 17 on the demo laptop; `npx cap add android`; one Gradle sync (downloads
      ~1–2 GB; campus Wi-Fi may be slow or blocked)
- [ ] A hello-world APK installed on **both** phones over USB. Redmi/MIUI needs Developer options → "Install via
      USB" (asks for a Mi account) and "USB debugging (Security settings)"
- [ ] Debug keystore and app id fixed (`in.humanslop.demopay`), so re-installs keep permissions and keys

On site (time-boxed, keep the web version as the fallback at every step):

| Order | Piece | Box |
|---|---|---|
| 1 | Shell loads `demo.humanslop.in` screens; role picker | 1 h |
| 2 | Call state + contact check → real `call` in assess (§3.1–3.2, §4.1) | 2 h |
| 3 | Family Verify notification service on Phone B (§3.3) | 1.5 h |
| 4 | `upi://` intent filter + handoff screen (§3.4) | 1 h |
| 5 | Name/icon, permissions screen, battery settings on both phones, 3 full rehearsals | 1 h |

Risks: MIUI/One UI kill the background service (whitelist the app); `READ_CALL_LOG` is fine sideloaded (not for
Play); Android 14 foreground-service types; Gradle on venue network (use the phone hotspot); scope creep. If a
step isn't working by the end of its box, ship without it.

## 8. Decisions for Varun + Galaba
- Prepare the skeleton before travel (recommended) or build everything on site?
- One APK with a role picker (recommended) or two apps?
- Bank-call demo: mock endpoint only, or a real Amazon Connect outbound flow?
- Real call drives T1 (recommended), with scenario buttons kept as fallback?
