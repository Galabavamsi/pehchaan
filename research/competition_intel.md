# RAKSHAM / Amazon AI Cyber Security Hackathon: Competition Intel

Compiled 2026-10-05. Sources were live-scraped on this date unless noted. **[UNVERIFIED]** marks anything I could not confirm from a primary page.

---

## 0. TL;DR: what changes our plan

1. **Round 1 submission closes 10 Oct 2026, 12:23 AM IST.** That is Unstop's "Idea Submission Round" end time, and it matches ARIES's "Submit your idea by 10 Oct 2026". The organisers' own description text still gives **7 Oct 2026** as the registration deadline. Unstop's widget says registration closes **9 Oct 2026, 12:00 AM IST**. To be safe, **register now and aim to upload by 7–8 Oct**.
2. **Submission platform: Unstop.** Upload one PDF. The pitch deck can have at most 10 slides plus an optional appendix. The architecture section can have at most 3 pages or slides. **No file-size limit or slide aspect ratio is stated anywhere.**
3. **The Unstop page shows 2,350 registrations** (live count, 5 Oct 2026). Only the top 30 teams reach the finale, so expect a shortlist of roughly 1–3% if most registrants submit.
4. **Do not cite Amazon Connect Voice ID.** It reached **end of support on 20 May 2026** and no longer exists. **Do not cite Amazon Fraud Detector as something we will use.** It has been **closed to new customers since 7 Nov 2025**.
5. **No judges or Amazon participants are named publicly.** In Round 1, "reviewers" score only the PDF.
6. The tone Amazon and the organisers use: "Substance matters more than slide polish. We reward products that are **specific, buildable, and safe**." Amazon's India trust chief: "**Behaviour is much harder to fake than documents or images.**"

---

## 1. Official listings

### 1.1 Unstop (primary listing, the submission platform)
URL: https://unstop.com/competitions/raksham-ai-cybersecurity-hackathon-iit-delhi-1761331
Scraped with India geo-targeting so times display in IST. Page footer: "Updated On: 26 Sep 26, 02:56 PM IST".

| Field | Value on Unstop |
|---|---|
| Listed by | Indian Institute of Technology (IIT), Delhi |
| Organisers | ARIES and DevClub, IIT Delhi, in collaboration with Amazon, supported by Learning Links Foundation |
| Team size (widget) | **1–4 members**. This conflicts with the description and the brief, which both say **2–4**. Use 2–4. |
| Eligibility tags | Undergraduate, Postgraduate, Engineering Students |
| **Stage 1: Idea Submission Round** | **26 Sep 2026, 12:23 AM IST to 10 Oct 2026, 12:23 AM IST**. "Submission round through Unstop platform on basis of the attached Problem Statements." Status: Live |
| **Stage 2: Offline Round** | **24 Oct 2026, 09:00 AM IST to 25 Oct 2026, 08:00 PM IST**, labelled "48-hour intense battle of minds and code". That window is only about 35 h, so the "48 hours" probably includes an overnight start or is approximate. **[ask organisers]** |
| Registration deadline (widget) | **09 Oct 2026, 12:00 AM IST**. The banner alt text says "Participate … before 2026-10-09T00:00:00+05:30". |
| Registration deadline (description text) | "Registration deadline: **7th October 2026**" |
| Grand Finale (description) | 24–25 Oct 2026 at IIT Delhi |
| Registered count | **2,350** (fresh scrape 2026-10-05; a cached copy showed 2,349). The page said "3 days left". |
| Prizes (₹4,00,000 total cash) | 1st ₹2,00,000; 2nd ₹1,00,000; 3rd ₹50,000; 4th ₹25,000; 5th ₹25,000 |
| Travel | "**Amazon will be providing travel** to participants for the grand finale, but participants need to **find accommodation themselves**." |
| Contacts | +91 7038703979, **+91 7058559569** (second number, not in our summary), team.ariesiitd@gmail.com, plus an Unstop "Send queries to organizers" button |
| Attachment | round-1-participant-brief.pdf (same file as our local `6ab571dd46c0a_round-1-participant-brief.pdf`) |
| FAQs / Discussions | **Empty**. No FAQs posted. |
| Judges | None listed |

Description text on Unstop (key lines, verbatim):
- "India now runs on UPI, digital banking, and wallets, and fraudsters are running on AI. Cloned voices of bank officials, deepfake videos of CEOs approving transfers, and AI-scripted scam workflows are hitting real people every day."
- Round 1: a single PDF. The deck covers "problem, user, threat scenario, detection approach, validation plan, safeguards, deployment pathway, and 48-hour prototype plan". The architecture overview covers "end-to-end system diagram, data flow, detection logic, human review and escalation path, and security/privacy mitigations". "Reviewers score only the submitted PDF, so it must stand on its own without a live pitch or external links."
- Rubric (100 points): Problem fit 20, Technical architecture & detection logic 20, Value & differentiation 15, Feasibility & finale plan 15, Safety/privacy/responsible AI 15, Adoption/integration/scale 10, Communication 5.
- "**Substance matters more than slide polish. We reward products that are specific, buildable, and safe.**"
- Rules: only synthetic, public, consented, or properly authorised data; disclose all AI-generated content, datasets, models, and third-party assets in an appendix; "Incomplete submissions may be **disqualified**".

### 1.2 Round 1 Participant Brief (local PDF, also attached on Unstop)
Additions beyond the Unstop text:
- "Select **exactly one** track. You may mention future extensions to other tracks, but your Round 1 submission will be evaluated against your selected track."
- Required deck contents: team, chosen challenge, and a one-sentence solution; user, threat scenario, and harm; current journey, product flow, and differentiation; core detection or decision approach; data, evidence, validation plan, and assumptions; privacy, security, safety, and misuse safeguards; deployment pathway and 48-hour prototype plan.
- Required architecture contents (at most 3 pages or slides): one legible end-to-end diagram; inputs, data sources, consent, and provenance; components, models or rules, storage, interfaces, and outputs; detection or decision flow, alerts, and escalation; human review, notifications, reporting, and evidence path; security, privacy, and adversarial mitigations; performance assumptions and validation.
- AI disclosure goes "in an appendix **or slide note**".
- "Build for Trust" design questions:
  - What data do you need, and what do you *not* collect?
  - How do you handle false positives and false negatives? "**Avoid automatic blocking or accusations based on a single weak signal.**"
  - Who can act on the result, and what human review comes before any high-impact action?
  - "**A detector score alone is not an explanation or proof.**"
  - How do you resist misuse: fraudster adaptation, adversarial inputs, privacy abuse, and unauthorised access to evidence?
- Track cues:
  - Voice: audio, behavioural, and call-context signals; customer friction; consent; a safe evidence path.
  - Scam: define the scam workflow; available metadata and behavioural signals; timely action; alert fatigue; transaction privacy.
  - Deepfake: provenance and forensic signals; explanations a non-technical reviewer can follow; evolving manipulation methods; a credible verification or reporting path.
- Reviewer checklist: can someone identify the primary user, the harmful moment, and the exact threat pattern **in under a minute**?
- "Questions about the submission format should be directed to the organising team **before the application deadline**."
- **Not specified anywhere:** file-size limit, slide aspect ratio, font rules, allowed or banned tools, or LLM usage limits. AI use is allowed but must be disclosed.

### 1.3 Third-party aggregator: StartupGrantsIndia
URL: https://www.startupgrantsindia.com/competitions/raksham-ai-cybersecurity-hackathon
This page mirrors the Unstop text. It states team size as 2–4 and adds: "Registration closes on 7th October 2026 (listed as 2026-10-09 on the platform)". That confirms the date discrepancy exists in the source listing.

### 1.4 DevClub website (devclub.in)
- https://devclub.in/events lists no RAKSHAM entry. The latest event shown is "AI Square Speedathon 2025". The site appears stale.
- X account https://x.com/devclub_iitd could not be scraped (unsupported site). **[UNVERIFIED: DevClub X posts]**

### 1.5 ARIES IIT Delhi
- Website https://ariesiitd.com/events: the site map has **no RAKSHAM page**. Past events include the Eightfold AI hackathon (Innov8), QRT x ARIES, Citadel Securities x ARIES, Ship-a-thon, and an NDTV AI Summit.
- Instagram https://www.instagram.com/aries.iitd/: Instagram blocks scraping. The caption below was reconstructed from search-engine snippets:
  > "Got an idea to fight AI-powered fraud? Now's your chance to build it! Introducing RAKSHAM: AI Cybersecurity Hackathon. Presented by IIT Delhi in collaboration with Amazon. Pick a problem. Build your solution. Make an impact … Finale: 24–25 Oct 2026 ⏰ **Submit your idea by 10 Oct 2026.** Think. Build. Defend. 🛡️ #RAKSHAM #AIHackathon #CyberSecurity #IITDelhi #Amazon"
- LinkedIn https://in.linkedin.com/company/aries-artificial-intelligence-society-iitd could not be scraped. **[UNVERIFIED]**

### 1.6 Learning Links Foundation (LLF)
- LinkedIn post (about 30 Sep 2026): https://www.linkedin.com/posts/learning-links-foundation_raksham-aihackathon-amazon-activity-7510958663080210432-QZeu
- Facebook: https://www.facebook.com/LearningLinksIndia/posts/the-next-breakthrough-in-ai-cybersecurity-could-begin-with-your-idea-registratio/1803410941793664/
- X: https://x.com/LLF_IN/status/2105193552234025230
- Snippet text: "Can your idea outsmart AI-powered cyber threats? Registrations are now open for Raksham, an AI Cybersecurity Hackathon that challenges students to develop innovative solutions to emerging … threats including **deepfake scams, voice cloning fraud, and AI-driven financial fraud**. **Sponsored by Amazon, with IIT Delhi as the knowledge and hosting partner** …" Hashtags: #Raksham #AIHackathon #Amazon #DigitalSecurity #LearningLinksFoundation.
- Context: LLF is Amazon's CSR implementation partner in India. It runs the **Amazon Future Engineer** programme (https://learninglinksindia.org/afe). This suggests a social-impact and CSR lens, which favours protecting first-time and vulnerable users.

### 1.7 Amazon pages
- No aboutamazon.in or Amazon press page about RAKSHAM was found. **[UNVERIFIED: no Amazon-side announcement located]**
- Possible origin: on 13–14 Sep 2025, I4C (Ministry of Home Affairs) and Amazon India launched **#ScamSmartIndia**. The plan explicitly included "**a national hackathon to develop AI-powered solutions for scam detection and prevention**". I found no evidence that this hackathon ran in 2025–26. RAKSHAM may be that commitment being delivered. **[UNVERIFIED link]**
  - https://government.economictimes.indiatimes.com/news/secure-india/amazon-and-i4c-launch-nationwide-campaign-to-combat-online-fraud-in-india/123877566
  - https://www.varindia.com/news/i4c-and-amazon-india-join-forces-for-scamsmartindia-campaign

### 1.8 Differences from our summary

| Our summary | What sources say |
|---|---|
| Registration deadline 7 Oct 2026 | Unstop description: 7 Oct. Unstop widget: **9 Oct 00:00 IST**. Submission stage ends **10 Oct 00:23 IST**. ARIES: "Submit your idea by 10 Oct". |
| Team size (not stated) | Brief and description: **2–4 students**, one entry. Unstop widget: 1–4. |
| Finale 24–25 Oct, 48h | Unstop window: 24 Oct 09:00 IST to 25 Oct 20:00 IST (about 35 h). |
| One contact number | A second number exists: +91 7058559569 |
| (not in summary) | Amazon pays finale travel; teams book their own accommodation |
| (not in summary) | Incomplete submissions "may be disqualified" (Unstop) or "ineligible" (brief) |
| Name | Brief title: "Amazon AI Cyber Security Hackathon". Unstop title: "RAKSHAM – AI Cybersecurity Hackathon". |
| Don't confuse | **E-Raksha Hackathon 2026** is a different event: eDC IIT Delhi with CyberPeace, held 16–18 Jan 2026 as part of BECon'26 (https://unstop.com/competitions/e-raksha-hackathon-2026-iit-delhi-1613454) |

---

## 2. Earlier editions and similar Amazon hackathons in India

- **RAKSHAM has no earlier edition.** It appears to be the first; no 2025 RAKSHAM was found. The precursor commitment is the I4C–Amazon national hackathon pledge from Sep 2025 (see 1.7). **[UNVERIFIED whether that hackathon was held]**
- **HackOn with Amazon** is Amazon India's flagship student hackathon, run on Unstop.
  - Season 6 (2026): https://unstop.com/hackathons/crp-hackon-with-amazon-60-amazon-1682652. Prize pool ₹2.25L. Format: coding round, then a 48h virtual hackathon, then mentorship, then a finale presented to Amazon leaders.
  - **Season 5 had a theme "AI-Powered Trust & Safety Platform"**: "Develop AI solutions to enhance marketplace trust through advanced fraud detection, counterfeit prevention, and review authenticity verification … LLMs to analyze patterns … real-time monitoring of product lifecycle from listing to returns." Source: https://www.scribd.com/document/878124822/HackOn-With-Amazon-Season-5-Idea-Submission-Round
  - Season 5 winners (Sarthak Sharma, Sarthak Gupta, Rohan Indora) built **"Amazon Hives"**, a group-shopping feature (https://www.youtube.com/watch?v=IEnsJWxjeX4). Their lessons:
    - Finale judges are senior leadership, so **impact and clarity beat technical depth**.
    - Keep the pitch crisp; there are only about 10 minutes.
    - **Tie the idea to how Amazon benefits** (customer obsession, business impact).
    - **Present it as a real product that plugs into Amazon.**
    - Get outside reviewers to check the deck.
  - Team "HackOGs" won HackOn with a returns-routing engine that decides the "next life" of returned items (https://www.youtube.com/watch?v=zKUNotgSpso). Judges valued **product design thinking**: the exact customer problem, a clear customer experience, and **thinking at Amazon scale**.
  - Third-party guides (low confidence) say judges reward complete working prototypes over half-built complex ideas, AWS or GenAI usage, scalable architecture, and real customer problems. Example: https://veedaily19.substack.com/p/hackon-with-amazon-60-complete-guide
- **Amazon Nova AI Challenge** (global, invite-only university competition; not India-specific). Track 1 (2025) was "**Trusted AI**": red-team bots against safe coding assistants. The 2026 track is "Trusted Software Agents". It shows that Amazon Science values **adversarial red-teaming and measurable safety**. Purdue won a round.
  - https://www.amazon.science/nova-ai-challenge
  - https://arxiv.org/abs/2508.10108
- **Amazon ML Challenge** is a leaderboard-scored ML competition. It was not researched in depth because it is of little relevance to a pitch-scored round. **[not verified]**

**What Amazon-linked judges tend to reward** (inferred from the above plus the RAKSHAM rubric):
- A sharply defined customer and the harmful moment ("work backwards from the customer").
- A narrow MVP that is demonstrably buildable.
- A clear integration point with a real operator, such as a bank, PSP, or Amazon Pay.
- Scale and latency awareness.
- Concrete safety and anti-misuse design: red-teaming and adversarial adaptation.
- Clarity over polish.

---

## 3. Amazon's India fraud-prevention positions (for pitch alignment)

### 3.1 Amazon India and Amazon global statements
- **"Here's how Amazon helps protect consumers from scammers"** (aboutamazon.in, 14 Aug 2024): https://www.aboutamazon.in/news/retail/amazon-guide-to-protecting-customers-from-scammers
  - Cites RBI FY2023-24 data: digital-payment-gateway fraud cases rose about 3x, to 36,075 from 13,564. Also cites GASA's estimate of over $1T in global scam losses in 2023.
  - The most-reported India scam in 2024 was fake messages "asking customers to verify a product order".
  - **amazon.in/reportascam** is a self-reporting tool in more than 8 languages. Amazon points victims to **1930** and **cybercrime.gov.in**.
  - "Mission GraHAQ" was run with UP Police and reached about 3M people. Amazon works with **I4C**.
  - In 2023 Amazon worked with Microsoft and the CBI; this "led to dismantling of over 70 fraudulent call centers in India".
  - Amazon publishes "what we will NOT do" messaging, for example: no gift-card payments, no software installs for customer service.
  - Amazon says it relies on customer reports to learn bad-actor patterns.
- **#ScamSmartIndia with I4C** (13–14 Sep 2025). Rakesh Bakshi, VP Legal, Amazon India: "**When scammers misuse names of known brands … they damage consumer confidence in the entire digital economy**." The campaign included "Scam-Free September" multilingual tips, flyers in Amazon packages, and the national AI hackathon pledge. I4C named **first-time internet users and senior citizens** as the vulnerable groups. Source: ET Government link in 1.7.
- **Mission GraHAQ, 4th edition** (31 Jul 2026, per YourStory). Amazon commissioned a handbook, "Your Guide to Safe Online Shopping" (by Safer Internet India), covering nine scams: fake websites and phishing, fake delivery, "too good to be true" deals, empty box, payment scams, fake urgency, delivery box scams, fake customer-support accounts, and membership renewal. https://yourstory.com/ai-story/amazon-warns-on-ai-scams-in-india
- **TOI, 4 Aug 2026.** Rohan Oommen, VP Customer & Partner Trust at Amazon, said the Indian challenge is AI scams aimed at **first-time users from tier-2 and tier-3 cities**. GenAI enables fake identities, forged documents, and synthetic reviews. Amazon uses **agentic AI for continuous audits** plus years of behavioural data.
  - "**Behaviour is much harder to fake than documents or images.**"
  - **Phone-based fraud is harder to tackle than fake websites because attribution is harder.**
  - Global figures for the last year: about 300M fake reviews removed, about 70,000 phishing sites taken down, and about 14,000 scam-linked phone numbers actioned.
  - https://timesofindia.indiatimes.com/business/india-business/ai-fraud-is-hitting-indias-new-net-users-hardest-amazon/articleshow/132843254.cms
- **SENTRIX** (13 Feb 2026). This is Amazon's AI phishing-site detection system; it raised successful phishing-URL takedowns by more than 10% in 2025. The paper was presented at ACL 2026. Scott Knapp, VP Worldwide Buyer Risk Prevention, is quoted. https://trustworthyshopping.aboutamazon.com/how-amazons-ai-innovation-helps-protect-customers-from-phishing-scams
- **"6 tips to avoid scams impersonating Amazon"** (Jul 2025, updated Jun 2026). Amazon can take down reported phishing sites "in just a few hours". It will never ask for payment over the phone or for remote access. Report to reportascam@amazon.com. https://www.aboutamazon.com/news/retail/how-to-avoid-amazon-scams
- **Scam Trends page**: over two-thirds of 2023 impersonation scams involved order or account issues. https://trustworthyshopping.aboutamazon.com/amazon-scam-trends

### 3.2 Amazon Pay India and UPI
- Girish Krishnan, Director, Payments & Merchant Services, Amazon Pay India: "**Most UPI frauds don't happen because systems fail**." He frames UPI fraud as social engineering: fake collect requests, QR fraud. The LinkedIn snippet says Amazon Pay India "works with **NPCI** to improve digital payment security through **reverse SMS binding, biometric authentication**, and fraud prevention". **[I could only read the snippet; the post itself was not opened]**
  - https://www.linkedin.com/posts/amazon-pay-india_girish-krishnan-director-payments-merchant-activity-7468575387418185728-LZ7Y
  - https://www.youtube.com/shorts/eBamJfdrulo
  - GFF 2026 talk: https://www.youtube.com/watch?v=yFw-sf4e3rU
- Amazon Pay UPI Circle (delegated family payments): https://www.aboutamazon.in/news/retail/amazon-pay-upi-circle-family-payments
- **[UNVERIFIED]**: I found no specific "Amazon Pay safe" campaign name.

**Pitch hooks:**
- Protect first-time and senior users at the moment of social engineering, with behavioural and call-context signals rather than a single deepfake score.
- Add a multilingual, plain-language warning.
- Use a one-tap report path into amazon.in/reportascam, **1930**, or cybercrime.gov.in, or into the bank's dispute flow.
- Offer human-reviewed escalation instead of auto-blocking.

### 3.3 AWS service status (verified in AWS docs, 2026-10-05)

| Service | Status | Use in pitch? |
|---|---|---|
| **Amazon Connect (Customer) Voice ID** | No new customers from 20 May 2025. **End of support 20 May 2026: no longer accessible.** AWS points to partners such as **Pindrop** (AWS Marketplace). https://docs.aws.amazon.com/connect/latest/adminguide/amazonconnect-voiceid-end-of-support.html | **NO.** Citing it signals stale research. |
| **Amazon Fraud Detector** | **Not open to new customers since 7 Nov 2025** (maintenance). AWS recommends **AutoGluon + Amazon SageMaker AI**, and **AWS WAF Fraud Control** (managed rules, not ML) for login and sign-up fraud. https://docs.aws.amazon.com/frauddetector/latest/ug/frauddetector-availability-change.html | **NO.** Use SageMaker/AutoGluon or our own models. |
| **Amazon Transcribe** (streaming) | Active. en-IN and hi-IN streaming are supported. Redaction works for en-IN but **not for hi-IN**. | Yes |
| **Amazon Transcribe Call Analytics** | Active. **en-IN and hi-IN are post-call only. Real-time Call Analytics is limited to en-US, en-GB, en-AU, fr, de, it, es-US, and pt-BR.** Issue detection is en-US/GB/AU only; summaries are en-* only. https://docs.aws.amazon.com/transcribe/latest/dg/supported-languages.html | Only for post-call or evidence; for real-time Indian calls use plain streaming plus our own logic |
| **Amazon Bedrock Guardrails** | Active: content filters, denied topics, PII filters, contextual grounding checks, **Automated Reasoning checks**. https://aws.amazon.com/bedrock/security-privacy-responsible-ai/ | Yes, for the LLM explanation layer |
| **Amazon Neptune / Neptune Analytics** (+ GraphStorm GNN) | Active. The AWS blog covers graph-ML fraud detection. https://aws.amazon.com/blogs/database/use-graph-machine-learning-to-detect-fraud-with-amazon-neptune-analytics-and-graphstorm/ | Yes, for mule or scam-ring graphs |
| Guidance for Transactional Fraud Detection on AWS | Uses Timestream + Neptune. **Timestream for LiveAnalytics has been closed to new customers since 20 Jun 2025**; use Timestream for InfluxDB. https://docs.aws.amazon.com/solutions/transactional-fraud-detection-on-aws/ | Cite with that caveat |
| **Amazon Rekognition Face Liveness** | Active. Detects spoofs presented to the camera and attacks that bypass the camera, such as injection. https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness.html | Yes (deepfake track) |
| Rekognition Streaming Events, Batch Image Content Moderation | Maintenance from 30 Apr 2026 | Avoid |
| Amazon Comprehend: Prompt Safety Classification, Topic Modeling, Event Detection | Maintenance from 30 Apr 2026. https://aws.amazon.com/about-aws/whats-new/2026/03/aws-service-availability/ | Avoid (PII detection is still fine) |
| Amazon Kendra, Amazon Q Business, **Bedrock Agents Classic** | Moving to maintenance (Jun 2026 announcement). https://aws.amazon.com/about-aws/whats-new/2026/06/aws-service-availability/ | Avoid; use Bedrock Knowledge Bases or AgentCore |
| Amazon Pinpoint | Has an announced end-of-support date (May 2025 announcement). https://aws.amazon.com/about-aws/whats-new/2025/05/aws-service-changes/ | Use **AWS End User Messaging** (SMS/WhatsApp) for alerts |
| Amazon Chime SDK voice analytics (speaker search, voice tone) | **[UNVERIFIED current status]**. Chime SDK SIP Media Application moves to maintenance on 29 Oct 2026. | Don't depend on it |
| Amazon Mechanical Turk | End of support 29 Sep 2026 | Don't plan labelling on it |

---

## 4. What organisers and judges signal they care about (from public posts)

- ARIES's caption, "Pick a problem. Build your solution. Make an impact … Think. Build. Defend.", stresses **building** and **defending**. The 48h finale is a build-a-prototype round, so the Round 1 plan must be buildable.
- The Unstop description says "**specific, buildable, and safe**" and "substance over slide polish".
- LLF frames the event as Amazon CSR, naming deepfake scams, voice cloning fraud, and AI-driven financial fraud. This suggests social impact and protection of vulnerable users.
- The brief repeatedly stresses:
  - no auto-blocking on a single weak signal;
  - "a detector score alone is not an explanation or proof";
  - human review before high-impact action;
  - consent and data minimisation;
  - adversarial adaptation;
  - an India-specific scenario that a reviewer can grasp in under a minute.
- No posts name judges, Amazon mentors, or speakers. **[UNVERIFIED whether Amazon Trust & Safety, Amazon Pay, or AWS staff will judge]**
- DevClub social posts about RAKSHAM were **not found or not accessible**.

---

## 5. Open questions to email team.ariesiitd@gmail.com (before the deadline)
1. Which deadline is authoritative: 7 Oct (description), 9 Oct 00:00 IST (registration widget), or 10 Oct 00:23 IST (submission stage)?
2. Is there a PDF file-size limit or slide aspect ratio requirement?
3. Does the 3-page architecture limit include the appendix? Is the appendix limited in length?
4. Can a team of 1 participate, given the Unstop widget says 1–4 but the brief says 2–4?
5. Finale timing: is it 24 Oct 09:00 to 25 Oct 20:00? Will Amazon cloud credits or Bedrock access be provided?

---

## Notes on method
- Instagram, LinkedIn, Facebook, and X pages cannot be scraped with Firecrawl. Social-post text was reconstructed from search-engine snippets.
- Firecrawl rate limits (HTTP 429) cut off a few follow-up searches: more HackOn winner details and DevClub X posts.
- AWS statuses come from docs.aws.amazon.com and aws.amazon.com "What's New" via the AWS documentation tool.
