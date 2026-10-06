# Pehchaan prototype app

Three surfaces on one live case, wired through WebSockets:
- the payer's phone (DemoPay, a fictional UPI app "Protected by Pehchaan");
- the relative's phone (Family Verify);
- the Bharat Demo Bank fraud-analyst console.

Everything is fictional (people, numbers, banks, UPI IDs). All context adapters are mocks (`mock_fri`, `mock_i4c`, `mock_bank_registry`, `mock_contacts`, `mock_payer_history`). The voice check uses a self-labelled mock unless `VOICE_SERVICE_URL` is set.

## Run (two terminals)

```bash
# 1. API (FastAPI, port 8400). PEHCHAAN_DEMO_TIME is optional: it runs the demo clock at that IST time.
cd app/server && python -m uvicorn pehchaan_api.main:app --port 8400

# 2. Web (React + Vite, port 5173). First time only: npm install
cd app/web && npm run dev
```

Then open http://127.0.0.1:5173/#/demo for the split view.

Other routes:
- `#/payer?scenario=T1&lang=hi&large=1`: the payer phone on its own.
- `#/relative`: the relative phone; it follows the scenario loaded on the demo page.
- `#/console`: the full analyst console, 1440 px wide.

Point the voice check at the ML service with `VOICE_SERVICE_URL=http://host:port` (the server proxies to `/v1/voice/score`).

## Tests and screenshots

```bash
cd engine && python -m pytest -q        # 45 tests: guardrails, evidence chain/signature, simulator parity
cd app/server && python -m pytest -q    # 15 tests: all flows, RBAC, signatures, voice gate; writes latency.json
python app/screenshots/shoot.py         # needs both servers running; writes the 12 deck PNGs (about 30 s)
```

## Scenarios (`POST /v1/demo/scenario/{name}`)

| ID | Story | What happens |
|---|---|---|
| T1 | A cloned "Rahul" calls Sunita from an unknown +44 WhatsApp number and asks for ₹50,000 to "Arif Traders". | One-tap question; naming Rahul sends Family Verify automatically (SPEC v0.2 A19). The real Rahul's phone says "No, that's not me", so G7 (decisive floor) puts it in a Red 30-minute hold. She cancels and the report is pre-filled. |
| L2 | The real Rahul, on his new +44 number, asks for ₹50,000 to "Rahul Sharma". | Same Amber context as T1. Family Verify gets "Yes, it's me", the result goes Green and she pays. One tap of friction. |
| L1 | Sunita pays her friend Meena ₹2,000 while on a call with her. | The trigger fires (new payee, active call), but the context is clearly benign. She goes straight to the PIN screen with no Pehchaan screen. |
| T2 | A "fraud department" caller on a 10-digit mobile (not 1600) asks Ramesh to move ₹35,000. | He picks **My bank**, then **Bharat Demo Bank**, which gives Amber with "Check with Bharat Demo Bank". The integrated registry shows no active call, so G7 holds the payment. If he names **Another bank** instead, the lookup returns `bank_registry_unknown` (LR 1): it stays Amber with "hang up and call the official number". |
| T3 | A fake CBI officer on a 47-minute WhatsApp call demands a ₹1,80,000 "settlement". | Authority claim goes straight to a Red hold with the fact card "There is no 'digital arrest' in Indian law". |

## Finale demo script (about 4 minutes)

1. **Set-up (20 s).** Open `#/demo` on the projector and click **T1**.
   - Say: "Sunita is on a WhatsApp call. The voice sounds exactly like her son Rahul. He says there's been an accident and asks for ₹50,000." For V4, play the consented cloned-voice call here.
2. **The pay tap (20 s).** Tap **Pay ₹50,000**. Pehchaan asks one question: *Who asked you to make this payment?* Tap **Family member**, then **Rahul**.
   - The Family Verify push goes out on its own: "We've asked Rahul to confirm on his own phone", with a small **Cancel request** link (SPEC v0.2 A19).
3. **Verify the person (40 s).** Rahul's phone (middle) lights up. Read the prompt aloud and tap **No, that's not me**.
   - Cancel request, if you want to show it, returns to the Amber screen with the two plain reasons (it never says "scam"), and Family Verify can be sent again from there.
   - All three screens update together. Sunita's payment is held for 30 minutes. The console shows the case in Red with the waterfall: the out-of-band "not me" is the decisive bar, not the voice.
4. **Report (30 s).** Tap **Cancel and report**.
   - Show the signed pack: the case ID, the SHA-256 chain, and the 1930, cybercrime.gov.in and Chakshu fields already filled in.
   - Say: "We never file for her. She decides."
5. **The false-positive story (40 s).** Click **L2**. It is the same +44 setup, but this time the real Rahul taps **Yes, it's me**, and she pays.
   - Say: "Same context, one tap, done. Genuine families aren't punished for living abroad."
6. **Voice is a clue, not the judge (30 s, optional).** On T1 at the Amber screen, tap **Check the caller's voice** and choose a demo clip, or upload a WAV / record from the speakerphone.
   - Show the quality gate and the "one clue, not proof" copy.
   - The detector runs in **shadow mode**. The payer sees "Thanks — this is saved with your case. Voice checks can't yet confirm who is calling on a phone line…", and the console shows the score with a "shadow: not used in decision" badge.
   - Say: "Our detector gets 4.8% EER on simulated phone lines, but a real cellular call fooled every detector, so it doesn't vote until it passes a real-call gate." 
7. **Bank and police (40 s).**
   - Click **T2** and pick **My bank**, then **Bharat Demo Bank**, then **Check with Bharat Demo Bank**. Result: "Bharat Demo Bank is not calling you right now."
   - Click **T3** and pick **Police, CBI or Govt** to show the "no digital arrest" fact card.
8. **Coached "no one" (20 s, optional).** On T1, answer **No one**. The claim alone would make it Green, but the context was Amber, so the checklist still appears (SPEC v0.2 A20). The three-question checklist appears (secrecy, OTP/PIN, arrest threat); ticking "keep it secret" raises the risk.
9. **Analyst (20 s).** In the console, open the T1 case.
   - Show the guardrail notes and the access-logged banner.
   - Click **Confirm scam and report**, which flags the payee VPA to the PSP.

Fallbacks:
- If a WebSocket drops, the clients reconnect automatically; reload the page if needed.
- `POST /v1/demo/fv/{challenge_id}/timeout` forces a Family Verify timeout. The result is still Amber, with callback and safe word offered.

## Layout

- `server/pehchaan_api/`: `main.py` (routes, WebSockets, RBAC), `risk.py` (case service: context → signals → engine, holds, Family Verify), `adapters.py` (mocks), `voice.py` (proxy or mock, demo audio), `scenarios.py` (seeds), `db.py` (SQLite).
- `web/src/`: `PayerPhone.tsx`, `RelativePhone.tsx`, `Console.tsx`, `App.tsx` (router and demo split), `components.tsx` (seal, device frame, rings, waterfall), `i18n.ts` (EN/HI copy).
- `screenshots/`: `shoot.py` and the PNGs. `NOTES.md` holds the SPEC deviations and proposals.
