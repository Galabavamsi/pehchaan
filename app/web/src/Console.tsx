import { useEffect, useMemo, useState } from "react";
import { Bank, CheckCircle, Eye, LockKey, SealCheck, ShieldCheck, UserCircle, WarningCircle, XCircle } from "@phosphor-icons/react";
import { api, subscribe, type Reason, type Tier } from "./api";
import { famName, Seal, TierChip, Waterfall } from "./components";
import { FAMILY_COLOR, formatINR, SHORT } from "./i18n";

type Filter = "all" | "held" | "review";

export function Console({ compact = false, follow = false }: { compact?: boolean; follow?: boolean }) {
  const [list, setList] = useState<any[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = async (pick?: string | null) => {
    const l = await api.cases().catch(() => []);
    setList(l);
    const target = pick ?? sel ?? (l.find((c: any) => c.scenario !== "background") ?? l[0])?.case_id ?? null;
    if (target) { setSel(target); setDetail(await api.case(target).catch(() => null)); }
    else setDetail(null);
  };

  useEffect(() => { load(); }, []);
  useEffect(() => subscribe("/ws/console", (m) => {
    if (m.type === "reset") { setSel(null); setDetail(null); setTimeout(() => load(null), 150); }
    if (m.type === "case_update") {
      const isNew = m.data?.scenario && m.data.scenario !== "background";
      load(follow && isNew ? m.case_id : undefined);
    }
  }), [sel, follow]);

  const select = async (id: string) => { setSel(id); setMsg(null); setDetail(await api.case(id)); };
  const decide = async (d: string) => {
    if (!sel) return;
    setBusy(true);
    try {
      const r = await api.decision(sel, d, note || undefined);
      setMsg(d === "confirm_fraud" ? "Marked as scam. Payee flagged to the PSP mule-risk team; customer's report pack stays with them."
        : d === "false_positive" ? "Marked as genuine. Label sent to the feedback loop for recalibration."
          : "Hold released. The customer must confirm the payment again.");
      setNote("");
      await load(sel);
      return r;
    } catch (e: any) { setMsg(String(e.message)); } finally { setBusy(false); }
  };

  const shown = list.filter((c) => filter === "all" ? true : filter === "held" ? c.status === "held" :
    (c.status === "held" && (c.amount_inr ?? 0) >= 50000));
  const counts = { all: list.length, held: list.filter((c) => c.status === "held").length,
    review: list.filter((c) => c.status === "held" && (c.amount_inr ?? 0) >= 50000).length };

  return (
    <div className={`console ${compact ? "compact" : ""}`} data-testid="console">
      <div className="con-top">
        <span className="bankmark"><span className="bm"><Bank size={17} weight="fill" /></span>Bharat Demo Bank</span>
        <span className="sep" />
        <span className="title">Fraud risk console</span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13, color: "#c9cdd3" }}><Seal size={16} dot="#fffdf8" />Pehchaan</span>
        <span className="grow" />
        <span className="logged"><Eye size={15} weight="bold" />{compact ? "Access logged" : "Every case you open is logged with your reason"}</span>
        <span className="role"><UserCircle size={16} weight="fill" /><b>Fraud analyst · L2</b><span className="mono" style={{ fontSize: 12, color: "#c9cdd3" }}>a.verma</span></span>
      </div>
      <div className="con-main">
        <aside className="queue">
          <div className="qh">
            <h2>Case queue</h2>
            <div className="seg" role="group" aria-label="Filter">
              {(["all", "held", "review"] as Filter[]).map((f) => (
                <button key={f} aria-pressed={filter === f} onClick={() => setFilter(f)}>
                  {f === "all" ? "All" : f === "held" ? "On hold" : "Needs review"} <span className="mono">{counts[f]}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="qlist">
            {shown.map((c) => (
              <button key={c.case_id} className="qitem" aria-current={c.case_id === sel} onClick={() => select(c.case_id)} data-testid={`q-${c.case_id}`}>
                <span className="bar" style={{ background: tierColor(c.tier) }} />
                <span style={{ minWidth: 0 }}>
                  <div className="qt">{c.payee_name}</div>
                  <div className="qs">{claimLabel(c.claim)} · {statusLabel(c.status)}</div>
                  <div style={{ marginTop: 6 }}><TierChip tier={c.tier} label={tierWord(c.tier, c.status)} /></div>
                </span>
                <span>
                  <div className="qa">{formatINR(c.amount_inr)}</div>
                  <div className="qtime">{(c.created_at_ist || "").slice(11, 16)}</div>
                </span>
              </button>
            ))}
            {!shown.length && <div className="empty">No cases here.</div>}
          </div>
        </aside>
        <main className="detail">
          {detail ? <Detail d={detail} compact={compact} busy={busy} note={note} setNote={setNote} decide={decide} msg={msg} /> :
            <div className="empty">Pick a case from the queue.</div>}
        </main>
      </div>
    </div>
  );
}

const tierWord = (t: Tier, status: string) =>
  ({ red: status === "held" ? "Red · on hold" : "Red", amber: "Amber", green: "Green" }[t]);
const tierColor = (t: Tier) => ({ red: "#c8372d", amber: "#e0a526", green: "#13796f" }[t] ?? "#6b7280");
const claimLabel = (c: string | null) => ({ family: "Claimed family", bank: "Claimed bank", upi_or_shop: "UPI app / shop",
  authority: "Claimed police / govt",
  other: "Someone else", none: "No one asked" } as any)[c ?? ""] ?? "No claim yet";
const statusLabel = (s: string) => ({ held: "On hold", paused: "Paused", awaiting_verification: "Waiting for relative",
  cleared: "Cleared", sent: "Sent", cancelled: "Cancelled by customer", reported: "Reported by customer",
  confirmed_fraud: "Confirmed scam", false_positive: "Marked genuine", released: "Released", open: "Open" } as any)[s] ?? s;

const EVT: Record<string, (d: any) => string> = {
  payment_attempt: (d) => `Pay tapped · trigger: ${(d.trigger || []).join(", ")}`,
  assessment: (d) => `Scored ${d.tier} · p ${Number(d.p).toFixed(3)} · ${d.why}${d.guardrails?.length ? " · " + d.guardrails.join(", ") : ""}`,
  claim: (d) => `Customer answered: ${d.claim}${d.claim_target ? " (" + d.claim_target.replace("rel_", "") + ")" : ""}`,
  fv_challenge_sent: (d) => `Family Verify sent to ${d.device_id} · shown ${d.shown?.amount_band} to ${d.shown?.payee_name}`,
  fv_response: (d) => `Relative answered "${d.answer}" · signature ${d.signature_verified ? "verified" : "failed"}`,
  fv_timeout: () => "Family Verify timed out (3 min)",
  hold_started: (d) => `Cooling-off hold ${d.minutes} min · no auto-send`,
  check_result: (d) => `${d.kind.replace("_", " ")}: ${d.result.replaceAll("_", " ")}`,
  voice_scored: (d) => `Voice ${d.band} · p ${Number(d.p_synthetic).toFixed(2)} · audio discarded`,
  user_action: (d) => `Customer: ${d.action}`,
  release_requested: (d) => `Customer asked to release · needs ${String(d.requires).replace("_", " ")}`,
  analyst_decision: (d) => `Analyst: ${d.decision.replace("_", " ")}`,
  evidence_pack_generated: () => "Evidence pack signed",
  checklist: (d) => `Checklist: ${(d.cues || []).join(", ")}`,
};

function Detail({ d, compact, busy, note, setNote, decide, msg }: {
  d: any; compact: boolean; busy: boolean; note: string; setNote: (s: string) => void; decide: (x: string) => void; msg: string | null;
}) {
  const reasons: Reason[] = d.reasons || [];
  const voice = d.checks?.voice;
  const fvr = d.checks?.family_verify;
  const held = d.status === "held";
  const closed = ["confirmed_fraud", "false_positive", "released"].includes(d.status);
  const sortedReasons = useMemo(() => [...reasons].sort((a, b) => b.contribution - a.contribution), [reasons]);
  return (
    <div data-testid="case-detail">
      <div className="dh-row">
        <span className="cid">{d.case_id}</span>
        <TierChip tier={d.tier} big label={tierWord(d.tier, d.status)} />
        <span className="st">{statusLabel(d.status)}{d.hold && !d.hold.released ? ` · until ${d.hold.until.slice(11, 16)} IST` : ""}</span>
        <span className="grow" />
        <span className="mono" style={{ fontSize: 13, color: "var(--slate)" }}>config v{d.config_version} · {d.created_at_ist?.slice(11, 19)} IST</span>
      </div>
      <div className="dh-sub">
        <b className="mono">{d.amount_display}</b> to <b>{d.payee_name}</b> <span className="mono">({d.payee_vpa})</span>{" "}
        from <b>{d.payer_name}</b> ({d.payer_age_band}) · caller <span className="mono">{d.caller_display}</span>{" "}
        ({d.call_channel === "whatsapp" ? "WhatsApp" : d.call_channel}, {d.caller_in_contacts ? "saved contact" : "not in contacts"}
        {d.call_duration_sec ? `, ${Math.round(d.call_duration_sec / 60)} min` : ""}) · claim <b>{d.claim ?? "–"}</b>
        {d.relative_name ? ` (${d.relative_name})` : ""}
      </div>
      <div className="dgrid">
        <div style={{ minWidth: 0 }}>
          <section className="panel">
            <h3>Why this decision</h3>
            <div className="ph-sub">Each bar is one signal's ln-LR contribution after family caps, from the prior to the final score. Guardrails then decide the tier.</div>
            <Waterfall reasons={reasons} priorLogOdds={d.prior_log_odds} logOdds={d.log_odds} p={d.p} prior={d.prior} compact={compact}
              width={compact ? 640 : 760} redAt={d.thresholds?.red_at_or_above ?? 0.75} greenBelow={d.thresholds?.green_below ?? 0.15} />
          </section>
          {!compact && (
            <section className="panel">
              <h3>All reasons</h3>
              <table className="rtable">
                <thead><tr><th></th><th>Signal</th><th>What the customer saw</th><th style={{ textAlign: "right" }}>LR</th><th style={{ textAlign: "right" }}>ln-LR</th></tr></thead>
                <tbody>
                  {sortedReasons.map((r) => (
                    <tr key={r.code}>
                      <td><span className="fam" style={{ background: FAMILY_COLOR[r.family] }} title={famName(r.family)}>{r.family}</span></td>
                      <td><div style={{ fontWeight: 600 }}>{SHORT[r.code]?.[0] ?? r.code}</div><div className="mono" style={{ fontSize: 11.5, color: "var(--slate)" }}>{r.code} · {r.basis}</div>{r.basis === "shadow" && <span className="shadow-badge">shadow: not used in decision</span>}</td>
                      <td>{r.text.en}<div className="hi" lang="hi">{r.text.hi}</div></td>
                      <td className="num">{r.lr < 1 ? r.lr.toFixed(2) : r.lr.toFixed(r.lr < 10 ? 1 : 0)}</td>
                      <td className="num" style={{ color: r.contribution > 0 ? "#b4531a" : "var(--teal)", fontWeight: 600 }}>{r.contribution > 0 ? "+" : "−"}{Math.abs(r.contribution).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </div>
        <div style={{ minWidth: 0 }}>
          <section className="panel">
            <h3>Decision</h3>
            <div className="ph-sub">{held ? (d.amount_inr >= 50000 ? "₹50,000 or more: early release needs an analyst." : "Customer can release after a positive check.") : closed ? "Closed." : "No hold on this case."}</div>
            <div className="acts">
              <button className="act ok" disabled={busy || !held} onClick={() => decide("release_hold")} data-testid="dec-release"><CheckCircle size={18} weight="bold" /><span>Release hold<span className="as">Customer must confirm the payment again</span></span></button>
              <button className="act danger" disabled={busy || closed} onClick={() => decide("confirm_fraud")} data-testid="dec-fraud"><XCircle size={18} weight="bold" /><span>Confirm scam and report<span className="as">Flags the payee UPI ID to the PSP mule-risk team</span></span></button>
              <button className="act" disabled={busy || closed} onClick={() => decide("false_positive")} data-testid="dec-fp"><WarningCircle size={18} weight="bold" /><span>Mark false positive<span className="as">Label goes to the recalibration loop</span></span></button>
              <input className="note-in" placeholder="Reason (stored in the access log)" value={note} onChange={(e) => setNote(e.target.value)} />
              {msg && <div style={{ fontSize: 13, color: "var(--ink-2)" }}>{msg}</div>}
              {d.analyst && <div style={{ fontSize: 12.5, color: "var(--slate)" }}>Decided by {d.analyst.by} ({d.analyst.role}) at {d.analyst.at.slice(11, 16)}</div>}
            </div>
          </section>
          <section className="panel">
            <h3>Guardrails applied</h3>
            {d.guardrails?.length ? (
              <div className="grd">{d.guardrails.map((g: any, i: number) => (
                <div className="g" key={i}><span className="gid">{g.id}</span><span><div className="ge">{g.name}: {g.effect}</div><div className="gd">{g.detail}</div></span></div>
              ))}</div>
            ) : <div style={{ fontSize: 13.5, color: "var(--ink-2)" }}>None changed the tier. Corroborating families with LR ≥ 3: <b className="mono">{(d.qualifying_families || []).join(", ") || "–"}</b>{(d.signals || []).some((s: string) => ["fv_denied", "callback_denied", "bank_no_active_call", "safeword_failed"].includes(s)) ? "; decisive out-of-band negative present." : "."}</div>}
          </section>
          <section className="panel">
            <h3>Checks</h3>
            <dl className="kv">
              <dt>Family Verify</dt><dd>{fvr ? <>{fvr.result ?? fvr.status}{fvr.sig_ok && <> · <SealCheck size={13} weight="fill" style={{ color: "var(--teal)", verticalAlign: -2 }} /> device signature</>}</> : "–"}</dd>
              <dt>Bank registry</dt><dd>{d.checks?.bank_registry ? `${d.checks.bank_registry.result.replaceAll("_", " ")}${d.claimed_bank ? ` (${d.claimed_bank.name}${d.claimed_bank.integrated ? ", integrated" : ", not integrated"})` : ""}` : "–"}</dd>
              <dt>Callback</dt><dd>{d.checks?.callback?.result ?? "–"}</dd>
              <dt>Voice</dt><dd>{voice ? <>{voice.voice_mode === "shadow" && <span className="shadow-badge" data-testid="voice-shadow-badge">shadow: not used in decision</span>}{voice.band.replaceAll("_", " ")} · p <span className="mono">{voice.p_synthetic.toFixed(2)}</span> · speech <span className="mono">{voice.quality.speech_sec}s</span> · SNR <span className="mono">{voice.quality.snr_db} dB</span>{voice.quality.ok ? "" : " (below gate)"}{voice.watermark?.detected ? <> · <b>watermark</b> (used)</> : null}<div className="mono" style={{ fontSize: 11.5, color: "var(--slate)" }}>{voice.model_version}</div></> : (d.voice_mode === "shadow" ? <>not performed <span className="shadow-badge">detector in shadow mode</span></> : "not performed")}</dd>
            </dl>
          </section>
          <section className="panel">
            <h3>Evidence chain</h3>
            <div className="ph-sub" style={{ display: "flex", gap: 6, alignItems: "center" }}>
              {d.chain?.verified ? <><ShieldCheck size={15} weight="fill" style={{ color: "var(--teal)" }} /><span className="ok" style={{ color: "var(--teal)", fontWeight: 600 }}>SHA-256 chain verified</span></> : <span style={{ color: "var(--red)" }}>chain broken</span>}
              <span>· {d.events?.length} events{d.evidence ? ` · signed ${d.evidence.sig_key_id}` : ""}</span>
            </div>
            <div className="chain">
              {(d.events || []).slice(compact ? -5 : -8).map((e: any) => (
                <div className="ce" key={e.seq}><span className="h">{e.seq}</span><span>{e.ts.slice(11, 19)}</span><span style={{ fontFamily: "var(--f-body)", fontSize: 12.5 }}>{e.type.replaceAll("_", " ")}</span><span className="h">{e.hash.slice(0, 10)}…</span></div>
              ))}
            </div>
          </section>
          {!compact && (
            <section className="panel">
              <h3>Timeline</h3>
              <ul className="tl">
                {(d.events || []).map((e: any) => (
                  <li key={e.seq}><span className="tt">{e.ts.slice(11, 19)}</span><span className="td" style={{ background: e.type === "hold_started" ? "var(--red)" : e.type === "fv_response" ? "var(--teal)" : undefined }} />
                    <span className="te">{(EVT[e.type] ?? ((x: any) => e.type))(e.data)}</span></li>
                ))}
              </ul>
              <div style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12.5, color: "var(--slate)", marginTop: 10 }}>
                <LockKey size={14} weight="bold" />Viewed by {d.access_log?.length ?? 0} analyst sessions; immutable access log.
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
