// Thin client for the Pehchaan risk API (app/server). All adapters behind it are mocks.
export type Tier = "green" | "amber" | "red";
export type Lang = "en" | "hi";
export interface Bi { en: string; hi: string }

export interface Reason {
  code: string; family: string; family_name: string; family_name_hi: string;
  lr: number; ln_lr: number; contribution: number; direction: "raises" | "lowers" | "neutral";
  text: Bi; basis: string;
}
export interface Action {
  id: string; kind: string; label: Bi; detail?: Bi | null; primary: boolean;
  enabled_after_sec: number; produces: string[]; requires?: string | null;
}
export interface Guardrail { id: string; name: string; effect: string; detail: string }
export interface Hold {
  started_at: string; until: string; minutes: number; auto_send_on_expiry: boolean; released: boolean;
  release_requires?: string; can_release_now?: boolean;
}
export interface Relative {
  id: string; name: string; name_hi?: string; full_name: string; relation: string; relation_hi?: string;
  device_id: string; saved_number?: string; lives_in?: string; calls_payer?: string; calls_payer_hi?: string;
  pronoun?: "he" | "she" | string;
}
export interface FvSent {
  challenge_id: string; expires_at: string; timeout_sec: number; auto?: boolean;
  relative?: { id: string; name: string; relation: string };
}
export interface VoiceResult {
  p_synthetic: number; band: string; quality: { speech_sec: number; snr_db: number; ok: boolean; duration_sec?: number };
  watermark: { detected: boolean; scheme: string | null }; model_version: string; latency_ms: number; mock?: boolean;
  mock_notice?: string; assessment?: Assessment;
}
export interface Assessment {
  case_id: string | null; triggered: boolean; stage?: string; tier: Tier; raw_tier?: Tier; p: number | null;
  log_odds?: number; prior?: number; prior_log_odds?: number;
  thresholds?: { green_below: number; red_at_or_above: number; green_below_log_odds: number; red_at_or_above_log_odds: number };
  reasons: Reason[]; top_reasons: Reason[]; actions: Action[]; guardrails: Guardrail[];
  families?: Record<string, { family: string; name: string; ln_lr: number; raw_ln_lr: number; capped: boolean; signals: string[] }>;
  signals?: string[]; qualifying_families?: string[]; ask_claim: boolean; status: string; hold?: Hold | null;
  copy: { title: Bi; body: Bi }; claim?: string | null; relative?: Relative | null;
  checks?: Record<string, any>; amount_display?: string; payee_name?: string; payee_vpa?: string;
  caller_display?: string; latency_ms?: number; utr?: string; release_requested?: boolean;
  context_tier?: Tier; auto_family_verify?: FvSent;
}
export interface Payer {
  id: string; name: string; name_hi?: string; gender?: string; age_band?: string; city?: string; phone: string;
  vpa: string; vpa_masked: string; bank_name: string; bank_name_hi?: string; lang: Lang; circle: Relative[];
}
export interface Scenario {
  scenario: string; title: string; pattern: string; script: string; payer: Payer; relative: Relative | null;
  call: { state: string; number: string; channel: string; duration_sec: number };
  payment: { payee_vpa: string; payee_name: string; amount_inr: number };
  expected: Record<string, any>; bank: { name: string; name_hi: string };
  banks?: { id: string; name: string; name_hi: string; label?: string; label_hi?: string; integrated: boolean; yours: boolean }[];
}

const qs = new URLSearchParams(location.search || location.hash.split("?")[1] || "");
export const API: string = qs.get("api") || (import.meta as any).env?.VITE_API || `http://${location.hostname || "127.0.0.1"}:8400`;
export const WS = API.replace(/^http/, "ws");
/** Server clock skew (the demo server may run a shifted demo clock). Countdowns use serverNow(). */
export const clock = { skewMs: 0 };
export const serverNow = () => Date.now() + clock.skewMs;
export const ANALYST_HEADERS = { "X-Role": "fraud_analyst", "X-Analyst": "a.verma", "X-Access-Reason": "queue review" };

async function req<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const headers: Record<string, string> = { ...(init?.headers as any) };
  let body = init?.body;
  if (init?.json !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(init.json); }
  const r = await fetch(API + path, { ...init, headers, body });
  const sn = r.headers.get("X-Server-Now");
  if (sn) clock.skewMs = new Date(sn).getTime() - Date.now();
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch { /* ignore */ }
    throw new Error(`${r.status}: ${detail}`);
  }
  return r.json() as Promise<T>;
}

export const api = {
  scenario: (name: string) => req<Scenario>(`/v1/demo/scenario/${name}`, { method: "POST" }),
  assess: (body: unknown) => req<Assessment>("/v1/risk/assess", { method: "POST", json: body }),
  verifyFamily: (case_id: string, relative_id?: string) =>
    req<FvSent & { assessment: Assessment }>("/v1/verify/family", { method: "POST", json: { case_id, relative_id } }),
  cancelFamilyVerify: (challenge_id: string) =>
    req<Assessment>(`/v1/verify/family/${challenge_id}/cancel`, { method: "POST" }),
  respond: (id: string, answer: "yes" | "no", device_id: string, signature_b64: string) =>
    req<{ ok: boolean; result: string; tier: Tier }>(`/v1/verify/family/${id}/respond`, { method: "POST", json: { answer, device_id, signature_b64 } }),
  registerDevice: (device_id: string, user_id: string, public_key_b64: string) =>
    req<{ key_id: string }>("/v1/devices/register", { method: "POST", json: { device_id, user_id, public_key_b64 } }),
  pending: (device_id: string) => req<any[]>(`/v1/devices/${device_id}/challenges`),
  check: (case_id: string, kind: string, result?: string) =>
    req<Assessment>(`/v1/cases/${case_id}/checks/${kind}`, { method: "POST", json: { result } }),
  userAction: (case_id: string, action: string) =>
    req<Assessment>(`/v1/cases/${case_id}/user-action`, { method: "POST", json: { action } }),
  evidence: (case_id: string) => req<any>(`/v1/cases/${case_id}/evidence-pack`, { method: "POST" }),
  cases: () => req<any[]>("/v1/cases", { headers: ANALYST_HEADERS }),
  case: (id: string) => req<any>(`/v1/cases/${id}`, { headers: ANALYST_HEADERS }),
  decision: (id: string, decision: string, note?: string) =>
    req<any>(`/v1/cases/${id}/decision`, { method: "POST", json: { decision, note }, headers: ANALYST_HEADERS }),
  voice: async (blob: Blob, case_id: string | null, demo_hint?: string) => {
    const fd = new FormData();
    fd.append("file", blob, "capture.wav");
    if (case_id) fd.append("case_id", case_id);
    if (demo_hint) fd.append("demo_hint", demo_hint);
    return req<VoiceResult>("/v1/voice/score", { method: "POST", body: fd });
  },
  demoAudio: async (kind: string) => (await fetch(`${API}/v1/demo/audio/${kind}.wav`)).blob(),
  forceTimeout: (challenge_id: string) => req<any>(`/v1/demo/fv/${challenge_id}/timeout`, { method: "POST" }),
};

/** Subscribe to a WebSocket topic with auto-reconnect. Returns an unsubscribe function. */
export function subscribe(path: string, onMsg: (m: any) => void): () => void {
  let ws: WebSocket | null = null;
  let closed = false;
  let timer: number | undefined;
  const open = () => {
    ws = new WebSocket(WS + path);
    ws.onmessage = (e) => { try { onMsg(JSON.parse(e.data)); } catch { /* ignore */ } };
    ws.onclose = () => { if (!closed) timer = window.setTimeout(open, 800); };
  };
  open();
  return () => { closed = true; window.clearTimeout(timer); ws?.close(); };
}

export const urlParam = (k: string): string | null => {
  const h = new URLSearchParams(location.hash.split("?")[1] || "");
  return h.get(k) ?? new URLSearchParams(location.search).get(k);
};
