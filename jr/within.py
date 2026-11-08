"""Within-project ROC-AUC: how well each feature set ranks the sprints of one project against each other.

    python -m jr.within        writes results/<cohort>/within_project.csv and within_differences.csv

Added after the full run (8 Nov 2026, fifth review). Every AUC elsewhere in the paper is pooled over all
test sprints of all projects, so it rewards a model for telling a high-spillover project from a
low-spillover one as well as for ranking a team's own sprints. A team using a warning tool only ever
sees its own sprints. Here AUC is computed only over positive-negative pairs from the same project
(the pair-weighted mean of per-project AUCs), on the same primary models, split and test sprints as
jr.run. Differences get a 95% interval from 2,000 project-level bootstrap resamples, as in jr.run.
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import jr
from jr.data import OUTCOMES
from jr.run import IN_DIFFS, IN_OUTCOMES, IN_SETS, N_BOOT, PLAN_DIFFS, PLAN_SETS, safe_auc, save, scores
from phase2.data import population

GB = "gradient_boosting"
MEDIAN = {"serious_spillover_median": ("nonempty", "label_serious_spillover_median")}


def per_project(te, y, s):
    """Per-project AUC and number of positive-negative pairs (projects with both classes only)."""
    rows = {}
    for p, g in te.groupby("project"):
        yy = g[y].astype(int).to_numpy()
        npos, nneg = int(yy.sum()), int((1 - yy).sum())
        if npos and nneg:
            rows[p] = (roc_auc_score(yy, s.loc[g.index].to_numpy()), npos * nneg)
    return rows


def within(rows):
    w = np.array([v[1] for v in rows.values()], float)
    a = np.array([v[0] for v in rows.values()])
    return float((a * w).sum() / w.sum())


def boot_diff(ra, rb, name):
    projects = sorted(ra)
    a = np.array([ra[p][0] for p in projects]); b = np.array([rb[p][0] for p in projects])
    w = np.array([ra[p][1] for p in projects], float)
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    vals = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(projects), len(projects))
        vals.append(((a[i] - b[i]) * w[i]).sum() / w[i].sum())
    d = float(((a - b) * w).sum() / w.sum())
    return d, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), len(projects)


def run(stage, fr, y, sets, diffs, split, oname, cp=None):
    te, s = scores(fr, y, GB, sets, "time", split)
    pp = {k: per_project(te, y, v) for k, v in s.items()}
    aucs = [{"stage": stage, "outcome": oname, "checkpoint": cp, "features": k, "n": len(te),
             "pooled": safe_auc(te[y], s[k]), "within": within(pp[k]), "projects": len(pp[k])} for k in sets]
    ds = []
    for a, b in diffs:
        d, lo, hi, k = boot_diff(pp[a], pp[b], f"within_{stage}_{oname}_{cp}_{a}_{b}")
        pooled = safe_auc(te[y], s[a]) - safe_auc(te[y], s[b])
        ds.append({"stage": stage, "outcome": oname, "checkpoint": cp, "comparison": f"{a} - {b}",
                   "pooled_delta": pooled, "delta": d, "ci_low": lo, "ci_high": hi, "projects": k})
    return aucs, ds


def main():
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    aucs, ds = [], []
    for oname, (pop, y) in {**OUTCOMES, **MEDIAN}.items():
        fr = population(f, pop).dropna(subset=[y]).copy()
        fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"
        a, d = run("planning", fr, y, PLAN_SETS, PLAN_DIFFS, split, oname)
        aucs += a; ds += d
        print("within planning", oname, "done", flush=True)
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    for oname in IN_OUTCOMES:
        y = OUTCOMES[oname][1]
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y]).copy()
            fr[y] = fr[y].astype(int)
            a, d = run("in-sprint", fr, y, IN_SETS, IN_DIFFS, "split_nonempty", oname, cp)
            aucs += a; ds += d
            print("within in-sprint", oname, cp, "done", flush=True)
    save(pd.DataFrame(aucs), "within_project.csv")
    save(pd.DataFrame(ds), "within_differences.csv")


if __name__ == "__main__":
    main()
