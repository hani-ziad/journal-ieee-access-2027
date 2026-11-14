"""Model ageing (PLAN.md section 11, fixed before the run on 14 Nov 2026).

How much ranking quality does a planning-time model lose when it is k years old? For each test year Y and
age k, train on sprints whose outcome was known before 1 January of Y - k and score the sprints that start
in Y. The test sprints are the same for every age. AUC is computed inside each project and test year and
averaged with pair weights; losses are paired on project-years and bootstrapped over projects.

    JR_TAWOS_DIR=data/raw/tawos_all JR_EXCLUDE_UNRECORDED=1 python -m jr.decay     TAWOS
    JR_TAWOS_DIR=data/raw/redhat    JR_EXCLUDE_UNRECORDED=1 python -m jr.decay     Red Hat
"""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import jr
from jr.data import OUTCOMES
from jr.run import PLAN_SETS, PRIMARY_MODEL, fit_predict, save
from phase2.data import population

AGES = (0, 1, 2, 3)
OUT = ("spillover", "serious_spillover", "late_closure")
MIN_TRAIN, MIN_CLASS, N_BOOT = 200, 5, 2000
YEARS = {"tawos_all_clean": (2017, 2018, 2019), "redhat_clean": (2023, 2024, 2025, 2026)}


def units(te, y, s):
    """AUC and pair count per project (at least MIN_CLASS sprints in each class)."""
    out = {}
    for p, g in te.groupby("project"):
        yy = g[y].to_numpy()
        npos, nneg = int(yy.sum()), int((1 - yy).sum())
        if npos >= MIN_CLASS and nneg >= MIN_CLASS:
            out[p] = (roc_auc_score(yy, s.loc[g.index].to_numpy()), npos * nneg)
    return out


def wmean(a, w):
    return float((a * w).sum() / w.sum())


def boot(rows, name):
    """rows: DataFrame with project, d (difference), w (pairs). Resample projects."""
    by = {p: g for p, g in rows.groupby("project")}
    ps = sorted(by)
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    vals = []
    for _ in range(N_BOOT):
        g = pd.concat([by[ps[i]] for i in rng.integers(0, len(ps), len(ps))])
        vals.append(wmean(g.d.to_numpy(), g.w.to_numpy()))
    return wmean(rows.d.to_numpy(), rows.w.to_numpy()), float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    cohort = jr.DATA.name
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    f["known"] = f.start_date + pd.to_timedelta(f.sprint_length_days + f.late_days.clip(lower=0), unit="D")
    unit_rows, match_rows, auc_rows, diff_rows = [], [], [], []
    for oname in OUT:
        pop, y = OUTCOMES[oname]
        fr = population(f, pop).dropna(subset=[y]).copy()
        fr[y] = fr[y].astype(int)
        for Y in YEARS[cohort]:
            te = fr[fr.start_date.dt.year == Y]
            for k in AGES:
                tr = fr[fr.known < pd.Timestamp(year=Y - k, month=1, day=1)]
                if len(tr) < MIN_TRAIN or tr[y].nunique() < 2:
                    continue
                # control added after the first results (see PLAN.md): an aged model also has less training
                # data, so a fresh model is refitted on the same number of sprints, the most recent ones
                fresh = fr[fr.known < pd.Timestamp(year=Y, month=1, day=1)].sort_values("known").tail(len(tr))
                for kind, part in (("aged", tr), ("fresh, same size", fresh)):
                    if kind != "aged" and k == 0:
                        continue
                    for name, (num, _proj) in PLAN_SETS.items():
                        s = pd.Series(fit_predict(PRIMARY_MODEL, num, False, part, te, y), index=te.index)
                        for p, (a, w) in units(te, y, s).items():
                            (unit_rows if kind == "aged" else match_rows).append(
                                {"outcome": oname, "year": Y, "age": k, "features": name, "project": p,
                                 "auc": a, "w": w, "n_train": len(part)})
            print(cohort, oname, Y, flush=True)
    u, m = pd.DataFrame(unit_rows), pd.DataFrame(match_rows)
    key = ["outcome", "year", "project"]
    for (oname, name, k), g in u.groupby(["outcome", "features", "age"]):
        auc_rows.append({"outcome": oname, "features": name, "age": k, "auc": wmean(g.auc.to_numpy(), g.w.to_numpy()),
                         "project_years": len(g), "projects": g.project.nunique(), "n_train_min": int(g.n_train.min())})
    # loss of an aged model: age k minus age 0, same features, same project-years
    for oname in OUT:
        for name in PLAN_SETS:
            base = u[(u.outcome == oname) & (u.features == name) & (u.age == 0)].set_index(key)
            for k in AGES[1:]:
                old = u[(u.outcome == oname) & (u.features == name) & (u.age == k)].set_index(key)
                j = old.join(base, lsuffix="_old", rsuffix="_new", how="inner").reset_index()
                if j.empty:
                    continue
                j["d"], j["w"] = j.auc_old - j.auc_new, j.w_new
                d, lo, hi = boot(j, f"decay_{cohort}_{oname}_{name}_{k}")
                diff_rows.append({"outcome": oname, "comparison": f"{name}: age {k} - age 0", "features": name, "age": k,
                                  "delta": d, "ci_low": lo, "ci_high": hi, "project_years": len(j), "projects": j.project.nunique()})
        # the same loss against a fresh model trained on the same number of sprints
        for name in PLAN_SETS:
            for k in AGES[1:]:
                old = u[(u.outcome == oname) & (u.features == name) & (u.age == k)].set_index(key)
                new = m[(m.outcome == oname) & (m.features == name) & (m.age == k)].set_index(key)
                j = old.join(new, lsuffix="_old", rsuffix="_new", how="inner").reset_index()
                if j.empty:
                    continue
                j["d"], j["w"] = j.auc_old - j.auc_new, j.w_new
                d, lo, hi = boot(j, f"decay_{cohort}_{oname}_{name}_{k}_matched")
                diff_rows.append({"outcome": oname, "comparison": f"{name}: age {k} - fresh of the same size", "features": name + " (size-matched)",
                                  "age": k, "delta": d, "ci_low": lo, "ci_high": hi, "project_years": len(j), "projects": j.project.nunique()})
        # gain of the new features at each age
        for k in AGES:
            a = u[(u.outcome == oname) & (u.features == "strict+new") & (u.age == k)].set_index(key)
            b = u[(u.outcome == oname) & (u.features == "strict") & (u.age == k)].set_index(key)
            j = a.join(b, lsuffix="_a", rsuffix="_b", how="inner").reset_index()
            if j.empty:
                continue
            j["d"], j["w"] = j.auc_a - j.auc_b, j.w_a
            d, lo, hi = boot(j, f"decay_{cohort}_{oname}_newgain_{k}")
            diff_rows.append({"outcome": oname, "comparison": f"strict+new - strict at age {k}", "features": "new gain", "age": k,
                              "delta": d, "ci_low": lo, "ci_high": hi, "project_years": len(j), "projects": j.project.nunique()})
    save(u, "decay_units.csv")
    save(m, "decay_units_matched.csv")
    save(pd.DataFrame(auc_rows), "decay_auc.csv")
    save(pd.DataFrame(diff_rows), "decay_differences.csv")


if __name__ == "__main__":
    main()
