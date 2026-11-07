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


if __name__ == "__main__":
    main()
