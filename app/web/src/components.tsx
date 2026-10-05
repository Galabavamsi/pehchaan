import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowsCounterClockwise, Bank, BatteryFull, CellSignalFull, CellSignalHigh, Clock, CurrencyInr, DeviceMobile, Flag,
  Gavel, Globe, Hash, Hourglass, IdentificationCard, Key, LockKey, Password, PhoneCall, PhoneOutgoing, Stack, Timer,
  UserCheck, UserMinus, UserPlus, Users, Waveform, WifiHigh, Fingerprint, Info,
} from "@phosphor-icons/react";
import { serverNow, type Reason, type Tier } from "./api";
import { FAMILY_COLOR, SHORT } from "./i18n";

/** Pehchaan seal: an open ring (the circle of people who know you) around a dot (the person). */
export function Seal({ size = 22, ring = "#e8742a", dot = "#1b1f24" }: { size?: number; ring?: string; dot?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 3.5a12.5 12.5 0 1 1-11.2 6.9" fill="none" stroke={ring} strokeWidth="4" strokeLinecap="round" />
      <circle cx="16" cy="16" r="5" fill={dot} />
    </svg>
  );
}

export function Wordmark({ light = false }: { light?: boolean }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 7 }}>
      <Seal size={20} dot={light ? "#fffdf8" : "#1b1f24"} />
      <span style={{ fontFamily: "var(--f-head)", fontWeight: 700, fontSize: 15 }}>Pehchaan</span>
      <span style={{ fontFamily: "'Noto Sans Devanagari'", fontSize: 13, opacity: 0.75 }}>पहचान</span>
    </span>
  );
}

export function StatusBar({ light = false, fill }: { light?: boolean; fill?: string }) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const t = setInterval(() => setNow(new Date()), 5000); return () => clearInterval(t); }, []);
  const fixed = new URLSearchParams(location.hash.split("?")[1] || "").get("clock");
  const hh = fixed || new Date(serverNow()).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" });
  return (
    <div className={`statusbar ${light ? "light" : ""}`} style={fill ? { background: fill } : undefined}>
      <span className="mono" style={{ fontFamily: "var(--f-body)" }}>{hh}</span>
      <span className="island" />
      <span className="icons"><CellSignalFull size={17} weight="fill" /><WifiHigh size={17} weight="bold" /><BatteryFull size={22} weight="fill" /></span>
    </div>
  );
}

export function Device({ children, large = false, testid, lang }: { children: ReactNode; large?: boolean; testid?: string; lang?: string }) {
  return (
    <div className="device" data-testid={testid}>
      <div className={`screen ${large ? "large" : ""}`} lang={lang}>{children}</div>
    </div>
  );
}

/** Countdown ring. frac = remaining fraction (0..1). */
export function Ring({ size, frac, stroke = 8, track, color, children }: {
  size: number; frac: number; stroke?: number; track: string; color: string; children?: ReactNode;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }} aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(0, Math.min(1, frac)))} style={{ transition: "stroke-dashoffset 1s linear" }} />
      </svg>
      <div className="center">{children}</div>
    </div>
  );
}

export function useCountdown(untilIso: string | undefined | null, totalSec: number) {
  const [now, setNow] = useState(serverNow());
  useEffect(() => { const t = setInterval(() => setNow(serverNow()), 1000); return () => clearInterval(t); }, []);
  if (!untilIso) return { left: totalSec, frac: 1, mmss: fmt(totalSec) };
  const left = Math.max(0, Math.round((new Date(untilIso).getTime() - now) / 1000));
  return { left, frac: left / totalSec, mmss: fmt(left) };
}
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

export function ReasonIcon({ code, size = 18 }: { code: string; size?: number }) {
  const p = { size, weight: "bold" as const };
  if (code === "caller_unknown") return <PhoneCall {...p} />;
  if (code === "caller_international") return <Globe {...p} />;
  if (code === "caller_voip_unknown") return <WifiHigh {...p} />;
  if (code === "bank_claim_not_1600") return <Hash {...p} />;
  if (code.startsWith("fri_")) return <CellSignalHigh {...p} />;
  if (code === "call_ongoing_long") return <Timer {...p} />;
  if (code === "payee_new") return <UserPlus {...p} />;
  if (code.startsWith("amount_")) return <CurrencyInr {...p} />;
  if (code.startsWith("payee_flagged")) return <Flag {...p} />;
  if (code === "payee_name_mismatch") return <IdentificationCard {...p} />;
  if (code === "burst_new_payees") return <Stack {...p} />;
  if (code === "watermark_detected") return <Fingerprint {...p} />;
  if (code.startsWith("voice_")) return <Waveform {...p} />;
  if (code === "cue_secrecy") return <LockKey {...p} />;
  if (code === "cue_urgency") return <Hourglass {...p} />;
  if (code === "cue_otp_pin") return <Password {...p} />;
  if (code === "cue_arrest_threat") return <Gavel {...p} />;
  if (code === "cue_remote_app") return <DeviceMobile {...p} />;
  if (code === "cue_refund_verification") return <ArrowsCounterClockwise {...p} />;
  if (code === "fv_denied") return <UserMinus {...p} />;
  if (code === "fv_confirmed") return <UserCheck {...p} />;
  if (code === "fv_timeout") return <Clock {...p} />;
  if (code.startsWith("callback")) return <PhoneOutgoing {...p} />;
  if (code.startsWith("safeword")) return <Key {...p} />;
  if (code.startsWith("bank_")) return <Bank {...p} />;
  if (code.startsWith("claim_")) return <Users {...p} />;
  return <Info {...p} />;
}

export function TierChip({ tier, big = false, label }: { tier: Tier; big?: boolean; label?: string }) {
  const names = { red: "Red", amber: "Amber", green: "Green" } as const;
  return <span className={`tierchip ${tier} ${big ? "big" : ""}`}><i />{label ?? names[tier]}</span>;
}

// ----------------------------------------------------------------------------- waterfall
const FAM_ORDER = ["K", "P", "C", "S", "V", "O"];
const FAM_NAME: Record<string, string> = {
  C: "Claim", K: "Call context", P: "Payment context", V: "Voice", S: "Script cues", O: "Out-of-band check",
};

/** Horizontal waterfall of ln-LR contributions from the prior to the final log-odds,
 *  drawn over the tier zones (green < 10% < amber < 60% < red). */
export function Waterfall({ reasons, priorLogOdds, logOdds, p, prior, width = 760, compact = false }: {
  reasons: Reason[]; priorLogOdds: number; logOdds: number; p: number; prior: number; width?: number; compact?: boolean;
}) {
  const rows = [...reasons].filter((r) => Math.abs(r.contribution) > 1e-6)
    .sort((a, b) => FAM_ORDER.indexOf(a.family) - FAM_ORDER.indexOf(b.family) || b.contribution - a.contribution);
  const labelW = compact ? 196 : 214;
  const valW = 54;
  const rowH = compact ? 25 : 28;
  const top = 34;
  const n = rows.length + 2;
  const h = top + n * rowH + 34;
  let cum = priorLogOdds;
  const pts = rows.map((r) => { const a = cum; cum += r.contribution; return { r, a, b: cum }; });
  const all = [priorLogOdds, logOdds, ...pts.map((x) => x.b), -7.5, 5];
  const lo = Math.floor(Math.min(...all) - 0.5);
  const hi = Math.ceil(Math.max(...all) + 0.5);
  const plotW = width - labelW - valW;
  const x = (v: number) => labelW + ((v - lo) / (hi - lo)) * plotW;
  const lg = (q: number) => Math.log(q / (1 - q));
  const g = lg(0.1), rd = lg(0.6);
  const ticks = [0.001, 0.01, 0.1, 0.6, 0.99, 0.999].filter((q) => lg(q) > lo && lg(q) < hi);
  const yOf = (i: number) => top + i * rowH;
  const fmtP = (q: number) => (q < 0.01 ? `${(q * 100).toFixed(1)}%` : q >= 0.995 ? ">99%" : `${Math.round(q * 100)}%`);
  const finalTier: Tier = p >= 0.6 ? "red" : p >= 0.1 ? "amber" : "green";
  const tierCol = { red: "#c8372d", amber: "#e0a526", green: "#13796f" }[finalTier];
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${h}`} role="img" aria-label="Contribution waterfall" style={{ display: "block", fontFamily: "Inter" }}>
      {/* tier zones */}
      <rect x={x(lo)} y={top - 8} width={x(g) - x(lo)} height={n * rowH + 8} fill="#d3e7e2" opacity="0.55" />
      <rect x={x(g)} y={top - 8} width={x(rd) - x(g)} height={n * rowH + 8} fill="#f4e2b4" opacity="0.65" />
      <rect x={x(rd)} y={top - 8} width={x(hi) - x(rd)} height={n * rowH + 8} fill="#f3d5cf" opacity="0.65" />
      <text x={(x(lo) + x(g)) / 2} y={top - 14} textAnchor="middle" fontSize="12" fontWeight="600" fill="#0d5c54">Green</text>
      <text x={(x(g) + x(rd)) / 2} y={top - 14} textAnchor="middle" fontSize="12" fontWeight="600" fill="#7a5a0c">Amber</text>
      <text x={(x(rd) + x(hi)) / 2} y={top - 14} textAnchor="middle" fontSize="12" fontWeight="600" fill="#a72c23">Red (if G1 allows)</text>
      {ticks.map((q) => (
        <g key={q}>
          <line x1={x(lg(q))} x2={x(lg(q))} y1={top - 8} y2={top + n * rowH} stroke="#1b1f24" strokeOpacity="0.12" />
          <text x={x(lg(q))} y={top + n * rowH + 16} textAnchor="middle" fontSize="11.5" fill="#6b7280" fontFamily="JetBrains Mono">{fmtP(q)}</text>
        </g>
      ))}
      <text x={width - valW} y={top + n * rowH + 30} textAnchor="end" fontSize="11" fill="#6b7280">probability of scam (log-odds scale)</text>
      {/* prior row */}
      <text x={labelW - 10} y={yOf(0) + rowH / 2 + 4} textAnchor="end" fontSize="13" fill="#1b1f24" fontWeight="600">Starting point (1 in {Math.round(1 / prior)})</text>
      <circle cx={x(priorLogOdds)} cy={yOf(0) + rowH / 2} r="5" fill="#1b1f24" />
      <text x={width - 4} y={yOf(0) + rowH / 2 + 4} textAnchor="end" fontSize="12" fontFamily="JetBrains Mono" fill="#6b7280">{priorLogOdds.toFixed(2)}</text>
      {pts.map(({ r, a, b }, i) => {
        const y = yOf(i + 1);
        const x0 = x(Math.min(a, b)), x1 = x(Math.max(a, b));
        const up = r.contribution > 0;
        return (
          <g key={r.code}>
            <line x1={x(a)} x2={x(a)} y1={y - 2} y2={y + 4} stroke="#1b1f24" strokeOpacity="0.35" />
            <rect x={labelW - 30} y={y + rowH / 2 - 8} width="16" height="16" rx="4" fill={FAMILY_COLOR[r.family]} />
            <text x={labelW - 22} y={y + rowH / 2 + 4} textAnchor="middle" fontSize="10.5" fontWeight="700" fill="#fff" fontFamily="JetBrains Mono">{r.family}</text>
            <text x={labelW - 36} y={y + rowH / 2 + 4} textAnchor="end" fontSize="13" fill="#1b1f24">{SHORT[r.code]?.[0] ?? r.code}</text>
            <rect x={x0} y={y + 5} width={Math.max(2, x1 - x0)} height={rowH - 10} rx="3" fill={up ? "#e8742a" : "#13796f"} />
            <text x={width - 4} y={y + rowH / 2 + 4} textAnchor="end" fontSize="12.5" fontFamily="JetBrains Mono" fontWeight="600" fill={up ? "#b4531a" : "#13796f"}>
              {up ? "+" : "−"}{Math.abs(r.contribution).toFixed(2)}
            </text>
          </g>
        );
      })}
      {/* result row */}
      <g>
        <text x={labelW - 10} y={yOf(n - 1) + rowH / 2 + 4} textAnchor="end" fontSize="13" fontWeight="700" fill="#1b1f24">Result p = {p >= 0.995 ? p.toFixed(3) : p.toFixed(2)}</text>
        <line x1={x(priorLogOdds)} x2={x(logOdds)} y1={yOf(n - 1) + rowH / 2} y2={yOf(n - 1) + rowH / 2} stroke="#1b1f24" strokeOpacity="0.25" strokeDasharray="3 3" />
        <circle cx={x(logOdds)} cy={yOf(n - 1) + rowH / 2} r="7.5" fill={tierCol} stroke="#fff" strokeWidth="2" />
        <text x={width - 4} y={yOf(n - 1) + rowH / 2 + 4} textAnchor="end" fontSize="12.5" fontFamily="JetBrains Mono" fontWeight="700">{logOdds.toFixed(2)}</text>
      </g>
    </svg>
  );
}

export const famName = (f: string) => FAM_NAME[f] ?? f;
