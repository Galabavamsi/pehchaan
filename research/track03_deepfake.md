# Track 03: Deepfake Detection for Financial Communications (research brief)

Prepared 2026-10-05 for the RAKSHAM Round 1 submission (due 2026-10-07).
Scope: India incidents, V-CIP, regulation/provenance, detection limits, reporting paths, competitors, and a recommendation.
Convention: **[V]** = checked against a primary or near-primary source during this research. **[S]** = secondary source (news, vendor, or blog), not independently confirmed. **[U]** = could not verify; do not put on a slide without re-checking.

---

## Key numbers with citations

| # | Fact / number | Source (publisher, date) | Status |
|---|---|---|---|
| 1 | Indians lost **Rs 22,845.73 crore** to cyber fraud in 2024 (Rs 7,465.18 cr in 2023); **36,37,288** financial-fraud incidents on NCRP + CFCFRMS in 2024 | MHA written reply in Lok Sabha, reported by New Indian Express, 22 Jul 2025, https://www.newindianexpress.com/india/2025/Jul/22/indian-citizens-lost-over-rs-22845-crore-to-online-fraudsters-in-2024-mha-in-lok-sabha | [V] (via press report of the parliamentary reply) |
| 2 | 2025: **Rs 22,495 crore** lost; complaints **28.15 lakh (+24%)**; **76% of money lost came from investment fraud** (Ponzi, fake stock-trading, crypto) | ThePrint, 21 Feb 2026 (MHA data), https://theprint.in/india/cybercrime-saw-24-spike-in-2025-indians-lost-rs-22495-crore-mainly-in-investment-scams/2859930/ | [S] (secondary, but it reports MHA data) |
| 3 | 2021–2025 total: >65.89 lakh financial-fraud complaints, >Rs 55,050 cr reported; Rs 11,158 cr "saved" by 30 Jun 2026 | PIB, MHA Lok Sabha reply (2026), https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287039 | [V] (exact release date not captured) |
| 4 | Jan–Apr 2024 (I4C CEO): Rs 1,420.48 cr lost to "trading scams", Rs 222.58 cr to "investment scams", Rs 120.30 cr to digital arrest. Note: TOI gives the labels the other way round (Rs 1,420 cr = 62,587 investment scams) | Indian Express, May 2024, https://indianexpress.com/article/india/indians-lost-rs-120-crore-in-digital-arrest-frauds-in-january-april-2024-9641952/ ; TOI, https://timesofindia.indiatimes.com/india/46-of-cyber-fraud-in-india-stems-from-southeast-asia/articleshow/110374898.cms | [S]. Labels conflict between the two outlets |
| 5 | Digital arrest: 2,41,537 cases and Rs 3,012 cr in losses, 2022–2025 | ORF, 18 Jul 2026 (citing ThePrint/MHA), https://www.orfonline.org/expert-speak/digital-arrest-scams-and-the-limits-of-domestic-enforcement | [S] |
| 6 | **RBI** press release cautioning the public about deepfake videos of its top management giving financial advice (PR 2024-2025/1537) | RBI, **19 Nov 2024**, https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=59135 | [V] |
| 7 | **NSE** warned about deepfakes of MD & CEO Ashishkumar Chauhan giving stock tips. ICICI Prudential AMC issued a similar notice on 22 Jan 2024 | Reuters, **10 Apr 2024**, https://www.reuters.com/technology/cybersecurity/beware-deepfake-ceo-recommending-stocks-says-indias-national-stock-exchange-2024-04-10/ ; NSE PR, 10 Jun 2024, https://nsearchives.nseindia.com/web/sites/default/files/2024-07/PR_cc_10062024.pdf | [V] |
| 8 | **BSE** deepfakes of MD & CEO Sundararaman Ramamurthy. Video promised "Rs 8 million by 2027" and pushed viewers to a WhatsApp channel. BSE then warned that the same video had "resurfaced" | BSE PRs: https://beta.bseindia.com/Downloads/MediaRelease/PR11012026_20261101_20261101.pdf (file dated 11-01-2026) ; https://beta.bseindia.com/Downloads/MediaRelease/PR09022026_20260902.pdf (file dated 09-02-2026). First BSE warning Apr 2024: https://oecd.ai/en/incidents/2024-04-18-3cf0 | [V] (dates taken from file names) |
| 9 | **PIB Fact Check**: deepfake of FM Nirmala Sitharaman promoting an investment platform | PIB Fact Check on X, 11 Mar 2026, https://x.com/PIBFactCheck/status/2031670993748705756 ; Mint, https://www.livemint.com/money/personal-finance/sitharaman-finance-minister-pib-fact-check-clarify-fake-ai-video-endorse-warns-against-fraudulent-online-investment-scam-11778145179400.html | [V] |
| 10 | **SEBI** cautioned about fake notices on forged SEBI letterhead that demand "STT" payments (PR 15/2026) | SEBI, **26 Feb 2026**, https://www.sebi.gov.in/media-and-notifications/press-releases/feb-2026/caution-to-the-public-regarding-fake-stt-notices_100031.html | [V] |
| 11 | **Arup** (Hong Kong): HK$200m (~US$25.6m) sent in **15 transfers to 5 accounts** after a multi-person video call in which every participant was a deepfake | CNN, 4 Feb 2024, https://www.cnn.com/2024/02/04/asia/deepfake-cfo-scam-hong-kong-intl-hnk ; Guardian (Arup confirms), 17 May 2024, https://www.theguardian.com/technology/article/2024/may/17/uk-engineering-arup-deepfake-scam-hong-kong-ai-video | [V] |
| 12 | **I4C "Boss Scam" advisory** (NCTAU): fake "RBI compliance" ZIP files install malware that hijacks executives' WhatsApp Web sessions. Finance departments are flagged as especially vulnerable | NDTV, 22 Jun 2026, https://www.ndtv.com/india-news/i4c-cyber-scams-cyber-crime-centre-warns-of-boss-scam-targeting-companies-11671896 ; ANI on X, https://x.com/ANI/status/2069039086384660907 | [V] (via press) |
| 13 | **Deepfake-Eval-2024**: on in-the-wild 2024 deepfakes, open-source detector AUC drops by **50% (video), 48% (audio), 45% (image)** compared with older benchmarks. Best off-the-shelf open-source AUC was **0.58**. Best commercial accuracy: video 0.78, audio 0.89, image 0.82. Human forensic analysts are estimated at ≥90% | Chandra et al., arXiv 2503.02857, 4 Mar 2025 (rev. May 2026), https://arxiv.org/abs/2503.02857 | [V] |
| 14 | Experts disagree with each other: in one DAU case, Northwestern's GODDS ran **22 video models (13 said fake, 9 said real)** and **70 audio models (35 fake, 35 real)**. Hiya returned 53% on one fake and 97% on another | DAU report, 27 Aug 2026, https://dau.trustedinfoalliance.in/blog/copycat-financial-scam-videos-of-arvind-kejriwal-shah-rukh-khan-use-a-i-voice | [V] |
| 15 | A state-of-the-art SSL-AASIST speech detector has **0.21% EER in-domain**. With its threshold transferred to In-the-Wild data it reaches **39.5% HTER and rejects 78.7% of genuine speech** | arXiv 2606.21584, Jun 2026, https://arxiv.org/abs/2606.21584 | [V] (abstract) |
| 16 | IT (Intermediary Guidelines) **Amendment Rules 2026** on synthetically generated information (SGI): notified **10 Feb 2026**, in force **20 Feb 2026**. Requires labels plus "permanent metadata ... unique identifier", declaration and technical verification by significant social media intermediaries (SSMIs), and **3-hour takedown** | MeitY consolidated rules PDF, https://www.meity.gov.in/static/uploads/2026/02/550681ab908f8afb135b0ad42816a1c9.pdf ; Lexology, https://www.lexology.com/library/detail.aspx?g=adb2714c-1188-43e3-b62b-eb6649727f6e ; JD Supra, https://www.jdsupra.com/legalnews/india-introduces-mandatory-labelling-8102704/ | [V] |
| 17 | iProov: **native virtual-camera attacks +2,665%** and **face-swap attacks +300%** (2024 vs 2023). 2026 report: **iOS injection attacks +741% for the year** (+1,151% in H2 2025) | iProov TIR 2025, https://www.iproov.com/press/annual-identity-verification-threat-intelligence-report ; TIR 2026, https://www.iproov.com/press/iproov-issues-annual-threat-intelligence-report | [S] (vendor) |
| 18 | Entrust/Onfido: **one deepfake attempt every 5 minutes in 2024**; digital document forgeries **+244%**. In 2025, deepfakes were **1 in 5 biometric fraud attempts**, injection attacks rose 40% and deepfake selfies rose 58% | Entrust, Nov 2024, https://www.entrust.com/company/newsroom/deepfake-attacks-strike-every-five-minutes-amid-244-surge-in-digital-document-forgeries ; 2026 report, https://www.entrust.com/company/newsroom/deepfakes-social-engineering-and-injection-attacks-on-the-rise | [S] (vendor) |
| 19 | SEBI register sizes: **1,050 Investment Advisers** and **2,271 Research Analysts**. Only these may legally give paid investment advice or research | SEBI Recognised Intermediaries page, data as of 4 Oct 2026, https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognised=yes | [V] |
| 20 | **RBI Alert List** of unauthorised forex trading platforms: ~95 entries, updated **19 Nov 2025** | RBI, https://rbi.org.in/scripts/bs_viewcontent.aspx?Id=4235 | [V] |
| 21 | **SEBI "@valid" UPI handles + "SEBI Check"** to verify an intermediary's UPI ID, QR code, or bank account. Effective **1 Oct 2025** | SEBI PR, Jun 2025, https://www.sebi.gov.in/media-and-notifications/press-releases/jun-2025/sebi-to-introduce-validated-upi-handles-and-sebi-check-for-secured-payments-by-investors-to-enhance-investor-protection-and-combat-fraud_94539.html | [V] |
| 22 | **TRAI 1600-series** mandatory for service and transactional calls from RBI/SEBI/PFRDA-regulated entities. Commercial banks by 1 Jan 2026; stockbrokers by 15 Mar 2026 | TRAI Direction, 19 Nov 2025, https://www.trai.gov.in/sites/default/files/2025-11/Direction_19112025.pdf ; phase dates per https://www.tatatelebusiness.com/marketing-solutions/1600-phone-number-series/ | [V]/[S] |
| 23 | Google: **>20 billion** pieces of AI content watermarked with SynthID. The Gemini check only recognises content from Google's own AI | Google blog, 20 Nov 2025, https://blog.google/innovation-and-ai/products/ai-image-verification-gemini-app/ ; Gemini help, https://support.google.com/gemini/answer/16722517 | [V] |
| 24 | Meta celeb-bait facial recognition protects **~500,000 public figures**. Celeb-bait ad reports fell 22% in H1 2025. Rolled out in UK, EU, and South Korea; **no India rollout announced** in the post | Meta newsroom, 21 Oct 2024 (updated 28 Sep 2025), https://about.fb.com/news/2024/10/testing-combat-scams-restore-compromised-accounts/ | [V] |
| 25 | Meta requires **SEBI verification for securities/investment ads** aimed at Indian users from **31 Jul 2025**. Deepfake scam ads still appeared on Facebook in 2026 (DAU reports) | PPC Land, https://ppc.land/meta-mandates-sebi-verification-for-india-securities-ads/ ; DAU reports, https://dau.trustedinfoalliance.in/tag/financial-scam | [S] |

---

## 1. India incidents (2023–2026)

### 1a. Deepfakes of regulators, ministers, exchange heads, and business leaders used for investment scams
- **RBI (Nov 2024).** RBI warned that deepfake videos of its Governor and top management were circulating with "advice" to invest in schemes. RBI stated it does not give such advice. PR dated 19 Nov 2024: https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=59135. Coverage: Mint, https://www.livemint.com/industry/banking/rbi-cautions-investors-says-deepfake-videos-of-governor-shaktikanta-das-circulating-on-social-media-11732007435377.html. PIB Fact Check has also debunked posts about Governor Sanjay Malhotra (e.g. https://x.com/PIBFactCheck/status/2090734995396808809; that post is a fake "DD interview" claim, not necessarily a video deepfake).
- **NSE (Apr and Jun 2024).** Deepfakes of the NSE CEO's face and voice gave stock tips (Reuters, 10 Apr 2024; NSE PR, 10 Jun 2024). The NSE CEO described a personal deepfake experience at IFTA 2025 (YouTube).
- **BSE (Apr 2024; Jan and Feb 2026).** Repeated deepfakes of the MD & CEO. One promised "Rs 8 million by 2027" and asked viewers to join a WhatsApp channel. BSE said such videos "may continue to resurface in different forms" (BSE PRs above). BSE has also warned about fake notices on forged SEBI letterhead (https://docs.publicnow.com/viewDoc.aspx?filename=37191%5CEXT%5CAAFDC14222E17D067EDB432BCB05ECA4DF519B13_B3369739797BDC6DB965810CD1470F0081E2770D.PDF).
- **Finance Minister (2024–2026).** Several PIB Fact Check debunks: 11 Mar 2026 (FM endorsing an investment scheme), plus PM+FM Facebook ad deepfakes (https://www.facebook.com/pibfactcheck/videos/-dont-fall-for-easy-money-scams-onlinea-facebook-advertisement-is-circulating-an/1061129753172441/). DAU debunked FM investment-platform videos on 20 Aug 2025, 22 Sep 2025, and 12 Dec 2025 (https://dau.trustedinfoalliance.in/tag/financial-scam).
- **Narayana Murthy / Sudha Murty / Mukesh Ambani.**
  - Murthy publicly flagged deepfakes endorsing trading apps (The Hindu, Dec 2023, https://www.thehindu.com/news/national/narayana-murthy-warns-about-deepfake-video-of-him-endorsing-trading-apps/article67641003.ece).
  - Mumbai Ayurvedic doctor lost about Rs 7 lakh after a deepfake of Ambani (Jun 2024, https://oecd.ai/en/incidents/2024-06-20-b99d). A retired Mumbai professional was also a victim (TOI, Jul 2024, https://timesofindia.indiatimes.com/city/mumbai/retired-professional-falls-victim-to-deepfake-scam-featuring-mukesh-ambani/articleshow/111667464.cms).
  - Bengaluru: Asok Kumar (63) lost **Rs 19 lakh** to "FX Road" after Facebook deepfakes of Murthy and Ambani. Veena (57) lost Rs 67.1 lakh across a deepfake trading scam plus a separate task scam. The headline "Rs 87 lakh" combines both (Indian Express, 5 Nov 2024, https://indianexpress.com/article/cities/bangalore/deepfake-videos-narayana-murthy-mukesh-ambani-bengaluru-trading-scam-9654607/).
  - A 79-year-old Bengaluru woman lost **Rs 35 lakh** over 8 months after a Murthy deepfake. She was then threatened with a fake money-laundering case (TOI, 27 Jun 2025, via AIID #1240, https://incidentdatabase.ai/cite/1240/).
  - Sudha Murty deepfake endorsing an investment: News18 segment (YouTube, https://www.youtube.com/watch?v=Xu5TfiUNyRA) [S].
- **2025–2026 DAU pattern (important for design).** Most debunked financial-scam videos are **real footage with a cloned voice and lip-sync**, not full synthesis. DAU repeatedly finds "**copycat**" scripts: the *same audio transcript* reused across different celebrities (Kejriwal and Shah Rukh Khan, Aug 2026; Gadkari and Sardesai, Sep 2025; Manmohan Singh). The pitch template also repeats: "Investment Rs 22,000 one-time", "Monthly income Rs 25,50,000", "Official link below". DAU's decisive evidence is usually a **reverse image search that finds the original source video** (e.g., an AAP YouTube upload from 27 Apr 2026, or a 2017 Film Companion interview). Detector scores were inconsistent. Source: https://dau.trustedinfoalliance.in/blog/copycat-financial-scam-videos-of-arvind-kejriwal-shah-rukh-khan-use-a-i-voice (27 Aug 2026).

### 1b. Scale of losses
See table rows 1–5. Investment fraud is the largest loss category: 76% of 2025 losses. Deepfake endorsements are one acquisition channel (Facebook/Instagram ads, then a WhatsApp/Telegram group, then a fake trading app). **No official figure isolates "deepfake-enabled" losses [U].** Do not invent one. Frame deepfakes as a trust-amplifier at the top of the investment-scam funnel.

### 1c. Deepfake CEO/CFO fraud
- **Arup, Hong Kong (Jan 2024).** HK$200m (~US$25.6m) in 15 transfers after a multi-person deepfake video call (CNN, Guardian; see table row 11). HK police also reported deepfakes used against facial recognition on ID-card loan applications "on at least 20 occasions" (CNN).
- **WPP.** An attempt on the CEO used a fake WhatsApp account, a voice clone, and YouTube footage in a Teams-style meeting (Guardian, 10 May 2024, https://www.theguardian.com/technology/article/2024/may/10/ceo-wpp-deepfake-scam).
- **India.** I found **no publicly confirmed Indian Arup-style deepfake video-call case [U]**. Indian corporate cases are mostly "Boss scams" that use WhatsApp display-picture impersonation:
  - Hyderabad CEO impersonated, Rs 1.20 cr (Mar 2026, https://www.facebook.com/theetemaaddaily/videos/120-crore-lost-hyderabad-ceo-impersonated-in-massive-whatsapp-frauda-ceo-of-a-co/1810758919603227/) [S]
  - Pune/Goa accountant, Rs 2 cr by RTGS (Sep 2026) [S]
  - Chairman's DP used (ETV Bharat, 7 Jul 2026, https://www.etvbharat.com/en/state/cyber-fraud-of-crores-by-posing-as-company-chairman-with-photo-as-whatsapp-dp-accused-arrested-enn26070702368) [S]
  - Mumbai DGM, Rs 10 cr (Jun 2026; only seen on an Instagram reel) [U]
- The I4C NCTAU advisory of 22 Jun 2026 notes that malware can hijack the **genuine** executive's WhatsApp Web session. Sender identity then proves nothing. The advisory recommends confirming by voice or face-to-face, which voice and video deepfakes are built to defeat. That gap is relevant to a corporate concept.

### 1d. Forged regulator/court letters and "digital arrest"
- SEBI fake STT notices (PR 15/2026, 26 Feb 2026). SEBI also flagged misuse of its logo, seal, and officials' names (Moneylife, https://www.moneylife.in/article/sebi-warns-about-forged-notices-misuse-of-its-letterhead-and-official-identity/77331.html; TOI, https://timesofindia.indiatimes.com/business/india-business/sebi-warns-investors-about-fake-stt-notices-and-fraudsters-posing-as-fund-managers/articleshow/128821521.cms).
- Digital arrest uses video calls with fake police/CBI uniforms and office sets, plus forged court orders. The Supreme Court took suo motu cognisance: order of 17 Oct 2025 (https://api.sci.gov.in/supremecourt/2025/59769/59769_2025_2_7_65003_Order_17-Oct-2025.pdf) and order of 1 Dec 2025 making CBI the lead agency (https://indiankanoon.org/doc/67470969/). Trigger: a senior-citizen couple lost Rs 1.05 cr to impersonated CBI/ED/judicial officers.
- I4C/MHA blocked 83,668 WhatsApp accounts and 3,962 Skype IDs linked to digital arrest (cited in ORF, 18 Jul 2026) [S]. Mumbai 86-year-old lost Rs 20.30 cr to a digital-arrest scam (DD News, https://ddnews.gov.in/en/mule-accounts-become-key-conduit-for-cyber-fraud-agencies-deploy-ai-tools-to-curb-misuse/) [S].
- Note: digital arrest mostly uses *real* people in costume on live calls, not deepfakes. The forged *documents* (SC orders, RBI/SEBI letters, warrants) are the manipulated artefacts. Forged-document checks (letterhead, reference number, signatory, official-domain verification) fit this track.

---

## 2. Video-KYC (RBI V-CIP) and deepfake injection

### RBI rules
- KYC Master Direction 2016, as amended (https://www.rbi.org.in/CommonPerson/english/scripts/notification.aspx?id=2607):
  - V-CIP is a "seamless, secure, live, informed-consent based audio-visual interaction".
  - Recordings must carry live GPS geo-tags and timestamps.
  - "The application shall have components with face liveness / spoof detection as well as face matching technology with high degree of accuracy ... Appropriate AI technology can be used".
  - V-CIP must be run by specially trained officials who can "carry out liveness check and detect any other fraudulent manipulation".
  - Questions must be varied to rule out pre-recorded video (per HyperVerge's summary).
  - V-CIP is treated on par with face-to-face CIP.
- On **28 Nov 2025** RBI consolidated its instructions into entity-specific Master Directions, e.g. "RBI (Commercial Banks – KYC) Directions, 2025" (Signzy, https://www.signzy.com/blogs/RBI-KYC-Master-Directions-2025-key-changes ; Mondaq). I did not re-read the 2025 V-CIP clauses. The core requirements appear to carry over **[S]**.
- HyperVerge says the Direction requires a forged identity detected through V-CIP to be reported as a cyber event, plus regular infrastructure upgrades (https://hyperverge.co/blog/rbi-video-kyc-deepfake-guidelines/) [S, vendor blog].
- **IBA guidance on deepfakes in V-CIP: none found [U].**
- RBIH's **MuleHunter.AI** is the RBI-side mule-account answer. Announced 6 Dec 2024; about 28–30 banks integrated (ETBFSI, 2026, https://bfsi.economictimes.indiatimes.com/articles/rbih-promotes-mulehunterai-for-combatting-cyber-fraud-in-banking/131185297). An I4C–RBIH MoU links the Suspect Registry to it (PIB, https://www.pib.gov.in/PressReleasePage.aspx?PRID=2260277).

### Documented injection / face-swap KYC attacks
- **Global (vendor data, [S]).**
  - iProov: virtual camera +2,665% and face swap +300% (2024). Earlier: face swap +704% and emulators +353% (H2 vs H1 2023, https://www.iproov.com/press/new-threat-intelligence-report-exposes-impact-generative-ai-remote-identity-verification). 2026: iOS injection +741%.
  - Entrust/Onfido: one deepfake every 5 minutes (2024); deepfakes 1 in 5 biometric fraud attempts (2025).
  - Sumsub 2025–26: identity-fraud rate 2.2%; "sophisticated" fraud rose from 10% to 28% of attempts; deepfakes are 11% of first-party schemes (https://sumsub.com/newsroom/sumsubs-annual-report-fraud-shifts-to-complex-multi-step-schemes-in-2025-agentic-ai-scams-poised-to-surge-in-2026/). APAC deepfakes rose 1,530% from 2022 to 2023 (Sumsub 2023 via PRNewswire, https://www.prnewswire.com/apac/news-releases/apac-deepfake-incidents-surge-1530-in-the-past-year-amidst-evolving-global-fraud-landscape-301999070.html).
- **Bank cases.**
  - ABN AMRO: one man opened 46 accounts with deepfaked passport-style faces.
  - Hong Kong, Apr 2025: 8 arrested; 21 stolen IDs used for 44 applications, ~30 successful.
  - Both via iProov blog, 2026, https://www.iproov.com/blog/deepfake-bank-account-kyc-account-fraud-abn-amro [S].
- **India.** Ahmedabad Cyber Crime arrested 4 (Apr 2026). They allegedly made deepfake videos from a businessman's photo (reportedly with Gemini/Meta AI tools) to pass Aadhaar facial authentication. They then changed his Aadhaar-linked mobile, accessed DigiLocker/e-KYC, opened bank accounts, and applied for loans (AIID #1472, https://incidentdatabase.ai/cite/1472/ ; OECD, https://oecd.ai/en/incidents/2026-04-29-b590). This is the clearest Indian evidence of deepfakes beating face authentication. It was Aadhaar face-auth, **not confirmed as a bank V-CIP session**.
- **Counter-evidence on Indian mule supply.** Most Indian mule accounts are opened with *real* KYC documents of recruited, rented, or complicit holders, sometimes with bank-staff collusion. Examples: Cyberabad arrested 7 bank officials for bypassing KYC (30 Apr 2026, Cyberabad Police FB); CBI Operation Chakra-V (26 Jun 2025, https://cbi.gov.in/press-detail/NzA4NA==); CyberPeace on branch-opened mule accounts. **No public evidence that V-CIP deepfake injection is a major Indian mule pipeline today [U].**

### Fit with track wording: a stretch, so keep it as an extension
- **For:** a V-CIP session is literally an audio-visual communication between a customer and a bank, and the brief says "people *and institutions*".
- **Against:**
  1. The organiser cue stresses "explanation for non-technical reviewers" and a "verification or **reporting** path". That reads as content arriving at people (messages, videos, letters, calls), not identity proofing.
  2. Injection defence is mostly a capture-integrity / SDK problem (virtual-camera and emulator detection, device attestation). Strong incumbents already sell it: HyperVerge, IDfy, Signzy, iProov.
  3. A 48h demo needs a fake bank V-CIP flow plus attacks on consented team faces. It is feasible but looks like a liveness demo.
  4. India evidence for V-CIP specifically is thin.
- **Recommendation:** mention it as an extension ("the same evidence-fusion engine scores V-CIP sessions for injection signals"), not as the core.

---

## 3. Regulatory and provenance landscape

- **MeitY advisories.** Dec 2023 and Mar 2024 advisories (eNo.2(4)/2023-CyberLaws-3, https://www.meity.gov.in/static/uploads/2024/02/9f6e99572739a3024c9cdaec53a0a0ef.pdf) "advised" labelling and permanent unique metadata for synthetic content.
- **IT Amendment Rules 2026** (binding; notified 10 Feb 2026, in force 20 Feb 2026). Key provisions:
  - Rule 2(1)(wa) defines SGI.
  - Rule 3(3): intermediaries offering SGI tools must block unlawful SGI. This explicitly covers SGI that "falsely depicts ... a natural person ... identity, voice, conduct, action, statement" and "false document or false electronic record". Lawful SGI needs a prominent label or audio prefix plus "permanent metadata ... including a unique identifier", and label/metadata removal must not be enabled.
  - Rule 4(1A): SSMIs must collect a user declaration, verify it with technical measures, and label.
  - Takedown within **3 hours** of actual knowledge (down from 36h).
  - MeitY FAQ: https://www.meity.gov.in/static/uploads/2025/10/065b6deb585441b5ccdf8be42502a49c.pdf
  - Critique (WITNESS, https://www.witness.org/indias-synthetic-media-rules-build-enforcement-on-the-wrong-foundation/): provenance must be interoperable and rights-respecting, and automated verification is fragile.
  - *Our inference:* WhatsApp is end-to-end encrypted, so the platform cannot inspect forwarded media. On WhatsApp, verification falls to the recipient. That is the gap a user-side verifier fills.
- **CERT-In** advisory CIAD-2024-0060, "Deepfakes – Threats and Countermeasures", 27 Nov 2024 (https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES02&VLCODE=CIAD-2024-0060).
- **C2PA / Content Credentials adoption.**
  - Pixel 10 (Aug 2025) is the first phone to sign *every* camera photo by default, with hardware-backed keys (Google security blog, Sep 2025, https://security.googleblog.com/2025/09/pixel-android-trusted-images-c2pa-content-credentials.html).
  - Samsung Galaxy S25/S26 add credentials only to **AI-edited** images.
  - iPhone has **no C2PA**. Lumethic, a vendor blog (Sep 2026, https://www.lumethic.com/en/articles/smartphones-c2pa-content-credentials), says the iPhone 18 Pro ships an Apple-only, opt-in "Reference Image" mode instead [S]. Vivo X300 Pro is also reported [S].
  - Platforms mostly strip credentials; adoption "in the wild" is tiny (Tim Bray, 18 Sep 2025, https://www.tbray.org/ongoing/When/202x/2025/09/18/C2PA-Investigations).
  - C2PA's answer is "durable" credentials via watermark or fingerprint soft-binding (https://c2pa.org/faqs/).
- **WhatsApp metadata stripping.** In photo mode WhatsApp strips EXIF, XMP, and C2PA. "Send as document" preserves the file (MetaClean 2026, https://metaclean.app/blog/does-whatsapp-remove-metadata ; CitizenEvidence 2020, https://citizenevidence.org/2020/04/20/sending-encrypted-photos-while-preserving-metadata/). Videos are re-encoded.
- **SynthID.** Over 20 billion items watermarked. The Gemini app verifies images, video, and audio, but only for Google AI output. Quotas are about 10 checks per type per 24h. "No watermark" does **not** mean real (Google help page).
- **How realistic are provenance checks on WhatsApp forwards in India? Low as a primary signal.**
  1. Most Indian phones don't sign at capture.
  2. Scam videos reuse real footage, which is genuinely camera-captured, so provenance on the visual track would be authentic.
  3. Forwarding strips manifests.
  4. Scammers use generators that don't watermark (open-source lip-sync, voice clones).
  - Provenance is valuable in the **positive** direction: verifying *official* communications, e.g. a C2PA-signed RBI/NSE video, an official-channel URL, or a bank.in domain. It is also valuable as **source-footage retrieval**: matching a forward to the original public clip, which is what DAU does manually.
  - I found no evidence that RBI, SEBI, NSE, or BSE currently sign their media with C2PA [U].

---

## 4. Detection state of the art and limits

- **Generalisation failure (the key citation).** Deepfake-Eval-2024 (arXiv 2503.02857) contains 45h of video, 56.5h of audio, and 1,975 images from 88 sites in 52 languages.
  - Off-the-shelf open-source detectors: AUC falls 45–50%; best AUC 0.58.
  - Fine-tuned models peak at accuracy 0.75 (video), 0.86 (audio), 0.63 (image).
  - Best commercial models: video acc 0.78 / AUC 0.79; audio 0.89 / 0.93; image 0.82 / 0.90 (precision 0.99, recall 0.71).
  - No model reaches the ≥90% of human analysts. The authors attribute the commercial edge mainly to dataset curation.
  - Error analysis: off-the-shelf models do worse on diffusion-generated video.
- **Audio.**
  - SSL-AASIST: in-domain EER 0.21%, but with a fixed threshold on In-the-Wild data it rejects 78.7% of genuine speech (arXiv 2606.21584). This is the false-positive trap.
  - P²V: 22 detectors lose 43% performance on realistic cloned speech with noise (arXiv 2508.10949).
  - Replay through a speaker and mic defeats detectors (ReplayDF, arXiv 2505.14862).
  - Indic data gaps: HAV-DF Hindi audio-video dataset (arXiv 2411.15457), IndieFake (arXiv 2506.19014), ML-ITW (14 languages, 180 public figures, arXiv 2603.05852).
- **Lip-sync / audio-visual consistency** (the relevant manipulation for Indian scam videos, which are real footage plus a cloned voice):
  - LipFD, "Lips Are Lying" (arXiv 2401.15668, NeurIPS 2024): temporal audio-visual inconsistency.
  - AV-Lip-Sync+ (arXiv 2311.02733): AV-HuBERT-based.
  - LoCC (arXiv 2606.22772): frame-level localisation.
  - BioLip (arXiv 2604.16808): lip kinematics ("temporal lip jitter"). The authors claim it generalises across languages, which matters for Hindi and regional content.
  - SAVe (arXiv 2603.25140): self-supervised, trained only on authentic video.
  - Classic SyncNet offset or confidence scores are also cheap baselines.
  - DAU experts identified "wav2lip-like" generators in Aug 2026 cases.
- **Open-source code and licences** (check every model before use):

  | Project | Licence | Note |
  |---|---|---|
  | TrueMedia `ml-models` (DistilDIRE, UniversalFakeDetectV2, FTCN, StyleFlow, reverse-search, transcript) | **MIT** | **Weights not released** as of the 3 Feb 2025 README note (https://github.com/truemediaorg/ml-models ; https://www.truemedia.org/post/open-source-release, 27 Jan 2025) |
  | DeepfakeBench (36+ detectors) | **CC BY-NC 4.0** | Non-commercial (https://github.com/sclbd/deepfakebench) |
  | SSL_Anti-spoofing (wav2vec2 XLS-R + AASIST) | **MIT** | https://github.com/TakHemlata/SSL_Anti-spoofing |
  | Wav2Lip | Personal/research/non-commercial | Trained on LRS2 (per a third-party licence note, https://github.com/Kaushik2210/Deepfake-Detector/blob/master/LICENSES.md) [S] |
  | Deepfake-Eval-2024 dataset | Repository terms | https://github.com/nuriachandra/Deepfake-Eval-2024 |

- **Why forensic scores alone are unreliable** (all citable):
  1. Distribution shift (Deepfake-Eval-2024).
  2. Threshold transfer produces huge false-positive rates (78.7% of genuine speech rejected).
  3. Compression and re-encoding: WhatsApp transcodes video, and GODDS analysts couldn't separate artefacts from compression or motion blur.
  4. Detectors disagree: 13/22 and 35/70 split votes; Hiya scored 53% on one confirmed fake.
  5. Vendor classifiers only see their own generators (ElevenLabs said "very unlikely" on a confirmed fake; SynthID covers Google AI only).
  6. Real-but-low-quality video triggers false positives. In the BBC test of Intel FakeCatcher (claimed 96%), "several times the system said a video was fake, when it was in fact real" (BBC, Jul 2023, https://www.bbc.com/news/technology-66267961).
  7. Adversarial adaptation: replay, laundering, and attackers probing public detectors as oracles.
- **Design implication.** Use forensics as supporting evidence with an explicit "inconclusive" band. Never use a single score as a verdict. The rubric says so too: "A detector score alone is not an explanation or proof."

---

## 5. Reporting and response paths in India (and what a prototype can query legally)

| Path | What it does | Machine-readable? | Prototype use (legal-safe) |
|---|---|---|---|
| **1930 / cybercrime.gov.in (NCRP)** | Victims report financial fraud; CFCFRMS freezes funds (the "golden hour") | **No public API.** Victim must file | Generate a pre-filled summary and evidence pack the user submits themselves. Show "call 1930 now if money was sent" |
| **Sanchar Saathi – Chakshu** (DoT) | Report suspected fraud *communications* by call, SMS, or WhatsApp | No public API | Deep-link plus a pre-filled text template (https://sancharsaathi.gov.in/sfc/) |
| **TRAI SMS Header portal** | Look up which entity owns an SMS header | Web lookup; TRAI also publishes a header list PDF | Manual or cached lookup; header-prefix rules (https://smsheader.trai.gov.in/ ; https://www.trai.gov.in/node/7411) |
| **TRAI 1600 series** | Genuine BFSI service/transaction calls come from 1600xx numbers (mandatory 2026) | Rule-based | Rule: a "bank" call from a normal mobile number is a red flag |
| **RBI Sachet** | Report unauthorised deposit-taking; check whether an entity is regulated | No public API | Deep-link (https://sachet.rbi.org.in/) |
| **RBI Alert List** (unauthorised forex/ETPs) | ~95 named platforms with websites; updated 19 Nov 2025 | Public HTML/PDF | **Snapshot and match** domains and names (https://rbi.org.in/scripts/bs_viewcontent.aspx?Id=4235) |
| **SEBI Recognised Intermediaries** | Registered IAs (1,050), RAs (2,271), brokers, etc. | Public HTML lists (data as of 4 Oct 2026) | **Snapshot and match** names and registration numbers (INA/INH) (https://www.sebi.gov.in/sebiweb/other/OtherAction.do?doRecognised=yes) |
| **SEBI Check / "@valid" UPI** | Verify a registered intermediary's UPI/QR/bank account (from 1 Oct 2025) | Web tool, no public API | Rule: payment to a non-"@valid" handle for "SEBI-registered" advice is a red flag. Deep-link to SEBI Check |
| **SEBI SCORES** | Complaints against *registered* intermediaries | No public API | Deep-link (https://scores.sebi.gov.in) |
| **bank.in / fin.in domains** | Banks moved to .bank.in (deadline 31 Oct 2025); NBFCs to fin.in | DNS-checkable | Rule: "bank" link not on .bank.in is a red flag (IDRBT PDF, https://www.idrbt.ac.in/wp-content/uploads/2025/04/btMoneyToday.pdf) |
| **Official press releases** (RBI, SEBI, NSE, BSE) | Standing denials, e.g. "RBI does not give investment advice", "BSE CEO doesn't give stock tips or run WhatsApp groups", "SEBI does not collect STT" | Public HTML/PDF/RSS | Curated **claim-rebuttal knowledge base** with citations |
| **PIB Fact Check** | Government-related claims; WhatsApp +91 8799711259 | No API; X/FB posts | Deep-link; index public debunks (https://www.pib.gov.in/PressReleaseDetail.aspx?PRID=2206735) |
| **DAU tipline** (MCA / "Trusted Information Alliance") | Expert multi-tool analysis; publishes assessment reports (active through Aug 2026) | No API; public reports | Escalation target for ambiguous cases; reports useful as labelled *descriptions* (DAU doesn't embed media) (https://dau.trustedinfoalliance.in ; tipline https://bit.ly/dauwatipline) |
| **Meta reporting / celeb-bait** | In-app ad and impersonation reports; FRT celeb-bait in UK/EU/KR | No public API for reports | Deep-link plus a report text template |
| **YouTube** | Privacy complaint for AI likeness; likeness detection for YPP creators (2025), pilot for civic leaders and journalists (10 Mar 2026, https://blog.youtube/news-and-events/expanding-likeness-detection-civic-leaders-journalists/) | No public API for third parties | Deep-link |
| **IT Rules 2026 grievance route** | Platforms must act within 3h on valid orders and within set timelines on grievances | n/a | Package evidence for the *impersonated institution's* brand-protection or legal team |

**Legal posture for the prototype:**
- Use only official public lists, snapshotted with a timestamp and source URL. Respect site terms and don't hammer servers.
- Never automate filings on NCRP, Chakshu, or SCORES. The user or institution submits.
- Phrase results as "not found in SEBI's register as of <date>", never "X is a fraudster".

---

## 6. Competitors and existing products

| Product | What it is | Gap for India finance |
|---|---|---|
| **DAU tipline** (MCA, Meta-funded, launched Mar 2024; https://about.fb.com/news/2024/02/mcas-whatsapp-helpline-curbing-the-spread-of-ai-generated-misinformation/) | Human fact-checkers plus a stack of tools (Hive, Hiya, Aurigin, ElevenLabs, Contrails, GODDS, RIT DeFake) | Manual and slow (report days to weeks after discovery); one report per video; no registry or claim checks; no bank integration |
| **Hive** | Detection API, free Chrome extension; US DoD/DIU contract $2.4M over 2 years (MIT Tech Review, 5 Dec 2024, https://www.technologyreview.com/2024/12/05/1107961/the-us-department-of-defense-is-investing-in-deepfake-detection/) | Score-centric; no Indian registry or reporting context |
| **Reality Defender** | API with free tier of 50 scans/month (Jul 2025); third-party listing shows $399/mo (https://www.realitydefender.com/insights/reality-defender-launches-free-access-to-deepfake-detection-api ; https://checkthat.ai/brands/reality-defender) | Enterprise screening; no claim verification |
| **Sensity** | Forensic investigation incl. face swap and ID documents; quote-only (https://tech-insider.org/reality-defender-vs-hive-vs-sensity-2026/) | Enterprise, expensive |
| **Intel FakeCatcher** | PPG blood-flow detector, "96%" claim (Intel); BBC test found false positives on real video, and it doesn't analyse audio | Fails exactly on the Indian lip-sync + cloned-audio pattern |
| **Resemble Detect** | Audio/video detection; vendor claims audio EER <6% across 50+ languages (https://www.resemble.ai/resemble-ai-vs-reality-defender) [S] | Vendor claims only |
| **McAfee Deepfake Detector** | Flags AI-generated *audio* in videos on AI PCs; launched in India (BusinessWire India, https://www.businesswireindia.com/mcafee-deepfake-detector-launches-in-india-the-worlds-first-automatic-and-ai-powered-deepfake-detector-93064.html) | Device-bound (AI PCs); Indian retail victims are mostly on phones and WhatsApp |
| **Contrails AI** (Bengaluru) | Audio/video deepfake detection; DAU partner; $1M pre-seed (ET B2B, ~Oct 2025, https://b2b.economictimes.indiatimes.com/amp/news/entrepreneur/contrails-ai-raises-1-million-in-pre-seed-funding-for-ai-driven-content-detection-platform/124363841) | B2B detection; low-confidence outputs on compressed scam videos (per DAU) |
| **pi-labs** (Pune) | "Authentify" deepfake detection for BFSI and law enforcement; cited by Gartner (https://www.pi-labs.ai/ ; Inc42) | Enterprise and forensic; not a consumer verification flow |
| **Kroop AI** (Gujarat) | "Vizmantiz" multimodal detector; on-device demo with Intel (https://kroop.ai/) | Detection-only |
| **Vastav AI** | Single-developer web tool claiming "99.7%" (https://vastav.ekoahamdutivnasti.com/) | Unverified claims |
| **IndiaAI Safe & Trusted AI picks** | Saakshya (IIT Jodhpur + IIT Madras; multi-agent RAG deepfake detection and governance), AI Vishleshak (IIT Mandi + HP forensics), IIT Kharagpur voice detection (PIB, https://www.pib.gov.in/PressReleasePage.aspx?PRID=2175698) | Research and government-forensics oriented |
| **KYC vendors** (HyperVerge, IDfy, Signzy, iProov, Sumsub) | Liveness and injection detection for V-CIP | Already cover the V-CIP niche, which is another reason not to make it the core |
| **Platform measures** | Meta SEBI verification for securities ads (31 Jul 2025); Meta celeb-bait FRT (not India); YouTube likeness detection | Scam ads still run (DAU 2026). Protection mostly needs the *celebrity* to enrol, not the victim |

**Remaining gaps:**
- **Retail investors (especially 50+, Hindi or regional-language, WhatsApp-first):**
  - No tool takes a *forwarded* video, image, PDF, or message and answers within a minute, in plain language: "Is this endorsement/platform/advisor/payment legit, and what should I do now?"
  - DAU is slow and manual. PIB covers government claims only. Detectors return scores, not actions.
  - The registries (SEBI IA/RA, @valid, RBI Alert List, bank.in, 1600) exist but are fragmented and unknown to users.
  - Reporting needs effort and the right channel at the right time (1930 within the golden hour).
- **Banks, exchanges, AMCs (brand-protection / investor-protection teams):**
  - They issue the same "beware deepfake" press release again and again (BSE: "may continue to resurface").
  - They lack campaign clustering (same script, same UPI, same WhatsApp-group link across many celebrity faces) and evidence packaging for the IT Rules 3-hour takedown route.
- **Corporate finance teams:** current advice (I4C, Jun 2026) is "confirm by voice call or face-to-face", which deepfakes defeat. Approval workflows lack cryptographic out-of-band confirmation and payment-claim checks against vendor masters.

---

## 7. Judgement and recommendation

### What most teams will build (predicted)
1. "Upload video, get a FAKE 93% score and a Grad-CAM heatmap" with an XceptionNet/EfficientNet trained on FaceForensics++/DFDC, wrapped in a web app or Chrome extension. This is the generic detection claim the rubric marks down. It will also fail on Indian lip-sync + cloned-voice WhatsApp forwards (Deepfake-Eval-2024).
2. A real-time deepfake detector for video calls (Arup-inspired) as a Zoom/Meet plugin. Weak India evidence; hard to show low false positives in 48h.
3. V-CIP liveness or anti-injection. Crowded with incumbents and only loosely matches "communications".
4. A WhatsApp bot that calls a detector API. Better UX, same core weakness.

### How to beat them: "verify the claim and the source, not just the pixels"
The bounded problem with the strongest rubric fit:
- **Primary user:** an Indian retail investor (and the family member they forward things to) who receives a *celebrity/regulator-endorsed investment pitch* or a *regulator-branded notice* on WhatsApp/Facebook.
- **Secondary user:** the impersonated institution's investor-protection or brand-protection team (exchange, AMC, bank).
- **Harmful moment:** the 5–30 minutes between seeing the video or notice and joining the WhatsApp group or paying the "registration/STT" amount.

**Why it wins:**
- **Problem fit (20).** Investment fraud is 76% of 2025 losses. There are named, dated regulator warnings (RBI, NSE, BSE, PIB, SEBI) and a concrete scam template (DAU).
- **Differentiation (15).** It goes beyond a generic detection claim. The core is India-specific *claim verification* against official registries, plus *source-footage tracing* and *copycat-campaign matching*. Those are the signals DAU's experts actually rely on.
- **Safety (15).** Multi-signal fusion with an explicit "inconclusive" state:
  - "High risk" requires at least two independent signals, at least one non-forensic (registry, rule, or source match).
  - No accusation wording; human review before any institution takedown request.
  - Rate-limiting and coarse public output to stop scammers using the tool as an oracle.
- **Adversarial robustness argument (the pitch line).** "Generators will keep improving; scam economics won't. Every scam must still route money or attention to something checkable: an unregistered advisor, a non-@valid UPI ID, an RBI-Alert-List platform, a non-bank.in link, a WhatsApp group. A perfect deepfake still fails the claim check."
- **Explanation for non-technical reviewers.** A Hindi/English "Verification Card" with three plain-language reasons, each linked to an official source. For example: "RBI says it never endorses schemes (RBI PR, 19 Nov 2024)", "This platform is on RBI's Alert List", "The visuals come from a 27 Apr 2026 YouTube speech about something else; the voice was replaced."

**Is cross-cutting claim verification a strong differentiator?** Yes, with caveats.
- **Strengths:**
  - It is deterministic, explainable, and cheap.
  - It is robust to new generators and uses public, legal data.
  - It aligns with organiser cues: "credible verification or reporting path" and "more than a generic AI detection claim".
- **Caveats:**
  1. It drifts toward Track 02 (scam patterns), so keep manipulation analysis visibly central: source tracing, lip-sync and voice signals, forged-letterhead checks.
  2. Registries are fragmented web pages, not APIs. Snapshot them and show freshness dates.
  3. Scammers impersonate *registered* entities, so verify contact points (official domain, @valid handle, 1600 number), not just names.
  4. Name-matching false positives need fuzzy-match thresholds and reviewer override.
  5. Legitimate celebrity ads by registered entities exist. A registered entity on an official channel should *lower* risk.

### Concept A (recommended): "Satyapan", a forward-to-verify assistant plus campaign desk
- **Inputs:** a forwarded video, image, PDF/letter, text, or link, sent by the user via a WhatsApp-style bot (demo: web/PWA share-target or WhatsApp sandbox) or a phone line (Vapi voice agent for elderly users: "describe what you received"). Consent banner. Ephemeral processing; delete after 24h unless the user opts in to share evidence.
- **Pipeline:**
  1. **ASR and translation.** Deepgram or Whisper, Hindi and English first.
  2. **LLM claim extraction.** Entities (person, institution, platform), claim type (endorsement, guaranteed returns, payment demand, legal threat), call-to-action (link, WhatsApp/Telegram group, UPI ID, phone number, app).
  3. **Registry and rule checks.** Snapshots of SEBI IA/RA/brokers and the RBI Alert List; @valid UPI rule; bank.in/fin.in domain rule; 1600/SMS-header rules; regulator standing-denial knowledge base (RBI, SEBI, NSE, BSE, PIB, with URLs).
  4. **Campaign matching.** Transcript MinHash or embedding against known scam scripts (seeded from public DAU/PIB/BSE descriptions and team-made synthetic variants); audio fingerprint; perceptual video hash. Detects "copycat" reuse.
  5. **Source-footage retrieval.** GPU-built index of *official public* clips of the ~25 most-impersonated figures (RBI, SEBI, NSE, BSE heads, FM, Murthy, Ambani...), from official channels, storing embeddings only. Answers: "visuals match this original; the audio doesn't."
  6. **Forensics as supporting evidence.** Lip-sync offset and confidence (SyncNet/LipFD-style); synthetic-speech score (SSL-AASIST, MIT), calibrated on compressed Hindi/English data with a wide "inconclusive" band. Forged-letter checks: reference-number format, signatory, domain, QR/URL resolution.
  7. **Fusion.** Rules plus a calibrated score yield Verified-official / Likely-scam / Unverified-be-careful. Requires at least two independent signals for "Likely scam".
  8. **Output.** Verification Card plus "What to do now": if paid, call 1930 within the golden hour; report on Chakshu; DAU tipline for expert review; platform report links; pre-filled complaint text.
- **Institution desk:** clusters of the same campaign (by script, UPI, group link, or impersonated person) with counts and first/last seen; reviewer queue (approve/reject); one-click evidence pack for platform grievance or takedown under IT Rules; "resurfaced" alerts, which BSE's repeated PRs show they need.
- **48h MVP (demonstrable):**
  - Web/PWA bot (WhatsApp sandbox if approved) handling video, image, PDF, and text.
  - Snapshots of SEBI IA/RA lists, the RBI Alert List, and ~30 regulator press releases.
  - Source index of ~10 public figures from official public uploads.
  - Synthetic test set, with consent: the team clones its *own* voices and lip-syncs its *own* faces into Hindi/English scam scripts; plus forged-letter mock-ups of a fictional regulator notice. Do not generate deepfakes of real officials; the brief allows only synthetic, public, consented, or authorised data.
  - Live demo: three forwards scored in under 60s each.
  - Metrics slide: false-positive rate on genuine official clips (e.g., actual RBI/NSE YouTube uploads should come out "Verified-official/no red flags"); detection on held-out unseen-generator fakes where the pixel detector alone fails but the claim and source checks catch it.
  - Reviewer dashboard showing clustering of three copycat variants.
- **Integration and owners:** a free consumer bot. B2B: exchanges, AMCs, and banks' investor-protection or brand-protection teams; regulators' investor-awareness cells; cybercrime cells as evidence consumers. Rollout: Hindi/English, then regional languages; WhatsApp channel; API for bank apps ("verify before you pay" inside UPI or net-banking flows).

### Concept B (alternative or extension): "Signed-request" verification for corporate finance
- **Threat:** CEO/CFO deepfake voice or video calls and hijacked WhatsApp "Boss scams" (I4C advisory, 22 Jun 2026; Arup).
- **Product:** a finance-team copilot that intercepts payment instructions (email, WhatsApp text, call transcript via Vapi/Deepgram). It extracts the claim (amount, beneficiary, urgency, secrecy cues), checks it against the vendor master and approval policy, then issues a **cryptographic out-of-band challenge** (passkey/WebAuthn push) to the executive's *registered* device. Optional deepfake signals are advisory only.
- **Pitch:** "Verify the request, not the face."
- **48h MVP:** chat/email parser, mock ERP vendor master, passkey confirmation, evidence log.
- **Risk:** less India-specific scale data, and overlap with Tracks 01/02. Keep as an extension slide, or as the "institutions" half of Concept A, where official bodies sign their communications. The same idea applies to RBI/SEBI publishing signed notices and C2PA-signed videos as "positive verification".

### Main risks and mitigations
1. **Over-claiming detection accuracy.** Judges know the Deepfake-Eval-2024 results. Cite them yourself and present forensics as supporting evidence.
2. **Track drift to 02.** Make manipulation analysis (source tracing, AV-consistency, forged documents) visibly central in the architecture.
3. **Data and legal.** Don't create deepfakes of real officials. Use consented team media and public official clips (index embeddings, not redistributed media). Snapshot registries with dates. Make no automated government filings. Mind DPDP Act 2023 obligations for any stored personal data.
4. **False positives on genuine content.** Positive-verification path (official channel or source match), "inconclusive" band, reviewer override, and no accusation language.
5. **Adversarial adaptation.** Fresh scripts beat transcript matching, and new domains beat static lists. Mitigate with semantic claim checks, continuous snapshots, and campaign clustering on payment endpoints. Rate-limit and avoid exposing raw scores, to stop oracle attacks.
6. **WhatsApp Business API approval and latency.** Use a web/PWA share-target fallback for the demo; target under 60s per forward and show the latency budget.
7. **Language coverage.** Hindi and English in the MVP; regional languages on the roadmap (ASR quality caveat).

### Items still unverified (re-check before putting on slides)
- Whether any official I4C figure isolates deepfake-enabled losses (none found).
- A confirmed Indian deepfake *video-call* CEO fraud (none found; cases found are WhatsApp DP impersonation).
- IBA guidance on V-CIP deepfakes (none found); exact V-CIP clause wording in the 28 Nov 2025 KYC Directions.
- iPhone 18 Pro "Apple Reference Image" and Vivo X300 Pro C2PA (single vendor-blog source).
- Exact release date of PIB PRID 2287039; BSE PR dates (inferred from file names).
- The Mumbai Rs 10 cr "Boss scam" (Instagram-only source).

Raw search outputs and page scrapes are in `D:/hackathons/amazon-raksham/research/raw/t03/`.
