import { useEffect, useState } from "react";
import nacl from "tweetnacl";
import { Check, Fingerprint, Phone, SealCheck, ShieldCheck, Timer, X } from "@phosphor-icons/react";
import { API, api, serverNow, subscribe, type Lang, type Relative } from "./api";
import { Device, Seal, StatusBar, useCountdown } from "./components";
import { UIContext, useT } from "./i18n";
import { isNative, Pehchaan } from "./native";

const b64 = (u: Uint8Array) => btoa(String.fromCharCode(...u));
const unb64 = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

/** Device-bound key: generated on the phone, never leaves it; the server stores only the public key. */
function deviceKey(deviceId: string) {
  const k = `pehchaan.devkey.${deviceId}`;
  const saved = localStorage.getItem(k);
  if (saved) {
    const sk = unb64(saved);
    return nacl.sign.keyPair.fromSecretKey(sk);
  }
  const kp = nacl.sign.keyPair();
  localStorage.setItem(k, b64(kp.secretKey));
  return kp;
}

export function RelativePhone({ relative, payerName, payerNameHi, initialLang = "en" }: {
  relative: Relative; payerName: string; payerNameHi?: string; initialLang?: Lang;
}) {
  const [lang, setLang] = useState<Lang>(initialLang);
  return (
    <UIContext.Provider value={{ lang, large: false }}>
      <Device testid="relative-device" lang={lang}>
        <RelativeFlow key={relative.device_id} relative={relative} payerName={payerName} payerNameHi={payerNameHi}
          lang={lang} setLang={setLang} />
      </Device>
    </UIContext.Provider>
  );
}

/** Requests this phone received, kept on the phone only (SPEC §7). */
interface FamilyReq { id: string; at: string; amount: string; payee: string; answer: "yes" | "no" | "expired" | null }
const REQ_KEY = "family.requests";
const loadReqs = (): FamilyReq[] => { try { return JSON.parse(localStorage.getItem(REQ_KEY) || "[]"); } catch { return []; } };

function RelativeFlow({ relative, payerName, payerNameHi, lang, setLang }: {
  relative: Relative; payerName: string; payerNameHi?: string; lang: Lang; setLang: (l: Lang) => void;
}) {
  const { t } = useT();
  const [push, setPush] = useState<any>(null);
  const [open, setOpen] = useState(false);
  const [done, setDone] = useState<null | "yes" | "no">(null);
  const [keyId, setKeyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [linked, setLinked] = useState(false);
  const [reqs, setReqs] = useState<FamilyReq[]>(loadReqs);
  const kp = deviceKey(relative.device_id);
  const note = (id: string, patch: Partial<FamilyReq>) => setReqs((all) => {
    const base = all.find((r) => r.id === id) ?? { id, at: new Date().toISOString(), amount: "", payee: "", answer: null };
    const next = [{ ...base, ...patch }, ...all.filter((r) => r.id !== id)].slice(0, 30);
    try { localStorage.setItem(REQ_KEY, JSON.stringify(next)); } catch { /* ignore */ }
    return next;
  });
  const received = (d: any) => { if (d?.challenge_id) note(d.challenge_id, { amount: d.amount_band ?? "", payee: d.payee_name ?? "" }); };
  const calls = lang === "hi" ? relative.calls_payer_hi || payerNameHi || payerName : relative.calls_payer || payerName;

  useEffect(() => {
    const pub = b64(kp.publicKey);
    api.registerDevice(relative.device_id, relative.id, pub).catch(() => {});
    // Android app: the native service keeps listening (and alerts) while this screen is closed
    if (isNative) Pehchaan.startProtection({ role: "relative", deviceId: relative.device_id, api: API }).catch(() => {});
    crypto.subtle?.digest("SHA-256", new TextEncoder().encode(pub)).then((h) => {
      const hex = [...new Uint8Array(h)].map((x) => x.toString(16).padStart(2, "0")).join("");
      setKeyId(hex.slice(-4).toUpperCase());
    }).catch(() => setKeyId(pub.slice(-4)));
    return subscribe(`/ws/device/${relative.device_id}`, (m) => {
      if (m.type === "hello" && m.pending?.length) { setPush(m.pending[0]); setDone(null); received(m.pending[0]); }
      if (m.type === "fv_request") { setPush(m.data); setDone(null); setOpen(false); received(m.data); }
      if (m.type === "fv_expired") setPush((cur: any) => { if (cur?.challenge_id) note(cur.challenge_id, { answer: "expired" }); return null; });
      if (m.type === "fv_expired" || m.type === "reset") { setPush(null); setOpen(false); if (m.type === "reset") setDone(null); }
    }, setLinked);
  }, [relative.device_id]);

  // On the real phone the system notification was the alert, so open the question directly
  useEffect(() => { if (isNative && push && !done) setOpen(true); }, [push, done]);

  async function answer(ans: "yes" | "no") {
    if (!push) return;
    setBusy(true);
    const msg = new TextEncoder().encode(`pehchaan-fv|${push.challenge_id}|${push.nonce}|${ans}`);
    const sig = b64(nacl.sign.detached(msg, kp.secretKey));
    try { await api.respond(push.challenge_id, ans, relative.device_id, sig); setDone(ans); setOpen(false); note(push.challenge_id, { answer: ans }); }
    finally { setBusy(false); }
  }

  const langBtn = (
    <button className="chipbtn" onClick={() => setLang(lang === "en" ? "hi" : "en")} data-testid="rel-lang">
      {lang === "en" ? "हिंदी" : "EN"}
    </button>
  );

  if (done) {
    return (
      <>
        <StatusBar />
        <div className="pp-head"><Seal size={20} /><span className="word">Pehchaan</span><span className="word-hi">पहचान</span><span className="grow" />{langBtn}</div>
        <div className="fv-done" data-testid="rel-done">
          <div className="di" style={{ background: done === "no" ? "var(--red-soft)" : "var(--teal-soft)", color: done === "no" ? "var(--red-deep)" : "var(--teal)" }}>
            {done === "no" ? <ShieldCheck size={38} weight="fill" /> : <Check size={38} weight="bold" />}
          </div>
          <h1>{done === "no" ? t("rel_no_done", { payer: calls }) : t("rel_yes_done", { payer: calls })}</h1>
          {done === "no" && <p>{t("rel_no_done_s", { payer: calls })}</p>}
          <div style={{ marginTop: "auto", display: "grid", gap: 10 }}>
            <button className="btn solid full"><Phone size={18} weight="fill" /> {t("rel_call_payer", { payer: calls })}</button>
            {isNative && <button className="btn ghost full" onClick={() => { setDone(null); setPush(null); }}>{lang === "hi" ? "होम पर जाएँ" : "Back to home"}</button>}
          </div>
        </div>
      </>
    );
  }

  if (push && open) {
    return <Prompt push={push} calls={calls} keyId={keyId} busy={busy} onAnswer={answer} langBtn={langBtn} />;
  }

  if (isNative) {
    const L = (en: string, hi: string) => (lang === "hi" ? hi : en);
    const said = { yes: L("You said: yes, it's me", "आपने कहा: हाँ, मैं हूँ"), no: L("You said: not me. Payment held", "आपने कहा: मैं नहीं। पेमेंट रोका गया"),
      expired: L("No answer in time", "समय पर जवाब नहीं"), pending: L("Waiting for your answer", "आपके जवाब का इंतज़ार") };
    return (
      <div className="famapp" data-testid="rel-idle">
        <div className="pp-head"><Seal size={20} /><span className="word">Pehchaan Family</span><span className="grow" />{langBtn}</div>
        <div className={`fam-status ${linked ? "on" : ""}`}>
          <span className="fam-dot" />{linked ? L("Connected. This phone will ask you first.", "जुड़ा है। यह फ़ोन पहले आपसे पूछेगा।") : L("Connecting to Pehchaan…", "पहचान से जुड़ रहा है…")}
        </div>
        <section className="fam-circle">
          <span className="dp-av">{calls[0]}</span>
          <div><b>{calls}</b><span>{lang === "hi" ? payerNameHi || payerName : payerName}</span></div>
          <ShieldCheck size={26} weight="duotone" className="fam-shield" />
        </section>
        <p className="fam-how">{t("rel_idle_s", { payer: calls })}</p>
        <h2 className="dp-h2">{L("Requests", "अनुरोध")}</h2>
        {reqs.length === 0 ? <p className="dp-empty">{L("No requests yet. You'll see each one here, with your answer.", "अभी कोई अनुरोध नहीं। हर अनुरोध और आपका जवाब यहाँ दिखेगा।")}</p> : (
          <div className="dp-list">
            {reqs.map((r) => (
              <div className="dp-row" key={r.id}>
                <span className={`fam-ans ${r.answer ?? "pending"}`}>{r.answer === "no" ? <ShieldCheck size={18} weight="fill" /> : r.answer === "yes" ? <Check size={18} weight="bold" /> : <Timer size={18} weight="bold" />}</span>
                <span className="dp-row-t">
                  <b>{r.amount} {L("to", "को")} {r.payee}</b>
                  <span>{said[r.answer ?? "pending"]} · {new Date(r.at).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}</span>
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  const now = new Date(serverNow());
  const date = now.toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { weekday: "long", day: "numeric", month: "long", timeZone: "Asia/Kolkata" });
  const tm = now.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" });
  return (
    <div className="lock" data-testid="rel-lock">
      <div className="lock-bg" />
      <StatusBar light />
      <div className="clock"><div className="d">{date}</div><div className="tm">{tm}</div></div>
      {push ? (
        <button className="notif" onClick={() => setOpen(true)} data-testid="rel-notif">
          <span className="nic"><Seal size={24} dot="#fffdf8" /></span>
          <span style={{ flex: 1 }}>
            <span style={{ display: "flex" }}><span className="nt">{t("rel_notif", { payer: calls })}</span><span className="nm">{lang === "hi" ? "अभी" : "now"}</span></span>
            <div className="nb">{lang === "hi" ? push.message?.hi : push.message?.en}</div>
            <div className="nb" style={{ fontWeight: 600, marginTop: 4 }}>{t("rel_open")}</div>
          </span>
        </button>
      ) : (
        <div className="notif" style={{ background: "rgba(245,240,230,0.16)", color: "#fff" }}>
          <span className="nic" style={{ background: "rgba(255,255,255,0.14)" }}><Seal size={24} dot="#fffdf8" /></span>
          <span><div className="nt">{t("rel_circle", { payer: calls })}</div><div className="nb" style={{ opacity: 0.85 }}>{t("rel_idle_s", { payer: calls })}</div></span>
        </div>
      )}
      <div className="hint">{lang === "hi" ? "खोलने के लिए ऊपर खिसकाएँ" : "Swipe up to open"}</div>
    </div>
  );
}

function Prompt({ push, calls, keyId, busy, onAnswer, langBtn }: {
  push: any; calls: string; keyId: string; busy: boolean; onAnswer: (a: "yes" | "no") => void; langBtn: React.ReactNode;
}) {
  const { t, lang } = useT();
  const cd = useCountdown(push.expires_at, push.timeout_sec || 180);
  const amount = lang === "hi" ? push.amount_band_hi || push.amount_band : push.amount_band;
  return (
    <>
      <StatusBar />
      <div className="pp-head"><Seal size={20} /><span className="word">Family Verify</span><span className="grow" />{langBtn}</div>
      <div className="fv" data-testid="rel-prompt">
        <div className="who">
          <span className="avatar">{calls[0]}</span>
          <div><div className="wn">{calls}</div><div className="wr">{lang === "hi" ? "पहचान सर्कल" : "Your Pehchaan circle"}</div></div>
        </div>
        {lang === "hi" ? (
          <p className="msg"><b>{calls}</b> '<b>{push.payee_name}</b>' को <span className="mono">{amount}</span> भेजने वाली हैं, क्योंकि किसी ने कहा कि वो आप हैं।</p>
        ) : (
          <p className="msg"><b>{calls}</b> is about to send <span className="mono">{amount}</span> to '<b>{push.payee_name}</b>' because someone said they are you.</p>
        )}
        <div className="ask" lang={lang}>{t("rel_is_this_you")}</div>
        <span className="timer"><Timer size={15} weight="bold" /><span className="mono">{cd.mmss}</span>{lang === "hi" ? " जवाब देने के लिए" : " left to answer"}</span>
        <p className="helper">{t("rel_helper", { payer: calls })}</p>
        <div className="answers">
          <button className="ans yes" disabled={busy} onClick={() => onAnswer("yes")} data-testid="rel-yes"><Check size={24} weight="bold" />{t("rel_yes")}</button>
          <button className="ans no" disabled={busy} onClick={() => onAnswer("no")} data-testid="rel-no"><X size={24} weight="bold" />{t("rel_no")}</button>
        </div>
        <div className="sig"><Fingerprint size={16} weight="bold" />{t("rel_signed")}<span className="mono">••{keyId}</span><SealCheck size={15} weight="fill" style={{ color: "var(--teal)" }} /></div>
        <div className="priv">{t("rel_privacy", { payer: calls })}</div>
      </div>
    </>
  );
}
