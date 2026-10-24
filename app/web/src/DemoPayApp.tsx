// DemoPay: the UPI app on both demo phones (SPEC §7 "Live payments" and "Two people, two phones"). Any payee, any
// amount, the phone's real call: Pehchaan decides. Each phone also answers Family Verify for the other person.
// All people, banks and UPI IDs are fictional.
import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";
import {
  ArrowLeft, At, CaretRight, CheckCircle, ClockCounterClockwise, Eye, HandPalm, Phone, QrCode, WhatsappLogo, XCircle,
} from "@phosphor-icons/react";
import { API, type Assessment, type Lang, type Scenario } from "./api";
import { Device, Seal } from "./components";
import { formatINR, UIContext } from "./i18n";
import { isNative, maskNumber, maskPhones, Pehchaan, rehearsal, usePhoneCall, type CallInfo, type PhoneCall } from "./native";
import { PayerPhone, type PayOutcome } from "./PayerPhone";
import { isVpa, paidBefore, parseUpi, resolvePayee, TRY_THESE, type Payee } from "./payees";
import type { Person } from "./people";
import { callsPayer, FamilyAnswered, FamilyPrompt, LangBtn, useFamilyInbox, type FamilyInbox } from "./RelativePhone";

type View =
  | { k: "home" } | { k: "payto" } | { k: "scan" } | { k: "history" }
  | { k: "pay"; payee: Payee & { verified: boolean }; amount: number | null; txId: string }
  | { k: "receipt"; txId: string };

interface Tx {
  id: string; at: string; vpa: string; name: string; amount: number;
  status: PayOutcome["status"]; utr: string | null; caseId: string | null; why: Why | null;
}
interface Why { tone: "ok" | "warn" | "stop"; title: [string, string]; lines: [string, string][] }

type Profile = Person["payer"];
const BANKS = [
  { id: "bdb", name: "Bharat Demo Bank", name_hi: "भारत डेमो बैंक", label: "Bharat Demo Bank", label_hi: "भारत डेमो बैंक", integrated: true, yours: true },
  { id: "other", name: "that bank", name_hi: "वो बैंक", label: "Another bank", label_hi: "कोई दूसरा बैंक", integrated: false, yours: false },
];

const load = <T,>(k: string, d: T): T => { try { return JSON.parse(localStorage.getItem(k) || "") as T; } catch { return d; } };
const save = (k: string, v: unknown) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } };
const initials = (name: string) => name.split(/\s+/).filter((w) => /^\p{L}/u.test(w)).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
export function DemoPayApp({ me, incomingUpi, onUpiHandled }: { me: Person; incomingUpi?: string | null; onUpiHandled?: () => void }) {
  const [lang, setLang] = useState<Lang>("en");
  const L = (en: string, hi: string) => (lang === "hi" ? hi : en);
  const [view, setView] = useState<View>({ k: "home" });
  const txKey = `demopay.tx.${me.key}`;
  const [txs, setTxs] = useState<Tx[]>(() => load<Tx[]>(txKey, []));
  const [profile, setProfile] = useState<Profile>(me.payer);
  const phone = usePhoneCall();
  const inbox = useFamilyInbox(me.inbox.relative);

  useEffect(() => {
    // The seeded profile on the server wins when it is the scenario's payer (same person, maybe updated)
    fetch(`${API}/v1/demo/current`).then((r) => (r.ok ? r.json() : null)).then((sc: Scenario | null) => {
      if (sc?.payer?.id === me.payer.id) setProfile({ ...me.payer, ...(sc.payer as any) });
    }).catch(() => {});
    // The phone's service watches calls and holds this phone's Family Verify inbox while the app is closed
    if (isNative) Pehchaan.startProtection({ role: "payer", deviceId: me.inbox.relative.device_id, api: API }).catch(() => {});
  }, [me.key]);
  useEffect(() => save(txKey, txs.slice(0, 40)), [txs]);

  // Android back: every screen other than home sits on one history entry
  const go = (v: View) => { if (view.k === "home" && v.k !== "home") history.pushState({ dp: 1 }, ""); setView(v); };
  const home = () => { if (view.k !== "home") history.back(); };
  useEffect(() => {
    const f = () => setView({ k: "home" });
    addEventListener("popstate", f);
    return () => removeEventListener("popstate", f);
  }, []);

  const startPay = (vpa: string, amount: number | null, nameFromQr?: string | null) =>
    go({ k: "pay", payee: resolvePayee(vpa, nameFromQr), amount, txId: Date.now().toString(36) });

  // A upi://pay link or QR opened with DemoPay from anywhere on the phone
  useEffect(() => {
    if (!incomingUpi) return;
    const u = parseUpi(incomingUpi);
    if (u) startPay(u.vpa, u.amount, u.name);
    onUpiHandled?.();
  }, [incomingUpi]);

  function onOutcome(v: Extract<View, { k: "pay" }>, o: PayOutcome) {
    const tx: Tx = {
      id: v.txId, at: new Date().toISOString(), vpa: v.payee.vpa, name: v.payee.name, amount: o.amount, status: o.status,
      utr: o.utr ?? (o.status === "paid" ? String(Date.now()).slice(-12) : null), caseId: o.caseId,
      why: explain(o, o.call),
    };
    setTxs((all) => [tx, ...all.filter((x) => x.id !== tx.id)]);
    if (o.status === "paid") setView({ k: "receipt", txId: tx.id });
  }

  // Family Verify for the other person opens over whatever screen is up
  const overlay = (inbox.push || inbox.done) && (
    <FamilyLayer inbox={inbox} me={me} lang={lang} setLang={setLang} />
  );

  if (view.k === "pay") {
    const known = paidBefore(me.paidBefore, view.payee.vpa);
    const sc = {
      scenario: "live", title: "", pattern: "", script: "", expected: {},
      payer: profile as any, relative: null, call: { state: "none", number: "", channel: "pstn", duration_sec: 0 },
      payment: { payee_vpa: view.payee.vpa, payee_name: view.payee.name, amount_inr: view.amount ?? 0 },
      bank: { name: profile.bank_name, name_hi: profile.bank_name_hi }, banks: BANKS, payee_new: !known,
    } as unknown as Scenario;
    return <>
      <PayerPhone key={view.txId} scenario={sc} initialLang={lang} onBack={home} onOutcome={(o) => onOutcome(view, o)} />
      {overlay}
    </>;
  }

  return (
    <div className="dp" lang={lang}>
      {view.k === "home" && (
        <Home L={L} lang={lang} setLang={setLang} me={me} profile={profile} phone={phone} txs={txs} inbox={inbox}
          onScan={() => go({ k: "scan" })} onPayTo={() => go({ k: "payto" })} onHistory={() => go({ k: "history" })}
          onPerson={(vpa) => startPay(vpa, null)} onTx={(id) => go({ k: "receipt", txId: id })} />
      )}
      {view.k === "payto" && <PayTo L={L} lang={lang} me={me} onBack={home} onPick={(vpa) => startPay(vpa, null)} />}
      {view.k === "scan" && <Scan L={L} onBack={home} onUpi={(u) => startPay(u.vpa, u.amount, u.name)} onTypeInstead={() => setView({ k: "payto" })} />}
      {view.k === "history" && <History L={L} txs={txs} onBack={home} onTx={(id) => setView({ k: "receipt", txId: id })} />}
      {view.k === "receipt" && (() => {
        const tx = txs.find((x) => x.id === view.txId);
        return tx ? <Receipt L={L} lang={lang} tx={tx} bank={L(profile.bank_name, profile.bank_name_hi)} onDone={home} /> : null;
      })()}
      {overlay}
    </div>
  );
}

/** Family Verify for the other person, full screen over DemoPay (their name, signed answer, then back). */
function FamilyLayer({ inbox, me, lang, setLang }: { inbox: FamilyInbox; me: Person; lang: Lang; setLang: (l: Lang) => void }) {
  const calls = callsPayer(me.inbox.relative, lang, me.inbox.payerName, me.inbox.payerNameHi);
  const payerShe = me.key === "rahul";
  const langBtn = <LangBtn lang={lang} setLang={setLang} />;
  return (
    <div className="fv-overlay">
      <UIContext.Provider value={{ lang, large: false }}>
        <Device lang={lang}>
          {inbox.done
            ? <FamilyAnswered done={inbox.done} calls={calls} langBtn={langBtn} payerShe={payerShe} onHome={inbox.dismiss} />
            : <FamilyPrompt push={inbox.push} calls={calls} keyId={inbox.keyId} busy={inbox.busy} onAnswer={inbox.answer} langBtn={langBtn} payerShe={payerShe} />}
        </Device>
      </UIContext.Provider>
    </div>
  );
}

// ------------------------------------------------------------------ home

function Home({ L, lang, setLang, me, profile, phone, txs, inbox, onScan, onPayTo, onHistory, onPerson, onTx }: {
  L: (en: string, hi: string) => string; lang: Lang; setLang: (l: Lang) => void; me: Person; profile: Profile; phone: CallInfo | null;
  txs: Tx[]; inbox: FamilyInbox; onScan: () => void; onPayTo: () => void; onHistory: () => void; onPerson: (vpa: string) => void;
  onTx: (id: string) => void;
}) {
  const [bal, setBal] = useState(false);
  return (
    <>
      <header className="dp-top">
        <span className="dp-av">{initials(profile.name)}</span>
        <div className="dp-me">
          <b>{L(profile.name, profile.name_hi)}</b>
          <span>{L("UPI ID", "UPI ID")}: {profile.vpa}</span>
        </div>
        <button className="dp-chip" onClick={() => setLang(lang === "en" ? "hi" : "en")}>{lang === "en" ? "हिंदी" : "EN"}</button>
      </header>

      {phone && phone.call.state !== "none" && <CallStrip L={L} info={phone} />}

      <section className="dp-bank">
        <div className="dp-bank-name">{L(profile.bank_name, profile.bank_name_hi)}</div>
        <div className="dp-bank-acct">{L("Savings", "बचत खाता")} ••4821</div>
        <button className="dp-bal" onClick={() => setBal(!bal)}>
          {bal ? <span className="dp-bal-v">₹1,84,230.50</span> : <><Eye size={18} weight="bold" />{L("Check balance", "बैलेंस देखें")}</>}
        </button>
      </section>

      <nav className="dp-actions">
        <button className="dp-act dp-act-main" onClick={onScan} data-testid="dp-scan">
          <QrCode size={34} weight="bold" />
          <span><b>{L("Scan QR", "QR स्कैन करें")}</b><span>{L("Shops, people, bills", "दुकान, लोग, बिल")}</span></span>
        </button>
        <button className="dp-act" onClick={onPayTo} data-testid="dp-payto">
          <At size={28} weight="bold" /><b>{L("Pay UPI ID", "UPI ID पर भेजें")}</b>
        </button>
        <button className="dp-act" onClick={onHistory}>
          <ClockCounterClockwise size={28} weight="bold" /><b>{L("History", "पुराने पेमेंट")}</b>
        </button>
      </nav>

      <section className="dp-sec">
        <h2>{L("People you've paid", "जिन्हें पहले भेजा")}</h2>
        <div className="dp-people">
          {me.paidBefore.map((p) => (
            <button key={p.vpa} className="dp-person" onClick={() => onPerson(p.vpa)}>
              <span className="dp-av sm">{initials(p.label)}</span>
              <span>{L(p.label, p.label_hi)}</span>
            </button>
          ))}
        </div>
      </section>

      <FamilySection L={L} lang={lang} me={me} inbox={inbox} />

      <section className="dp-sec">
        <h2>{L("Recent payments", "हाल के पेमेंट")}</h2>
        {txs.length === 0 ? (
          <p className="dp-empty">{L("No payments yet. Scan a QR or pay a UPI ID to start.", "अभी कोई पेमेंट नहीं। शुरू करने के लिए QR स्कैन करें या UPI ID पर भेजें।")}</p>
        ) : (
          <div className="dp-list">{txs.slice(0, 4).map((x) => <TxRow key={x.id} L={L} tx={x} onClick={() => onTx(x.id)} />)}</div>
        )}
      </section>

      <footer className="dp-foot"><Seal size={16} />{L("Payments are checked by Pehchaan during calls", "कॉल के दौरान पेमेंट की जाँच पहचान करता है")}</footer>
    </>
  );
}

/** Both directions of the family check: who protects my payments, and whose payments this phone answers for. */
function FamilySection({ L, lang, me, inbox }: { L: (en: string, hi: string) => string; lang: Lang; me: Person; inbox: FamilyInbox }) {
  const calls = callsPayer(me.inbox.relative, lang, me.inbox.payerName, me.inbox.payerNameHi);
  const circle = me.payer.circle.map((r) => (lang === "hi" ? r.name_hi || r.name : r.name)).join(L(" or ", " या "));
  const said = { yes: L("You said: yes, it's me", "आपने कहा: हाँ, मैं हूँ"), no: L("You said: not me. Payment held", "आपने कहा: मैं नहीं। पेमेंट रोका गया"),
    expired: L("No answer in time", "समय पर जवाब नहीं"), pending: L("Waiting for your answer", "आपके जवाब का इंतज़ार") };
  return (
    <section className="dp-sec">
      <h2>{L("Family Verify", "फ़ैमिली वेरिफ़ाई")}</h2>
      <div className="dp-list dp-fam">
        <div className="dp-row">
          <span className={`fam-dot ${inbox.linked ? "on" : ""}`} />
          <span className="dp-row-t">
            <b>{inbox.linked ? L(`This phone answers for ${calls}`, `यह फ़ोन ${calls} के लिए जवाब देता है`) : L("Connecting to Pehchaan…", "पहचान से जुड़ रहा है…")}</b>
            <span>{L(`If someone uses your name to ask ${calls} for money, you're asked here first.`, `अगर कोई आपके नाम से ${calls} से पैसे माँगे, तो पहले आपसे यहीं पूछा जाएगा।`)}</span>
          </span>
        </div>
        <div className="dp-row">
          <span className="dp-av sm">{me.payer.circle[0]?.name[0]}</span>
          <span className="dp-row-t">
            <b>{L(`Your circle: ${circle}`, `आपका सर्कल: ${circle}`)}</b>
            <span>{L("If a caller says they're one of them, their own phone is asked.", "अगर कॉल करने वाला कहे कि वो इनमें से कोई है, तो उनके अपने फ़ोन पर पूछा जाता है।")}</span>
          </span>
        </div>
        {inbox.reqs.slice(0, 3).map((r) => (
          <div className="dp-row" key={r.id}>
            <span className={`fam-ans ${r.answer ?? "pending"}`}>{r.answer === "no" ? "✕" : r.answer === "yes" ? "✓" : "…"}</span>
            <span className="dp-row-t">
              <b>{r.amount} {L("to", "को")} {r.payee}</b>
              <span>{said[r.answer ?? "pending"]} · {new Date(r.at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}</span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

/** The phone knows about the call: shown whenever a payment would be checked (SPEC §2 trigger). */
function CallStrip({ L, info }: { L: (en: string, hi: string) => string; info: CallInfo }) {
  const c = info.call;
  const voip = c.channel === "voip";
  const saved = info.meta.contact_name;
  const who = saved ?? (c.number ? maskNumber(c.number) : voip ? L("Internet call", "इंटरनेट कॉल") : L("Number hidden", "नंबर छिपा है"));
  const tag = rehearsal.get() && c.number ? L("Rehearsal: treated as unknown", "रिहर्सल: अनजान माना गया")
    : c.in_contacts === true ? L("Saved contact", "सेव नंबर") : c.in_contacts === false ? L("Not in your contacts", "आपके कॉन्टैक्ट में नहीं") : voip ? L("Caller not visible to apps", "कॉल करने वाला ऐप को नहीं दिखता") : "";
  const live = c.state === "active";
  const sec = c.duration_sec ?? 0;
  return (
    <div className={`dp-callstrip ${live ? "live" : ""}`} data-testid="dp-callstrip">
      <span className="dp-cs-ic">{voip ? <WhatsappLogo size={18} weight="fill" /> : <Phone size={18} weight="fill" />}</span>
      <span className="dp-cs-t">
        <b>{live ? (saved ? L(`On a call with ${saved}`, `${saved} से कॉल चालू है`) : L("On a call", "कॉल चालू है"))
          : L(`Call ended ${Math.max(1, Math.round((c.ended_sec_ago ?? 0) / 60))} min ago`, `कॉल ${Math.max(1, Math.round((c.ended_sec_ago ?? 0) / 60))} मिनट पहले खत्म हुई`)}</b>
        <span>{live && saved ? (c.number ? maskNumber(c.number) : "") : who}{tag && ` · ${tag}`}</span>
      </span>
      {live && <span className="dp-cs-time">{Math.floor(sec / 60)}:{String(sec % 60).padStart(2, "0")}</span>}
    </div>
  );
}

function TxRow({ L, tx, onClick }: { L: (en: string, hi: string) => string; tx: Tx; onClick: () => void }) {
  const st = {
    paid: L("Paid", "भेजा गया"), held: L("On hold", "रोका गया"), cancelled: L("Cancelled", "रद्द"), reported: L("Reported", "रिपोर्ट किया"),
  }[tx.status];
  const d = new Date(tx.at);
  return (
    <button className="dp-row" onClick={onClick}>
      <span className="dp-av sm">{initials(tx.name)}</span>
      <span className="dp-row-t"><b>{tx.name}</b><span>{d.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}, {d.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}</span></span>
      <span className="dp-row-r"><b>{formatINR(tx.amount)}</b><span className={`dp-st ${tx.status}`}>{st}</span></span>
    </button>
  );
}

// ------------------------------------------------------------------ choose a payee

function PayTo({ L, lang, me, onBack, onPick }: { L: (en: string, hi: string) => string; lang: Lang; me: Person; onBack: () => void; onPick: (vpa: string) => void }) {
  const [q, setQ] = useState("");
  const ok = isVpa(q);
  const found = ok ? resolvePayee(q) : null;
  return (
    <>
      <Bar onBack={onBack} title={L("Pay to a UPI ID", "UPI ID पर पैसे भेजें")} />
      <div className="dp-pad">
        <label className="dp-field">
          <span>{L("UPI ID", "UPI ID")}</span>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="name@bank" autoCapitalize="none" autoCorrect="off"
            spellCheck={false} inputMode="email" data-testid="dp-vpa" />
        </label>
        {q && !ok && <p className="dp-hint">{L("A UPI ID looks like name@bank.", "UPI ID ऐसी दिखती है: name@bank")}</p>}
        {found && (
          <button className="dp-verified" onClick={() => onPick(found.vpa)} data-testid="dp-vpa-go">
            <span className="dp-av">{initials(found.name)}</span>
            <span className="dp-row-t">
              <b>{found.name}</b>
              <span>{found.verified ? L("Registered name", "बैंक में दर्ज नाम") : L("Name not verified (demo directory)", "नाम सत्यापित नहीं (डेमो)")}</span>
            </span>
            <CaretRight size={20} />
          </button>
        )}

        <h2 className="dp-h2">{L("Try these payees", "इन्हें आज़माएँ")}</h2>
        <p className="dp-note">{L("Fictional UPI IDs. Each one changes what Pehchaan sees.", "काल्पनिक UPI ID। हर एक से पहचान को अलग संकेत मिलते हैं।")}</p>
        <div className="dp-list">
          {TRY_THESE.map((p) => (
            <button key={p.vpa} className="dp-row" onClick={() => onPick(p.vpa)}>
              <span className="dp-av sm">{initials(p.name)}</span>
              <span className="dp-row-t"><b>{p.name}</b><span>{p.vpa} · {lang === "hi" ? p.hint_hi : p.hint}</span></span>
              <CaretRight size={18} />
            </button>
          ))}
        </div>

        <h2 className="dp-h2">{L("People you've paid", "जिन्हें पहले भेजा")}</h2>
        <div className="dp-list">
          {me.paidBefore.map((p) => (
            <button key={p.vpa} className="dp-row" onClick={() => onPick(p.vpa)}>
              <span className="dp-av sm">{initials(p.label)}</span>
              <span className="dp-row-t"><b>{L(p.label, p.label_hi)}</b><span>{p.vpa} · {L(`paid ${p.times} times`, `${p.times} बार भेजा`)}</span></span>
              <CaretRight size={18} />
            </button>
          ))}
        </div>
      </div>
    </>
  );
}

function Scan({ L, onBack, onUpi, onTypeInstead }: {
  L: (en: string, hi: string) => string; onBack: () => void; onTypeInstead: () => void;
  onUpi: (u: NonNullable<ReturnType<typeof parseUpi>>) => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const [err, setErr] = useState<string | null>(null);
  const [notUpi, setNotUpi] = useState(false);
  useEffect(() => {
    let stream: MediaStream | null = null;
    let raf = 0;
    let done = false;
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const tick = () => {
      const v = video.current;
      if (!done && v && v.readyState >= 2 && ctx) {
        const w = 480, h = Math.round((v.videoHeight / v.videoWidth) * 480) || 480;
        canvas.width = w; canvas.height = h;
        ctx.drawImage(v, 0, 0, w, h);
        const code = jsQR(ctx.getImageData(0, 0, w, h).data, w, h, { inversionAttempts: "dontInvert" });
        if (code?.data) {
          const u = parseUpi(code.data);
          if (u) { done = true; onUpi(u); return; }
          setNotUpi(true);
        }
      }
      if (!done) raf = requestAnimationFrame(tick);
    };
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((s) => {
        if (done) { s.getTracks().forEach((t) => t.stop()); return; }  // left Scan before the camera opened
        stream = s;
        if (video.current) { video.current.srcObject = s; video.current.play().catch(() => {}); }
        raf = requestAnimationFrame(tick);
      })
      .catch(() => setErr(L("Camera is off for DemoPay. Allow the camera, or type the UPI ID.", "DemoPay के लिए कैमरा बंद है। कैमरा चालू करें या UPI ID टाइप करें।")));
    return () => { done = true; cancelAnimationFrame(raf); stream?.getTracks().forEach((t) => t.stop()); };
  }, []);
  return (
    <div className="dp-scan">
      <Bar onBack={onBack} title={L("Scan any UPI QR", "कोई भी UPI QR स्कैन करें")} dark />
      <div className="dp-scan-view">
        <video ref={video} playsInline muted />
        <span className="dp-scan-frame" />
      </div>
      <div className="dp-scan-foot">
        {err ?? (notUpi ? L("That QR isn't a UPI payment code.", "यह UPI पेमेंट वाला QR नहीं है।") : L("Point the camera at the QR code.", "कैमरा QR कोड पर रखें।"))}
        <button className="dp-chip light" onClick={onTypeInstead}>{L("Type UPI ID instead", "UPI ID टाइप करें")}</button>
      </div>
    </div>
  );
}

function History({ L, txs, onBack, onTx }: { L: (en: string, hi: string) => string; txs: Tx[]; onBack: () => void; onTx: (id: string) => void }) {
  return (
    <>
      <Bar onBack={onBack} title={L("Payment history", "पेमेंट हिस्ट्री")} />
      <div className="dp-pad">
        {txs.length === 0 ? <p className="dp-empty">{L("No payments yet.", "अभी कोई पेमेंट नहीं।")}</p>
          : <div className="dp-list">{txs.map((x) => <TxRow key={x.id} L={L} tx={x} onClick={() => onTx(x.id)} />)}</div>}
      </div>
    </>
  );
}

// ------------------------------------------------------------------ receipt

function Receipt({ L, lang, tx, bank, onDone }: { L: (en: string, hi: string) => string; lang: Lang; tx: Tx; bank: string; onDone: () => void }) {
  const paid = tx.status === "paid";
  const d = new Date(tx.at);
  const icon = paid ? <CheckCircle size={56} weight="fill" /> : tx.status === "cancelled" ? <XCircle size={56} weight="fill" /> : <HandPalm size={56} weight="fill" />;
  const title = {
    paid: L("Payment successful", "पेमेंट सफल"), held: L("Payment on hold", "पेमेंट रोका गया"),
    cancelled: L("Payment cancelled", "पेमेंट रद्द"), reported: L("Payment stopped and reported", "पेमेंट रोका और रिपोर्ट किया"),
  }[tx.status];
  const w = tx.why;
  return (
    <div className="dp-receipt">
      <Bar onBack={onDone} title="" />
      <div className={`dp-rc-top ${tx.status}`}>
        {icon}
        <div className="dp-rc-amt">{formatINR(tx.amount)}</div>
        <div className="dp-rc-title">{title}</div>
      </div>
      <dl className="dp-rc-rows">
        <div><dt>{L("Paid to", "किसे")}</dt><dd><b>{tx.name}</b><span>{tx.vpa}</span></dd></div>
        <div><dt>{L("From", "खाते से")}</dt><dd>{bank} ••4821</dd></div>
        <div><dt>{L("Date and time", "तारीख और समय")}</dt><dd>{d.toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { dateStyle: "medium", timeStyle: "short" })}</dd></div>
        {tx.utr && <div><dt>{L("UPI ref no.", "UPI रेफ़ नंबर")}</dt><dd className="dp-num">{tx.utr}</dd></div>}
        {tx.caseId && <div><dt>{L("Pehchaan case", "पहचान केस")}</dt><dd className="dp-num">{tx.caseId}</dd></div>}
      </dl>
      {w && (
        <section className={`dp-why ${w.tone}`} data-testid="dp-why">
          <div className="dp-why-h"><Seal size={18} /><b>{lang === "hi" ? w.title[1] : w.title[0]}</b></div>
          <ul>{w.lines.map((l, i) => <li key={i}>{maskPhones(lang === "hi" ? l[1] : l[0])}</li>)}</ul>
        </section>
      )}
      <div className="dp-rc-foot"><button className="dp-btn" onClick={onDone}>{L("Done", "ठीक है")}</button></div>
    </div>
  );
}

function Bar({ onBack, title, dark = false }: { onBack: () => void; title: string; dark?: boolean }) {
  return (
    <div className={`dp-bar ${dark ? "dark" : ""}`}>
      <button className="iconbtn" onClick={onBack} aria-label="Back"><ArrowLeft size={22} /></button>
      <span>{title}</span>
    </div>
  );
}

// ------------------------------------------------------------------ why Pehchaan did (or didn't) ask

const WHY: Record<string, [string, string]> = {
  "call active": ["You were on a call while paying", "पेमेंट के समय आप कॉल पर थे"],
  "new payee": ["First payment to this person", "इन्हें पहली बार पैसे भेज रहे थे"],
  "amount above usual (p95)": ["More than you usually send", "आम तौर से ज़्यादा रकम"],
};

/** Plain-language reasons for the receipt, from the API's own trigger and reasons (nothing invented here). */
function explain(o: PayOutcome, call: PhoneCall | null): Why {
  const a = o.first as (Assessment & { trigger?: { fired: boolean; call_condition: boolean; payment_condition: boolean; why: string[] } }) | null;
  if (!a) return { tone: "ok", title: ["Not checked", "जाँच नहीं हुई"], lines: [] };
  const tr = a.trigger;
  const trig: [string, string][] = (tr?.why ?? []).map((w) =>
    WHY[w] ?? (w.startsWith("call ended") ? [`A call had ended ${w.match(/[\d.]+/)?.[0] ?? ""} min before`, `${w.match(/[\d.]+/)?.[0] ?? ""} मिनट पहले कॉल खत्म हुई थी`] : [w, w]));
  const caller: [string, string][] = !call || call.state === "none" ? []
    : call.in_contacts === true ? [["The caller is in your contacts", "कॉल करने वाला आपके कॉन्टैक्ट में है"]]
      : call.in_contacts === false ? [["The caller isn't in your contacts", "कॉल करने वाला आपके कॉन्टैक्ट में नहीं है"]]
        : call.channel === "voip" ? [["Internet call: apps can't see who is calling", "इंटरनेट कॉल: ऐप को नहीं दिखता कि कौन है"]] : [];
  if (a.status === "not_assessed") {
    if (tr && !tr.call_condition) return { tone: "ok", title: ["No check needed", "जाँच की ज़रूरत नहीं थी"], lines: [["You weren't on a call, or in the 10 minutes before paying.", "पेमेंट से पहले के 10 मिनट में आप कॉल पर नहीं थे।"]] };
    return { tone: "ok", title: ["No check needed", "जाँच की ज़रूरत नहीं थी"], lines: [...trig, ["You've paid them before and the amount is usual for you.", "आप इन्हें पहले भेज चुके हैं और रकम आम है।"]] };
  }
  if (a.status === "cleared_silently") {
    return { tone: "ok", title: ["Checked: nothing looked risky", "जाँच हुई: कुछ खतरनाक नहीं दिखा"], lines: [...trig, ...caller] };
  }
  const last = o.last ?? a;
  const top: [string, string][] = (last.top_reasons?.length ? last.top_reasons : last.reasons).slice(0, 3)
    .map((r) => [maskPhones(r.text.en), maskPhones(r.text.hi)]);
  const tone = o.status === "paid" ? "ok" : o.status === "cancelled" ? "warn" : "stop";
  const title: [string, string] = o.status === "paid" ? ["Checked and confirmed", "जाँच हुई और पुष्टि हुई"]
    : o.status === "held" ? ["Held by Pehchaan", "पहचान ने रोका"] : o.status === "reported" ? ["Stopped and reported", "रोका और रिपोर्ट किया"]
      : ["You cancelled after the check", "जाँच के बाद आपने रद्द किया"];
  return { tone, title, lines: [...top, ...caller.filter(() => !top.some((t) => /contact/i.test(t[0])))] };
}
