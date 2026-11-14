"""Second feature round (PLAN.md section 12, fixed before the run on 14 Nov 2026).

Three further ideas on top of strict+new, both sources, same split, model and bootstrap as the paper:
  A. calendar features (planned-end and start weekday, end on Fri/Sat/Sun, sprint spans the year end);
  B. depth and haste (earlier sprints per committed issue, share added in the last day before the start);
  C. an issue-level model (resolved by the planned end?) whose summed risk is passed to the sprint model;
  D. by-product of C: which issue is left over, scored inside each test sprint.
Success rule: interval above zero pooled AND within projects, in both sources. Nothing met it.

    JR_TAWOS_DIR=data/raw/tawos_all JR_EXCLUDE_UNRECORDED=1 python -m jr.round2     TAWOS, about 4 min
    JR_TAWOS_DIR=data/raw/redhat    JR_EXCLUDE_UNRECORDED=1 python -m jr.round2     Red Hat, about 5 min

Writes data/<cohort>/issue_frame.csv (one row per sprint and committed issue) and
results/<cohort>/round2_auc.csv, round2_diff.csv, round2_issue_rank.csv.
"""
from __future__ import annotations

from bisect import bisect_right

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier as HGB
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

import jr
import jr.data as jd
from jr.data import OUTCOMES
from jr.run import PLAN_SETS, PRIMARY_MODEL, cluster_diff, safe_auc, save, scores
from jr.within import boot_diff, per_project, within
from phase2.data import population


def issue_frame():
    """One row per (sprint, committed issue) with planning-time facts. Mirrors jr.data.issue_level."""
    raw = jr.RAW
    jd.use_raw(raw)
    base = pd.read_csv(jr.DATA / "planning_frame.csv", usecols=["sprint_id", "project"])
    info = jd.p2d.load_reconstructed_sprints()[["sprint_id", "start_date", "end_date"]]
    cohort = base.merge(info, on="sprint_id", how="left")
    sprints = jd.load_sprints(raw, modeling_only=True); issues = jd.load_issues(raw); cl = jd.load_change_log(raw, required=True)
    (jira_maps, raw_maps, name_maps), events = jd._issue_events(issues, cl, sprints)
    start = {r.sprint_id: r.start_date.value for r in cohort.itertuples()}
    end = {r.sprint_id: r.end_date.value for r in cohort.itertuples()}
    ids = set(start); DAY = jd.DAY; rows = []
    for issue in issues.itertuples(index=False):
        p = issue.project
        if p not in jira_maps: continue
        jm, rm, nm = jira_maps[p], raw_maps[p], name_maps[p]
        ev = events.get(issue.raw_issue_id, [])
        sp_ev = [e for e in ev if jd._field_kind(e.field) == "sprint"]; st_ev = [e for e in ev if jd._field_kind(e.field) == "story_point"]
        sp_times = [e.change_date.value for e in sp_ev]
        sp_from = [jd._parse_change_sprint_set(e.from_value, e.from_string, jira_map=jm, name_map=nm)[0] for e in sp_ev]
        sp_to = [jd._parse_change_sprint_set(e.to_value, e.to_string, jira_map=jm, name_map=nm)[0] for e in sp_ev]
        if sp_ev:
            terminal = sp_to[-1]; cand = set(terminal)
            for a, b in zip(sp_from, sp_to): cand |= a | b
        else:
            terminal = set()
            if not pd.isna(issue.raw_sprint_id):
                key = str(int(float(issue.raw_sprint_id)))
                if key in rm: terminal = {rm[key]}
            cand = set(terminal)
        cand &= ids
        if not cand: continue
        st_times = [e.change_date.value for e in st_ev]
        static = None if pd.isna(issue.story_point) else float(issue.story_point)
        st_term = jd._story_after(st_ev[-1]) if st_ev else static
        def members(t):
            i = bisect_right(sp_times, t); return sp_from[i] if i < len(sp_times) else terminal
        def story(t):
            i = bisect_right(st_times, t); return jd._story_before(st_ev[i]) if i < len(st_times) else st_term
        created = None if pd.isna(issue.creation_date) else issue.creation_date.value
        resolved = None if pd.isna(issue.resolution_date) else issue.resolution_date.value
        for sid in cand:
            t0 = start[sid]
            if resolved is not None and resolved < t0: continue
            if not (sid in members(t0) and (created is None or created <= t0)): continue
            prior = set()
            entry = None
            for t, a, b in zip(sp_times, sp_from, sp_to):
                if t <= t0:
                    prior |= (a | b) - {sid}
                    if sid in b and sid not in a: entry = t
            sp0 = story(t0)
            rows.append({"sprint_id": sid, "issue": issue.raw_issue_id,
                         "age_days": (t0 - created) / DAY if created is not None else np.nan,
                         "n_prior": len(prior), "sp": sp0 if sp0 is not None else np.nan, "unest": int(sp0 is None),
                         "reest": int(any(e.change_date.value <= t0 and jd._story_before(e) is not None and jd._story_before(e) != jd._story_after(e) for e in st_ev)),
                         "hours_in_sprint": (t0 - entry) / DAY * 24 if entry is not None else np.nan,
                         "done": int(resolved is not None and resolved <= end[sid])})
    # sorted, written and read back, so that every later number is a function of the stored file
    pd.DataFrame(rows).sort_values(["sprint_id", "issue"]).to_csv(jr.DATA / "issue_frame.csv", index=False)
    return pd.read_csv(jr.DATA / "issue_frame.csv")


def yearend(s, e):
    for yr in range(s.year, e.year + 1):
        for a, b in ((pd.Timestamp(yr, 12, 24), pd.Timestamp(yr + 1, 1, 1)), (pd.Timestamp(yr - 1, 12, 24), pd.Timestamp(yr, 1, 1))):
            if s <= b and e >= a:
                return 1
    return 0


def main():
    tag = jr.DATA.name
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    iss = issue_frame()
    # A. calendar
    end = f.start_date + pd.to_timedelta(f.sprint_length_days, unit="D")
    f["end_dow"] = end.dt.dayofweek; f["end_fss"] = (f.end_dow >= 4).astype(int); f["start_dow"] = f.start_date.dt.dayofweek
    f["yearend"] = [yearend(s, e) for s, e in zip(f.start_date, end)]
    CAL = ["end_fss", "end_dow", "start_dow", "yearend"]
    # B. depth and haste
    g = iss.groupby("sprint_id")
    dep = pd.DataFrame({"prior_mean": g.n_prior.mean(), "prior_max": g.n_prior.max(),
                        "prior2_share": g.n_prior.apply(lambda x: (x >= 2).mean()),
                        "lastday_share": g.hours_in_sprint.apply(lambda x: (x <= 24).mean())}).reset_index()
    f = f.merge(dep, on="sprint_id", how="left"); DEP = ["prior_mean", "prior_max", "prior2_share", "lastday_share"]
    f[DEP] = f[DEP].fillna(0.0)
    ctx = f.set_index("sprint_id")[["committed_issue_count", "sprint_length_days"]]
    iss = iss.join(ctx, on="sprint_id")
    IF = ["age_days", "n_prior", "sp", "unest", "reest", "hours_in_sprint", "committed_issue_count", "sprint_length_days"]
    ISS = ["iss_any", "iss_mean", "iss_sum"]
    BASE = list(PLAN_SETS["strict+new"][0])
    rng = np.random.default_rng(20261114)
    rows, drows, seed_rows = [], [], []
    for oname in ("spillover", "serious_spillover", "late_closure"):
        pop, y = OUTCOMES[oname]
        fr = population(f, pop).dropna(subset=[y]).copy(); fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"
        trs = set(fr.loc[fr[split] == "train", "sprint_id"]); tes = set(fr.loc[fr[split] == "test", "sprint_id"])
        itr, ite = iss[iss.sprint_id.isin(trs)].copy(), iss[iss.sprint_id.isin(tes)].copy()
        # C. issue model: out-of-fold on training sprints, one fit for test sprints
        def issue_scores(seed):
            tr_ = itr.sample(frac=1.0, random_state=seed).copy(); te_ = ite.copy()
            tr_["p"] = np.nan
            for a, b in GroupKFold(5).split(tr_, groups=tr_.sprint_id):
                m = HGB(max_iter=200, learning_rate=0.05, random_state=seed).fit(tr_.iloc[a][IF], tr_.iloc[a].done)
                tr_.iloc[b, tr_.columns.get_loc("p")] = m.predict_proba(tr_.iloc[b][IF])[:, 1]
            m = HGB(max_iter=200, learning_rate=0.05, random_state=seed).fit(tr_[IF], tr_.done)
            te_["p"] = m.predict_proba(te_[IF])[:, 1]
            al = pd.concat([tr_, te_]); al["p"] = al.p.clip(1e-4, 1 - 1e-4)
            ag = al.groupby("sprint_id").p
            agg = pd.DataFrame({"iss_any": 1 - np.exp(ag.apply(lambda x: np.log(x).sum())), "iss_mean": ag.apply(lambda x: (1 - x).mean()),
                                "iss_sum": ag.apply(lambda x: (1 - x).sum())}).reset_index()
            return te_, agg

        base_fr = fr
        ite, agg = issue_scores(0)
        fr = base_fr.merge(agg, on="sprint_id", how="left"); fr[ISS] = fr[ISS].fillna(0.0)
        # added after the first run: the issue-model gain moved when the rows were merely reordered, so the
        # step is repeated with four more seeds (row order, folds, model) and the spread is reported
        for seed in (1, 2, 3, 4):
            _, ag2 = issue_scores(seed)
            f2 = base_fr.merge(ag2, on="sprint_id", how="left"); f2[ISS] = f2[ISS].fillna(0.0)
            te2, s2 = scores(f2, y, PRIMARY_MODEL, {"base": (BASE, True), "+issue model": (BASE + ISS, True)}, "time", split)
            p2 = {k: per_project(te2, y, v) for k, v in s2.items()}
            seed_rows.append({"cohort": tag, "outcome": oname, "seed": seed,
                              "pooled_d": safe_auc(te2[y], s2["+issue model"]) - safe_auc(te2[y], s2["base"]),
                              "within_d": within(p2["+issue model"]) - within(p2["base"])})
        sets = {"base": (BASE, True), "+calendar": (BASE + CAL, True), "+depth": (BASE + DEP, True),
                "+issue model": (BASE + ISS, True), "+all": (BASE + CAL + DEP + ISS, True)}
        te, s = scores(fr, y, PRIMARY_MODEL, sets, "time", split)
        s["issue model alone"] = te["iss_any"] if oname == "spillover" else te["iss_mean"]
        pp = {k: per_project(te, y, v) for k, v in s.items()}
        for k in s:
            rows.append({"cohort": tag, "outcome": oname, "set": k, "pooled": safe_auc(te[y], s[k]), "within": within(pp[k]), "n": len(te)})
            if k == "base": continue
            d, lo, hi = cluster_diff(te, y, s[k], s["base"], rng)
            wd, wlo, whi, kk = boot_diff(pp[k], pp["base"], f"r2_{tag}_{oname}_{k}")
            drows.append({"cohort": tag, "outcome": oname, "set": k, "pooled_d": d, "p_lo": lo, "p_hi": hi, "within_d": wd, "w_lo": wlo, "w_hi": whi, "projects": kk})
        if oname == "spillover":  # D. which issue is left over, inside each test sprint
            res = {"model": [], "points": [], "age": [], "prior": []}
            for sid, gg in ite.groupby("sprint_id"):
                if gg.done.nunique() < 2 or len(gg) < 5: continue
                yy = 1 - gg.done
                res["model"].append(roc_auc_score(yy, 1 - gg.p)); res["points"].append(roc_auc_score(yy, gg.sp.fillna(0)))
                res["age"].append(roc_auc_score(yy, gg.age_days.fillna(0))); res["prior"].append(roc_auc_score(yy, gg.n_prior))
            rank = pd.DataFrame([{"ranker": k, "auc": float(np.mean(v)), "sprints": len(v)} for k, v in res.items()])
        print(tag, oname, "done", flush=True)
    save(pd.DataFrame(rows), "round2_auc.csv"); save(pd.DataFrame(drows), "round2_diff.csv"); save(rank, "round2_issue_rank.csv")
    d = pd.DataFrame(drows); z = d[d.set == "+issue model"]
    seeds = pd.concat([pd.DataFrame(seed_rows), z.assign(seed=0)[["cohort", "outcome", "seed", "pooled_d", "within_d"]]])
    save(seeds.sort_values(["outcome", "seed"]), "round2_issue_seeds.csv")


if __name__ == "__main__":
    main()
