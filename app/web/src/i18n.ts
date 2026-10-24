import { createContext, useContext } from "react";
import type { Bi, Lang } from "./api";

// UI copy. Calm, plain, sentence case. Never accusatory (G6).
const S = {
  protected: ["Protected by Pehchaan", "पहचान से सुरक्षित"],
  paying: ["Paying", "पैसे भेज रहे हैं"],
  new_payee: ["First time paying", "पहली बार भेज रहे हैं"],
  add_note: ["Add a note", "नोट जोड़ें"],
  from_acct: ["From", "खाते से"],
  pay: ["Pay", "भेजें"],
  on_call: ["On a call", "कॉल चालू है"],
  unknown_number: ["Not in contacts", "सेव नहीं है"],
  whatsapp_call: ["WhatsApp call", "WhatsApp कॉल"],
  phone_call: ["Phone call", "फ़ोन कॉल"],
  call_ended_ago: ["Call ended {min} min ago", "कॉल {min} मिनट पहले ख़त्म हुई"],
  checking: ["Checking…", "जाँच हो रही है…"],
  who_asked: ["Who asked you to make this payment?", "ये पेमेंट करने को आपसे किसने कहा?"],
  who_sub: ["You are paying {amount} to {payee} during a call. Your answer stays private.",
            "आप कॉल के दौरान {payee} को {amount} भेज रहे हैं। आपका जवाब किसी और को नहीं दिखेगा।"],
  who_sub_after: ["You are paying {amount} to {payee} soon after a call. Your answer stays private.",
                  "आप कॉल के कुछ देर बाद {payee} को {amount} भेज रहे हैं। आपका जवाब किसी और को नहीं दिखेगा।"],
  opt_family: ["Family member", "परिवार का सदस्य"], opt_family_s: ["Son, daughter or a relative", "बेटा, बेटी या कोई रिश्तेदार"],
  opt_bank: ["My bank", "मेरा बैंक"], opt_bank_s: ["Someone said they are from your bank", "किसी ने कहा कि वो आपके बैंक से हैं"],
  opt_upi: ["UPI app, shop or delivery", "UPI ऐप, दुकान या डिलीवरी"], opt_upi_s: ["A payments app, a shop or a delivery person", "कोई पेमेंट ऐप, दुकान या डिलीवरी वाला"],
  which_bank: ["Which bank did they say they are from?", "उन्होंने कौन-सा बैंक बताया?"],
  bank_yours: ["Your account is with this bank", "आपका खाता इसी बैंक में है"],
  bank_other_s: ["Any other bank", "कोई भी दूसरा बैंक"],
  cl_title: ["Three quick questions about the call", "कॉल के बारे में तीन छोटे सवाल"],
  cl_sub: ["Tap any that happened. This helps us check the right thing.", "जो हुआ हो, उसे दबाएँ। इससे हम सही चीज़ जाँच पाएँगे।"],
  cl_secrecy: ["They asked me to keep it secret", "उन्होंने बात छिपाने को कहा"],
  cl_otp: ["They asked for an OTP or PIN", "उन्होंने OTP या PIN माँगा"],
  cl_arrest: ["They said someone could be arrested", "उन्होंने किसी की गिरफ़्तारी की बात कही"],
  cl_remote: ["They asked me to install an app or share my screen", "उन्होंने कोई ऐप डालने या स्क्रीन शेयर करने को कहा"],
  cl_refund: ["They said I must pay to get a refund or to verify", "उन्होंने कहा कि रिफ़ंड या वेरिफ़िकेशन के लिए पैसे भेजने होंगे"],
  cl_none: ["None of these", "इनमें से कुछ नहीं"],
  cl_done: ["Done", "हो गया"],
  cancel_safer: ["Cancel is the safer choice: what you heard on the call did not match.", "रद्द करना ही सुरक्षित है: कॉल पर जो सुना, वो मेल नहीं खाता।"],
  opt_authority: ["Police, CBI or Govt", "पुलिस, CBI या सरकार"], opt_authority_s: ["An officer, court or department", "कोई अफ़सर, अदालत या विभाग"],
  opt_other: ["Someone else", "कोई और"], opt_other_s: ["A friend, neighbour or anyone else", "दोस्त, पड़ोसी या कोई और"],
  opt_none: ["No one", "किसी ने नहीं"], opt_none_s: ["I decided to pay on my own", "मैंने खुद भेजने का फ़ैसला किया"],
  which_family: ["Who in your family?", "परिवार में कौन?"],
  someone_else_family: ["Someone else in the family", "परिवार में कोई और"],
  amber_brand: ["Ruko, pehle pehchaan karo", "रुको, पहले पहचान करो"],
  amber_sub: ["Pause and check who is really asking", "रुकें और पक्का करें कि असल में कौन माँग रहा है"],
  we_noticed: ["What we noticed", "हमने क्या देखा"],
  check_really: ["Check it's really {name}", "पक्का करें कि ये सच में {name} हैं"],
  check_bank: ["Check it's really your bank", "पक्का करें कि ये सच में आपका बैंक है"],
  check_generic: ["Check before you pay", "भेजने से पहले जाँच लें"],
  continue_in: ["Continue anyway ({s})", "फिर भी आगे बढ़ें ({s})"],
  continue: ["Continue anyway", "फिर भी आगे बढ़ें"],
  cancel_payment: ["Cancel payment", "पेमेंट रद्द करें"],
  waiting_for: ["Waiting for {name}", "{name} के जवाब का इंतज़ार"],
  waiting_sub: ["We sent a private question to {name}'s phone. Only that phone can answer it.",
                "हमने {name} के फ़ोन पर एक निजी सवाल भेजा है। जवाब सिर्फ़ वही फ़ोन दे सकता है।"],
  fv_sent: ["Question sent", "सवाल भेजा गया"],
  fv_auto_title: ["We've asked {name} to confirm on {their} own phone", "हमने {name} से उनके अपने फ़ोन पर पक्का करने को कहा है"],
  fv_auto_sub: ["Only {name}'s own phone can answer. You don't need to do anything.",
                "जवाब सिर्फ़ {name} का अपना फ़ोन दे सकता है। आपको कुछ नहीं करना है।"],
  fv_cancel_request: ["Cancel request", "अनुरोध रद्द करें"],
  fv_signed: ["Answer will be signed by their phone", "जवाब उनके फ़ोन से साइन होगा"],
  fv_left: ["left to answer", "जवाब देने का समय बचा"],
  call_instead: ["Call {name}'s saved number instead", "इसके बजाय {name} के सेव किए नंबर पर कॉल करें"],
  hold_title: ["We've paused this payment for 30 minutes", "हमने ये पेमेंट 30 मिनट के लिए रोक दिया है"],
  hold_not_sent: ["Your {amount} has not been sent.", "आपके {amount} नहीं भेजे गए हैं।"],
  hold_left: ["minutes left on hold", "मिनट की रोक बाकी"],
  why_paused: ["Why we paused", "हमने क्यों रोका"],
  more_noticed: ["Also noticed", "और क्या देखा"],
  hold_auto: ["When the 30 minutes end, we will not send the money on our own. You decide.",
              "30 मिनट पूरे होने पर भी हम अपने-आप पैसे नहीं भेजेंगे। फ़ैसला आपका होगा।"],
  cancel_report: ["Cancel and report", "रद्द करें और शिकायत करें"],
  talk_person: ["Talk to a person at your bank", "अपने बैंक के किसी व्यक्ति से बात करें"],
  talk_person_s: ["{bank}'s safety desk calls you back", "{bank} की सुरक्षा टीम आपको वापस कॉल करेगी"],
  rel_helper: ["If you did not call {payer}, tap No. The money stays in {payer}'s account.", "अगर आपने {payer} को कॉल नहीं किया, तो 'नहीं' दबाएँ। पैसे {payer} के खाते में ही रहेंगे।"],
  release_early: ["Release early", "रोक जल्दी हटाएँ"],
  release_review: ["A bank officer reviews payments of ₹50,000 or more first", "₹50,000 या ज़्यादा पर पहले बैंक अधिकारी जाँच करते हैं"],
  release_check: ["Possible after a successful check with the real person", "असली व्यक्ति से पुष्टि होने के बाद संभव"],
  release_requested: ["Request sent. A bank officer will call you.", "अनुरोध भेज दिया गया। बैंक अधिकारी आपको कॉल करेंगे।"],
  answered_from: ["Answered from {name}'s own phone · signature checked", "{name} के अपने फ़ोन से जवाब · हस्ताक्षर जाँचा गया"],
  coached: ["If someone on the call is telling you what to tap, that is a warning sign. It is okay to hang up.",
            "अगर कॉल पर कोई आपको बता रहा है कि क्या दबाना है, तो ये खतरे का संकेत है। फ़ोन काट देना बिल्कुल ठीक है।"],
  green_title: ["You're good to go", "आप पेमेंट कर सकते हैं"],
  pay_now: ["Pay {amount}", "{amount} भेजें"],
  enter_pin: ["Enter UPI PIN", "UPI PIN डालें"],
  sent_title: ["{amount} sent", "{amount} भेज दिए गए"],
  sent_to: ["to {payee}", "{payee} को"],
  done: ["Done", "ठीक है"],
  cancelled_title: ["Payment cancelled", "पेमेंट रद्द हो गया"],
  cancelled_sub: ["Your money is safe in your account.", "आपके पैसे आपके खाते में सुरक्षित हैं।"],
  report_this: ["Report this", "इसकी शिकायत करें"],
  report_ready: ["Your report is ready", "आपकी शिकायत तैयार है"],
  report_sub: ["Everything is filled in from this payment. You review it and decide where to send it.",
               "इस पेमेंट की सारी जानकारी भर दी गई है। आप देखकर तय करें कि इसे कहाँ भेजना है।"],
  call_1930: ["Call 1930", "1930 पर कॉल करें"], call_1930_s: ["National cyber helpline, 24×7", "राष्ट्रीय साइबर हेल्पलाइन, 24×7"],
  ncrp: ["cybercrime.gov.in", "cybercrime.gov.in"], ncrp_s: ["Complaint form filled in for you", "शिकायत फ़ॉर्म भरा हुआ है"],
  chakshu: ["Chakshu", "चक्षु"], chakshu_s: ["Sanchar Saathi: report the caller's number", "संचार साथी: कॉल करने वाले नंबर की रिपोर्ट"],
  noticed_before: ["Why you saw a check", "आपको जाँच क्यों दिखी"],
  bank_told: ["{bank}'s safety team has a copy", "{bank} की सुरक्षा टीम के पास कॉपी है"],
  signed_pack: ["Signed and sealed", "साइन और सील किया गया"],
  no_recording: ["No call recording is included. Nothing is sent until you choose.", "इसमें कॉल की रिकॉर्डिंग नहीं है। आपके चुनने तक कुछ नहीं भेजा जाता।"],
  download_pdf: ["Download PDF", "PDF डाउनलोड करें"],
  open_form: ["Open form", "फ़ॉर्म खोलें"],
  voice_title: ["Check the caller's voice", "कॉल करने वाले की आवाज़ जाँचें"],
  voice_sub: ["One clue, not proof. Asking the real person is always stronger.", "ये सिर्फ़ एक संकेत है, सबूत नहीं। असली व्यक्ति से पूछना हमेशा बेहतर है।"],
  voice_step1: ["Put the call on speaker", "कॉल को स्पीकर पर रखें"],
  voice_step2: ["Hold your phone near the speaker for 10 seconds", "फ़ोन को 10 सेकंड स्पीकर के पास रखें"],
  voice_step3: ["We check the audio, then delete it", "हम आवाज़ जाँचकर मिटा देते हैं"],
  voice_listen: ["Start listening", "सुनना शुरू करें"],
  voice_listening: ["Listening… {s}s", "सुन रहे हैं… {s} सेकंड"],
  voice_demo: ["Demo clips", "डेमो क्लिप"],
  voice_upload: ["Upload a WAV", "WAV अपलोड करें"],
  voice_back: ["Back to checks", "जाँच पर वापस"],
  voice_quality: ["Speech {s} s · line quality {db} dB", "आवाज़ {s} सेकंड · लाइन {db} dB"],
  voice_mock: ["Demo detector: not a real voice check", "डेमो जाँच: असली आवाज़ जाँच नहीं"],
  rel_circle: ["You're in {payer}'s Pehchaan circle", "आप {payer} के पहचान सर्कल में हैं"],
  rel_idle: ["No questions right now", "अभी कोई सवाल नहीं"],
  rel_idle_s: ["If someone asks {payer} for money in your name, we'll ask you here first.",
               "अगर कोई आपके नाम से {payer} से पैसे माँगेगा, तो हम पहले यहाँ आपसे पूछेंगे।"],
  rel_is_this_you: ["Is this you?", "क्या ये आप हैं?"],
  rel_yes: ["Yes, it's me", "हाँ, ये मैं हूँ"],
  rel_no: ["No, that's not me", "नहीं, ये मैं नहीं हूँ"],
  rel_signed: ["Your answer is signed by this phone", "आपका जवाब इसी फ़ोन से साइन होगा"],
  rel_privacy: ["You see only the amount and who is being paid. You can't see {payer}'s other payments.",
                "आपको सिर्फ़ रकम और पाने वाले का नाम दिखता है। {payer} के बाकी पेमेंट आपको नहीं दिखते।"],
  rel_no_done: ["Thank you. {payer}'s payment is on hold.", "धन्यवाद। {payer} का पेमेंट रोक दिया गया है।"],
  rel_no_done_s: ["Someone asked {payer} for money in your name. Call {payer} now on the number you know.",
                  "किसी ने आपके नाम से {payer} से पैसे माँगे। अभी {payer} को उनके जाने-पहचाने नंबर पर कॉल करें।"],
  rel_yes_done: ["Thanks. {payer} can go ahead.", "धन्यवाद। {payer} पेमेंट कर सकती हैं।"],
  rel_call_payer: ["Call {payer}", "{payer} को कॉल करें"],
  rel_notif: ["Family Verify · {payer} needs you", "फ़ैमिली वेरिफ़ाई · {payer} को आपकी ज़रूरत है"],
  rel_open: ["Tap to answer", "जवाब देने के लिए दबाएँ"],
  large_text: ["Large text", "बड़े अक्षर"],
};

export type Key = keyof typeof S;
export interface UI { lang: Lang; large: boolean }
export const UIContext = createContext<UI>({ lang: "en", large: false });

export function useT() {
  const { lang } = useContext(UIContext);
  const t = (k: Key, vars: Record<string, string | number | undefined> = {}) => {
    let s = S[k][lang === "hi" ? 1 : 0];
    for (const [a, b] of Object.entries(vars)) s = s.split(`{${a}}`).join(String(b ?? ""));
    return s;
  };
  const bi = (x?: Bi | null) => (x ? (lang === "hi" ? x.hi : x.en) : "");
  return { t, bi, lang };
}

// Short labels for signals (console waterfall, reason icons).
export const SHORT: Record<string, [string, string]> = {
  claim_family: ["Claim: family", "दावा: परिवार"], claim_bank: ["Claim: bank", "दावा: बैंक"],
  claim_authority: ["Claim: police / govt", "दावा: पुलिस/सरकार"], claim_other: ["Claim: someone else", "दावा: कोई और"],
  claim_none: ["Claim: no one", "दावा: किसी ने नहीं"],
  caller_unknown: ["Caller not in contacts", "नंबर सेव नहीं"], caller_international: ["International caller", "विदेशी नंबर"],
  caller_voip_unknown: ["Internet call, unsaved", "इंटरनेट कॉल, अनसेव"], bank_claim_not_1600: ["'Bank' not on 1600", "'बैंक' 1600 नहीं"],
  fri_medium: ["DoT FRI: medium", "DoT FRI: मध्यम"], fri_high: ["DoT FRI: high", "DoT FRI: ज़्यादा"],
  fri_very_high: ["DoT FRI: very high", "DoT FRI: बहुत ज़्यादा"], call_ongoing_long: ["Call over 15 min", "15 मिनट से लंबी कॉल"],
  payee_new: ["New payee", "नया पाने वाला"], amount_gt_p95: ["Above usual amount", "आम से ज़्यादा"],
  amount_gt_p99: ["Far above usual", "आम से बहुत ज़्यादा"], payee_flagged_medium: ["Payee flagged: medium", "खाता: मध्यम जोखिम"],
  payee_flagged_high: ["Payee on I4C registry", "खाता I4C सूची में"], payee_name_mismatch: ["Payee name ≠ relative", "नाम मेल नहीं"],
  burst_new_payees: ["Several new payees", "कई नए पाने वाले"],
  voice_likely_synthetic: ["Voice: likely synthetic", "आवाज़: कंप्यूटर जैसी"], voice_inconclusive: ["Voice: inconclusive", "आवाज़: तय नहीं"],
  voice_no_strong_evidence: ["Voice: no strong evidence", "आवाज़: पक्का संकेत नहीं"], watermark_detected: ["AI watermark found", "AI निशान मिला"],
  cue_secrecy: ["Asked for secrecy", "छिपाने को कहा"], cue_urgency: ["Told to hurry", "जल्दी करने को कहा"],
  cue_otp_pin: ["Asked for OTP / PIN", "OTP/PIN माँगा"], cue_arrest_threat: ["Arrest threat", "गिरफ़्तारी की धमकी"],
  cue_remote_app: ["Asked to install app", "ऐप डालने को कहा"], cue_refund_verification: ["Pay to 'verify'", "'वेरिफ़ाई' के लिए पैसे"],
  fv_denied: ["Relative: not me", "रिश्तेदार: मैं नहीं"], fv_confirmed: ["Relative: yes, it's me", "रिश्तेदार: हाँ, मैं"],
  fv_timeout: ["Relative: no answer yet", "रिश्तेदार: जवाब नहीं"], callback_denied: ["Callback: not them", "कॉल-बैक: वो नहीं"],
  callback_confirmed: ["Callback: confirmed", "कॉल-बैक: पक्का"], safeword_failed: ["Safe word failed", "गुप्त शब्द गलत"],
  safeword_passed: ["Safe word passed", "गुप्त शब्द सही"], bank_no_active_call: ["Bank: no call to you", "बैंक: कोई कॉल नहीं"],
  bank_active_call_1600: ["Bank: 1600 call active", "बैंक: 1600 कॉल चालू"],
};

export const FAMILY_COLOR: Record<string, string> = {
  C: "#8a5a2b", K: "#3d5a80", P: "#6b4e9b", V: "#9b6b1f", S: "#7a3e5d", O: "#13796f",
};

export function formatINR(n: number): string {
  const s = Math.round(n).toString();
  if (s.length <= 3) return "₹" + s;
  const tail = s.slice(-3);
  let head = s.slice(0, -3);
  const parts: string[] = [];
  while (head.length > 2) { parts.unshift(head.slice(-2)); head = head.slice(0, -2); }
  if (head) parts.unshift(head);
  return "₹" + parts.join(",") + "," + tail;
}
