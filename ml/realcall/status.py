"""Progress against this week's collection targets (README "Targets").  python -m realcall.status"""
import pandas as pd

from realcall import protocol
from realcall.settings import MANIFESTS, calls

TARGETS = {"live_test": protocol.GATE_MIN_LIVE_CALLS, "live_train": 40, "tape": 60, "uplink": 10, "speakers": 8}


def main():
    cs = [c for c in calls().values() if c.get("kind")]
    done = [c for c in cs if "hangup_t" in c or c.get("file") or c.get("uplink_wav")]
    by = pd.DataFrame([{"kind": c["kind"], "route": c.get("route"), "device": c.get("device"),
                        "speaker": c.get("speaker") or c.get("caller") or "", "cause": c.get("hangup_cause")} for c in done])
    print(f"calls registered {len(cs)}, finished {len(done)}")
    if by.empty:
        return
    print(by.groupby(["kind", "route"]).size().to_string(), "\n")
    p = MANIFESTS / "realcall.csv"
    if p.exists():
        m = pd.read_csv(p)
        live = m[(m.kind == "live") & (m.gate_window.astype(str) == "True") & (m.qc == "ok")]
        lt, ltr = int((live.split == "test").sum()), int((live.split != "test").sum())
        spk = m[(m.label == "bonafide") & (m.qc == "ok")].speaker.nunique()
        rows = [("live genuine calls, test", lt, TARGETS["live_test"]), ("live genuine calls, train/dev", ltr, TARGETS["live_train"]),
                ("tape calls", m[m.kind == "tape"].call_id.nunique(), TARGETS["tape"]),
                ("uplink calls", m[m.kind == "uplink"].call_id.nunique(), TARGETS["uplink"]),
                ("distinct genuine speakers", spk, TARGETS["speakers"])]
        for name, have, want in rows:
            print(f"{name:32s} {have:4d} / {want:<4d} {'ok' if have >= want else ''}")
        tape = m[m.kind == "tape"]
        if len(tape):
            print(f"\ntape items qc ok: {(tape.qc == 'ok').mean() * 100:.0f} % of {len(tape)}")


if __name__ == "__main__":
    main()
