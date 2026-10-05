"""Detection metrics. Convention: label 1 = spoof (synthetic), 0 = bona fide; score higher = more synthetic.

Terminology (ASVspoof convention, stated in every results file):
  FAR = false acceptance rate = share of SPOOF clips accepted as bona fide (missed clones)
  FRR = false rejection rate  = share of BONA FIDE clips flagged as synthetic (false alarms on real people)
  EER = operating point where FAR == FRR
We report FRR at FAR = 5 % and 1 % (how many real callers get flagged if we want to miss at most 5 % / 1 %
of clones) and the converse FAR at FRR = 5 % / 1 % (how many clones slip through if we only tolerate
5 % / 1 % false alarms on real people), plus ROC AUC.
"""
import numpy as np


def _rates(y, s):
    y = np.asarray(y).astype(int)
    s = np.asarray(s, dtype=np.float64)
    order = np.argsort(-s, kind="mergesort")
    s, y = s[order], y[order]
    P, N = y.sum(), (1 - y).sum()
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    # thresholds between distinct scores; prepend "reject nothing"
    idx = np.r_[np.where(np.diff(s))[0], len(s) - 1]
    tpr = np.r_[0, tp[idx] / max(P, 1)]
    fpr = np.r_[0, fp[idx] / max(N, 1)]
    thr = np.r_[np.inf, s[idx]]
    far = 1 - tpr  # spoof accepted
    frr = fpr      # bona fide flagged
    return far, frr, thr, tpr, fpr


def eer(y, s):
    y = np.asarray(y)
    if len(np.unique(y)) < 2:
        return float("nan"), float("nan")
    far, frr, thr, _, _ = _rates(y, s)
    i = np.argmin(np.abs(far - frr))
    # linear interpolation between neighbours for a less jumpy estimate
    j = i + 1 if i + 1 < len(far) and (far[i] - frr[i]) * (far[i + 1] - frr[i + 1]) <= 0 else max(i - 1, 0)
    a, b = far[i] - frr[i], far[j] - frr[j]
    if a != b:
        t = a / (a - b)
        e = far[i] + t * (far[j] - far[i])
    else:
        e = (far[i] + frr[i]) / 2
    return float(e), float(thr[i])


def frr_at_far(y, s, target):
    far, frr, thr, _, _ = _rates(y, s)
    ok = np.where(far <= target)[0]
    return float(frr[ok[0]]) if len(ok) else 1.0


def far_at_frr(y, s, target):
    far, frr, thr, _, _ = _rates(y, s)
    ok = np.where(frr <= target)[0]
    return float(far[ok[-1]]) if len(ok) else 1.0


def auc(y, s):
    y = np.asarray(y)
    if len(np.unique(y)) < 2:
        return float("nan")
    _, _, _, tpr, fpr = _rates(y, s)
    trap = getattr(np, "trapezoid", None) or np.trapz
    return float(trap(np.r_[tpr, 1.0], np.r_[fpr, 1.0]))


def ece(y, p, n_bins=15):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    bins = np.linspace(0, 1, n_bins + 1)
    e = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi) if hi < 1 else (p >= lo) & (p <= hi)
        if m.any():
            e += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(e)


def summary(y, s):
    y = np.asarray(y)
    n_s, n_b = int((y == 1).sum()), int((y == 0).sum())
    out = {"n_spoof": n_s, "n_bonafide": n_b}
    if n_s == 0 or n_b == 0:
        out.update({"eer": None, "auc": None})
        return out
    e, t = eer(y, s)
    out.update({
        "eer": round(e, 4), "eer_threshold": round(t, 4), "auc": round(auc(y, s), 4),
        "frr_at_far5": round(frr_at_far(y, s, 0.05), 4), "frr_at_far1": round(frr_at_far(y, s, 0.01), 4),
        "far_at_frr5": round(far_at_frr(y, s, 0.05), 4), "far_at_frr1": round(far_at_frr(y, s, 0.01), 4),
    })
    return out


def det_curve(y, s, n=200):
    """Return (far, frr) arrays for plotting."""
    far, frr, _, _, _ = _rates(y, s)
    return far, frr


def bootstrap_eer_ci(y, s, n_boot=300, seed=0, alpha=0.05):
    y = np.asarray(y)
    s = np.asarray(s)
    r = np.random.default_rng(seed)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    if len(pos) < 2 or len(neg) < 2:
        return None
    vals = []
    for _ in range(n_boot):
        idx = np.r_[r.choice(pos, len(pos)), r.choice(neg, len(neg))]
        vals.append(eer(y[idx], s[idx])[0])
    return [round(float(np.percentile(vals, 100 * alpha / 2)), 4), round(float(np.percentile(vals, 100 * (1 - alpha / 2))), 4)]
