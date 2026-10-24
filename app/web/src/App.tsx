import { useEffect, useLayoutEffect, useState } from "react";
import { ArrowClockwise, Phone } from "@phosphor-icons/react";
import { API, api, subscribe, urlParam, type Lang, type Scenario } from "./api";
import { Bench } from "./Bench";
import { BenchmarkPage } from "./Benchmark";
import { JuryPanel } from "./JuryPanel";
import { RedTeamPage, Tour } from "./Tour";
import { Console } from "./Console";
import { PayerPhone } from "./PayerPhone";
import { RelativePhone } from "./RelativePhone";
import { Seal } from "./components";

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
  const route = useRoute();
  const lang = (urlParam("lang") as Lang) || undefined;
  if (route === "console") return <Console follow={urlParam("follow") === "1"} />;
  if (route === "bench") return <Bench />;
  if (route === "tour") return <Tour />;
  if (route === "redteam") return <RedTeamPage />;
  if (route === "benchmark") return <BenchmarkPage />;
  if (route === "payer") return <Standalone kind="payer" lang={lang} />;
  if (route === "relative") return <Standalone kind="relative" lang={lang} />;
  return <DemoControl />;
}

function Standalone({ kind, lang }: { kind: "payer" | "relative"; lang?: Lang }) {
  const { sc, n } = useScenario(kind === "payer" ? urlParam("scenario") : null);
  if (!sc) return <div className="empty">Load a scenario from the demo page first.</div>;
  return (
    <div style={{ padding: 24, display: "flex", justifyContent: "center" }}>
      {kind === "payer"
        ? <PayerPhone key={n} scenario={sc} initialLang={lang ?? "en"} initialLarge={urlParam("large") === "1"} />
        : sc.relative ? <RelativePhone key={n} relative={sc.relative} payerName={sc.payer.name} payerNameHi={sc.payer.name_hi} initialLang={lang ?? "en"} />
          : <div className="empty">This scenario has no relative.</div>}
    </div>
  );
}

function DemoControl() {
  const first = urlParam("scenario") || "T1";
  const { sc, n, load } = useScenario(first);
  const [jury, setJury] = useState(() => urlParam("jury") === "1");
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
        <button className="chipbtn" aria-pressed={sc?.scenario === "CUSTOM"} onClick={() => setJury(true)} data-testid="jury-open"
          style={{ minHeight: 40, padding: "0 12px" }}>Your case</button>
        <button className="chipbtn" onClick={() => sc && load(sc.scenario)} aria-label="Restart scenario" style={{ minHeight: 40, padding: "0 12px" }}>
          <ArrowClockwise size={16} weight="bold" /> Restart
        </button>
        <a className="chipbtn" href="#/bench" style={{ minHeight: 40, padding: "0 12px", textDecoration: "none" }}>Detector bench</a>
      </header>
      {jury && <JuryPanel current={sc} onClose={() => setJury(false)} />}
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
