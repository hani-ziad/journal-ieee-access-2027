"""Numbers for the theory section and the calibration table, computed on the current cohort.

    python -m jr.theory_numbers        writes results/<cohort>/theory_numbers.json and calibration.csv

Everything uses the primary model (gradient boosting) and the per-project time split, except
Proposition 2, which uses the outside-project setting of `jr.run external` (trained on all
TAWOS sprints, no project feature, no story-point features).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

import jr
from jr.data import OUTCOMES, planning_frame, use_raw
from jr.run import IN_OUTCOMES, IN_SETS, PLAN_SETS, SP_COLS, fit_predict, save, youden
from phase2.data import population
from phase2.models import feature_columns, make_classifier

GB = "gradient_boosting"


def prop1(f: pd.DataFrame) -> dict:
    """Structural negatives: spillover scored on all sprints, empty ones included."""
    y = "label_spillover"
    fr = population(f, "full").dropna(subset=[y]).copy()
    fr[y] = fr[y].astype(int)
    tr, te = fr[fr.split_full == "train"], fr[fr.split_full == "test"]
    num, proj = PLAN_SETS["strict+new"]
    s = pd.Series(fit_predict(GB, num, proj, tr, te, y), index=te.index)
    yy = te[y]
    pos, neg = s[yy == 1], s[yy == 0]
    n0 = neg[~te.loc[neg.index, "nonempty"]]
    n1 = neg[te.loc[neg.index, "nonempty"]]

    def a(p, n):  # P(random positive outscores random negative), ties count half
        p, n = p.to_numpy()[:, None], n.to_numpy()[None, :]
        return float(((p > n) + 0.5 * (p == n)).mean())

    pi0 = len(n0) / len(neg)
    a0, a1 = a(pos, n0), a(pos, n1)
    return {"n_test": int(len(te)), "positives": int(len(pos)), "negatives": int(len(neg)),
            "structural_negatives": int(len(n0)), "pi0": pi0, "A0": a0, "auc_nonempty": a1,
            "auc_all": float(roc_auc_score(yy, s)), "auc_all_from_mixture": pi0 * a0 + (1 - pi0) * a1,
            "auc_all_if_A0_is_1": pi0 + (1 - pi0) * a1, "inflation_if_A0_is_1": pi0 * (1 - a1)}


def prop2(f: pd.DataFrame) -> dict:
    """A Youden threshold fitted on TAWOS, carried to the outside projects (late closure)."""
    y = "label_delay"
    tr = population(f, "full").dropna(subset=[y])
    num = [c for c in PLAN_SETS["strict+new"][0] if c not in SP_COLS]
    cols = feature_columns(num, False)
    est = make_classifier(GB, num, False)
    ytr = tr[y].astype(int).to_numpy()
    oof = cross_val_predict(est, tr[cols], ytr, cv=StratifiedKFold(5, shuffle=True, random_state=jr.SEED),
                            method="predict_proba")[:, 1]
    thr = youden(ytr, oof)
    est.fit(tr[cols], ytr)
    ext = []
    for inst in ("mariadb", "mongodb"):
        e, _, _ = planning_frame(jr.EXTERNAL_RAW / inst)
        ext.append(e)
    use_raw(jr.RAW)
    ext = population(pd.concat(ext, ignore_index=True), "full").dropna(subset=[y])
    rows = []
    for p, g in ext.groupby("project"):
        yy = g[y].astype(int).to_numpy()
        if yy.sum() < 5 or (1 - yy).sum() < 5:
            continue
        pred = est.predict_proba(g[cols])[:, 1] >= thr
        rows.append({"project": p, "n": len(g), "prevalence": yy.mean(),
                     "sensitivity": (pred & (yy == 1)).sum() / yy.sum()})
    r = pd.DataFrame(rows)
    pi_tr = float(ytr.mean())
    return {"threshold": thr, "train_prevalence": pi_tr, "implied_ratio_train": (1 - pi_tr) / pi_tr,
            "n_projects": int(len(r)), "prev_min": float(r.prevalence.min()), "prev_max": float(r.prevalence.max()),
            "ratio_at_min_prev": float((1 - r.prevalence.min()) / r.prevalence.min()),
            "ratio_at_max_prev": float((1 - r.prevalence.max()) / r.prevalence.max()),
            "sens_min": float(r.sensitivity.min()), "sens_max": float(r.sensitivity.max()),
            "spearman_prev_sens": float(spearmanr(r.prevalence, r.sensitivity)[0]),
            "per_project": r.to_dict("records")}


def minimal_model(f: pd.DataFrame) -> dict:
    ne = f[f.nonempty]
    q = 1 - float(ne.carry_ratio.median())
    return {"median_carry_ratio": 1 - q, "q": q, "p_spill_n3": 1 - q ** 3,
            "nonempty_spillover_rate": float(ne.label_spillover.mean()),
            "median_committed_issues": float(ne.committed_issue_count.median()),
            "p_spill_at_median_n": 1 - q ** float(ne.committed_issue_count.median())}


def calibration_row(y, p, **key) -> dict:
    y, p = np.asarray(y), np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    bins = np.minimum((p * 10).astype(int), 9)
    ece = sum(abs(y[bins == b].mean() - p[bins == b].mean()) * (bins == b).mean() for b in np.unique(bins))
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(logit, y)
    return {**key, "n": len(y), "prevalence": y.mean(), "mean_predicted": p.mean(),
            "brier": brier_score_loss(y, p), "brier_reference": y.mean() * (1 - y.mean()),
            "ece": ece, "slope": float(lr.coef_[0, 0]), "intercept": float(lr.intercept_[0])}


def calibration(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for oname, (pop, y) in OUTCOMES.items():
        fr = population(f, pop).dropna(subset=[y]).copy()
        split = "split_full" if pop == "full" else "split_nonempty"
        tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
        for name in ("scope", "strict+new"):
            num, proj = PLAN_SETS[name]
            rows.append(calibration_row(te[y].astype(int), fit_predict(GB, num, proj, tr, te, y),
                                        stage="planning", outcome=oname, features=name))
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    for oname in IN_OUTCOMES:
        y = OUTCOMES[oname][1]
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y])
            tr, te = fr[fr.split_nonempty == "train"], fr[fr.split_nonempty == "test"]
            for name in ("choet", "ours"):
                num, proj = IN_SETS[name]
                rows.append(calibration_row(te[y].astype(int), fit_predict(GB, num, proj, tr, te, y),
                                            stage=f"in-sprint {int(cp * 100)}%", outcome=oname, features=name))
    return pd.DataFrame(rows)


def gaps(f: pd.DataFrame) -> dict:
    """The minimal model's prediction: history beats scope by more for serious spillover."""
    a = pd.read_csv(jr.RESULTS / "planning_auc.csv")
    a = a[a.model == "Gradient boosting"]
    out = {}
    for o in ("spillover", "serious_spillover"):
        for prot in ("time", "lopo"):
            t = a[(a.outcome == o) & (a.protocol == prot)].set_index("features").auc
            out[f"{o}_{prot}_strict_minus_scope"] = float(t["strict"] - t["scope"])
            out[f"{o}_{prot}_strictnew_minus_scope"] = float(t["strict+new"] - t["scope"])
    return out


if __name__ == "__main__":
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    out = {"cohort": jr.COHORT, "prop1": prop1(f), "prop2": prop2(f), "minimal_model": minimal_model(f),
           "gaps": gaps(f)}
    (jr.RESULTS / "theory_numbers.json").write_text(json.dumps(out, indent=1, default=float))
    cal = calibration(f)
    save(cal, "calibration.csv")
    print(json.dumps({k: v for k, v in out.items() if k != "prop2"}, indent=1, default=float))
    print({k: v for k, v in out["prop2"].items() if k != "per_project"})
    print(cal.round(3).to_string())
