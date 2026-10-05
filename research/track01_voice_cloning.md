# RAKSHAM Track 01: Voice Cloning Fraud Detection (research findings)

Prepared 2026-10-05 for the Round 1 PDF (due 2026-10-07). Every number below links to a source. Where a claim comes from a vendor or a secondary source, it is labelled that way. Anything I could not verify is listed in section 9.

---

## Key numbers with citations

| # | Fact / number | Source (publisher, date) |
|---|---|---|
| 1 | **47%** of Indian adults said they had experienced an AI voice scam or knew someone who had (global figure 25%). **83%** of Indian victims lost money, and 48% of those lost up to Rs 50,000. **69%** of Indians were not confident they could tell a cloned voice from a real one. **86%** share their voice online at least weekly. The survey covered n=7,054 people in 7 countries, 13–19 Apr 2023. | McAfee, *Beware the Artificial Impostor*, May 2023 ([PDF](https://www.mcafee.com/content/dam/consumer/en-us/resources/cybersecurity/artificial-intelligence/rp-beware-the-artificial-impostor-report.pdf)); [BusinessWire 1 May 2023](https://www.businesswire.com/news/home/20230501005587/en/Artificial-Intelligence-Voice-Scams-on-the-Rise-with-1-in-4-Adults-Impacted); [BOOM 3 May 2023](https://www.boomlive.in/explainers/ai-voice-scam-voice-cloning-mcafee-report-21851) |
| 2 | Chakshu (Sanchar Saathi) reports of **"Impersonation as a relative/friend"** went from **258 in 2024 to 19,564 in 2025** (about 76x). "Impersonation as Police/CBI/Customs/Aadhaar/RBI" went from 44,865 to 54,639. All Chakshu reports went from 208,224 to 519,662. | PIB / DoT Rajya Sabha reply, [5 Feb 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223779) |
| 3 | In its first 24 hours, DoT's International Incoming Spoofed Calls Prevention System blocked **1.35 crore calls**. That was **90%** of all incoming international calls showing +91 numbers. | PIB, [22 Oct 2024](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2067113) |
| 4 | DoT's **Financial Fraud Risk Indicator (FRI)** launched 21–22 May 2025. It prevented an estimated **Rs 660 crore** in losses in its first 6 months, and **1000+ banks, TPAPs and PSOs** joined the Digital Intelligence Platform (DIP). By Feb 2026, DIP had 1200+ organisations, including about 1100 banks. | PIB [21 May 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2130249); DoT/PIB [22 Dec 2025 (PDF)](https://www.dot.gov.in/static/uploads/2026/02/1994430b3740f7f61b7d7fd8b7f5120d.pdf); PIB [5 Feb 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223779) |
| 5 | TRAI made the **1600-series** mandatory for BFSI service and transactional calls. Deadlines: commercial banks **1 Jan 2026**; large NBFCs, payments banks and SFBs 1 Feb 2026; co-op banks, RRBs and remaining NBFCs 1 Mar 2026. Before the mandate, only about 485 entities (2,800+ numbers) had adopted it. | PIB / TRAI, [19 Nov 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2191647); [TRAI Direction PDF](https://www.trai.gov.in/sites/default/files/2025-11/Direction_19112025.pdf) |
| 6 | **CNAP** (KYC-name caller ID): TRAI agreed with DoT to make it default with opt-out (28 Oct 2025). The pilot started Oct–Nov 2025, initially excluding 2G. Vi said it was live on-net nationwide on 30 Dec 2025. The target for full rollout was March 2026. | [Business Standard 28 Oct 2025](https://www.business-standard.com/industry/news/trai-dot-cnap-default-opt-out-caller-id-rollout-125102801428_1.html); [Storyboard18 29 Oct 2025](https://www.storyboard18.com/how-it-works/caller-name-display-pilot-to-begin-this-week-on-mobile-networks-2g-users-left-out-83313.htm); [TelecomTalk 30 Dec 2025](https://telecomtalk.info/vi-claims-cnap-live-across-india-net/1003106/); [TOI 8 Jan 2026](https://timesofindia.indiatimes.com/technology/tech-news/why-you-are-seeing-names-flashing-for-calls-from-unknown-numbers-what-is-governments-cnap-how-it-works-and-is-different-from-truecaller/articleshow/126389246.cms) |
| 7 | **ASVspoof 5** (2024), Track 1 deepfake detection. Baselines: EER >29%. Best closed-condition system: EER **8.61%** (minDCF 0.2436). Best open-condition system: EER **2.59%** (minDCF 0.0750). Top systems were badly calibrated (actDCF about 1.0). The evaluation set includes 8 kHz codecs (Opus, AMR, Speex). | Wang et al., [arXiv 2408.08739, 16 Aug 2024](https://arxiv.org/abs/2408.08739) |
| 8 | Detectors trained on ASVspoof degrade by **up to 1000%** on real-world "In-the-Wild" audio. | Müller et al., Interspeech 2022, [arXiv 2203.16263](https://arxiv.org/abs/2203.16263) |
| 9 | On real 2024 deepfakes, open-source SOTA **audio detectors lose 48% AUC**. Commercial and fine-tuned models do better but still trail human forensic analysts. | Chandra et al., *Deepfake-Eval-2024*, [arXiv 2503.02857, Mar 2025](https://arxiv.org/abs/2503.02857) |
| 10 | Generalisation gap in one model: NII **AntiDeepfake MMS-300M** (post-trained on 56k h real and 18k h fake audio) scores **EER 2.90% on In-the-Wild** but **32.84% on Deepfake-Eval-2024**. After fine-tuning on DFE-2024, EER is **17.15% with 4 s** windows and 10.79% with 50 s windows. | [HF model card](https://huggingface.co/nii-yamagishilab/mms-300m-anti-deepfake); [arXiv 2506.21090, Jun 2025](https://arxiv.org/abs/2506.21090) |
| 11 | **PITCH** challenge-response against real-time deepfake calls: machine AUROC 88.7%; humans alone 72.6%; human+AI 84.5%. | Mittal et al., [arXiv 2402.18085 (Feb 2024, v4)](https://arxiv.org/abs/2402.18085) |
| 12 | Open-source real-time voice conversion (**Seed-VC**) has about **300 ms algorithmic plus about 100 ms device latency**. It needs only 1–30 s of reference audio and no training. | [Seed-VC README](https://github.com/Plachtaa/seed-vc) |
| 13 | Pindrop (vendor): deepfake fraud attempts **+1,300% in 2024** (from 1 per month to 7 per day); synthetic-voice attacks at banks +149%. | [Pindrop PR, 12 Jun 2025](https://www.prnewswire.com/news-releases/pindrops-2025-voice-intelligence--security-report-reveals-1-300-surge-in-deepfake-fraud-302479482.html) |
| 14 | Google's on-device **Scam Detection** for calls launched in India in Hindi and English, but only on **Pixel 9+**. Pixel had **<1%** share of India's smartphone market in 2024. | [TechCrunch, 20 Nov 2025](https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain/) |
| 15 | **Truecaller AI Call Scanner** is "currently only available in the U.S. on Android" (vendor page, checked Oct 2026). | [truecaller.com/ai-call-scanner](https://www.truecaller.com/ai-call-scanner) |
| 16 | **RBI Authentication Directions 2025**: compliance date **1 Apr 2026**. Issuers may run risk-based checks beyond 2FA using "transaction location, user behaviour patterns, device attributes". DigiLocker may be used to notify and confirm **high-risk transactions**. Non-compliant issuers must compensate customers in full. | [RBI/2025-26/79, 25 Sep 2025](https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12898) |
| 17 | **Amazon Connect Voice ID** (AWS voice biometrics) **end of support: 20 May 2026**. OpenAI publicly recommended "phasing out voice based authentication" for bank accounts. | [AWS docs](https://docs.aws.amazon.com/connect/latest/adminguide/amazonconnect-voiceid-end-of-support.html); [OpenAI, 29 Mar 2024](https://openai.com/index/navigating-the-challenges-and-opportunities-of-synthetic-voices/) |
| 18 | **IndicSynth**: 4,000 h of synthetic speech from 989 speakers in 12 Indian languages, licensed CC-BY-NC-4.0. It uses only **XTTS-v2, VITS and FreeVC24**, which are older generators. | [ACL 2025](https://aclanthology.org/2025.acl-long.1070/); [HF dataset card](https://huggingface.co/datasets/vdivyasharma/IndicSynth) |
| 19 | National Cybercrime Reporting Portal (NCRP), 2021–2025: **>65.9 lakh** financial-fraud complaints and **>Rs 55,050 crore** reported. Rs 11,158 crore saved via 1930/CFCFRMS (to 30 Jun 2026). | PIB / MHA, [21 Jul 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287039) |
| 20 | Airtel's AI spam filter had flagged **27.5 billion** calls as spam by Apr 2025. Spam alerts are now shown in 9 Indian languages. | [Airtel PR, 21 Apr 2025](https://www.airtel.in/press-release/04-2025/airtel-announces-new-features-in-its-continued-fight-against-spam) |

---

## 1. India threat evidence (2023–2026)

### 1a. Reported incidents (verified to a news or government source)
| Date | Incident | Pattern | Source |
|---|---|---|---|
| Jul 2023 | Kozhikode, Kerala: P.S. Radhakrishnan lost Rs 40,000 to a deepfake **video+voice** call from someone posing as a former colleague. This is widely called Kerala's first AI deepfake fraud. | Friend in need | [OECD AI incident 2023-07-16](https://oecd.ai/en/incidents/2023-07-16-08e3) |
| Nov 2023 | Hyderabad: a 59-year-old woman lost Rs 1.4 lakh. The caller sounded like her nephew in Canada, "in the Punjabi we speak at home", and claimed he had an accident and faced jail. | Family emergency (NRI relative) | [IndiaAI, 21 Nov 2023 (citing TOI)](https://indiaai.gov.in/news/a-woman-from-hyderabad-loses-1-4-lakh-rupees-in-an-ai-scam) |
| 8 Jan 2024 | Delhi-NCR: a father heard "Papa please pay him, they are real policemen" from a voice cloned from his 18-year-old son, and paid Rs 10,000. Delhi Police called it "an uptick in cases of cloning". A similar attempt targeted a Noida mother. | Fake police + child in custody | [Straits Times, 12 Feb 2024 (citing Indian Express)](https://www.straitstimes.com/asia/south-asia/scammers-are-using-ai-to-clone-kids-voices-and-fool-parents-in-india) |
| Apr 2024 | Tamil Nadu Cyber Crime Wing issued an advisory on AI voice-clone impersonation of relatives and friends. | Advisory | [The Hindu, 27 Apr 2024](https://www.thehindu.com/news/national/tamil-nadu/tn-cyber-crime-police-issue-advisory-on-new-scam-involving-ai-voice-cloning/article68113216.ece) |
| Oct 2024 | **Corporate**: Airtel chairman Sunil Bharti Mittal said scammers cloned his voice to tell a senior finance executive in Dubai to make a large transfer. The executive did not comply. | CEO/CFO fraud (attempt) | [The Hindu / PTI, 22 Oct 2024](https://www.thehindu.com/sci-tech/technology/scammers-cloned-billionaire-sunil-mittals-voice-with-ai-to-con-his-executive-report/article68781591.ece) |
| Mar 2025 | Hyderabad: a 72-year-old homemaker lost Rs 1.97 lakh via GPay. Police said the scammers "could have used AI-generated voice" to mimic her sister-in-law. | Family emergency | [The Hindu, 18 Mar 2025](https://www.thehindu.com/news/national/telangana/homemaker-duped-of-197-lakh-in-ai-voice-scam/article69344422.ece) |
| (reported May 2025) | Delhi: Laxmi Chand Chawla paid Rs 50,000. A fake "cop" put a cloned voice of his nephew on the line, claiming custody in an assault case, then demanded Rs 2 lakh more. Mumbai: K.T. Vinod paid Rs 80,000 after a fake "Indian Embassy Dubai" call with his son's cloned voice. | Fake police + relative | [Indian Express, 23 May 2025](https://indianexpress.com/article/technology/tech-news-technology/the-safe-side-ai-voice-cloning-scams-10023971/) |
| Jan 2026 | Uttarakhand police describe AI voice cloning and digital arrest as the new modus operandi. The state had 10,300 cybercrime cases and Rs 90 crore in losses in 2025. | Trend | [ETV Bharat, 10 Jan 2026](https://www.etvbharat.com/en/state/cyber-fraudsters-are-emptying-uttarakhand-people-bank-accounts-using-otp-fraud-and-ai-generated-voice-impersonation-enn26011003515) |
| Oct 2026 | J&K Police advisory on AI voice-cloning scams. MeitY social post: "Deepfakes are being used to impersonate loved ones. Set a family passphrase…" | Advisory | J&K Police (FB, early Oct 2026); [MeitY on X, early Oct 2026](https://x.com/GoI_MeitY/status/2107055701042577847/photo/1) (exact date approximate) |

**Pattern for the deck:** the dominant Indian voice-clone fraud is a hybrid. A fake authority (police, CBI, embassy) and a cloned relative appear on the same call. The call comes from an unknown or overseas number, often over WhatsApp/OTT. The victim is told to pay *now* through UPI/GPay and keep it secret. The victim's bank sees only a normal, customer-authenticated UPI payment. This is "authorised push payment" (APP) fraud: the victim's own credentials are used, so OTP/2FA does not help.

**Digital arrest context:** 2022–2025 saw 241,537 digital-arrest cases and Rs 3,012 crore in losses (ThePrint, via [ORF, 18 Jul 2026](https://www.orfonline.org/expert-speak/digital-arrest-scams-and-the-limits-of-domestic-enforcement)). A secondary source, citing I4C, reports 92,000+ cases in Jan–Oct 2024 with Rs 2,140 crore lost ([Securonix blog](https://www.securonix.com/blog/digital-arrest-scams-india-social-engineering/)). How much of digital arrest uses *cloned* voices, rather than live human actors, is **not quantified** in any source I found. Most reports describe fake uniforms, backdrops and documents. Claim "AI voice is an emerging component", not that it dominates.

### 1b. Surveys
- McAfee 2023: see key numbers #1. This is the best-known India figure. Be precise in the deck: the 47% is "experienced *or know someone who* experienced", not 47% victims.
- McAfee 2024 (deepfakes, election year): 75% of Indians surveyed had seen deepfake content in the previous 12 months ([Mint, Apr 2024](https://www.livemint.com/mint-lounge/india-ai-deepfake-content-mcafee-cricket-elections-ipl-11714215815801.html)). This is secondary and not voice-specific.
- UK comparator: Starling Bank found 28% of UK adults were targeted by an AI voice-clone scam in the past year ([Guardian, 18 Sep 2024](https://www.theguardian.com/money/2024/sep/18/warning-social-media-videos-exploited-scammers-clone-voices)).

### 1c. Government and regulator advisories
- **CERT-In CIAD-2024-0060, "Deepfakes – Threats and Countermeasures"** (27 Nov 2024, severity High). Covers fake audio and "robotic-sounding voices". Advice: verify through other channels and limit what you share ([CERT-In](https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES02&VLCODE=CIAD-2024-0060)).
- **I4C / CyberDost** runs recurring social posts on AI voice cloning and "police will never arrest you over a phone call" (Facebook/Instagram). I found no I4C formal advisory PDF specific to voice cloning ([I4C advisories index](https://i4c.mha.gov.in/advisories.aspx)).
- **DoT**: the spoofed-call system, Chakshu, FRI and CNAP are all call-context tools (section 2). I found no DoT document specific to voice cloning.
- **RBI**: no voice-cloning-specific circular found. The relevant hook is the **2025 Authentication Directions**, with risk-based step-up and DigiLocker confirmation for high-risk transactions (key numbers #16). RBIH's MuleHunter.AI targets mule accounts; per an RTI, 23 banks use it ([MediaNama, Dec 2025](https://www.medianama.com/2025/12/223-rti-23-banks-mulehunter-mule-accounts/)).
- **NPCI**: no voice-cloning advisory found.
- **Banks' own awareness posts**: Union Bank, IOB and RBL Bank have published voice-clone warnings ([RBL blog](https://www.rbl.bank.in/blog/banking/safe-banking/what-is-voice-cloning-fraud-how-to-safeguard-yourself-from-voice-cloning-fraud)).

### 1d. Indian banks using voice biometrics or phone banking for high-risk actions
- **ICICI Bank** launched voice-recognition authentication for its call centre on **25 May 2015**, for 33 million customers: "Their voice will now act as the password for banking transactions through the call centre" ([ICICI press release](https://www.icici.bank.in/about-us/news-room/2015/news-icici-bank-introduces-voice-recognition-for-biometric-authentication)). I could not verify whether it is still active in 2026.
- **Citi India** introduced voice-biometric authentication for phone banking in 2017. Only secondary sources (quiz sites, FB) confirm this; treat as unverified.
- Vendors such as Gnani.ai and YuVerse market voice biometrics to Indian banks. Their "92–98% accuracy" style claims are vendor marketing.
- I could not confirm which Indian banks allow **mobile-number change, credential reset or beneficiary addition purely over phone/IVR**. Most public bank pages route these through the app, net banking, branch or ATM with OTP or TPIN. **Implication:** the bigger Indian risk is on the **customer side** (the victim authorises a UPI payment while on a scam call) and in **contact-centre social engineering** (requests to unblock, raise limits or update contact details), rather than voiceprint spoofing.
- Global signal: AWS is retiring Amazon Connect Voice ID (20 May 2026). OpenAI recommends phasing out voice authentication. Sam Altman told a Fed conference that "AI has fully defeated" voiceprint authentication ([Fortune, 24 Jul 2025](https://fortune.com/2025/07/24/sam-altman-fraud-crisis-ai-voice-mimicking-federal-reserve/)). **Do not build a "better voiceprint". Build the replacement workflow.**

---

## 2. Indian telecom and regulatory context (call-context signals)

| Signal | Status (as of Oct 2026) | How a product could use it | Limits |
|---|---|---|---|
| **1600-series** for BFSI service/transaction calls | Mandated. Banks were due 1 Jan 2026, all RBI-regulated entities by 1 Mar 2026 ([PIB 19 Nov 2025](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2191647)). Insurance deadline still pending with IRDAI. Actual compliance level after the deadlines: **unverified**. | A caller claiming to be "your bank" from a non-1600 number is a strong red flag. The bank app can show "Genuine bank calls come only from 1600-xx". | Says nothing about relative or police impersonation. Scammers can still call from 10-digit numbers and just claim to be the bank. |
| **International Incoming Spoofed Calls Prevention System** | Live since 22 Oct 2024. Blocked 1.35 crore spoofed calls in the first 24 hours ([PIB](https://www.pib.gov.in/PressReleaseIframePage.aspx?PRID=2067113)). TSPs also show "International call" labels. RICWIN lets citizens report international calls showing +91 numbers. | "Call is international or OTT" is a contextual risk feature. | Pushes fraud onto OTT (WhatsApp) and domestic SIM-boxes. MediaNama raised false-positive concerns ([Oct 2024](https://www.medianama.com/2024/10/223-indian-spoofed-calls-prevention-system-blocks-1-35-crore-calls-amidst-false-positives-concerns/)). |
| **FRI (Financial Fraud Risk Indicator)** via DoT DIP | Live since May 2025. Scores mobile numbers Medium/High/Very High. PhonePe declines "Very High" and warns on "Medium". 1000+ banks/TPAPs onboarded; Rs 660 crore saved in 6 months ([PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2130249), [DoT PDF](https://www.dot.gov.in/static/uploads/2026/02/1994430b3740f7f61b7d7fd8b7f5120d.pdf)). | Risk of the **payee's** linked mobile and of the **caller's** number, plus MNRL (revoked numbers). A model for graded friction: PhonePe already declines Very High and only warns on Medium. | Number-level, so it lags fresh SIMs. Access is for regulated entities only; a hackathon must **mock** it. |
| **Sanchar Saathi / Chakshu** | 7.7 lakh citizen inputs led to 39.43 lakh connections disconnected. Category data shows relative/friend impersonation rising ([PIB 5 Feb 2026](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223779)). It also publishes "Trusted Contact Details" for banks. | One-tap "report to Chakshu" in the evidence path. The trusted-contact directory supports a **callback-to-verified-number** step. | Crowd-sourced and after the fact. |
| **CNAP** (KYC name shown on incoming calls) | Framework approved Oct 2025, default with opt-out. Pilots ran Oct–Nov 2025 (2G excluded). Vi live on-net Dec 2025; users saw names from Jan 2026. Target nationwide March 2026. **Whether full interoperable rollout is complete is unverified.** | Mismatch signal: the voice says "I'm your son/Inspector X" but the KYC name shown is someone else. | Shows the SIM owner's KYC name, often a mule, so it confirms only "not who they claim". Does not cover WhatsApp/VoIP calls. Opt-out exists. |
| **Telco AI spam detection** | Airtel launched network AI spam detection in Sep 2024 (flagging 100M spam calls a day), had flagged 27.5 bn calls by Apr 2025, and added Business Name Display in May 2025 ([Airtel 2024](https://www.airtel.in/press-release/09-2024/airtel-cracks-down-on-spam-launches-indias-first-ai-powered-network-solution-for-spam-detection), [2025](https://www.airtel.in/press-release/04-2025/airtel-announces-new-features-in-its-continued-fight-against-spam), [GSMA](https://www.gsma.com/solutions-and-impact/technologies/security/scams/general/bharti-airtel-spam-and-scam-prevention-with-ai/)). Jio began showing spam/fraud alerts around Sep 2025 ([TelecomTalk 20 Sep 2025](https://telecomtalk.info/jio-starts-showing-spam-fraud-alerts/999928/)). | A "suspected spam" label is an input feature, if the OS or telco exposes it. | Based on number reputation and traffic patterns, not on the voice. Personalised one-off clone calls look like ordinary calls. |

**Insight:** India already has a **national call-context stack**: 1600, spoof blocking, CNAP, FRI/DIP, Chakshu. RBI's directions explicitly allow risk-based step-up on "behavioural/contextual parameters". **No one links that stack to the live moment of payment, or to the content and acoustics of the call.** That gap is our opening.

---

## 3. Competitors and existing products: what they leave open

| Product | What it does | India availability | Gap |
|---|---|---|---|
| **Truecaller AI Call Scanner** (launched May 2024) | User taps "Start AI Detection". The call is briefly put on hold while the voice is analysed, then shows "Human/AI Voice Detected". | **US Android only** (vendor page, Oct 2026) | Not in India. Manual trigger. Premium-only. Binary verdict. Not linked to payments. |
| **Google Scam Detection** (Phone by Google, Gemini Nano) | On-device analysis of the *conversation content* for scam patterns. Off by default. Unknown numbers only. Beeps to announce itself. Hindi + English. Also a screen-share alert pilot with Navi, Paytm and GPay. | Pixel 9+ only (<1% share) ([TechCrunch](https://techcrunch.com/2025/11/20/google-steps-up-ai-scam-protection-in-india-but-gaps-remain/); [Google blog](https://blog.google/security/new-ai-powered-scam-detection-features/)) | Pattern detection, not voice-clone detection. Tiny reach. No bank-side evidence path. |
| **McAfee Deepfake Detector** | Flags AI-generated audio in *videos* playing on select AI PCs. | Launched in India Jan 2025 ([MediaNama](https://www.medianama.com/2025/01/223-mcafee-deepfake-detector-india-ai-altered-audio/)) | PC/video only. Not phone calls. |
| **Pindrop Pulse / Protect / Passport** | Enterprise contact-centre deepfake and liveness detection combined with device, behaviour and metadata signals. | US-centric. No Indian bank deployment found. | Enterprise, English-centric, no Indian telecom-signal integration. This is the closest analogue to "bank-side". |
| **Reality Defender** | Real-time voice deepfake detection API for call centres. Vendor case study: a global bank detected about 960 synthetic calls ([case study](https://www.realitydefender.com/case-studies/how-a-global-bank-mitigates-contact-center-deepfake-threats-with-reality-defender)). | Global API | Detector-only. Customer friction and workflow are left to the bank. |
| **Resemble Detect / DETECT-2B** | Vendor claims 94% accuracy, 200 ms latency, 30+ languages ([page](https://www.resemble.ai/learn/models/detect2b)). Later claims of 99.47% ([BiometricUpdate, Aug 2026](https://www.biometricupdate.com/202608/resemble-ai-expands-multimodal-deepfake-detection-approach-for-new-accuracy-highs)). | API | Vendor-reported accuracy only. A detector alone. Also the maker of Chatterbox. |
| **Modulate** | Claims best accuracy on the HF [Speech-DF-Arena](https://huggingface.co/spaces/Speech-Arena-2025/Speech-DF-Arena) leaderboard. Raised $25M in Sep 2026 ([BiometricUpdate](https://www.biometricupdate.com/202609/deepfake-defense-draws-new-capital-as-voice-detection-checks-near-5-5b-by-2028)). | API | Same: a detector alone. |
| **Indian startups**: Contrails AI (Bengaluru; trust and safety, election deepfakes), pi-labs (Pune; "Authentify", in Gartner's 2026 Emerging Market Quadrant, focused on defence and law enforcement, includes VideoKYC deepfakes), Kroop AI (VizMantiz multimodal, on-device demo with Intel), Vastav AI (Zero Defend; "99%" claim) | Mostly **upload-and-analyse media forensics** or enterprise trust-and-safety tools. | India | None is publicly positioned as a **real-time, payment-flow-integrated** voice-clone defence using Indian telecom signals. Their accuracy claims are unaudited. |
| **Telcos (Airtel/Jio), CNAP, FRI** | Number reputation and identity. | India | Does not examine voice or content. Blind to OTT calls. |

**Gaps to claim:**
1. Indic and code-mixed (Hinglish) robustness on narrowband phone audio.
2. **Fusing** acoustic, call-context, conversation and transaction signals *at the moment of payment or high-risk action*.
3. Graded friction instead of a binary block.
4. A consented, privacy-preserving **evidence path** to the bank, 1930/NCRP and Chakshu.
5. Honest calibration and uncertainty, where competitors market "99%".

---

## 4. Detection state of the art and its limits

### 4a. Benchmarks
- **ASVspoof 5** (Aug 2024; [arXiv 2408.08739](https://arxiv.org/abs/2408.08739), [2502.08857](https://arxiv.org/abs/2502.08857)). About 2,000 crowdsourced speakers (MLS English), 32 attack algorithms, and the first adversarial attacks (Malafide, Malacopula). Codec conditions C1–C11 include **8 kHz narrowband Opus, AMR and Speex**. Track 1 results are in key numbers #7. "Most of the well-performing submissions use features extracted by pre-trained SSL models." Licence: ODC-By ([Zenodo](https://zenodo.org/records/14498691)). **English only.**
- **In-the-Wild** (Müller et al. 2022): 37.9 h of celebrity/politician audio, 17.2 h of it fake. Apache-2.0 ([deepfake-total.com](https://deepfake-total.com/in_the_wild)).
- **Deepfake-Eval-2024** (Mar 2025): 56.5 h of audio from 88 websites in 52 languages. Open-source SOTA loses 48% AUC. CC-BY-SA-4.0, gated ([HF](https://huggingface.co/datasets/nuriachandra/Deepfake-Eval-2024)).
- **Newer generators break detectors.** A Jan 2026 study of Dia2, Maya1 and MeloTTS found that detectors that work on one TTS architecture "may fail against others, particularly LLM-based synthesis". Multi-view fusion was robust ([arXiv 2601.20510](https://arxiv.org/abs/2601.20510)). ShiftySpeech (3,000+ h, 6 TTS, 12 vocoders, Apache-2.0) is a controlled benchmark for this kind of distribution shift ([arXiv 2502.05674](https://arxiv.org/abs/2502.05674)).
- **Telephony and codec effects.** ADD-C benchmark (Apr 2025): codec compression plus packet loss causes a "significant decline" for baseline detectors. Codec augmentation recovers much of the loss ([arXiv 2504.12423](https://arxiv.org/abs/2504.12423)). Narrowband (8 kHz G.711/AMR-NB) removes energy above 4 kHz, where many vocoder artefacts live.
- **Partial spoofs.** PartialSpoof (CC-BY-4.0, [Zenodo](https://zenodo.org/records/4817532), [GitHub](https://github.com/nii-yamagishilab/PartialSpoof)) covers clips where only some segments are synthetic, with frame-level localisation. This matters because a scam call can mix a real human "inspector" with a short cloned "son" segment. A call-level detector must score **per segment** and look for transitions. NII also published `whisper-deepfake-word-detection` (CC-BY-4.0) on HF; I did not evaluate it.
- **Humans are poor judges.** PITCH found 72.6% human accuracy on hard samples. McAfee found 69% of Indians unsure.

### 4b. Open-source pretrained detectors (licences and reported EERs)
| Detector | Backbone | Licence | Reported EER | Notes |
|---|---|---|---|---|
| [TakHemlata/SSL_Anti-spoofing](https://github.com/TakHemlata/SSL_Anti-spoofing) | wav2vec2 XLS-R-300M + AASIST, RawBoost augmentation | **MIT** (code); checkpoints in the repo | 0.82% (ASVspoof21 LA), 2.85% (21 DF) | The standard strong baseline. Easy to fine-tune on our data. |
| [QiShanZhang/SLSforASVspoof-2021-DF](https://github.com/QiShanZhang/SLSforASVspoof-2021-DF) (ACM MM 2024) | XLS-R-300M + Sensitive Layer Selection | **No licence file** (all rights reserved by default) | 1.92% (21 DF), 2.87% (21 LA), **7.46% (In-the-Wild)** | Good ITW number, but legally risky to redistribute. Fine for a research comparison. |
| [nii-yamagishilab/AntiDeepfake](https://github.com/nii-yamagishilab/AntiDeepfake) ([HF collection](https://huggingface.co/collections/nii-yamagishilab/antideepfake-685a1788fc514998e841cdfc)) | wav2vec2 / **MMS-300M/1B** / XLS-R-1B/2B / HuBERT, post-trained on 74k h in 100+ languages | Code BSD-3. **Checkpoints CC BY-NC-SA 4.0.** | MMS-300M: ITW 2.90%, DFE-2024 32.84% (zero-shot); after DFE fine-tune, 17.15% (4 s) to 10.79% (50 s) | **Best starting backbone for Indic.** MMS was pre-trained on 1,400+ languages. Non-commercial weights are fine for a hackathon. |
| [clovaai/aasist](https://github.com/clovaai/aasist) | Spectro-temporal graph attention | MIT | ASVspoof19 era | Lightweight back-end. |
| HF community models: `Gustking/wav2vec2-large-xlsr-deepfake-audio-classification`, `MelodyMachine/Deepfake-audio-detection-V2`, `garystafford/wav2vec2-deepfake-voice-detector` | wav2vec2 classifiers | Apache-2.0 | Self-reported, no audit | Likely overfit to their training sets. **Do not demo these as-is.** |

**Latency.** Published SOTA detectors are utterance-level. For real time, use 2–4 s sliding windows with a 0.5–1 s hop and accumulate evidence over the call. AntiDeepfake's numbers show the trade-off: **short windows give much worse EER** (4 s: 17% versus 50 s: 11%). My estimate (not sourced; benchmark it yourselves) is that an XLS-R-300M forward pass on a 4 s window takes tens of milliseconds on an A100/H100. So compute is not the bottleneck; how much audio you have heard is. Vendors claim 200 ms (Resemble) or "seconds" (Pindrop).

### 4c. Indian-language spoof datasets
| Dataset | Content | Licence | Caveat |
|---|---|---|---|
| **IndicSynth** (ACL 2025, IIIT-Delhi) | 4,000 h synthetic from 989 speakers in 12 languages (bn, gu, hi, kn, ml, mr, or, pa, sa, ta, te, ur). Bona fide audio comes from IndicSUPERB. | CC-BY-NC-4.0 | Generators are only **XTTS-v2, VITS, FreeVC24** (2021–23 era). Clean read speech, no telephony. |
| **IndieFake** ([arXiv 2506.19014](https://arxiv.org/abs/2506.19014), Jun 2025) | 27.17 h from 50 *English-speaking Indian* speakers. Harder than In-the-Wild. | Research use (project site) | English with Indian accent only. |
| **MLAAD v11** ([arXiv 2401.09512](https://arxiv.org/abs/2401.09512)) | 205 TTS models, 1,153.6 h, 54 languages | CC-BY-NC-4.0 | Bona fide side is M-AILABS (European languages). **Could not verify Indic coverage.** |
| **BanglaFake** (2025) | Bengali TTS fakes ([HF](https://huggingface.co/datasets/sifat1221/banglaFake)) | Check card | Bangladeshi Bengali. |

**Gap we can fill:** no public Indic spoof corpus uses **2025–26 generators** (IndicF5, Chatterbox-hi, Fish S2, Seed-VC/RVC voice conversion) **passed through Indian telephony channels**. A small consented corpus of team voices × 6 generators × 4 channels, with a held-out generator protocol, is a credible differentiator. It is also allowed under the "synthetic/consented" data rule.

---

## 5. Open-source cloning, TTS and VC systems for a consented Indic spoof corpus

| System | Released | Licence (weights) | Indian languages | Cloning / real time | Use in corpus |
|---|---|---|---|---|---|
| **IndicF5** (AI4Bharat) | Mar 2025 | **MIT** (HF gated: accept terms) | 11: as, bn, gu, hi, kn, ml, mr, or, pa, ta, te | Zero-shot from a reference clip. Not streaming. | **Core Indic cloner** ([HF](https://huggingface.co/ai4bharat/IndicF5)) |
| **Indic Parler-TTS** (AI4Bharat) | Oct 2024 | **Apache-2.0** | about 20 Indic languages + English | Description-controlled, named speakers. **Not zero-shot cloning.** | "Generic synthetic Indic voice" class ([HF](https://huggingface.co/ai4bharat/indic-parler-tts)) |
| **Chatterbox Multilingual** (Resemble) | Sep 2025 (V3 in 2026) | **MIT** | **Hindi** among 23 languages, plus a dedicated Hindi single-language model | Zero-shot cloning. **Perth watermark on every output.** | Core cloner; also a watermark experiment ([GitHub](https://github.com/resemble-ai/chatterbox)) |
| **XTTS-v2** (Coqui) | 2023 | **CPML, non-commercial** (Coqui shut down Jan 2024, so no commercial licence is available) | Hindi among 17 | 6 s cloning | Legacy generator (also in IndicSynth) ([HF](https://huggingface.co/coqui/XTTS-v2)) |
| **Fish Audio S2 Pro** | Mar 2026 | Fish Audio Research Licence (non-commercial) | 80+, incl. hi, ta, te, bn, ml, kn, pa, ur | Cloning; RTF 0.195; streaming | Modern LLM-based generator; **good held-out test** ([HF](https://huggingface.co/fishaudio/s2-pro)) |
| **F5-TTS** | Oct 2024 | Code MIT; **weights CC-BY-NC** | en/zh base (IndicF5 is its Indic finetune) | RTF 0.15 | Optional ([arXiv 2410.06885](https://arxiv.org/abs/2410.06885)) |
| **CosyVoice 2 / Fun-CosyVoice 3** | Dec 2024 / Dec 2025 | **Apache-2.0** | 9 languages, **no Hindi** | Bi-streaming, about 150 ms | Cross-lingual or English-accent attacks only |
| **IndexTTS2 / 2.5** (bilibili) | Jun 2025 | Custom bilibili Model Use Licence | zh/en (2.5 "multilingual"; list unverified) | Emotion and duration control | Optional |
| **Higgs Audio v2** (Boson) | Jul 2025 | Code Apache-2.0; model "other" (custom); v3 is research/non-commercial | Unverified for Indic | Cloning | Optional |
| **VibeVoice** (Microsoft) | Aug 2025 | MIT, but **TTS code removed from the repo "for responsible use"**. The model card forbids real-time voice conversion and "live deep-fake" uses and embeds a watermark. | en/zh only | Realtime-0.5B about 300 ms first audio | Avoid (policy) |
| **Qwen3-TTS** | Jan 2026 | Apache-2.0 | 10 languages, no Hindi | Streaming | English only |
| **VoxCPM 1.5** | Dec 2025 | Apache-2.0 | zh/en | RTF 0.17 (RTX 4090) | English only |
| **Veena** (Maya Research) | Jun 2025 | Apache-2.0 | Hindi/English | **4 fixed speakers, no cloning**; claims sub-80 ms on H100 | Generic Hindi synthetic class |
| **Sarvam Bulbul v3** | 2026 | **Commercial API**. Consent-verified cloning for enterprise only. | 11 Indian languages | API | Optional negative class via API; not open weights |
| **OpenVoice V2** (MyShell) | Apr 2024 | **MIT** | Tone-colour converter is language-agnostic; native TTS in 6 non-Indic languages | Fast | VC-style attack ([GitHub](https://github.com/myshell-ai/OpenVoice)) |
| **Seed-VC** | 2024–25 | **GPL-3.0** | **Language-agnostic** voice conversion | **Real time, about 300 ms + 100 ms**, 1–30 s reference | **The key "live scam" attack**: a scammer speaks Hindi, and the voice is converted to the victim's relative ([GitHub](https://github.com/Plachtaa/seed-vc)) |
| **RVC WebUI** (+ w-okada voice-changer) | 2023–26 | MIT | Language-agnostic | Real time after a short per-voice training | Second VC attack ([GitHub](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)) |

**Important for Indian languages:** zero-shot TTS coverage for Indic languages is uneven. **Voice conversion is language-agnostic.** That makes real-time VC (Seed-VC/RVC) the most realistic attack on Hindi, Tamil or other regional calls, and the hardest for content-free detectors. It should be a mandatory held-out test.

**Corpus protocol (consent-first):**
1. Written consent from each team member whose voice is cloned. No public figures, no non-consenting voices.
2. Generate with 4 generators for training (e.g. IndicF5, Chatterbox-hi, XTTS-v2, Indic Parler) and hold out 2 (Fish S2, Seed-VC).
3. Pass every clip, real and fake, through: clean 16 kHz; 8 kHz G.711 μ-law; AMR-NB; Opus narrowband with packet loss; and a **real PSTN or Vapi round-trip recording**.
4. Report EER per generator × channel. Never pool numbers into a single headline "accuracy".
5. Watermark your own synthetic outputs and do not release cloned-voice checkpoints.

---

## 6. Provenance and watermarking

- **AudioSeal** (Meta, Jan 2024; MIT; [arXiv 2401.17264](https://arxiv.org/abs/2401.17264), [HF](https://huggingface.co/facebook/audioseal)). Localised, sample-level watermark detection with a fast single-pass detector. It only helps if the generator embedded it.
- **Perth** (Resemble; MIT; [GitHub](https://github.com/resemble-ai/perth)). Embedded in **every Chatterbox output**. The README claims it survives MP3 compression and editing "while maintaining nearly 100% detection accuracy". However, an attacker running open-source Chatterbox can simply delete the watermark call. VibeVoice also embeds a watermark.
- **AudioMarkBench** (NeurIPS 2024 D&B; [arXiv 2406.06979](https://arxiv.org/abs/2406.06979)) benchmarks removal and forgery attacks and finds current audio watermarks vulnerable to perturbations.
- **C2PA** supports file-embedded manifests for audio (WAV, MP3, M4A; OGG added in spec 2.4) ([spec](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html)). It **does not survive a live PSTN or VoIP call**, because there is no file container and the audio is re-encoded. That makes it irrelevant for real-time call defence. It is useful in our **evidence path**: sign the evidence packet so it is tamper-evident.

**Verdict:** a watermark check is a **positive-only** signal. A hit is strong evidence of synthesis; absence proves nothing. Robustness through 8 kHz telephony is **unverified**. A cheap experiment for the deck: watermark clips with Perth and AudioSeal, pass them through G.711/AMR, and measure detection rate. That shows rigour and gives an honest answer. Use watermarks as a bonus feature, never as the core.

---

## 7. Non-audio defences that work, and what official bodies recommend

| Defence | Evidence / recommendation | Strength vs voice cloning |
|---|---|---|
| **Out-of-band, device-bound confirmation** (in-app push on the bound device, passkey/FIDO) | RBI 2025 Directions: risk-based additional checks; DigiLocker for confirming high-risk transactions. **NIST SP 800-63B-4**: "Biometrics SHALL only be used as part of multi-factor authentication with a physical authenticator" ([NIST](https://pages.nist.gov/800-63-4/sp800-63b.html)). | **Strongest against impersonation of the *customer*** (contact-centre attacks), because the cloned voice cannot approve a push on the customer's phone. **Does not stop APP fraud**, where the real customer approves. |
| **Callback to a verified number** | FTC: "call the person… using a phone number you know is theirs" ([FTC, Apr 2024](https://consumer.ftc.gov/consumer-alerts/2024/04/fighting-back-against-harmful-voice-cloning)). Sanchar Saathi's trusted-contact directory; 1600-series numbers. | Very strong, but users skip it under pressure. The product should **make it one tap**: "Call Rahul (saved contact) now". |
| **Safe words / family passphrase** | FBI IC3 PSA, 3 Dec 2024 ("Create a secret word or phrase with your family") ([IC3](https://www.ic3.gov/PSA/2024/PSA241203)). Starling Bank "Safe Phrases" (Sep 2024). MeitY (Oct 2026). | Cheap and strong if set up beforehand. Weak if the victim is panicking. A product can *prompt* for it at the right moment. |
| **Challenge-response liveness** | PITCH (above): challenges raise machine AUROC to 88.7%. The authors warn adversaries can pre-fabricate responses to public challenges, so randomise. Real-time VC adds about 400 ms, and challenges such as interrupting, whispering, singing, tongue-twisters or tapping the mic stress VC pipelines. | Medium. Useful as an *escalation* step with a human in the loop, never as a sole gate. |
| **Delays / cooling-off** | PIB on FRI: a UPI platform "introduced transaction delays, with alerts and needing user confirmations". | Strong against urgency-driven scams. Has a friction cost, so apply only at high risk. |
| **Red-flag typologies and reporting** | FinCEN Alert FIN-2024-Alert004, 13 Nov 2024: red flags and the SAR key term "FIN-2024-DEEPFAKEFRAUD" ([FinCEN](https://www.fincen.gov/news/news-releases/fincen-issues-alert-fraud-schemes-involving-deepfake-media-targeting-financial)). India: 1930 / NCRP / Chakshu. | Feeds the evidence path. |
| **Retire voiceprint-only authentication** | OpenAI (Mar 2024); AWS Voice ID end-of-support (May 2026); Fed Governor Barr, Apr 2025: "Identity verification standards at banks often use voice detection, which may become vulnerable" ([Fed](https://www.federalreserve.gov/newsevents/speech/barr20250417a.htm)). | Supports positioning: we build the workflow that replaces voiceprints. |

---

## 8. Judgement: framing, competition, risks, concepts, MVP

### 8a. Bounded framing that should score highest
**"Stop the payment, not just the voice."** Narrow the problem to one India-specific, high-loss workflow:

> *A customer is on a live call (cellular or WhatsApp) with someone posing as police, a bank, or a relative in trouble, often with a cloned voice, and opens their bank or UPI app to make an urgent, first-time transfer. We detect this situation with fused weak signals and apply graded, consent-based friction that verifies through channels a cloned voice cannot fake.*

Why this scores well against the rubric:
- **Problem fit (20).** Matches the dominant Indian pattern: Chakshu relative/friend impersonation up 76x in 2025, fake police at 54k reports, plus the Delhi, Hyderabad and Mumbai cases. Elderly and NRI-family users are the target personas.
- **Architecture (20).** Shows fusion of acoustic, call-context (1600, international/OTT, CNAP mismatch, FRI of payee), conversation (Hindi/English ASR keywords and intent) and transaction (new payee, amount, time) signals, with calibrated scores.
- **Differentiation (15).** Explicitly "more than a detector": the detector is one calibrated, uncertainty-aware input. The core is the India telecom-signal fusion plus out-of-band verification, both of which work **even when the detector is fooled**.
- **Feasibility (15).** Every component exists: Vapi, Deepgram, an open-source SSL detector, rules plus a small logistic model, and a mock bank app.
- **Safety (15).** Matches the stated criteria: no auto-block on a single signal, a friction ladder, false-positive handling, human review, adversarial red-teaming with held-out generators and real-time VC, on-device or ephemeral audio, DPDP Act consent.
- **Adoption (10).** Fits RBI Directions §8 (risk-based step-up) and DIP/FRI (already used by 1000+ entities). Ships as a bank-app SDK plus a contact-centre API.

### 8b. What most teams will do, and how to beat them
Likely: (1) fine-tune wav2vec2/AASIST on ASVspoof or In-the-Wild, then show an upload page reading "97% FAKE"; (2) an LLM transcript classifier for scam scripts; (3) maybe a Twilio/Vapi bot. Many will quote the 47% McAfee stat.

How to beat them:
- **Show the honest numbers.** A leave-one-generator-out and telephony-channel EER table on our Indic corpus, including the failure case. Judges reward rigour and the rubric penalises "generic AI detection claims".
- **Demo a real-time voice-conversion attack in Hindi over a real phone line**, and show the *system* still catches it even when the detector score is ambiguous.
- **Graded friction plus a false-positive story.** Run a legitimate-call demo where a real relative calls about a real emergency, and show minimal friction (one-tap callback).
- **Evidence path:** a consented, hashed evidence packet that pre-fills a 1930/NCRP and Chakshu report and goes to the bank's fraud queue.

### 8c. Main risks and mitigations
| Risk | Mitigation |
|---|---|
| **Detector brittleness makes the demo unconvincing** (Deepfake-Eval-2024: -48% AUC; DFE EER about 33% zero-shot; narrowband hurts) | The decision never hinges on the detector. Show calibrated probabilities with an "uncertain" band. Fine-tune on our own telephony-channel corpus. Rehearse the demo on the actual phone path. Keep a pre-recorded fallback. |
| **False positives on legitimate users** (accents, elderly speakers, noisy lines, speech impairments, code-mixing) | Audio alone can raise risk only to Amber (a nudge), never Red. Measure FPR on real consented team calls across languages. Add an opt-in "trusted caller" list and feedback to the bank queue. Run fairness slices by language and gender. |
| **Privacy / DPDP** (call audio is sensitive; recording laws) | On-device or ephemeral processing. Only features and scores leave the device, and only with explicit consent. No raw-audio retention by default. The evidence packet is user-initiated and has a retention limit. |
| **Adversarial adaptation** | Held-out generators and VC in evaluation. Randomised challenge prompts. Don't expose scores to the caller. Periodic retraining. Rely on non-audio controls such as callback and device binding. |
| **Licences** (XTTS CPML, F5 / AntiDeepfake / IndicSynth / MLAAD / Fish = non-commercial; Seed-VC = GPL) | Fine for a hackathon. Disclose in the deck and name a production path (e.g. train on Apache/MIT generators plus our own data). |
| **Ethics of cloning** | Team voices only, with written consent. Watermark outputs. No release of cloned models. Name these points in the Responsible AI slide. |
| **Access to FRI / DIP / CNAP** | Mock these via an adapter interface. Say explicitly that production access is limited to regulated entities. |

### 8d. Product concepts (48h-demonstrable)

**Concept A (recommended): "Pause-and-Verify" on-call payment guard (customer side, bank-app SDK)**

**Trigger:** the user starts a high-risk action (first-time payee, amount above their usual pattern, beneficiary addition or limit change) **while a call is active**. Android exposes call state, and a VoIP/OTT call is visible through audio mode. Google's screen-share alert pilot with Navi, Paytm and GPay shows call-aware alerts are deployable in India.

**Signals, each producing a calibrated score plus a reason:**
1. **Call context.** Unknown vs saved contact; 10-digit vs **1600**; international/OTT; CNAP name vs claimed identity; caller number FRI/MNRL (mocked DIP).
2. **Conversation** (with consent, on-device or streaming). Deepgram Nova-3/Flux multilingual (Hindi + English code-switching) detects scam-script cues: police/CBI/custody, "don't tell anyone", urgency, payment instructions, "send to this UPI ID".
3. **Acoustic.** Synthetic-speech score from the fine-tuned SSL detector on 2–4 s windows, plus segment-level change detection for "partial" calls where a human and a clone hand off. Includes an *uncertain* band.
4. **Transaction.** New payee, payee FRI, amount vs history, time of day.

**Friction ladder** (never block on audio alone):
- **Green:** proceed.
- **Amber:** interstitial ("You're on a call with an unknown number. Genuine police never ask for money on calls."), one-tap **"Call [saved contact] now"**, family safe-word prompt.
- **Red** (≥2 independent strong signals): 30-minute cooling-off hold plus out-of-band confirmation (device-bound in-app or DigiLocker-style). Optional opt-in *trusted-contact* notification for senior users. Bank analyst review with appeal.

**Evidence path:** a user-consented packet containing signal reasons, model versions, timestamps, a transcript excerpt and a hash of the audio snippet. It is signed (C2PA-style or a simple Ed25519 signature) and pre-fills 1930/NCRP and Chakshu reports and the bank's fraud ticket.

**48h demo:**
- A Vapi assistant scripted as "Inspector Sharma, Delhi Police", plus a Seed-VC real-time clone of a consenting teammate as the "son", calls a teammate's phone in Hindi.
- The teammate opens the mock UPI app to pay Rs 50,000 to a new payee, and the dashboard lights up.
- Second run: a benign call from the real teammate shows Green or a light Amber with a one-tap callback.
- Bank-analyst console shows the review queue and feedback buttons.

**Concept B (secondary, or a module of A): "Contact-Centre Shield" for bank IVR/agents (bank side)**
- Inbound calls requesting high-risk servicing (unblock card, raise limit, update email/mobile, add beneficiary, unfreeze account) get a streaming synthetic-voice and replay score, caller-ID context (spoof/international flags, number history, FRI), and an agent-assist panel.
- Policy: **voice is never an authenticator**. Any high-risk change triggers device-bound in-app approval on the registered device, or a callback to the registered number. A randomised challenge-response is used only as an escalation, with the human agent deciding.
- Ties into the Amazon story: Amazon Connect Voice ID has been retired, so this is the replacement pattern. Host the detector on AWS GPU (SageMaker/EC2); optionally use Amazon Bedrock with Guardrails for transcript intent. Vapi can stand in for the IVR in the demo.

**Recommendation:** pitch **A as the product** (stronger India problem fit and demo) and **B as the bank-side extension** in the scale/adoption slide. Both share one risk engine.

### 8e. 48-hour build plan (uses the team's GPUs, Vapi and Deepgram)
- **Before Oct 24, if allowed (check event rules on pre-built assets; otherwise do it in the first 8 hours):** consent forms; corpus generation on H100/A100 (6 generators × team voices × 4 channels, about 5–10 h of audio); fine-tune XLS-R-300M+AASIST or MMS-300M-AntiDeepfake with RawBoost and codec augmentation; leave-one-generator-out evaluation; temperature/Platt calibration.
- **Hours 0–12:** streaming pipeline. Phone call → Vapi `monitor.listenUrl` WebSocket (live call audio) ([Vapi docs](https://docs.vapi.ai/calls/call-features)) → GPU detector service (sliding windows) and Deepgram streaming ASR (`language=multi`, Nova-3, or `flux-general-multi` with Hindi) ([Deepgram](https://developers.deepgram.com/docs/multilingual-code-switching)) → risk engine.
- **Hours 12–30:** risk engine (rules plus a logistic model with per-signal reason codes), mock DIP/FRI and 1600/CNAP adapters, mock bank/UPI app with the friction ladder, analyst console.
- **Hours 30–42:** evidence packet (hash, sign, PDF/JSON), red-team runs with held-out Seed-VC and Fish S2, FPR test on real benign calls, latency measurement (time-to-first-alert).
- **Hours 42–48:** freeze; rehearse the scam and benign demo runs; prepare a recorded fallback.
- **Metrics to show:** per-generator × channel EER; time-to-first-alert in seconds; benign-call friction rate; end-to-end catch rate on the scripted scenarios with the detector on vs off (shows the fusion carries the decision).

---

## 9. Unverified or open items (do not state as fact)
- No **Indian company CEO/CFO voice-clone fraud with confirmed losses** found. Only the Sunil Mittal attempt, which failed. International cases: Arup Hong Kong $25M (Feb 2024, [CNN](https://www.cnn.com/2024/02/04/asia/deepfake-cfo-scam-hong-kong-intl-hnk)), UK energy firm €220k (2019, WSJ), WPP attempt (May 2024, Guardian). An Instagram post claims "a Hyderabad company lost Rs 87 lakh" but I could not source it.
- The share of digital-arrest cases that use cloned voices is not quantified anywhere I found.
- Actual 1600-series compliance after the 2026 deadlines, and whether nationwide CNAP rollout is complete.
- Whether ICICI or Citi India voice biometrics are still in production in 2026. Which Indian banks allow high-risk changes purely by phone.
- MLAAD's Indic-language coverage. IndexTTS2.5 language list. Higgs Audio v2 exact licence terms.
- Robustness of Perth and AudioSeal watermarks through 8 kHz G.711/AMR (testable by the team).
- My latency estimate for XLS-R inference: measure it.
- All vendor accuracy claims (Resemble 94–99.47%, Vastav 99%, Pindrop growth rates) are self-reported.

## 10. Further sources consulted
- McAfee blog on AI voice scams: https://www.mcafee.com/blogs/privacy-identity-protection/artificial-imposters-cybercriminals-turn-to-ai-voice-cloning-for-a-new-breed-of-scam/
- Starling Safe Phrases: https://www.starlingbank.com/safe-phrases/
- FinCEN alert PDF: https://www.fincen.gov/system/files/shared/FinCEN-Alert-DeepFakes-Alert508FINAL.pdf
- Pindrop audio deepfake use case: https://www.pindrop.com/use-cases/audio-deepfake-detection
- Reality Defender call centres: https://www.realitydefender.com/insights/real-time-deepfake-detection-in-call-centers
- pi-labs: https://www.pi-labs.ai/ ; Kroop AI: https://kroop.ai/ ; Contrails: https://www.contrails.ai/ ; Vastav: https://vastav.ekoahamdutivnasti.com/
- The Atlantic on Indian election deepfakes and Contrails (Jun 2024): https://www.theatlantic.com/technology/archive/2024/06/india-election-deepfakes-generative-ai/678597/
- PIB I4C–RBIH MuleHunter MoU: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260277
- VibeVoice repo notice: https://github.com/microsoft/VibeVoice ; model card: https://huggingface.co/microsoft/VibeVoice-1.5B
- Fish Speech paper: https://arxiv.org/abs/2411.01156 ; CosyVoice 3: https://arxiv.org/abs/2505.17589 ; IndexTTS2: https://arxiv.org/abs/2506.21619
- Sarvam TTS: https://www.sarvam.ai/text-to-speech ; Veena: https://huggingface.co/maya-research/Veena
- Seed-VC HF weights (GPL-3.0): https://huggingface.co/Plachta/Seed-VC
- Deepgram models: https://developers.deepgram.com/docs/models-languages-overview ; Vapi WebSocket transport: https://docs.vapi.ai/calls/websocket-transport
