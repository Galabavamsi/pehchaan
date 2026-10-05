"""Latency check for POST /v1/risk/assess (SPEC 7: < 300 ms p95, no audio).

Measured in-process through the ASGI TestClient (includes HTTP routing,
validation, mock adapter lookups, fusion, SQLite writes and WS publish).
Writes app/server/latency.json for the deck.
"""
import json
import statistics
import time
from pathlib import Path


def test_risk_assess_latency(client):
    sc = client.post("/v1/demo/scenario/T1", params={"background": "false"}).json()
    body = {"payer_id": sc["payer"]["id"], "payment": sc["payment"], "call": sc["call"]}
    for _ in range(10):  # warm-up
        client.post("/v1/risk/assess", json=body)
    new_case, reassess, server_side = [], [], []
    for i in range(300):
        t0 = time.perf_counter()
        r = client.post("/v1/risk/assess", json=body)
        new_case.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200
        server_side.append(r.json()["latency_ms"])
        cid = r.json()["case_id"]
        t0 = time.perf_counter()
        client.post("/v1/risk/assess", json={"case_id": cid, "claim": "family", "claim_target": "rel_rahul"})
        reassess.append((time.perf_counter() - t0) * 1000)

    def pct(xs, q):
        xs = sorted(xs)
        return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]

    out = {
        "endpoint": "POST /v1/risk/assess", "n": len(new_case), "target_p95_ms": 300,
        "new_case_ms": {"p50": round(statistics.median(new_case), 2), "p95": round(pct(new_case, 0.95), 2),
                        "max": round(max(new_case), 2)},
        "reassess_with_claim_ms": {"p50": round(statistics.median(reassess), 2), "p95": round(pct(reassess, 0.95), 2)},
        "server_side_ms": {"p50": round(statistics.median(server_side), 2), "p95": round(pct(server_side, 0.95), 2)},
        "note": "In-process ASGI TestClient on a laptop (Windows 11, Python 3.12, SQLite). Excludes network/mTLS.",
    }
    Path(__file__).resolve().parents[1].joinpath("latency.json").write_text(json.dumps(out, indent=2))
    print("\nLATENCY", json.dumps(out))
    assert out["new_case_ms"]["p95"] < 300
    assert out["reassess_with_claim_ms"]["p95"] < 300
