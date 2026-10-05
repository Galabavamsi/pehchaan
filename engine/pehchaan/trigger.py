"""When Pehchaan runs (SPEC section 2). No audio is used here.

Pehchaan assesses a payment only if BOTH hold:
  * a phone/VoIP call is active, or ended <= 10 minutes ago; and
  * the payee is new, or the amount is above the user's p95, or >= Rs 10,000.
Trusted bypass (G5): payee paid >= 3 times and amount <= 1.5x usual -> Green.
"""
from __future__ import annotations

from pydantic import BaseModel

from .config import Config, default_config


class TriggerInput(BaseModel):
    call_active: bool = False
    call_ended_sec_ago: float | None = None
    payee_new: bool = False
    amount_inr: float = 0
    amount_p95_inr: float | None = None


class TriggerResult(BaseModel):
    fired: bool
    call_condition: bool
    payment_condition: bool
    why: list[str]


def evaluate_trigger(t: TriggerInput, cfg: Config | None = None) -> TriggerResult:
    cfg = cfg or default_config()
    why: list[str] = []
    call_ok = t.call_active or (
        t.call_ended_sec_ago is not None and t.call_ended_sec_ago <= cfg.trigger.call_window_min * 60
    )
    if t.call_active:
        why.append("call active")
    elif call_ok:
        why.append(f"call ended {t.call_ended_sec_ago / 60:.1f} min ago")
    pay_ok = False
    if t.payee_new:
        pay_ok = True
        why.append("new payee")
    if t.amount_p95_inr is not None and t.amount_inr > t.amount_p95_inr:
        pay_ok = True
        why.append("amount above usual (p95)")
    if t.amount_inr >= cfg.trigger.amount_abs_inr:
        pay_ok = True
        why.append(f"amount >= {cfg.trigger.amount_abs_inr:,.0f}")
    return TriggerResult(fired=call_ok and pay_ok, call_condition=call_ok, payment_condition=pay_ok, why=why)
