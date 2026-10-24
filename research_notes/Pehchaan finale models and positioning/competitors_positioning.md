# Pehchaan finale: competitive landscape and positioning against the RAKSHAM rubric (as of 24 Oct 2026)

Scope: voice-clone and impersonation fraud defence (commercial, consumer, behavioural and verification products), how independent measurements compare with vendor claims, India regulatory fit, Pehchaan strengths and weaknesses per rubric line, likely judge questions, and the highest-leverage 2-day changes.

Notes on method:
- Searched and fetched 24 Oct 2026 using WebSearch, WebFetch and Firecrawl (Firecrawl rate-limited after 4 queries). Where a fact comes from the team's earlier notes (`research/*.md`, compiled 5–20 Oct 2026), the original URL is cited and "(team notes)" is added.
- Project facts are cited to repo files: `ml/realcall/FINDINGS.md`, `engine/results/deck_numbers.json`, `SPEC.md`, `TASKS.md`.
- **Vendor claim** marks self-reported accuracy. **Independent** marks a third-party measurement.

---

## Q1. Who competes or sits next to Pehchaan, what do they detect, where are they deployed, and what accuracy and pricing do they claim?

### Takeaway
Funded players fall into three groups:
- **Voice or media detectors**: enterprise contact-centre products (Pindrop, Reality Defender, Resemble, Hiya) and consumer or device products (Truecaller, McAfee, Google, DetectifAI, isVerified).
- **Session-behaviour scam scores**: BioCatch, Feedzai, Sardine.
- **Verification habits**: UK bank "call status" screens, safe-word apps.

None publicly offers what Pehchaan does: a **UPI payment-moment flow that verifies the claimed person out of band** (the relative's own device, the bank's call registry). Pehchaan's closest mechanism analogues are Monzo/Starling/Revolut call status and BioCatch's active-call signal. Its closest regulatory analogue is the RBI's April 2026 "trusted person" and 1-hour-hold discussion paper (Q4).

### Cited Findings

**Enterprise voice deepfake detectors**
- **Pindrop Pulse** (vendor claim):
  - 99% detection on known deepfake engines and over 90% on new or "zero-day" engines, from 2 s of net speech, with a false-positive rate under 1%. First National Bank of Omaha was in the first deploying cohort — [Pindrop](https://www.pindrop.com/resources/article/pindrop-pulse-for-audio-deepfake-detection).
  - Pulse Inspect was trained on 370+ generation tools and 20M statements. Pindrop says third parties confirmed it was "40 percentage points" more accurate than competitors — [Pindrop](https://www.pindrop.com/resources/article/combat-deepfakes-pindrop-pulse-inspect).
  - The homepage says "Independently validated at 99% accuracy" — [Pindrop](https://www.pindrop.com/).
  - Pindrop raised $100M in July 2024. SiliconANGLE reported "up to 94.6%" in independent testing, while current product pages quote 99% *when combined with* Pindrop's multifactor platform — [SiliconANGLE](https://siliconangle.com/2024/07/17/pindrop-security-raises-100m-funding-fight-deepfakes-ai-powered-voice-authentication-tech/).
  - Pulse for Meetings was named one of TIME's Best Inventions of 2025 — [BusinessWire](https://www.businesswire.com/news/home/20251119488893/en/Pindrops-Pulse-for-Meetings-Named-One-of-TIMEs-Best-Inventions-of-2025-Launches-to-Defend-Virtual-Collaboration-from-Deepfakes).
  - No Indian deployment or India-specific validation was found — searched 24 Oct; also in [team notes](../../research/track01_voice_cloning.md).
- **Amazon Connect Customer Voice ID** has been retired:
  - No new customers from 20 May 2025. "After May 20, 2026, you will no longer be able to use" it.
  - AWS points to "AWS Partners available on the AWS Marketplace, such as Pindrop", or to a do-it-yourself OTP built on AWS End User Messaging SMS — [AWS docs](https://docs.aws.amazon.com/connect/latest/adminguide/amazonconnect-voiceid-end-of-support.html).
  - Trade press summarised this as "Amazon … recommends Pindrop" — [BiometricUpdate, Jun 2025](https://www.biometricupdate.com/202506/amazon-to-end-support-for-voice-biometrics-recommends-pindrop). ValidSoft also markets itself as a replacement — [ValidSoft](https://www.validsoft.com/blog/amazon-connect-voice-id-retires/).
  - Amazon Fraud Detector has been closed to new customers since 7 Nov 2025 — [AWS docs](https://docs.aws.amazon.com/frauddetector/latest/ug/frauddetector-availability-change.html) (team notes).
- **Reality Defender**:
  - Offers ready-made contact-centre integrations or an encrypted API, plus private-cloud or on-prem deployment — [Reality Defender](https://realitydefender.com/solutions/contact-center-security).
  - Its case study says a Tier-1 global bank detected deepfakes in real time with "99.99% accuracy" (vendor claim) — [case study](https://www.realitydefender.com/case-studies/how-a-global-bank-mitigates-contact-center-deepfake-threats-with-reality-defender).
  - Free API tier of 50 scans a month from July 2025 — [Reality Defender](https://www.realitydefender.com/insights/reality-defender-launches-free-access-to-deepfake-detection-api). A third-party listing shows $399/month — [checkthat.ai](https://checkthat.ai/brands/reality-defender) (team notes).
- **Resemble Detect / DETECT-2B** (vendor claims):
  - 94% accuracy, 200 ms latency, 30+ languages — [Resemble](https://www.resemble.ai/learn/models/detect2b).
  - A later claim of 99.47% — [BiometricUpdate, Aug 2026](https://www.biometricupdate.com/202608/resemble-ai-expands-multimodal-deepfake-detection-approach-for-new-accuracy-highs) (team notes).
  - Resemble also ships the open-source Chatterbox cloner with a Perth watermark — [GitHub](https://github.com/resemble-ai/chatterbox) (team notes).
- **Hiya AI Voice Detection** (built from the 2024 Loccus.ai acquisition):
  - Sold as a consumer app (Hiya AI Phone), for network-level deployment by carriers and handset makers, to enterprises, and as a free Chrome extension for media.
  - Claims "Over 99% accuracy vs. the most complex 'In-the-wild' datasets", "fractions of a second", "Language and channel independent". No pricing on the page — [Hiya](https://www.hiya.com/products/ai-voice).
  - GSMA Foundry listing: flags AI voices "within two seconds" at "99%" (vendor claim) — [GSMA](https://www.gsma.com/get-involved/gsma-foundry/gsma_resources/hiya-security-real-time-scam-protection-with-ai/).
- **ElevenLabs AI Speech Classifier**:
  - Detects only ElevenLabs-generated audio. The launch post claimed over 99% on unmodified audio and over 90% after codec or reverb — [ElevenLabs blog](https://elevenlabs.io/blog/ai-speech-classifier).
  - Current docs give "99% precision, 80% recall" on unmodified ElevenLabs audio — [ElevenLabs docs](https://elevenlabs.io/docs/product-guides/audio-tools/ai-speech-classifier).
  - The tool page says it does not reliably classify output from the Eleven v3 model — [ElevenLabs](https://elevenlabs.io/ai-speech-classifier).
- **Modulate** claims the top score on the Hugging Face Speech-DF-Arena and raised $25M in Sep 2026 — [BiometricUpdate](https://www.biometricupdate.com/202609/deepfake-defense-draws-new-capital-as-voice-detection-checks-near-5-5b-by-2028) (team notes).

**Consumer and device call-time detectors**
- **Truecaller AI Call Scanner**:
  - Launched May 2024 as the "World's First AI Call Scanner"; the user starts detection during a call — [BusinessWire](https://www.businesswire.com/news/home/20240528009351/en/Introducing-The-Worlds-First-AI-Call-Scanner-by-Truecaller-The-Fastest-Most-Accurate-AI-Voice-Scam-Detection-System).
  - The vendor page said "currently only available in the U.S. on Android" when the team checked in Oct 2026 — [Truecaller](https://www.truecaller.com/ai-call-scanner) (team notes; could not re-fetch on 24 Oct).
  - Truecaller Scam Checker (number, link and message checks) launched in India on 28 Sep 2026 — [TechRepublic](https://www.techrepublic.com/article/news-truecaller-scam-checker-apac-india/) (team notes).
- **McAfee Deepfake Detector**:
  - Runs on-device on the NPU of Copilot+ PCs (preinstalled on HP models from Jan 2025) and flags AI audio *in videos*. McAfee says it does not collect or record audio — [McAfee](https://www.mcafee.com/en-us/newsroom/press-releases/2025/mcafee-brings-mcafee-deepfake-detector-to-select-hp-copilot-pcs.html).
  - The India launch was English-only — [Outlook Business](https://www.outlookbusiness.com/news/mcafee-launches-worlds-first-ai-powered-deepfake-detector-in-india).
  - No published accuracy figures were found.
- **Google Scam Detection** (Gemini Nano, on-device):
  - Came to India in Nov 2025, initially **Pixel 9 and later only**, off by default, unknown numbers only. Pixel had under 1% Indian share in 2024.
  - Google also piloted screen-sharing scam protection with Navi, Paytm and Google Pay — [TechCrunch](https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain).
  - Sources disagree on Hindi support — [Storyboard18](https://www.storyboard18.com/digital/google-rolls-out-on-device-scam-detection-in-india-as-digital-fraud-losses-top-%e2%82%b970-billion-84553.htm).
- **DetectifAI** (San Francisco; the founder's grandfather paid a ransom after a deepfake call):
  - On-device detector SDK, sold first to phone makers. Claims it handles more than 100,000 calls a month for Indian financial institutions (AI voice agents for debt collection), with deepfake detection and speaker verification.
  - No accuracy figures. Was in TechCrunch Disrupt Battlefield, Oct 2026 — [TechCrunch, 28 Sep 2026](https://techcrunch.com/2026/09/28/after-a-deepfake-voice-fooled-her-grandfather-this-founder-sprang-into-action).
- **isVerified** (Israel): Android and iOS apps with continuous voice authentication during calls — [IDTechWire](https://idtechwire.com/startup-isverified-emerges-from-stealth-with-voice-deepfake-detection-apps/).

**Behavioural and payment-side scam platforms**
- **BioCatch**:
  - Treats an active phone call during a banking session as a scam signal.
  - Scams360, launched Jul 2025 for authorised-push-payment (APP) fraud, can route the case to a live agent — [BioCatch PR](https://www.biocatch.com/press-release/biocatch-delivers-scams360); [SecurityBrief](https://securitybrief.co.uk/story/biocatch-launches-scams360-to-cut-450-million-uk-scam-losses).
  - Vendor figure from an investment-scam case study: 90% of reported fraud payments happened while the user was on an active call — [BioCatch](https://www.biocatch.com/hubfs/White%20Papers/New%20Brand/Biocatch_DS_Social_Engineering_Scam_15_Sept.pdf?hsLang=en).
- **Sardine Shield** (consumer): call-scam detection; flags risky payments and screen shares; blocks remote-access tools. Says calls and messages are "never accessed or stored" — [Sardine](https://www.sardine.ai/shield).
- **Feedzai ScamPrevent**: behavioural biometrics flag likely scam victims before they authorise a payment. Its ebook covers deepfake voice plus screen sharing. No dedicated voice-scam signal product was found — [Feedzai](https://www.feedzai.com/resource/fraud-scam-how-to-guide/).
- **UK bank call status (the closest analogue to Pehchaan's bank registry check)**:
  - Monzo Call Status (Sep 2023) shows in the app whether a Monzo agent is really on the line and tells the user to hang up if not. About 700 uses a month report suspected fraud.
  - Starling shows call status inside the payment screen. Revolut detects whether the user is on a call when the app opens and flags whether it is a Revolut agent — [Which?](https://www.which.co.uk/news/article/monzo-customers-can-now-check-if-theyre-on-the-phone-to-a-scammer-aOEOE2M1DotL).
  - Monzo joined the UK's 159 safe-bank-call service — [Stop Scams UK](https://stopscamsuk.org.uk/monzo-joins-159/).

**Indian startups**
- **pi-labs (Pune)**:
  - pi-authentify is recognised in "Gartner's 2026 Emerging Market Quadrant for Deepfake Detection". It is positioned for defence and law enforcement, plus VideoKYC — [pi-labs](https://www.pi-labs.ai/).
  - Pitched at BFSI — [Inc42](https://inc42.com/startups/can-pi-labs-fend-off-deepfake-attacks-with-its-ai-arsenal/).
- **Contrails AI (Bengaluru)**:
  - Multimodal trust-and-safety detection; $1M pre-seed (Huddle Ventures, IAN Group).
  - Says it is piloting with marketplaces, media firms and financial institutions — [Entrackr](https://entrackr.com/snippets/contrails-ai-raises-1-mn-in-pre-seed-round-from-huddle-ventures-and-ian-group-10537705).
  - Used by the Deepfakes Analysis Unit (DAU) — [DAU](https://dau.trustedinfoalliance.in/blog/copycat-financial-scam-videos-of-arvind-kejriwal-shah-rukh-khan-use-a-i-voice) (team notes).
- **Kroop AI** (VizMantiz multimodal) — [Kroop](https://kroop.ai/). **Vastav AI** ("99.7%" claim, single developer) — [Vastav](https://vastav.ekoahamdutivnasti.com/) (team notes).
- **Bureau (bureau.id)**: no voice-deepfake product found (see Gaps).
- **Threat-side Indian vendor: Sarvam Bulbul V3** (Feb 2026):
  - TTS in 11 Indian languages; Sarvam's page lists voice cloning. Beta price ₹30 per 10K characters — [Sarvam](https://www.sarvam.ai/tts-v2); [YourStory](https://yourstory.com/ai-story/sarvam-ai-bulbul-v3).
  - Digit reports "consent-based" cloning, while one blog says there is no self-serve cloning; this conflict is unresolved — [Digit](https://www.digit.in/news/general/better-than-google-gemini-and-chatgpt-indian-startup-sarvam-ai-claims-to-beat-global-models.html/amp/).

### Inferences
- **Turn competitors into suppliers.** Pehchaan's voice slot is a pluggable, capped signal: Pindrop, Reality Defender, Hiya or our own model can feed it. The product is the payment-moment decision and the out-of-band check that still works when every detector is fooled. This answers "why not just buy Pindrop?" and avoids a head-to-head accuracy contest Pehchaan would lose on paper.
- **The Amazon story has to be framed correctly.** Voice ID is gone, and AWS itself pointed customers to Pindrop or OTP. Pehchaan's `bank_active_call_1600` registry check ([SPEC.md](../../SPEC.md)) is effectively Monzo Call Status for Indian banks: a bank's Amazon Connect outbound-contact records can feed it. That makes it an Amazon-native "is my bank really calling me?" check that needs no voice biometrics. Pitch it as "what replaces voiceprints in an Amazon Connect contact centre", not as a Voice ID integration.
- **The India gap is real but narrow.** India's consumer detectors are either device-limited (Google on Pixel 9+ only; Truecaller's scanner apparently US-only) or English-only (McAfee). India's startups do upload-and-analyse forensics. No Indian bank call-status feature like Monzo's was found (see Gaps).

### Gaps
- Pricing for Pindrop, Hiya Enterprise and Resemble Detect is not public.
- No published Indian bank or UPI deployment of any real-time voice deepfake detector was found. DetectifAI's Indian FI customers are unnamed.
- No search result covered a Bureau (bureau.id) voice or deepfake product.
- Could not confirm whether any Indian bank offers Monzo-style in-app call status.
- Could not re-verify Truecaller AI Call Scanner availability in India today (fetch blocked).

---

## Q2. How reliable are voice-clone detectors outside the lab? (vendor claims vs independent measurements)

### Takeaway
Independent tests consistently land far below vendors' "99%":
- an in-the-wild benchmark showed a 48% AUC drop for open-source audio detectors;
- NPR found two of three commercial tools unreliable;
- ElevenLabs' own classifier cannot reliably catch its own newest model.

Pehchaan's measured fall from 4.8% simulated EER to 6.8%/11.7% on real calls, and **0/12 on Sarvam**, is the same pattern measured honestly. That is a credibility asset if framed as evidence for the design.

### Cited Findings
- **Deepfake-Eval-2024** (independent; 56.5 h of audio from 88 websites in 52 languages): AUC fell 48% for open-source audio models versus academic benchmarks. Commercial models did better than open source but "fall short of human forensic analysts" — [arXiv 2503.02857](https://arxiv.org/abs/2503.02857v1).
- A Reality Defender blog says leading commercial detectors reach about 78% on in-the-wild deepfakes. This is a vendor citing the field and was not confirmed against the paper — [Reality Defender](https://www.realitydefender.com/insights/lab-benchmarks-ineffective-in-deepfake-detection).
- **NPR, Apr 2024** (independent; 84 clips of 5–8 s, PlayHT clones of three reporters):
  - Pindrop got all but three right. AI or Not got about half wrong. AI Voice Detector misidentified 20 of 84 at its own 60% threshold — [NPR](https://www.npr.org/2024/04/05/1241446778/deepfake-audio-detection).
  - Pindrop's write-up of the same study: 81/84 (96.4%) — [Pindrop](https://www.pindrop.com/article/npr-audio-deepfake-study/).
- **DAU (India), Aug 2026**: on one case, Northwestern's GODDS ran 70 audio models and the vote split 35 fake / 35 real. Hiya scored 53% on one confirmed fake and 97% on another — [DAU](https://dau.trustedinfoalliance.in/blog/copycat-financial-scam-videos-of-arvind-kejriwal-shah-rukh-khan-use-a-i-voice) (team notes).
- **ElevenLabs**: 80% recall on its own unmodified audio and no reliable detection of v3 output — [ElevenLabs docs](https://elevenlabs.io/docs/product-guides/audio-tools/ai-speech-classifier); [ElevenLabs](https://elevenlabs.io/ai-speech-classifier).
- **PITCH** (academic, challenge-response for live deepfake calls): machine AUROC 88.7%, humans 72.6%, human plus AI 84.5% — [arXiv 2402.18085](https://arxiv.org/abs/2402.18085) (team notes).
- **Cloner safeguards are weak.** Consumer Reports (Mar 2025) found 4 of 6 cloning services (ElevenLabs, Speechify, PlayHT, Lovo) required only a self-attestation checkbox. Descript and Resemble had real barriers — [Consumer Reports](https://innovation.consumerreports.org/new-report-do-these-6-ai-voice-cloning-companies-do-enough-to-prevent-misuse/); [The Register](https://www.theregister.com/2025/03/10/ai_voice_cloning_safeguards/).
- **Pehchaan's own measurements** (pre-registered splits; two consented speakers, one carrier, one seed):

  | Measurement | Result |
  |---|---|
  | v1 (served), simulated channels | 4.8% EER |
  | v1, real calls on D1 (Samsung M34) | 24.6% EER |
  | Model A, real calls on D1 | 6.8% EER, 75% of clones caught, 0% genuine flagged |
  | Model A, held-out handset D2 (Redmi, 274 clips) | 11.7% EER, 84.6% caught (78–90%), 8% genuine flagged (5–14%) |
  | Both models, Sarvam (`sarvam_ivc`, never trained on) | **0/12 caught (95% CI 0–24%)** |
  | Deployed voice service (2 vCPU, CPU int8) | 3.1 s per 10 s clip, against a 1.5 s SPEC budget |

  Source: [FINDINGS.md](../../ml/realcall/FINDINGS.md).

### Inferences
- Claim "pre-registered, held-out handset, with confidence intervals", not "our detector is accurate". Few hackathon teams, and few vendors, publish a held-out-device result with intervals or a generator their model fails on.
- Sarvam 0/12 sits alongside ElevenLabs v3 and the Deepfake-Eval drop as one sentence: "every detector, including the vendors' own, loses to the newest generator. That's why ours can't hold money (G2)."
- n = 12 for Sarvam is small. Say "0 of 12 (CI up to 24%)", never "Sarvam is undetectable".

### Gaps
- No independent audit was found of Pindrop, Reality Defender, Hiya or Resemble on Indian-language, narrowband, speakerphone phone audio.
- The current Speech-DF-Arena leaderboard standings were not re-checked today.

---

## Q3. Are there open-source or academic "family verification", "safe word" or challenge-response products, and how does Pehchaan differ?

### Takeaway
Safe words are official advice (FBI, FTC, banks) and are becoming apps:
- **Trust Onion**: rotating family codewords, Sep 2026.
- **Signet**: open-source, rotating per-contact phrases.
- **realxreal**: commercial, 60-second rotating codewords.

All rely on the victim remembering to challenge the caller *during* the call. Pehchaan triggers automatically at **Pay**, and gets the answer from the **relative's own device**, not over the channel the scammer controls. That is the defensible difference.

### Cited Findings
- FBI IC3 PSA (3 Dec 2024): "Create a secret word or phrase with your family" — [IC3](https://www.ic3.gov/PSA/2024/PSA241203) (team notes).
- FTC (Apr 2024): call the person back on a number you know is theirs — [FTC](https://consumer.ftc.gov/consumer-alerts/2024/04/fighting-back-against-harmful-voice-cloning) (team notes).
- Starling Bank "Safe Phrases" campaign (Sep 2024): agree a phrase "which you never share digitally" — [ITV](https://www.itv.com/news/2024-09-17/ai-voice-cloning-scam-warning-issued-by-bank); [Starling](https://www.starlingbank.com/safe-phrases/).
- Expert advice in US elder-fraud coverage: a safe phrase of at least four words — [CBS News](https://cbsnews.com/amp/news/elder-scams-family-safe-word).
- **Trust Onion** (Sep 2026): free App Store and Google Play app; three rotating private family codewords (vendor description) — [Cyber Magazine / GlobeNewswire](https://cybermagazine.com/globenewswire/3356048).
- **Signet**: open-source Android app (AGPL-3.0, F-Droid) for verifying calls from family and colleagues. Each paired contact gets a rotating four-word phrase, after pairing once in person or over a trusted channel — [IzzyOnDroid](https://apt.izzysoft.de/fdroid/index/apk/dev.digitalgrease.signet?repo=main).
- **realxreal**: "multi-factor authentication for human interaction"; rotating codeword pairs, said to change every 60 s (vendor claim) — [Mergeek](https://mergeek.com/en/latest/eBGqKWdxVxBWLvlO).
- **PITCH challenge-response**: randomised challenges stress real-time voice conversion. The authors warn attackers can pre-fabricate answers to public challenges — [arXiv 2402.18085](https://arxiv.org/abs/2402.18085) (team notes).
- **RBI "trusted person" proposal (Apr 2026)**: a nominated trusted individual must approve APP transfers of ₹50,000 and above. This is mandatory for people aged 70+ and persons with disabilities, optional for others, and has a 24-hour cooling-off before changing the trusted person — [MediaNama](https://www.medianama.com/2026/04/223-safeguard-elderly-rbi-suggests-trusted-person-approval-high-value-digital-payments/). Details in Q4.

### Inferences
- **Codeword apps vs Pehchaan:**
  - A codeword is spoken over the scammer's channel. The scammer can coach around it ("I'm hurt, I can't remember the word") or exploit panic.
  - Pehchaan's Family Verify asks the *named* relative on *their* phone, with a device-signed answer, and starts automatically when the payer says "my son asked". This removes the "remember to challenge" step that elders skip under pressure.
  - Pehchaan already keeps the safe word as a fallback ([SPEC.md](../../SPEC.md)).
- A judge may ask "why not just Signet?". Answer on adoption: Signet needs both people to install a separate app and remember to use it mid-crisis. Pehchaan sits inside the payment app the elder already opens, at the one moment money moves.
- Rotating codewords, like Signet's, could be an upgrade path for Pehchaan's static safe word. That is a one-line roadmap item, not a 2-day build.

### Gaps
- The team's earlier notes cite a MeitY safe-word advisory (Oct 2026), but no source was found today. **Do not put it on a slide** unless the URL is found (CLAUDE.md numbers rule).
- No usage numbers or independent evaluations exist for Trust Onion, Signet or realxreal.

---

## Q4. What Indian regulation and platform constraints shape adoption and feasibility (NPCI, RBI, TRAI, DoT, DPDP, Android)?

### Takeaway
The regulatory tide favours Pehchaan's design:
- The **RBI's April 2026 discussion paper** proposes a payer-side hold of up to 1 hour on P2P transfers over ₹10,000 and a "trusted person" approval for elders. Pehchaan is effectively a *risk-triggered* version of both, which answers the critics' friction objection.
- **TRAI's 1600-series** mandate makes the bank-call check concrete.
- **DoT FRI** is already used by PhonePe, Paytm and Google Pay.

The binding feasibility constraint is **Android permissions** (Play Store call-log policy), and it should be answered before a judge raises it.

### Cited Findings
- **RBI discussion paper** "Exploring safeguards in digital payments to curb frauds" (Department of Payment and Settlement Systems, Apr 2026; comments until 8 May 2026):
  - A payer-side hold of up to 1 hour on APP/P2P transfers above ₹10,000, during which the sender can cancel.
  - Trusted-person approval at ₹50,000 and above: mandatory for 70+ and persons with disabilities, optional for others. Merchant, recurring and cheque payments excluded.
  - A 24-hour cooling-off for changing the trusted person.
  - Sources: [Outlook Business](https://www.outlookbusiness.com/economy-and-policy/rbi-proposes-1-hour-delay-for-transactions-above-10000-to-fight-digital-fraud); [MediaNama](https://www.medianama.com/2026/04/223-safeguard-elderly-rbi-suggests-trusted-person-approval-high-value-digital-payments/); [Moneylife](https://moneylife.in/article/rbis-proposed-digital-payment-safeguards-what-do-they-mean-for-you/80218.html).
  - Critics note the trusted person would influence execution without any legal or beneficial interest in the account — [Moneylife MAS360](https://mas360.moneylife.in/article/rbi-proposes-new-safeguards-against-digital-payment-frauds/4876.html).
  - No post-consultation draft directions were found as of 24 Oct 2026.
- **TRAI 1600-series direction** (19 Nov 2025): RBI-, SEBI- and PFRDA-regulated entities must move service and transactional calls to 1600 numbers.
  - Deadlines: commercial banks by 1 Jan 2026; large NBFCs, payments banks and small finance banks by 1 Feb 2026; the rest by 1 Mar 2026 — [The Week / PTI](https://www.theweek.in/wire-updates/business/2025/11/19/del27-biz-trai-bfsi.amp.html); [Storyboard18](https://www.storyboard18.com/amp/how-it-works/trai-sets-early-2026-deadline-for-bfsi-to-transition-to-1600-calling-range-to-combat-spoofing-84495.htm).
  - Earlier RBI circular (17 Jan 2025): 1600xx for transactional calls, 140xxx for promotional — [Outlook Money](https://www.outlookmoney.com/banking/rbi-asks-banks-to-use-only-1600xx-series-phone-numbers-to-call-customers-for-transactional-purposes).
  - Enforcement and completion status in 2026 were not found.
- **DoT Financial Fraud Risk Indicator (FRI)**, launched 21 May 2025 within the Digital Intelligence Platform: tags mobile numbers as Medium, High or Very High risk.
  - PhonePe declines Very High-risk numbers and was testing warnings for Medium.
  - PhonePe, Paytm and Google Pay (over 90% of UPI) were integrating DIP alerts, and some platforms added transaction delays and confirmations — [Business Standard](https://www.business-standard.com/industry/news/dot-launches-financial-fraud-risk-indicator-to-aid-cybercrime-detection-125052101912_1.html); [Sanchar Saathi PDF](https://www.sancharsaathi.gov.in/SancharSaathiDocuments/ImportantDocuments/DoT%20Introduces%20Financial%20Fraud%20Risk%20Indicator%20(FRI)%20to%20strengthen%20Cyber%20Fraud%20Prevention.pdf).
- **DPDP Rules 2025** (notified 13 Nov 2025): consent-manager rules take effect 13 Nov 2026; notice, consent, security, retention and rights obligations take effect 13 May 2027 — [Hogan Lovells](https://www.hoganlovells.com/en/publications/indias-digital-personal-data-protection-act-2023-brought-into-force-); [Deccan Herald](https://www.deccanherald.com/amp/story/india%2Fcentre-notifies-dpdp-rules-implementation-planned-in-phases-spread-over-12-18-months-3798465).
- **Google Play policy**: SMS and Call Log permissions are allowed only for "critical core functionality" with a declaration form. A July 2026 preview removes "account verification via phone call" as a READ_CALL_LOG use case from 27 Jan 2027 — [Play Console Help](https://support.google.com/googleplay/android-developer/answer/9047303); [Play Console Help (2026 update)](https://support.google.com/googleplay/android-developer/answer/17225965).
- **Government warnings**: the MHA/I4C (June 2026) warned banks and fintechs that deepfakes can bypass facial authentication, liveness and video KYC — [FastBull](https://www.fastbull.com/brokersview/news/india-warns-banks-and-fintechs-over-rising-ai-deepfake-fraud-threat-324193) (secondary source).
- **Amazon's stated priorities** (useful for an Amazon judge):
  - "Behaviour is much harder to fake than documents or images." Phone fraud is harder to tackle because attribution is harder. The focus is first-time users in tier-2 and tier-3 cities — [Times of India, 4 Aug 2026](https://timesofindia.indiatimes.com/business/india-business/ai-fraud-is-hitting-indias-new-net-users-hardest-amazon/articleshow/132843254.cms) (team notes).
  - Amazon Pay UPI Circle (delegated family payments) — [aboutamazon.in](https://www.aboutamazon.in/news/retail/amazon-pay-upi-circle-family-payments) (team notes).

### Inferences
- **Strongest adoption line:** "RBI has proposed a trusted person and a 1-hour hold for everyone. Pehchaan applies the same protections only when risk is present (call-adjacent, new payee), so most payments stay friction-free. The simulator projects 94.4% of genuine triggered payments see no Pause & Verify screen (silent 41.8% + one tap 52.6%) ([deck_numbers.json](../../engine/results/deck_numbers.json), projection)."
  - Say "discussion paper", not "rule".
  - Pehchaan's 30-minute cooling-off sits inside RBI's proposed 1-hour window.
- **Amazon Pay fit:** UPI Circle already models a family relationship inside Amazon Pay. Family Verify can reuse that graph as the "circle".
- **Android call-state permissions are a likely hard question.**
  - From platform knowledge (not verified today): call *state* needs READ_PHONE_STATE, which is not in the restricted Call Log group, while reading the caller's *number* needs READ_CALL_LOG, which is restricted.
  - Pehchaan's SPEC hashes caller-in-contacts on-device. Check whether the native app needs READ_CALL_LOG and have the answer ready: "bank apps would declare it under fraud-prevention core functionality, or degrade to call-state-only plus the 'Who asked you to pay?' claim."
  - WhatsApp and other VoIP calls don't show in telephony call state. Detecting them is plausible from audio mode, but unverified.
- **NPCI fit:** a TPAP or bank app adds Pehchaan before its UPI collect or pay call, so no NPCI change is needed.
  - "upi:// interception" by a third-party app is the riskier claim. Present it as a demo convenience; in production the SDK sits inside the PSP app.

### Gaps
- No final RBI directions after the May 2026 consultation were found.
- No 2026 data on FRI adoption or outcomes.
- No source confirms whether Play policy explicitly allows fraud-detection use of READ_CALL_LOG. Nothing was verified on detecting VoIP calls on Android.
- No NPCI circular on third-party interception of UPI intents was found.

---

## Q5. Pehchaan's honest strengths and weaknesses per rubric line

### Takeaway
Pehchaan is strongest on **architecture, differentiation, safety and feasibility**: a deployed live system, a real cloned call to HOLD in 14 s, guardrails, pre-registered real-call evaluation.

The exposed flanks are:
- **Problem fit (track semantics)**: judges may expect a detector for "Voice Cloning Fraud Detection".
- **Adoption**: integrations with FRI, the bank registry and NCRP are mocked, and relatives must enrol.
- **Unvalidated field claims**: fusion numbers are simulator projections; there are no live genuine callers and no comprehension test yet.

### Cited Findings (project evidence)
- **Problem fit (20)**
  - Strength: the target is the payment moment for UPI payers, with elders aged 45+ as the highest-risk users ([SPEC.md](../../SPEC.md)). McAfee (Feb 2026): 1 in 5 Indians have encountered a voice-clone scam — [McAfee India](https://www.mcafee.com/en-in/consumer-corporate/newsroom/press-releases/2026/20260204-1.html) (team notes). Amazon's focus on first-time and new users matches (TOI above).
  - Risk: the track is titled "Voice Cloning Fraud Detection", and the brief stresses "a detector score alone is not an explanation or proof" ([competition_intel.md](../../research/competition_intel.md)). That supports Pehchaan's framing, but the pitch must show it detects *the clone attack* (the HOLD), not the clone *audio*.
- **Architecture and detection (20)**
  - Strength: explainable log-odds fusion; guardrails G1–G7; EN and HI reasons; signed evidence pack; real-call pipeline with pre-registered splits ([SPEC.md](../../SPEC.md); [FINDINGS.md](../../ml/realcall/FINDINGS.md)).
  - Weakness: fusion outcomes are "assumption-driven projection[s] … not measured outcomes" ([deck_numbers.json](../../engine/results/deck_numbers.json)). The voice service takes 3.1 s per 10 s clip on the deployed CPU, against a 1.5 s budget. The quality gate passed only 29/210 B3 clips ([FINDINGS.md](../../ml/realcall/FINDINGS.md)).
- **Differentiation (15)**
  - Strength: no competitor combines automatic relative verification, a bank 1600 registry check and UPI payment-moment triggering (Q1).
  - Weakness: each ingredient has precedent (Monzo Call Status, safe-word apps, RBI trusted person, BioCatch active-call signal). Claim *integration at the right moment for India*, not invention.
- **Feasibility (15)**
  - Strength: deployed on AWS Mumbai. A live Sarvam-cloned call followed by Pay gave a Red hold in **14 s** (T1) and **4 s** (T3) on two real phones ([FINDINGS.md](../../ml/realcall/FINDINGS.md)). Tests: 85 for the engine, 27 for the API ([TASKS.md](../../TASKS.md)).
  - Weakness: FRI/DIP, the I4C registry, the bank registry and the payee-risk adapters are mocked ([SPEC.md](../../SPEC.md)). The native Android app is new on site, so demo risk is high. Live genuine callers (≥ 50-call gate) have not been run ([FINDINGS.md](../../ml/realcall/FINDINGS.md)).
- **Safety, privacy, responsible AI (15)**
  - Strength:
    - Consent is enforced in code (`ml/realcall/consent.py`).
    - Voice can never hold money (G2), and no single weak signal can hold.
    - Release of a held payment needs a human.
    - Metadata only, no raw audio for decisions.
    - Fictional demo identities.
    - Fairness slices are planned by language and gender ([SPEC.md](../../SPEC.md); [CLAUDE.md](../../CLAUDE.md)).
  - Weakness: fairness evidence covers only two speakers and one carrier ([FINDINGS.md](../../ml/realcall/FINDINGS.md)). The projected 5.6% of genuine triggered payments reaching Pause & Verify (2.7% ending Amber, 0.21% Red) is still friction for elders ([deck_numbers.json](../../engine/results/deck_numbers.json)). Family-circle data is new personal data under DPDP (Q4).
- **Adoption (10)**
  - Strength: ships as an SDK plus risk API for TPAPs and banks (e.g. Amazon Pay) ([SPEC.md](../../SPEC.md)). It maps to the RBI paper, TRAI 1600, DoT FRI and NCRP/Chakshu (Q4).
  - Weakness: needs each bank's outbound-call registry; Family Verify needs relatives to enrol (network effect); there is no pricing or business model on file.
- **Communication (5)**
  - Strength: honest, traceable numbers.
  - Risk: G1–G7, log-odds and LR tables can swamp a 4-minute slot. The judge notes below say the opening 30 s set the score.

### Inferences
- The biggest swing is **problem fit and differentiation**. Open with the attack (a cloned voice asks for money, then HOLD), then explain why detectors fail (0/12), then the fix. Otherwise judges anchored on "detection" may score fit low.
- The biggest residual risk is feasibility on stage, from the native app and venue network. Keep the web two-phone flow as the guaranteed path.

### Gaps
- Not known whether judges score the deck or only the live pitch at the finale, or the time per team.
- No measured elder comprehension yet (V3 is "planned for the finale" in [SPEC.md](../../SPEC.md)).

---

## Q6. Likely hard questions from security researchers, Amazon engineers and bankers, with strong answers

### Takeaway
Expect attacks on:
- the trust anchor (the relative's phone, SIM swap, coached victims);
- detector credibility (0/12, 11.7% EER vs "99%");
- friction and liability (genuine emergencies);
- Android and VoIP feasibility;
- adoption (who integrates, who pays).

Each has a concise, evidence-backed answer below. Naming two or three of these weaknesses *before* being asked is itself a scoring move (Q7).

### Cited Findings (answers grounded in sources)
- **"Your detector caught 0 of 12 Sarvam clones. Why trust any of this?"**
  - Answer: "That's exactly why voice can't hold money (G2). The newest generator beats every detector. ElevenLabs can't reliably detect its own v3, and open-source detectors lose 48% AUC in the wild. Our hold came from the relative's 'Not me', 14 s after Pay."
  - Sources: [FINDINGS.md](../../ml/realcall/FINDINGS.md); [ElevenLabs](https://elevenlabs.io/ai-speech-classifier); [arXiv 2503.02857](https://arxiv.org/abs/2503.02857v1).
- **"Pindrop claims 99%. You're at 11.7% EER."**
  - Answer: "Vendor numbers aren't measured on Hindi speakerphone audio over Jio. In NPR's independent test, one of three vendors did well and the others misclassified 24–50%. Ours is a pre-registered held-out handset with confidence intervals. And if a bank prefers Pindrop, it plugs into our voice slot."
  - Sources: [NPR](https://www.npr.org/2024/04/05/1241446778/deepfake-audio-detection); [FINDINGS.md](../../ml/realcall/FINDINGS.md).
- **"What if the scammer coaches the victim to say 'nobody asked me'?"**
  - Answer: "The call-context signals still fire: on or just after a call, new payee, unknown caller, FRI tier. So 'nobody' plus those signals still means Pause. We can't fully protect a coached victim; that's why the cooling-off and the RBI-style hold exist."
  - The simulator ablation shows context alone puts 85.3% of scams at Amber or above (projection) — [deck_numbers.json](../../engine/results/deck_numbers.json).
- **"What if the relative's phone or SIM is compromised?"**
  - Answer: "The answer is signed by a key bound to the relative's app install, not to the SIM, so a SIM swap doesn't move it. Compromising the relative's handset costs far more than 3 seconds of public audio."
  - Device-binding rationale: NIST SP 800-63B-4, "Biometrics SHALL only be used as part of multi-factor authentication with a physical authenticator" — [NIST](https://pages.nist.gov/800-63-4/sp800-63b.html) (team notes).
  - Have the key-storage detail (Android Keystore?) ready. Unverified here.
- **"Can a scammer spam Family Verify to wear out the relative (MFA fatigue)?"**
  - Answer: requests start only from the payer's own app during a payment and show amount, payee and a reason. Rate-limit them, and treat a timeout as non-decisive.
  - Confirm rate limiting actually exists in code before claiming it.
- **"The caller claims to be police or a friend, not family."**
  - Answer: bank claims go to the 1600 registry check, which TRAI has mandated since Jan–Mar 2026 — [Storyboard18](https://www.storyboard18.com/amp/how-it-works/trai-sets-early-2026-deadline-for-bfsi-to-transition-to-1600-calling-range-to-combat-spoofing-84495.htm).
  - Police: the arrest-threat cue plus a long call means Pause ([SPEC.md](../../SPEC.md)).
  - A friend outside the circle: one-tap callback to the saved number, or the safe word.
- **"A genuine medical emergency gets held. Who's liable?"**
  - Answer: Family Verify "Yes, it's me" or a callback confirmation is decisive Green (G4). Holds are released by a human, and the cooling-off is capped at 30 min.
  - Projected 0.21% of genuine triggered payments end Red — [deck_numbers.json](../../engine/results/deck_numbers.json). Always say "projection".
- **(Amazon) "Why not Amazon Connect Voice ID?"**
  - Answer: "It reached end of support on 20 May 2026. AWS pointed customers to Pindrop or OTP. We don't do voiceprints at all: Connect's outbound-contact records feed our 'is your bank really calling?' check."
  - Source: [AWS docs](https://docs.aws.amazon.com/connect/latest/adminguide/amazonconnect-voiceid-end-of-support.html).
- **(Amazon) "What breaks first at scale? Latency? Cost?"**
  - Answer: the decision path is arithmetic over signals. Voice (3.1 s on CPU) is off the decision path in shadow mode ([FINDINGS.md](../../ml/realcall/FINDINGS.md)).
  - The first to break are human release-queue staffing and relative response times, not compute.
  - Have a per-decision cost estimate ready (not computed here: a gap).
- **(Bank) "How does this fit RBI and NPCI?"**
  - Answer: "It's a risk-triggered version of RBI's April 2026 trusted-person and 1-hour-hold proposals, applied only when a call and a new payee co-occur. It sits inside the PSP or bank app before the UPI call, so no NPCI change is needed."
  - Sources: [MediaNama](https://www.medianama.com/2026/04/223-safeguard-elderly-rbi-suggests-trusted-person-approval-high-value-digital-payments/); [Outlook Business](https://www.outlookbusiness.com/economy-and-policy/rbi-proposes-1-hour-delay-for-transactions-above-10000-to-fight-digital-fraud).
- **(Bank) "How many good customers will you annoy?"**
  - Answer (simulator projection): 41.8% of genuine triggered payments pass silently, 52.6% with one tap, 5.6% see Pause & Verify, 2.7% end Amber, 0.21% end Red — [deck_numbers.json](../../engine/results/deck_numbers.json).
  - Contrast: RBI's proposal would hold *every* P2P transfer above ₹10,000 for up to an hour.
- **"Does it work on WhatsApp calls? Do you record calls?"**
  - Answer: no recording for decisions; call metadata only; voice scoring is opt-in and in shadow mode ([SPEC.md](../../SPEC.md)).
  - WhatsApp: be honest about what the native app detects today. Telephony call state does not cover VoIP; unverified.
- **(Security) "Can't the scammer just tell the victim to use a different app?"**
  - Answer: Pehchaan has to be in the bank or PSP layer to be unavoidable. That's why the adoption path is via TPAPs (PhonePe, Paytm and Google Pay are over 90% of UPI and already integrate FRI) — [Business Standard](https://www.business-standard.com/industry/news/dot-launches-financial-fraud-risk-indicator-to-aid-cybercrime-detection-125052101912_1.html).

### Inferences
- Prepare a one-page "known weak spots" sheet: Sarvam 0/12, mocked adapters, no live genuine callers, projections, two speakers, Android permissions. Volunteer two of them in the pitch.
- Every numeric answer must cite `FINDINGS.md` or `deck_numbers.json` and say "projection" where it applies (CLAUDE.md rule).

### Gaps
- No verified source for Pehchaan's key storage, rate limiting, or VoIP call detection. Confirm in code before answering.
- No cost-per-decision or pricing model was found in the repo.

---

## Q7. What do winning AI-security hackathon pitches do well, and how do judges weigh live demos, measured results and honest negatives?

### Takeaway
Judges reward:
- a working end-to-end demo over slides;
- narrow scope executed well;
- a plain "this does X for Y" opening;
- volunteering known weaknesses (claiming nothing breaks "lose[s] credibility instantly");
- a clear split between what existed before and what was built at the event.

RAKSHAM's own text asks for "specific, buildable, and safe" and "substance over slide polish". Its brief explicitly distrusts single detector scores, which favours Pehchaan's honest negatives.

### Cited Findings
- A judge's year-long notes:
  - a live demo "removes doubt";
  - narrow, well-built projects beat platform-scale ones ("judgment under a constraint");
  - naming a weakness before being asked raised scores;
  - judges usually ask who it is for, what was built this weekend, and what breaks first at scale;
  - blurring prior work reads as concealment;
  - the opening 30 s is "where the score is set";
  - over-polished UI suggests a neglected backend.
  - Source: [DEV Community](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l).
- Indian hackathon judging usually varies five criteria: innovation, technical implementation, impact, demo/presentation and completeness. Judges check whether it works rather than being a mockup — [Reskilll](https://blogs.reskilll.com/what-hackathon-judges-look-for-complete-judging-criteria-breakdown-2026/).
- Practical demo advice: hardcode or cache the demo path, test on a clean restart, have fallbacks for rate limits — [Reskilll](https://blogs.reskilll.com/what-hackathon-judges-look-for-complete-judging-criteria-breakdown-2026/); [HackerEarth](https://www.hackerearth.com/blog/10-tips-win-hackathon).
- An AWS security-AI hackathon asked for one overview slide plus a live demo — [AWS](https://aws.amazon.com/startups/events/aws-ai-agents-hackathon).
- RAKSHAM:
  - "Substance matters more than slide polish. We reward products that are specific, buildable, and safe."
  - The brief stresses no auto-blocking on a single weak signal, that "a detector score alone is not an explanation or proof", human review, and adversarial adaptation.
  - Source: [Unstop listing](https://unstop.com/competitions/raksham-ai-cybersecurity-hackathon-iit-delhi-1761331) via [competition_intel.md](../../research/competition_intel.md).
- The team's earlier prediction for rivals: most Track 01 teams will show a fine-tuned wav2vec2/AASIST upload page reading "97% FAKE" — [track01_voice_cloning.md](../../research/track01_voice_cloning.md) (team judgement, not a source).

### Inferences
- With 30 finalists, a two-phone live attack that ends in HOLD is the memorable "central identity". Pehchaan should be "the team whose cloned call got stopped in 14 seconds".
- Honest negatives score when they come *with a design response*: "0/12, so voice is shadow-only." Without one, they read as failure.
- State plainly what was built before 16 Oct, between 16 and 23 Oct, and on site.

### Gaps
- No public guidance on how RAKSHAM finale judges weight the live demo against the deck, or on pitch length.
- No public list of finale judges (team notes say none were named).

---

## Q8. What are the highest-leverage additions for the 2 finale days, and what are the top 5 changes to the pitch and demo?

### Takeaway
The team's own plan says no new features on 24 Oct, only fixes ([TASKS.md](../../TASKS.md)). So the biggest gains come from **reframing and low-risk evidence**, not new code:
- an attack-first demo with the genuine-path contrast;
- a positioning slide that turns detectors into plug-ins;
- an RBI/TRAI/FRI/Amazon Connect adoption slide;
- a 5-person comprehension test plus a 10-minute red-team round;
- a pre-empted weak-spots and Q&A sheet.

The native Android app is worth showing only if it is rock-solid; the web two-phone flow is the guaranteed path.

### Cited Findings
- Planned but not done:
  - V3 comprehension hallway test with 5 people ([SPEC.md](../../SPEC.md));
  - the full end-to-end run ×3 on deployed URLs, backup video, and rehearsal ×3 ([TASKS.md](../../TASKS.md));
  - live genuine calls ([FINDINGS.md](../../ml/realcall/FINDINGS.md)).
- Already measured and demo-ready: a live cloned call then Pay gave HOLD in 14 s (T1) and 4 s (T3) ([FINDINGS.md](../../ml/realcall/FINDINGS.md)).
- Regulatory hooks: RBI trusted person and 1-hour hold (Apr 2026), TRAI 1600 deadlines (Jan–Mar 2026), DoT FRI used by PhonePe, Paytm and Google Pay (Q4 sources).
- Amazon hooks:
  - Voice ID end of support, with AWS pointing to Pindrop or OTP — [AWS docs](https://docs.aws.amazon.com/connect/latest/adminguide/amazonconnect-voiceid-end-of-support.html);
  - Amazon Pay UPI Circle — [aboutamazon.in](https://www.aboutamazon.in/news/retail/amazon-pay-upi-circle-family-payments);
  - "Behaviour is much harder to fake" — [TOI](https://timesofindia.indiatimes.com/business/india-business/ai-fraud-is-hitting-indias-new-net-users-hardest-amazon/articleshow/132843254.cms).
- Judges reward volunteered weaknesses and a sharp opening — [DEV Community](https://dev.to/kurbaitaev/what-judges-actually-score-notes-from-a-year-of-hackathon-judging-3p4l).

### Inferences

**Other additions considered, ranked lower:**
- **Multilingual elder UX polish** (Hindi read-aloud, large text): good for Safety and Problem fit, but only if it's copy and config. Not new screens.
- **"Bring your own detector" adapter demo** (call Reality Defender's free tier, 50 scans a month, from the voice slot): strong differentiation story but new integration risk. Mention it; don't build it.
- **Native Android app** (real call state, Family Verify notification, upi:// interception): high Feasibility upside, high stage risk. Show it as a 20-second clip or a secondary path, with the web flow as the primary path.
- **Rotating safe word (Signet-style)**: a roadmap line only.
- **Live genuine calls toward the ≥ 50-call gate**: needs signed volunteer consent ([TASKS.md](../../TASKS.md)). If not done, say "not yet shown".

### Top 5 changes to the pitch and demo for the biggest score gain in 2 days (ranked)

1. **Open with the attack, not the architecture.** (Problem fit 20, Communication 5, Feasibility 15.) This is the "central identity" judges remember.
   - First 30 s: "Pehchaan stops UPI payments to voice-cloned callers by verifying the person, not the voice."
   - Then, live on two phones: a consented Sarvam-cloned "son" calls; the payer taps Pay; "Who asked you to pay?"; automatic Family Verify; "Not me" on the real son's phone; HOLD in about 14 s.
   - Immediately run the genuine path (the real son confirms, payment goes through) to show low friction.
   - The backup video must be ready.
2. **Add one positioning slide: "Detectors are a plug-in; verification is the product."** (Differentiation 15, Architecture 20.)
   - Columns: detectors (Pindrop / Reality Defender / Hiya / Resemble / Truecaller / Google), behavioural scores (BioCatch / Feedzai / Sardine), verification habits (Monzo call status, safe-word apps), and Pehchaan as the payment-moment orchestration layer.
   - Under it, one line of independent evidence: NPR (two of three tools unreliable), Deepfake-Eval (−48% AUC), ElevenLabs can't catch its own v3, and our own **0/12 on Sarvam**.
   - This turns the honest negative into the thesis.
3. **Add one adoption slide that maps Pehchaan onto Indian regulation and Amazon.** (Adoption 10, Feasibility 15.)
   - RBI's April 2026 discussion paper: trusted person (= Family Verify) and a 1-hour hold (Pehchaan's 30-min cooling-off, risk-triggered only).
   - TRAI 1600 (= the bank registry check).
   - DoT FRI (already in PhonePe, Paytm, Google Pay).
   - NCRP / Chakshu evidence pack.
   - Amazon: Connect outbound-contact records feed "is my bank calling?" (the replacement for voiceprints, since Voice ID ended 20 May 2026), and Amazon Pay UPI Circle as the family graph.
   - Label the RBI item "proposal".
4. **Generate two small pieces of on-site evidence: a 5-person comprehension test and a 10-minute red-team round.** (Safety and responsible AI 15, Problem fit 20.)
   - Comprehension: run SPEC's V3 test of the Pause & Verify screen with consenting participants, using fictional names. Report time-to-decision and how many understood the reason, with n and caveats.
   - Red team: invite mentors or other teams to try to get money through (coach the victim to say "nobody", spam Family Verify, "I forgot the safe word"). Log each attempt and outcome on one slide.
   - Little or no new code. Directly answers the brief's "adversarial adaptation" and "human review" asks.
5. **Pre-empt the hard questions: a "What we haven't proven yet" strip and a printed Q&A sheet.** (Communication 5, plus credibility across all lines.)
   - Volunteer in the pitch: Sarvam 0/12 (n = 12); FRI and registry adapters mocked; fusion numbers are simulator projections (5.6% of genuine payments see Pause & Verify, 0.21% Red); no live genuine callers yet; two speakers and one carrier.
   - Show a three-column "before 16 Oct / 16–23 Oct / on site" build split.
   - Rehearse the answers in Q6, especially Android permissions or VoIP, the trust anchor, and liability for a genuine emergency.

### Gaps
- Scores per change are judgement, not measured. Nothing public says how much RAKSHAM judges value each item.
- Whether the comprehension test is feasible on site depends on finding consenting participants and on IIT Delhi venue rules (not checked).
