"""Load and validate the fusion config (config.yaml).

The voice-band LRs can be swapped for measured values with one line in
config.yaml (`voice.lr_source: ../../ml/results/metrics.json`). The loader is
tolerant about the shape of metrics.json; see `load_measured_voice_lrs`.
"""
from __future__ import annotations

import copy
import json
import math
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from .signals import FAMILIES, SIGNAL_FAMILY, VOICE_BANDS

PKG_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PKG_DIR / "config.yaml"
REPO_ROOT = PKG_DIR.parent.parent
DEFAULT_ML_METRICS = REPO_ROOT / "ml" / "results" / "metrics.json"

Basis = Literal["assumed", "measured"]


class SignalCfg(BaseModel):
    lr: float = Field(gt=0)
    basis: Basis
    rationale: str
    family: str = ""
    source: str | None = None


class FamilyCfg(BaseModel):
    cap_lr: float = Field(gt=1)
    basis: Basis
    rationale: str


class PriorCfg(BaseModel):
    value: float = Field(gt=0, lt=1)
    basis: Basis
    rationale: str


class TierCfg(BaseModel):
    green_below: float
    red_at_or_above: float
    ask_claim_at_or_above: float = 0.01
    basis: Basis = "assumed"
    rationale: str = ""


class GuardrailCfg(BaseModel):
    g1_min_families: int = 2
    g1_min_family_lr: float = 3.0
    g1_excluded_families: list[str] = ["V"]
    g3_min_speech_sec: float = 4.0
    g3_min_snr_db: float = 10.0
    g4_flag_exception: str = "payee_flagged_high"
    g5_min_prior_payments: int = 3
    g5_max_amount_ratio: float = 1.5
    basis: Basis = "assumed"
    rationale: str = ""


class TriggerCfg(BaseModel):
    call_window_min: float = 10
    amount_abs_inr: float = 10000
    long_call_min: float = 15
    burst_window_min: float = 30
    burst_min_new_payees: int = 2


class ActionsCfg(BaseModel):
    amber_min_read_sec: int = 5
    hold_minutes: int = 30
    analyst_review_at_or_above_inr: float = 50000
    family_verify_timeout_sec: int = 180


class VoiceCfg(BaseModel):
    lr_source: str = "assumed"
    no_strong_evidence_lr_floor: float | None = 0.7
    band_thresholds: dict[str, float] = {
        "likely_synthetic_at_or_above": 0.70,
        "no_strong_evidence_below": 0.30,
    }
    measured_from: str | None = None
    model_version: str | None = None


class Config(BaseModel):
    version: str
    prior: PriorCfg
    tiers: TierCfg
    families: dict[str, FamilyCfg]
    signals: dict[str, SignalCfg]
    guardrails: GuardrailCfg
    trigger: TriggerCfg
    actions: ActionsCfg
    voice: VoiceCfg

    @model_validator(mode="after")
    def _check(self) -> "Config":
        missing = set(SIGNAL_FAMILY) - set(self.signals)
        extra = set(self.signals) - set(SIGNAL_FAMILY)
        if missing or extra:
            raise ValueError(f"config signals mismatch: missing={sorted(missing)} extra={sorted(extra)}")
        if set(self.families) != set(FAMILIES):
            raise ValueError("config families must be exactly C,K,P,V,S,O")
        for code, s in self.signals.items():
            s.family = SIGNAL_FAMILY[code]
        if not (0 < self.tiers.green_below < self.tiers.red_at_or_above < 1):
            raise ValueError("tier thresholds must satisfy 0 < green < red < 1")
        return self

    # convenience -------------------------------------------------------
    def ln_lr(self, code: str) -> float:
        return math.log(self.signals[code].lr)

    def ln_cap(self, family: str) -> float:
        return math.log(self.families[family].cap_lr)

    def with_prior(self, prior: float) -> "Config":
        c = self.model_copy(deep=True)
        c.prior.value = prior
        return c


# ---------------------------------------------------------------------------
# measured voice LRs
# ---------------------------------------------------------------------------
_SPOOF_KEYS = ("spoof", "synthetic", "fake", "attack", "scam")
_BONA_KEYS = ("bonafide", "bona_fide", "genuine", "real", "human")


def _norm_band(k: str) -> str | None:
    k = k.lower().replace("-", "_").replace(" ", "_")
    if k.startswith("voice_"):
        k = k[len("voice_"):]
    aliases = {
        "likely_synthetic": "likely_synthetic", "synthetic": "likely_synthetic", "high": "likely_synthetic",
        "inconclusive": "inconclusive", "uncertain": "inconclusive", "mid": "inconclusive",
        "no_strong_evidence": "no_strong_evidence", "low": "no_strong_evidence", "bona_fide_like": "no_strong_evidence",
    }
    return aliases.get(k)


def _walk(obj: Any, path: str = ""):
    yield path, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")


def _band_dict(d: Any) -> dict[str, float] | None:
    if not isinstance(d, dict):
        return None
    out = {}
    for k, v in d.items():
        b = _norm_band(str(k))
        if b and isinstance(v, (int, float)):
            out[b] = float(v)
    return out if len(out) >= 2 else None


def load_measured_voice_lrs(path: Path) -> tuple[dict[str, float], dict]:
    """Return ({band: LR}, provenance) from an ML metrics file.

    Accepted shapes (searched anywhere in the JSON; paths containing
    'held_out'/'heldout' are preferred because unseen generators are the
    honest case):
      1. {"band_lr": {"likely_synthetic": 7.1, "inconclusive": 1.0, "no_strong_evidence": 0.4}}
         (also "voice_band_lr", "fusion_lr", "lr")
      2. {"band_rates": {"spoof": {band: rate, ...}, "bonafide": {band: rate, ...}}}
         LR(band) = P(band | spoof) / P(band | bona fide), add-0.5 smoothed if counts.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    candidates: list[tuple[int, str, dict[str, float]]] = []
    for p, node in _walk(data):
        if not isinstance(node, dict):
            continue
        for key in ("band_lr", "voice_band_lr", "fusion_lr", "lr", "band_lrs"):
            bd = _band_dict(node.get(key))
            if bd:
                candidates.append((0, f"{p}.{key}" if p else key, bd))
        for key in ("band_rates", "band_probs", "rates_by_band", "confusion_by_band"):
            rates = node.get(key)
            if isinstance(rates, dict):
                spoof = next((_band_dict(rates[k]) for k in rates if any(s in k.lower() for s in _SPOOF_KEYS)), None)
                bona = next((_band_dict(rates[k]) for k in rates if any(s in k.lower() for s in _BONA_KEYS)), None)
                if spoof and bona:
                    lrs = {}
                    for b in VOICE_BANDS:
                        if b in spoof and b in bona:
                            lrs[b] = max(spoof[b], 1e-4) / max(bona[b], 1e-4)
                    if len(lrs) >= 2:
                        candidates.append((1, f"{p}.{key}" if p else key, lrs))
    if not candidates:
        raise ValueError(f"no voice band LRs or band rates found in {path}")
    candidates.sort(key=lambda c: (0 if ("held_out" in c[1] or "heldout" in c[1]) else 1, c[0]))
    prio, where, lrs = candidates[0]
    version = None
    for p, node in _walk(data):
        if isinstance(node, dict) and isinstance(node.get("model_version"), str):
            version = node["model_version"]
            break
    return lrs, {"file": str(path), "json_path": where, "model_version": version}


def _apply_measured_voice(cfg: Config, base_dir: Path) -> Config:
    src = cfg.voice.lr_source
    if not src or src == "assumed":
        return cfg
    path = (base_dir / src).resolve() if not Path(src).is_absolute() else Path(src)
    if not path.exists():
        warnings.warn(f"voice.lr_source {path} not found; keeping assumed voice LRs")
        return cfg
    lrs, prov = load_measured_voice_lrs(path)
    floor = cfg.voice.no_strong_evidence_lr_floor
    for band, lr in lrs.items():
        code = f"voice_{band}"
        note = f"measured from {prov['file']} ({prov['json_path']})"
        if band == "no_strong_evidence" and floor is not None and lr < floor:
            note += f"; raw {lr:.3f} floored at {floor} (G2 safety floor)"
            lr = floor
        cfg.signals[code] = SignalCfg(lr=lr, basis="measured", rationale=note, family="V", source=prov["file"])
    cfg.voice.measured_from = prov["file"]
    cfg.voice.model_version = prov["model_version"]
    return cfg


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if overrides:
        raw = _deep_merge(copy.deepcopy(raw), overrides)
    cfg = Config.model_validate(raw)
    return _apply_measured_voice(cfg, path.parent)


@lru_cache(maxsize=1)
def default_config() -> Config:
    return load_config()


def _deep_merge(a: dict, b: dict) -> dict:
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_merge(a[k], v)
        else:
            a[k] = v
    return a
