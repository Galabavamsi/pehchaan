import { useEffect, useMemo, useState } from "react";
import { API } from "./api";
import { Seal } from "./components";

/** FINALE_PLAN A7: clone-vs-detect benchmark (ml/eval/clone_vs_detect.py). How convincing each cloner is (ClonEval
 *  speaker similarity) against how often each detector catches it, on clean audio, a phone codec and real calls. */
type Row = { n: number } & Record<string, number>;
type Cond = { all_speakers: Record<string, Row>; heldout_speaker_S02: Record<string, Row>; never_trained_rows: Record<string, Row> };
interface Result {
  method: string; models: Record<string, string>; fused_members: string[];
  conditions: { clean?: Cond; amr?: Cond; realcall?: { all: Record<string, Row>; by_device: Record<string, Record<string, Row>> } };
  generators: Record<string, { n: number; similarity_mean: number; similarity_sd: number; heldout: boolean; kind: string }>;
}

const GEN: Record<string, string> = {
  xtts: "XTTS-v2", f5: "F5-TTS", f5hi: "F5-TTS Hindi", cosyvoice2: "CosyVoice2", chatterbox: "Chatterbox",
  seedvc: "Seed-VC", sarvam_ivc: "Sarvam instant cloning", genuine: "Real voices",
};
const DET_ORDER = ["la", "nii", "v1", "A", "fused"];
const DET_SHORT: Record<string, string> = {
  la: "Off-the-shelf", nii: "NII MMS-300M", v1: "Ours v1", A: "Ours A", fused: "Fused",
};
// validated sequential ramp (dataviz reference palette, blue 100 → 700): magnitude only, one hue
const RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
  "#1c5cab", "#184f95", "#104281", "#0d366b"];
const heat = (v: number) => RAMP[Math.min(RAMP.length - 1, Math.round(v * (RAMP.length - 1)))];
const pct = (v: number | undefined) => (v == null || Number.isNaN(v) ? "–" : `${Math.round(v * 100)}%`);

const CONDS = [
  { id: "clean", label: "Clean audio" },
  { id: "amr", label: "Phone codec (AMR-NB)" },
  { id: "realcall", label: "Real phone calls" },
] as const;
type CondId = typeof CONDS[number]["id"];

export function BenchmarkPage() {
  const [r, setR] = useState<Result | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cond, setCond] = useState<CondId>("clean");
  const [heldoutSpk, setHeldoutSpk] = useState(false);
  useEffect(() => {
    fetch(`${API}/v1/benchmark`).then(async (x) => (x.ok ? setR(await x.json()) : setErr(`${x.status}: ${(await x.json()).detail}`)))
      .catch((e) => setErr(String(e)));
  }, []);

  const rows = useMemo(() => {
    if (!r) return null;
    const c = r.conditions[cond];
    if (!c) return null;
    if (cond === "realcall") return (c as Result["conditions"]["realcall"])!.all;
    return heldoutSpk ? (c as Cond).heldout_speaker_S02 : (c as Cond).all_speakers;
  }, [r, cond, heldoutSpk]);
  const dets = r ? DET_ORDER.filter((d) => rows && Object.values(rows).some((x) => d in x)) : [];
  const sim = (g: string) => r?.generators[g]?.similarity_mean;
  const clones = rows ? Object.keys(rows).filter((g) => g !== "genuine").sort((a, b) => (sim(b) ?? 0) - (sim(a) ?? 0)) : [];
  const name = (d: string) => (d === "fused" ? `Fused, 24 Oct (${(r?.fused_members ?? []).join(" + ")})` : r?.models[d] ?? d);

  return (
    <div className="tour">
      <header className="tour-top">
        <a href="#/tour" className="wm" style={{ textDecoration: "none", color: "inherit" }}>
          <Seal size={26} /><span className="w">Pehchaan</span><span className="whi">पहचान</span>
        </a>
        <span className="tag">Clone vs detect: how convincing, how detectable</span>
      </header>
      <main className="tour-body">
        <h1>How convincing is each cloner, and which detector still catches it?</h1>
        <p className="tour-lede">
          Every clone of our two consenting teammates, scored by every detector at its own threshold. <b>Speaker similarity</b> is
          ClonEval's measure (arXiv:2504.20581): how close a clone sounds to the real speaker to a speaker-recognition model
          (WavLM). The same files then go through a phone codec, and real phone calls come from our pre-registered test split.
        </p>
        <div className="panel" style={{ margin: "4px 0 16px" }}>
          <div className="sec-t">Read this first</div>
          <ul className="fine" style={{ margin: "6px 0 10px", paddingLeft: 18, display: "grid", gap: 4 }}>
            <li><b>Scored on 24 Oct</b>, before our reference model n3 existed. n3's results are in the table below (FINDINGS, v5).</li>
            <li><b>Off-the-shelf</b> (XLS-R + AASIST) and <b>NII MMS-300M</b> are public models, shown for comparison only.
              <b> Ours v1</b> and <b>Ours A</b> are trained by us.</li>
            <li><b>Fused, 24 Oct</b> was the plain average of A, NII and v1, retired on 25 Oct. It shows why averaging fails:
              on clean Sarvam clones NII caught 71/71, A and v1 caught 0/71, and the average caught 0/71.</li>
            <li>Since 25 Oct the bench's headline is <b>n3</b>: our model, fine-tuned by us on our data starting from NII's
              published weights, so it inherits NII's non-commercial licence.</li>
          </ul>
          <table className="rtable">
            <thead><tr><th>Real phone calls, 510 test clips</th><th>EER</th><th>Genuine flagged</th><th>Clones caught</th><th>Sarvam clones, unseen speaker</th></tr></thead>
            <tbody>
              <tr className="fused-row"><td><b>n3, our reference</b></td><td className="mono">7.8 %</td><td className="mono">3/256</td><td className="mono">190/254</td><td className="mono">0/12</td></tr>
              <tr><td>A, ours (previous)</td><td className="mono">11.0 %</td><td className="mono">11/256</td><td className="mono">204/254</td><td className="mono">0/12</td></tr>
              <tr><td>NII, public, used as is</td><td className="mono">51.2 %</td><td className="mono">144/256</td><td className="mono">133/254</td><td className="mono">10/12</td></tr>
            </tbody>
          </table>
          <p className="fine" style={{ marginTop: 6 }}>NII "catches" Sarvam on calls only by flagging 56 % of genuine callers. No detector is good
            enough to decide on its own, which is why Pehchaan verifies the person instead. Source: ml/realcall/FINDINGS.md, v5 section.</p>
        </div>
        {err && (err.startsWith("404")
          ? <p className="bm-note" title={err}>The results are being re-scored with the detector bench's scoring plan. They appear here
              as soon as that run finishes.</p>
          : <p className="bm-err" title={err}>The benchmark results could not be loaded right now. Please try again in a minute.</p>)}
        {r && rows && (<>
          <div className="bm-ctl">
            <div className="seg" role="group" aria-label="Condition">
              {CONDS.map((c) => <button key={c.id} aria-pressed={cond === c.id} onClick={() => setCond(c.id)}>{c.label}</button>)}
            </div>
            {cond !== "realcall" && (
              <label className="bm-check"><input type="checkbox" checked={heldoutSpk} onChange={(e) => setHeldoutSpk(e.target.checked)} />
                Only the speaker no model was trained on (S02)</label>
            )}
          </div>

          <div className="bm-tablewrap">
            <table className="bm-table">
              <thead>
                <tr><th>Cloner</th><th className="num">Clips</th><th className="num">Speaker similarity</th>
                  {dets.map((d) => <th key={d} className="num" title={name(d)}>{DET_SHORT[d]}</th>)}</tr>
              </thead>
              <tbody>
                {clones.map((g) => (
                  <tr key={g}>
                    <td className="gen">{GEN[g] ?? g}{r.generators[g]?.heldout && <span className="bm-ho">never trained on</span>}</td>
                    <td className="num mono">{rows[g].n}</td>
                    <td className="num mono">{sim(g) != null ? `${sim(g)!.toFixed(3)} ± ${r.generators[g].similarity_sd.toFixed(3)}` : "–"}</td>
                    {dets.map((d) => (
                      <td key={d} className="num mono heat" title={`${name(d)}: caught ${pct(rows[g][d])} of ${rows[g].n} ${GEN[g] ?? g} clips`}
                        style={{ background: heat(rows[g][d] ?? 0), color: (rows[g][d] ?? 0) > 0.5 ? "#fff" : "var(--ink)" }}>
                        {pct(rows[g][d])}</td>
                    ))}
                  </tr>
                ))}
                {rows.genuine && (
                  <tr className="bm-gen">
                    <td className="gen">Real voices, wrongly flagged <span className="bm-low">lower is better</span></td>
                    <td className="num mono">{rows.genuine.n}</td>
                    <td className="num mono">{sim("genuine") != null ? `${sim("genuine")!.toFixed(3)} (ceiling)` : "–"}</td>
                    {dets.map((d) => <td key={d} className="num mono"><b>{pct(rows.genuine[d])}</b></td>)}
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="bm-note">Cells: share of each cloner's clips caught (darker = more caught). Columns, left to right: {dets.map((d) => name(d)).join(" · ")}.
            The real-voice similarity is one real recording against the same speaker's others: the most a real voice reaches.</p>

          <h2 className="bm-h2">Does a more convincing clone get past the detector?</h2>
          <p className="bm-note" style={{ marginTop: 0 }}>One panel per detector. Across: speaker similarity (clean audio). Up: share caught in the condition above.
            Hollow rings are cloners no model was trained on.</p>
          <div className="bm-multi">
            {dets.map((d) => <Panel key={d} title={name(d)} points={clones.filter((g) => sim(g) != null && rows[g][d] != null).map((g) => ({
              g, x: sim(g)!, y: rows[g][d], held: !!r.generators[g]?.heldout, n: rows[g].n }))} flagged={rows.genuine?.[d]} />)}
          </div>
          <p className="tour-foot">
            Two consenting speakers, content-matched lines, one run; thresholds are each detector's equal-error point on our simulated
            test sample, unchanged. Per-clip scores stay on the laptop with the audio. Source: ml/results/clone_vs_detect.json, made by
            ml/eval/clone_vs_detect.py; caveats in ml/realcall/FINDINGS.md.
          </p>
        </>)}
      </main>
    </div>
  );
}

/** One small-multiple scatter: single series, x = similarity, y = caught. Hover a dot for its numbers. */
function Panel({ title, points, flagged }: { title: string; points: { g: string; x: number; y: number; held: boolean; n: number }[]; flagged?: number }) {
  const [hover, setHover] = useState<string | null>(null);
  const W = 300, H = 210, L = 34, R = 10, T = 12, B = 30;
  const xs = points.map((p) => p.x);
  const x0 = Math.min(0.5, ...xs) - 0.02, x1 = Math.max(0.95, ...xs) + 0.02;
  const sx = (v: number) => L + ((v - x0) / (x1 - x0)) * (W - L - R);
  const sy = (v: number) => T + (1 - v) * (H - T - B);
  const hp = points.find((p) => p.g === hover);
  return (
    <figure className="bm-panel">
      <figcaption>{title}{flagged != null && <span className="bm-fl">real voices flagged: {pct(flagged)}</span>}</figcaption>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title}: share caught against speaker similarity`}>
        {[0, 0.5, 1].map((v) => (
          <g key={v}><line x1={L} x2={W - R} y1={sy(v)} y2={sy(v)} stroke="#e1e9f8" strokeWidth={1} />
            <text x={L - 6} y={sy(v) + 4} textAnchor="end" className="bm-ax">{v * 100}%</text></g>
        ))}
        {[0.6, 0.7, 0.8, 0.9].filter((v) => v > x0 && v < x1).map((v) => (
          <text key={v} x={sx(v)} y={H - 10} textAnchor="middle" className="bm-ax">{v.toFixed(1)}</text>
        ))}
        <line x1={L} x2={W - R} y1={sy(0)} y2={sy(0)} stroke="#c3cfe6" strokeWidth={1} />
        {points.map((p) => (
          <g key={p.g} onMouseEnter={() => setHover(p.g)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}>
            <circle cx={sx(p.x)} cy={sy(p.y)} r={14} fill="transparent" />
            <circle cx={sx(p.x)} cy={sy(p.y)} r={5} fill={p.held ? "#ffffff" : "#2a78d6"} stroke="#2a78d6" strokeWidth={2} />
          </g>
        ))}
        {hp && (
          <g pointerEvents="none">
            <rect x={Math.min(sx(hp.x) + 8, W - 128)} y={Math.max(sy(hp.y) - 34, 2)} width={120} height={30} rx={6} fill="#111d3c" opacity={0.92} />
            <text x={Math.min(sx(hp.x) + 14, W - 122)} y={Math.max(sy(hp.y) - 20, 16)} className="bm-tip">{GEN[hp.g] ?? hp.g}</text>
            <text x={Math.min(sx(hp.x) + 14, W - 122)} y={Math.max(sy(hp.y) - 8, 28)} className="bm-tip">sim {hp.x.toFixed(3)} · caught {pct(hp.y)}</text>
          </g>
        )}
      </svg>
    </figure>
  );
}
