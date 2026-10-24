# Verification signals that complement (or replace) acoustic deepfake detection for voice-clone payment fraud (2024–2026)

Research date: 24 Oct 2026 (finale day 1). Scope: signals that sit beside, or instead of, a "is this voice synthetic?" classifier inside a UPI/bank app (Pehchaan). Evidence labels used throughout:

- **[M-PR]** measured, peer-reviewed.
- **[M-pre]** measured, arXiv preprint, not yet peer-reviewed. Many 2026 items are this kind.
- **[V]** vendor claim, not independently verified.
- **[Reg]** regulator or government source.
- **[Press]** news report.
- **[Internal]** Pehchaan's own measurement. Slide-traceable only if it is in `ml/results/metrics.json`, `ml/realcall/FINDINGS.md` or `engine/results/deck_numbers.json`.

Anything before 2024 is marked *background*.

Pehchaan already has these signals (per `SPEC.md` §3):
- call context: unknown, international or VoIP caller; `bank_claim_not_1600`; DoT FRI tier (mocked); long call;
- payment context;
- voice provenance in shadow mode, plus a Perth watermark check;
- opt-in script cues (ASR or a 3-question tap checklist);
- out-of-band checks: Family Verify (device-signed), callback, safe word, the bank's outbound-call registry;
- a 30-minute cooling-off hold.

The findings below are therefore framed as (a) evidence for what Pehchaan already does and (b) genuinely new signals.

---

## 1. Challenge-response / liveness for live calls (PITCH and successors; real-time VC latency; "ask what only they know")

### Takeaway
Active challenges measurably raise detection of **real-time voice conversion (VC)**: PITCH lifts machine AUROC from 56% with no challenge to 88.7% with its 10 best challenges, and DF-CAPTCHA beats passive detectors by 20–29 percentage points in audio. However, every published evaluation used older research VC models (FreeVC, StarGANv2-VC, PPG-VC), not 2025–26 commercial cloners. Modern streaming VC runs at roughly 60–430 ms latency, so timing alone will not expose it. The strongest "liveness" for Pehchaan's threat is still a secret or a channel the cloner cannot reach. Challenges are best used as a cheap, human-in-the-loop escalation, and they are especially useful against **typed-TTS attackers** (the Sarvam-style attack), who cannot whisper, hum or answer instantly.

### Cited Findings
- **PITCH (ACM AsiaCCS 2025) [M-PR]:**
  - Dataset: 18,600 genuine and 1.6M deepfake samples from 100 users.
  - Machine AUROC: 56.0% with no challenge, 88.7% averaged over the 10 best challenges.
  - Humans: 72.6% accuracy on a hard balanced subset (machine 87.7%); human plus AI: 84.5%.
  - Source: [arXiv 2402.18085](https://arxiv.org/abs/2402.18085).
- **PITCH per-challenge AUC [M-PR]:**
  - Most effective: instrumental playback 98, cup mouth 97, foreign words 97, whisper 92, crosstalk 90, high pitch 86, static mouth 85, lyric playback 85, emotions 82.
  - Below 70 and disqualified: accent 57, read slowly 55, clap 51, cough/whistle 54, hold nose 63, low pitch 65, speak loudly 62.
  - Nose-holding had only 43% compliance even among genuine speakers.
  - Source: [PITCH, Table 3](https://arxiv.org/abs/2402.18085).
- **PITCH threat model [M-PR]:** tested against FreeVC (main), StarGANv2-VC and PPG-VC, with AUC about 88.2–88.3% on the latter two. Six of D-CAPTCHA's nine original tasks were ineffective against FreeVC. The authors attribute the remaining effect to two weaknesses: VC models are limited by training-data diversity, and they "do not encode the physiology and physics of human speech". Source: [arXiv 2402.18085](https://arxiv.org/abs/2402.18085).
- **DF-CAPTCHA (Sept 2026) [M-pre]:**
  - Verifies four things: realism, identity consistency, task completion, and response time (the response must start within about 1 s).
  - Audio task-verification AUC: cough 1.0, hum 0.999, playback 0.998, sing 0.993, repeat-accent 0.864.
  - Beats the best passive detector by 20–29 pp in audio.
  - Best audio detector with a challenge: AUC 0.978 (GMM on talk-and-clap), against 0.949 without.
  - One detector (SpecRNet) got *worse* under challenges: 0.952 down to 0.538.
  - The top audio RT-DF it evaluated was StarGANv2-VC.
  - Limitations it states: it does not address pre-recorded deepfakes; challenges may lose effect as models improve; friction; false positives under poor recording conditions.
  - Source: [arXiv 2609.11404](https://arxiv.org/abs/2609.11404).
- **D-CAPTCHA++ (2024) [M-pre]:** transferable imperceptible adversarial perturbations can fool the original D-CAPTCHA detectors and task classifiers; adversarial training mitigates this. Source: [arXiv 2409.07390](https://arxiv.org/abs/2409.07390). D-CAPTCHA itself (Yasur et al., 2023) is *background*.
- **Real-time VC latency in 2024–26:**
  - Seed-VC README: about 300 ms algorithmic delay plus about 100 ms device delay; about 430 ms end to end on an RTX 3060 Laptop [V/README] ([HF mirror of Seed-VC README](https://www.huggingface.co/RedRepter/seed-vc-api)).
  - MeanVC 2: 110 ms, down from 211 ms, with 40 ms chunks [M-pre] ([arXiv 2606.09050](https://arxiv.org/abs/2606.09050)).
  - RT-VC: 61.4 ms on CPU [M-pre] ([arXiv 2506.10289](https://arxiv.org/abs/2506.10289)).
  - SynthVC: 77.1 ms end to end [M-pre] ([arXiv 2510.09245](https://arxiv.org/abs/2510.09245)).
  - X-VC: 240 ms model-induced latency [M-pre] ([arXiv 2604.12456](https://arxiv.org/abs/2604.12456)).
  - Voice *style* conversion (timbre, accent and emotion): StyleStream 2.0 at 520 ms, down from about 1 s [M-pre] ([arXiv 2610.28940](https://arxiv.org/abs/2610.28940)).
- **CallShield, "a secret only they know", done cryptographically (Jan 2026) [M-pre]:**
  - Embeds an HMAC challenge-response in live 8 kHz call audio: 1 bit per 40 ms frame (25 bps), with BCH error correction and retransmission.
  - Uses pairwise keys shared offline between trusted contacts.
  - Authentication success: 99.2% on clean audio, over 95% under telephony distortions; 0% false acceptance without the key.
  - Takes an average of **63 s** per call; PESQ above 4.2.
  - Needs the app on both endpoints.
  - States that AudioSeal, SilentCipher, WMCodec and Timbre need clips of 1 s or more at above 8 kHz, so they are unsuitable for live narrowband calls.
  - Source: [arXiv 2601.09327](https://arxiv.org/abs/2601.09327).
- **Graduated actions in a network-edge detector (Oct 2026) [M-pre]:** SENTRY outputs LOG / CHALLENGE / DROP rather than a binary verdict, which is a design precedent for "challenge only on suspicion". It reports 5.05% EER on ASVspoof 2019 LA over an 8 kHz µ-law channel; ASVspoof 2019 is an old benchmark, and SENTRY leaves generalization to unseen generators open. Source: [arXiv 2610.24468](https://arxiv.org/abs/2610.24468).
- **Knowledge questions and safe words:**
  - The FBI PSA I-120324-PSA (3 Dec 2024) advises: "Create a secret word or phrase with your family to verify their identity". It also advises hanging up and calling back on a number you look up yourself [Reg] ([IC3](https://www.ic3.gov/PSA/2024/PSA241203)).
  - Starling Bank's "Safe Phrases" campaign (Sept 2024) advises agreeing a phrase and never sharing it digitally [Press] ([LBC](https://www.lbc.co.uk/tech/10673c0432c44540821b4277394926a8)).

### Inferences
- **Challenges target VC, not TTS.** All the measured gains come from attacking *real-time voice conversion*, where the attacker speaks and a model re-voices them.
  - Pehchaan's Sarvam result was a **cloned TTS** attack: Sarvam instant voice cloning (`sarvam_ivc`) playing pre-generated script clips. Per `ml/realcall/FINDINGS.md`, both detectors caught 0/12 (95% CI 0–24%).
  - A TTS operator cannot whisper, hum, cup their mouth or answer a random question within about 1 s. A challenge plus a response-time check is therefore likely *more* effective against Sarvam-style attacks than against the VC models in PITCH.
  - This is an untested inference. It can be measured on site with consented team voices: ask the clone pipeline to "whisper the word X" or "hum Happy Birthday".
- **Timing alone won't catch modern VC.** Streaming VC adds 60–430 ms, which is within normal conversational turn gaps. Only typed-TTS attacks add multi-second delays.
- **Product fit.** A randomised challenge is a **human-in-the-loop** step: "Ask them to whisper your pet's name, then speak a sentence in Telugu." The user reports the outcome, and Pehchaan logs `challenge_failed` or `challenge_passed`.
  - This fits Pehchaan's "verify the person" framing without needing the voice detector to be trusted.
  - It should never be decisive on its own, for three reasons: PITCH shows humans alone reach only 72.6%, genuine callers under stress or in noise fail too, and challenges age as generators improve.
- **Keyed proofs beat in-band challenges.** CallShield shows a keyed proof can travel *inside* the call, but it takes 63 s and needs both phones to run the app. Family Verify, a signed push to the relative's own phone, achieves the same binding faster and out of band. CallShield belongs on a roadmap as "works even when the relative has no data connection", not in a 2-day build.

| Signal | How it works | Evidence | Limits / attacks | Who integrates | Privacy | 1.5-day prototype? |
|---|---|---|---|---|---|---|
| Human-in-the-loop randomised challenge (PITCH-lite) | App suggests 1–2 random tasks (whisper, foreign word, hum, interrupt); user reports pass or fail and time to respond | PITCH AUROC 56% to 88.7% (machine), human plus AI 84.5% [M-PR]; DF-CAPTCHA +20–29 pp [M-pre] | Tested on 2021–23 VC only; human judgement weak (72.6%); genuine callers fail in noise; adaptive attackers can pre-generate | Pehchaan app only | No audio needed if self-reported | **Yes**: UI step plus signal, a few hours |
| Machine-scored challenge (capture the response and score degradation or compliance) | Speakerphone capture of the challenge response, then compliance/quality scoring | Same as above | Needs audio capture; phone-channel degradation (see §2, §3) | Pehchaan plus Voice Provenance Service | Audio capture, consent | Partial: capture exists, but scoring is unvalidated |
| Safe word | Pre-agreed family phrase | FBI PSA [Reg], Starling [Press]; no outcome data found | Victim forgets to ask under stress; phrase leaks if shared digitally | App prompts at the right moment | Phrase never leaves the device if hashed | Already in Pehchaan |
| In-band keyed call authentication (CallShield) | HMAC challenge-response embedded as 25 bps watermark in call audio | 99.2% clean / >95% distorted, 0% FAR, 63 s [M-pre] | Both endpoints need the app; slow; replay assumptions | OS or dialer vendors, families | Keys only, no transcript | No (roadmap) |

### Gaps
- No published challenge-response evaluation against 2025–26 commercial zero-shot cloners (ElevenLabs, Sarvam, Chatterbox) or against typed-TTS operators. This is the key open question, and Pehchaan can measure it.
- No field data on how often real victims actually ask a safe word or challenge before paying, or on its false-reject rate.
- Seed-VC latency figures come from the project's own README (mirror), not an independent benchmark.

---

## 2. Audio watermarking and provenance (AudioSeal, SynthID, Perth, WavMark, C2PA): who watermarks, phone-codec robustness, detector availability

### Takeaway
Watermarks are a **positive-only** clue: a hit is strong evidence, absence proves nothing. They only work if the attacker used a cooperating generator *and* the mark survives the call.
- **Sarvam documents no watermark**, so the generator that beat Pehchaan's detector is invisible to watermark checks.
- Pehchaan's own test shows Perth survives Opus and PSTN simulation (100%) but **mostly not AMR-NB (29.8%)**.
- 2026 preprints show that noise plus generative speech enhancement strips AudioSeal, WavMark, SilentCipher and Perth to 4% or less.
- C2PA is file metadata and cannot cross a phone call.

### Cited Findings
- **Who watermarks today:**
  - **ElevenLabs:**
    - Embeds Google DeepMind's **SynthID**. Coverage is phased: currently all free-tier TTS and "select paid features" [V] ([ElevenLabs help: SynthID](https://elevenlabs.io/docs/help-center/legal/audio-detector/what-is-synth-id-and-why-is-eleven-labs-using-it)).
    - Its Audio Detector only detects ElevenLabs-embedded marks; third-party models on ElevenLabs are "generally not watermarked" [V] (same source).
    - The detector requires sign-in, and no API is mentioned [V] ([ElevenLabs Audio Detector docs](https://elevenlabs.io/docs/eleven-creative/audio-tools/audio-detector)).
    - Its legacy classifier reports 99% precision and 80% recall on *unmodified* ElevenLabs audio [V] (same).
  - **Google:**
    - SynthID marks Lyria music and NotebookLM audio.
    - The **SynthID Detector** portal opened to the public on **7 Oct 2026** (synthid.com; free; sign-in required). It also checks partner content from OpenAI, NVIDIA and Kakao, with Apple "coming soon".
    - It is "not a general AI detector", and no accuracy figures have been published [Press] ([IT-Connect](https://www.it-connect.fr/google-synthid-detector-grand-public/); [BestForAndroid](https://bestforandroid.com/radar/synthid-detector-went-public-check-photo-video-ai-watermarks/)).
    - It had been limited to testers since May 2025 [Press] ([Gigazine](https://www.gigazine.net/gsc_news/en/20250521-google-synthid-detector/)).
    - Google Cloud's **Chirp 3 Instant Custom Voice** requires a spoken consent statement, but its docs do not mention SynthID ([Google Cloud docs](https://docs.cloud.google.com/text-to-speech/docs/chirp3-instant-custom-voice)).
  - **Resemble (Chatterbox, MIT licence):** the **Perth** watermark is on every output, and the README claims it survives MP3 and editing with "nearly 100%" detection [V] ([GitHub resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox)). Because the model is open source, an attacker can delete the watermark call (noted in the team's `research/track01_voice_cloning.md`).
  - **Microsoft Azure personal voice:** watermarks are added to output; a reported 99.7% detection on personal-voice audio [V via Press] ([MediaNama](https://www.medianama.com/2024/05/223-truecaller-partners-with-microsoft-for-personalized-voice-ai-assistant/)). It is a Limited Access feature.
  - **OpenAI Voice Engine** (Mar 2024 limited preview): OpenAI stated it uses watermarking to trace audio, and required consent from partners [Press] ([Al Jazeera](https://www.aljazeera.com/amp/economy/2024/4/1/openai-unveils-voice-cloning-tool-but-deems-it-too-risky-for-public-release)). I found nothing on watermarking of current gpt-realtime custom voices.
  - **Sarvam:**
    - Its creative voice-cloning docs describe only a mandatory consent checkbox and a live, roughly 10 s in-browser recording.
    - There is **no mention of watermarking, provenance, a detector or C2PA** ([Sarvam docs](https://docs.sarvam.ai/creative-voice-cloning.md)).
    - Instant Voice Cloning (beta) was exposed in the Python and TypeScript SDKs on 12 Oct 2026 ([Sarvam changelog](https://docs.sarvam.ai/changelog/2026/10/12)).
- **Pehchaan's own Perth test [Internal, slide-traceable: `ml/results/metrics.json` → `watermark_perth`]:**
  - Chatterbox clips (n=57) detected at: clean 100%, Opus 100%, PSTN 100%, replay 87.7%, **AMR 29.8%**.
  - Non-Chatterbox clips (n=150) falsely detected at: 0% clean, AMR and PSTN; 0.7% Opus; 6.7% replay.
- **Speech enhancement as a removal attack (Sept 2026) [M-pre]:**
  - Unattacked, all six watermarks are detected at TPR 99.5–100%.
  - EnCodec 24 kbps re-synthesis leaves AudioSeal at 100% and Perth at 60%, but removes WavMark, SilentCipher and Timbre.
  - The BigVGAN vocoder removes AudioSeal (0%) but leaves Perth at 100%.
  - LM-based generative speech enhancement (GenSE, UniSE) removes everything except AlignMark.
  - Gaussian noise at 20 dB followed by FlowSE or SGMSE drives AudioSeal, WavMark, SilentCipher and Perth to 4% or less.
  - Source: [arXiv 2609.29040](https://arxiv.org/abs/2609.29040).
- **Training-free structural removal (Aug 2026) [M-pre]:** one domain-matched attack erases the WavMark, SilentCipher and audiowmark payloads, or removes AudioSeal's detection flag, at PESQ ≥ 3.6. Latent-domain marks (VoiceMark, WMCodec, AlignMark, AWARE) resisted every training-free attack tried. Source: [arXiv 2608.16566](https://arxiv.org/abs/2608.16566).
- **RAW-Bench (May 2025) [M-pre]:** neural compression is the hardest distortion, even when methods are trained against it; polarity inversion, time-stretch and reverb break some methods. Source: [arXiv 2505.19663](https://arxiv.org/abs/2505.19663).
- **Mitigations under research [M-pre]:**
  - Codec-latent watermarks: Latent-Mark ([arXiv 2603.05310](https://arxiv.org/abs/2603.05310)) and CRAW ([arXiv 2609.03107](https://arxiv.org/abs/2609.03107)).
  - Multiplexing AudioSeal with PerTh: TPR@1%FPR rises from 0.75 to 0.88 with a learned router ([arXiv 2511.02278](https://arxiv.org/abs/2511.02278)).
  - AudioSeal itself is ICML 2024 [M-PR] ([arXiv 2401.17264](https://arxiv.org/abs/2401.17264)).
- **C2PA:** Content Credentials (spec v2.4) support MP3, WAV and AIFF [Reg/standards body] ([C2PA deployment guidance, Jul 2026](https://c2pa.org/wp-content/uploads/sites/33/2026/07/Content-Credentials-Deployment-Guidance.pdf)).

### Inferences
- **Watermarks don't help against the observed threat.** A watermark check cannot catch the attack that beat Pehchaan's detector: Sarvam publishes no watermark, and a scammer can choose a non-watermarking or open-source model. Keep `watermark_detected` as a capped positive-only signal, which Pehchaan already does (LR 50 capped at 8), and say so explicitly on the slide.
- **AMR-NB is the binding constraint.** AMR-NB is the default narrowband cellular codec for 2G/3G and VoLTE fallback, so the 29.8% Perth survival through AMR is the most relevant phone-channel number. The Opus and PSTN results suggest WhatsApp/OTT calls preserve Perth better than cellular AMR. This is an inference from simulated codecs only, not from real calls.
- **C2PA cannot cross a call.** It is a signed manifest attached to a *file*. A phone call carries only re-encoded audio samples, so C2PA provenance cannot reach a call recipient. It is useful only for files (for example, voice notes forwarded on WhatsApp, if the app preserves metadata). This is an inference; I found no C2PA work on telephony.
- **Detector access is a deployment blocker.** SynthID and ElevenLabs detection are web portals behind sign-in, with no public API documented. Bank-side integration would need a commercial agreement. This belongs on the roadmap.

| Signal | How it works | Evidence | Limits / attacks | Who integrates | Privacy | 1.5-day prototype? |
|---|---|---|---|---|---|---|
| Perth/AudioSeal watermark check on captured call audio | Run the open detectors on the 8–12 s capture | Perth: AMR 29.8%, Opus/PSTN 100% [Internal]; removable by SE [M-pre] | Only cooperating generators; open-source code removable; Sarvam not covered | Pehchaan (open models) | Same capture as voice check | Perth done; AudioSeal could be added in hours, but low value |
| SynthID / ElevenLabs detector | Vendor portal checks for vendor marks | No public accuracy figures [V/Press] | No API; vendor-specific; partner list | Bank with Google / ElevenLabs agreements | Audio sent to vendor | No (roadmap) |
| C2PA manifests | Signed metadata on files | Spec supports audio files [Reg] | Lost in any phone call | Generators plus messaging apps | Low | No (not applicable to calls) |

### Gaps
- I found no evaluation of any production watermark (SynthID, Perth, AudioSeal) through **real** cellular calls (AMR-NB/AMR-WB/EVS on a live network) rather than simulated codecs.
- I could not confirm whether Sarvam, Google Chirp 3 custom voice or OpenAI's current voice products watermark output. The absence of documentation is not proof that there is no watermark.
- SynthID Detector has published no accuracy or false-positive data.

---

## 3. Speaker verification as a signal, and spoofing-aware speaker verification (SASV)

### Takeaway
Speaker verification (SV) answers "same voice?", and a good clone is designed to say yes. In a 2026 test, open-source clones trained on 20 minutes of target speech bypassed a state-of-the-art SV system 43–83% of the time at a 0.01% false-accept threshold. SASV systems post 1–2% EER in-domain but still struggle across domains. Voice biometrics is being publicly abandoned as an authenticator. For Pehchaan, SV would add biometric enrolment of family members for little gain. At most, a mismatch is a weak negative clue against low-effort, non-cloned impersonators.

### Cited Findings
- **SV bypass by clones (Jan 2026) [M-pre]:**
  - Setup: an ECAPA-TDNN SV system tuned to 0.01% FAR on genuine impostors; 50 Mandarin speakers (AISHELL-3); 20 minutes of target speech per speaker.
  - Bypass rates: GPT-SoVITS 56.2%, Bert-VITS2 82.7%, RVC 43.1%. Average cosine similarity of attacks was 0.56–0.68, against a typical genuine range of 0.6–0.8.
  - XLS-R+AASIST countermeasure: 0.83% EER in-domain, but it "struggle[s] to generalize" to eight unseen TTS systems.
  - Source: [arXiv 2601.02914](https://arxiv.org/abs/2601.02914).
- **SASV state of the art [M-pre]:**
  - SASV-EER of 1.22% on ASVspoof 2019 LA ([ELEAT-SAGA, arXiv 2602.13761](https://arxiv.org/abs/2602.13761)).
  - WildSpoof 2026 SASV entry: SASV-EER 2.08%, but results on unseen ASVspoof5 "highlight the critical challenge of cross-domain generalization" ([arXiv 2601.17557](https://arxiv.org/abs/2601.17557)).
  - ASVspoof 5: min a-DCF 0.196 and spoof EER 7.6% with nonlinear fusion ([arXiv 2510.01818](https://arxiv.org/abs/2510.01818)).
  - Shared W2V-BERT encoder: 0.092 min a-DCF and 3.60% CM-EER on ASVspoof5 ([arXiv 2610.08845](https://arxiv.org/abs/2610.08845)).
  - Large audio-language models are "near chance" zero-shot for SASV ([arXiv 2607.14753](https://arxiv.org/abs/2607.14753)).
- **Channel effects [M-pre]:**
  - RealComm (Oct 2026): detectors "reveal substantial degradation after call transmission"; one detector's EER fell only from 37.94% to 22.37% after real-call training ([arXiv 2610.27459](https://arxiv.org/abs/2610.27459)).
  - Building datasets "presented" through phone channels improved detection 39% in lab and 57% on a real-world benchmark ([arXiv 2509.26471](https://arxiv.org/abs/2509.26471)).
  - RTCFake: about 600 h of deepfake speech passed through Zoom and similar platforms ([arXiv 2604.23742](https://arxiv.org/abs/2604.23742)).
- **Industry stance:**
  - Sam Altman, 22 Jul 2025, at a Federal Reserve conference: accepting voiceprints is "a crazy thing to still be doing… AI has fully defeated that" [Press] ([PYMNTS](https://www.pymnts.com/news/2025/sam-altman-says-ai-has-defeated-bank-voice-id-protections/); [WSLS/AP](https://www.wsls.com/business/2025/07/22/openais-sam-altman-warns-of-ai-voice-fraud-crisis-in-banking/)).
  - The team's `research/track01_voice_cloning.md` records Amazon Connect Voice ID end of support on 20 May 2026 ([AWS docs](https://docs.aws.amazon.com/connect/latest/adminguide/amazonconnect-voiceid-end-of-support.html)). I did not re-verify this.

### Inferences
- **Use SV only as a negative clue.** A "different speaker" result is mild evidence of a *non-clone* impersonator, the classic "it's me, I have a cold" scam. A "same speaker" result is worthless against clones, so SV should never reassure (the same rule as Pehchaan's `voice_no_strong_evidence` LR 1.0).
- **The privacy cost is high.** It needs enrolled voiceprints of relatives, which is biometric data. It also brings consent burdens, and that data is itself cloning material if leaked. Not worth adding.
- **External support for shadow mode.** RealComm and the "presentation" paper independently support Pehchaan's finding that detectors trained on clean audio fail on real calls.

| Signal | Evidence | Limits | Who integrates | Privacy | 1.5-day? |
|---|---|---|---|---|---|
| SV of caller against an enrolled relative | 43–83% clone bypass at 0.01% FAR [M-pre] | Clones pass; channel mismatch; enrolment burden | App plus family enrolment | Biometric templates of third parties | Technically possible, **not recommended** |
| SASV (SV plus countermeasure fusion) | 1–2% EER in-domain [M-pre] | Cross-domain generalization unsolved | Bank IVR or contact centre | Biometric | No |

### Gaps
- No SASV evaluation on Indian-language commercial clones over real Indian cellular calls.
- No public data on the false-reject rate of SV for the same speaker across a handset call versus a reference recording.

---

## 4. Behavioural and context signals: active call during payment, remote access / screen sharing, coaching cues, device binding, telco metadata (CNAP, call origin, VoIP)

### Takeaway
"On a call while paying a new payee" is now an industry-standard signal, and Pehchaan's trigger already uses it:
- BioCatch sells it.
- Monzo, CommBank and Standard Bank ship in-app "is the bank really calling?" checks.
- Google ships OS-level warnings in India for screen-sharing during calls (GPay, Paytm, Navi).

India's telco layer is changing **this week**:
- CNAP, showing the operator's KYC name, starts on 4G/5G from **1 Nov 2026** and labels international calls.
- Banks must call from 1600-series numbers (banks by 1 Jan 2026).
- DoT FRI tiers are live and integrated by PhonePe.

The most useful *new* signals for Pehchaan are CNAP-name mismatch and screen-share or remote-access during the call.

### Cited Findings
- **BioCatch Scams360 [V]:** looks for an active call during a transfer, hesitation, erratic typing and long inactivity ([BioCatch press release](https://www.biocatch.com/press-release/biocatch-delivers-scams360)). Its case study claims call status gives a "10–15% detection uplift", and that a top-5 UK bank saved £250K–£500K per month over four months [V] ([BioCatch case study PDF](https://www.biocatch.com/hubfs/Case_Studies/BC%20CS%20APP%20Fraud%20V6.pdf?hsLang=en)). A vendor chart claiming that 90% of fraud payments happen on an active call has no traceable origin; treat it as unverified.
- **Bank "is it really us calling?" checks, direct precedents for Pehchaan's bank registry:**
  - **Monzo "call status"** (Sept 2023, described as a UK first): the app shows whether a Monzo employee is on the line; if not, the user is told to hang up and can report it ([Android Developers Blog](https://android-developers.googleblog.com/2024/03/battling-impersonation-scams-monzo-innovative-approach.html); [Finder](https://finder.com/uk/news/monzo-adds-new-feature-to-help-spot-scams)).
  - **CommBank CallerCheck:**
    - Used about 420,000 times between Nov 2022 and Aug 2023 (*background*) and 3.8M times in FY24 [V] ([CommBank Aug 2024](https://commbank.com.au/articles/newsroom/2024/08/cba-cuts-scam-losses-for-customers.html); [CommBank Sep 2023](https://commbank.com.au/articles/newsroom/2023/09/commbank-scams-and-fraud-research.html)).
    - CommBank says customer scam losses halved in FY24, but attributes this to several measures together, mainly NameCheck (an estimated $40M+ prevented) [V].
  - **Standard Bank "Trust Call"** (South Africa, dated 1 Aug 2025): with phone permission, the app shows a pop-up confirming a verified agent during a bank call, and warns with scam-tactic tips when a call can't be verified. The bank says it does not record or listen to calls [V] ([Standard Bank Trust Call](https://www.standardbank.co.za/southafrica/personal/products-and-services/security-centre/bank-safely/trust-call)).
- **OS-level in-call protections (Google):**
  - Opening a participating banking app while screen-sharing with an unknown contact triggers a warning and a one-tap "end call and stop sharing". Android 11+ for the banking warning [Reg-ish, vendor] ([Google Security Blog, May 2025](https://security.googleblog.com/2025/05/whats-new-in-android-security-privacy-2025.html)).
  - The UK pilot added a 30 s wait before sharing could continue [Press] ([TechCrunch](https://techcrunch.com/2025/05/13/google-announces-new-security-features-for-android-for-protection-against-scam-and-theft)).
  - Android 16 blocks sideloading, accessibility-permission grants and disabling Play Protect during calls (same sources).
  - India pilot (Nov 2025) with **Google Pay, Paytm and Navi** [Press] ([Gulf News](https://gulfnews.com/technology/media/google-ramps-up-ai-scam-protection-in-india-1.500355149); [TechCrunch Nov 2025](https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain)).
- **Screen-recording detection API (Android 15):**
  - `WindowManager.addScreenRecordingCallback()` with the `DETECT_SCREEN_RECORDING` permission, registered per activity ([ProAndroidDev](https://proandroiddev.com/screen-recording-detection-android-15-26ee709b66b4)).
  - Bypassable if recording started before registration; not recommended as a first line of defence ([Guardsquare](https://www.guardsquare.com/blog/android-15-screen-spying-protection)).
- **DoT Financial Fraud Risk Indicator (FRI), launched 21 May 2025 [Reg]:**
  - Rates mobile numbers Medium / High / Very High risk, using data from NCRP, Chakshu and bank intelligence ([Sanchar Saathi PDF](https://www.sancharsaathi.gov.in/SancharSaathiDocuments/ImportantDocuments/DoT%20Introduces%20Financial%20Fraud%20Risk%20Indicator%20(FRI)%20to%20strengthen%20Cyber%20Fraud%20Prevention.pdf); [Business Standard](https://www.business-standard.com/industry/news/dot-launches-financial-fraud-risk-indicator-to-aid-cybercrime-detection-125052101912_1.html)).
  - PhonePe declines Very High payments and shows alerts; it is working on Medium warnings. It says "the majority of flagged numbers later proved to be involved in fraud" [V] ([Moneylife](https://www.moneylife.in/article/new-fraud-indicator-flags-risky-mobile-numbers-in-realtime-to-thwart-upi-scams/77200.html)).
- **TRAI 1600 series [Reg]:**
  - Deadlines: commercial banks 1 Jan 2026; large NBFCs, payments banks and SFBs 1 Feb 2026; others 1 Mar 2026.
  - Over 485 BFSI entities with more than 2,800 numbers had adopted it by Nov 2025.
  - Source: [TRAI PR 135/2025](https://trai.gov.in/sites/default/files/2025-11/PR_No.135of2025.pdf).
- **CNAP (Calling Name Presentation) [Press, citing DoT]:**
  - Operators are to implement it from **1 Nov 2026** on 4G and higher; 2G, 3G and PSTN later.
  - The name comes from the originating operator's subscriber record; saved contacts still show the saved name.
  - International calls show "International Call".
  - Businesses can show a preferred name only if it is a registered trademark or GST trade name.
  - Sources: [Telangana Today, 15 Oct 2026](https://telanganatoday.com/mobile-users-to-see-callers-names-under-new-cnap-framework-from-november-1); [Inc42](https://inc42.com/buzz/centre-directs-telcos-to-display-caller-names-from-november-1/).
  - The earlier target of 31 Mar 2026 slipped ([Business Standard](https://www.business-standard.com/industry/news/cnap-service-nationwide-rollout-by-march-2026-dot-trai-telecom-125102901190_1.html)).
- **Scale of voice deepfake attacks [V]:**
  - Pindrop's 2025 report: deepfake fraud attempts up more than 1,300% in 2024, from about one a month to seven a day; +149% synthetic voice attacks at banks ([CIO Influence](https://cioinfluence.com/security/pindrops-2025-voice-intelligence-security-report-reveals-1300-surge-in-deepfake-fraud/)).
  - Pindrop also cites +680% year on year on a different metric; secondary sites quote mixed figures.

### Inferences
- **CNAP mismatch is a new signal Pehchaan can add.**
  - Trigger: the user says "my son Rahul is calling", but CNAP shows an unrelated KYC name, "International Call", or nothing.
  - Grounds: CNAP uses operator KYC, which an attacker can't set; the only exception is SIM fraud or a mule SIM in someone else's name.
  - Caveats: it works only on 4G/5G, only from 1 Nov 2026, and not for WhatsApp/OTT calls. Many genuine family SIMs are registered to another family member (a parent's KYC on a child's SIM), so it should be a moderate, non-decisive signal.
- **OTT calls bypass the telco layer.** WhatsApp/OTT calls carry no CNAP, 1600 or FRI context. Scammers can move victims to OTT calls, so Pehchaan must keep the out-of-band checks decisive. Detecting a VoIP/OTT call from inside a third-party app is not reliably supported on Android; I found no authoritative API documentation. Pehchaan's existing `caller_voip_unknown` presumably relies on a mock or on OS call state, and that should be stated honestly.
- **Screen-sharing during the call is a strong, cheap signal.**
  - It covers remote-access and "digital arrest" scams more than family-emergency voice clones.
  - Google already ships this in India with GPay and Paytm, so Pehchaan can cite it as validated practice and add `screen_shared_during_call` (mocked in the web demo; real via Android 15's API or a MediaProjection state check in a native build).
- **Precedent for the bank registry signal.** Monzo, CommBank and Standard Bank Trust Call are three shipped products, and Standard Bank's (Aug 2025) is almost exactly Pehchaan's `bank_active_call_1600` / `bank_no_active_call`. This is strong "a bank has already done this" evidence for judges, but no product has published an isolated effectiveness figure.

| Signal | How it works | Evidence | Limits / attacks | Who integrates | Privacy | 1.5-day prototype? |
|---|---|---|---|---|---|---|
| Active call during payment (have) | OS call state at payment time | BioCatch +10–15% uplift [V] | Attacker asks the victim to hang up first (Pehchaan's ≤10 min window helps) | App | Metadata only | Already |
| Bank outbound-call registry (have) | Bank dialer publishes live calls; app checks | Monzo, CommBank (3.8M uses FY24), Standard Bank Trust Call [V] | Needs the bank's dialer integration | Bank contact centre | Low | Already (mock) |
| **CNAP name / origin mismatch (new)** | Compare CNAP name with claimed identity; "International Call" label | Regulatory rollout 1 Nov 2026 [Press/Reg]; no effectiveness data yet | 4G+ only; OTT calls excluded; family SIMs in other names | Telcos (provide), OS dialer (exposes), app (reads) | KYC name shown on screen; app reading it may need dialer/role permissions | **Yes** as a mocked call-context field, a few hours |
| **Screen-share / remote-access during call (new)** | MediaProjection or screen-recording callback; enabled accessibility services; recent sideload | Google India pilot with GPay/Paytm/Navi [Press]; Android 16 in-call blocks [V] | Bypassable on rooted devices; per-activity callback; mostly relevant to non-voice-clone scams | App (native) or OS | Device state only | **Yes** as mocked signal plus UI; real detection needs a native Android build |
| DoT FRI tier (have, mocked) | Bank/PSP queries the DIP for the payee or caller number risk | PhonePe enforcement [V/Reg] | Number churn; coverage | Bank/PSP via DoT DIP | Government risk list | Already (mock) |
| Behavioural biometrics (hesitation, typing, coaching) | SDK models session behaviour | BioCatch claims [V] | Needs training data and an SDK; false positives for elderly and accessibility users | Bank plus vendor SDK | Continuous behavioural telemetry | No (roadmap) |

### Gaps
- No independent (non-vendor) measurement of how much the "active call" or "screen share" signals reduce losses.
- I could not verify whether a third-party Android app can read the CNAP name or detect an OTT call without privileged roles. This needs Android docs or on-device testing.
- No published accuracy figure for DoT FRI.

---

## 5. Out-of-band and friction controls: confirmation of payee, trusted-contact / delegated approval, cooling-off delays, kill switches, safe words, family verification

### Takeaway
"Verify through a second person or channel" has moved from advice to shipped banking features in 2025–26:
- Standard Bank **Trusted Person** (Aug 2025);
- KBC **Guardian Angel** (2026, rolling out to 4M+ customers);
- Capitec Trusted Approver and Yandex Pay trusted contact;
- India's **UPI Circle** already has per-payment approval rails.

Regulators also now permit **delays**: the UK lets banks hold suspicious payments for up to 4 business days, and Singapore applies a 24 h cooling period to held transactions. **Lock** features have mass adoption: Singapore Money Lock covers 350k+ customers and about S$28B. None of these publish an isolated effectiveness figure. Pehchaan's Family Verify sits squarely in this trend; its twist is verifying the *claimed caller* on their own device.

### Cited Findings
- **Trusted-contact co-approval:**
  - **Standard Bank Trusted Person** ("New feature", 4 Aug 2025) [V]:
    - One nominee, who must be a Standard Bank app user; high-value or criteria-matched payments need the nominee to confirm or decline in their app.
    - The nominee can't see balances.
    - If the nominee is unavailable, the payer may need to wait or use another verification method.
    - Source: [Standard Bank](https://www.standardbank.co.za/southafrica/personal/products-and-services/security-centre/bank-safely/trusted-person).
  - **KBC Guardian Angel** (Belgium) [Press]:
    - Suspicious payments are paused; both the customer and the guardian are alerted, and the KBC fraud team calls the guardian before approving.
    - Pilot of more than 2,000 users in 2026; rolling out to 4M+ customers (article dated 15 Sep 2026).
    - No quantitative results; anecdote only.
    - Source: [FStech](https://fstech.co.uk/fst/KBC_Rolls_Out_Guardian_Angel_Antifraud_Tool_To_Over_4m_Belgian_Customers.php).
  - **Capitec Trusted Approver:** threshold-based, with a 12 h approval window [unverified LinkedIn source] ([LinkedIn](https://za.linkedin.com/in/andrewp0tter)).
  - **Yandex Pay:** trusted contact approves transfers above a set limit; disabling the feature has a 24 h delay [Press] ([Zamin](https://zamin.uz/en/technology/204838-yandex-pay-launches-verification-feature-for-large-transfers-via-trusted-contact.html)).
- **UPI Circle (NPCI, 2024):** under *partial delegation*, the secondary user initiates and the primary user approves each payment with their UPI PIN; full delegation is capped at ₹15,000 a month and ₹5,000 per transaction [Press/secondary] ([Razorpay](https://razorpay.com/blog/what-is-upi-circle/)). I found no NPCI primary source.
- **Confirmation of payee:**
  - **RBI beneficiary name lookup** for NEFT/RTGS: circular of 30 Dec 2024, live by 1 Apr 2025, free, NPCI-run [Reg via Press] ([Tribune](https://www.tribuneindia.com/news/business/rbi-directs-banks-to-implement-beneficiary-name-look-up-for-rtgs-neft-transfers-by-april-2025/amp); [Taxmann](https://www.taxmann.com/post/blog/rbi-introduces-beneficiary-bank-account-name-look-up-facility-for-rtgs-and-neft-systems)).
  - CommBank NameCheck: an estimated $40M+ of scam payments prevented in FY24 [V] ([CommBank](https://commbank.com.au/articles/newsroom/2024/08/cba-cuts-scam-losses-for-customers.html)).
- **Cooling-off and delays:**
  - UK Payment Services (Amendment) Regulations 2024, in force Oct 2024 [Reg] ([FCA FG24/6](https://fca.org.uk/publication/finalised-guidance/fg24-6.pdf)):
    - PSPs may delay outbound payments up to 4 business days when they have reasonable grounds to suspect fraud;
    - the grounds must be established by the end of the next business day;
    - the customer must be told, and the firm bears the costs.
  - The PSR's mandatory APP reimbursement started 7 Oct 2024 (same source cluster).
  - Singapore: enhanced surveillance from 15 Oct 2025, with a 24 h cooling period on held transactions [Press] ([The Asset](https://www.theasset.com/article/55037/singapore-banks-enhance-safeguards-against-digital-scams)).
- **Kill switches and locks (Singapore):**
  - Self-service kill switch since Oct 2022 (*background*).
  - Money Lock (Nov 2023 onwards): more than 350,000 customers had locked about S$28B by 31 May 2025 [Press] ([Fintech News SG](https://fintechnews.sg/?p=114020); [MDDI](https://www.mddi.gov.sg/newsroom/measures-to-protect-singaporeans-against-online-scams/)).
  - Scam cases fell 26% year on year in H1 2025; this is multi-causal and not attributable to Money Lock alone [Press] (The Asset, above).
- **Safe words:**
  - FBI PSA, Dec 2024 [Reg] ([IC3](https://www.ic3.gov/PSA/2024/PSA241203)).
  - Starling/Mortar survey, Aug 2024, 3,000+ UK adults: about 28% think they may have been targeted by a voice-clone scam in the past year; 46% didn't know such scams exist; **8% would send money even if the call seemed strange** [V/Press] ([LBC](https://www.lbc.co.uk/tech/10673c0432c44540821b4277394926a8)). Belgian police reported the 28% as "were targeted", which overstates it ([police.be](https://www.police.be/shape/en/node/13219)).
  - MeitY (India) posted "Set a family passphrase" in early Oct 2026, per the team's `research/track01_voice_cloning.md` ([X post](https://x.com/GoI_MeitY/status/2107055701042577847/photo/1)).

### Inferences
- **Family Verify vs trusted-person models.** Standard Bank, KBC and Capitec verify *the payer's intent* through a guardian. Pehchaan verifies *the caller's claimed identity* on the relative's own device. These are complementary.
  - Add **guardian co-approval** for Amber/Red outcomes, aimed at elders. It reuses Pehchaan's existing Family Verify push and signed-response infrastructure, with a different recipient and question: "Your father is about to pay ₹40,000 to a new payee during a call. Approve?"
  - UPI Circle shows NPCI already runs per-payment approval rails, so the production path is plausible.
- **Prompt the safe word.** The 8% "would pay anyway" figure is the case for friction that *requires* action, such as hold, verify or a guardian, rather than warnings alone. Safe-word advice alone is passive; Pehchaan's value is prompting it at the payment moment.
- **Regulatory backing for the hold.** Pehchaan's 30-minute hold is mild compared with the UK's 4-business-day power and Singapore's 24 h. The slide can cite these as regulatory precedent that holds are acceptable and scale. Any Indian equivalent would need RBI/NPCI rules; I found none.
- **Money Lock maps to a "Lock my savings" button.** Shown on Red, it is a credible roadmap item with a large adoption precedent. It is low effort to mock, but adds less evidence than guardian approval.

| Signal / control | Evidence | Limits / attacks | Who integrates | Privacy | 1.5-day? |
|---|---|---|---|---|---|
| Family Verify on the claimed relative's phone (have) | Analogues: Trusted Person, Guardian Angel [V/Press]; CallShield shows keyed proofs work [M-pre] | Relative offline (timeout, fallback); relative's phone compromised | App on both phones; bank | Minimal: yes/no plus signature | Already |
| **Guardian co-approval (new)** | Standard Bank (Aug 2025), KBC (4M customers), Capitec, Yandex [V/Press] | Guardian unavailable; friction; coercion of both | Bank/PSP; NPCI-like rails (UPI Circle) | Guardian sees one payment only | **Yes**: reuse FV infra, about half a day |
| Confirmation of payee / name mismatch (have: `payee_name_mismatch`) | RBI name lookup [Reg]; NameCheck $40M+ [V] | Mule accounts with plausible names | PSP/bank, NPCI | Name disclosure | Already |
| Cooling-off hold (have) | UK 4-business-day regime [Reg]; Singapore 24 h [Press] | User frustration; scammer keeps the victim on the line through the hold | Bank, regulator | None | Already |
| Money Lock / kill switch | Singapore: 350k+ customers, about S$28B [Press] | Must be set up before the scam | Bank core banking | None | Mock only (roadmap) |
| Safe word (have) | FBI, Starling, MeitY advice [Reg/Press] | Forgotten under stress; leaks | App prompt | Hash on device | Already |

### Gaps
- No published effectiveness data, such as loss reduction or false-hold rate, for any trusted-contact, call-status or Money Lock feature isolated from other measures.
- No Indian regulation found that permits multi-day holds on UPI payments on suspicion.
- I could not verify Capitec's feature from a primary source.

---

## 6. LLM/ASR scam-script cue detection on calls (on-device), and privacy trade-offs

### Takeaway
On-device scam-call classifiers are shipping, but only narrowly. Google's Gemini Nano Scam Detection works in India only on **Pixel 9+**, in **English only**, off by default, only for unknown numbers, and it beeps to notify participants. Research shows small fine-tuned models can match large LLMs; for example, a Qwen3-4B screener reaches AUROC 0.974 at 64.5 ms per turn on a GPU. However, the evaluations mostly use synthetic or non-Indian data and carry self-declared test-set exposure. Script cues detect *the scam*, not *the voice*, so they survive any cloner. The privacy cost (transcribing third-party speech) is why Pehchaan's opt-in plus tap-checklist design is sound.

### Cited Findings
- **Google Scam Detection (India, Nov 2025):**
  - On-device Gemini Nano; doesn't record audio or send it to Google; off by default; unknown callers only; beeps to notify; Pixel 9+ only; English only; Indian languages "planned" [Press] ([TechCrunch](https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain)).
  - I found no 2026 source confirming expansion to non-Pixel phones or Indian languages ([Storyboard18](https://www.storyboard18.com/digital/google-rolls-out-on-device-scam-detection-in-india-as-digital-fraud-losses-top-%e2%82%b970-billion-84553.htm)).
- **CallScreenBench / JevLite (Sept 2026) [M-pre]:**
  - Qwen3-4B with LoRA: AUROC 0.974, calibration error 0.052, no false alarms on legitimate calls, decisions 1.14 turns earlier than an LLM judge, 64.5 ms per decision on one consumer GPU.
  - Caveats stated by the authors: "the recipe was selected with test-set exposure, and all callers are synthetic". A fine-tuned ModernBERT was not significantly worse.
  - Source: [arXiv 2609.23959](https://arxiv.org/abs/2609.23959).
- **ScriptMind (Jan 2026) [M-pre]:** an 11B model fine-tuned on 571 Korean phone-scam cases (22,712 instances) outperformed GPT-4o by 13% and sustained user suspicion in simulations ([arXiv 2601.13581](https://arxiv.org/abs/2601.13581)).
- **Low-resource languages (2026) [M-pre]:** on a Turkish set of 100 audio-transcript pairs, transcript input beat raw audio input across seven LLMs, and ASR transcripts performed about as well as human-corrected ones ([arXiv 2606.24523](https://arxiv.org/abs/2606.24523)).
- **Timeliness vs recall (Feb 2025) [M-pre]:** real-time LLM detection trades recall against how early it warns; users valued warnings "just at the right moment" ([arXiv 2502.03964](https://arxiv.org/abs/2502.03964)). An earlier survey flags biased datasets, low recall and hallucinations ([arXiv 2409.11643](https://arxiv.org/abs/2409.11643)).
- **Progression modelling [M-pre]:** PreScam (11,573 real-report scam conversations) found supervised encoders beat zero-shot LLMs at predicting when a scam reaches its termination stage ([arXiv 2605.12243](https://arxiv.org/abs/2605.12243)). Small models (Phi-4, LLaMA-3.2) do turn-wise elder-scam risk scoring suitable for mobile ([arXiv 2609.00005](https://arxiv.org/abs/2609.00005)).
- **Privacy [M-pre]:** MASK proposes tunable PII sanitisation before LLM scam analysis, because transcripts expose sensitive data to third parties ([arXiv 2510.18493](https://arxiv.org/abs/2510.18493)). CallShield argues transcript-based approaches are "reactive" and need connectivity ([arXiv 2601.09327](https://arxiv.org/abs/2601.09327)).

### Inferences
- **Generator-independent.** Script cues ("don't tell anyone", "send it now", OTP requests, "police / digital arrest") are independent of the voice generator. Under Pehchaan's threat (cloners beat detectors) they are more robust than acoustic features, but they are weak in short family-emergency calls where the script is brief and emotional.
- **Keep the tap checklist as the default.** It matches the evidence: no audio, zero privacy cost, and works on any phone. ASR plus a small classifier stays opt-in.
- **Don't swap the classifier on site.** Replacing the cue model in 1.5 days is not advisable: there is no Indian-language labelled call data and evaluation would be weak. The roadmap item is "on-device Indic SLM (Gemini Nano-class), consented, PII-redacted, warns only".
- **Mind the beep.** Google's design choice (beep plus off by default) is a useful privacy benchmark: any audio-processing feature should notify the other party and stay off unless the user opts in. India's DPDP Act implications were not researched here.

| Signal | Evidence | Limits | Who integrates | Privacy | 1.5-day? |
|---|---|---|---|---|---|
| Tap checklist (have) | n/a (UX) | Depends on user honesty | App | None | Already |
| ASR plus keyword/LLM cues (have, opt-in) | AUROC 0.974 synthetic [M-pre]; ScriptMind +13% vs GPT-4o [M-pre] | Indic languages, code-mixing; short emotional calls; synthetic eval | App (on-device) or OS | Transcribes the other party; needs notice and consent | Already (keyword); new model: no |
| OS-level scam detection (Google) | Shipping on Pixel 9+ [Press] | English only in India; Pixel only | OS vendor | On-device, beep | No (cite as ecosystem) |

### Gaps
- No public, consented Hindi/Hinglish/Telugu scam-call corpus with labels found.
- No published field precision or recall for Google's Scam Detection.
- DPDP Act 2023 / DPDP Rules treatment of on-device call transcription was not researched.

---

## 7. Ranking for Pehchaan: what to add in the next ~1.5 days, and what goes on the production-roadmap slide

### Takeaway
On site, add only signals that are (a) mockable in the engine and demo within hours, (b) backed by shipped precedent or regulation, and (c) independent of voice acoustics:
1. guardian co-approval;
2. CNAP name/origin mismatch;
3. screen-share during call;
4. a human-in-the-loop challenge, plus a quick measured test against the team's own Sarvam pipeline.

Everything that needs a telco, an OS vendor, NPCI or a model-vendor API goes on the roadmap. Per `CLAUDE.md`, each new signal must be written into `SPEC.md` first, and any LR shown must be labelled as uncalibrated, since none of these signals has Pehchaan-measured likelihood ratios.

### Cited Findings
(All supporting citations are in sections 1–6. The ranking below is the researcher's synthesis.)

### Inferences

**Add in ~1.5 days (ranked):**

1. **Guardian co-approval (`guardian_declined`, `guardian_approved`, `guardian_timeout`).**
   - Why: reuses the Family Verify push and signed-response path; strongest real-world precedent (Standard Bank Trusted Person Aug 2025; KBC Guardian Angel with 4M+ customers, 2026; Capitec; Yandex); India rails exist (UPI Circle partial delegation).
   - Demo line: "Banks in South Africa and Belgium already ship this; we add it only when the call-plus-new-payee trigger fires."
   - Effort: about half a day (engine signal, UI card, tests).
   - Caveat: no published effectiveness data, so don't claim a number.
2. **CNAP name / origin mismatch (`cnap_name_mismatch`, reuse `caller_international`).**
   - Why: CNAP goes live on 4G/5G from **1 Nov 2026**, one week after the finale, which makes it topical. Operator KYC names can't be set by the caller, and international calls are labelled.
   - Effort: a few hours as a mocked call-context field.
   - Caveats to state: 4G+ only; WhatsApp/OTT calls carry no CNAP; family SIMs are often registered to another relative, so give it a moderate LR and never decisive.
3. **Screen-share / remote access during the call (`screen_shared_during_call`, `accessibility_service_unknown`).**
   - Why: Google ships this exact warning in India with GPay, Paytm and Navi, and Android 16 blocks risky grants during calls.
   - Coverage: mainly digital-arrest and remote-access scams; it broadens Pehchaan beyond voice clones at no privacy cost.
   - Effort: a few hours as a mock; real detection needs a native Android build (Android 15 screen-recording callback, accessibility-service enumeration).
4. **Randomised human-in-the-loop challenge (`challenge_failed`, `challenge_passed`).**
   - Why: PITCH (88.7% machine AUROC vs 56% with no challenge) and DF-CAPTCHA (+20–29 pp) are the only peer-reviewed or measured liveness evidence, and the step costs no audio.
   - Quick experiment that adds a *measured, slide-traceable* number if logged to `FINDINGS.md`: with consented team voices, ask the Sarvam clone pipeline to whisper a given word, hum, or answer within 2 s, and count compliance failures.
   - Effort: a few hours for the UI, about 1–2 hours for the experiment.
   - Caveat: published results are on 2021–23 VC models, not commercial TTS clones.
5. **Optional, low value: add the AudioSeal detector beside Perth.** It is cheap, but it doesn't address Sarvam, and Pehchaan's own data shows AMR destroys Perth (29.8%). Only do it if time remains; keep it positive-only.

**Explicitly not recommended for the finale:**
- speaker verification against enrolled relatives (clones bypass it 43–83% [M-pre]; biometric privacy cost);
- replacing the script-cue model (no Indic eval data);
- CallShield-style in-band crypto (needs both endpoints; 63 s);
- behavioural biometrics (needs a vendor SDK and data).

**Production-roadmap slide (who must integrate):**

| Roadmap item | Integrator | Evidence / precedent |
|---|---|---|
| Live bank outbound-call registry via 1600-series dialers | Banks' contact centres | TRAI 1600 mandate (banks by 1 Jan 2026); Monzo call status, CommBank CallerCheck, Standard Bank Trust Call |
| CNAP name, call origin and international flag exposed to payment apps | Telcos plus OS dialer (DoT/TRAI) | CNAP from 1 Nov 2026 |
| Live DoT FRI via DIP, plus payee mule scores | DoT, PSPs | FRI (May 2025); PhonePe enforcement |
| Guardian co-approval on NPCI rails | NPCI, PSPs | UPI Circle partial delegation; Standard Bank, KBC |
| OS in-call protections as signals (screen share, sideload, accessibility) | Google/Android, PSPs | Google's India pilot with GPay, Paytm, Navi |
| Hold-on-suspicion policy (hours to days) and a "Money Lock" savings lock | RBI/NPCI, banks | UK 4-business-day regs; Singapore 24 h cooling and Money Lock |
| Partner watermark detection (SynthID, ElevenLabs, Azure) as a positive-only clue | Model vendors (API access needed) | SynthID Detector public 7 Oct 2026, no API or accuracy published; Sarvam undocumented |
| On-device Indic scam-cue SLM (consented, PII-redacted, warns only) | App/OS | Google Scam Detection (English, Pixel only); CallScreenBench, ScriptMind (preprints) |
| Family call authentication when the relative is offline (CallShield-style keyed proof) | Dialer/OS vendors | CallShield preprint: 99.2%, 63 s |
| Behavioural-biometric coaching cues | Bank plus vendor SDK | BioCatch claims (vendor) |

**Deck guardrails:**
- Quote vendor numbers (BioCatch +10–15%, CommBank 3.8M uses or $40M+, Pindrop +1,300%) only as "vendor-reported".
- Quote PITCH and DF-CAPTCHA with their threat model ("older real-time VC models").
- Quote Perth codec survival only from `ml/results/metrics.json`.
- Preprints from 2026 (`26xx.xxxxx`) are not peer-reviewed.

### Gaps
- None of the recommended new signals has a Pehchaan-measured likelihood ratio. The only quick way to get one on site is the challenge experiment.
- Whether a UPI app can legally and technically read CNAP and call state, and detect OTT calls, on Android without privileged roles is unverified.
- No India-specific evidence on how elderly users respond to guardian co-approval or hold friction. The planned V3 hallway test is the only source.
