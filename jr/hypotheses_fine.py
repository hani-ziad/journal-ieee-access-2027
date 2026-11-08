"""The 22 hypothesis comparisons again, with 10,000 project-level bootstrap resamples, so that the
Holm-adjusted p-values are not limited by the resolution of 2,000 resamples (smallest p 1/2,000).

    python -m jr.hypotheses_fine     writes results/<cohort>/hypotheses_fine.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import jr
import jr.run as run
from jr.data import OUTCOMES
from jr.run import IN_SETS, PLAN_SETS, PRIMARY_MODEL, cluster_diff, scores, save, unit
from phase2.data import population

HYP = [("H1", "planning", ("strict+new", "strict"), list(OUTCOMES), [None]),
       ("H2", "in-sprint", ("ours", "worki"), ["spillover", "serious_spillover"], [0.25, 0.5]),
       ("H3", "in-sprint", ("ours", "choet"), ["spillover", "serious_spillover", "late_closure", "seriously_late"], [0.25, 0.5]),
       ("H4", "planning", ("strict+new", "scope"), list(OUTCOMES), [None])]


def main():
    run.N_BOOT = 10_000
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    rows = []
    for h, stage, (a, b), outs, cps in HYP:
        for o in outs:
            for cp in cps:
                def work(rng, h=h, stage=stage, a=a, b=b, o=o, cp=cp):
                    y = OUTCOMES[o][1]
                    if stage == "planning":
                        pop = OUTCOMES[o][0]
                        fr = population(f, pop).dropna(subset=[y]).copy()
                        split = "split_full" if pop == "full" else "split_nonempty"
                        sets = {k: PLAN_SETS[k] for k in (a, b)}
                    else:
                        fr = c[c.checkpoint == cp].dropna(subset=[y]).copy()
                        split = "split_nonempty"
                        sets = {k: IN_SETS[k] for k in (a, b)}
                    fr[y] = fr[y].astype(int)
                    te, s = scores(fr, y, PRIMARY_MODEL, sets, "time", split)
                    d, lo, hi = cluster_diff(te, y, s[a], s[b], rng)
                    return {"h": h, "outcome": o, "checkpoint": cp, "delta": d, "lo": lo, "hi": hi, "p": cluster_diff.last_p}
                rows.append(unit(f"fine_{h}_{o}_{cp}", work))
                print(h, o, cp, flush=True)
    d = pd.DataFrame(rows)
    p = d.p
    order = p.sort_values().index
    m, run_max, adj = len(p), 0.0, pd.Series(index=p.index, dtype=float)
    for k, i in enumerate(order):
        run_max = max(run_max, min(1.0, (m - k) * p[i]))
        adj[i] = run_max
    d["p_holm"] = adj
    save(d, "hypotheses_fine.csv")
    print(d.round(4).to_string())


if __name__ == "__main__":
    main()
