# Pehchaan voice recording kit

**Why we need this:** to test our voice-clone detector honestly, we clone *our own* voices (with consent) using several AI voice tools, then check whether the detector can tell the clone from the real person — in Indian languages and over real phone lines. Real recordings of you are the "genuine" side of that test. Most teams will only test on English academic datasets; this is our edge.

**Time needed:** about 12 minutes of speaking per person, plus one 3-minute phone call per pair.

**Before you start:** read and sign the consent form (`CONSENT_FORM.md`). No consent, no recording.

---

## How to record

- Quiet room. Turn off fans/AC near you, no music or TV.
- Use your phone's voice recorder (Voice Memos / Recorder app) or a laptop mic. Hold the phone about 15–20 cm from your mouth.
- Speak the way you would **on a phone call** — natural, not a slow "reading" voice. Different speeds and emotions are good; for the role-play lines, act it out.
- Leave a 1–2 second pause between lines. If you stumble, just say the line again.
- One file per section is fine. WAV is best; M4A/MP3 from a phone is OK.
- Female speakers: change the Hindi verb forms to feminine (गया → गई, करता → करती, बोल रहा → बोल रही).

## File names

Each person gets an ID: `S01`, `S02`, `S03`, `S04`. Name files like this:

| Section | File name |
|---|---|
| A. English lines | `S01_A_en.wav` |
| B. Hindi lines | `S01_B_hi.wav` |
| C. Mother-tongue lines | `S01_C_te.wav` (use a language code: te, ta, kn, ml, mr, bn, gu, pa, or, ur…) |
| D. Free speech | `S01_D_free.wav` |
| E. Phone call (pair) | `S01-S02_E_cellular.m4a` and `S01-S02_E_whatsapp.m4a` |

Put every file (and a photo or scan of each signed consent form) in
`D:\hackathons\amazon-raksham\data\raw\recordings\` on the build laptop. Don't post them in group chats or public drives. They are kept out of git.

---

## A. English (about 1.5 min)

Everyday call lines:

- **E01** Hi Ma, I reached the hostel safely, I'll call you after dinner.
- **E02** Can you send me the electricity bill amount? I'll pay it on UPI tonight.
- **E03** The meeting is shifted to four thirty, please inform the rest of the team.
- **E04** I'm stuck in traffic near the metro station, start without me.
- **E05** Please check if the courier has arrived, the tracking says it was delivered.

Scam role-play lines (fictional, act them out):

- **E06** Papa, it's me. I've had an accident and the police have taken my phone.
- **E07** Please don't tell Mummy, just send fifty thousand rupees to this UPI ID right now.
- **E08** Hello, I'm calling from your bank's fraud department. Your account will be blocked today.
- **E09** Sir, to stop the transaction, please read out the six digit OTP you just received.
- **E10** This is Inspector Sharma from the cyber cell. You are under digital arrest, do not disconnect.
- **E11** Transfer the amount for verification; it will be refunded within one hour.

Numbers and mixed sounds:

- **E12** My UPI ID is ravi dot kumar at the rate okaxis, and the amount is twelve thousand four hundred.
- **E13** The quick brown fox jumps over the lazy dog while the sun sets behind the hills.
- **E14** Account number ending four seven two nine, IFSC code S B I N zero zero one two three four.
- **E15** Thank you for calling, have a good evening, and please stay safe.

## B. Hindi (about 2 min)

- **H01** हाँ माँ, मैं ठीक से पहुँच गया हूँ, खाना खाकर फ़ोन करता हूँ।
  *Haan Maa, main theek se pahunch gaya hoon, khaana khaakar phone karta hoon.*
- **H02** बिजली का बिल कितना आया है? मैं आज रात UPI से भर दूँगा।
  *Bijli ka bill kitna aaya hai? Main aaj raat UPI se bhar doonga.*
- **H03** मीटिंग साढ़े चार बजे हो गई है, सबको बता देना।
  *Meeting saadhe chaar baje ho gayi hai, sabko bata dena.*
- **H04** मैं मेट्रो स्टेशन के पास ट्रैफ़िक में फँसा हूँ, तुम लोग शुरू करो।
  *Main metro station ke paas traffic mein phansa hoon, tum log shuru karo.*
- **H05** पापा, मैं बोल रहा हूँ। मेरा एक्सीडेंट हो गया है और पुलिस ने मेरा फ़ोन ले लिया है।
  *Papa, main bol raha hoon. Mera accident ho gaya hai aur police ne mera phone le liya hai.*
- **H06** मम्मी को मत बताना, बस अभी इस UPI ID पर पचास हज़ार भेज दो।
  *Mummy ko mat batana, bas abhi is UPI ID par pachaas hazaar bhej do.*
- **H07** नमस्ते, मैं आपके बैंक के फ्रॉड डिपार्टमेंट से बोल रहा हूँ, आज आपका खाता बंद हो जाएगा।
  *Namaste, main aapke bank ke fraud department se bol raha hoon, aaj aapka khaata band ho jaayega.*
- **H08** ट्रांज़ैक्शन रोकने के लिए अभी आया हुआ छह अंकों का OTP बताइए।
  *Transaction rokne ke liye abhi aaya hua chhah ankon ka OTP bataiye.*
- **H09** मैं साइबर सेल से इंस्पेक्टर शर्मा बोल रहा हूँ, आप डिजिटल अरेस्ट में हैं, फ़ोन मत काटिए।
  *Main cyber cell se Inspector Sharma bol raha hoon, aap digital arrest mein hain, phone mat kaatiye.*
- **H10** वेरिफिकेशन के लिए पैसे भेजिए, एक घंटे में वापस आ जाएँगे।
  *Verification ke liye paise bhejiye, ek ghante mein vaapas aa jaayenge.*
- **H11** मेरी UPI ID है रवि डॉट कुमार एट द रेट ओकेएक्सिस, और रकम है बारह हज़ार चार सौ।
  *Meri UPI ID hai Ravi dot Kumar at the rate okaxis, aur rakam hai baarah hazaar chaar sau.*
- **H12** खाता नंबर के आख़िरी अंक चार सात दो नौ हैं।
  *Khaata number ke aakhiri ank chaar saat do nau hain.*
- **H13** कल सुबह दस बजे बैंक जाकर पासबुक अपडेट करवा लेना।
  *Kal subah das baje bank jaakar passbook update karva lena.*
- **H14** आज बहुत गर्मी है, शाम को बारिश हो सकती है।
  *Aaj bahut garmi hai, shaam ko baarish ho sakti hai.*
- **H15** फ़ोन करने के लिए धन्यवाद, अपना ध्यान रखना।
  *Phone karne ke liye dhanyavaad, apna dhyaan rakhna.*

## C. Your mother tongue (about 1.5 min)

If your mother tongue is not Hindi or English, say **E01–E11** in it, the way you would naturally say them on a call. Don't translate word for word. Mixing in English words (as people really do) is fine. Start each line by saying its number ("E-zero-one…") so we can line them up later.

If Hindi is your mother tongue, skip this section, or do it in any other Indian language you speak well.

## D. Free speech (about 4 min)

Unscripted speech matters: AI voices mostly copy *read* speech, so real conversation is the hardest test. Use any language or a mix (Hinglish is great).

1. **About 1 min:** describe what you did yesterday, from morning to night.
2. **About 1 min:** explain to a friend how to make your favourite dish.
3. **About 2 min, in pairs:** role-play a phone call. One of you is a parent, the other is a student calling from the hostel about fees, an exam or travel plans. Keep it natural, no script.

## E. Real phone call (pairs, about 3 min each)

This gives us *genuine* speech after it has passed through a real phone network, so the detector can't cheat by learning "phone quality = fake".

1. Speaker A calls Speaker B on a **normal mobile call**. B records the call, either with the dialer's built-in call recorder or by putting the call on speaker and recording it on a second device.
2. A reads **E01–E05** and **H01–H05**, then you chat for about 1 minute.
3. Repeat the same thing as a **WhatsApp voice call**.
4. Swap roles if you have time.

Tell each other that the call is being recorded. Everyone on the call must have signed the consent form.

---

**Checklist before handing over:** signed consent form; sections A, B, D (and C if applicable); one cellular and one WhatsApp call per pair; files named correctly.
