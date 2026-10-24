# Pehchaan — product & detection spec (v0.2, 2026-10-06)

> **Verify the person, not the voice.**
> A safeguard inside UPI/bank apps that catches voice-clone fraud at the moment money moves. It asks *who* is on the line and checks that claim through channels a cloned voice cannot reach. AI voice forensics is one supporting signal, never the judge.

Track: **RAKSHAM 01 — Voice Cloning Fraud Detection.** This file is the single source of truth for the engine, app, ML pipeline and deck. If you change behaviour, change this file first.

---

## 1. Problem

**Threat patterns (India, 2023–2026, sourced in `research/track01_voice_cloning.md`):**

| ID | Pattern | Typical script |
|---|---|---|
| T1 | **Cloned relative.** Son, nephew or sibling, cloned from social media clips. Comes from an unknown, overseas or WhatsApp number. | "Papa, accident ho gaya, police ne phone le liya… Mummy ko mat batana, abhi ₹50,000 bhejo." |
| T2 | **Fake bank official.** Synthetic or cloned voice, often an AI voice agent working at scale. | "Fraud department se… account block ho jayega… OTP batao / safe account mein transfer karo." |
| T3 | **Hybrid digital arrest.** Fake police/CBI plus a cloned relative on the same call. | "Your son is in custody" → a cloned son pleads → "pay bail/settlement now". |

All three end in an **authorised push payment**: the victim enters their own UPI PIN, so OTP/2FA does not help, and the bank sees a normal transaction.

**Primary user:** a retail UPI customer (highest risk: parents and elders aged 45+) at the moment they tap **Pay** during, or within 10 minutes after, a call.
**Operating owner:** the fraud-risk team of the bank or UPI app (TPAP, e.g. Amazon Pay), shipped as an SDK plus a risk API.
**Secondary users:** the *claimed* relative (answers Family Verify), and bank fraud analysts (review queue).

**Out of scope for v1:** detecting clones outside a payment moment, corporate CEO fraud, and bank contact-centre inbound protection. That last one is phase 2, the "Amazon Connect Voice ID replacement" story.

## 2. When Pehchaan runs (the trigger, no audio)

Pehchaan assesses a payment only if **both** hold:
- a phone call is active, a VoIP call is active (the audio mode shows an ongoing call, e.g. WhatsApp), **or** a call ended ≤ 10 minutes ago (≤ **60 minutes** when the amount is ≥ ₹50,000); **and**
- the payee is new, **or** the amount is above the user's 95th percentile, **or** the amount is ≥ ₹10,000, **or** the amounts this payer has already sent during the same call plus this one reach ₹10,000.

*v0.3 (24 Oct 2026, on site): two evasions closed. "Hang up, wait 15 minutes, then pay" is covered by the longer window for large amounts (RBI's April 2026 paper: ~92% of fraud value is in payments above ₹50,000). "Send ₹9,500 five times" is covered by counting what was already sent during the same call, so splitting a demand under ₹10,000 no longer escapes the trigger. Payments made during the call also don't make a payee familiar: a payee first paid during this call stays **new** for the rest of the call, and those payments don't count toward the trusted bypass. Without this, the second ₹9,500 would go through silently (the payee already "paid once") and the fourth would be trusted.*

Every other payment is untouched, which keeps friction at zero for the large majority. **Trusted bypass:** payees paid ≥ 3 times before this call, with an amount ≤ 1.5× their usual, go Green.

## 3. Signals — six independent families

| Family | Signal (code) | Source | Notes |
|---|---|---|---|
| **C: Claim** | `claim_family`, `claim_bank` ("my bank", which names the bank), `claim_upi_or_shop` (UPI app, shop, delivery), `claim_authority`, `claim_other`, `claim_none` | User's one-tap answer to "Who asked you to make this payment?" | Asked only when the trigger fires. If `claim_authority` comes with a money request, that is a near-certain scam. |
| **K: Call context** | `caller_unknown` (not in contacts, matched on-device by hash), `caller_international`, `caller_voip_unknown`, `bank_claim_not_1600` (claimed bank, but the number isn't in the TRAI 1600 series), `fri_medium/high/very_high` (DoT FRI tier via the bank's DIP integration, mocked), `call_ongoing_long` (> 15 min, typical of digital arrest) | OS call state; bank risk API | Metadata only, never audio. |
| **P: Payment context** | `payee_new`, `amount_gt_p95`, `amount_gt_p99`, `payee_flagged_high/medium` (suspect registry or mule score, mocked), `payee_name_mismatch` (claimed family, but the VPA name is unrelated), `burst_new_payees` (≥ 2 new payees in 30 min) | Bank/PSP | Server-side. |
| **V: Voice provenance** (opt-in) | `voice_likely_synthetic`, `voice_inconclusive`, `voice_no_strong_evidence`, `watermark_detected` | 8–12 s speakerphone capture → Voice Provenance Service | Calibrated probability plus a quality gate. Low quality means inconclusive, never "real". |
| **S: Script cues** (opt-in) | `cue_secrecy`, `cue_urgency`, `cue_otp_pin`, `cue_arrest_threat`, `cue_remote_app`, `cue_refund_verification` | Hindi/English/Hinglish ASR on the same capture, **or** a 3-question tap checklist (no audio) | |
| **O: Out-of-band verification** (decisive) | `fv_denied` (relative's own phone: "Not me"), `fv_confirmed` ("Yes, it's me"), `fv_timeout`, `callback_denied` / `callback_confirmed` (user called the saved number), `safeword_failed` / `safeword_passed`, `bank_no_active_call` / `bank_active_call_1600` (bank's outbound-call registry) | Family Verify push; user report; bank dialer registry | A cloned voice cannot answer from the real person's phone. |

## 4. Fusion logic (explainable log-odds plus guardrails)

`log_odds = logit(prior) + Σ_family clip(Σ_signals ln LR, −cap_f, +cap_f)` → `p = sigmoid(log_odds)`

- **Prior** `π0` = P(scam | trigger fired). Default 1/400, configurable. The simulator sweeps 1/2000 to 1/100.
- **Likelihood ratios** are initial expert values, documented in `engine/pehchaan/config.yaml`. Each is tagged `assumed` or `measured`. The voice LRs become `measured` from our detector's calibrated confusion rates.
- **Family caps** (`cap_f`): C 60, K 30, P 30, V 8, S 30, O 300 (expressed as LR; the cap is applied on ln LR).

Initial LRs (scam vs genuine, given the trigger fired):

| Signal | LR | Signal | LR |
|---|---|---|---|
| claim_family | 1.5 | claim_bank | 6 |
| claim_authority | 60 | claim_other / claim_none | 1.0 / 0.8 |
| claim_upi_or_shop | 0.8 | | |
| caller_unknown | 4 | caller_international | 6 |
| caller_voip_unknown | 3 | bank_claim_not_1600 | 20 |
| fri_medium / high / very_high | 3 / 10 / 30 | call_ongoing_long | 3 |
| payee_new | 2.5 | amount_gt_p95 / p99 | 1.8 / 3 |
| payee_flagged_medium / high | 4 / 25 | payee_name_mismatch | 5 |
| burst_new_payees | 4 | | |
| voice_likely_synthetic | 8 | voice_inconclusive | 1.0 |
| voice_no_strong_evidence | **1.0** (never reassures) | watermark_detected | 50 → capped at 8 |
| cue_secrecy / urgency | 4 / 2 | cue_otp_pin / arrest_threat | 8 / 10 |
| cue_remote_app / refund_verification | 6 / 5 | | |
| fv_denied | 300 (decisive, G7) | callback_denied | 30 (user-reported) |
| fv_confirmed / callback_confirmed | 0.02 | bank_registry_unknown | 1.0 |
| safeword_failed / passed | 30 / 0.1 | bank_no_active_call / bank_active_call_1600 | 50 (decisive, G7) / 0.05 (decisive, G4) |
| fv_timeout | 1.0 | | |

**Tiers** (thresholds in config, tuned by the simulator to an **alert budget**: at π0 = 1/400, ≤ 0.25% of genuine triggered sessions end in Red and ≤ 6% see Pause & Verify):
- **Green** `p < 0.15`: proceed silently. (Raised from 0.10 to meet the Pause & Verify budget; simulator sweep in `engine/results/sim_threshold_sweep.json`.)
- **Amber** `0.15 ≤ p < θ_red`: Pause & Verify interstitial. The user may continue after reading it (minimum 5 s).
- **Red** `p ≥ θ_red` (0.75, chosen from the plateau in the 0.72–0.76 band) **and** a guardrail-qualified condition, **or** any decisive negative (G7): cooling-off hold. The payment is not sent.

**Guardrails (hard rules, applied after scoring):**
- **G1 (no single weak signal):** Red requires either:
  - (a) ≥ 2 families each contributing LR ≥ 3, where **trigger-implied evidence does not count**. P qualifies only through `payee_flagged_*`, `payee_name_mismatch` or `burst_new_payees`, not `payee_new` or `amount_gt_*`. V never counts (G2). Or:
  - (b) a decisive negative from a channel outside the user's own taps: `fv_denied` (device-signed by the relative) or `bank_no_active_call` (only for an integrated bank that the user named).

  Otherwise the result is capped at Amber.
- **G2 (voice is supporting evidence):** V never counts toward G1, and if removing V would drop the tier below Red, the result is capped at Amber (strict). `voice_no_strong_evidence` has LR 1.0: the detector can raise suspicion but **never lower it**, because detectors miss unseen generators. "Sounds real" is not proof.
- **Voice shadow mode (default, v0.2 final):** on one real cellular call, every detector we tested, ours included, flagged 91–95% of genuine speech as synthetic (measured LR on real-call genuine speech = 0.93). The detector score is therefore logged and shown to analysts but uses LR 1.0 in decisions, until it passes a real-call gate (≤ 5% false flags on ≥ 50 consented real calls). `watermark_detected` stays active. See `ml/results/SUMMARY.md`.
- **G3 (quality gate):** speech < 4 s or SNR < 10 dB means `voice_inconclusive`.
- **G4 (decisive positive):** `fv_confirmed`, `callback_confirmed` or `bank_active_call_1600` (the bank's own registry confirms a live 1600 call) put the result at Green, unless `payee_flagged_high` is present (then Amber).
- **G5 (trusted bypass):** see §2.
- **G6 (no accusation):** user-facing text never says "this is a scam" or "fake voice detected". It says what we noticed and what to check.
- **G7 (decisive floor):** `fv_denied` or `bank_no_active_call` puts the result at **Red regardless of p**. If the real relative's phone says "not me", "Continue anyway" is not offered.
  - User-reported negatives (`callback_denied`, `safeword_failed`) are strong evidence (LR 30) but **not** decisive. The UI makes "Cancel" the primary action instead.
  - A registry lookup against a bank that isn't integrated returns `bank_registry_unknown` (LR 1), never `bank_no_active_call`.
- **Coached "no one":** show the 3-tap cue checklist (secrecy · OTP/PIN · arrest threat) when the claim is `claim_none` or `claim_other` **and the context alone (K + P, before the claim) was Amber**, even if the claim answer lowers p below Amber.
- **Auto Family Verify:** when the claim is `claim_family` and the named relative is in the payer's Pehchaan circle, the verify push is sent **automatically**. The payer sees "We've asked Rahul to confirm on his own phone" and can cancel the request. This defeats "don't call your son" coaching and removes taps for elders.

Every decision returns `reasons[]`: code, plain-language text (EN + HI), contribution in ln-LR, and family. The UI shows the top 2–3, while the analyst sees all of them.

## 5. Actions per tier

- **Green:** proceed; aggregated, anonymous counters only.
- **Amber — "Ruko, pehle pehchaan karo" (Pause & Verify):**
  - The top reasons, in plain language and the user's language.
  - One-tap checks that depend on the claim:
    - family → **Ask {name} on their phone** (Family Verify), **Call {name}'s saved number**, **Ask our family safe word**
    - bank → **Check with my bank** (registry lookup), **Call the bank on 1600 / the official number**
    - authority → a hard fact card: "There is no 'digital arrest' in Indian law. Police never ask for money on a call."
  - **Continue anyway** (after 5 s) and **Cancel payment**.
- **Red — Cooling-off hold:** the payment is held for 30 minutes and not sent.
  - **Release early** after a positive out-of-band check, or after a bank analyst review (required for amounts ≥ ₹50,000).
  - **Cancel and report:** builds the evidence pack.
  - When the hold expires, the payment is **not** sent automatically; the user must re-confirm.
  - The user always has a human path: a callback from the bank fraud desk.
- **Report path (any tier, user-initiated):** a signed evidence pack with case ID, IST timestamps, masked payer, payee VPA, amount, caller number, claim, reasons, voice score plus model version, and an optional transcript snippet. It pre-fills fields for **1930 / cybercrime.gov.in (NCRP)** and **Sanchar Saathi Chakshu**, and flags the payee VPA to the PSP's mule-risk team. Pehchaan **never files a police complaint by itself**; the user submits.

## 6. Privacy & safety by design

- **Never collected:** call recordings by default, contact lists (only on-device hash matches), SMS/WhatsApp content, location history, voiceprints of the user.
- **Voice check:** opt-in for each call, started by the user, 8–12 s. Audio is processed in memory and **discarded after scoring**, unless the user taps "Save as evidence". Saved audio is KMS-encrypted, retained 90 days or for the life of the case, and can only be opened by an analyst with a case ID and a logged reason.
- **Family Verify:** both sides opt in to the "Pehchaan circle". The verify message shows the amount band and payee name only. It is sent per payment and started by the payer, so there is no ongoing monitoring. Abuse guard: a relative cannot see your transactions or trigger checks.
- **Security:**
  - Device-bound keys for Family Verify responses (signed challenge).
  - Family Verify rate limit (v0.3): at most 3 requests per payer and 5 per relative in any hour. Beyond that no push is sent; the payer is asked to call the relative's saved number instead. This stops an attacker from spamming a relative into tapping "yes" or tuning them out.
  - mTLS from app to API.
  - Analyst RBAC with immutable access logs.
  - Evidence hash chain, plus S3 Object Lock for saved evidence.
- **Fairness:** report detector false-reject rates by language, gender and speaker. Elderly mode offers large text, vernacular UI and read-aloud.
- **Adversarial adaptation:**
  - Coached victims: the UI says "If someone on the call is telling you what to tap, that is a warning sign", and `claim_none` still keeps context risk.
  - Hang-up-then-pay: covered by the 10-minute window.
  - New generators: the voice signal is capped, out-of-band checks are decisive, and the red-team corpus is refreshed monthly. We report results on held-out generators.
  - Codec laundering: training uses channel augmentation.
  - Payee hopping: the burst signal plus PSP mule feed.

## 7. Components & interfaces

**Customer phone (Pehchaan SDK inside the bank/UPI app):** call-state sensor; on-device contact-hash matcher; payment hook; Pause & Verify UI; voice-check capture with VAD and quality gate.

**Bank/PSP cloud (AWS; production in ap-south-1 for RBI payment-data localisation):**
- Risk API: FastAPI on ECS Fargate behind API Gateway.
- Fusion Engine: the `pehchaan` Python package.
- Voice Provenance Service: a GPU endpoint running the fine-tuned XLS-R/AASIST ensemble plus a watermark check.
- Script Cue Service: Deepgram / Sarvam ASR, then a cue classifier. The classifier is rules plus an LLM (Amazon Bedrock with Guardrails), structured output only.
- Context adapters: DoT FRI/DIP, I4C suspect registry, the bank's outbound-call registry (contact-centre dialer / Amazon Connect), and PSP payee risk. All are mocked in the prototype.
- Family Verify Service: push plus a signed challenge.
- Case & Evidence Vault: DynamoDB plus S3 Object Lock and KMS.
- Analyst Console: Cognito RBAC.
- Reporting connector: pre-filled NCRP/Chakshu.
- Feedback & model-ops loop: labels, recalibration, red-team refresh, drift monitoring, LLM tracing in Langfuse.

**Prototype API contracts:**
- `POST /v1/risk/assess` → `{case_id, tier, p, reasons[], actions[], guardrails[]}`
- `POST /v1/voice/score` (wav, 16 kHz mono, ≤ 12 s) → `{p_synthetic, band, quality{speech_sec, snr_db, ok}, watermark{detected, scheme}, model_version, latency_ms}`
- `POST /v1/verify/family` → creates a challenge; `POST /v1/verify/family/{id}/respond`; WebSocket `/ws/case/{case_id}` streams updates.
- `GET /v1/cases`, `GET /v1/cases/{id}`, `POST /v1/cases/{id}/decision` (analyst)
- `POST /v1/cases/{id}/evidence-pack` → JSON + PDF

**Latency budget:**
- Risk assess at Pay tap: **< 300 ms p95**, with no audio.
- Voice check: 8–12 s capture, then **< 1.5 s** inference.
- Family Verify: asynchronous, 3-minute timeout. A timeout falls back to callback or safe word.

## 8. Validation plan (what we measure, and what we claim)

- **V1 Detector:** consented Indic corpus — team speakers × {en, hi, mother tongue} × generators {IndicF5, F5-TTS, XTTS-v2, Chatterbox-multilingual, CosyVoice2, Seed-VC (voice conversion), Sarvam Bulbul, OpenAI TTS, Gemini TTS} × channels {clean, PSTN 8 kHz G.711, AMR-NB, Opus/WhatsApp-like, speaker→mic replay}. Bona fide audio comes from team recordings, including real cellular and WhatsApp calls, plus public CC0/CC-BY Indic speech.
  - **Splits:** ≥ 2 generators fully held out, and 1 held-out speaker.
  - **Metrics:** EER; FRR at FAR = 5%; per generator × channel table; calibration (ECE); FRR by language and gender.
- **V2 Fusion and alert budget:** a synthetic session simulator with documented assumptions, anchored to public base rates (NPCI volumes, NCRP fraud counts). It reports the % of genuine triggered payments that see Amber or Red, catch rate per scam pattern, and sensitivity to the prior and to detector quality. These are **assumption-driven projections, labelled as such**.
- **V3 Comprehension:** a 5-person hallway test of the Pause & Verify screen with parents/elders (consented), measuring time-to-decision and whether they understood the reason. Planned for the finale.
- **V4 Live adversarial demo:** a Vapi/Bolna agent speaking in a cloned (consented) teammate voice calls a teammate, who tries to pay in the demo app.

## 9. Repo layout

- `research/`: cited findings.
- `data/recording-kit/`: scripts and consent.
- `data/raw/`: audio, gitignored.
- `ml/`: corpus generation, channel simulation, detector training/eval, serving, and `ml/results/*.json` metrics.
- `engine/`: the `pehchaan` Python package (signals, fusion, explanations, config, simulator, tests).
- `app/server/`: FastAPI. `app/web/`: React demo with three surfaces: payer phone, relative phone, analyst console.
- `deck/`: the Round 1 PDF source.
