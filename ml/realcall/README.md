# Real-call collection (closing the real-call gap)

Round 1 finding: on one real cellular call, every detector (ours included) flagged 91–95 % of genuine
speech as fake (LR 0.93). Voice is therefore in shadow mode until it passes the gate below. This
package collects **consented real phone calls** over Indian networks so we can measure the gap,
retrain on it, and report the false-flag rate before and after.

Everything here runs on the laptop. Keys stay in the repo-root `.env`. Audio, phone numbers and the
participant registry live under `ml/realcall/work/` and `ml/realcall/participants.yaml` (both gitignored).

## The gate (fixed before any real-call training)

Voice moves from shadow to calibrated mode only if, on the **test** split:

- at least **50 live genuine calls** (a real person speaking live, not a replayed recording),
  from callers never used for training; and
- at most **5 %** of those calls are flagged `likely_synthetic`, where a call is scored the way the
  product scores it: one 10 s window (the first 10 s of the call's speech that passes the quality gate);
- reported with the Wilson 95 % upper bound, the chunk-level false-flag rate, and clone detection
  on real-network tapes (`likely_synthetic` rate and EER).

`realcall/gate.py` computes all of it. Thresholds are the deployed ones in `serve/model_config.json`.

## Three kinds of call

| Kind | What travels over the network | Who speaks | Captured where | Automated? |
|---|---|---|---|---|
| **tape** | Vobiz plays a *tape*: genuine team recordings and their clones, shuffled, content-matched (same script lines) | nobody live | the receiving handset, on speakerphone next to the laptop mic (`capture.py`), and/or its dialer recording | yes: `dial.py tape` |
| **live** | an ordinary cellular or WhatsApp call into the test handset | a consented person, live | same as tape | caller dials by hand; `capture.py live` labels it |
| **uplink** | Vobiz calls a speaker's phone and prompts them line by line; optional clone replay into their mic | a consented person, live | Vobiz network side, 16 kHz L16 via `<Stream>` (the bank/IVR view) | yes: `dial.py uplink` |

Why tapes: genuine and clone audio take *exactly* the same path in the same call, so the only thing
that differs is whether the speech is synthetic. Live calls are the gate set, because the false-flag
problem is about real people on real lines. Uplink calls give the bank-side view and 16 kHz audio.

Each tape starts with a sync chirp and ends with another; `ingest.py` finds both by matched filter,
corrects clock drift, then locates every item by local cross-correlation. Items whose correlation
peak is too low (dropped audio, the network's noise suppressor ate it) are marked `qc_fail`, not
silently kept.

## Splits (pre-registered in `realcall/protocol.py`)

- **Test only:** speaker S02 (as in Round 1), generator `sarvam_ivc` (Sarvam instant voice cloning,
  never trained on: the "brand-new generator" for the finale), every call on devices listed as
  `test_devices`, and every live caller listed as `test_callers`.
- Everything else is assigned by a hash of the call ID (tapes) or of the caller ID (live calls), so one
  caller never appears in two splits: 60 % train, 15 % dev, 25 % test.

## Consent rules (enforced in code)

- `dial.py` refuses any number that isn't a registered device of a participant with `record: true`.
- Tapes only contain clones of participants with `clone: true` (S01, S02 signed in Round 1).
- Live-call volunteers only need `record: true` (genuine speech, no cloning). This is the cheapest
  way to get more speakers, which is the actual failure mode.
- Everything is deleted by 31 Dec 2026 (S3 lifecycle + `work/` is local). Logs store phone numbers
  only as salted hashes.

## Setup (once)

1. `pip install soundfile sarvamai sounddevice fastapi uvicorn requests pyyaml websockets`
2. Add to the repo-root `.env`: `VOBIZ_AUTH_ID=MA_...`, `VOBIZ_AUTH_TOKEN=...` (`SARVAM_API_KEY` is already there).
3. `cp realcall/participants.example.yaml realcall/participants.yaml` and fill in real numbers and
   devices; `cp realcall/config.example.yaml realcall/config.yaml` and set `vobiz_number`.
4. Pull the Round 1 team audio (genuine segments, clones, line texts) from S3:
   ```bash
   aws s3 sync s3://pehchaan-ml-301745146083-use1/work/team_seg realcall/work/src/genuine
   aws s3 sync s3://pehchaan-ml-301745146083-use1/work/gen/team realcall/work/src/clone --exclude "refs/*"
   aws s3 cp s3://pehchaan-ml-301745146083-use1/work/manifests/team_bona.csv realcall/work/src/team_bona.csv
   ```
5. Make the Sarvam clones (new held-out generator): `python -m realcall.sarvam_clone`
6. Public HTTPS for the webhook server: `cloudflared tunnel --url http://127.0.0.1:8600` (or Tailscale
   Funnel), then put the printed URL in `config.yaml` as `public_base_url`.

## A collection session (run from `ml/`)

```bash
python -m realcall.server                                   # terminal 1: webhooks, tapes, uplink WebSocket
python -m realcall.capture session --device D2              # terminal 2: laptop mic next to D2 on speakerphone
python -m realcall.dial tape --device D2 --n 10             # terminal 3: 10 tape calls to D2, one after another
python -m realcall.dial tape --device D1 --n 20 --auto-answer --pull   # hands-free: phone on USB with debugging allowed
python -m realcall.phone status                             # adb: connected phone, call state, auto-record setting
python -m realcall.capture live --device D2 --caller V03 --route whatsapp   # a volunteer calls D2 live
python -m realcall.dial uplink --speaker S01 --device D1 --lines 12        # S01 reads lines; network-side capture
python -m realcall.ingest                                   # cut, align, QC -> work/manifests/realcall.csv
python -m realcall.gate --url http://127.0.0.1:8500         # score with the served model -> work/reports/
python -m realcall.status                                   # counts per kind/split vs the targets
```

Phone set-up for tape and live calls: answer on **speakerphone**, volume at about 70 %, phone flat
about 20 cm from the laptop mic, quiet room, no Bluetooth. If the dialer records calls, copy the files
to `work/device_uploads/<device>/` and `ingest.py` will align those as a second capture.

## Targets for this week

| | Target | Why |
|---|---|---|
| live genuine calls, test callers | ≥ 50 | the gate |
| live genuine calls, train callers | ≥ 40 | so retraining sees real-line genuine speech |
| tape calls | ≥ 60 (≈ 1,000 items) | clone detection on real lines + training data |
| uplink calls | ≥ 10 | bank-side view, 16 kHz |
| distinct genuine speakers | ≥ 8 | the Round 1 gap was per-speaker |
| networks | Jio, Airtel, Vi; cellular + WhatsApp | different codecs and noise suppression |

## Then

`work/manifests/realcall.csv` uses the corpus columns (`utt_id, path, label, generator, speaker, lang,
line_id, split, heldout, source, native_channel`) plus call metadata. Append the train/dev rows to
`corpus_src.csv` to fine-tune (rows with a `realcall_*` native channel skip channel simulation),
re-run `gate.py` with the new model, and only promote voice if the gate passes.
