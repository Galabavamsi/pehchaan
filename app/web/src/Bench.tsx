import { useEffect, useMemo, useRef, useState } from "react";
import { DownloadSimple, Microphone, Stop, UploadSimple, WarningCircle } from "@phosphor-icons/react";
import { api, type PanelResult } from "./api";
import { Seal } from "./components";

type Label = "unknown" | "genuine" | "clone";
interface Row { id: number; name: string; label: Label; status: "queued" | "scoring" | "done" | "error"; res?: PanelResult; err?: string }

const MODEL_ORDER = ["n3", "v1", "A", "nii", "la"];
const SHORT_NAME: Record<string, string> = { v1: "Ours v1", A: "Ours A", nii: "NII", la: "Off-the-shelf", n3: "Ours n3" };

/** Guess a label from the file name (judges can change it): only used for the accuracy summary. */
function guessLabel(name: string): Label {
  const n = name.toLowerCase();
  if (/(fake|clone|cloned|tts|synth|spoof|deepfake|generated|ai[_-])/.test(n)) return "clone";
  if (/(real|genuine|bona|human|original)/.test(n)) return "genuine";
  return "unknown";
}

function Verdict({ v, small = false }: { v?: "synthetic" | "genuine"; small?: boolean }) {
  if (!v) return <span className="bv bv-none">–</span>;
  return <span className={`bv ${v === "synthetic" ? "bv-syn" : "bv-gen"} ${small ? "bv-sm" : ""}`}>{v === "synthetic" ? "Clone" : "Genuine"}</span>;
}

export function Bench() {
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [rec, setRec] = useState<MediaRecorder | null>(null);
  const [drag, setDrag] = useState(false);
  const nextId = useRef(1);
  const fileRef = useRef<HTMLInputElement>(null);
  const queue = useRef<{ id: number; blob: Blob; name: string }[]>([]);

  const update = (id: number, patch: Partial<Row>) => setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)));

  const pump = async () => {
    if (busy) return;
    setBusy(true);
    while (queue.current.length) {
      const job = queue.current.shift()!;
      update(job.id, { status: "scoring" });
      try { update(job.id, { status: "done", res: await api.panel(job.blob, job.name) }); }
      catch (e: any) { update(job.id, { status: "error", err: String(e.message || e) }); }
    }
    setBusy(false);
  };

  const add = (files: { blob: Blob; name: string }[]) => {
    const fresh = files.map((f) => ({ id: nextId.current++, ...f }));
    setRows((rs) => [...rs, ...fresh.map((f) => ({ id: f.id, name: f.name, label: guessLabel(f.name), status: "queued" as const }))]);
    queue.current.push(...fresh);
    setTimeout(pump, 0);
  };

  // The microphone must never outlive the page: stop it on leave, even if access is granted after we left.
  const alive = useRef(true);
  const starting = useRef(false);
  const recRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  useEffect(() => () => {
    alive.current = false;
    const r = recRef.current;
    if (r && r.state !== "inactive") { r.onstop = null; r.stop(); }
    streamRef.current?.getTracks().forEach((t) => t.stop());
  }, []);

  const record = async () => {
    if (rec) { rec.stop(); return; }
    if (starting.current) return;
    starting.current = true;
    let stream: MediaStream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } finally { starting.current = false; }
    if (!alive.current) { stream.getTracks().forEach((t) => t.stop()); return; }
    const mr = new MediaRecorder(stream);
    streamRef.current = stream;
    recRef.current = mr;
    const chunks: Blob[] = [];
    mr.ondataavailable = (e) => chunks.push(e.data);
    mr.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      recRef.current = null;
      if (!alive.current) return;
      setRec(null);
      add([{ blob: new Blob(chunks, { type: mr.mimeType }), name: `mic-${new Date().toLocaleTimeString()}.webm` }]);
    };
    mr.start();
    setRec(mr);
  };

  const models = useMemo(() => {
    const seen = new Set<string>();
    rows.forEach((r) => r.res?.models.forEach((m) => seen.add(m.id)));
    return MODEL_ORDER.filter((m) => seen.has(m));
  }, [rows]);

  const fused = rows.find((r) => r.res?.fused)?.res?.fused;
  // one member = the headline is that detector alone (the laptop runs the reference model n3 this way)
  const headName = fused?.members.length === 1 ? `Pehchaan (${SHORT_NAME[fused.members[0]] ?? fused.members[0]})` : "Pehchaan fused";

  const summary = useMemo(() => {
    const done = rows.filter((r) => r.status === "done" && r.res && r.label !== "unknown");
    const score = (pick: (r: Row) => string | undefined) => {
      let ok = 0, fp = 0, miss = 0, gen = 0, cl = 0;
      done.forEach((r) => {
        const v = pick(r);
        if (!v) return;
        const syn = v === "synthetic";
        if (r.label === "genuine") { gen++; if (syn) fp++; else ok++; } else { cl++; if (syn) ok++; else miss++; }
      });
      return { ok, n: gen + cl, fp, gen, miss, cl };
    };
    const out: { id: string; name: string; s: ReturnType<typeof score> }[] = [
      { id: "fused", name: headName, s: score((r) => r.res?.fused?.verdict) },
      ...models.map((m) => ({ id: m, name: SHORT_NAME[m] ?? m, s: score((r) => r.res?.models.find((x) => x.id === m)?.verdict) })),
    ];
    return { labelled: done.length, out };
  }, [rows, models, headName]);

  const csv = () => {
    const head = ["file", "label", "audio_s", "speech_s", "fused", ...models.flatMap((m) => [`${m}_verdict`, `${m}_z`])];
    const lines = rows.filter((r) => r.res).map((r) => [r.name, r.label, r.res!.audio_seconds, r.res!.quality.speech_sec,
      r.res!.fused?.verdict ?? "", ...models.flatMap((m) => { const x = r.res!.models.find((y) => y.id === m); return [x?.verdict ?? "", x?.z ?? ""]; })]);
    // quote every field that needs it (a filename may hold commas, quotes or line breaks), and keep spreadsheet
    // formulas out of text cells
    const cell = (v: unknown) => {
      let t = String(v ?? "");
      if (typeof v === "string" && /^[=+\-@]/.test(t) && Number.isNaN(Number(t))) t = `'${t}`;
      return /[",\r\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
    };
    const blob = new Blob([[head, ...lines].map((l) => l.map(cell).join(",")).join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "pehchaan-bench.csv";
    a.click();
  };

  return (
    <div className="bench" data-testid="bench">
      <header className="demo-top">
        <span className="wm"><Seal size={26} /><span className="w">Pehchaan</span><span className="whi">पहचान</span></span>
        <span className="tag">Detector bench · every model on your audio, side by side</span>
        <span className="grow" />
        <a className="chipbtn" href="#/demo" style={{ minHeight: 40, padding: "0 12px", textDecoration: "none" }}>Live demo</a>
      </header>

      <div className="bench-body">
        <div
          className={`bench-drop ${drag ? "on" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); add([...e.dataTransfer.files].map((f) => ({ blob: f, name: f.name }))); }}
        >
          <UploadSimple size={28} />
          <div><b>Drop audio files here</b> (wav, mp3, m4a, ogg, webm, any length; up to 60 s of each is scored)</div>
          <div className="btn-row">
            <button className="chipbtn" onClick={() => fileRef.current?.click()}><UploadSimple size={16} /> Choose files</button>
            <button className="chipbtn" onClick={record} aria-pressed={!!rec}>{rec ? <><Stop size={16} /> Stop recording</> : <><Microphone size={16} /> Record from mic</>}</button>
            {rows.some((r) => r.res) && <button className="chipbtn" onClick={csv}><DownloadSimple size={16} /> CSV</button>}
          </div>
          <input ref={fileRef} type="file" accept="audio/*,.wav,.mp3,.m4a,.ogg,.opus,.webm,.flac" multiple hidden
            onChange={(e) => { add([...(e.target.files ?? [])].map((f) => ({ blob: f, name: f.name }))); e.target.value = ""; }} />
          <div className="fine">Audio is scored in memory and dropped; nothing is stored. Bench results are evidence for analysts and judges and never move money.</div>
        </div>

        {models.length === 1 && rows.some((r) => r.res) && (
          <div className="fine" style={{ margin: "10px 2px 0" }} data-testid="bench-one-model">
            Only {SHORT_NAME[models[0]] ?? models[0]} runs on this server. The full panel (four detectors, with our reference
            model n3 as the headline verdict) runs on the team laptop: ask us to show it.
          </div>
        )}
        {rows.length > 0 && (
          <div className="panel bench-table-wrap">
            <table className="rtable bench-table">
              <thead>
                <tr>
                  <th>File</th><th>Your label</th><th>{headName}</th>
                  {models.map((m) => <th key={m}>{SHORT_NAME[m] ?? m}</th>)}
                  <th>Speech</th><th>Time</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const right = r.res?.fused && r.label !== "unknown"
                    ? (r.label === "clone") === (r.res.fused.verdict === "synthetic") : null;
                  return (
                    <tr key={r.id} className={right === false ? "wrong" : ""}>
                      <td className="mono fname" title={r.name}>{r.name}</td>
                      <td>
                        <select value={r.label} onChange={(e) => update(r.id, { label: e.target.value as Label })}>
                          <option value="unknown">?</option><option value="genuine">Genuine</option><option value="clone">Clone</option>
                        </select>
                      </td>
                      <td>
                        {r.status === "done" ? <><Verdict v={r.res?.fused?.verdict} /> {right !== null && <span className={right ? "ok-mark" : "bad-mark"}>{right ? "✓" : "✗"}</span>}</>
                          : r.status === "error" ? <span className="err" title={r.err}>error</span> : <span className="fine">{r.status}…</span>}
                      </td>
                      {models.map((m) => {
                        const x = r.res?.models.find((y) => y.id === m);
                        return <td key={m} title={x ? `score ${x.raw} · threshold ${x.threshold} · z ${x.z}` : ""}>{x ? <><Verdict v={x.verdict} small /> <span className="mono fine">{x.z > 0 ? "+" : ""}{x.z.toFixed(2)}</span></> : "–"}</td>;
                      })}
                      <td className="mono">{r.res ? <>{r.res.quality.speech_sec.toFixed(1)} s{!r.res.quality.ok && <span className="warnq" title="Under 4 s of speech or SNR under 10 dB: low confidence"> low</span>}</> : ""}</td>
                      <td className="mono fine">{r.res ? `${(r.res.latency_ms / 1000).toFixed(1)} s` : ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="bench-side">
          {summary.labelled > 0 && (
            <div className="panel">
              <div className="sec-t">On your labelled clips ({summary.labelled})</div>
              <table className="rtable">
                <thead><tr><th>Detector</th><th>Correct</th><th>Genuine flagged</th><th>Clones missed</th></tr></thead>
                <tbody>
                  {summary.out.map((o) => (
                    <tr key={o.id} className={o.id === "fused" ? "fused-row" : ""}>
                      <td>{o.name}</td><td className="mono">{o.s.ok}/{o.s.n}</td>
                      <td className="mono">{o.s.fp}/{o.s.gen}</td><td className="mono">{o.s.miss}/{o.s.cl}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="fine">On clips the models never saw (like a jury's kit) this is a never-trained test. Small counts: read them as examples, not rates.</div>
            </div>
          )}
          <div className="panel">
            <div className="sec-t">How the verdicts are made</div>
            <p className="fine">Each detector keeps its own threshold: its equal-error point on the same 6,000-clip simulated test sample.
              {" "}{fused?.members.length === 1
                ? <>Pehchaan's verdict is our reference detector, {SHORT_NAME[fused.members[0]] ?? fused.members[0]} (simulated EER {(fused.sim_eer * 100).toFixed(1)}%), chosen on 25 Oct after it was the only new model to beat A on real calls. The others are shown beside it.</>
                : <>Pehchaan's fused verdict is the plain average of {fused ? fused.members.map((m) => SHORT_NAME[m] ?? m).join(", ") : "ours v1, ours A and NII"} after putting each on that common scale. No weight was fitted
                  {fused ? <> (simulated EER {(fused.sim_eer * 100).toFixed(1)}%)</> : null}.</>}
              {models.includes("la") && " The off-the-shelf model is shown for comparison only."}</p>
          </div>
          <div className="panel bench-fail">
            <div className="sec-t"><WarningCircle size={16} weight="fill" /> Where it still fails</div>
            <ul className="fine">
              <li><b>Brand-new commercial cloners</b>, especially instant voice cloning, can pass as genuine: Sarvam's instant
                clones of a person no model was trained on got through on real calls 0 of 12 times for every model we trained,
                n3 included (v5, 25 Oct).</li>
              <li><b>Real voices recorded from the phone network</b> (a dialer's recording of a cellular call) are almost always
                flagged: model A flagged 40 of 44 such clips, but none of 80 direct microphone recordings. On the speakerphone
                path Pehchaan uses, it flagged 13 of 256 (clone-vs-detect benchmark, 24 Oct). n3 flags 18 of 44 dialer clips,
                none of the 80 microphone recordings and 3 of 256 genuine speakerphone clips (v5, 25 Oct).</li>
              <li><b>Short clips</b> (under 4 s of speech) and heavy noise: low confidence.</li>
              <li><b>Phone audio</b> through cheap speakerphones and codecs shifts scores; the real-call retrain (A) helps but doesn't remove it.</li>
              <li>Music, overlapping speakers or non-speech are out of scope.</li>
            </ul>
            <div className="fine">That's why the voice score never holds money: Pehchaan verifies the person through Family Verify, the bank registry or a safe word.</div>
          </div>
        </div>
      </div>
    </div>
  );
}
