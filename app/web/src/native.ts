// Bridge to the native Pehchaan SDK when the demo runs inside the Android app (SPEC §7). On the web, isNative
// is false and every screen behaves exactly as before.
import { useEffect, useState } from "react";
import { Capacitor, registerPlugin, type PluginListenerHandle } from "@capacitor/core";

export const isNative = Capacitor.isNativePlatform();
if (isNative) document.documentElement.classList.add("native");

/** The `call` object of POST /v1/risk/assess, read from the phone. */
export interface PhoneCall {
  state: "active" | "ended" | "none"; number: string | null; channel: "pstn" | "voip";
  duration_sec: number | null; ended_sec_ago: number | null; in_contacts?: boolean;
}
/** meta is for this phone's own screen; contact_name is the saved name and is never sent anywhere. */
export interface CallInfo {
  call: PhoneCall; meta: { source: string; audio_mode: number; screen_recording: boolean | null; contact_name?: string | null };
}
export interface NativeStatus {
  phone: boolean; contacts: boolean; notifications: boolean; call_log: boolean; full_screen: boolean;
  battery_unrestricted: boolean; sdk_int: number; screen_share_detect: boolean;
}

interface PehchaanPlugin {
  getCallContext(): Promise<CallInfo>;
  status(): Promise<NativeStatus>;
  requestForRole(o: { role: Role }): Promise<NativeStatus>;
  startProtection(o: { role: "payer" | "relative"; deviceId?: string; api: string }): Promise<void>;
  stopProtection(): Promise<void>;
  setSecure(o: { on: boolean }): Promise<void>;
  openSettings(o: { which: "battery" | "fullscreen" | "notifications" | "app" }): Promise<void>;
  getLaunchRoute(): Promise<{ route: string | null }>;
  addListener(ev: "callChanged", f: (c: CallInfo) => void): Promise<PluginListenerHandle>;
  addListener(ev: "screenRecording", f: (r: { recording: boolean }) => void): Promise<PluginListenerHandle>;
  addListener(ev: "route", f: (r: { route: string }) => void): Promise<PluginListenerHandle>;
}

export const Pehchaan = registerPlugin<PehchaanPlugin>("Pehchaan");

/** Live call context: pushed by the SDK on every change, re-read every 2 s so durations stay current. */
export function usePhoneCall(): CallInfo | null {
  const [info, setInfo] = useState<CallInfo | null>(null);
  useEffect(() => {
    if (!isNative) return;
    let alive = true;
    const read = () => Pehchaan.getCallContext().then((c) => alive && setInfo(c)).catch(() => {});
    read();
    const t = setInterval(read, 2000);
    const h = Pehchaan.addListener("callChanged", (c) => alive && setInfo(c));
    return () => { alive = false; clearInterval(t); h.then((x) => x.remove()); };
  }, []);
  return info;
}

/**
 * Rehearsal mode: every caller is treated as unknown, so a team whose numbers are all saved on each other's
 * phones can rehearse the full flow. It changes only `in_contacts` in what is sent, and the screens say it is on.
 */
const REHEARSAL_KEY = "demopay.rehearsal";
export const rehearsal = {
  get: () => { try { return localStorage.getItem(REHEARSAL_KEY) === "1"; } catch { return false; } },
  set: (on: boolean) => { try { localStorage.setItem(REHEARSAL_KEY, on ? "1" : "0"); } catch { /* ignore */ } },
};
export const forRehearsal = (c: PhoneCall): PhoneCall =>
  rehearsal.get() && c.state !== "none" && c.number ? { ...c, in_contacts: false } : c;

export type Role = "payer" | "relative";
