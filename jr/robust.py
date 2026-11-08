"""Robustness and decision analyses added after review (PLAN.md deviations log).

    python -m jr.robust        writes results/<cohort>/robust_*.csv

1. Tuned gradient boosting: a small grid chosen on a time-ordered validation slice of the training data
   (the last 20% of each project's training sprints), then refit on all training sprints.
2. A single calendar cut instead of the per-project split: train on sprints whose outcome was known
   before the cut, test on sprints that start after it.
3. Warning budgets: if a team can act on k% of its sprints, how many of the flagged sprints are real
   problems, per feature set.
4. Net benefit of a warning at threshold p* (Section III, warnings as decisions), at planning time and
   at 25% and 50% of the sprint, on the same sprints, with the break-even ratio e(c)/e(0).
5. Reliability bins for the figure.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

import jr
from jr.data import OUTCOMES
from jr.run import IN_SETS, PLAN_SETS, PRIMARY_MODEL, diff_row, fit_predict, safe_auc, save, unit
from phase2.data import population
from phase2.models import feature_columns, make_classifier

GRID = list(itertools.product((2, 3, 5), (0.03, 0.1), (100, 300), (10, 40)))
H_COMPARISONS = [("strict+new", "strict"), ("strict+new", "scope")]


def tuned_predict(num, proj, tr, te, y):
    tr = tr.sort_values(["project", "start_date", "sprint_id"])
    parts_fit, parts_val = [], []
    for _, g in tr.groupby("project"):
        cut = max(1, int(len(g) * 0.8))
        parts_fit.append(g.iloc[:cut]); parts_val.append(g.iloc[cut:])
    fit, val = pd.concat(parts_fit), pd.concat(parts_val)
    cols = feature_columns(num, proj)
    best, best_auc = None, -1
    for d, lr, it, leaf in GRID:
        est = make_classifier(PRIMARY_MODEL, num, proj).set_params(
            model__max_depth=d, model__learning_rate=lr, model__max_iter=it, model__min_samples_leaf=leaf)
        if fit[y].nunique() < 2 or val[y].nunique() < 2:
            continue
        est.fit(fit[cols], fit[y].astype(int))
        a = safe_auc(val[y].astype(int), est.predict_proba(val[cols])[:, 1])
        if a > best_auc:
            best, best_auc = (d, lr, it, leaf), a
    d, lr, it, leaf = best
    est = make_classifier(PRIMARY_MODEL, num, proj).set_params(
        model__max_depth=d, model__learning_rate=lr, model__max_iter=it, model__min_samples_leaf=leaf)
    est.fit(tr[cols], tr[y].astype(int))
    return est.predict_proba(te[cols])[:, 1], best


def calendar_split(fr):
    cut = fr["start_date"].quantile(0.7)
    known = fr["start_date"] + pd.to_timedelta(fr["sprint_length_days"] + fr["late_days"].clip(lower=0), unit="D")
    return fr[known <= cut], fr[fr["start_date"] >= cut], cut


def planning_robust(f):
    aucs, diffs = [], []
    for oname, (pop, y) in OUTCOMES.items():
        fr = population(f, pop).dropna(subset=[y]).copy()
        fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"

        def work(rng):
            ua, ud = [], []
            tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
            s = {}
            for name, (num, proj) in PLAN_SETS.items():
                p, best = tuned_predict(num, proj, tr, te, y)
                s[name] = pd.Series(p, index=te.index)
                ua.append({"protocol": "time, tuned", "outcome": oname, "features": name, "n": len(te),
                           "auc": safe_auc(te[y], p), "best": str(best)})
            ud += [diff_row({"protocol": "time, tuned", "outcome": oname}, te, y, s, a, b, rng, True) for a, b in H_COMPARISONS]
            tr2, te2, cut = calendar_split(fr)
            s2 = {name: pd.Series(fit_predict(PRIMARY_MODEL, num, proj, tr2, te2, y), index=te2.index)
                  for name, (num, proj) in PLAN_SETS.items()}
            for name in PLAN_SETS:
                ua.append({"protocol": "calendar cut", "outcome": oname, "features": name, "n": len(te2),
                           "auc": safe_auc(te2[y], s2[name]), "best": str(cut.date()),
                           "projects": te2.project.nunique()})
            ud += [diff_row({"protocol": "calendar cut", "outcome": oname}, te2, y, s2, a, b, rng, True) for a, b in H_COMPARISONS]
            return ua, ud

        ua, ud = unit(f"robust_planning_{oname}", work)
        aucs += ua; diffs += ud
        print("robust planning", oname, flush=True)
    save(pd.DataFrame(aucs), "robust_auc.csv")
    save(pd.DataFrame(diffs), "robust_differences.csv")


def budgets(f):
    rows = []
    for oname, y, pop in (("late_closure", "label_delay", "full"),
                          ("serious_spillover_median", "label_serious_spillover_median", "nonempty"),
                          ("serious_spillover", "label_serious_spillover", "nonempty")):
        fr = population(f, pop).dropna(subset=[y]).copy()
        split = "split_full" if pop == "full" else "split_nonempty"
        tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
        yy = te[y].astype(int).to_numpy()
        for name, (num, proj) in PLAN_SETS.items():
            p = fit_predict(PRIMARY_MODEL, num, proj, tr, te, y)
            order = np.argsort(-p, kind="stable")
            for k in (0.1, 0.2, 0.3):
                m = int(round(k * len(te)))
                hits = int(yy[order[:m]].sum())
                rows.append({"outcome": oname, "features": name, "budget": k, "n": len(te), "flagged": m,
                             "hits": hits, "precision": hits / m, "prevalence": yy.mean(),
                             "hits_per_100_sprints": 100 * hits / len(te)})
    save(pd.DataFrame(rows), "robust_budgets.csv")


def net_benefit(y, p, t):
    y, p = np.asarray(y), np.asarray(p)
    w = p >= t
    n = len(y)
    return (w & (y == 1)).sum() / n - t * w.sum() / n


def decisions(f):
    """Net benefit per unit e(c)F of warning at threshold p*, on sprints scored at all three stages."""
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    rows, rel = [], []
    for oname in ("serious_spillover", "late_closure"):
        y = OUTCOMES[oname][1]
        ids = None
        stage_scores = {}
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y])
            tr, te = fr[fr.split_nonempty == "train"], fr[fr.split_nonempty == "test"]
            num, proj = IN_SETS["ours"]
            stage_scores[cp] = pd.Series(fit_predict(PRIMARY_MODEL, num, proj, tr, te, y), index=te.sprint_id.values)
            ids = set(te.sprint_id) if ids is None else ids & set(te.sprint_id)
        fr = population(f, "nonempty").dropna(subset=[y])
        tr, te = fr[fr.split_nonempty == "train"], fr[fr.split_nonempty == "test"]
        num, proj = PLAN_SETS["strict+new"]
        stage_scores[0.0] = pd.Series(fit_predict(PRIMARY_MODEL, num, proj, tr, te, y), index=te.sprint_id.values)
        ids = sorted(ids & set(te.sprint_id))
        truth = fr.set_index("sprint_id").loc[ids, y].astype(int).to_numpy()
        for t in (0.3, 0.5, 0.7, 0.9):
            nb = {st: net_benefit(truth, stage_scores[st].loc[ids].to_numpy(), t) for st in (0.0, 0.25, 0.5)}
            rows.append({"outcome": oname, "p_star": t, "n": len(ids), "prevalence": truth.mean(),
                         "nb_warn_all": truth.mean() - t, "nb_planning": nb[0.0], "nb_25": nb[0.25], "nb_50": nb[0.5],
                         "breakeven_25": nb[0.0] / nb[0.25] if nb[0.25] > 0 and nb[0.0] > 0 else np.nan,
                         "breakeven_50": nb[0.0] / nb[0.5] if nb[0.5] > 0 and nb[0.0] > 0 else np.nan})
        for st in (0.0, 0.5):
            p = stage_scores[st].loc[ids].to_numpy()
            bins = np.minimum((p * 10).astype(int), 9)
            for b in np.unique(bins):
                rel.append({"outcome": oname, "stage": st, "bin": int(b), "n": int((bins == b).sum()),
                            "mean_predicted": float(p[bins == b].mean()), "observed": float(truth[bins == b].mean())})
    save(pd.DataFrame(rows), "robust_net_benefit.csv")
    save(pd.DataFrame(rel), "robust_reliability.csv")


def nothing_finished_projects(f, limit=0.5):
    ne = f[f.nonempty]
    share = ne.groupby("project").carry_ratio.apply(lambda x: (x == 1).mean())
    return sorted(share[share > limit].index)


def restricted_tests(f, drop=None, key="robust_restricted", out_name="robust_restricted.csv"):
    """Primary comparisons with the test sprints of some projects set aside (by default the projects where
    most sprints finish nothing). Models are trained as in the primary analysis; only the evaluation set changes."""
    drop = nothing_finished_projects(f) if drop is None else drop
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    rows = []

    def work(rng):
        out = []
        for oname, (pop, y) in OUTCOMES.items():
            fr = population(f, pop).dropna(subset=[y]).copy()
            fr[y] = fr[y].astype(int)
            split = "split_full" if pop == "full" else "split_nonempty"
            tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
            s = {n: pd.Series(fit_predict(PRIMARY_MODEL, num, proj, tr, te, y), index=te.index)
                 for n, (num, proj) in PLAN_SETS.items()}
            keep = ~te.project.isin(drop)
            tk, sk = te[keep], {k: v[keep] for k, v in s.items()}
            out += [diff_row({"stage": "planning", "outcome": oname, "checkpoint": np.nan}, tk, y, sk, a, b, rng, True)
                    for a, b in H_COMPARISONS]
        for oname in ("spillover", "serious_spillover", "late_closure", "seriously_late"):
            y = OUTCOMES[oname][1]
            for cp in (0.25, 0.5):
                fr = c[c.checkpoint == cp].dropna(subset=[y]).copy()
                fr[y] = fr[y].astype(int)
                tr, te = fr[fr.split_nonempty == "train"], fr[fr.split_nonempty == "test"]
                names = ("worki", "choet", "choet+ctx", "ours", "ours+worki")
                s = {n: pd.Series(fit_predict(PRIMARY_MODEL, *IN_SETS[n], tr, te, y), index=te.index) for n in names}
                keep = ~te.project.isin(drop)
                tk, sk = te[keep], {k: v[keep] for k, v in s.items()}
                out += [diff_row({"stage": "in-sprint", "outcome": oname, "checkpoint": cp}, tk, y, sk, a, b, rng, True)
                        for a, b in (("ours", "worki"), ("ours+worki", "ours"), ("ours", "choet"),
                                     ("choet+ctx", "choet"), ("ours", "choet+ctx"))]
        return out

    rows = unit(key, work)
    d = pd.DataFrame(rows)
    d["excluded_projects"] = "; ".join(drop)
    save(d, out_name)


def history_tests(f, limit=0.85):
    """Primary comparisons on the test sprints of projects where at least `limit` of the issues ever placed
    in a sprint have sprint history in the change log (jr.validate), so that sprint membership at the start
    comes from the replay rather than from the exported value."""
    cov = pd.read_csv(jr.RESULTS / "reconstruction_coverage.csv")
    drop = sorted(cov.loc[cov.in_sprint_with_history < limit, "project"])
    restricted_tests(f, drop, key="robust_history", out_name="robust_history.csv")


if __name__ == "__main__":
    import sys
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    if "history" in sys.argv:
        history_tests(f)
        print(pd.read_csv(jr.RESULTS / "robust_history.csv").round(3).to_string())
        raise SystemExit
    planning_robust(f)
    budgets(f)
    decisions(f)
    restricted_tests(f)
    for n in ("robust_auc", "robust_differences", "robust_budgets", "robust_net_benefit", "robust_restricted"):
        print(pd.read_csv(jr.RESULTS / f"{n}.csv").round(3).to_string())
