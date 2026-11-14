"""Independent replication on a second Jira source (Red Hat), added after the full run (14 Nov 2026).

The 19-project "held-out subset" is part of the TAWOS cohort, so it is not an independent replication.
This module reruns the primary analysis (gradient boosting, per-project time split, project-cluster
bootstrap) on a cohort built from another organisation's public Jira, trained and tested on that cohort
only, and lines the 22 hypothesis tests up against the TAWOS ones.

    JR_TAWOS_DIR=data/raw/redhat JR_EXCLUDE_UNRECORDED=1 python -m jr.data        frames for the new cohort
    JR_TAWOS_DIR=data/raw/redhat JR_EXCLUDE_UNRECORDED=1 python -m jr.replicate   results/redhat_clean/replicate_*.csv
    JR_TAWOS_DIR=data/raw/redhat JR_EXCLUDE_UNRECORDED=1 python -m jr.within      within-project scores there too
    JR_TAWOS_DIR=data/raw/tawos_all JR_EXCLUDE_UNRECORDED=1 python -m jr.replicate transfer
                                                         trained on TAWOS, tested on the new cohort

Which projects were pulled, and why, is fixed in data_export/redhat/SELECTION.md before any outcome was
computed. Nothing in this module chooses projects.
"""
from __future__ import annotations

import sys
import zlib

import numpy as np
import pandas as pd

import jr
from jr.data import OUTCOMES
from jr.run import (IN_DIFFS, IN_OUTCOMES, IN_SETS, PLAN_DIFFS, PLAN_SETS, PRIMARY_MODEL, diff_row, fit_predict,
                    safe_auc, save, scores, unit)
from phase2.data import population

NEW = "redhat_clean"


def main():
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    aucs, diffs = [], []
    for oname, (pop, y) in OUTCOMES.items():
        fr = population(f, pop).dropna(subset=[y]).copy()
        fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"

        def work(rng):
            ua, ud = [], []
            te, s = scores(fr, y, PRIMARY_MODEL, PLAN_SETS, "time", split)
            for name in PLAN_SETS:
                ua.append({"stage": "planning", "outcome": oname, "checkpoint": np.nan, "features": name,
                           "n": len(te), "projects": te.project.nunique(), "positives": int(te[y].sum()),
                           "auc": safe_auc(te[y], s[name])})
            for a, b in PLAN_DIFFS:
                ud.append(diff_row({"stage": "planning", "outcome": oname, "checkpoint": np.nan}, te, y, s, a, b, rng, True))
            return ua, ud

        ua, ud = unit(f"replicate_planning_{oname}", work)
        aucs += ua; diffs += ud
        print("replicate planning", oname, flush=True)
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    for oname in IN_OUTCOMES:
        y = OUTCOMES[oname][1]
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y]).copy()
            fr[y] = fr[y].astype(int)

            def work(rng):
                ua, ud = [], []
                te, s = scores(fr, y, PRIMARY_MODEL, IN_SETS, "time", "split_nonempty")
                for name in IN_SETS:
                    ua.append({"stage": "in-sprint", "outcome": oname, "checkpoint": cp, "features": name,
                               "n": len(te), "projects": te.project.nunique(), "positives": int(te[y].sum()),
                               "auc": safe_auc(te[y], s[name])})
                for a, b in IN_DIFFS:
                    ud.append(diff_row({"stage": "in-sprint", "outcome": oname, "checkpoint": cp}, te, y, s, a, b, rng, True))
                return ua, ud

            ua, ud = unit(f"replicate_insprint_{oname}_{cp}", work)
            aucs += ua; diffs += ud
            print("replicate insprint", oname, cp, flush=True)
    save(pd.DataFrame(aucs), "replicate_auc.csv")
    save(pd.DataFrame(diffs), "replicate_differences.csv")


def transfer():
    """Trained on the whole TAWOS cohort, scored on the new cohort's sprints (all of them).

    Same rules as the MariaDB/MongoDB outside test: no project one-hot (the new projects are unseen).
    Unlike that test, story points stay in, because the new source records them. AUC is reported
    pooled and as the mean of per-project AUCs (projects with at least five sprints in each class)."""
    tw = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    rh = pd.read_csv(jr.ROOT / "data" / NEW / "planning_frame.csv", parse_dates=["start_date"])
    rows, per_rows, diff_rows = [], [], []
    for oname, (pop, y) in OUTCOMES.items():
        tr = population(tw, pop).dropna(subset=[y]).copy(); tr[y] = tr[y].astype(int)
        te = population(rh, pop).dropna(subset=[y]).copy(); te[y] = te[y].astype(int)
        per_set = {}
        for name, (num, _proj) in PLAN_SETS.items():
            s = pd.Series(fit_predict(PRIMARY_MODEL, num, False, tr, te, y), index=te.index)
            per = {}
            for p, g in te.groupby("project"):
                if g[y].sum() >= 5 and (1 - g[y]).sum() >= 5:
                    per[p] = safe_auc(g[y], s.loc[g.index])
                    per_rows.append({"outcome": oname, "features": name, "project": p, "n": len(g),
                                     "positives": int(g[y].sum()), "auc": per[p]})
            per_set[name] = per
            v = list(per.values())
            rows.append({"outcome": oname, "features": name, "n": len(te), "positives": int(te[y].sum()),
                         "pooled": safe_auc(te[y], s), "per_project_mean": float(np.mean(v)) if v else np.nan,
                         "per_project_sd": float(np.std(v, ddof=1)) if len(v) > 1 else np.nan, "k": len(v)})
        # paired differences of per-project AUC, 95% interval from 2,000 project resamples
        for a, b in PLAN_DIFFS:
            ps = sorted(set(per_set[a]) & set(per_set[b]))
            d = np.array([per_set[a][p] - per_set[b][p] for p in ps])
            rng = np.random.default_rng(zlib.crc32(f"transfer_{oname}_{a}_{b}".encode()))
            bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)] if len(d) else [np.nan]
            diff_rows.append({"outcome": oname, "comparison": f"{a} - {b}", "delta": float(d.mean()) if len(d) else np.nan,
                              "ci_low": float(np.percentile(bs, 2.5)), "ci_high": float(np.percentile(bs, 97.5)),
                              "projects": len(ps)})
        print("transfer", oname, flush=True)
    out = jr.ROOT / "results" / NEW
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "transfer_from_tawos.csv", index=False)
    pd.DataFrame(per_rows).to_csv(out / "transfer_per_project.csv", index=False)
    pd.DataFrame(diff_rows).to_csv(out / "transfer_differences.csv", index=False)


if __name__ == "__main__":
    transfer() if (len(sys.argv) > 1 and sys.argv[1] == "transfer") else main()
