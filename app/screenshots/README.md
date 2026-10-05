# Deck screenshots

All 13 images are produced by `python app/screenshots/shoot.py`, which drives the live app (API on :8400, web on :5173) with Playwright at deviceScaleFactor 2. The API was started with `PEHCHAAN_DEMO_TIME=10:38`, so the clocks read 10:38–10:39 IST.

- Phone shots are cropped to the device frame: 824×1732 px, a 390×844 screen plus bezel.
- `09` is the full console page: 1440 px wide, so 2880 px.
- `10` is the 1920×1080 split view: 3840×2160 px.

All people, numbers, banks and UPI IDs are fictional. Context adapters are mocks.

| File | What it shows |
|---|---|
| `01_call_and_pay.png` | Sunita is on a WhatsApp call with an unknown +44 number (the "Not in contacts" chip) and is entering ₹50,000 to Arif Traders, a first-time payee, in DemoPay. "Protected by Pehchaan" sits under the Pay button. |
| `02_pause_who.png` | The one-tap question "Who asked you to make this payment?" with the six v0.2 options (Family member, My bank, UPI app/shop/delivery, Police/CBI/Govt, Someone else, No one) and the coached-victim warning ("If someone on the call is telling you what to tap…"). |
| `03_family_options.png` | SPEC v0.2 A19: after "Family member" → Rahul, Family Verify is sent automatically: "We've asked Rahul to confirm on his own phone", a 3:00 countdown, a small **Cancel request** link, "Call Rahul's saved number instead" and Cancel payment. (The filename is kept for the deck.) |
| `04_relative_prompt.png` | Rahul's phone: "Mummy is about to send ₹50,000 to 'Arif Traders' because someone said they are you. Is this you?", with Yes / No buttons, a countdown, the device-key signature hint and a privacy note. |
| `05_red_hold.png` | After "No, that's not me": a Red cooling-off hold with a 30:00 ring. The lead card says Rahul answered from his own phone (signature checked), followed by the remaining reasons and the release paths: report, talk to a person at the bank, callback, release early (analyst review at ₹50,000 or more). |
| `06_evidence_pack.png` | "Your report is ready": the case number, an Ed25519 signature and the SHA-256 chain head, then Call 1930 and the pre-filled cybercrime.gov.in (NCRP) and Chakshu fields. |
| `07_bank_claim.png` | T2, a fake bank call from a 10-digit mobile. The customer named Bharat Demo Bank, which is integrated, and its registry has no live call: "Bharat Demo Bank is not calling you right now", with the 1600-series explanation. Payment held (G7). |
| `08_authority_fact.png` | T3, digital arrest: the hold leads with the fact card "There is no 'digital arrest' in Indian law. Police never ask for money on a call." |
| `09_console_case.png` | The analyst console for the T1 case: tier and hold, the ln-LR contribution waterfall from the 1-in-400 prior to p = 0.998, all reasons (EN + HI, LR, basis), Release / Confirm / False-positive actions, the guardrail status, the checks, the verified evidence chain, the timeline, the RBAC role badge and the "access logged" notice. |
| `10_split_demo.png` | Demo-control split view at the moment of the hold: the payer phone in Red, Rahul's phone after answering, and the console updated live over WebSockets. |
| `11_hindi_amber.png` | The Amber options in Hindi (Devanagari): "रुको, पहले पहचान करो". Reached by tapping Cancel request on the auto-sent Family Verify, so "Ask Rahul on his phone" is offered again. |
| `13_cue_checklist.png` | SPEC v0.2 A20, T1: a coached "No one" answer would score Green (p 0.13 < 0.15), but the context alone was Amber, so the three-tap checklist (keep it secret, OTP/PIN, arrest threat) still appears, with the context reasons (international caller, unsaved number). |
| `12_green_legit.png` | L2, the real son on his new +44 number (Family Verify auto-sent, he taps Yes): "Rahul confirmed on his own phone that it really is him", which turns the result Green. "Why you saw a check" lists the context, then Pay ₹50,000. |
