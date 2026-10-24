import { useEffect, useLayoutEffect, useState } from "react";
import { ArrowClockwise, CheckCircle, Phone, Users, Wallet, XCircle } from "@phosphor-icons/react";
import { API, api, subscribe, urlParam, type Lang, type Scenario } from "./api";
import { Console } from "./Console";
import { PayerPhone } from "./PayerPhone";
import { RelativePhone } from "./RelativePhone";
import { Device, Seal } from "./components";
import { DemoPayApp } from "./DemoPayApp";
import { isNative, Pehchaan, ROLE_KEY, savedRole, type NativeStatus, type Role } from "./native";
import { QrCards } from "./QrCards";
import type { Relative } from "./api";

const SCEN: { id: string; label: string }[] = [
  { id: "T1", label: "Cloned son, +44" },
  { id: "T2", label: "Fake bank call" },
  { id: "T3", label: "Digital arrest" },
  { id: "L1", label: "Paying a friend" },
  { id: "L2", label: "Real son, new number" },
];

function useRoute() {
  const [r, setR] = useState(() => location.hash.replace(/^#\/?/, "").split("?")[0] || "demo");
  useEffect(() => {
    const f = () => setR(location.hash.replace(/^#\/?/, "").split("?")[0] || "demo");
    addEventListener("hashchange", f);
    return () => removeEventListener("hashchange", f);
  }, []);
  return r;
}

/** Current scenario: load it (POST) if asked to, otherwise follow whatever the demo page loaded. */
function useScenario(loadName: string | null) {
  const [sc, setSc] = useState<Scenario | null>(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    if (loadName) api.scenario(loadName).then((s) => { setSc(s); setN((x) => x + 1); });
    else fetch(`${API}/v1/demo/current`).then((r) => (r.ok ? r.json() : null)).then((s) => s && setSc(s));
    return subscribe("/ws/demo", (m) => { if (m.type === "scenario") { setSc(m.data); setN((x) => x + 1); } });
  }, [loadName]);
  const load = async (name: string) => { await api.scenario(name); };
  return { sc, n, load };
}

export function App() {
  if (isNative) return <NativeApp />;
  return <WebApp />;
}

function WebApp() {
  const route = useRoute();
  const lang = (urlParam("lang") as Lang) || undefined;
  if (route === "console") return <Console follow={urlParam("follow") === "1"} />;
  if (route === "payer") return <Standalone kind="payer" lang={lang} />;
  if (route === "relative") return <Standalone kind="relative" lang={lang} />;
  // Laptop helpers for the Android demo: the payer app in a phone frame, and payee QR cards to scan
  if (route === "app") return <div className="theme-app" style={{ padding: 24, display: "flex", justifyContent: "center" }}><Device><DemoPayApp /></Device></div>;
  if (route === "qr") return <QrCards />;
  return <DemoControl />;
}

function Standalone({ kind, lang }: { kind: "payer" | "relative"; lang?: Lang }) {
  const { sc, n } = useScenario(kind === "payer" ? urlParam("scenario") : null);
  if (!sc) return <div className="empty">Load a scenario from the demo page first.</div>;
  // The Android app stays enrolled as the payer's relative whichever scenario the demo page has loaded.
  const relative = sc.relative ?? (isNative ? sc.payer.circle[0] : null);
  return (
    <div style={{ padding: isNative ? 0 : 24, display: "flex", justifyContent: "center" }}>
      {kind === "payer"
        ? <PayerPhone key={n} scenario={sc} initialLang={lang ?? "en"} initialLarge={urlParam("large") === "1"} />
        : relative ? <RelativePhone key={n} relative={relative} payerName={sc.payer.name} payerNameHi={sc.payer.name_hi} initialLang={lang ?? "en"} />
          : <div className="empty">This scenario has no relative.</div>}
    </div>
  );
}

function DemoControl() {
  const first = urlParam("scenario") || "T1";
  const { sc, n, load } = useScenario(first);
  const [scale, setScale] = useState(1);
  useLayoutEffect(() => {
    const forced = Number(urlParam("scale"));
    const f = () => setScale(forced || Math.min(1, Math.max(0.6, (innerHeight - 150) / 900)));
    f();
    addEventListener("resize", f);
    return () => removeEventListener("resize", f);
  }, []);
  const phoneW = 412 * scale, phoneH = 866 * scale;
  return (
    <div className="demo" data-testid="demo">
      <header className="demo-top">
        <span className="wm"><Seal size={26} /><span className="w">Pehchaan</span><span className="whi">पहचान</span></span>
        <span className="tag">Verify the person, not the voice.</span>
        <span className="grow" />
        <div className="scen" role="group" aria-label="Scenario">
          {SCEN.map((s) => (
            <button key={s.id} aria-pressed={sc?.scenario === s.id} onClick={() => load(s.id)} data-testid={`scen-${s.id}`}>
              <b>{s.id}</b><span>{s.label}</span>
            </button>
          ))}
        </div>
        <button className="chipbtn" onClick={() => sc && load(sc.scenario)} aria-label="Restart scenario" style={{ minHeight: 40, padding: "0 12px" }}>
          <ArrowClockwise size={16} weight="bold" /> Restart
        </button>
      </header>
      {sc && (
        <div className="demo-script">
          <Phone size={16} weight="fill" />
          <span className="lab">{sc.pattern}</span>
          <span className="q">{sc.script}</span>
          <span style={{ marginLeft: "auto", color: "var(--slate)", fontSize: 13 }}>Fictional people and numbers · context adapters are mocks</span>
        </div>
      )}
      {sc && (
        <div className="demo-stage">
          <div className="demo-col">
            <div className="cl">{sc.payer.name}'s phone <small>payer · {sc.payer.age_band}</small></div>
            <div style={{ width: phoneW, height: phoneH }}>
              <div className="scaled" style={{ transform: `scale(${scale})` }}>
                <PayerPhone key={`p${n}`} scenario={sc} initialLang={(urlParam("lang") as Lang) || "en"} />
              </div>
            </div>
          </div>
          <div className="demo-col">
            <div className="cl">{sc.relative ? `${sc.relative.name}'s phone` : "Relative's phone"} <small>{sc.relative ? `${sc.relative.relation} · ${sc.relative.lives_in ?? ""}` : "not part of this scenario"}</small></div>
            <div style={{ width: phoneW, height: phoneH }}>
              <div className="scaled" style={{ transform: `scale(${scale})` }}>
                {sc.relative ? <RelativePhone key={`r${n}`} relative={sc.relative} payerName={sc.payer.name} payerNameHi={sc.payer.name_hi} />
                  : <div className="device" style={{ opacity: 0.35 }}><div className="screen" style={{ display: "grid", placeItems: "center", color: "var(--slate)" }}>No Family Verify in this scenario</div></div>}
              </div>
            </div>
          </div>
          <div className="demo-col" style={{ alignItems: "stretch", minWidth: 0, height: phoneH + 30 }}>
            <div className="cl">Bharat Demo Bank console <small>fraud analyst</small></div>
            <div className="console-frame" style={{ minHeight: 0, height: phoneH }}>
              <Console key={`c${n}`} compact follow />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Android app (SPEC §7)

/** One APK, two roles: the payer's phone (DemoPay) or the relative's phone (Pehchaan Family). */
function NativeApp() {
  const [role, setRole] = useState<Role | null>(savedRole);
  const [setup, setSetup] = useState(() => !savedRole());
  useEffect(() => {
    if (role === "payer") Pehchaan.startProtection({ role: "payer", api: API }).catch(() => {});
  }, [role]);
  // Routes from outside the web layer (the launch route is read once, so one handler takes all of them):
  // "setup" from the status notification's Setup action, "upi:…" from a UPI QR or link opened with DemoPay
  const [upi, setUpi] = useState<string | null>(null);
  useEffect(() => {
    const take = (r: string | null) => {
      if (r === "setup") setSetup(true);
      else if (r?.startsWith("upi:")) setUpi(r.slice(4));
    };
    Pehchaan.getLaunchRoute().then((x) => take(x.route)).catch(() => {});
    const h = Pehchaan.addListener("route", (x) => take(x.route));
    return () => { h.then((x) => x.remove()); };
  }, []);
  if (!role || setup) {
    return <NativeSetup role={role} onDone={(r) => {
      try { localStorage.setItem(ROLE_KEY, r); } catch { /* ignore */ }
      setRole(r); setSetup(false);
    }} />;
  }
  return role === "payer" ? <DemoPayApp incomingUpi={upi} onUpiHandled={() => setUpi(null)} /> : <NativeFamily />;
}

/** The family phone is always Rahul in Sunita's circle, whichever scenario the demo page has loaded. */
const RAHUL: Relative = {
  id: "rel_rahul", name: "Rahul", name_hi: "राहुल", full_name: "Rahul Sharma", relation: "son", relation_hi: "बेटा", pronoun: "he",
  device_id: "dev_rahul", lives_in: "London", calls_payer: "Mummy", calls_payer_hi: "मम्मी",
};
function NativeFamily() {
  const [rel, setRel] = useState<Relative>(RAHUL);
  useEffect(() => {
    fetch(`${API}/v1/demo/current`).then((r) => (r.ok ? r.json() : null)).then((sc: Scenario | null) => {
      const r = sc?.payer?.id === "u_sunita" ? sc.payer.circle.find((x) => x.id === RAHUL.id) : null;
      if (r) setRel(r);
    }).catch(() => {});
  }, []);
  return <RelativePhone relative={rel} payerName="Sunita Sharma" payerNameHi="सुनीता शर्मा" />;
}

function NativeSetup({ role, onDone }: { role: Role | null; onDone: (r: Role) => void }) {
  const [pick, setPick] = useState<Role | null>(role);
  const [st, setSt] = useState<NativeStatus | null>(null);
  const refresh = () => Pehchaan.status().then(setSt).catch(() => {});
  useEffect(() => {
    refresh();
    const f = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", f);
    return () => document.removeEventListener("visibilitychange", f);
  }, []);

  async function choose(r: Role) {
    setPick(r);
    setSt(await Pehchaan.requestForRole({ role: r }).catch(() => null) ?? await Pehchaan.status().catch(() => null));
  }

  if (!pick) {
    return (
      <div className="native-setup">
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Seal size={26} /><b>Pehchaan</b><span>पहचान</span></span>
        <h1>Who is using this phone?</h1>
        <button className="role" onClick={() => choose("payer")} data-testid="role-payer">
          <Wallet size={30} weight="duotone" />
          <span><b>I'm paying</b><span>DemoPay with Pehchaan. Checks payments made during or just after a call.</span></span>
        </button>
        <button className="role" onClick={() => choose("relative")} data-testid="role-relative">
          <Users size={30} weight="duotone" />
          <span><b>I'm family</b><span>Pehchaan Family. You're asked when someone uses your name to ask for money.</span></span>
        </button>
        <p style={{ marginTop: "auto", fontSize: 13 }}>Demo app: fictional bank, people and UPI IDs. Pehchaan never records or listens to calls.</p>
      </div>
    );
  }

  const rows: { ok: boolean | undefined; label: string; fix: () => void }[] = pick === "payer" ? [
    { ok: st?.phone, label: "Call state (on a call or not)", fix: () => choose("payer") },
    { ok: st?.call_log, label: "Caller's number (call log)", fix: () => choose("payer") },
    { ok: st?.contacts, label: "Contacts, matched on this phone", fix: () => choose("payer") },
    { ok: st?.battery_unrestricted, label: "Battery: no restrictions", fix: () => { Pehchaan.openSettings({ which: "battery" }); } },
  ] : [
    { ok: st?.notifications, label: "Notifications", fix: () => choose("relative") },
    { ok: st?.full_screen, label: "Full-screen alerts on the lock screen", fix: () => { Pehchaan.openSettings({ which: "fullscreen" }); } },
    { ok: st?.battery_unrestricted, label: "Battery: no restrictions", fix: () => { Pehchaan.openSettings({ which: "battery" }); } },
  ];
  return (
    <div className="native-setup">
      <h1>{pick === "payer" ? "DemoPay setup" : "Pehchaan Family setup"}</h1>
      <p>{pick === "payer"
        ? "Pehchaan reads only whether you're on a call, the caller's number and whether it's saved. Contacts and calls never leave this phone."
        : "Keep this phone signed in. When a relative is about to pay someone who said they are you, this phone asks you first."}</p>
      <div>
        {rows.map((r) => (
          <div className="check" key={r.label}>
            {r.ok ? <CheckCircle size={22} weight="fill" className="ok" /> : <XCircle size={22} weight="fill" className="no" />}
            <span>{r.label}</span>
            {!r.ok && <button className="chipbtn" onClick={r.fix}>Allow</button>}
          </div>
        ))}
      </div>
      <p style={{ fontSize: 13 }}>On Xiaomi phones also turn on Settings → Apps → DemoPay → Autostart.
        {st && !st.screen_share_detect && " Screen-share detection needs Android 15 or later."}</p>
      <div style={{ marginTop: "auto", display: "grid", gap: 10 }}>
        <button className="btn solid full" onClick={() => onDone(pick)} data-testid="setup-done">Continue</button>
        <button className="btn ghost full" onClick={() => setPick(null)}>Change role</button>
      </div>
    </div>
  );
}
