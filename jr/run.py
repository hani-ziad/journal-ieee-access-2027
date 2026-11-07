"""All experiments of PLAN.md, in one runner. Every result is written, whatever it shows.

Primary analysis (PLAN.md Section 6): gradient boosting on the per-project time split,
one paired difference per outcome and comparison, with both a project-cluster bootstrap
interval and a sprint-level bootstrap interval. Everything else is secondary and
descriptive. The secondary tables carry no correction for multiple comparisons and are
read as patterns, not tests.

    python -m jr.run planning     planning-time models, all outcomes, three protocols
    python -m jr.run insprint     25% and 50% checkpoints: ours vs Worki vs Choetkiertikul
    python -m jr.run external     trained on TAWOS, tested on MariaDB and MongoDB projects
    python -m jr.run all

Reads the frames written by `python -m jr.data`. Results go to results/<cohort>/.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

import jr
from jr.data import CHOET_COLS, NEW_FEATURES, OUTCOMES, SENSITIVITY, build, planning_frame, use_raw
from jr.worki_features import R_COLS
from phase2.data import STRICT_NUMERIC, population
from phase2.models import feature_columns, make_classifier
from phase3.data import PROGRESS_FEATURES

N_BOOT = 2000
MODELS = {"logreg": "Logistic regression", "random_forest": "Random forest", "gradient_boosting": "Gradient boosting"}
SCOPE = ["committed_issue_count", "committed_story_points", "sprint_length_days"]
SP_COLS = {"committed_story_points", "hist_avg_delivered_sp_3", "unestimated_share", "reestimated_share"}

PLAN_SETS = {  # name: (numeric columns, use project one-hot on the time split)
    "scope": (SCOPE, False),
    "strict": (list(STRICT_NUMERIC), True),
    "strict+new": (list(STRICT_NUMERIC) + NEW_FEATURES, True),
}
OURS = list(dict.fromkeys(list(STRICT_NUMERIC) + NEW_FEATURES + PROGRESS_FEATURES))
IN_SETS = {
    "scope": (SCOPE, False),
    "choet": (CHOET_COLS, False),
    "worki": (R_COLS, False),
    "ours": (OURS, True),
    "ours+worki": (OURS + R_COLS, True),
}
PLAN_DIFFS = [("strict+new", "strict"), ("strict+new", "scope"), ("strict", "scope")]
IN_DIFFS = [("ours", "worki"), ("ours", "choet"), ("ours+worki", "ours"), ("worki", "scope"), ("choet", "scope")]
IN_OUTCOMES = ["spillover", "late_closure", "serious_spillover", "seriously_late"]
PRIMARY_MODEL, PRIMARY_PROTOCOL = "gradient_boosting", "time"


# ---------------------------------------------------------------- helpers
def fit_predict(model, numeric, proj, tr, te, y):
    est = make_classifier(model, numeric, proj)
    cols = feature_columns(numeric, proj)
    est.fit(tr[cols], tr[y].astype(int))
    return est.predict_proba(te[cols])[:, 1]


def youden(y, s):
    best, thr = -1.0, 0.5
    for t in np.unique(s):
        p = s >= t
        j = (p & (y == 1)).sum() / max((y == 1).sum(), 1) + (~p & (y == 0)).sum() / max((y == 0).sum(), 1) - 1
        if j > best:
            best, thr = j, t
    return float(thr)


def decision(model, numeric, proj, tr, te, y):
    """Threshold from 5-fold out-of-fold training scores (never the test set)."""
    est = make_classifier(model, numeric, proj)
    cols = feature_columns(numeric, proj)
    ytr = tr[y].astype(int).to_numpy()
    oof = cross_val_predict(est, tr[cols], ytr, cv=StratifiedKFold(5, shuffle=True, random_state=jr.SEED),
                            method="predict_proba")[:, 1]
    thr = youden(ytr, oof)
    est.fit(tr[cols], ytr)
    s = est.predict_proba(te[cols])[:, 1]
    yt = te[y].astype(int).to_numpy()
    pred = (s >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[0, 1]).ravel()
    return {"threshold": thr, "sensitivity": tp / max(tp + fn, 1), "specificity": tn / max(tn + fp, 1),
            "f1": f1_score(yt, pred, zero_division=0)}


def safe_auc(y, s):
    y = np.asarray(y)
    return roc_auc_score(y, s) if 0 < y.sum() < len(y) else np.nan


def cluster_diff(test, y, sa, sb, rng, level="project"):
    """Paired AUC difference with a 95% bootstrap interval, resampling projects (default) or sprints."""
    if level == "project":
        projects = test["project"].unique()
        by = {p: test.index[test["project"] == p] for p in projects}
        draw = lambda: np.concatenate([by[p] for p in rng.choice(projects, len(projects), replace=True)])
    else:
        all_idx = test.index.to_numpy()
        draw = lambda: rng.choice(all_idx, len(all_idx), replace=True)
    vals = []
    for _ in range(N_BOOT):
        idx = draw()
        yy = test.loc[idx, y]
        if yy.nunique() < 2:
            continue
        vals.append(roc_auc_score(yy, sa.loc[idx]) - roc_auc_score(yy, sb.loc[idx]))
    d = safe_auc(test[y], sa) - safe_auc(test[y], sb)
    return d, float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def diff_row(base, test, y, s, a, b, rng, primary):
    """One difference record; primary comparisons also get a sprint-level interval."""
    d, lo, hi = cluster_diff(test, y, s[a], s[b], rng)
    r = {**base, "comparison": f"{a} - {b}", "delta": d, "ci_low": lo, "ci_high": hi,
         "excludes_zero": lo > 0 or hi < 0, "primary": primary}
    if primary:
        _, slo, shi = cluster_diff(test, y, s[a], s[b], rng, level="sprint")
        r.update({"sprint_ci_low": slo, "sprint_ci_high": shi})
    return r


def scores(frame, y, model, sets, protocol, split_col):
    """Out-of-sample scores of every feature set on one aligned test index."""
    out = {}
    if protocol == "time":
        tr, te = frame[frame[split_col] == "train"], frame[frame[split_col] == "test"]
        for name, (num, proj) in sets.items():
            out[name] = pd.Series(fit_predict(model, num, proj, tr, te, y), index=te.index)
        return te, out
    parts = {name: [] for name in sets}
    for p in sorted(frame["project"].unique()):
        tr, te = frame[frame["project"] != p], frame[frame["project"] == p]
        if tr[y].nunique() < 2:
            continue
        for name, (num, _) in sets.items():
            parts[name].append(pd.Series(fit_predict(model, num, False, tr, te, y), index=te.index))
    out = {k: pd.concat(v) for k, v in parts.items()}
    return frame.loc[out[next(iter(out))].index], out


def repeats(frame, y, model, sets):
    """Five time-ordered repeats: first 40..80% of each project for training, next 20% for testing."""
    rows = []
    for k, frac in enumerate((0.4, 0.5, 0.6, 0.7, 0.8), start=1):
        tr_parts, te_parts = [], []
        for _, g in frame.groupby("project"):
            g = g.sort_values(["start_date", "sprint_id"])
            a, b = int(len(g) * frac), int(len(g) * min(frac + 0.2, 1.0))
            tr_parts.append(g.iloc[:a]); te_parts.append(g.iloc[a:b])
        tr, te = pd.concat(tr_parts), pd.concat(te_parts)
        if tr[y].nunique() < 2 or te[y].nunique() < 2:
            continue
        for name, (num, proj) in sets.items():
            rows.append({"repeat": k, "train_fraction": frac, "features": name, "n_test": len(te),
                         "auc": safe_auc(te[y], fit_predict(model, num, proj, tr, te, y))})
    return rows


def save(df: pd.DataFrame, name: str):
    jr.RESULTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(jr.RESULTS / name, index=False)


# ---------------------------------------------------------------- planning
def run_planning():
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    rng = np.random.default_rng(jr.SEED)
    aucs, diffs, reps, dec = [], [], [], []
    for oname, (pop, y) in {**OUTCOMES, **SENSITIVITY}.items():
        fr = population(f, pop).dropna(subset=[y]).copy()
        fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"
        main = oname in OUTCOMES
        for model, mname in MODELS.items():
            for protocol in ("time", "lopo"):
                te, s = scores(fr, y, model, PLAN_SETS, protocol, split)
                for name in PLAN_SETS:
                    aucs.append({"outcome": oname, "protocol": protocol, "model": mname, "features": name,
                                 "n": len(te), "positives": int(te[y].sum()), "auc": safe_auc(te[y], s[name])})
                primary = main and model == PRIMARY_MODEL and protocol == PRIMARY_PROTOCOL
                base = {"outcome": oname, "protocol": protocol, "model": mname}
                for a, b in PLAN_DIFFS:
                    diffs.append(diff_row(base, te, y, s, a, b, rng, primary))
                if primary and pop == "nonempty":
                    # provenance check: the same comparison on sprints whose committed story points
                    # all come from recorded history (no static fallback)
                    keep = te["sp_fallback_share"] == 0
                    if keep.sum() >= 30 and te.loc[keep, y].nunique() == 2:
                        tk = te[keep]
                        sk = {k: v.loc[tk.index] for k, v in s.items()}
                        for a, b in PLAN_DIFFS:
                            diffs.append(diff_row({**base, "protocol": "time, no SP fallback"}, tk, y, sk, a, b, rng, False))
                        for name in PLAN_SETS:
                            aucs.append({"outcome": oname, "protocol": "time, no SP fallback", "model": mname,
                                         "features": name, "n": len(tk), "positives": int(tk[y].sum()),
                                         "auc": safe_auc(tk[y], sk[name])})
            if main:
                for r in repeats(fr, y, model, PLAN_SETS):
                    reps.append({"outcome": oname, "model": mname, **r})
                tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
                for name, (num, proj) in PLAN_SETS.items():
                    dec.append({"outcome": oname, "model": mname, "features": name,
                                **decision(model, num, proj, tr, te, y)})
            print("planning", oname, mname, "done", flush=True)
    save(pd.DataFrame(aucs), "planning_auc.csv")
    save(pd.DataFrame(diffs), "planning_differences.csv")
    r = pd.DataFrame(reps)
    save(r, "planning_repeats.csv")
    save(r.groupby(["outcome", "model", "features"]).auc.agg(["mean", "std", "count"]).reset_index(),
         "planning_repeats_summary.csv")
    save(pd.DataFrame(dec), "planning_decision.csv")


# ---------------------------------------------------------------- in-sprint
def run_insprint():
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    rng = np.random.default_rng(jr.SEED + 1)
    aucs, diffs = [], []
    for oname in IN_OUTCOMES:
        y = OUTCOMES[oname][1]
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y]).copy()
            fr[y] = fr[y].astype(int)
            for model, mname in MODELS.items():
                for protocol in ("time", "lopo"):
                    te, s = scores(fr, y, model, IN_SETS, protocol, "split_nonempty")
                    for name in IN_SETS:
                        aucs.append({"outcome": oname, "checkpoint": cp, "protocol": protocol, "model": mname,
                                     "features": name, "n": len(te), "positives": int(te[y].sum()),
                                     "auc": safe_auc(te[y], s[name])})
                    primary = model == PRIMARY_MODEL and protocol == PRIMARY_PROTOCOL
                    base = {"outcome": oname, "checkpoint": cp, "protocol": protocol, "model": mname}
                    for a, b in IN_DIFFS:
                        diffs.append(diff_row(base, te, y, s, a, b, rng, primary))
                print("insprint", oname, cp, mname, "done", flush=True)
    save(pd.DataFrame(aucs), "insprint_auc.csv")
    save(pd.DataFrame(diffs), "insprint_differences.csv")


# ---------------------------------------------------------------- external
def run_external():
    """Train on all TAWOS sprints of the cohort, test on each outside project (no project feature,
    no story-point features). Per project AUC; a project counts only with 5+ sprints in each class."""
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    ext = []
    for inst in ("mariadb", "mongodb"):
        raw = jr.EXTERNAL_RAW / inst
        e, _, _ = planning_frame(raw)
        e["instance"] = inst
        ext.append(e)
    use_raw(jr.RAW)
    ext = pd.concat(ext, ignore_index=True)
    sets = {k: ([c for c in num if c not in SP_COLS], False) for k, (num, _) in PLAN_SETS.items()}
    rows = []
    for oname, (pop, y) in OUTCOMES.items():
        tr = population(f, pop).dropna(subset=[y])
        te_all = population(ext, pop).dropna(subset=[y])
        for model, mname in MODELS.items():
            for name, (num, _) in sets.items():
                est = make_classifier(model, num, False)
                cols = feature_columns(num, False)
                est.fit(tr[cols], tr[y].astype(int))
                for proj, te in te_all.groupby("project"):
                    yy = te[y].astype(int)
                    npos, nneg = int(yy.sum()), int((1 - yy).sum())
                    ok = npos >= 5 and nneg >= 5
                    rows.append({"outcome": oname, "model": mname, "features": name,
                                 "instance": te["instance"].iloc[0], "project": proj, "n": len(te),
                                 "positives": npos, "interpretable": ok,
                                 "auc": safe_auc(yy, est.predict_proba(te[cols])[:, 1]) if ok else np.nan})
        print("external", oname, "done", flush=True)
    r = pd.DataFrame(rows)
    save(r, "external_per_project.csv")
    ok = r[r.interpretable]
    save(ok.groupby(["outcome", "model", "features"]).auc.agg(["mean", "std", "count"]).reset_index(),
         "external_summary.csv")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if not (jr.DATA / "planning_frame.csv").exists():
        build()
    if what in ("planning", "all"):
        run_planning()
    if what in ("insprint", "all"):
        run_insprint()
    if what in ("external", "all"):
        run_external()
    (jr.RESULTS / "run_info.json").write_text(json.dumps(
        {"cohort": jr.COHORT, "raw": str(jr.RAW), "seed": jr.SEED, "bootstrap": N_BOOT}, indent=1))
