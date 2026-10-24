// Fictional UPI directory for the Android demo (SPEC §7 "Live payments"). It stands in for the PSP's
// "verify UPI ID" lookup: the registered name shown before paying. Every handle here is fictional and
// mirrors the server's seeded data (app/server/pehchaan_api/scenarios.py).

export interface Payee { vpa: string; name: string; hint?: string; hint_hi?: string }

const DIRECTORY: Payee[] = [
  { vpa: "ariftraders@okdemo", name: "Arif Traders", hint: "A shop you haven't paid before", hint_hi: "दुकान, पहले कभी नहीं भेजा" },
  { vpa: "rahul.sharma@okdemo", name: "Rahul Sharma", hint: "Rahul's new account", hint_hi: "राहुल का नया खाता" },
  { vpa: "rbi.kyc.update@okdemo", name: "Suresh Kumar", hint: "On the suspect list (mock I4C)", hint_hi: "संदिग्ध सूची में (मॉक I4C)" },
  { vpa: "sharma.logistics88@okdemo", name: "Sharma Logistics", hint: "A business you haven't paid before", hint_hi: "कंपनी, पहले कभी नहीं भेजा" },
  { vpa: "meena.g.kitty@okdemo", name: "Meena Gupta", hint: "Meena's new UPI ID", hint_hi: "मीना की नई UPI ID" },
  { vpa: "rahul.s@bdb", name: "Rahul Sharma" },
  { vpa: "priya.sharma@okdemo", name: "Priya Sharma" },
  { vpa: "meena.gupta@okdemo", name: "Meena Gupta" },
  { vpa: "jvvnl.bill@okdemo", name: "JVVNL Electricity" },
  { vpa: "kavya.ent.secure@okdemo", name: "Kavya Enterprises" },
  { vpa: "court.fee.desk@okdemo", name: "Gupta Traders" },
  { vpa: "fresh.mart@okdemo", name: "Fresh Mart" },
  { vpa: "sunita.sharma@bdb", name: "Sunita Sharma" },
  { vpa: "thames.lettings@okdemo", name: "Thames Lettings" },
];

/** Payees a tester can pick to vary the case; each one exercises a different signal. */
export const TRY_THESE = DIRECTORY.filter((p) => p.hint);

export const isVpa = (s: string) => /^[a-z0-9][a-z0-9._-]{1,48}@[a-z][a-z0-9]{1,15}$/i.test(s.trim());

/** Registered name for a UPI ID: the directory's, else one made from the handle (as unverified). */
export function resolvePayee(vpa: string, nameFromQr?: string | null): Payee & { verified: boolean } {
  const v = vpa.trim().toLowerCase();
  const hit = DIRECTORY.find((p) => p.vpa === v);
  if (hit) return { ...hit, verified: true };
  const words = v.split("@")[0].split(/[._\-0-9]+/).filter(Boolean);
  const derived = words.map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");
  return { vpa: v, name: nameFromQr?.trim() || derived || "UPI user", verified: false };
}

export const paidBefore = (list: { vpa: string }[], vpa: string) => list.find((p) => p.vpa === vpa.trim().toLowerCase());

/** Parse a `upi://pay?pa=…&pn=…&am=…&tn=…` link (from a QR or an intent). */
export function parseUpi(uri: string): { vpa: string; name: string | null; amount: number | null; note: string | null } | null {
  if (!/^upi:\/\/pay\?/i.test(uri.trim())) return null;
  const q = new URLSearchParams(uri.trim().replace(/^upi:\/\/pay\?/i, ""));
  const vpa = q.get("pa");
  if (!vpa || !isVpa(vpa)) return null;
  const am = Number(q.get("am"));
  // Whole rupees only: the amount keypad has no paise, so an amount with paise is left for the payer to type
  const amount = Number.isInteger(am) && am > 0 ? am : null;
  return { vpa, name: q.get("pn"), amount, note: q.get("tn") };
}

export const upiLink = (p: Payee, amount?: number) =>
  `upi://pay?pa=${encodeURIComponent(p.vpa)}&pn=${encodeURIComponent(p.name)}${amount ? `&am=${amount}` : ""}&cu=INR`;
