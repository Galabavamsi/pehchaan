# CLAUDE.md: Pehchaan (team humanslop, RAKSHAM Track 01)

Read `HANDOVER.md` (full context) and `TASKS.md` (what's left, day plan, final checklist) before doing work.
The finale is **24–25 Oct 2026 at IIT Delhi**, 09:00–19:00 each day, and **everything must be built and tested
before 24 Oct**. On site is for validating, polishing and presenting.

## What the product is
Pehchaan protects UPI and bank payers from voice-cloning fraud by **verifying the person, not the voice**:
- a risky payment during or after a call triggers *"Who asked you to pay?"*;
- the claim is checked out of band (Family Verify on the relative's own phone, the bank call registry, a safe
  word);
- the result is GO / PAUSE / HOLD.

The voice detector is a supporting clue in **shadow mode**; it can never hold money (guardrail G2).

## Rules (don't break these)
- **Consent:**
  - Only clone or record people with a saved consent form. `ml/realcall/consent.py` enforces it; don't bypass it.
  - No real people's voices from the internet, ever.
  - Demo screens use fictional names, banks and UPI IDs.
- **Secrets:**
  - Keys live only in the repo-root `.env`.
  - Phone numbers live only in `ml/realcall/participants.yaml`; audio only in `data/raw/` and
    `ml/realcall/work/`. All of these are gitignored.
  - Never commit, print or paste them, and never copy `.env` to a cloud box.
- **Numbers:**
  - Every number on a slide must trace to `ml/results/metrics.json`, `ml/realcall/FINDINGS.md` or
    `engine/results/deck_numbers.json`.
  - Don't round in our favour; keep the caveats.
- **Protocol:** splits and the gate are pre-registered in `ml/realcall/protocol.py`. Don't change them after
  looking at test results; add a dated note if you change them at all.
- **Spec first:** product or detection-logic changes go into `SPEC.md` before code.
- **Cloud:**
  - Stop GPU instances when idle (the retrain script stops itself).
  - Don't touch resources that aren't Pehchaan's: the `urumi-vps` and `t9984-speech-recorder` instances (paused),
    and the jalsakshi, charter and urumi DNS records.
  - Ask before anything that costs real money or is visible outside (support cases, posts, DNS changes).

## Where things are
- `engine/`: fusion engine and simulator (pytest).
- `app/server`: FastAPI risk API (pytest).
- `app/web`: React demo.
- `ml/`: detector training, evaluation and serving.
- `ml/realcall/`: real phone-call collection, the learned channel, comparison (pytest in `realcall/tests`).
- `ml/infra/`: GPU box scripts.
- `deck/`: pitch deck source.

## Commands
```bash
cd engine && python -m pytest -q
```
```bash
cd app/server && python -m pytest -q
```
```bash
cd ml && python -m pytest -q realcall/tests
```
```bash
cd app/server && python -m uvicorn pehchaan_api.main:app --port 8400
```
```bash
cd app/web && npm run dev
```
```bash
python deck/build.py
```

## Environment gotchas (Windows laptop)
- Use the Bash tool with POSIX syntax. Long inline Python heredocs with nested quotes break: write a temp `.py` file.
- Set `PYTHONIOENCODING=utf-8` when printing Hindi/Telugu.
- `git status` may show CRLF-only changes; check real changes with `git diff --ignore-cr-at-eol --stat`.
- The AWS MCP connector drops tools mid-session. Reload it with ToolSearch, or use the AWS CLI (configured on the laptop).
- adb lives at `%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`; cloudflared at `C:\Program Files (x86)\cloudflared\`.
- The GPU launch template attaches the default security group; swap it to `pehchaan-ml-ssh` or SSH times out.
