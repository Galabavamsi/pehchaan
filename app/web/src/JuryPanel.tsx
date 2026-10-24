import { useState } from "react";
import { X } from "@phosphor-icons/react";
import { api, type CustomCase, type Scenario } from "./api";

/** FINALE_PLAN B1: the jury sets up their own case. The claim, the relative's answer and every check are then
 *  given on the two phones, exactly as in the fixed scenarios. */
const PAYERS: { id: CustomCase["payer_id"]; label: string }[] = [
  { id: "u_sunita", label: "Sunita, 55–64, Jaipur (son Rahul)" },
  { id: "u_ramesh", label: "Ramesh, 65+, Chennai (son Anand)" },
  { id: "u_kamala", label: "Kamala, 65+, Lucknow (son Vikas)" },
];
const CALLERS: { id: CustomCase["caller"]; label: string }[] = [
  { id: "unknown", label: "Unknown Indian mobile" },
  { id: "international", label: "Unknown +44 number" },
  { id: "saved", label: "The son's saved number" },
  { id: "bank_1600", label: "1600 bank number" },
];
const DEFAULTS: CustomCase = {
  payer_id: "u_sunita", caller: "international", channel: "whatsapp", call_state: "active", duration_min: 6,
  ended_min: 5, amount_inr: 50000, payee: "new", payee_name: "Arif Traders", payee_flagged: false,
  caller_fri: null, bank_calling: false,
};

function Seg<T extends string>({ value, options, onChange, label }: {
  value: T; options: { id: T; label: string }[]; onChange: (v: T) => void; label: string;
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" aria-pressed={value === o.id} onClick={() => onChange(o.id)}>{o.label}</button>
      ))}
    </div>
  );
}

export function JuryPanel({ current, onClose }: { current: Scenario | null; onClose: () => void }) {
  const [c, setC] = useState<CustomCase>(current?.custom ?? DEFAULTS);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const set = <K extends keyof CustomCase>(k: K, v: CustomCase[K]) => setC((x) => ({ ...x, [k]: v }));
  const onCall = c.call_state !== "none";

  async function run() {
    setBusy(true); setErr(null);
    try { await api.custom(c); onClose(); } catch (e) { setErr(String((e as Error).message ?? e)); } finally { setBusy(false); }
  }

  return (
    <div className="jury-back" role="dialog" aria-modal="true" aria-labelledby="jury-h" onClick={onClose}>
      <form className="jury" onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); run(); }}>
        <div className="jury-h">
          <h2 id="jury-h">Your case</h2>
          <button type="button" className="chipbtn" onClick={onClose} aria-label="Close"><X size={16} weight="bold" /></button>
        </div>
        <p className="jury-sub">Set it up any way you like. Then answer on the phones: who asked to pay, and the son's yes or no.
          All people, numbers and UPI IDs stay fictional.</p>

        <label>Who is paying</label>
        <select value={c.payer_id} onChange={(e) => set("payer_id", e.target.value as CustomCase["payer_id"])}>
          {PAYERS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>

        <label>The call</label>
        <Seg label="Call state" value={c.call_state} onChange={(v) => set("call_state", v)}
          options={[{ id: "active", label: "On the call" }, { id: "ended", label: "Call ended" }, { id: "none", label: "No call" }]} />
        {c.call_state === "active" && (
          <div className="jury-row"><span>Call so far</span>
            <input type="number" min={0} max={240} value={c.duration_min} onChange={(e) => set("duration_min", Number(e.target.value))} /> min</div>
        )}
        {c.call_state === "ended" && (
          <div className="jury-row"><span>Ended</span>
            <input type="number" min={0} max={1440} value={c.ended_min} onChange={(e) => set("ended_min", Number(e.target.value))} /> min ago</div>
        )}

        {onCall && (<>
          <label>Who is calling</label>
          <Seg label="Caller" value={c.caller} onChange={(v) => set("caller", v)} options={CALLERS} />
          <Seg label="Channel" value={c.channel} onChange={(v) => set("channel", v)}
            options={[{ id: "pstn", label: "Phone call" }, { id: "whatsapp", label: "WhatsApp call" }]} />
          <div className="jury-row"><span>Telecom fraud flag on the caller (DoT FRI, mock)</span>
            <select value={c.caller_fri ?? ""} onChange={(e) => set("caller_fri", (e.target.value || null) as CustomCase["caller_fri"])}>
              <option value="">None</option><option value="medium">Medium</option><option value="high">High</option><option value="very_high">Very high</option>
            </select></div>
          {c.caller === "bank_1600" && (
            <label className="jury-check"><input type="checkbox" checked={c.bank_calling} onChange={(e) => set("bank_calling", e.target.checked)} />
              The bank really is calling (its call registry has this call)</label>
          )}
        </>)}

        <label>The payment</label>
        <div className="jury-row"><span>Amount ₹</span>
          <input type="number" min={1} max={10000000} value={c.amount_inr} onChange={(e) => set("amount_inr", Number(e.target.value))} /></div>
        <Seg label="Payee" value={c.payee} onChange={(v) => set("payee", v)}
          options={[{ id: "new", label: "A new payee" }, { id: "usual", label: "The son's usual account" }]} />
        {c.payee === "new" && (
          <div className="jury-row"><span>Name on the UPI ID</span>
            <input type="text" maxLength={60} value={c.payee_name} onChange={(e) => set("payee_name", e.target.value)} /></div>
        )}
        <label className="jury-check"><input type="checkbox" checked={c.payee_flagged} onChange={(e) => set("payee_flagged", e.target.checked)} />
          Payee is on the suspect registry (I4C, mock)</label>

        {err && <div className="jury-err" role="alert">{err}</div>}
        <button type="submit" className="btn solid full" disabled={busy}>{busy ? "Setting up…" : "Run this case"}</button>
      </form>
    </div>
  );
}
