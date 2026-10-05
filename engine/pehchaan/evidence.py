"""Evidence pack (SPEC section 5, "Report path").

* Case events form a SHA-256 hash chain: h_i = SHA256(canonical(event_i without hash) ), where the
  event carries prev_hash = h_{i-1} (genesis = 64 zeros). Any edit breaks every later link.
* The pack is signed with Ed25519 (python `cryptography`). The public key and
  key id travel with the pack; verify_pack() checks both chain and signature.
* Field mappings pre-fill NCRP (cybercrime.gov.in, "Report Financial Fraud")
  and Sanchar Saathi Chakshu ("Report Suspected Fraud Communication").
  Categories are copied from the live Chakshu form (checked 2026-10-06).
  Pehchaan never files anything itself: the user reviews and submits.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

IST = timezone(timedelta(hours=5, minutes=30))
GENESIS = "0" * 64
PACK_SCHEMA = "pehchaan.evidence/v1"


def now_ist() -> datetime:
    return datetime.now(IST)


def ist_iso(dt: datetime | None = None) -> str:
    return (dt or now_ist()).astimezone(IST).isoformat(timespec="seconds")


def canonical(obj: Any) -> bytes:
    """Deterministic JSON for hashing/signing (sorted keys, no spaces, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------
# hash chain
# ---------------------------------------------------------------------------
def chain_event(prev_hash: str, seq: int, etype: str, actor: str, data: dict, ts: str | None = None) -> dict:
    ev = {"seq": seq, "ts": ts or ist_iso(), "type": etype, "actor": actor, "data": data, "prev_hash": prev_hash}
    ev["hash"] = sha256_hex(canonical(ev))
    return ev


def append_event(chain: list[dict], etype: str, actor: str, data: dict, ts: str | None = None) -> dict:
    prev = chain[-1]["hash"] if chain else GENESIS
    ev = chain_event(prev, len(chain), etype, actor, data, ts)
    chain.append(ev)
    return ev


def verify_chain(chain: list[dict]) -> tuple[bool, str]:
    prev = GENESIS
    for i, ev in enumerate(chain):
        if ev.get("prev_hash") != prev:
            return False, f"event {i}: prev_hash does not match"
        body = {k: v for k, v in ev.items() if k != "hash"}
        if sha256_hex(canonical(body)) != ev.get("hash"):
            return False, f"event {i}: hash mismatch (content changed)"
        prev = ev["hash"]
    return True, "ok"


# ---------------------------------------------------------------------------
# signing
# ---------------------------------------------------------------------------
class Signer:
    """Ed25519 signer. In production the key lives in AWS KMS / CloudHSM; here it
    is a PEM file created on first use (gitignored)."""

    def __init__(self, key: Ed25519PrivateKey):
        self._key = key
        raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public_key_b64 = base64.b64encode(raw).decode()
        self.key_id = "ed25519:" + sha256_hex(raw)[:16]

    @classmethod
    def load_or_create(cls, path: str | Path) -> "Signer":
        path = Path(path)
        if path.exists():
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            assert isinstance(key, Ed25519PrivateKey)
            return cls(key)
        key = Ed25519PrivateKey.generate()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        return cls(key)

    @classmethod
    def ephemeral(cls) -> "Signer":
        return cls(Ed25519PrivateKey.generate())

    def sign(self, message: bytes) -> str:
        return base64.b64encode(self._key.sign(message)).decode()


def verify_signature(public_key_b64: str, message: bytes, sig_b64: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64)).verify(base64.b64decode(sig_b64), message)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# masking helpers
# ---------------------------------------------------------------------------
def mask_name(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(w[0] + "*" * max(1, len(w) - 2) + (w[-1] if len(w) > 1 else "") for w in name.split())


def mask_phone(num: str | None) -> str:
    if not num:
        return ""
    digits = [c for c in num if c.isdigit()]
    if len(digits) < 6:
        return num
    prefix = num[: num.find(digits[0]) + 2] if num.startswith("+") else digits[0] + digits[1]
    return f"{prefix}{'•' * (len(digits) - 5)}{''.join(digits[-3:])}"


# ---------------------------------------------------------------------------
# report pre-fill mappings
# ---------------------------------------------------------------------------
CHAKSHU_CATEGORIES = {
    "family": "Impersonation as a relative / friend",
    "authority": "Impersonation as Police, CBI, Customs, Aadhaar, RBI etc",
    "bank": "KYC and Payment related to Bank / Electricity / Gas / Insurance etc",
    "other": "Any Other Suspected Fraud",
    "none": "Any Other Suspected Fraud",
}


def _incident_text(case: dict) -> str:
    claim_words = {
        "family": f"a caller claiming to be my family member ({case.get('relative_name') or 'relative'})",
        "bank": f"a caller claiming to be from {case.get('bank_name') or 'my bank'}",
        "authority": "a caller claiming to be police / a government officer",
        "other": "a caller", "none": "a caller",
    }.get(case.get("claim") or "none", "a caller")
    held = case.get("status") in ("held", "cancelled", "reported")
    parts = [
        f"On {case.get('created_at_ist', '')[:16].replace('T', ' ')} IST I received a "
        f"{'WhatsApp/internet' if case.get('call_channel') in ('whatsapp', 'voip') else 'phone'} call from "
        f"{case.get('caller_number') or 'an unknown number'} from {claim_words}.",
        f"I was asked to pay {case.get('amount_display', '')} to {case.get('payee_name') or ''} "
        f"(UPI ID {case.get('payee_vpa') or ''}).",
    ]
    if case.get("check_summary"):
        parts.append(case["check_summary"])
    parts.append(
        "My bank app paused the payment before it was sent; no money was debited."
        if held else "The payment details are attached."
    )
    parts.append(f"Pehchaan case reference {case.get('case_id')}; signed evidence pack attached.")
    return " ".join(p for p in parts if p)


def ncrp_prefill(case: dict) -> dict:
    """Fields for cybercrime.gov.in > Report Cyber Crime > Financial Fraud.
    Field labels follow the public NCRP user manual (bank-published PDFs) and
    acknowledgement slips; verify against the live form before production."""
    debited = case.get("status") == "sent"
    return {
        "portal": "https://cybercrime.gov.in",
        "helpline": "1930",
        "fields": {
            "Category of complaint": "Online Financial Fraud",
            "Sub-category of complaint": "UPI Related Frauds",
            "Approximate date & time of incident/receiving information": case.get("created_at_ist"),
            "Is there any delay in reporting": "No",
            "Additional information about the incident (min 200 characters)": _incident_text(case),
            "Mode of money transfer": "UPI",
            "Bank / Wallet / Merchant": case.get("payer_bank") or "Bharat Demo Bank",
            "Account number / UPI ID (debited)": case.get("payer_vpa_masked"),
            "Transaction ID / UTR number": case.get("utr") or ("not sent — payment held by bank app" if not debited else ""),
            "Amount": int(case["amount_inr"]) if isinstance(case.get("amount_inr"), (int, float)) else case.get("amount_inr"),
            "Transaction date": (case.get("created_at_ist") or "")[:10],
            "Suspect mobile number": case.get("caller_number"),
            "Suspect UPI ID / bank account": case.get("payee_vpa"),
            "Suspect name (as shown on UPI)": case.get("payee_name"),
        },
        "user_must_fill": ["Complainant name, address, ID proof (entered by you on the portal)", "OTP verification"],
        "note": "Pre-filled for you to review. Pehchaan does not submit complaints on your behalf.",
    }


def chakshu_prefill(case: dict) -> dict:
    """Fields for sancharsaathi.gov.in/sfc > Report Suspected Fraud Communication.
    Medium and category values copied from the live form (2026-10-06)."""
    channel = case.get("call_channel")
    return {
        "portal": "https://sancharsaathi.gov.in/sfc/",
        "fields": {
            "Medium of suspected fraud communication": "WhatsApp" if channel == "whatsapp" else "Call",
            "Type of suspected WhatsApp communication": "WhatsApp Call" if channel == "whatsapp" else None,
            "Suspected fraud communication category": CHAKSHU_CATEGORIES.get(case.get("claim") or "none"),
            "Number from which communication received": case.get("caller_number"),
            "Date and time of communication": case.get("created_at_ist"),
            "Complaint details": _incident_text(case)[:500],
        },
        "user_must_fill": ["Your name and mobile number (OTP verification on the portal)"],
        "note": "Chakshu reports help DoT disconnect numbers used for impersonation.",
    }


def psp_mule_flag(case: dict) -> dict:
    return {
        "to": "PSP mule-risk team (payee bank)",
        "payee_vpa": case.get("payee_vpa"),
        "reason_codes": [r["code"] for r in case.get("reasons", [])][:6],
        "case_id": case.get("case_id"),
    }


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------
def build_evidence_pack(case: dict, events: list[dict], signer: Signer, *, include_transcript: bool = False,
                        now_iso: str | None = None) -> dict:
    ok, msg = verify_chain(events)
    now_iso = now_iso or ist_iso()
    pack = {
        "schema": PACK_SCHEMA,
        "case_id": case["case_id"],
        "generated_at_ist": now_iso,
        "payer": {"name_masked": mask_name(case.get("payer_name")), "phone_masked": mask_phone(case.get("payer_phone")),
                  "vpa_masked": case.get("payer_vpa_masked")},
        "payment": {"payee_vpa": case.get("payee_vpa"), "payee_name": case.get("payee_name"),
                    "amount_inr": case.get("amount_inr"), "status": case.get("status")},
        "call": {"caller_number": case.get("caller_number"), "channel": case.get("call_channel"),
                 "duration_sec": case.get("call_duration_sec")},
        "claim": case.get("claim"),
        "decision": {"tier": case.get("tier"), "p": case.get("p"), "guardrails": case.get("guardrails", []),
                     "config_version": case.get("config_version")},
        "reasons": [{"code": r["code"], "family": r["family"], "contribution_ln_lr": round(r["contribution"], 4),
                     "text_en": r["text"]["en"], "text_hi": r["text"]["hi"]} for r in case.get("reasons", [])],
        "voice": case.get("voice"),
        "transcript_snippet": case.get("transcript_snippet") if include_transcript else None,
        "events": events,
        "hash_chain": {"algorithm": "SHA-256", "head": events[-1]["hash"] if events else GENESIS,
                       "length": len(events), "verified": ok, "detail": msg},
        "prefill": {"ncrp": ncrp_prefill(case), "chakshu": chakshu_prefill(case), "psp_mule_flag": psp_mule_flag(case)},
        "privacy": {"audio_included": False,
                    "note": "No call recording is included. Audio was scored in memory and discarded unless you chose 'Save as evidence'."},
    }
    digest = sha256_hex(canonical(pack))
    pack["signature"] = {
        "alg": "Ed25519", "key_id": signer.key_id, "public_key_b64": signer.public_key_b64,
        "signed_sha256": digest, "sig_b64": signer.sign(digest.encode()), "signed_at_ist": now_iso,
    }
    return pack


def verify_pack(pack: dict) -> tuple[bool, str]:
    sig = pack.get("signature") or {}
    body = {k: v for k, v in pack.items() if k != "signature"}
    digest = sha256_hex(canonical(body))
    if digest != sig.get("signed_sha256"):
        return False, "pack content changed after signing"
    if not verify_signature(sig.get("public_key_b64", ""), digest.encode(), sig.get("sig_b64", "")):
        return False, "bad signature"
    ok, msg = verify_chain(pack.get("events", []))
    return (ok, "ok" if ok else msg)


# ---------------------------------------------------------------------------
# optional 1-page PDF (Playwright / Chromium)
# ---------------------------------------------------------------------------
def render_pack_html(pack: dict, fonts_css_href: str | None = None) -> str:
    from html import escape as e

    p, pay, call = pack["payer"], pack["payment"], pack["call"]
    reasons = "".join(
        f"<tr><td class=m>{e(r['family'])}</td><td>{e(r['text_en'])}<div class=hi>{e(r['text_hi'])}</div></td>"
        f"<td class='m r'>{r['contribution_ln_lr']:+.2f}</td></tr>" for r in pack["reasons"][:8])
    events = "".join(
        f"<tr><td class=m>{ev['seq']}</td><td class=m>{e(ev['ts'][11:19])}</td><td>{e(ev['type'])}</td>"
        f"<td class=m>{ev['hash'][:16]}…</td></tr>" for ev in pack["events"][-10:])
    ncrp = "".join(f"<tr><td>{e(k)}</td><td>{e(str(v) if v is not None else '')}</td></tr>"
                   for k, v in pack["prefill"]["ncrp"]["fields"].items() if not k.startswith("Additional"))
    ch = "".join(f"<tr><td>{e(k)}</td><td>{e(str(v))}</td></tr>"
                 for k, v in pack["prefill"]["chakshu"]["fields"].items() if v and k != "Complaint details")
    voice = pack.get("voice") or {}
    vline = (f"p_synthetic {voice.get('p_synthetic', 0):.2f} · band {e(str(voice.get('band')))} · model {e(str(voice.get('model_version')))}"
             if voice else "No voice check performed")
    fonts = f"<link rel=stylesheet href='{fonts_css_href}'>" if fonts_css_href else ""
    sig = pack["signature"]
    return f"""<!doctype html><html><head><meta charset=utf-8>{fonts}<style>
@page {{ size: A4; margin: 12mm }}
body {{ font-family: Inter, 'Noto Sans Devanagari', sans-serif; color:#1b1f24; font-size:9.5px; margin:0 }}
h1 {{ font-family:'Space Grotesk',Inter,sans-serif; font-size:20px; margin:0 }}
h2 {{ font-family:'Space Grotesk',Inter,sans-serif; font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#6b7280; margin:10px 0 4px }}
.m {{ font-family:'JetBrains Mono',monospace; font-size:8.5px }} .r {{ text-align:right }}
.hi {{ color:#6b7280; font-size:8.5px }}
table {{ width:100%; border-collapse:collapse }} td {{ border-bottom:1px solid #e5dccb; padding:3px 4px; vertical-align:top }}
.top {{ display:flex; justify-content:space-between; align-items:flex-end; border-bottom:3px solid #e8742a; padding-bottom:6px }}
.chip {{ display:inline-block; padding:2px 8px; border-radius:99px; color:#fff; font-weight:700; background:{ {'red':'#c8372d','amber':'#e0a526','green':'#13796f'}.get(pack['decision']['tier'],'#6b7280') } }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px }}
.box {{ background:#f5f0e6; padding:6px 8px; border-radius:6px }}
</style></head><body>
<div class=top><div><div class=m style="color:#e8742a">PEHCHAAN · SIGNED EVIDENCE PACK</div><h1>Case {e(pack['case_id'])}</h1></div>
<div style="text-align:right"><span class=chip>{e(pack['decision']['tier'].upper())}</span><div class=m>generated {e(pack['generated_at_ist'])}</div></div></div>
<div class=grid style="margin-top:8px">
<div class=box><b>Payer</b> {e(p['name_masked'])} · <span class=m>{e(p['phone_masked'])}</span><br>
<b>Payee</b> {e(str(pay['payee_name']))} · <span class=m>{e(str(pay['payee_vpa']))}</span><br>
<b>Amount</b> <span class=m>{e(_inr(pay['amount_inr']))}</span> · status <b>{e(str(pay['status']))}</b></div>
<div class=box><b>Caller</b> <span class=m>{e(str(call['caller_number']))}</span> · {e(str(call['channel']))}<br>
<b>Claim</b> {e(str(pack['claim']))} · <b>p</b> <span class=m>{pack['decision']['p']:.3f}</span><br>
<b>Voice</b> {vline}</div></div>
<h2>Reasons (ln-LR contribution)</h2><table>{reasons}</table>
<h2>Guardrails applied</h2><div>{e(', '.join(g['id'] + ' ' + g['effect'] for g in pack['decision']['guardrails']) or 'none')}</div>
<div class=grid><div><h2>NCRP pre-fill (cybercrime.gov.in · 1930)</h2><table>{ncrp}</table></div>
<div><h2>Chakshu pre-fill (Sanchar Saathi)</h2><table>{ch}</table>
<h2>Case events · SHA-256 chain</h2><table>{events}</table></div></div>
<h2>Integrity</h2><div class=m>chain head {pack['hash_chain']['head']} · {pack['hash_chain']['length']} events · verified={pack['hash_chain']['verified']}<br>
{e(sig['alg'])} {e(sig['key_id'])} · sig {sig['sig_b64'][:44]}…</div>
<p class=hi>Pre-filled for the user to review and submit. Pehchaan never files a police complaint by itself. No call audio is included.</p>
</body></html>"""


def _inr(v) -> str:
    from .explain import format_inr
    return format_inr(v) if isinstance(v, (int, float)) else str(v)


def render_pack_pdf(pack: dict, out_path: str | Path, fonts_css_href: str | None = None) -> Path | None:
    """Render a 1-page PDF with Playwright. Returns None if Playwright is unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # pragma: no cover
        return None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html = render_pack_html(pack, fonts_css_href)
    tmp = out_path.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(150)
        pg.pdf(path=str(out_path), format="A4", print_background=True)
        b.close()
    tmp.unlink(missing_ok=True)
    return out_path
