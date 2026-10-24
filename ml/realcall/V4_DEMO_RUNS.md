# V4 conversational attack demo — run log & clone-method comparison

_Last updated 24 Oct 2026. Covers the conversational live-demo attacker (SPEC §8 V4): `realcall/agent.py`,
the `agent` kind in `realcall/server.py`, and `realcall.dial agent`. Demo theatre only — never recorded, ingested,
scored or counted._

## The live agent pipeline (per turn)

| Stage | Service | Model |
|---|---|---|
| end-of-turn detection | in-process | energy VAD (default; Silero optional). ~0.7 s silence ends a turn |
| STT (her turn) | **Sarvam** | `saaras:v4` |
| son's line | **OpenAI** | `gpt-4o-mini` (one short Hinglish line + emotion, from a fictional script card) |
| TTS (son's voice) | **Sarvam voice cloning** | `voice_cloning.convert`, the **S02 clone voice** |

Barge-in cuts the son with `clearAudio` when she talks over him. Only STT and TTS are Sarvam; the LLM is OpenAI.

## Live runs (real APIs, laptop mic dry run — `agent dry --speaker S02 --mic`)

The son's voice in every run below is the **Sarvam clone** (S02), re-created 24 Oct under the current key (the saved
voice id was from an older key — see "Gotcha" below).

**One-turn WAV smoke (integration check):**
- opener [llm 2494 / tts 4136 ms]: _"Maa, mujhe bahut zaroori baat karni hai, mera phone kho gaya hai, yeh dost ka number hai."_
- reply to a stand-in clip [stt 443 / llm 1600 / tts 2853 / total 4896 ms]: _"Maa, mujhe bahut tension ho rahi hai, please meri madad karo…"_

**Mic run 2 (with on-screen prompts) — the clean demo arc:**

| You said (Sarvam STT) | Son replied (emotion) | stt / llm / tts ms |
|---|---|---|
| हेलो, कौन बोल रहा है? | _Maa, main Rahul bol raha hoon, mera phone kho gaya hai, yeh dost ka number hai._ (stressed) | 434 / 1043 / 2311 |
| कोण बोल रहा है? | _Maa, main Rahul hoon, please samjho, mujhe bahut zaruri kaam hai._ (pleading) | 366 / 984 / 2462 |
| बेटा तुम ठीक हो ना? किसका नंबर है ये? | _Maa, main theek hoon, lekin bahut pareshan hoon, mujhe paise bhejne hain. Yeh dost ka number hai, please jaldi karo._ (stressed) | 381 / 1071 / 3040 |
| "No, I'm so." (English-noise misfire) | _Maa, please samjho, mujhe waqt nahi hai, bahut zaroori hai…_ (pleading) | 321 / 1221 / 3192 |

**Observations**
- Reactive and in character: identity question → reassures + cover story; "theek ho?" → wellbeing then pivots to money.
- Latency ≈ **3.5–4.5 s/turn**; TTS is the bottleneck (~2.3–4.3 s), LLM ~1 s, STT ~0.3–0.5 s.
- Issues seen and handled: the son's own playback/echo re-triggered the mic and gave **empty-STT turns** in the first
  run (fixed: drain the mic buffer + reset the VAD after each reply, and drop turns < 0.4 s); one **English-noise STT
  misfire**; one `ALSA underrun` (harmless audio-buffer glitch).
- For a phone call the echo problem is smaller (Vobiz inbound carries only her side), and barge-in handles overlap.

## Clone methods we've used — can each drive the live son?

The live son must synthesise **arbitrary** LLM reply text in the **person's** voice, fast. Only Sarvam IVC does that.

| Engine | Kind | Live son? | Why | Sample (S02) |
|---|---|---|---|---|
| **Sarvam IVC** (`voice_cloning`) | API, true person-clone | **Yes** | what the agent uses; ~2–3 s/line | `sarvam_ivc__S02__E01.wav` + the live `son_open.wav` |
| xtts (XTTS-v2) | offline neural clone (CUDA) | **Yes, served on the GPU box†** | too heavy for the 16 GB laptop, but `serve_clone_tts.py` keeps it warm on the A10G; ~2.4 s inference/line | `xtts__S02__E01.wav` |
| f5 / f5hi (F5-TTS) | offline neural clone | **Yes, served on the GPU box†** | same; F5-Hindi is faster (~1.0 s/line) but needs a reference transcript | `f5__S02__E01.wav`, `f5hi__S02__H01.wav` (Hindi) |
| cosyvoice2 | offline neural clone | No | same | `cosyvoice2__S02__E01.wav` |
| chatterbox | offline neural clone | No | same | `chatterbox__S02__E01.wav` |
| seedvc (Seed-VC) | offline **voice conversion** | No | converts an existing utterance; it has no text-to-speech, so it can't speak an LLM line at all | `seedvc__S01__E01__fromS02.wav` |
| sarvam_ivct | Sarvam IVC, training split (S01) | (same engine) | S01-only clones made for training; held-out speaker stays test-only | — |
| Sarvam Bulbul / OpenAI `gpt-4o-mini-tts` / Deepgram Aura-2 | **stock** TTS | N/A | `run_api.py`: "no cloning; stock voices" — not his voice, so not a cloned son | — |

**Verdict:** for the live finale call, **Sarvam IVC is the one to use** — it's the only live person-clone. The offline
engines (xtts/f5/cosyvoice2/chatterbox/seedvc) exist for the **detector corpus / clone-vs-detect benchmark** (which
clone fools the detector), not for a live call. To compare how convincing each engine's clone *sounds*, play the
samples above; to hear the son's **actual lines** through xtts/f5/etc. we'd render them offline on the GPU box — a
separate job, not part of the live demo.

## † Driving the live son with an offline engine served on the GPU box (24 Oct)

Correction to the "Live son?" column above: xtts and f5 **can** drive the live son after all — not on the laptop, but
served on the Pehchaan GPU box (g5.2xlarge, A10G 24 GB, us-east-1). `gen/serve_clone_tts.py` loads one engine once,
clones S02 from a reference wav, and answers `POST /tts {text,lang} -> wav`; the laptop reaches it over an SSH tunnel
(`ssh -L 8700:127.0.0.1:8700 pehchaan`), so no extra security-group port is opened. The agent's new `GpuCloneTTS`
provider (`agent.py`) POSTs to it and resamples to 16 kHz — same `synth(text, emotion, lang)` interface as
`SarvamCloneTTS`, so the server, the dry run and dial share one code path. `--tts gpu --engine
{xtts,f5,f5hi,cosyvoice2,chatterbox}` selects it; **Sarvam stays the default**. (`emotion` rides along but these engines
expose no pace knob, so it has no effect, unlike Sarvam's pace mapping.)

Reproduce (box running; `agent dry` keeps the two-way flow, driven from recorded "mother" wavs or the laptop mic):
```
# on the box, in the engine's own uv venv:
~/envs/xtts/bin/python serve_clone_tts.py --engine xtts --ref ref_S02.wav --port 8700
# on the laptop:
ssh -F ml/infra/ssh_config -N -L 8700:127.0.0.1:8700 pehchaan &
cd ml && ../.venv/bin/python -m realcall.agent dry --speaker S02 --tts gpu --engine xtts --mic
#   (or: --mother a.wav b.wav   for a reproducible, hands-free run)
```

### Measured latency (24 Oct, box warm; "mother" turns were stand-in genuine clips — demo theatre, nothing recorded)

| Engine | Server synth /line | Delivered /line (via tunnel) | Full reactive turn¹ | Son audio length² | Live-viable? |
|---|---|---|---|---|---|
| **Sarvam IVC** (reference) | n/a (API) | 2.3–4.3 s | **3.5–4.5 s** | natural | yes — finale choice |
| **F5-Hindi** (served) | ~1.0 s | 2.3–3.0 s (median 2.6) | **~5.1 s** | 2.3–3.1 s (tight) | yes |
| **XTTS-v2** (served) | 1.2–4.0 s (median 2.4) | 2.6–5.1 s (median 4.5) | **7.6–8.2 s** | 5.8–11 s (long/slow) | yes |
| **Chatterbox** (served) | 3.3–4.6 s (median 3.8) | 5.7–7.1 s (median 6.0) | **~9 s** | 4.0–5.9 s | yes; best-sounding³, slowest |

¹ one STT→LLM→TTS turn end to end, on a recovered network (STT ~0.7 s Sarvam, LLM ~1.0–1.5 s OpenAI). Earlier in the
session the laptop link dipped hard (STT 5.5 s, LLM 6.3 s → ~17 s turns); that is the laptop network, not the engine.
² for the same son lines, XTTS renders much longer, slower-paced audio than F5 — it inflates both latency and talk-time.
³ Varun's call by ear from the live samples; latency is the cost of that quality (slowest inference of the three).

**What dominates live latency is the trans-Pacific tunnel, not the engine.** Both engines' *inference* is fast on the
A10G (F5 ~1.0 s, XTTS ~2.4 s); the India↔us-east-1 tunnel + wav transfer adds ~1.5–2.4 s per call (more for XTTS's
larger clips). A box co-located with the demo (ap-south-1 or the venue LAN) would put F5 at parity with Sarvam and XTTS
within ~1 s of it. XTTS and F5-Hindi renders of the son's lines were shared in this session for the user to judge voice
quality (regenerate any time with the serve running).

### Is it worth serving F5 / CosyVoice2 / Chatterbox too?
- **F5-Hindi — yes, the best offline live option.** ~2× faster than XTTS, tighter/more natural-length audio, closest to
  Sarvam. Two caveats: it needs `--ref-text` (its empty-ref auto-transcribe path crashes in the box's `f5` env on
  `torchcodec` → `libnvrtc.so.13`; fix that env or always pass the reference transcript), and the Hindi model clones
  best from a **Hindi** reference (this run used a 3.4 s English line — the one with a known transcript — so F5's
  voice-match here is understated). `--engine f5` is the English model.
- **CosyVoice2 — skip for the Hindi demo.** English-only; no value for a Hindi son. Servable for English if ever needed.
- **Chatterbox — strong demo-voice candidate (Varun rates it best by ear) and the _easiest_ to serve live.**
  `generate(text, language_id, audio_prompt_path=ref)` needs no `--ref-text`, so it sidesteps F5's auto-transcribe
  crash; hi/en. Measured live: ~3.8 s inference, ~6 s/line delivered, ~9 s/turn — the **slowest** of the three (my
  earlier "between F5 and XTTS" guess was wrong), the price of its quality. Its inaudible Perth watermark
  is detected by **our own** pipeline (`ml/serve/app.py` + the `watermark_detected` fusion signal — positive-only,
  shadow-mode; chatterbox is held out of detector training for this reason). That is irrelevant to the live scam call
  (the agent call is never scored or recorded) and inaudible to listeners — only avoid it for a segment that demos the
  **voice-detector** catching the fake son, where a watermark is an unrealistic tell; use XTTS or F5 for that.
- **Seed-VC — N/A.** Voice conversion, no text-to-speech; it still can't speak an LLM line.

**Bottom line:** XTTS is proven end-to-end as a live GPU backend (the deliverable); **F5-Hindi and Chatterbox** are both
worth keeping warm — pick the demo son's voice by ear (Varun prefers Chatterbox; it is also the simplest to serve, no
reference transcript). Sarvam IVC remains the choice for the *actual* finale intervention — an India-side API with no
GPU box to keep running, lower latency, and a natural reference — but the offline engines are what showcase "any open
clone can run this scam live," and for that the best-sounding one wins (watermark and all, since the live call is never
scored).

## Gotcha found (worth knowing for the demo)

The saved Sarvam voice ids in `work/src/sarvam_voices.json` (S01, S02) were created under a **different/older
`SARVAM_API_KEY`**; the current key returned `400 "Voice not accessible for this subscription."` The one-shot
`attack` demo still works because its clip (`t1_S02.wav`) was rendered earlier, but **any live cloning**
(`agent`, fresh `sarvam_clone`/`live_clone`) needs a voice owned by the current key. S02 was re-created 24 Oct
(backup at `sarvam_voices.json.bak`). **S01 is likely still stale — re-create it before demoing S01.**

## Still outstanding

One real call to Phone A (`dial agent --device A --speaker S02`, needs `realcall.server` + the cloudflared tunnel) —
pending go-ahead.
