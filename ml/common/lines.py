"""Script lines from data/recording-kit/RECORDING_KIT.md (E01-E15 English, H01-H15 Hindi).

Hindi lines that change with the speaker's gender have a feminine variant (the kit tells female
speakers to switch verb forms). Generators read the variant that matches the speaker, so real and
cloned audio say the same words (content-matched comparison).
"""

EN = {
    "E01": "Hi Ma, I reached the hostel safely, I'll call you after dinner.",
    "E02": "Can you send me the electricity bill amount? I'll pay it on UPI tonight.",
    "E03": "The meeting is shifted to four thirty, please inform the rest of the team.",
    "E04": "I'm stuck in traffic near the metro station, start without me.",
    "E05": "Please check if the courier has arrived, the tracking says it was delivered.",
    "E06": "Papa, it's me. I've had an accident and the police have taken my phone.",
    "E07": "Please don't tell Mummy, just send fifty thousand rupees to this UPI ID right now.",
    "E08": "Hello, I'm calling from your bank's fraud department. Your account will be blocked today.",
    "E09": "Sir, to stop the transaction, please read out the six digit OTP you just received.",
    "E10": "This is Inspector Sharma from the cyber cell. You are under digital arrest, do not disconnect.",
    "E11": "Transfer the amount for verification; it will be refunded within one hour.",
    "E12": "My UPI ID is ravi dot kumar at the rate okaxis, and the amount is twelve thousand four hundred.",
    "E13": "The quick brown fox jumps over the lazy dog while the sun sets behind the hills.",
    "E14": "Account number ending four seven two nine, IFSC code S B I N zero zero one two three four.",
    "E15": "Thank you for calling, have a good evening, and please stay safe.",
}

HI_M = {
    "H01": "हाँ माँ, मैं ठीक से पहुँच गया हूँ, खाना खाकर फ़ोन करता हूँ।",
    "H02": "बिजली का बिल कितना आया है? मैं आज रात UPI से भर दूँगा।",
    "H03": "मीटिंग साढ़े चार बजे हो गई है, सबको बता देना।",
    "H04": "मैं मेट्रो स्टेशन के पास ट्रैफ़िक में फँसा हूँ, तुम लोग शुरू करो।",
    "H05": "पापा, मैं बोल रहा हूँ। मेरा एक्सीडेंट हो गया है और पुलिस ने मेरा फ़ोन ले लिया है।",
    "H06": "मम्मी को मत बताना, बस अभी इस UPI ID पर पचास हज़ार भेज दो।",
    "H07": "नमस्ते, मैं आपके बैंक के फ्रॉड डिपार्टमेंट से बोल रहा हूँ, आज आपका खाता बंद हो जाएगा।",
    "H08": "ट्रांज़ैक्शन रोकने के लिए अभी आया हुआ छह अंकों का OTP बताइए।",
    "H09": "मैं साइबर सेल से इंस्पेक्टर शर्मा बोल रहा हूँ, आप डिजिटल अरेस्ट में हैं, फ़ोन मत काटिए।",
    "H10": "वेरिफिकेशन के लिए पैसे भेजिए, एक घंटे में वापस आ जाएँगे।",
    "H11": "मेरी UPI ID है रवि डॉट कुमार एट द रेट ओकेएक्सिस, और रकम है बारह हज़ार चार सौ।",
    "H12": "खाता नंबर के आख़िरी अंक चार सात दो नौ हैं।",
    "H13": "कल सुबह दस बजे बैंक जाकर पासबुक अपडेट करवा लेना।",
    "H14": "आज बहुत गर्मी है, शाम को बारिश हो सकती है।",
    "H15": "फ़ोन करने के लिए धन्यवाद, अपना ध्यान रखना।",
}

HI_F = dict(HI_M)
HI_F.update({
    "H01": "हाँ माँ, मैं ठीक से पहुँच गई हूँ, खाना खाकर फ़ोन करती हूँ।",
    "H02": "बिजली का बिल कितना आया है? मैं आज रात UPI से भर दूँगी।",
    "H04": "मैं मेट्रो स्टेशन के पास ट्रैफ़िक में फँसी हूँ, तुम लोग शुरू करो।",
    "H05": "पापा, मैं बोल रही हूँ। मेरा एक्सीडेंट हो गया है और पुलिस ने मेरा फ़ोन ले लिया है।",
    "H07": "नमस्ते, मैं आपके बैंक के फ्रॉड डिपार्टमेंट से बोल रही हूँ, आज आपका खाता बंद हो जाएगा।",
    "H09": "मैं साइबर सेल से इंस्पेक्टर शर्मा बोल रही हूँ, आप डिजिटल अरेस्ट में हैं, फ़ोन मत काटिए।",
})

# Romanised Hindi (from the kit), useful for TTS engines that do better with Latin script
HI_ROMAN = {
    "H01": "Haan Maa, main theek se pahunch gaya hoon, khaana khaakar phone karta hoon.",
    "H02": "Bijli ka bill kitna aaya hai? Main aaj raat UPI se bhar doonga.",
    "H03": "Meeting saadhe chaar baje ho gayi hai, sabko bata dena.",
    "H04": "Main metro station ke paas traffic mein phansa hoon, tum log shuru karo.",
    "H05": "Papa, main bol raha hoon. Mera accident ho gaya hai aur police ne mera phone le liya hai.",
    "H06": "Mummy ko mat batana, bas abhi is UPI ID par pachaas hazaar bhej do.",
    "H07": "Namaste, main aapke bank ke fraud department se bol raha hoon, aaj aapka khaata band ho jaayega.",
    "H08": "Transaction rokne ke liye abhi aaya hua chhah ankon ka OTP bataiye.",
    "H09": "Main cyber cell se Inspector Sharma bol raha hoon, aap digital arrest mein hain, phone mat kaatiye.",
    "H10": "Verification ke liye paise bhejiye, ek ghante mein vaapas aa jaayenge.",
    "H11": "Meri UPI ID hai Ravi dot Kumar at the rate okaxis, aur rakam hai baarah hazaar chaar sau.",
    "H12": "Khaata number ke aakhiri ank chaar saat do nau hain.",
    "H13": "Kal subah das baje bank jaakar passbook update karva lena.",
    "H14": "Aaj bahut garmi hai, shaam ko baarish ho sakti hai.",
    "H15": "Phone karne ke liye dhanyavaad, apna dhyaan rakhna.",
}


def hindi_lines(gender: str = "m") -> dict:
    return HI_F if str(gender).lower().startswith("f") else HI_M


def all_lines(gender: str = "m") -> dict:
    """line_id -> (lang, text)"""
    out = {k: ("en", v) for k, v in EN.items()}
    out.update({k: ("hi", v) for k, v in hindi_lines(gender).items()})
    return out
