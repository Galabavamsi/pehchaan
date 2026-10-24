# India voice-cloning and call-led payment fraud: evidence fact sheet (2025–2026)

Prepared 24 Oct 2026 for the Pehchaan finale deck (slide 2/3, "problem fit"). Builds on `research/india_fraud_stats_and_track02.md` (5 Oct 2026); everything below was re-opened in this pass unless marked "not re-opened".

Labels: **[P]** primary = government, regulator, court or Parliament text read on the official page. **[S]** secondary = media, vendor survey or op-ed. **[D]** = my arithmetic on cited numbers. **[U]** = unverified or conflicting; keep off slides.

## Q0. Do the deck's current citations still hold?

### Takeaway
All six citations check out against their sources, but two need wording fixes: the "76×" Chakshu ratio rounds up in our favour and is probably inflated by how Chakshu categories were introduced in 2024, and the "0.4 %" refund share is more precisely 0.37 %.

### Cited Findings
- **Chakshu, "Impersonation as a relative / friend": 258 (2024) → 19,564 (2025) → 1,201 (2026, to the reply date).** Total Chakshu reports: 2,08,224 (2024) → 5,19,662 (2025) → 42,855 (2026). Written reply by MoS Communications Dr Pemmasani Chandra Sekhar, Rajya Sabha, posted 5 Feb 2026. **[P]** — [PIB 2223779](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223779)
  - Same table: "Impersonation as Police, CBI, Customs, Aadhaar, RBI etc." 44,865 → 54,639. "Investment, Stock Market and Trading" 165 → 29,140. "Impersonation as DoT / TRAI" 217 → 15,595. **[P]** — same source.
  - The reply itself says Chakshu captures suspected communications "where a fraud was attempted but not actually committed"; losses go to I4C. **[P]** — same source.
  - Same reply: FRI-based fraud prevented "more than ₹1000 crores"; WhatsApp disengaged 28 lakh profiles; DIP has more than 1,200 organisations. **[P]** — same source.
- **NCRP FY2023-24 to FY2025-26:** more than 53,87,905 cyber-fraud complaints; more than 1,81,271 FIRs; more than **₹56,087 crore reported**; more than ₹9,079 crore lien-marked; **"amount refunded is more than ₹206 crores"**. MoS Home Bandi Sanjay Kumar, Rajya Sabha, posted 22 Jul 2026. **[P]** — [PIB 2287674](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287674)
  - Same reply: CFCFRMS "saved" more than ₹11,158 crore in more than 32.80 lakh complaints, till 30 Jun 2026 (cumulative since 2021; "saved" is a different measure from "refunded"). Suspect Registry: 30.48 lakh suspect identifiers and 32.08 lakh Layer-1 mule accounts shared, with **declined transactions worth ₹25,698 crore** (till 30 Jun 2026). Money Restoration Module live from April 2026. **[P]**
- **2025 losses ₹22,495 crore, 28.15 lakh complaints (22.68 lakh in 2024, +24 %), FIRs 55,484 (66,370 in 2024).** Investment fraud 76 % of value and 35 % of cases; digital arrest 9 % of value and 6 % of cases; sextortion 4 % of value and 19 % of cases. Data "sourced from the Ministry of Home Affairs". ThePrint, 21 Feb 2026. **[S]** — [ThePrint](https://theprint.in/india/cybercrime-saw-24-spike-in-2025-indians-lost-rs-22495-crore-mainly-in-investment-scams/2859930/)
  - The same ₹22,495 crore / 28.15 lakh / 76 % appears on pib.gov.in, but only as a NIELIT Kohima faculty member citing "figures from his presentation" at a PIB media workshop, 21 Aug 2026. It is not a ministry statement. **[S, hosted on PIB]** — [PIB 2301973](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2301973)
- **McAfee 2026 "State of the Scamiverse" (India release dated 5 Feb 2026):** verified. Details are under Q3. **[S, vendor]** — [McAfee India](https://www.mcafee.com/en-in/consumer-corporate/newsroom/press-releases/2026/20260204-1.html)
- **NPCI September 2026:** 24.07 bn UPI transactions worth ₹29.37 lakh crore (August: 24.51 bn / ₹29.82 lakh crore); +23 % YoY volume, +18 % YoY value. **[S, quoting NPCI]** — [MediaNama](https://www.medianama.com/2026/10/223-upi-transactions-september-value-slipped/); [DD News](https://ddnews.gov.in/en/upi-transactions-surge-23-to-24-07-billion-in-september-npci/). The exact 24,068.38 mn is on [NPCI product statistics](https://www.npci.org.in/product/upi/product-statistics) per the 5 Oct notes; not re-opened.
- **CERT-In Advisory CIAD-2024-0060, "Deepfakes – Threats and Countermeasures", 27 Nov 2024, Severity High.** **[P]** — [CERT-In](https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES02&VLCODE=CIAD-2024-0060)
  - It names "impersonating a loved one in distress" and impersonating "family members to request money transfers".
  - It recommends "callback procedures for sensitive transactions", which is Pehchaan's out-of-band check in CERT-In's own words.

### Inferences
- **The 76× ratio is the weak point.** 19,564 / 258 = 75.8× [D], so "76×" rounds up by 0.2 in our favour. More importantly, several categories jumped by similar or larger multiples in the same table (Investment 177×, DoT/TRAI 72×), while all Chakshu reports grew only 2.5× [D]. That pattern suggests the 2024 counts in these categories are small partly because of how or when they were introduced in a new portal, not only because the fraud was rarer. **Safer wording:** "19,564 citizen reports of relative/friend impersonation calls in 2025 (258 in 2024)", or "3.8 % of all 5,19,662 Chakshu reports in 2025" [D].
- **The refund share is 206 / 56,087 = 0.37 %** [D]. "0.4 %" is not in our favour (it overstates refunds), but 0.37 % is exact and keeps the "more than" qualifiers honest.

### Gaps
- PIB 2223779 does not say when each Chakshu category was introduced. Whether the 2024 base is artificially low is my inference, not a stated fact.
- I did not re-open the McAfee 2023 "Artificial Impostor" original. The 5 Oct notes cite it via Express Computer.

## Q1. Official 2025–2026 figures (I4C/NCRP, digital arrest, Chakshu/Sanchar Saathi, RBI, DoT FRI)

### Takeaway
On primary sources, India's call- and impersonation-led payment fraud runs to roughly ₹22,900 crore a year (2025). Victims authorise the payments themselves, and the money is almost never recovered: ₹206 crore refunded out of ₹56,087 crore reported over three financial years. RBI's own 2026 paper names "impersonation of family members" as a typical pattern. RBI bank-fraud tables are not a usable measure of these scams.

### Cited Findings
- **NCRP digital-payment frauds by year, as tabled by RBI:** 2021: 2.6 lakh / ₹551 cr. 2022: 6.9 lakh / ₹2,290 cr. 2023: 13.1 lakh / ₹7,465 cr. **2024: 24 lakh / ₹22,848 cr. 2025: 28 lakh / ₹22,931 cr.** RBI Discussion Paper "Exploring safeguards in digital payments to curb frauds", 9 Apr 2026. **[P]** — [RBI](https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23810)
- **Same RBI paper, direct quotes:**
  - On the mechanism: fraud happens "mostly through manipulation of users through social engineering, coercion, or impersonation. Victims, acting under deception, themselves initiate and authenticate transactions, leading to 'Authorised' Push-Payment (APP) frauds."
  - On tactics: fraudsters deploy "bogus call centres, deepfake-driven impersonation scams and mule account networks"; "vulnerable groups such as senior citizens have fallen prey".
  - On vulnerable customers: "Such frauds often involve impersonation of family members or the fabrication of urgent scenarios relating to medical, legal, or other emergencies."
  - On size of payments: per NCRP, transactions above ₹10,000 are **about 45 % of reported fraud cases by volume but about 98.5 % by value**, and **nearly 92 % of fraud value is above ₹50,000**.
  - Proposals: a 1-hour lag on APP transactions above ₹10,000, and trusted-person confirmation above ₹50,000, mandatory for citizens aged 70+ and persons with disabilities.
  - **[P]** — [RBI DP, 9 Apr 2026](https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23810)
- **NCRP cumulative, 2021–2025:** more than 65,89,201 financial-fraud complaints; more than ₹55,050 crore reported; more than ₹8,189 crore lien-marked; more than 1,95,760 FIRs. Lok Sabha reply, posted 21 Jul 2026. **[P]** — [PIB 2287039](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287039)
- **NCRB "Crime in India" 2024 (the latest published):** 1,01,928 cyber-crime cases registered (86,420 in 2023). The "Fraud" head rose from 19,466 (2023) to 29,758 (2024). **[P]** — [PIB 2287039](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287039). Growth: +17.9 % overall and +52.9 % for fraud [D].
- **Competing 2025 loss figure:** ₹19,813 crore across 21.77 lakh complaints, 77 % from investment schemes (I4C via Mint). McAfee's 2026 release cites it. **[S]** — [McAfee India](https://www.mcafee.com/en-in/consumer-corporate/newsroom/press-releases/2026/20260204-1.html), citing [Mint](https://www.livemint.com/news/india/529760000000-lost-to-cyber-frauds-in-india-in-6-years-says-report-shocking-numbers-explained-digital-arrest-mha-11767416448678.html). It probably used an earlier cut-off. It conflicts with ₹22,495 cr (ThePrint) and ₹22,931 cr (RBI).
- **Digital arrest: the figures conflict, so treat this whole block as [U] for 2025 counts.**
  - 2022: 39,925 cases / ₹91.14 crore. 2024: 1,23,672 cases / ₹1,935.51 crore. From a Rajya Sabha reply of Mar 2025, quoted by Frontline. **[S]** — [Frontline](https://frontline.thehindu.com/social-issues/ai-deepfake-digital-arrest-scams-india-cybercrime/article70587955.ece)
  - 2025: 6 % of cases and 9 % of value (MHA data via [ThePrint](https://theprint.in/india/cybercrime-saw-24-spike-in-2025-indians-lost-rs-22495-crore-mainly-in-investment-scams/2859930/)). That implies about 1.69 lakh cases and about ₹2,025 crore [D].
  - Against that: "more than 32,000 complaints related to digital arrest scams in 2025" per NCRP data, in an India Foundation fellow's op-ed (Firstpost, 31 May 2026). **[S, opinion]** — [Firstpost](https://www.firstpost.com/opinion/digital-arrest-scams-how-fear-is-robbing-indias-elderly-14017137.html)
  - The Supreme Court said on 3 Nov 2025 that more than ₹3,000 crore had been taken through digital arrests, from victims "mostly drawn from the elderly population". **[S, reporting the court's oral remarks]** — [The Hindu](https://www.thehindu.com/news/national/supreme-court-shocked-over-3000-crore-loss-in-digital-arrest-scams/article70235621.ece)
  - NHRC (10 Jun 2026): ₹52,976 crore lost to cyber-enabled fraud over six years, "nearly 8 %" linked to digital arrest, and "more than 3,000 digital arrest frauds targeting senior citizens" in 2025. **[S]** — [The Hindu](https://www.thehindu.com/sci-tech/technology/nhrc-flags-52976-crore-cyber-fraud-losses-seeks-urgent-action-against-digital-arrest-scams/article71081619.ece)
- **DoT / Sanchar Saathi (as on 15 Jul 2026):** 11.18 lakh citizen reports led to 50.90 lakh connections disconnected. More than 88 lakh connections were disconnected after failing re-verification (the ASTR AI tool). Posted 23 Jul 2026. **[P]** — [PIB 2288303](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2288303)
- **DoT Financial Fraud Risk Indicator (FRI):**
  - Prevented suspected fraud worth **₹5,043.73 crore by Aug 2026**: about ₹660 crore in the first six months after launch on 22 May 2025, and more than ₹2,000 crore in the four months from April 2026.
  - More than 1,600 organisations are on DIP. PhonePe uses "Very High" risk to decline transactions; Paytm and Google Pay are integrating it.
  - **[S]** — [ET Government, 10 Sep 2026](https://government.economictimes.indiatimes.com/news/digital-india/5043-crore-saved-how-india-is-building-a-real-time-defence-against-digital-fraud/133989749). The earlier official point was "more than ₹1000 crores" (PIB 2223779, 5 Feb 2026) **[P]**.
- **RBI Annual Report 2025-26** (frauds of ₹1 lakh and above): 10,114 cases / ₹48,021 crore in FY26. The "card, internet and digital payments" category was only **293 cases / ₹29 crore** (FY25: 13,332 / ₹517 cr; FY24: 28,836 / ₹1,452 cr). Advances were ₹40,774 crore. **[S]** — [ETBFSI, 30 May 2026](https://bfsi.economictimes.indiatimes.com/articles/surge-in-bank-fraud-rs-48021-crore-in-fy26-despite-decrease-in-cases-rbi-reports/131402703); RBI AR source: [rbi.org.in](https://www.rbi.org.in/Scripts/AnnualReportPublications.aspx?Id=1466)
- **State-level recovery gap (Madhya Pradesh):** citizens lost more than ₹1,054 crore to cyber fraud between 1 May 2021 and 13 Jul 2025, and only ₹1.94 crore (0.18 %) was returned. From the Home Department's Vidhan Sabha data, as reported by NDTV on 10 Jan 2026. **[S]** — [NDTV](https://www.ndtv.com/india-news/scamsters-use-ai-to-clone-cousins-voice-dupe-indore-teacher-of-rs-1-lakh-10604289)

### Inferences
- **For slides, use the RBI paper.** Its NCRP table (₹22,931 crore / 28 lakh in 2025) is the strongest primary loss figure: an RBI document tabling I4C data. It also comes with RBI's own description of the problem as authorised payments, family impersonation and senior citizens, which fits Pehchaan's thesis closely.
- **Never use the RBI Annual Report's digital-fraud count to size scams.** The collapse to 293 cases reflects reporting rules (₹1 lakh threshold, and only frauds concluded as frauds on the bank), not less fraud. Customer-authorised scams mostly fall outside it.
- **The 98.5 %-of-value figure supports Pehchaan's trigger design.** Almost all scam money moves in a small number of high-value authorised payments, so a payment-time check on risky payments covers most of the value without touching everyday UPI.

### Gaps
- No primary (PIB or sansad.in) 2025 digital-arrest count was found. Sources disagree (about 1.69 lakh implied vs "more than 32,000"). Keep 2025 digital-arrest counts off slides.
- No official figure was found for losses from AI voice-cloned calls specifically. NCRP, Chakshu and RBI publish no "voice clone" category. Chakshu's "relative / friend impersonation" is the closest official proxy.
- The MeitY IT Rules amendment FAQ (2026), which lists "an AI-generated audio clip cloning the voice of an individual" as deceptive impersonation, showed up in search ([MeitY PDF](https://www.meity.gov.in/static/uploads/2025/10/065b6deb585441b5ccdf8be42502a49c.pdf)) but was not opened. Its notification date is unverified.

## Q2. Documented Indian AI voice-clone relative/official scams, 2025–2026

### Takeaway
There are a handful of well-documented 2026 cases with police on record. They share the pattern Pehchaan targets: an urgent call from a "known" voice, then several quick UPI/QR or bank transfers within the same call or the same hour. Most cases are small (₹1–2 lakh), and police usually say AI was "strongly indicated" rather than forensically proven.

### Cited Findings
- **Indore, Madhya Pradesh: incident 6 Jan 2026, reported 10 Jan 2026.**
  - A schoolteacher got a night-time call from a number resembling her cousin's. The caller, in her cousin's voice, said a friend needed heart surgery and sent QR codes.
  - She paid **₹97,500 in four transactions (3 × ₹30,000 + ₹7,500)**. The number was then blocked. FIR at Lasudia police station.
  - Additional DCP (Crime) Rajesh Dandotiya: "The voice was exactly like her cousin's." Police called it possibly MP's "first confirmed case of AI-driven voice-modulation cyber fraud."
  - **[S]** — [NDTV](https://www.ndtv.com/india-news/scamsters-use-ai-to-clone-cousins-voice-dupe-indore-teacher-of-rs-1-lakh-10604289)
- **Kolkata (Beleghata), reported 19 Aug 2026.** A 67-year-old man lost **₹95,990** in several online bank transfers, **within less than an hour**, to a caller using an AI-cloned voice of an acquaintance, "Ajoy", who claimed a medical emergency. Beleghata PS is investigating via CDRs and beneficiary accounts. Police advised calling back on a known number. **[S]** — [Times of India](https://timesofindia.indiatimes.com/city/kolkata/man-loses-rs-95k-to-ai-voice-scam/articleshow/133331043.cms)
- **Delhi Police arrest five, reported 17 Jun 2026.** The gang allegedly cloned a Mumbai company MD's voice with AI and induced the firm's Deputy GM to transfer **more than ₹10 crore**, routed into **63 bank accounts**. They were caught trying to encash a ₹9 lakh cheque in Sarita Vihar. This is corporate "CEO fraud", not a relative scam. **[S]** — [India Today](https://www.indiatoday.in/cities/delhi/story/ai-voice-cloning-fraud-delhi-police-arrest-five-rs-10-crore-mumbai-company-scam-2928485-2026-06-17)
- **Hyderabad, 18 Mar 2025.** A homemaker was duped of ₹1.97 lakh. Police said scammers "could have used AI-generated voice technology" to mimic her sister-in-law. **[S]** — [The Hindu](https://www.thehindu.com/news/national/telangana/homemaker-duped-of-197-lakh-in-ai-voice-scam/article69344422.ece) (already on the deck)
- **Delhi, 19 Feb 2026 (weak sourcing).** A 65-year-old woman was reportedly duped of ₹2 lakh by a cloned "daughter" voice in a fake-kidnapping call; payment by UPI/bank transfer. No police station, FIR or named official is given. **[S, low-reliability outlet; treat as U]** — [The420.in](https://the420.in/ai-voice-clone-scam-delhi-elderly-woman-kidnapping-fraud/)
- **Digital-arrest cases with elderly victims** (impersonating officials, mostly by video call):
  - Om Taneja (81) and his wife (77) lost ₹14.85 crore, Delhi, Jan 2026.
  - An 82-year-old petitioner lost ₹22.92 crore, described as the largest individual digital-arrest case.
  - Frontline reports that AI deepfakes are used in these scams. **[S]** — [Frontline](https://frontline.thehindu.com/social-issues/ai-deepfake-digital-arrest-scams-india-cybercrime/article70587955.ece)

### Inferences
- **The Indore case is the best single story for a slide.** It is recent, a senior police officer is on record, the voice is a relative's, and the payment is UPI via QR, split into four transfers in one evening. That is exactly the "who asked you to pay?" moment.
- In both 2026 relative/acquaintance cases, the victim finds out by calling the real person back afterwards. That is the check Pehchaan moves to before the payment (Family Verify / callback), and the check CERT-In recommends.

### Gaps
- No court judgment or chargesheet was found that establishes forensically that a cloned voice was used in an Indian relative scam. Police attributions are "indicates" or "could have".
- The Indian Express case (23 May 2025) already on the deck was not re-opened in this pass.
- I found no published count of AI voice-clone FIRs for any state or the nation.

## Q3. Can Indians tell cloned voices from real ones? Are gangs adopting voice AI?

### Takeaway
Surveys say exposure is widespread (1 in 5 Indians report meeting a voice-clone scam). Peer-reviewed lab work shows listeners rate clones as about as "real" as human recordings. Police across India now issue specific AI voice-cloning advisories, but no agency publishes adoption numbers.

### Cited Findings
- **McAfee 2026 State of the Scamiverse (India release, 5 Feb 2026)** **[S, vendor]** — [McAfee India](https://www.mcafee.com/en-in/consumer-corporate/newsroom/press-releases/2026/20260204-1.html):
  - **"1 in 5 Indians say they've encountered a voice-clone scam"**, often impersonating "loved ones, bank agents or government officials".
  - More than 1 in 3 are not confident they can identify a deepfake scam. Indians see on average 4 deepfakes a day.
  - 51 % report losing money to a scam, with an average loss of **₹93,915**.
  - Among people harmed, **the typical scam unfolded in 30 minutes or less**.
  - Method: online survey in Nov 2025 of 7,592 adults across 7 countries; the India sample size is not stated.
- **McAfee 2023 "Artificial Impostor" (India):**
  - 47 % have experienced, or know someone who experienced, an AI voice scam (global 25 %); 83 % of Indian victims lost money.
  - **69 % think they don't know or cannot tell the difference between an AI voice and a real voice.**
  - **[S, vendor, 2023; not re-opened]** — [Express Computer](https://www.expresscomputer.in/artificial-intelligence-ai/47-of-indians-have-experienced-ai-voice-scams/97359/)
- **Lavan, Irvine, Rosi & McGettigan, "Voice clones sound realistic but not (yet) hyperrealistic", PLOS One 2025** (QMUL release, 21 Oct 2025). **[peer-reviewed; UK listeners, not India]** — [PLOS One](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0332692); [QMUL](https://www.qmul.ac.uk/news/latest-news/2025/science-and-engineering/se/ai-generated-voices-now-indistinguishable-from-real-human-voices.html)
  - Voice clones were rated about as real as human voices: mean realness 63.0 vs 63.8, p = .682, and 56.6 vs 57.6 in Experiment 1b.
  - Listeners were biased towards labelling clones as human.
  - The authors caveat that clones may be less convincing to listeners who know the speaker well.
  - The paper cites Barrington, Cooper & Farid (2025), "People are poorly equipped to detect AI-powered voice clones", *Scientific Reports* 15:11004 (not opened).
- **Police advisories:**
  - **J&K Police, Cyber Police Station Srinagar (Dainik Jagran, Hindi, 2 Oct 2026):** cyber criminals use AI to imitate a person's voice and make fake calls or audio messages in the names of relatives, friends, employees or officers. Hearing a familiar voice, once a basic proof of identity, is now challenged by voice cloning. **[S]** — [Jagran](https://www.jagran.com/jammu-and-kashmir/srinagar-jk-police-alert-beware-of-ai-voice-cloning-scams-40391941.html)
  - Similar Hindi-language advisories appear on Himachal Pradesh Police, Rajasthan Police, Chhattisgarh Police and Delhi Police ("Cyber Pulse") social channels, and in an I4C CyberDost reel. These were seen only as search snippets. **[S, not opened]**
- **Official awareness messaging:** at a PIB Kohima media workshop (21 Aug 2026), a NIELIT expert listed "AI voice-cloning frauds" next to digital arrest and investment scams. **[S, on PIB]** — [PIB 2301973](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2301973)

### Inferences
- **The evidence supports "verify the person, not the voice".** Lab results show clones are as believable as real voices to unfamiliar listeners. The police message is "don't trust the voice; call back". The detector stays a supporting clue, consistent with guardrail G2.
- The PLOS caveat that familiar listeners may do better is honest to mention. It does not rescue the victim in practice: scam calls are short, emotional and often "bad line" calls.

### Gaps
- No 2025–2026 India-specific study measuring detection accuracy (a listening test) for cloned voices was found. McAfee 2023's 69 % is self-reported and three years old.
- No LocalCircles, Norton or Truecaller 2025–2026 India survey specifically on voice cloning was found in this pass.
- No law-enforcement statement gives a number for AI voice-tool adoption by gangs: no share of cases and no seized-tool counts.

## Q4. What share of payment fraud happens during, or within minutes of, a call?

### Takeaway
No Indian agency publishes a "paid while on the call" share. The available evidence is indirect but consistent: victims authorise the payments themselves under deception (RBI), scams complete in about 30 minutes (McAfee), fraud calls and sessions are getting shorter (BioCatch India), and in documented cases the transfers happen within the call or the hour.

### Cited Findings
- **RBI DP (9 Apr 2026):** victims "themselves initiate and authenticate transactions". A short delay "can act as a preventive control by disrupting the fraudster's psychological influence over the victim". **[P]** — [RBI](https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23810)
- **McAfee 2026:** "Among people harmed by a scam, the typical scam unfolded in just 30 minutes or less." **[S, vendor]** — [McAfee India](https://www.mcafee.com/en-in/consumer-corporate/newsroom/press-releases/2026/20260204-1.html)
- **BioCatch "2026 Digital Banking Fraud Trends in India" (press release, Mumbai, 22 Jul 2026)**, based on its Indian bank customers' data: **average call length fell 31 %** and **median fraud session length fell 32 %**; attempted fraud payment value rose 35 %; mobile fraud sessions rose 67 %; text-message scams rose 146 % (H2 2025 + H1 2026 vs the year before). **[S, vendor]** — [BioCatch PR](https://www.biocatch.com/press-release/indian-banks-see-146-spike-in-text-message-based-scams); [report page](https://www.biocatch.com/2026-digital-banking-fraud-trends-in-india)
- **Cases:** Indore (four QR payments in the same evening as the call; [NDTV](https://www.ndtv.com/india-news/scamsters-use-ai-to-clone-cousins-voice-dupe-indore-teacher-of-rs-1-lakh-10604289)). Kolkata (transfers "within less than an hour"; [TOI](https://timesofindia.indiatimes.com/city/kolkata/man-loses-rs-95k-to-ai-voice-scam/articleshow/133331043.cms)). **[S]**
- **Google** runs an India pilot of in-call scam protection with financial apps. When a user opens a participating finance app while screen-sharing on a call with an unsaved number, Android warns them, offers one-tap "end call", and imposes a 30-second wait. **[S, vendor]** — [Google blog](https://blog.google/security/android-expands-pilot-in-call-scam-protection-financial-apps/). No India outcome numbers were published.

### Inferences
- **The "during or right after a call" window is where the money moves.** That supports Pehchaan's trigger (a risky payment during or after a call) and argues against after-the-fact recovery: only ₹206 crore refunded vs ₹56,087 crore reported (PIB 2287674).
- **Shorter fraud calls (−31 %) narrow the window for any in-call detector.** That favours a payment-time check over relying on detecting the call itself.

### Gaps
- **No official or published Indian figure for the share of fraud payments made during a live call, or within N minutes of one.** NCRP, RBI and NPCI publish none. BioCatch's full report (gated) may contain an "active call during session" rate; I could not access it.
- No India results from Google's pilot.

## Q5. Regional language and elderly angle

### Takeaway
Elderly people are disproportionately targeted and lose large sums. Police in Hyderabad and Pune report ₹100 crore or more in senior-citizen losses over 19 months in each city, and RBI proposes mandatory protection for people aged 70+. On language, police advisories are now issued in Hindi and other languages, but there is no quantitative data on the languages scam calls use.

### Cited Findings
- **Hyderabad Cyber Crime Police (The Hindu, 9 Aug 2026):** senior citizens lost **₹102.02 crore in 403 cases over 19 months** (2025: 285 cases / ₹71.81 crore; 2026 to 31 Jul: 118 cases / ₹30.20 crore). By type: trading 113 cases / ₹55.88 crore; digital arrest 69 / ₹31.93 crore; OTP 115 / ₹4.94 crore. **[S, police data]** — [The Hindu](https://www.thehindu.com/news/national/telangana/senior-citizens-lose-102-crore-to-cyber-fraud-in-19-months-in-hyderabad-say-police/article71324536.ece)
- **Pune cyber police (Times of India, 2026):** senior citizens lost about **₹100 crore in 136 digital-arrest cases over 19 months**; in 2025, 85 cases and ₹53.52 crore. Examples include an 82-year-old who lost ₹10.75 crore (Jan 2026) and an 87-year-old who lost ₹3.46 crore (May 2026). **[S, police data]** — [TOI](https://timesofindia.indiatimes.com/city/pune/senior-citizens-collectively-lose-100-crore-in-136-digital-arrest-cases-over-19-months/articleshow/134373902.cms). The exact publication date was not captured; it is likely Sep–Oct 2026.
- **NHRC (10 Jun 2026):** "more than 3,000 digital arrest frauds targeting senior citizens" in 2025. **[S]** — [The Hindu](https://www.thehindu.com/sci-tech/technology/nhrc-flags-52976-crore-cyber-fraud-losses-seeks-urgent-action-against-digital-arrest-scams/article71081619.ece)
- **Supreme Court (3 Nov 2025):** more than ₹3,000 crore lost to digital arrests, victims mostly elderly. **[S]** — [The Hindu](https://www.thehindu.com/news/national/supreme-court-shocked-over-3000-crore-loss-in-digital-arrest-scams/article70235621.ece)
- **RBI DP (9 Apr 2026):** proposes trusted-person confirmation above ₹50,000, mandatory for citizens aged 70+. It states that frauds against vulnerable groups "often involve impersonation of family members" and "frequently result in disproportionately higher financial losses". **[P]** — [RBI](https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23810)
- **Language:** J&K Police issued its AI voice-cloning advisory in Hindi via Dainik Jagran (2 Oct 2026). Multiple state police forces and I4C CyberDost post Hindi voice-clone warnings. **[S]** — [Jagran](https://www.jagran.com/jammu-and-kashmir/srinagar-jk-police-alert-beware-of-ai-voice-cloning-scams-40391941.html)

### Inferences
- RBI's 70+ trusted-person proposal is regulatory validation of Family Verify: a second, known person confirms a high-value payment. Pehchaan does this only when a call-linked risk is present, not on every payment above ₹50,000.
- A regional-language demo (Hindi and Telugu, as the repo already supports) matches how police are communicating this threat. There is no hard number to put on a slide.

### Gaps
- No data on the language mix of scam calls (Hindi vs regional) was found from any official or survey source.
- No national figure on the share of cyber-fraud losses borne by senior citizens. City-level police data only (Hyderabad, Pune).

## Q6. Shortlist: the 6–8 numbers best suited for slide 2/3

### Takeaway
Lead with primary numbers that tie together call, impersonation, authorised payment and no recovery. Use surveys and cases as colour, labelled as such.

### Cited Findings
1. **19,564** Chakshu reports of "impersonation as a relative / friend" in 2025 (258 in 2024). DoT, Rajya Sabha written reply, 5 Feb 2026. **Primary.** — [PIB 2223779](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2223779)
   - Wording: "19,564 reports of fake-relative calls in 2025 (258 in 2024)". Avoid "76×"; if a ratio is wanted, use "75.8×" and footnote that these are reported attempts, not losses.
2. **₹22,931 crore** lost across **28 lakh** NCRP digital-payment frauds in 2025 (₹22,848 crore / 24 lakh in 2024). RBI Discussion Paper, 9 Apr 2026, citing NCRP. **Primary.** — [RBI](https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23810)
   - This could replace the current ₹22,495 cr / 28.15 lakh (ThePrint), which is secondary.
3. **₹206 crore refunded of ₹56,087 crore reported (0.37 %)**, FY2023-24 to FY2025-26 (both "more than"). MHA, Rajya Sabha reply, 22 Jul 2026. **Primary.** — [PIB 2287674](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287674)
4. **98.5 % of reported fraud value is in transactions above ₹10,000** (only 45 % of cases), and about 92 % above ₹50,000. RBI DP, 9 Apr 2026, citing NCRP. **Primary.** — [RBI](https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=23810)
   - Pair it with RBI's line that these frauds "often involve impersonation of family members" and that victims "themselves initiate and authenticate" payments.
5. **1 in 5 Indians** say they've encountered a voice-clone scam, and **the typical scam unfolded in 30 minutes or less**. McAfee 2026 State of the Scamiverse, India release 5 Feb 2026 (survey Nov 2025, n = 7,592 across 7 countries). **Secondary (vendor survey).** — [McAfee India](https://www.mcafee.com/en-in/consumer-corporate/newsroom/press-releases/2026/20260204-1.html)
6. **Voice clones rated as real as human voices** (mean realness 63.0 vs 63.8, p = .682). Lavan et al., PLOS One 2025. **Peer-reviewed (UK sample, not India).** — [PLOS One](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0332692)
   - Use it to justify "verify the person, not the voice". Note in the speaker notes that familiar listeners may do better.
7. **₹102.02 crore** lost by senior citizens in **403 cases in 19 months**, Hyderabad alone (Jan 2025–Jul 2026). Hyderabad Cyber Crime Police via The Hindu, 9 Aug 2026. **Secondary (police data).** — [The Hindu](https://www.thehindu.com/news/national/telangana/senior-citizens-lose-102-crore-to-cyber-fraud-in-19-months-in-hyderabad-say-police/article71324536.ece)
   - Alternative: the RBI proposal of mandatory trusted-person confirmation for people aged 70+ **[P]**.
8. **Case:** Indore, 6 Jan 2026. Cousin's cloned voice; **₹97,500 in four QR/UPI payments in one evening**; ADCP (Crime): "The voice was exactly like her cousin's." NDTV, 10 Jan 2026. **Secondary.** — [NDTV](https://www.ndtv.com/india-news/scamsters-use-ai-to-clone-cousins-voice-dupe-indore-teacher-of-rs-1-lakh-10604289)

Supporting, for a "why now / ecosystem" slide rather than the problem slide:
- **CERT-In CIAD-2024-0060** (27 Nov 2024, Severity High) recommends "callback procedures for sensitive transactions". **Primary.** — [CERT-In](https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES02&VLCODE=CIAD-2024-0060)
- **DoT FRI: ₹5,043.73 crore** of suspected fraud prevented by Aug 2026. **Secondary.** — [ET Government](https://government.economictimes.indiatimes.com/news/digital-india/5043-crore-saved-how-india-is-building-a-real-time-defence-against-digital-fraud/133989749)
- **Suspect Registry declined ₹25,698 crore** of transactions (to 30 Jun 2026). **Primary.** — [PIB 2287674](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2287674)
- **UPI: 24.07 bn transactions, ₹29.37 lakh crore** in Sep 2026. NPCI via MediaNama / DD News. — [MediaNama](https://www.medianama.com/2026/10/223-upi-transactions-september-value-slipped/)

### Inferences
- Numbers 1–4 are all primary and tell the whole story on their own: fake-relative calls are reported at scale; the money is large, high-value and authorised by the victim; and recovery is about 0.4 % or less.
- Numbers 5–8 add the voice-clone and human angle, each clearly labelled as survey, lab or case evidence.
- Per CLAUDE.md, every slide number must trace to `ml/results/metrics.json`, `ml/realcall/FINDINGS.md` or `engine/results/deck_numbers.json`. Any of these that go on a slide need adding to `engine/results/deck_numbers.json`, or a sources note, with these citations.

### Gaps
- None of the shortlisted numbers measures AI voice-clone losses directly. India publishes no such figure. Say so on the slide ("India does not yet count voice-clone fraud separately; the closest official proxy is…"), rather than implying one exists.
