import { useEffect, useState } from "react";
import { ArrowRight, Microphone, ShieldCheck, Sliders, Sword } from "@phosphor-icons/react";
import { API } from "./api";
import { Seal } from "./components";

/** A walk-up visitor's way in: four things to try, each one minute. */
interface RedTeamRow { id: string; evasion: string; outcome: string; observed: string; why: string }
interface RedTeam { run_at: string; rows: RedTeamRow[]; declared: { evasion: string; status: string }[]; note: string }

const OUTCOME: Record<string, { label: string; cls: string }> = {
  stopped: { label: "Stopped", cls: "rt-ok" },
  paused: { label: "Paused and asked", cls: "rt-pause" },
  missed: { label: "Not caught", cls: "rt-miss" },
  passes: { label: "Real son goes through", cls: "rt-ok" },
  false_alarm: { label: "Real son blocked", cls: "rt-miss" },
  error: { label: "Error", cls: "rt-miss" },
};

function useRedTeam() {
  const [rt, setRt] = useState<RedTeam | null>(null);
  useEffect(() => { fetch(`${API}/v1/redteam`).then((r) => (r.ok ? r.json() : null)).then(setRt).catch(() => {}); }, []);
  return rt;
}

function counts(rt: RedTeam | null) {
  const c: Record<string, number> = {};
  for (const r of rt?.rows ?? []) c[r.outcome] = (c[r.outcome] ?? 0) + 1;
  return c;
}

function Top({ sub }: { sub?: string }) {
  return (
    <header className="tour-top">
      <a href="#/tour" className="wm" style={{ textDecoration: "none", color: "inherit" }}>
        <Seal size={26} /><span className="w">Pehchaan</span><span className="whi">पहचान</span>
      </a>
      <span className="tag">{sub ?? "Verify the person, not the voice."}</span>
    </header>
  );
}

export function Tour() {
  const rt = useRedTeam();
  const c = counts(rt);
  const cards = [
    { icon: <ShieldCheck size={26} weight="duotone" />, title: "Watch a cloned-voice scam get stopped", time: "1 min",
      body: "Sunita gets a WhatsApp call in her son's cloned voice asking for ₹50,000. She pays, Pehchaan asks who asked, her son's own phone says \"Not me\", and the money is held.",
      href: "#/demo?scenario=T1", cta: "Open the live demo" },
    { icon: <Sliders size={26} weight="duotone" />, title: "Try to fool it", time: "2 min", today: true,
      body: "Pick who calls, the call, the amount and the payee, then play it out on the two phones and the bank console.",
      href: "#/demo?scenario=T1&jury=1", cta: "Build your own case" },
    { icon: <Sword size={26} weight="duotone" />, title: "We attacked it ourselves", time: "1 min", today: true,
      body: rt ? `${rt.rows.length} cases run through the live pipeline: ${c.stopped ?? 0} attacks stopped, ${c.paused ?? 0} paused and asked, ${c.missed ?? 0} not caught${c.passes ? ", and the real son still gets through" : ""}. Plus what we changed because of them.`
        : "Every attack we could think of, run through the live pipeline, with what still gets through.",
      href: "#/redteam", cta: "See the attacks" },
    { icon: <Microphone size={26} weight="duotone" />, title: "Every detector, side by side", time: "1 min", today: true,
      body: "Drop any audio or record your own voice: several deepfake detectors score it in parallel. In Pehchaan the voice score is only a clue. It never holds money.",
      href: "#/bench", cta: "Open the bench" },
  ];
  return (
    <div className="tour">
      <Top />
      <main className="tour-body">
        <h1>A cloned voice can sound exactly like your son. So we check with your son.</h1>
        <p className="tour-lede">
          When a risky UPI payment happens during or just after a call, Pehchaan asks <b>"Who asked you to pay?"</b>,
          then checks that person out of band: on the relative's own phone, with the bank's call registry, or with a
          family safe word. The result is go, pause, or a 30-minute hold.
        </p>
        <div className="tour-grid">
          {cards.map((k) => (
            <a key={k.title} className="tcard" href={k.href}>
              <div className="tcard-h">{k.icon}<span className="tcard-time">{k.time}</span>{k.today && <span className="tcard-today">Built on site today</span>}</div>
              <h2>{k.title}</h2>
              <p>{k.body}</p>
              <span className="tcard-cta">{k.cta} <ArrowRight size={15} weight="bold" /></span>
            </a>
          ))}
        </div>
        <p className="tour-honest">
          <b>Why the voice score never decides.</b> On real phone calls to a handset no model had seen (consented team
          voices), our retrained detector caught 115 of 136 clones (84.6%) and flagged 11 of 138 genuine clips (8%).
          Both of our models missed all 12 clones from a commercial cloner neither was trained on. A detector helps;
          the person on the other phone decides.
        </p>
        <p className="tour-foot">All people, numbers, banks and UPI IDs on these screens are fictional. Context adapters (telecom, suspect registry, bank) are mocks.</p>
      </main>
    </div>
  );
}

export function RedTeamPage() {
  const rt = useRedTeam();
  const c = counts(rt);
  return (
    <div className="tour">
      <Top sub="Red team: we attacked it ourselves" />
      <main className="tour-body">
        <h1>Every attack we could think of, run through the live pipeline</h1>
        {!rt && <p className="tour-lede">Loading the last run…</p>}
        {rt && (<>
          <p className="tour-lede">
            Each row starts a fresh demo with fictional people and plays the attack through the same API the phones use.
            Run on {rt.run_at.slice(0, 10)} at {rt.run_at.slice(11, 16)}. Rows marked v0.3 are fixes we made on site
            because an earlier run showed the gap.
          </p>
          <div className="rt-sum">
            {(["stopped", "paused", "missed", "passes"] as const).filter((k) => c[k]).map((k) => (
              <span key={k} className={`rt-chip ${OUTCOME[k].cls}`}><b>{c[k]}</b> {OUTCOME[k].label.toLowerCase()}</span>
            ))}
            <a className="chipbtn" href="#/demo?scenario=T1&jury=1" style={{ marginLeft: "auto", textDecoration: "none" }}>Try one yourself</a>
          </div>
          <div className="rt-list">
            {rt.rows.map((r) => (
              <div key={r.id} className="rt-row">
                <div className="rt-id mono">{r.id}</div>
                <div className="rt-main">
                  <div className="rt-ev">{r.evasion}</div>
                  <div className="rt-obs">{r.observed}</div>
                  <div className="rt-why">{r.why}</div>
                </div>
                <span className={`rt-chip ${(OUTCOME[r.outcome] ?? OUTCOME.error).cls}`}>{(OUTCOME[r.outcome] ?? OUTCOME.error).label}</span>
              </div>
            ))}
          </div>
          <h2 className="rt-h2">Not runnable in software, stated plainly</h2>
          <div className="rt-list">
            {rt.declared.map((d) => (
              <div key={d.evasion} className="rt-row">
                <div className="rt-main"><div className="rt-ev">{d.evasion}</div><div className="rt-obs">{d.status}</div></div>
              </div>
            ))}
          </div>
          <p className="tour-foot">{rt.note} Source: <span className="mono">app/server/redteam.py</span> → <span className="mono">RED_TEAM.md</span>.</p>
        </>)}
      </main>
    </div>
  );
}
