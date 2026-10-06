import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft, Backspace, Bank, CaretRight, Check, CheckCircle, DeviceMobile, FilePdf, Gavel, HandPalm, Key, Microphone,
  Phone, PhoneDisconnect, PhoneOutgoing, SealCheck, ShieldCheck, Signature, Storefront, UploadSimple, User,
  UserCircle, Users, WhatsappLogo, X,
} from "@phosphor-icons/react";
import { API, api, subscribe, type Action, type Assessment, type FvSent, type Lang, type Relative, type Scenario, type VoiceResult } from "./api";
import { Device, ReasonIcon, Ring, Seal, StatusBar, useCountdown } from "./components";
import { formatINR, UIContext, useT } from "./i18n";
import { recordWav } from "./wav";

type Screen = "pay" | "who" | "family" | "bank" | "options" | "fv_wait" | "voice" | "hold" | "green" | "pin" | "sent" | "cancelled" | "report";
type ClaimCode = "family" | "bank" | "upi_or_shop" | "authority" | "other" | "none";

export function PayerPhone({ scenario, initialLang, initialLarge = false }: { scenario: Scenario; initialLang?: Lang; initialLarge?: boolean }) {
  const [lang, setLang] = useState<Lang>(initialLang ?? "en");
  const [large, setLarge] = useState(initialLarge);
  return (
    <UIContext.Provider value={{ lang, large }}>
      <Device testid="payer-device" large={large} lang={lang}>
        <PayerFlow key={scenario.scenario + scenario.payment.payee_vpa} scenario={scenario}
          toggles={{ lang, setLang, large, setLarge }} />
      </Device>
    </UIContext.Provider>
  );
}

interface Toggles { lang: Lang; setLang: (l: Lang) => void; large: boolean; setLarge: (b: boolean) => void }

function PayerFlow({ scenario, toggles }: { scenario: Scenario; toggles: Toggles }) {
  const { t, bi, lang } = useT();
  const [screen, setScreen] = useState<Screen>("pay");
  const [amountStr, setAmountStr] = useState(String(scenario.payment.amount_inr));
  const [busy, setBusy] = useState(false);
  const [a, setA] = useState<Assessment | null>(null);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [claim, setClaim] = useState<ClaimCode | null>(null);
  const [relative, setRelative] = useState<Relative | null>(null);
  const [fv, setFv] = useState<FvSent | null>(null);
  const [pack, setPack] = useState<any>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [utr, setUtr] = useState<string | null>(null);
  const screenRef = useRef(screen);
  screenRef.current = screen;

  const amount = Number(amountStr || 0);
  const amountTxt = formatINR(amount);
  const payee = scenario.payment.payee_name;
  const relName = relative ? (lang === "hi" ? relative.name_hi || relative.name : relative.name) : "";
  const bankName = lang === "hi" ? scenario.bank.name_hi : scenario.bank.name;

  // live updates for this case (relative answers on their phone; analyst actions)
  useEffect(() => {
    if (!caseId) return;
    return subscribe(`/ws/case/${caseId}`, (m) => {
      if (m.type !== "assessment" && m.type !== "case_status") return;
      const next: Assessment = m.data;
      setA(next);
      const fvr = next.checks?.family_verify?.result;
      if (screenRef.current === "fv_wait" && fvr) route(next);
    });
  }, [caseId]);

  function route(x: Assessment) {
    setA(x);
    const checklist = x.actions.some((y) => y.id === "cue_checklist");
    if (x.tier === "red") setScreen("hold");
    else if (x.tier === "green" && !checklist) setScreen("green");
    else setScreen("options");  // Amber, or Green with the A20 checklist (context alone was Amber)
  }

  const run = async <T,>(f: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true); setErr(null);
    try { return await f(); } catch (e: any) { setErr(String(e.message || e)); } finally { setBusy(false); }
  };

  async function onPay() {
    const r = await run(() => api.assess({
      payer_id: scenario.payer.id, scenario: scenario.scenario,
      payment: { ...scenario.payment, amount_inr: amount }, call: scenario.call,
    }));
    if (!r) return;
    setA(r);
    if (r.case_id) setCaseId(r.case_id);
    if (!r.case_id || (!r.ask_claim && r.tier === "green")) { setScreen("pin"); return; }
    if (r.ask_claim || r.tier !== "red") setScreen("who"); else route(r);
  }

  async function sendClaim(c: ClaimCode, rel?: Relative | null, target?: string) {
    setClaim(c);
    if (rel) setRelative(rel);
    const r = await run(() => api.assess({ case_id: caseId, claim: c, claim_target: rel?.id ?? target }));
    if (!r) return;
    if (r.auto_family_verify) {  // SPEC v0.2 A19: the push is already on the relative's phone
      setA(r); setFv(r.auto_family_verify); setScreen("fv_wait");
    } else route(r);
  }

  async function cancelFvRequest() {
    if (!fv) return;
    const r = await run(() => api.cancelFamilyVerify(fv.challenge_id));
    if (r) { setFv(null); route(r); }
  }

  async function sendCues(cues: string[]) {
    const r = await run(() => api.assess({ case_id: caseId, cues, checklist_done: true }));
    if (r) route(r);
  }

  async function doAction(act: Action) {
    if (!caseId) return;
    if (act.id === "family_verify") {
      const r = await run(() => api.verifyFamily(caseId, relative?.id));
      if (r) { setFv(r); setA(r.assessment); setScreen("fv_wait"); }
    } else if (act.id === "bank_registry") {
      const r = await run(() => api.check(caseId, "bank_registry"));
      if (r) route(r);
    } else if (act.id === "voice_check") {
      setScreen("voice");
    } else if (act.id === "callback" || act.id === "safeword") {
      setDialog(act.id);
    } else if (act.id === "call_bank_official" || act.id === "callback_known" || act.id === "call_1930") {
      setToast(act.id === "call_1930" ? "Calling 1930…" : lang === "hi" ? "फ़ोन काटकर भरोसे वाले नंबर पर कॉल करें।" : "Hang up first, then call the number you trust.");
    }
  }

  const [dialog, setDialog] = useState<null | "callback" | "safeword">(null);
  async function answerDialog(kind: "callback" | "safeword", ok: boolean) {
    setDialog(null);
    const res = kind === "callback" ? (ok ? "confirmed" : "denied") : (ok ? "passed" : "failed");
    const r = await run(() => api.check(caseId!, kind, res));
    if (r) route(r);
  }

  async function userAction(action: string) {
    if (!caseId) return;
    const r: any = await run(() => api.userAction(caseId, action));
    if (!r) return;
    setA(r);
    if (action === "cancel") setScreen("cancelled");
    if (action === "continue" || action === "pay") { setUtr(r.utr); setScreen("pin"); }
    if (action === "bank_callback") setToast(lang === "hi" ? `${bankName} की सुरक्षा टीम 10 मिनट में आपको कॉल करेगी।` : `${scenario.bank.name}'s safety desk will call you within 10 minutes.`);
    if (action === "release") setToast(r.release_requested ? t("release_requested") : "Released");
  }

  async function openReport() {
    if (!caseId) return;
    await run(() => api.userAction(caseId, "report"));
    const p = await run(() => api.evidence(caseId));
    if (p) { setPack(p); setScreen("report"); }
  }

  useEffect(() => { if (!toast) return; const x = setTimeout(() => setToast(null), 3500); return () => clearTimeout(x); }, [toast]);

  const head = (variant: "plain" | "amber" | "red" | "teal" = "plain") => (
    <div className={variant === "plain" ? "pp-head" : "band-head"}>
      <Seal size={20} dot={variant === "red" || variant === "teal" ? "#fffdf8" : "#1b1f24"} ring={variant === "amber" ? "#1b1f24" : variant === "plain" ? "#e8742a" : "#ffd2b0"} />
      <span className="word">Pehchaan</span><span className="word-hi" style={{ opacity: 0.8 }}>पहचान</span>
      <span className="grow" />
      <LangToggle toggles={toggles} dark={variant === "red" || variant === "teal"} />
    </div>
  );

  // ------------------------------------------------------------------ render
  const call = scenario.call;
  return (
    <>
      {screen === "pay" || screen === "pin" || screen === "sent" ? (
        <>
          <StatusBar />
          {call.state === "active" && screen !== "sent" && <CallPill scenario={scenario} />}
          <div className="body">
            {screen === "pay" && (
              <PayScreen scenario={scenario} amountStr={amountStr} setAmountStr={setAmountStr} busy={busy}
                onPay={onPay} toggles={toggles} />
            )}
            {screen === "pin" && <PinScreen amountTxt={amountTxt} payee={payee} onDone={async () => {
              if (caseId && a?.status !== "sent") {
                const r: any = await run(() => api.userAction(caseId, a?.tier === "green" ? "pay" : "continue"));
                if (r?.utr) setUtr(r.utr);
              }
              setScreen("sent");
            }} />}
            {screen === "sent" && <SentScreen amountTxt={amountTxt} payee={payee} utr={utr} />}
          </div>
        </>
      ) : null}

      {screen === "who" && (
        <div className="sheet" data-testid="screen-who">
          <StatusBar />
          {head("plain")}
          <div className="sbody">
            <h1 className="q" lang={lang}>{t("who_asked")}</h1>
            <p className="lede">{t("who_sub", { amount: amountTxt, payee })}</p>
            <div className="options">
              <Opt icon={<Users size={24} weight="duotone" />} t={t("opt_family")} st={t("opt_family_s")} onClick={() => setScreen("family")} testid="claim-family" />
              <Opt icon={<Bank size={24} weight="duotone" />} t={t("opt_bank")} st={t("opt_bank_s")} onClick={() => setScreen("bank")} testid="claim-bank" />
              <Opt icon={<DeviceMobile size={24} weight="duotone" />} t={t("opt_upi")} st={t("opt_upi_s")} onClick={() => sendClaim("upi_or_shop")} testid="claim-upi_or_shop" />
              <Opt icon={<Gavel size={24} weight="duotone" />} t={t("opt_authority")} st={t("opt_authority_s")} onClick={() => sendClaim("authority")} testid="claim-authority" />
              <Opt icon={<UserCircle size={24} weight="duotone" />} t={t("opt_other")} st={t("opt_other_s")} onClick={() => sendClaim("other")} testid="claim-other" />
              <Opt icon={<HandPalm size={24} weight="duotone" />} t={t("opt_none")} st={t("opt_none_s")} onClick={() => sendClaim("none")} testid="claim-none" />
            </div>
            <div className="warn-line"><PhoneDisconnect size={18} weight="bold" /><span>{t("coached")}</span></div>
          </div>
        </div>
      )}

      {screen === "family" && (
        <div className="sheet" data-testid="screen-family">
          <StatusBar />
          {head("plain")}
          <div className="sbody">
            <button className="chipbtn" onClick={() => setScreen("who")} style={{ marginTop: 8 }}><ArrowLeft size={14} /> {lang === "hi" ? "वापस" : "Back"}</button>
            <h1 className="q" lang={lang}>{t("which_family")}</h1>
            <div className="options">
              {scenario.payer.circle.map((r) => (
                <Opt key={r.id} testid={`rel-${r.id}`} icon={<span className="avatar" style={{ width: 44, height: 44, fontSize: 16 }}>{r.name[0]}</span>}
                  t={lang === "hi" ? `${r.name_hi || r.name} · ${r.relation_hi || r.relation}` : `${r.name} · ${r.relation}`}
                  st={r.lives_in ? (lang === "hi" ? `${r.lives_in} में` : `Lives in ${r.lives_in}`) : ""}
                  onClick={() => sendClaim("family", r)} />
              ))}
              <Opt icon={<UserCircle size={24} weight="duotone" />} t={t("someone_else_family")} st="" onClick={() => sendClaim("family", null)} />
            </div>
          </div>
        </div>
      )}

      {screen === "bank" && (
        <div className="sheet" data-testid="screen-bank">
          <StatusBar />
          {head("plain")}
          <div className="sbody">
            <button className="chipbtn" onClick={() => setScreen("who")} style={{ marginTop: 8 }}><ArrowLeft size={14} /> {lang === "hi" ? "वापस" : "Back"}</button>
            <h1 className="q" lang={lang}>{t("which_bank")}</h1>
            <div className="options">
              {(scenario.banks ?? [{ id: "bdb", name: scenario.bank.name, name_hi: scenario.bank.name_hi, integrated: true, yours: true }]).map((b) => (
                <Opt key={b.id} testid={`bank-${b.id}`} icon={<Bank size={24} weight={b.yours ? "fill" : "duotone"} />}
                  t={lang === "hi" ? (b.label_hi ?? b.name_hi) : (b.label ?? b.name)}
                  st={b.yours ? t("bank_yours") : t("bank_other_s")} onClick={() => sendClaim("bank", null, b.id)} />
              ))}
            </div>
          </div>
        </div>
      )}

      {screen === "options" && a && (
        <OptionsScreen a={a} head={head("amber")} claim={claim} relName={relName} amountTxt={amountTxt} payee={payee}
          busy={busy} onAction={doAction} onCues={sendCues} onContinue={() => userAction("continue")} onCancel={() => userAction("cancel")} />
      )}

      {screen === "fv_wait" && fv && (
        <FvWait fv={fv} relName={relName} pronoun={relative?.pronoun} head={head("plain")} onCallInstead={() => setDialog("callback")}
          onCancel={() => userAction("cancel")} onCancelRequest={cancelFvRequest} busy={busy} />
      )}

      {screen === "voice" && (
        <VoiceScreen caseId={caseId} head={head("plain")} onBack={(x) => { if (x) route(x); else setScreen("options"); }} />
      )}

      {screen === "hold" && a && (
        <HoldScreen a={a} head={head("red")} relName={relName} relative={relative} bankName={bankName} amountTxt={amountTxt}
          claim={claim} busy={busy} onReport={openReport} onCallback={() => userAction("bank_callback")}
          onRelease={() => userAction("release")} onAction={doAction} />
      )}

      {screen === "green" && a && (
        <GreenScreen a={a} head={head("teal")} relName={relName} amountTxt={amountTxt} payee={payee}
          vpa={scenario.payment.payee_vpa} bank={bankName} onPay={() => setScreen("pin")} />
      )}

      {screen === "cancelled" && (
        <div className="sheet" data-testid="screen-cancelled">
          <StatusBar />
          {head("plain")}
          <div className="sbody">
            <div className="sent" style={{ paddingTop: 60 }}>
              <div className="bigtick" style={{ background: "var(--ink)" }}><ShieldCheck size={46} weight="bold" /></div>
              <h1>{t("cancelled_title")}</h1>
              <div className="to">{t("cancelled_sub")}</div>
            </div>
          </div>
          <div className="foot">
            <button className="btn saffron full" onClick={openReport}>{t("report_this")}</button>
            <button className="btn ghost full" onClick={() => setScreen("pay")}>{t("done")}</button>
          </div>
        </div>
      )}

      {screen === "report" && pack && <ReportScreen pack={pack} head={head("plain")} bankName={bankName} />}

      {dialog && (
        <Dialog kind={dialog} relName={relName} onAnswer={(ok) => answerDialog(dialog, ok)} onClose={() => setDialog(null)} />
      )}
      {toast && <div style={toastStyle} role="status">{toast}</div>}
      {err && <div style={{ ...toastStyle, background: "var(--red)" }} role="alert">{err}</div>}
      <span style={{ display: "none" }}>{bi(a?.copy?.title)}</span>
    </>
  );
}

const toastStyle: React.CSSProperties = {
  position: "absolute", left: 16, right: 16, bottom: 28, zIndex: 20, background: "var(--ink)", color: "var(--white)",
  borderRadius: 16, padding: "12px 14px", fontSize: 14.5, lineHeight: 1.4,
};

function LangToggle({ toggles, dark = false }: { toggles: Toggles; dark?: boolean }) {
  const st: React.CSSProperties = dark ? { background: "rgba(255,255,255,0.16)", borderColor: "transparent", color: "#fff" } : {};
  return (
    <span className="toggles">
      <button className="chipbtn" style={st} data-testid="lang-toggle" aria-label="Switch language"
        onClick={() => toggles.setLang(toggles.lang === "en" ? "hi" : "en")}>{toggles.lang === "en" ? "हिंदी" : "EN"}</button>
      <button className="chipbtn" style={st} aria-pressed={toggles.large} aria-label="Large text"
        onClick={() => toggles.setLarge(!toggles.large)}>Aa</button>
    </span>
  );
}

function CallPill({ scenario }: { scenario: Scenario }) {
  const { t, lang } = useT();
  const [sec, setSec] = useState(scenario.call.duration_sec);
  useEffect(() => { const x = setInterval(() => setSec((s) => s + 1), 1000); return () => clearInterval(x); }, []);
  const n = scenario.call.number;
  const pretty = n.startsWith("+44") ? `+44 ${n.slice(3, 7)} ${n.slice(7)}` : n.startsWith("+91") ? `+91 ${n.slice(3, 8)} ${n.slice(8)}` : n;
  const saved = (scenario as any).caller_saved_as as string | null;
  const wa = scenario.call.channel === "whatsapp";
  return (
    <div className="callpill" data-testid="callpill">
      <span className="dot">{wa ? <WhatsappLogo size={17} weight="fill" /> : <Phone size={16} weight="fill" />}</span>
      <span>
        <div className="num">{saved ?? pretty}</div>
        <div className="meta">{wa ? t("whatsapp_call") : t("phone_call")}{!saved && <span className="flag">{t("unknown_number")}</span>}</div>
      </span>
      <span className="timer">{Math.floor(sec / 60)}:{String(sec % 60).padStart(2, "0")}</span>
      <span style={{ display: "none" }}>{lang}</span>
    </div>
  );
}

function PayScreen({ scenario, amountStr, setAmountStr, busy, onPay, toggles }: {
  scenario: Scenario; amountStr: string; setAmountStr: (s: string) => void; busy: boolean; onPay: () => void; toggles: Toggles;
}) {
  const { t } = useT();
  const p = scenario.payment;
  const initials = p.payee_name.split(" ").map((w) => w[0]).slice(0, 2).join("");
  const amt = Number(amountStr || 0);
  const shown = amountStr ? formatINR(amt).slice(1) : "0";
  const press = (k: string) => {
    if (k === "del") setAmountStr(amountStr.slice(0, -1));
    else if (amountStr.length < 7) setAmountStr((amountStr === "0" ? "" : amountStr) + k);
  };
  return (
    <div data-testid="screen-pay">
      <div className="appbar">
        <ArrowLeft size={22} />
        <span className="brand"><span className="sq">₹</span>DemoPay</span>
        <span className="spacer" />
        <LangToggle toggles={toggles} />
      </div>
      <div className="payee">
        <span className="avatar">{initials}</span>
        <div>
          <div style={{ fontSize: 13, color: "var(--slate)" }}>{t("paying")}</div>
          <div className="name">{p.payee_name}</div>
          <div className="vpa">{p.payee_vpa}</div>
          {(scenario as any).payee_new && <div className="newtag"><User size={13} weight="bold" />{t("new_payee")}</div>}
        </div>
      </div>
      <div className="amount">
        <div className="val" data-testid="amount"><span className="cur">₹</span>{shown}<span className="caret" /></div>
        <div className="note">{t("add_note")}</div>
      </div>
      <div className="fromrow">
        <span className="bank"><Bank size={17} weight="fill" /></span>
        <span>{t("from_acct")} <b>{scenario.bank.name}</b> <span className="mono" style={{ color: "var(--slate)" }}>••4821</span></span>
      </div>
      <div className="keypad">
        {["1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "0", "del"].map((k) => (
          <button key={k} className="key" onClick={() => press(k)} aria-label={k === "del" ? "Delete" : k}>
            {k === "del" ? <Backspace size={24} /> : k}
          </button>
        ))}
      </div>
      <button className="paybtn" onClick={onPay} disabled={busy || !amt} data-testid="pay-btn">
        {busy ? t("checking") : <>{t("pay")} <span className="mono">{formatINR(amt)}</span></>}
      </button>
      <div className="pp-foot"><Seal size={16} />{t("protected")}</div>
    </div>
  );
}

function Opt({ icon, t, st, onClick, testid }: { icon: React.ReactNode; t: string; st: string; onClick: () => void; testid?: string }) {
  return (
    <button className="opt" onClick={onClick} data-testid={testid}>
      <span className="ic">{icon}</span>
      <span><div className="t">{t}</div>{st && <div className="st">{st}</div>}</span>
      <CaretRight size={18} className="chev" />
    </button>
  );
}

function OptionsScreen({ a, head, claim, relName, amountTxt, payee, busy, onAction, onCues, onContinue, onCancel }: {
  a: Assessment; head: React.ReactNode; claim: ClaimCode | null; relName: string; amountTxt: string; payee: string; busy: boolean;
  onAction: (x: Action) => void; onCues: (cues: string[]) => void; onContinue: () => void; onCancel: () => void;
}) {
  const { t, bi, lang } = useT();
  const [left, setLeft] = useState(5);
  useEffect(() => { const x = setInterval(() => setLeft((s) => Math.max(0, s - 1)), 1000); return () => clearInterval(x); }, []);
  const top = a.top_reasons.slice(0, 2);
  const checklist = a.actions.find((x) => x.id === "cue_checklist");
  const checks = a.actions.filter((x) => x.kind === "check" && x.id !== "cue_checklist");
  const primary = checks.find((x) => x.primary);
  const cancelAct = a.actions.find((x) => x.id === "cancel_payment");
  const cancelFirst = !!cancelAct?.primary;
  const unknownReg = a.reasons.find((r) => r.code === "bank_registry_unknown");
  const userNeg = a.reasons.find((r) => r.code === "callback_denied" || r.code === "safeword_failed");
  const others = checks.filter((x) => x !== primary);
  const fact = a.actions.find((x) => x.id === "authority_fact" || x.id === "bank_fact" || x.id === "coached_warning");
  const checkTitle = claim === "family" && relName ? t("check_really", { name: relName }) : claim === "bank" ? t("check_bank") : t("check_generic");
  return (
    <div className="sheet" data-testid="screen-options">
      <div className="band amber">
        <StatusBar fill="var(--amber)" />
        {head}
        <div className="brandline" lang={lang}>{t("amber_brand")}</div>
        <div className="sub">{lang === "hi" ? `${payee} को ${amountTxt} · ${t("amber_sub")}` : `${amountTxt} to ${payee} · ${t("amber_sub")}`}</div>
      </div>
      <div className="sbody">
        {checklist && <CueChecklist busy={busy} onDone={onCues} />}
        {(unknownReg || userNeg) && (
          <div className="warn-line" style={{ marginTop: 14 }}><ShieldCheck size={18} weight="bold" style={{ color: "var(--ink)" }} />
            <span>{bi((userNeg ?? unknownReg)!.text)}</span></div>
        )}
        <div className="sec-t">{t("we_noticed")}</div>
        <div className="reasons">
          {top.map((r) => (
            <div className="reason" key={r.code} data-code={r.code}>
              <span className="ri"><ReasonIcon code={r.code} /></span><span className="rt">{bi(r.text)}</span>
            </div>
          ))}
        </div>
        {fact && claim !== "family" && (
          <div className="warn-line" style={{ background: fact.id === "authority_fact" ? "var(--ink)" : undefined, color: fact.id === "authority_fact" ? "#fff" : undefined }}>
            <ShieldCheck size={18} weight="bold" /><span>{bi(fact.label)}</span>
          </div>
        )}
        {(primary || others.length > 0) && <div className="sec-t">{checkTitle}</div>}
        <div className="checks">
          {primary && (
            <button className="check-primary" onClick={() => onAction(primary)} disabled={busy} data-testid={`act-${primary.id}`}>
              <span className="ic">{actionIcon(primary.id, 24)}</span>
              <span><div className="t">{bi(primary.label)}</div>{primary.detail && <div className="st">{bi(primary.detail)}</div>}</span>
            </button>
          )}
          {others.map((x) => (
            <button className="check-row" key={x.id} onClick={() => onAction(x)} disabled={busy} data-testid={`act-${x.id}`}>
              <span className="ic">{actionIcon(x.id, 20)}</span><span>{bi(x.label)}</span><CaretRight size={16} className="chev" />
            </button>
          ))}
        </div>
      </div>
      <div className="foot">
        {cancelFirst && <div style={{ fontSize: 13.5, color: "var(--ink-2)", lineHeight: 1.4 }}>{t("cancel_safer")}</div>}
        <div className="btn-row">
          <button className={`btn ${cancelFirst ? "saffron" : "solid"}`} onClick={onCancel} data-testid="cancel-payment">{t("cancel_payment")}</button>
          <button className="btn ghost" disabled={left > 0} onClick={onContinue} data-testid="continue-anyway">
            {left > 0 ? t("continue_in", { s: left }) : t("continue")}
          </button>
        </div>
      </div>
    </div>
  );
}

function CueChecklist({ busy, onDone }: { busy: boolean; onDone: (cues: string[]) => void }) {
  const { t } = useT();
  const [on, setOn] = useState<Set<string>>(new Set());
  const items: [string, string][] = [["cue_secrecy", t("cl_secrecy")], ["cue_otp_pin", t("cl_otp")], ["cue_arrest_threat", t("cl_arrest")]];
  const flip = (c: string) => setOn((s) => { const n = new Set(s); n.has(c) ? n.delete(c) : n.add(c); return n; });
  return (
    <div className="checklist" data-testid="cue-checklist" style={{ marginTop: 16 }}>
      <div className="ct">{t("cl_title")}</div>
      <div className="cs">{t("cl_sub")}</div>
      {items.map(([c, label]) => (
        <button key={c} className="cl-row" aria-pressed={on.has(c)} onClick={() => flip(c)} data-testid={`cl-${c}`}>
          <span className="box">{on.has(c) && <Check size={15} weight="bold" />}</span>{label}
        </button>
      ))}
      <div className="cl-actions">
        <button className="btn ghost" disabled={busy} onClick={() => onDone([])} data-testid="cl-none">{t("cl_none")}</button>
        <button className="btn solid" disabled={busy || on.size === 0} onClick={() => onDone([...on])} data-testid="cl-done">{t("cl_done")}</button>
      </div>
    </div>
  );
}

function actionIcon(id: string, size: number) {
  const p = { size, weight: "bold" as const };
  switch (id) {
    case "family_verify": return <Signature {...p} />;
    case "callback": case "callback_known": return <PhoneOutgoing {...p} />;
    case "safeword": return <Key {...p} />;
    case "bank_registry": return <Bank {...p} />;
    case "call_bank_official": return <Phone {...p} />;
    case "voice_check": return <Microphone {...p} />;
    case "call_1930": return <Phone {...p} />;
    default: return <CaretRight {...p} />;
  }
}

function FvWait({ fv, relName, pronoun, head, onCallInstead, onCancel, onCancelRequest, busy }: {
  fv: FvSent; relName: string; pronoun?: string; head: React.ReactNode; onCallInstead: () => void; onCancel: () => void;
  onCancelRequest: () => void; busy: boolean;
}) {
  const { t } = useT();
  const cd = useCountdown(fv.expires_at, fv.timeout_sec);
  const their = pronoun === "he" ? "his" : pronoun === "she" ? "her" : "their";
  return (
    <div className="sheet" data-testid="screen-fv-wait" data-auto={fv.auto ? "1" : "0"}>
      <StatusBar />
      {head}
      <div className="sbody">
        <h1 className="q">{fv.auto ? t("fv_auto_title", { name: relName, their }) : t("waiting_for", { name: relName })}</h1>
        <p className="lede">{fv.auto ? t("fv_auto_sub", { name: relName }) : t("waiting_sub", { name: relName })}</p>
        <div className="ring-wrap">
          <Ring size={190} frac={cd.frac} stroke={12} track="#ede5d5" color="#e8742a">
            <div><div className="big">{cd.mmss}</div><div className="small">{t("fv_left")}</div></div>
          </Ring>
        </div>
        <ul className="steps">
          <li><span className="tick"><Check size={15} weight="bold" /></span>{t("fv_sent")}</li>
          <li><span className="tick wait pulse"><Signature size={15} weight="bold" /></span>{t("fv_signed")}</li>
        </ul>
        {fv.auto && (
          <button className="linkbtn" onClick={onCancelRequest} disabled={busy} data-testid="fv-cancel-request">
            {t("fv_cancel_request")}
          </button>
        )}
      </div>
      <div className="foot">
        <button className="btn full" onClick={onCallInstead}>{t("call_instead", { name: relName })}</button>
        <button className="btn ghost full" onClick={onCancel}>{t("cancel_payment")}</button>
      </div>
    </div>
  );
}

function Jaali() {
  // A light lattice: the hold is a screen in front of your money, not a wall.
  return (
    <svg className="jaali" width="100%" height="100%" aria-hidden="true">
      <defs>
        <pattern id="jl" width="28" height="28" patternUnits="userSpaceOnUse">
          <path d="M14 0 L28 14 L14 28 L0 14 Z" fill="none" stroke="#fff" strokeWidth="1.4" />
          <circle cx="14" cy="14" r="2.2" fill="#fff" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#jl)" />
    </svg>
  );
}

function HoldScreen({ a, head, relName, relative, bankName, amountTxt, claim, busy, onReport, onCallback, onRelease, onAction }: {
  a: Assessment; head: React.ReactNode; relName: string; relative: Relative | null; bankName: string; amountTxt: string;
  claim: ClaimCode | null; busy: boolean; onReport: () => void; onCallback: () => void; onRelease: () => void; onAction: (x: Action) => void;
}) {
  const { t, bi, lang } = useT();
  const hold = a.hold;
  const cd = useCountdown(hold?.until, (hold?.minutes ?? 30) * 60);
  const sig = new Set(a.signals ?? []);
  const reasonBy = (c: string) => a.reasons.find((r) => r.code === c);
  let lead: React.ReactNode = null;
  const used = new Set<string>();
  if (sig.has("fv_denied") || sig.has("callback_denied")) {
    const r = reasonBy(sig.has("fv_denied") ? "fv_denied" : "callback_denied")!;
    used.add(r.code);
    lead = (
      <div className="lead-card" data-testid="lead-fv">
        <div className="who"><span className="lc-ic"><span style={{ fontFamily: "var(--f-head)", fontWeight: 700, fontSize: 19 }}>{relName[0]}</span></span>
          <div className="lc-t">{bi(r.text)}</div></div>
        {r.code === "fv_denied" && <div className="lc-s"><SealCheck size={16} weight="fill" />{t("answered_from", { name: relName })}</div>}
      </div>
    );
  } else if (sig.has("bank_no_active_call")) {
    const r = reasonBy("bank_no_active_call")!;
    used.add(r.code); used.add("bank_claim_not_1600");
    const n1600 = reasonBy("bank_claim_not_1600");
    lead = (
      <div className="lead-card bank" data-testid="lead-bank">
        <div className="who"><span className="lc-ic"><Bank size={24} weight="fill" /></span><div className="lc-t">{bi(r.text)}</div></div>
        {n1600 && <div className="lc-b">{bi(n1600.text)}</div>}
        <div className="lc-s" style={{ color: "var(--ink-2)" }}><ShieldCheck size={16} weight="fill" />{lang === "hi" ? `${bankName} के कॉल रिकॉर्ड से जाँचा गया` : `Checked with ${bankName}'s own call records`}</div>
      </div>
    );
  } else if (claim === "authority" || sig.has("claim_authority")) {
    used.add("claim_authority");
    const fact = lang === "hi" ? ["भारतीय कानून में ‘डिजिटल अरेस्ट’ नाम की कोई चीज़ नहीं है।", "पुलिस कभी फ़ोन पर पैसे नहीं माँगती। अगर डर लग रहा है, तो फ़ोन काटें और 1930 पर कॉल करें।"]
      : ["There is no ‘digital arrest’ in Indian law.", "Police never ask for money on a call. If you feel scared, hang up and call 1930."];
    lead = (
      <div className="lead-card fact" data-testid="lead-fact">
        <div className="who"><span className="lc-ic"><Gavel size={24} weight="fill" /></span><div className="lc-t">{fact[0]}</div></div>
        <div className="lc-b">{fact[1]}</div>
      </div>
    );
  }
  const more = a.top_reasons.filter((r) => !used.has(r.code)).slice(0, lead ? 2 : 3);
  const release = a.actions.find((x) => x.id === "release_early");
  const checks = a.actions.filter((x) => x.kind === "check" && x.id !== "safeword");
  return (
    <div className="sheet" data-testid="screen-hold">
      <div className="hold-top">
        <Jaali />
        <StatusBar light />
        {head}
        <div className="hold-grid">
          <div className="hold-ring">
            <Ring size={116} frac={cd.frac} stroke={9} track="rgba(255,255,255,0.22)" color="#fffdf8">
              <div><div className="big">{cd.mmss}</div><div className="small">{lang === "hi" ? "रोक बाकी" : "on hold"}</div></div>
            </Ring>
          </div>
          <div>
            <h1 lang={lang}>{t("hold_title")}</h1>
            <div className="ns">{t("hold_not_sent", { amount: amountTxt })}</div>
          </div>
        </div>
      </div>
      <div className="sbody" style={{ paddingTop: 14 }}>
        {lead}
        {more.length > 0 && (<>
          <div className="sec-t">{lead ? t("more_noticed") : t("why_paused")}</div>
          <div className="reasons">
            {more.map((r) => (
              <div className="reason" key={r.code}><span className="ri"><ReasonIcon code={r.code} /></span><span className="rt">{bi(r.text)}</span></div>
            ))}
          </div>
        </>)}
        <div className="hold-actions">
          <button className="hold-act primary" onClick={onReport} disabled={busy} data-testid="cancel-report">
            <FilePdf size={22} className="ic" weight="bold" />
            <span><div className="t">{t("cancel_report")}</div><div className="st">1930 · cybercrime.gov.in · Chakshu</div></span>
          </button>
          <button className="hold-act" onClick={onCallback} data-testid="bank-callback">
            <Phone size={22} className="ic" weight="bold" />
            <span><div className="t">{t("talk_person")}</div><div className="st">{t("talk_person_s", { bank: bankName })}</div></span>
          </button>
          {checks.map((x) => (
            <button className="hold-act" key={x.id} onClick={() => onAction(x)} data-testid={`hold-${x.id}`}>
              <span className="ic">{actionIcon(x.id, 22)}</span><span><div className="t">{bi(x.label)}</div></span>
            </button>
          ))}
          {release && (
            <button className="hold-act" onClick={onRelease} data-testid="release-early">
              <ShieldCheck size={22} className="ic" weight="bold" />
              <span><div className="t">{t("release_early")}</div>
                <div className="st">{release.requires === "analyst_review" ? t("release_review") : t("release_check")}</div></span>
            </button>
          )}
        </div>
        <p className="fine">{t("hold_auto")}</p>
        {relative && <span style={{ display: "none" }}>{relative.id}</span>}
      </div>
    </div>
  );
}

function GreenScreen({ a, head, relName, amountTxt, payee, vpa, bank, onPay }: {
  a: Assessment; head: React.ReactNode; relName: string; amountTxt: string; payee: string; vpa: string; bank: string; onPay: () => void;
}) {
  const { t, bi, lang } = useT();
  const conf = a.reasons.find((r) => r.code === "fv_confirmed" || r.code === "callback_confirmed" || r.code === "bank_active_call_1600");
  return (
    <div className="sheet" data-testid="screen-green">
      <div className="green-top">
        <StatusBar light />
        {head}
        <div className="gt-ic"><CheckCircle size={40} weight="fill" /></div>
        <h1 lang={lang}>{t("green_title")}</h1>
        <div className="gs">{conf ? bi(conf.text) : bi(a.copy.body)}</div>
      </div>
      <div className="sbody">
        {conf?.code === "fv_confirmed" && (
          <div className="lc-s" style={{ display: "flex", gap: 7, alignItems: "center", color: "var(--teal)", fontWeight: 600, fontSize: 13, marginTop: 14 }}>
            <SealCheck size={16} weight="fill" />{t("answered_from", { name: relName })}
          </div>
        )}
        <div className="sec-t">{t("noticed_before")}</div>
        <div className="reasons">
          {a.reasons.filter((r) => r.direction === "raises" && !r.code.startsWith("claim_")).slice(0, 2).map((r) => (
            <div className="reason" key={r.code} style={{ opacity: 0.8 }}><span className="ri"><ReasonIcon code={r.code} /></span><span className="rt">{bi(r.text)}</span></div>
          ))}
        </div>
        <div className="summary">
          <div className="row"><span>{lang === "hi" ? "किसे" : "To"}</span><span style={{ textAlign: "right" }}><b>{payee}</b><br /><span className="mono" style={{ color: "var(--slate)", fontSize: 12.5 }}>{vpa}</span></span></div>
          <div className="row"><span>{lang === "hi" ? "रकम" : "Amount"}</span><span className="mono"><b>{amountTxt}</b></span></div>
          <div className="row"><span>{lang === "hi" ? "खाते से" : "From"}</span><span>{bank} <span className="mono" style={{ color: "var(--slate)" }}>••4821</span></span></div>
        </div>
      </div>
      <div className="foot">
        <button className="paybtn" style={{ margin: 0, width: "100%" }} onClick={onPay} data-testid="green-pay">{t("pay_now", { amount: amountTxt })}</button>
      </div>
    </div>
  );
}

function PinScreen({ amountTxt, payee, onDone }: { amountTxt: string; payee: string; onDone: () => void }) {
  const { t } = useT();
  const [n, setN] = useState(0);
  useEffect(() => { if (n >= 4) { const x = setTimeout(onDone, 350); return () => clearTimeout(x); } }, [n]);
  return (
    <div data-testid="screen-pin" style={{ padding: "10px 0" }}>
      <div style={{ textAlign: "center", marginTop: 18 }}>
        <div style={{ fontSize: 14, color: "var(--slate)" }}>{payee}</div>
        <div className="mono" style={{ fontSize: 30, fontWeight: 600, marginTop: 4 }}>{amountTxt}</div>
        <div style={{ fontFamily: "var(--f-head)", fontSize: 20, fontWeight: 600, marginTop: 26 }}>{t("enter_pin")}</div>
      </div>
      <div className="pin-dots">{[0, 1, 2, 3].map((i) => <span key={i} className={i < n ? "on" : ""} />)}</div>
      <div className="keypad">
        {["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "del"].map((k, i) => (
          <button key={i} className="key" disabled={!k} onClick={() => setN(k === "del" ? Math.max(0, n - 1) : Math.min(4, n + 1))} data-testid={`pin-${k || "x"}`}>
            {k === "del" ? <Backspace size={24} /> : k}
          </button>
        ))}
      </div>
    </div>
  );
}

function SentScreen({ amountTxt, payee, utr }: { amountTxt: string; payee: string; utr: string | null }) {
  const { t } = useT();
  return (
    <div className="sent" data-testid="screen-sent">
      <div className="bigtick" style={{ marginTop: 70 }}><Check size={48} weight="bold" /></div>
      <h1 className="mono">{t("sent_title", { amount: amountTxt })}</h1>
      <div className="to">{t("sent_to", { payee })}</div>
      <div className="utr">UTR {utr ?? "DEMO" + Date.now().toString().slice(-10)}</div>
    </div>
  );
}

function Dialog({ kind, relName, onAnswer, onClose }: { kind: "callback" | "safeword"; relName: string; onAnswer: (ok: boolean) => void; onClose: () => void }) {
  const { lang } = useT();
  const q = kind === "callback"
    ? (lang === "hi" ? `${relName} के सेव किए नंबर पर कॉल करें। क्या उन्होंने कहा कि ये पैसे उन्होंने माँगे हैं?` : `Call ${relName || "them"} on the number saved in your phone. Did they say they asked for this money?`)
    : (lang === "hi" ? "कॉल करने वाले से परिवार का गुप्त शब्द पूछें। क्या उन्होंने सही बताया?" : "Ask the caller for your family safe word. Did they say it correctly?");
  const yes = kind === "callback" ? (lang === "hi" ? "हाँ, उन्होंने माँगे" : "Yes, they asked") : (lang === "hi" ? "हाँ, सही बताया" : "Yes, correct");
  const no = kind === "callback" ? (lang === "hi" ? "नहीं, उन्होंने नहीं माँगे" : "No, they didn't") : (lang === "hi" ? "नहीं, गलत बताया" : "No, wrong");
  return (
    <div style={{ position: "absolute", inset: 0, background: "rgba(27,31,36,0.45)", zIndex: 15, display: "flex", alignItems: "flex-end" }} onClick={onClose}>
      <div style={{ background: "var(--paper)", borderRadius: "26px 26px 0 0", padding: "22px 20px 30px", width: "100%" }} onClick={(e) => e.stopPropagation()}>
        <div style={{ fontFamily: "var(--f-head)", fontWeight: 600, fontSize: 20, lineHeight: 1.3 }}>{q}</div>
        <div style={{ display: "grid", gap: 10, marginTop: 18 }}>
          <button className="btn teal full" onClick={() => onAnswer(true)}>{yes}</button>
          <button className="btn solid full" style={{ background: "var(--red)", borderColor: "var(--red)" }} onClick={() => onAnswer(false)}>{no}</button>
          <button className="btn ghost full" onClick={onClose}><X size={16} /> {lang === "hi" ? "बंद करें" : "Close"}</button>
        </div>
      </div>
    </div>
  );
}

function VoiceScreen({ caseId, head, onBack }: { caseId: string | null; head: React.ReactNode; onBack: (a?: Assessment) => void }) {
  const { t, bi, lang } = useT();
  const [state, setState] = useState<"idle" | "listening" | "done">("idle");
  const [left, setLeft] = useState(0);
  const [res, setRes] = useState<VoiceResult | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const bars = useMemo(() => Array.from({ length: 34 }, (_, i) => i), []);
  async function score(blob: Blob, hint?: string) {
    setState("listening");
    for (let s = 3; s > 0; s--) { setLeft(s); await new Promise((r) => setTimeout(r, 500)); }
    try { setRes(await api.voice(blob, caseId, hint)); setState("done"); } catch (e: any) { setErr(String(e.message)); setState("idle"); }
  }
  async function demo(kind: string, hint: string) { score(await api.demoAudio(kind), hint); }
  async function mic() {
    try { setState("listening"); const blob = await recordWav(10, setLeft); score(blob); }
    catch { setErr(lang === "hi" ? "माइक्रोफ़ोन नहीं मिला। डेमो क्लिप चुनें।" : "No microphone available. Use a demo clip."); setState("idle"); }
  }
  const bandText = res ? (res.quality.ok ? res.band : "inconclusive") : "";
  const txt: Record<string, [string, string]> = {
    likely_synthetic: ["Our voice check found signs that this voice may be computer-made. The check can be wrong, so please confirm another way.", "आवाज़ की जाँच में कुछ संकेत मिले कि ये आवाज़ कंप्यूटर से बनी हो सकती है। जाँच गलत भी हो सकती है, इसलिए किसी और तरीके से पक्का करें।"],
    inconclusive: ["The voice check could not decide. The line may be noisy or the clip too short.", "आवाज़ की जाँच से कुछ तय नहीं हो पाया। लाइन में शोर हो सकता है या रिकॉर्डिंग बहुत छोटी थी।"],
    no_strong_evidence: ["The voice check found no strong signs of a computer-made voice. That alone does not prove who is speaking.", "आवाज़ की जाँच में कंप्यूटर से बनी आवाज़ के पक्के संकेत नहीं मिले। पर सिर्फ़ इससे ये पक्का नहीं होता कि बात कौन कर रहा है।"],
  };
  return (
    <div className="sheet" data-testid="screen-voice">
      <StatusBar />
      {head}
      <div className="sbody">
        <h1 className="q" lang={lang}>{t("voice_title")}</h1>
        <p className="lede">{t("voice_sub")}</p>
        <div className={`mic-stage ${state === "listening" ? "on" : ""}`}>
          {bars.map((i) => <i key={i} style={{ animationDelay: `${(i % 7) * 0.11}s`, opacity: state === "idle" ? 0.35 : 1 }} />)}
        </div>
        {state === "idle" && (<>
          <ol className="vsteps"><li>{t("voice_step1")}</li><li>{t("voice_step2")}</li><li>{t("voice_step3")}</li></ol>
          <button className="btn saffron full" style={{ marginTop: 14 }} onClick={mic}><Microphone size={18} weight="bold" /> {t("voice_listen")}</button>
          <div className="sec-t">{t("voice_demo")}</div>
          <div className="demo-clips">
            <button className="chipbtn" onClick={() => demo("synthetic", "synthetic")} data-testid="clip-synthetic">{lang === "hi" ? "क्लोन आवाज़" : "Cloned voice"}</button>
            <button className="chipbtn" onClick={() => demo("bonafide", "bonafide")} data-testid="clip-real">{lang === "hi" ? "असली आवाज़" : "Real voice"}</button>
            <button className="chipbtn" onClick={() => demo("noisy", "synthetic")}>{lang === "hi" ? "शोर वाली लाइन" : "Noisy line"}</button>
            <button className="chipbtn" onClick={() => fileRef.current?.click()}><UploadSimple size={14} /> {t("voice_upload")}</button>
            <input ref={fileRef} type="file" accept="audio/wav,.wav" hidden onChange={(e) => e.target.files?.[0] && score(e.target.files[0])} />
          </div>
        </>)}
        {state === "listening" && <p className="lede" style={{ textAlign: "center", marginTop: 12 }}>{t("voice_listening", { s: left })}</p>}
        {state === "done" && res && (
          <div className="vresult" data-testid="voice-result" data-mode={res.voice_mode ?? "calibrated"}>
            {res.user_message ? (
              // shadow mode (or a watermark hit): no verdict on the voice, just what happens next (G6)
              <div className="vb">{bi(res.user_message)}</div>
            ) : (<>
              <div className="vb">{lang === "hi" ? txt[bandText][1] : txt[bandText][0]}</div>
              <div className="meter"><span className="pin" style={{ left: `calc(${(res.p_synthetic * 100).toFixed(0)}% - 2px)` }} /></div>
              <div className="vq mono">{t("voice_quality", { s: res.quality.speech_sec.toFixed(1), db: res.quality.snr_db.toFixed(0) })}{res.quality.ok ? " ✓" : " ✗"}</div>
              <div className="vq mono" style={{ marginTop: 2 }}>p = {res.p_synthetic.toFixed(2)} · {res.model_version}</div>
            </>)}
            {res.mock && <div className="mocktag">{t("voice_mock")}</div>}
            <span style={{ display: "none" }}>{bi(res.assessment?.copy?.title)}</span>
          </div>
        )}
        {err && <div className="warn-line">{err}</div>}
      </div>
      <div className="foot">
        <button className="btn solid full" onClick={() => onBack(res?.assessment)}>{t("voice_back")}</button>
      </div>
    </div>
  );
}

const prettyNum = (n?: string) => !n ? "" : n.startsWith("+44") ? `+44 ${n.slice(3, 7)} ${n.slice(7)}` :
  n.startsWith("+91") ? `+91 ${n.slice(3, 8)} ${n.slice(8)}` : n;

function ReportScreen({ pack, head, bankName }: { pack: any; head: React.ReactNode; bankName: string }) {
  const { t, lang } = useT();
  const nc = pack.prefill.ncrp.fields;
  const ch = pack.prefill.chakshu.fields;
  return (
    <div className="sheet" data-testid="screen-report">
      <StatusBar />
      {head}
      <div className="sbody">
        <h1 className="q" lang={lang}>{t("report_ready")}</h1>
        <p className="lede" style={{ marginBottom: 0 }}>{t("report_sub")}</p>
        <div className="pack-id">
          <div style={{ fontSize: 12.5, color: "#c9cdd3" }}>{lang === "hi" ? "केस नंबर" : "Case number"}</div>
          <div className="pid">{pack.case_id}</div>
          <div className="seal"><SealCheck size={16} weight="fill" />{t("signed_pack")} · Ed25519 · {pack.hash_chain.length} {lang === "hi" ? "घटनाएँ जुड़ी" : "events chained"}</div>
          <div className="hash">SHA-256 {pack.hash_chain.head.slice(0, 32)}…</div>
        </div>
        <div className="dest">
          <div className="dest-card hot">
            <div className="dh"><span className="dic"><Phone size={22} weight="fill" /></span>
              <span><div className="dt">{t("call_1930")}</div><div className="ds">{t("call_1930_s")}</div></span>
              <a className="go" href="tel:1930" style={{ color: "#fff", textDecoration: "none" }}>{lang === "hi" ? "कॉल" : "Call"}</a></div>
          </div>
          <div className="dest-card">
            <div className="dh"><span className="dic"><ShieldCheck size={22} weight="duotone" /></span>
              <span><div className="dt">{t("ncrp")}</div><div className="ds">{t("ncrp_s")}</div></span>
              <a className="go" href="https://cybercrime.gov.in" target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }}>{t("open_form")}</a></div>
            <dl className="fields">
              <dt>Category</dt><dd>{nc["Category of complaint"]}</dd>
              <dt>Sub-category</dt><dd>{nc["Sub-category of complaint"]}</dd>
              <dt>Suspect mobile</dt><dd>{prettyNum(nc["Suspect mobile number"])}</dd>
              <dt>Suspect UPI ID</dt><dd>{nc["Suspect UPI ID / bank account"]}</dd>
            </dl>
          </div>
          <div className="dest-card">
            <div className="dh"><span className="dic"><PhoneDisconnect size={22} weight="duotone" /></span>
              <span><div className="dt">{t("chakshu")}</div><div className="ds">{t("chakshu_s")}</div></span>
              <a className="go" href="https://sancharsaathi.gov.in/sfc/" target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }}>{t("open_form")}</a></div>
            <dl className="fields">
              <dt>Medium</dt><dd>{ch["Medium of suspected fraud communication"]}</dd>
              <dt>Category</dt><dd>{ch["Suspected fraud communication category"]}</dd>
              <dt>Number</dt><dd>{prettyNum(ch["Number from which communication received"])}</dd>
            </dl>
          </div>
        </div>
        <div className="warn-line" style={{ marginTop: 12 }}><Bank size={18} weight="bold" style={{ color: "var(--ink)" }} /><span>{t("bank_told", { bank: bankName })}. {t("no_recording")}</span></div>
        <a className="btn full" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, marginTop: 12, textDecoration: "none", color: "inherit" }}
          href={`${API}${pack.pdf_url}`} target="_blank" rel="noreferrer"><FilePdf size={18} /> {t("download_pdf")}</a>
      </div>
    </div>
  );
}
