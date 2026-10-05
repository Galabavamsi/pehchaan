"""SVG charts for the alert-budget simulator (deck-ready).

Designed at 600 px wide (1 SVG unit = 1 px when placed at 600 px on a
1280x720 slide), so every label is >= 12 px. Text stays text
(svg.fonttype='none') and names the deck fonts: Space Grotesk (titles), Inter
(labels), JetBrains Mono (numbers). PNG previews (1200 px) are written to
results/preview/ for checking layout.
"""
from __future__ import annotations

import glob
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

PAPER, INK, ORANGE, TEAL, AMBER, RED, SLATE = "#f5f0e6", "#1b1f24", "#e8742a", "#13796f", "#e0a526", "#c8372d", "#6b7280"
GRID = "#e2d9c6"
TITLE = ["Space Grotesk", "Space Grotesk Light", "Inter", "sans-serif"]
BODY = ["Inter", "Noto Sans Devanagari", "sans-serif"]
MONO = ["JetBrains Mono", "monospace"]
W_IN = 600 / 72  # 600 SVG units wide
FOOT = "Assumption-driven projection · engine/sim_assumptions.yaml"

_REPO = Path(__file__).resolve().parents[2]
for _f in glob.glob(str(_REPO / "deck" / "tooling-samples" / "fonts-ttf" / "*.ttf")):
    try:
        fm.fontManager.addfont(_f)
    except Exception:  # pragma: no cover
        pass

plt.rcParams.update({
    "svg.fonttype": "none", "font.family": BODY, "font.size": 13, "axes.edgecolor": GRID,
    "axes.linewidth": 1, "xtick.color": SLATE, "ytick.color": SLATE, "xtick.labelsize": 13,
    "ytick.labelsize": 13, "axes.labelcolor": SLATE, "figure.dpi": 72, "savefig.dpi": 72,
})


def _fig(h_px: float):
    fig = plt.figure(figsize=(W_IN, h_px / 72))
    fig.patch.set_alpha(0)
    return fig


def _px(fig, x_px: float, y_px: float) -> tuple[float, float]:
    """figure fraction from px measured from the top-left."""
    w, h = fig.get_size_inches() * 72
    return x_px / w, 1 - y_px / h


def _header(fig, title: str, subtitle: str):
    fig.text(*_px(fig, 20, 30), title, family=TITLE, weight="bold", size=20, color=INK, va="baseline")
    fig.text(*_px(fig, 20, 52), subtitle, family=BODY, size=13, color=SLATE, va="baseline")


def _footer(fig, extra: str = ""):
    h = fig.get_size_inches()[1] * 72
    fig.text(*_px(fig, 20, h - 10), FOOT + (f" · {extra}" if extra else ""), family=BODY, size=12, color=SLATE,
             va="baseline")


def _clean(ax, grid_axis: str = "x"):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(False)
    ax.set_facecolor("none")
    if grid_axis in ("x", "y", "both"):
        ax.grid(axis=grid_axis, color=GRID, linewidth=1, zorder=0)
    ax.tick_params(length=0)


def _hbar(ax, fig, y, w, h, color, r_px=4.0, z=3):
    """Horizontal bar, square at the baseline, 4 px rounded data-end."""
    if w <= 0:
        return
    bb = ax.get_window_extent()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    sx = bb.width / (x1 - x0)  # px per data unit
    sy = bb.height / abs(y1 - y0)
    r = min(r_px / sx, w / 2)
    ax.add_patch(FancyBboxPatch((0, y - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                mutation_aspect=sx / sy, facecolor=color, edgecolor="none", zorder=z))
    ax.add_patch(Rectangle((0, y - h / 2), max(w - r, 0), h, facecolor=color, edgecolor="none", zorder=z))


def _vbar(ax, x, w, h, color, r_px=4.0, z=3):
    """Vertical bar, square at the baseline, 4 px rounded data-end."""
    if h <= 0:
        return
    bb = ax.get_window_extent()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    sx = bb.width / (x1 - x0)
    sy = bb.height / (y1 - y0)
    r_y = min(r_px / sy, h / 2)
    r_x = r_y * sy / sx  # rounding_size is in x units; mutation_aspect stretches it to r_y
    ax.add_patch(FancyBboxPatch((x - w / 2, 0), w, h, boxstyle=f"round,pad=0,rounding_size={r_x}",
                                mutation_aspect=sx / sy, facecolor=color, edgecolor="none", zorder=z))
    ax.add_patch(Rectangle((x - w / 2, 0), w, max(h - r_y, 0), facecolor=color, edgecolor="none", zorder=z))


def _canvas(fig, H):
    """Full-figure axes in px units (origin top-left) for hand-laid charts."""
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 600)
    ax.set_ylim(H, 0)
    ax.axis("off")
    return ax


def _pxbar(ax, x, y, w, h, color, r=4.0, z=3):
    """Horizontal bar in px units, square left end, rounded right end."""
    if w <= 0:
        return
    r = min(r, w / 2, h / 2)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", facecolor=color,
                                edgecolor="none", zorder=z))
    ax.add_patch(Rectangle((x, y), max(w - r, 0), h, facecolor=color, edgecolor="none", zorder=z))


def _fmt_pct(v: float) -> str:
    if v >= 10:
        return f"{v:.0f}%"
    if v >= 1:
        return f"{v:.1f}%"
    return f"{v:.2f}%"


def _save(fig, out: Path, name: str):
    out.mkdir(parents=True, exist_ok=True)
    fig.savefig(out / f"{name}.svg", format="svg", transparent=True)
    prev = out / "preview"
    prev.mkdir(exist_ok=True)
    fig.patch.set_alpha(1)
    fig.patch.set_facecolor(PAPER)
    fig.savefig(prev / f"{name}.png", format="png", dpi=144, facecolor=PAPER)
    plt.close(fig)


# ---------------------------------------------------------------------------
def chart_friction_funnel(summary: dict, out: Path):
    f = summary["friction_budget_genuine_pct"]
    asked = f["one_tap_question_then_green"] + f["saw_pause_and_verify"]
    rows = [
        ("Genuine payments made during or just after a call", 100.0, SLATE,
         f"{_fmt_pct(f['silent_green'])} go through with no screen at all"),
        ("Asked one tap: “Who asked you to make this payment?”", asked, ORANGE,
         f"{_fmt_pct(f['one_tap_question_then_green'])} answer and pay straight away"),
        ("Shown Pause & Verify (reasons + one-tap checks)", f["saw_pause_and_verify"], AMBER,
         f"{_fmt_pct(f['resolved_to_green_by_a_check'])} cleared by a check, e.g. the relative taps “Yes, it’s me”"),
        ("Payment held for 30 minutes (Red)", f["final_red_hold"], RED,
         "released after a check with the real person, or a bank review"),
    ]
    H = 470
    fig = _fig(H)
    _header(fig, "Friction budget for genuine payments",
            f"Share of genuine triggered payments · prior {summary['prior']['as_fraction']} · "
            f"{summary['voice']['check_uptake']:.0%} voice-check uptake")
    ax = _canvas(fig, H)
    x0, wmax, y = 20, 470, 96
    for lab, v, col, note in rows:
        ax.text(x0, y, lab, family=BODY, size=14, color=INK, va="baseline", weight="semibold")
        ax.add_patch(Rectangle((x0, y + 10), wmax, 22, facecolor=GRID, alpha=0.5, edgecolor="none", zorder=1))
        _pxbar(ax, x0, y + 10, wmax * v / 100, 22, col)
        ax.text(x0 + wmax + 10, y + 21, _fmt_pct(v), family=MONO, size=16, color=INK, va="center")
        ax.text(x0, y + 52, note, family=BODY, size=12.5, color=SLATE, va="baseline")
        y += 84
    _footer(fig, f"seed {summary['seed']}")
    _save(fig, out, "chart_friction_funnel")


def chart_catch_by_pattern(summary: dict, out: Path):
    c = summary["catch_rates_pct"]
    g = summary["friction_budget_genuine_pct"]
    rows = [("T1 Cloned relative", c["T1"]["saw_pause_and_verify"], c["T1"]["red_hold"]),
            ("T2 Fake bank official", c["T2"]["saw_pause_and_verify"], c["T2"]["red_hold"]),
            ("T3 Digital-arrest hybrid", c["T3"]["saw_pause_and_verify"], c["T3"]["red_hold"]),
            ("Genuine payments", g["saw_pause_and_verify"], g["final_red_hold"])]
    H = 430
    fig = _fig(H)
    _header(fig, "Scams are paused and held; genuine payments rarely are",
            f"% of triggered payments · prior {summary['prior']['as_fraction']} · "
            f"{summary['voice']['check_uptake']:.0%} voice-check uptake")
    # legend row
    lx, ly = 20, 78
    for col, lab in ((AMBER, "Paused (Pause & Verify shown)"), (RED, "Held 30 min (Red)")):
        fig.patches.append(Rectangle(_px(fig, lx, ly + 2), 14 / 600, 14 / H, transform=fig.transFigure,
                                     facecolor=col, edgecolor="none"))
        fig.text(*_px(fig, lx + 20, ly), lab, family=BODY, size=13, color=INK, va="center")
        lx += 250
    ax = fig.add_axes([182 / 600, 62 / H, 360 / 600, (H - 62 - 100) / H])
    ax.set_xlim(0, 100)
    ax.set_ylim(len(rows) - 0.45, -0.55)
    _clean(ax, "x")
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"], family=MONO, size=12.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], family=BODY, size=13.5, color=INK)
    ax.tick_params(axis="y", pad=10)
    fig.canvas.draw()
    for i, (_, pv, red) in enumerate(rows):
        _hbar(ax, fig, i - 0.17, pv, 0.26, AMBER)
        _hbar(ax, fig, i + 0.17, red, 0.26, RED)
        ax.text(pv + 1.2, i - 0.17, _fmt_pct(pv), family=MONO, size=13, color=INK, va="center", clip_on=False)
        ax.text(red + 1.2, i + 0.17, _fmt_pct(red), family=MONO, size=13, color=INK, va="center", clip_on=False)
    ax.plot([-48, 100], [2.55, 2.55], color="#cfc5b0", linewidth=1, clip_on=False, zorder=0)
    _footer(fig, f"seed {summary['seed']}")
    _save(fig, out, "chart_catch_by_pattern")


def chart_ablation(ablation: dict, summary: dict, out: Path):
    rows = ablation["rows"]
    labels = ["Context only\n(call + payment)", "+ one-tap\nclaim", "+ out-of-band\nchecks",
              f"+ voice check\n({ablation['voice_uptake']:.0%} uptake)"]
    series = [("scam_amber_plus_pct", AMBER, "Scams paused (Amber+)"),
              ("scam_red_pct", RED, "Scams held (Red)"),
              ("genuine_saw_pause_and_verify_pct", SLATE, "Genuine payments paused")]
    H = 430
    fig = _fig(H)
    _header(fig, "What each layer adds",
            f"Cumulative layers · scam patterns weighted T1/T2/T3 · prior {summary['prior']['as_fraction']}")
    lx, ly = 20, 78
    for _, col, lab in series:
        fig.patches.append(Rectangle(_px(fig, lx, ly + 2), 14 / 600, 14 / H, transform=fig.transFigure,
                                     facecolor=col, edgecolor="none"))
        fig.text(*_px(fig, lx + 20, ly), lab, family=BODY, size=13, color=INK, va="center")
        lx += {AMBER: 196, RED: 160, SLATE: 0}[col]
    ax = fig.add_axes([52 / 600, 112 / H, 530 / 600, (H - 112 - 118) / H])
    ax.set_xlim(-0.6, len(rows) - 0.4)
    ax.set_ylim(0, 100)
    _clean(ax, "y")
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0", "25", "50", "75", "100%"], family=MONO, size=12.5)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, family=BODY, size=13, color=INK, linespacing=1.15)
    ax.tick_params(axis="x", pad=8)
    fig.canvas.draw()
    bw = 0.24
    for i, r in enumerate(rows):
        for j, (key, col, _) in enumerate(series):
            x = i + (j - 1) * (bw + 0.035)
            v = r[key]
            _vbar(ax, x, bw, v, col)
            ax.text(x, v + 1.6, _fmt_pct(v), family=MONO, size=12, color=INK, ha="center", va="bottom")
        ax.text(i, -36, f"genuine held {_fmt_pct(r['genuine_red_pct'])}", family=BODY, size=12, color=SLATE,
                ha="center", va="top", clip_on=False)
    _footer(fig, f"voice band rates: {summary['voice']['band_rates_source'].split(' (')[0]}")
    _save(fig, out, "chart_ablation")


def chart_sensitivity(sensitivity: dict, summary: dict, out: Path):
    rows = sensitivity["rows"]
    priors = sorted({r["prior"] for r in rows})
    ups = sorted({r["voice_uptake"] for r in rows})
    H = 420
    fig = _fig(H)
    _header(fig, "Still works with zero voice checks",
            "Re-scored across the prior P(scam | trigger) and voice-check uptake")
    styles = {0.0: (INK, "0% voice checks"), 0.3: (ORANGE, "30%"), 0.7: (SLATE, "70%")}
    lx, ly = 20, 78
    for up in ups:
        col, lab = styles.get(up, (SLATE, f"{up:.0%}"))
        fig.add_artist(plt.Line2D([lx / 600, (lx + 18) / 600], [1 - (ly) / H] * 2, color=col, linewidth=2.5,
                                  transform=fig.transFigure))
        fig.text(*_px(fig, lx + 24, ly), lab, family=BODY, size=13, color=INK, va="center")
        lx += 150 if up == 0.0 else 70
    tick_lab = [("1/2k" if round(1 / p) == 2000 else "1/1k" if round(1 / p) == 1000 else f"1/{round(1 / p)}")
                for p in priors]
    anchor = summary["prior"]["base_rate_anchor"]["prior_derived"]
    default = summary["prior"]["value"]

    def setup(ax, ymax, yticks, label_lines=True):
        ax.set_xscale("log")
        ax.set_xlim(priors[0] / 1.25, priors[-1] * 1.25)
        ax.set_ylim(0, ymax)
        _clean(ax, "y")
        ax.set_xticks(priors)
        ax.set_xticklabels(tick_lab, family=MONO, size=12)
        ax.minorticks_off()
        ax.set_yticks(yticks)
        ax.set_yticklabels([f"{t:g}" for t in yticks[:-1]] + [f"{yticks[-1]:g}%"], family=MONO, size=12)
        for xv, lab in ((default, "SPEC default"), (anchor, "base-rate\nanchor")):
            ax.axvline(xv, color="#cfc5b0", linewidth=1, zorder=1)
            if label_lines:
                ax.text(xv * 1.06, ymax * 0.985, lab, family=BODY, size=12, color=SLATE, va="top", ha="left",
                        linespacing=1.1)

    axl = fig.add_axes([46 / 600, 92 / H, 238 / 600, (H - 92 - 128) / H])
    setup(axl, 100, [0, 25, 50, 75, 100])
    axl.set_title("Scams held (Red)", family=BODY, size=14, weight="semibold", color=INK, loc="left", pad=8)
    for up in ups:
        col, _ = styles.get(up, (SLATE, ""))
        ys = [next(r["scam_red_pct"] for r in rows if r["prior"] == p and r["voice_uptake"] == up) for p in priors]
        axl.plot(priors, ys, color=col, linewidth=2, solid_capstyle="round", zorder=4 if up == 0 else 3)
        axl.plot(priors, ys, "o", color=col, markersize=6, markeredgecolor=PAPER, markeredgewidth=2, zorder=5)
        if up == 0.0:
            axl.text(priors[0], ys[0] - 6, f"{ys[0]:.0f}%", family=MONO, size=12, color=INK, va="top", ha="center")
            axl.text(priors[-1], ys[-1] - 8, f"{ys[-1]:.0f}%", family=MONO, size=12, color=INK, va="top",
                     ha="center")

    axr = fig.add_axes([344 / 600, 92 / H, 236 / 600, (H - 92 - 128) / H])
    up0 = 0.3 if 0.3 in ups else ups[0]
    up0_label = f"{up0:.0%} voice"
    gmax = max(r["genuine_saw_pause_and_verify_pct"] for r in rows)
    ytop = 10 * (int(gmax / 10) + 1)
    setup(axr, ytop, list(range(0, ytop + 1, 10)), label_lines=False)
    axr.set_title(f"Genuine payments ({up0_label})", family=BODY, size=14, weight="semibold", color=INK, loc="left",
                  pad=8)
    for key, col, lab in (("genuine_saw_pause_and_verify_pct", AMBER, "paused"), ("genuine_red_pct", RED, "held")):
        ys = [next(r[key] for r in rows if r["prior"] == p and r["voice_uptake"] == up0) for p in priors]
        axr.plot(priors, ys, color=col, linewidth=2, solid_capstyle="round", zorder=3)
        axr.plot(priors, ys, "o", color=col, markersize=6, markeredgecolor=PAPER, markeredgewidth=2, zorder=5)
        axr.text(priors[-1] / 1.15, ys[-1] + ytop * 0.03, f"{lab} {_fmt_pct(ys[-1])}", family=MONO, size=12,
                 color=INK, va="bottom", ha="right")
    fig.text(*_px(fig, 46, H - 40), "x: prior P(scam | trigger fired), log scale · vertical lines in both panels",
             family=BODY, size=12.5, color=SLATE)
    _footer(fig, f"seed {summary['seed']}")
    _save(fig, out, "chart_sensitivity")


def render_all(summary: dict, sensitivity: dict, ablation: dict, out: Path):
    out = Path(out)
    chart_friction_funnel(summary, out)
    chart_catch_by_pattern(summary, out)
    chart_ablation(ablation, summary, out)
    chart_sensitivity(sensitivity, summary, out)
