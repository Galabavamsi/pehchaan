import { useEffect, useLayoutEffect, useState } from "react";
import { ArrowClockwise, CheckCircle, Phone, XCircle } from "@phosphor-icons/react";
import { API, api, subscribe, urlParam, type Lang, type Scenario } from "./api";
import { Console } from "./Console";
import { PayerPhone } from "./PayerPhone";
import { RelativePhone } from "./RelativePhone";
import { Device, Seal } from "./components";
import { DemoPayApp } from "./DemoPayApp";
import { isNative, Pehchaan, rehearsal, type NativeStatus } from "./native";
import { PEOPLE, savedPerson, savePerson, type PersonKey } from "./people";
import { QrCards } from "./QrCards";

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
  if (route === "app") {
    const me = PEOPLE[(urlParam("me") as PersonKey) || "sunita"] ?? PEOPLE.sunita;
    return <div className="theme-app" style={{ padding: 24, display: "flex", justifyContent: "center" }}><Device><DemoPayApp me={me} /></Device></div>;
  }
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

/** One app on both phones: DemoPay for this phone's person, with Family Verify for the other person built in. */
function NativeApp() {
  const [who, setWho] = useState<PersonKey | null>(savedPerson);
  const [setup, setSetup] = useState(() => !savedPerson());
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
  if (!who || setup) {
    return <NativeSetup who={who} onDone={(k) => { savePerson(k); setWho(k); setSetup(false); }} />;
  }
  return <DemoPayApp key={who} me={PEOPLE[who]} incomingUpi={upi} onUpiHandled={() => setUpi(null)} />;
}

function NativeSetup({ who, onDone }: { who: PersonKey | null; onDone: (k: PersonKey) => void }) {
  const [pick, setPick] = useState<PersonKey | null>(who);
  const [st, setSt] = useState<NativeStatus | null>(null);
  const [reh, setReh] = useState(rehearsal.get);
  const refresh = () => Pehchaan.status().then(setSt).catch(() => {});
  useEffect(() => {
    refresh();
    const f = () => { if (document.visibilityState === "visible") refresh(); };
    document.addEventListener("visibilitychange", f);
    return () => document.removeEventListener("visibilitychange", f);
  }, []);

  async function choose(k: PersonKey) {
    setPick(k);
    setSt(await Pehchaan.requestForRole({ role: "payer" }).catch(() => null) ?? await Pehchaan.status().catch(() => null));
  }

  if (!pick) {
    return (
      <div className="native-setup">
        <span style={{ display: "flex", alignItems: "center", gap: 8 }}><Seal size={26} /><b>DemoPay</b><span>with Pehchaan</span></span>
        <h1>Who is using this phone?</h1>
        <p>Both phones can pay. Each one also answers when someone uses its person's name to ask the other for money.</p>
        {(["sunita", "rahul"] as PersonKey[]).map((k) => (
          <button key={k} className="role" onClick={() => choose(k)} data-testid={`me-${k}`}>
            <span className="dp-av">{PEOPLE[k].payer.name.split(" ").map((w) => w[0]).join("")}</span>
            <span><b>{PEOPLE[k].payer.name}</b><span>{PEOPLE[k].blurb} · {PEOPLE[k].payer.vpa}</span></span>
          </button>
        ))}
        <p style={{ marginTop: "auto", fontSize: 13 }}>Demo app: fictional bank, people and UPI IDs. Pehchaan never records or listens to calls.</p>
      </div>
    );
  }

  const rows: { ok: boolean | undefined; label: string; fix: () => void }[] = [
    { ok: st?.phone, label: "Call state (on a call or not)", fix: () => choose(pick) },
    { ok: st?.call_log, label: "Caller's number (call log)", fix: () => choose(pick) },
    { ok: st?.contacts, label: "Contacts, matched on this phone", fix: () => choose(pick) },
    { ok: st?.notifications, label: "Notifications (Family Verify)", fix: () => choose(pick) },
    { ok: st?.full_screen, label: "Alerts over the lock screen", fix: () => { Pehchaan.openSettings({ which: "fullscreen" }); } },
    { ok: st?.battery_unrestricted, label: "Battery: no restrictions", fix: () => { Pehchaan.openSettings({ which: "battery" }); } },
  ];
  const p = PEOPLE[pick];
  return (
    <div className="native-setup">
      <h1>{p.payer.name}</h1>
      <p>Pehchaan reads only whether you're on a call, the caller's number and whether it's saved. Contacts and calls never leave this phone.</p>
      <div>
        {rows.map((r) => (
          <div className="check" key={r.label}>
            {r.ok ? <CheckCircle size={22} weight="fill" className="ok" /> : <XCircle size={22} weight="fill" className="no" />}
            <span>{r.label}</span>
            {!r.ok && <button className="chipbtn" onClick={r.fix}>Allow</button>}
          </div>
        ))}
      </div>
      <label className="check rehearsal">
        <input type="checkbox" checked={reh} onChange={(e) => { rehearsal.set(e.target.checked); setReh(e.target.checked); }} />
        <span>Rehearsal mode: treat every caller as unknown
          <small>For practice when all your numbers are saved on this phone. Turn it off for the real demo.</small></span>
      </label>
      <p style={{ fontSize: 13 }}>On Xiaomi phones also turn on Settings → Apps → DemoPay → Autostart.
        {st && !st.screen_share_detect && " Screen-share detection needs Android 15 or later."}</p>
      <div style={{ marginTop: "auto", display: "grid", gap: 10 }}>
        <button className="btn solid full" onClick={() => onDone(pick)} data-testid="setup-done">Continue as {p.payer.name.split(" ")[0]}</button>
        <button className="btn ghost full" onClick={() => setPick(null)}>Someone else uses this phone</button>
      </div>
    </div>
  );
}
