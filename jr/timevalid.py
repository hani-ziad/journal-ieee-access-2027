"""Time-valid (rolling-origin) re-evaluation of the headline comparisons (PLAN.md section 14).

The paper's time split is per project: each project's first 70% of sprints train and the last 30% test, and one
model is fitted on all training parts together. A test sprint can therefore start before a training sprint of
another project. Here the test sprints are the same, grouped by the calendar quarter they start in, and for each
quarter the model is fitted only on training-split sprints (of any project) whose outcome was known before the
quarter began (known = start + sprint length + days late, as in jr/decay.py). A quarter is scored only with at
least MIN_TRAIN such sprints and both classes. Both protocols are scored on the same test sprints.

    JR_TAWOS_DIR=data/raw/tawos_all JR_EXCLUDE_UNRECORDED=1 python -m jr.timevalid            TAWOS (about 10 min)
    JR_TAWOS_DIR=data/raw/redhat    JR_EXCLUDE_UNRECORDED=1 python -m jr.timevalid            Red Hat (about 15 min)
    JR_TAWOS_DIR=data/raw/tawos_all JR_EXCLUDE_UNRECORDED=1 python -m jr.timevalid transfer   TAWOS to Red Hat
    python -m jr.timevalid table                                                              paper/tables/timevalid.tex
"""
from __future__ import annotations

import sys
import zlib

import numpy as np
import pandas as pd

import jr
from jr.data import OUTCOMES
from jr.run import IN_SETS, PLAN_DIFFS, PLAN_SETS, cluster_diff, fit_predict, safe_auc
from jr.within import boot_diff, per_project, within
from phase2.data import population

GB = "gradient_boosting"
MIN_TRAIN = 150
OUT = ("spillover", "serious_spillover", "late_closure")
IN_D = [("ours", "worki"), ("ours+worki", "ours")]
ORG = {"Alloy Framework": "Appcelerator", "Appcelerator Daemon": "Appcelerator", "Appcelerator Studio": "Appcelerator",
       "Command-Line Interface": "Appcelerator", "The Titanium SDK": "Appcelerator", "Titanium Mobile Platform": "Appcelerator",
       "Apache Mesos": "Apache", "Apache Usergrid": "Apache", "Mule": "MuleSoft", "Mule APIkit": "MuleSoft",
       "Spring DataCass": "Spring", "Spring XD": "Spring", "Lsstcorp Data management": "LSST", "Moodle": "Moodle",
       "Sonatype Nexus": "Sonatype"}


def org(p):
    return ORG.get(p, p.split()[0])  # Atlassian ..., Hyperledger ..., Red Hat ...


def known(f):
    return f.start_date + pd.to_timedelta(f.sprint_length_days + f.late_days.clip(lower=0).fillna(0), unit="D")


def roll(fr, y, sets, split):
    tr_all, te_all = fr[fr[split] == "train"], fr[fr[split] == "test"]
    q = te_all.start_date.dt.to_period("Q")
    tv, kept = {k: [] for k in sets}, []
    for per in sorted(q.unique()):
        te = te_all[q == per]
        tr = tr_all[tr_all.known < per.start_time]
        if len(tr) < MIN_TRAIN or tr[y].nunique() < 2:
            continue
        kept.append(te.index)
        for k, (num, proj) in sets.items():
            tv[k].append(pd.Series(fit_predict(GB, num, proj, tr, te, y), index=te.index))
    te = te_all.loc[np.concatenate(kept)]
    tv = {k: pd.concat(v) for k, v in tv.items()}
    pap = {k: pd.Series(fit_predict(GB, num, proj, tr_all, te, y), index=te.index) for k, (num, proj) in sets.items()}
    return te, len(te_all), pap, tv


def report(stage, oname, cp, te, n_all, pap, tv, y, sets, diffs, A, D):
    for prot, s in (("paper", pap), ("time-valid", tv)):
        pp = {k: per_project(te, y, v) for k, v in s.items()}
        for k in sets:
            A.append(dict(stage=stage, outcome=oname, checkpoint=cp, protocol=prot, features=k, n=len(te), n_all=n_all,
                          pooled=safe_auc(te[y], s[k]), within=within(pp[k]), projects=len(pp[k])))
        for a, b in diffs:
            name = f"tv_{stage}_{oname}_{cp}_{prot}_{a}_{b}"
            d, lo, hi = cluster_diff(te, y, s[a], s[b], np.random.default_rng(zlib.crc32(name.encode())))
            wd, wlo, whi, k = boot_diff(pp[a], pp[b], name)
            row = dict(stage=stage, outcome=oname, checkpoint=cp, protocol=prot, comparison=f"{a} - {b}", n=len(te),
                       pooled_delta=d, p_low=lo, p_high=hi, within_delta=wd, w_low=wlo, w_high=whi, projects=k)
            if stage == "planning":  # organisation-level interval: resample organisations, not projects
                t2 = te.assign(project=te.project.map(org))
                _, olo, ohi = cluster_diff(t2, y, s[a], s[b], np.random.default_rng(zlib.crc32((name + "org").encode())))
                row.update(org_low=olo, org_high=ohi, organisations=t2.project.nunique())
            D.append(row)


def weekday(te, y, s):
    """Late closure within a project: one-bit rule (planned end on Friday, Saturday or Sunday) against the model."""
    end = te.start_date + pd.to_timedelta(te.sprint_length_days, unit="D")
    flag = end.dt.dayofweek.isin([4, 5, 6]).astype(float)
    pf, pm = per_project(te, y, flag), per_project(te, y, s)
    d, lo, hi, k = boot_diff(pm, pf, "tv_weekday")
    return dict(flag_pooled=safe_auc(te[y], flag), flag_within=within(pf), model_within=within(pm),
                model_minus_flag=d, ci_low=lo, ci_high=hi, projects=k, n=len(te))


def main():
    A, D = [], []
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    f["known"] = known(f)
    for oname in OUT:
        pop, y = OUTCOMES[oname]
        fr = population(f, pop).dropna(subset=[y]).copy(); fr[y] = fr[y].astype(int)
        te, n_all, pap, tv = roll(fr, y, PLAN_SETS, "split_full" if pop == "full" else "split_nonempty")
        report("planning", oname, np.nan, te, n_all, pap, tv, y, PLAN_SETS, PLAN_DIFFS, A, D)
        if oname == "late_closure":
            pd.DataFrame([weekday(te, y, tv["strict+new"])]).to_csv(jr.RESULTS / "timevalid_weekday.csv", index=False)
        print("planning", oname, len(te), n_all, flush=True)
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"])
    c["known"] = known(c)
    sets = {k: IN_SETS[k] for k in ("worki", "ours", "ours+worki")}
    for oname in OUT:
        y = OUTCOMES[oname][1]
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y]).copy(); fr[y] = fr[y].astype(int)
            te, n_all, pap, tv = roll(fr, y, sets, "split_nonempty")
            report("insprint", oname, cp, te, n_all, pap, tv, y, sets, IN_D, A, D)
            print("insprint", oname, cp, len(te), n_all, flush=True)
    pd.DataFrame(A).to_csv(jr.RESULTS / "timevalid_auc.csv", index=False)
    pd.DataFrame(D).to_csv(jr.RESULTS / "timevalid_diff.csv", index=False)


def transfer():
    """TAWOS to Red Hat as in jr.replicate.transfer, but scoring only Red Hat sprints that start after the
    outcome of the last TAWOS sprint was known."""
    tw = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    rh = pd.read_csv(jr.ROOT / "data" / "redhat_clean" / "planning_frame.csv", parse_dates=["start_date"])
    cut = known(tw).max()
    rows = []
    for oname in OUT:
        pop, y = OUTCOMES[oname]
        tr = population(tw, pop).dropna(subset=[y]).copy(); tr[y] = tr[y].astype(int)
        al = population(rh, pop).dropna(subset=[y]).copy(); al[y] = al[y].astype(int)
        te = al[al.start_date > cut]
        per = {}
        for name, (num, _p) in PLAN_SETS.items():
            s = pd.Series(fit_predict(GB, num, False, tr, te, y), index=te.index)
            per[name] = {p: safe_auc(g[y], s.loc[g.index]) for p, g in te.groupby("project")
                         if g[y].sum() >= 5 and (1 - g[y]).sum() >= 5}
        for a, b in PLAN_DIFFS:
            ps = sorted(set(per[a]) & set(per[b]))
            d = np.array([per[a][p] - per[b][p] for p in ps])
            rng = np.random.default_rng(zlib.crc32(f"tv_transfer_{oname}_{a}_{b}".encode()))
            bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(2000)]
            rows.append(dict(outcome=oname, comparison=f"{a} - {b}", delta=float(d.mean()), ci_low=float(np.percentile(bs, 2.5)),
                             ci_high=float(np.percentile(bs, 97.5)), projects=len(ps), n=len(te), n_all=len(al), cutoff=str(cut.date())))
        print("transfer", oname, len(te), len(al), flush=True)
    pd.DataFrame(rows).to_csv(jr.ROOT / "results" / "redhat_clean" / "timevalid_transfer.csv", index=False)


def table():
    from jr.tables import ci, d3
    R = jr.ROOT / "results"
    d = {s: pd.read_csv(R / c / "timevalid_diff.csv") for s, c in (("T", "tawos_all_clean"), ("R", "redhat_clean"))}

    def cell(src, stage, o, comp, cp, col):
        q = d[src][(d[src].protocol == "time-valid") & (d[src].stage == stage) & (d[src].outcome == o) & (d[src].comparison == comp)]
        if cp is not None:
            q = q[q.checkpoint == cp]
        r = q.iloc[0]
        lo, hi = ("p_low", "p_high") if col == "pooled_delta" else ("w_low", "w_high")
        return f"{d3(r[col])} {ci(r[lo], r[hi])}"

    spec = [("New features", "Spillover", "planning", "spillover", "strict+new - strict", None),
            ("", "Serious spillover", "planning", "serious_spillover", "strict+new - strict", None),
            ("", "Late closure", "planning", "late_closure", "strict+new - strict", None),
            ("History alone", "Serious spillover", "planning", "serious_spillover", "strict - scope", None),
            ("Progress over burndown", "Spillover, 50\\%", "insprint", "spillover", "ours - worki", 0.5),
            ("", "Serious spillover, 50\\%", "insprint", "serious_spillover", "ours - worki", 0.5),
            ("Burndown added", "Spillover, 50\\%", "insprint", "spillover", "ours+worki - ours", 0.5),
            ("", "Serious spillover, 50\\%", "insprint", "serious_spillover", "ours+worki - ours", 0.5)]
    lines = [f"{a} & {b} & " + " & ".join(cell(s, st, o, cmp_, cp, col) for s in "TR" for col in ("pooled_delta", "within_delta")) + r" \\"
             for a, b, st, o, cmp_, cp in spec]
    (jr.ROOT / "paper" / "tables" / "timevalid.tex").write_text("\n".join(lines) + "\n")
    # macros for the text (paper/tables/tvnums.tex)
    m = {}

    def row(src, prot, stage, o, comp, cp=None):
        q = d[src][(d[src].protocol == prot) & (d[src].stage == stage) & (d[src].outcome == o) & (d[src].comparison == comp)]
        return (q[q.checkpoint == cp] if cp is not None else q).iloc[0]

    lab = {"spillover": "Sp", "serious_spillover": "Ss", "late_closure": "Lc"}
    for src in "TR":
        for o, L in lab.items():
            for prot, P in (("time-valid", "v"), ("paper", "p")):
                r = row(src, prot, "planning", o, "strict+new - strict")
                m[f"Tv{P}d{src}New{L}"], m[f"Tv{P}c{src}New{L}"] = d3(r.pooled_delta), ci(r.p_low, r.p_high)
                m[f"Tv{P}w{src}New{L}"], m[f"Tv{P}x{src}New{L}"] = d3(r.within_delta), ci(r.w_low, r.w_high)
                if prot == "time-valid":
                    m[f"Tvo{src}New{L}"] = ci(r.org_low, r.org_high)
            r = row(src, "time-valid", "planning", o, "strict - scope")
            m[f"Tvvw{src}Str{L}"], m[f"Tvvx{src}Str{L}"] = d3(r.within_delta), ci(r.w_low, r.w_high)
        r = row(src, "time-valid", "planning", "spillover", "strict+new - strict")
        m[f"TvN{src}"], m[f"TvOrg{src}"] = f"{int(r.n):,}", str(int(r.organisations))
        a = pd.read_csv(R / ("tawos_all_clean" if src == "T" else "redhat_clean") / "timevalid_auc.csv")
        m[f"TvNall{src}"] = f"{int(a[(a.stage == 'planning') & (a.outcome == 'spillover')].n_all.iloc[0]):,}"
        w = pd.read_csv(R / ("tawos_all_clean" if src == "T" else "redhat_clean") / "timevalid_weekday.csv").iloc[0]
        m[f"TvWdFlag{src}"], m[f"TvWdModel{src}"] = f"{w.flag_within:.3f}", f"{w.model_within:.3f}"
        m[f"TvWdDiff{src}"], m[f"TvWdCi{src}"] = d3(w.model_minus_flag), ci(w.ci_low, w.ci_high)
    q = pd.concat([d[s_][(d[s_].protocol == "time-valid") & (d[s_].stage == "insprint") & d[s_].outcome.isin(["spillover", "serious_spillover"])] for s_ in "TR"])
    wk, ad = q[q.comparison == "ours - worki"], q[q.comparison == "ours+worki - ours"]
    m["TvWkMin"], m["TvWkMax"] = f"{wk.pooled_delta.min():.2f}", f"{wk.pooled_delta.max():.2f}"
    m["TvAddMax"] = f"{max(ad.pooled_delta.abs().max(), ad.within_delta.abs().max()):.3f}"
    t = pd.read_csv(R / "redhat_clean" / "timevalid_transfer.csv")
    r = t[(t.outcome == "serious_spillover") & (t.comparison == "strict+new - strict")].iloc[0]
    m["TvdZNewSs"], m["TvcZNewSs"], m["TvZN"], m["TvZAll"], m["TvZProj"] = d3(r.delta), ci(r.ci_low, r.ci_high), f"{int(r.n):,}", f"{int(r.n_all):,}", str(int(r.projects))
    (jr.ROOT / "paper" / "tables" / "tvnums.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in m.items()))
    print("\n".join(lines)); print(m)


if __name__ == "__main__":
    {"transfer": transfer, "table": table}.get(sys.argv[1] if len(sys.argv) > 1 else "", main)()
