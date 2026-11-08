"""The paper's figure: every hypothesis comparison with both bootstrap intervals.

    python -m jr.figures      writes paper/fig_primary.pdf
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import jr  # noqa: E402

NAMES = {"late_closure": "Late closure", "seriously_late": "Seriously late", "spillover": "Spillover",
         "serious_spillover": "Serious spillover", "scope_churn": "Scope churn"}


def rows():
    p = pd.read_csv(jr.RESULTS / "planning_differences.csv")
    p = p[p.primary == True]  # noqa: E712
    i = pd.read_csv(jr.RESULTS / "insprint_differences.csv")
    i = i[i.primary == True]  # noqa: E712
    out = []
    for h, comp, outs in (("H1", "strict+new - strict", list(NAMES)), ("H4", "strict+new - scope", list(NAMES))):
        for o in outs:
            r = p[(p.outcome == o) & (p.comparison == comp)].iloc[0]
            out.append((h, NAMES[o], r))
    for h, comp, outs in (("H2", "ours - worki", ["spillover", "serious_spillover"]),
                          ("H3", "ours - choet", ["spillover", "serious_spillover", "late_closure", "seriously_late"])):
        for o in outs:
            for cp in (0.25, 0.5):
                r = i[(i.outcome == o) & (i.comparison == comp) & (i.checkpoint == cp)].iloc[0]
                out.append((h, f"{NAMES[o]}, {int(cp * 100)}%", r))
    return out


def main():
    rs = rows()
    fig, ax = plt.subplots(figsize=(3.5, 6.2))
    y, ticks, labels, prev = 0, [], [], None
    for h, lab, r in rs:
        if prev is not None and h != prev:
            y += 0.8
        holds = r.ci_low > 0
        ax.plot([r.sprint_ci_low, r.sprint_ci_high], [y, y], color="0.7", lw=4, solid_capstyle="butt")
        ax.plot([r.ci_low, r.ci_high], [y, y], color="black", lw=1)
        ax.plot([r.delta], [y], "o", ms=4, mfc="black" if holds else "white", mec="black")
        ticks.append(y)
        labels.append(f"{h}  {lab}")
        prev = h
        y += 1
    ax.axvline(0, color="0.4", lw=0.6, ls="--")
    ax.set_yticks(ticks)
    ax.set_yticklabels(labels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("Difference in ROC-AUC", fontsize=7)
    ax.tick_params(axis="x", labelsize=6.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(jr.ROOT / "paper" / "fig_primary.pdf")


def carry_figure():
    """Per-project median carry ratio on the full 29-project export, with the projects excluded by the
    recording check marked. Always drawn from the uncleaned frame so the excluded projects are visible."""
    full = jr.ROOT / "data" / "tawos_all"
    f = pd.read_csv(full / "planning_frame.csv")
    rc = pd.read_csv(full / "recording_check.csv") if (full / "recording_check.csv").exists() else None
    ne = f[f.nonempty]
    g = ne.groupby("project").agg(med=("carry_ratio", "median"), none=("carry_ratio", lambda x: (x == 1).mean()))
    g = g.sort_values("med")
    bad = set(rc.loc[rc.excluded, "project"]) if rc is not None else set()
    fig, ax = plt.subplots(figsize=(3.5, 4.6))
    ys = range(len(g))
    colors = ["#b2182b" if p in bad else "0.25" for p in g.index]
    ax.barh(list(ys), g.none, color="0.8", height=0.75, label="sprints finishing nothing")
    ax.scatter(g.med, list(ys), c=colors, s=14, zorder=3, label="median carry ratio")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([p.replace("Atlassian ", "") for p in g.index], fontsize=5.8)
    for t, p in zip(ax.get_yticklabels(), g.index):
        if p in bad:
            t.set_color("#b2182b")
    ax.set_xlim(0, 1.02)
    ax.set_xlabel("Share of committed issues (dot) or of sprints (bar)", fontsize=6.5)
    ax.tick_params(axis="x", labelsize=6.5)
    ax.legend(fontsize=5.8, loc="lower right", frameon=False)
    for s_ in ("top", "right"):
        ax.spines[s_].set_visible(False)
    fig.tight_layout()
    fig.savefig(jr.ROOT / "paper" / "fig_carry.pdf")


def reliability_figure():
    r = pd.read_csv(jr.RESULTS / "robust_reliability.csv")
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 1.9), sharey=True)
    for ax, o, title in zip(axes, ("serious_spillover", "late_closure"), ("Serious spillover", "Late closure")):
        for st, mk, lab in ((0.0, "o", "planning"), (0.5, "s", "50% of sprint")):
            d = r[(r.outcome == o) & (r.stage == st) & (r.n >= 10)]
            ax.plot(d.mean_predicted, d.observed, marker=mk, ms=3, lw=0.8, label=lab,
                    color="black" if st == 0.0 else "0.55")
        ax.plot([0, 1], [0, 1], ls="--", lw=0.5, color="0.5")
        ax.set_title(title, fontsize=7)
        ax.set_xlabel("Predicted risk", fontsize=6.5)
        ax.tick_params(labelsize=6)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
    axes[0].set_ylabel("Observed rate", fontsize=6.5)
    axes[0].legend(fontsize=5.5, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(jr.ROOT / "paper" / "fig_reliability.pdf")


if __name__ == "__main__":
    main()
    carry_figure()
    if (jr.RESULTS / "robust_reliability.csv").exists():
        reliability_figure()
