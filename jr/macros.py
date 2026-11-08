"""Every number in the paper's running text, written as a LaTeX macro from the result files.

    python -m jr.macros      writes paper/tables/textnums.tex

Naming (letters only, as LaTeX requires):
  d<stage><protocol><comparison><outcome>[<checkpoint>]   a difference in AUC
  c<...>                                                   its 95% project-level interval, "[lo, hi]"
  a<stage><protocol><outcome>[<checkpoint>]<set>           an AUC
stage: P planning, I in-sprint.  protocol: T time split, L leave one project out, F no story-point
fallback, C confirmation set.  outcome: Sp spillover, Ss serious spillover, Lc late closure,
Sl seriously late, Sc scope churn, Sm serious spillover (median), Sf serious spillover (50%),
St serious spillover (20%), Sh scope churn (50%), Ss7 is not used.  checkpoint: A 25%, B 50%.
comparison: New strict+new - strict, Hist strict+new - scope, Str strict - scope, Wk ours - worki,
Ch ours - choet, Add ours+worki - ours, Ctx choet+ctx - choet, Prog ours - choet+ctx, Ws worki - scope.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import jr

OUT = jr.ROOT / "paper" / "tables" / "textnums.tex"
R = jr.RESULTS
GB = "Gradient boosting"
OUTC = {"spillover": "Sp", "serious_spillover": "Ss", "late_closure": "Lc", "seriously_late": "Sl",
        "scope_churn": "Sc", "serious_spillover_median": "Sm", "serious_spillover_50": "Sf",
        "serious_spillover_20": "St", "scope_churn_50": "Sh"}
COMP = {"strict+new - strict": "New", "strict+new - scope": "Hist", "strict - scope": "Str",
        "ours - worki": "Wk", "ours - choet": "Ch", "ours+worki - ours": "Add", "choet+ctx - choet": "Ctx",
        "ours - choet+ctx": "Prog", "worki - scope": "Ws", "choet - scope": "Cs"}
PROT = {"time": "T", "lopo": "L", "time, no SP fallback": "F"}
SETS = {"scope": "Scope", "strict": "Strict", "strict+new": "New", "choet": "Choet", "choet+ctx": "Ctx",
        "worki": "Worki", "ours": "Ours", "ours+worki": "OursW"}
CP = {0.25: "A", 0.5: "B"}
M: dict[str, str] = {}


def num(x, k=3):
    x = round(float(x), k) + 0.0
    s = f"{x:.{k}f}"
    return s.replace("-", "$-$")


def put(name, val):
    assert name.isalpha(), name
    assert name not in M, name
    M[name] = val


def diff_macros(df, stage, prot_name, prot_code, checkpoint=False):
    for r in df.itertuples():
        if r.comparison not in COMP or r.outcome not in OUTC:
            continue
        cp = CP[r.checkpoint] if checkpoint else ""
        key = f"{stage}{prot_code}{COMP[r.comparison]}{OUTC[r.outcome]}{cp}"
        put("d" + key, num(r.delta))
        put("c" + key, f"[{num(r.ci_low)}, {num(r.ci_high)}]")


def main():
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    ne = f[f.nonempty]
    full = jr.ROOT / "data" / "tawos_all"
    rc = pd.read_csv(jr.DATA / "recording_check.csv")
    counts = pd.read_csv(jr.ROOT / "data_export" / "tawos_sprint_counts.csv")
    dev = set(pd.read_csv(jr.ROOT / "data" / "dev_8projects" / "planning_frame.csv").project)
    g = f.groupby("project").size()
    te_all = f[f.split_full == "test"]
    te_ne = ne[ne.split_nonempty == "test"]
    put("NProjSprints", f"{len(counts)}")
    put("NProjThirty", f"{int((counts.usable_sprints >= 30).sum())}")
    put("NProjExport", f"{int((counts.usable_sprints >= 30).sum()) - 3}")
    put("NProj", f"{f.project.nunique()}")
    put("NSprints", f"{len(f):,}")
    put("NNonempty", f"{int(f.nonempty.sum()):,}")
    put("SprintMin", f"{g.min()}"); put("SprintMax", f"{g.max()}"); put("SprintMed", f"{g.median():.0f}")
    put("DateFrom", f.start_date.min().strftime("%B %Y")); put("DateTo", f.start_date.max().strftime("%B %Y"))
    put("TestAll", f"{len(te_all):,}"); put("TestNonempty", f"{len(te_ne):,}")
    put("TestFullNonempty", f"{int(te_all.nonempty.sum()):,}")
    put("NegSp", f"{int((te_ne.label_spillover == 0).sum())}")
    put("NegSs", f"{int((te_ne.label_serious_spillover == 0).sum())}")
    put("CarryMedPct", f"{100 * ne.carry_ratio.median():.0f}")
    put("PosSs", f"{100 * ne.label_serious_spillover.mean():.0f}")
    put("PosSm", f"{100 * ne.label_serious_spillover_median.mean():.0f}")
    put("PosSp", f"{100 * ne.label_spillover.mean():.0f}")
    put("DevProj", f"{len(dev & set(f.project))}")
    put("DevSprints", f"{int(f.project.isin(dev).sum()):,}")
    put("ConfProj", f"{f.project.nunique() - len(dev & set(f.project))}")
    put("ConfSprints", f"{int((~f.project.isin(dev)).sum()):,}")
    ex = rc[rc.excluded].sort_values("share", ascending=False)
    put("NExcluded", f"{len(ex)}")
    for nm, r in zip(("UnrecA", "UnrecB", "UnrecC"), ex.itertuples()):
        put(nm, f"{100 * r.share:.0f}")
    put("UnrecOtherMax", f"{100 * rc[~rc.excluded].share.max():.1f}")
    fullf = pd.read_csv(full / "planning_frame.csv")
    fne = fullf[fullf.nonempty]
    put("FullNothingPct", f"{100 * (fne.carry_ratio == 1).mean():.0f}")
    put("FullSprints", f"{len(fullf):,}")
    put("CleanNothingPct", f"{100 * (ne.carry_ratio == 1).mean():.0f}")

    # differences
    pdf = pd.read_csv(R / "planning_differences.csv")
    pdf = pdf[pdf.model == GB]
    for prot, code in PROT.items():
        diff_macros(pdf[pdf.protocol == prot], "P", prot, code)
    idf = pd.read_csv(R / "insprint_differences.csv")
    idf = idf[idf.model == GB]
    for prot, code in (("time", "T"), ("lopo", "L")):
        diff_macros(idf[idf.protocol == prot], "I", prot, code, checkpoint=True)
    cf = pd.read_csv(R / "confirm_differences.csv")
    diff_macros(cf[cf.stage == "planning"], "P", "confirm", "C")
    diff_macros(cf[cf.stage == "in-sprint"], "I", "confirm", "C", checkpoint=True)
    ca = pd.read_csv(R / "confirm_auc.csv")
    put("ConfTestAll", f"{ca[ca.stage == 'planning'].n.max():,}")
    put("ConfTestNonempty", f"{ca[(ca.stage == 'planning') & (ca.outcome == 'spillover')].n.max():,}")

    # AUCs
    pa = pd.read_csv(R / "planning_auc.csv")
    pa = pa[pa.model == GB]
    for r in pa.itertuples():
        if r.protocol in PROT and r.outcome in OUTC:
            put(f"aP{PROT[r.protocol]}{OUTC[r.outcome]}{SETS[r.features]}", num(r.auc))
    ia = pd.read_csv(R / "insprint_auc.csv")
    ia = ia[(ia.model == GB) & (ia.protocol == "time")]
    for r in ia.itertuples():
        put(f"aIT{OUTC[r.outcome]}{CP[r.checkpoint]}{SETS[r.features]}", num(r.auc))
    c = pd.read_csv(jr.DATA / "checkpoint_frame.csv")
    put("InTestA", f"{int(((c.checkpoint == 0.25) & (c.split_nonempty == 'test')).sum())}")
    put("InTestB", f"{int(((c.checkpoint == 0.5) & (c.split_nonempty == 'test')).sum())}")
    add = idf[(idf.protocol == "time") & (idf.comparison == "ours+worki - ours")].delta.abs().max()
    put("AddMax", num(np.ceil(add * 1000) / 1000))

    # binomial
    ba = pd.read_csv(R / "binomial_auc.csv").set_index(["outcome", "model"]).auc
    bd = pd.read_csv(R / "binomial_differences.csv")
    bc = pd.read_csv(R / "binomial_calibration.csv").set_index(["outcome", "model"])
    bv = pd.read_csv(R / "binomial_variance.csv")
    for o in ("spillover", "serious_spillover"):
        k = OUTC[o]
        put(f"aBin{k}", num(ba[(o, "binomial")])); put(f"aBeta{k}", num(ba[(o, "beta-binomial")]))
        put(f"aBinGb{k}", num(ba[(o, "strict+new")]))
        put(f"sBin{k}", num(bc.loc[(o, "binomial"), "slope"], 2)); put(f"sBeta{k}", num(bc.loc[(o, "beta-binomial"), "slope"], 2))
        put(f"sGb{k}", num(bc.loc[(o, "strict+new"), "slope"], 2))
        for comp, code in (("strict+new - binomial", "GbBin"), ("binomial - scope", "BinScope"),
                           ("beta-binomial - binomial", "BetaBin")):
            r = bd[(bd.outcome == o) & (bd.comparison == comp)].iloc[0]
            put(f"d{code}{k}", num(r.delta)); put(f"c{code}{k}", f"[{num(r.ci_low)}, {num(r.ci_high)}]")
        put(f"mBetaCost{k}", num(-bd[(bd.outcome == o) & (bd.comparison == 'beta-binomial - binomial')].delta.iloc[0]))
    bcf = R / "binomial_confirm.csv"
    if bcf.exists():
        b2 = pd.read_csv(bcf)
        for o in ("spillover", "serious_spillover"):
            k = OUTC[o]
            for comp, code in (("strict+new - binomial", "GbBinC"), ("binomial - scope", "BinScopeC")):
                r = b2[(b2.outcome == o) & (b2.comparison == comp)].iloc[0]
                put(f"d{code}{k}", num(r.delta)); put(f"c{code}{k}", f"[{num(r.ci_low)}, {num(r.ci_high)}]")
    put("VarRatioSmall", f"{bv.var_observed[0] / bv.var_binomial[0]:.1f}")
    put("VarRatioLarge", f"{bv.var_observed[3] / bv.var_binomial[3]:.1f}")
    put("VarObsLarge", num(bv.var_observed[3])); put("VarBetaLarge", num(bv.var_betabinomial[3]))

    # calibration
    cal = pd.read_csv(R / "calibration.csv")
    s1 = cal[cal.features.isin(["strict+new", "ours"]) & cal.outcome.isin(["spillover", "serious_spillover"])].slope
    s2 = cal[cal.features.isin(["strict+new", "ours"]) & cal.outcome.isin(["late_closure", "seriously_late"])].slope
    put("SlopeSpMin", num(s1.min(), 2)); put("SlopeSpMax", num(s1.max(), 2))
    put("SlopeLateMin", num(s2.min(), 2)); put("SlopeLateMax", num(s2.max(), 2))

    # outside
    e = pd.read_csv(R / "external_summary.csv")
    e = e[e.model == GB].set_index(["outcome", "features"])
    for o in ("spillover", "serious_spillover", "late_closure"):
        for fs in ("scope", "strict", "strict+new"):
            put(f"e{OUTC[o]}{SETS[fs]}", num(e.loc[(o, fs), "mean"]))
        put(f"eK{OUTC[o]}", f"{int(e.loc[(o, 'scope'), 'count'])}")

    # repeats and decisions
    rep = pd.read_csv(R / "planning_repeats_summary.csv")
    rep = rep[(rep.model == GB) & (rep.features == "strict+new")].set_index("outcome")
    for o in ("spillover", "serious_spillover", "late_closure"):
        put(f"rep{OUTC[o]}", f"{num(rep.loc[o, 'mean'])} $\\pm$ {num(rep.loc[o, 'std'])}")

    # hypotheses with Holm
    h = pd.read_csv(R / "hypotheses.csv")
    put("NHyp", f"{len(h)}")
    put("NHoldRaw", f"{int((h.lo > 0).sum())}")
    put("NHoldHolm", f"{int((h.p_holm < 0.05).sum())}")
    put("NHoldConf", f"{int(((h.lo > 0) & (h.c_lo > 0)).sum())}")
    # intervals whose lower end is within 0.001 of zero: their tick depends on the bootstrap draw
    put("NBoundary", f"{int((h.lo.abs() < 0.001).sum())}")
    h3 = h[h.h == "H3"]
    put("NHThree", f"{len(h3)}"); put("NHThreeOver", f"{int((h3.delta > 0.05).sum())}")
    r3 = h3[(h3.outcome == "spillover") & (h3.checkpoint == 0.5)].iloc[0]
    put("LoChSpB", f"{r3.lo:.4f}")

    # within-project AUC (jr/within.py): only pairs of sprints from the same project
    wf = R / "within_differences.csv"
    if wf.exists():
        wd = pd.read_csv(wf)
        diff_macros(wd[wd.stage == "planning"], "P", "within", "W")
        diff_macros(wd[wd.stage == "in-sprint"], "I", "within", "W", checkpoint=True)
        wa = pd.read_csv(R / "within_project.csv")
        for r in wa[wa.stage == "planning"].itertuples():
            if r.outcome in OUTC and r.features in SETS:
                put(f"wPT{OUTC[r.outcome]}{SETS[r.features]}", num(r.within))

    # theory numbers for the cohort
    t = json.loads((R / "theory_numbers.json").read_text())
    put("QhatPct", f"{100 * t['minimal_model']['q']:.0f}")

    # robustness and decisions
    if (R / "robust_differences.csv").exists():
        rd = pd.read_csv(R / "robust_differences.csv")
        for prot, code in (("time, tuned", "U"), ("calendar cut", "K")):
            diff_macros(rd[rd.protocol == prot], "P", prot, code)
        ra = pd.read_csv(R / "robust_auc.csv")
        k = ra[ra.protocol == "calendar cut"]
        put("CutDate", pd.Timestamp(k.best.iloc[0]).strftime("%B %Y"))
        put("CutProj", f"{int(k.projects.max())}")
        rr = pd.read_csv(R / "robust_restricted.csv")
        diff_macros(rr[rr.stage == "planning"], "P", "restricted", "R")
        diff_macros(rr[rr.stage == "in-sprint"], "I", "restricted", "R", checkpoint=True)
        put("RestrictedProj", rr.excluded_projects.iloc[0].replace("; ", " and "))
        b = pd.read_csv(R / "robust_budgets.csv")
        for o in ("serious_spillover_median", "late_closure"):
            for kk, kc in ((0.1, "Ten"), (0.2, "Twenty")):
                t_ = b[(b.outcome == o) & (b.budget == kk)].set_index("features")
                for fs in ("scope", "strict+new"):
                    put(f"b{OUTC[o]}{kc}{SETS[fs]}", f"{100 * t_.loc[fs, 'precision']:.0f}")
                put(f"b{OUTC[o]}{kc}Base", f"{100 * t_.loc['scope', 'prevalence']:.0f}")
                put(f"b{OUTC[o]}{kc}Extra", f"{t_.loc['strict+new', 'hits'] - t_.loc['scope', 'hits']:.0f}")
                put(f"b{OUTC[o]}{kc}Flag", f"{int(t_.loc['scope', 'flagged'])}")
        nb = pd.read_csv(R / "robust_net_benefit.csv").set_index(["outcome", "p_star"])
        for o in ("serious_spillover", "late_closure"):
            for p_, pc in ((0.5, "Half"), (0.7, "Seven"), (0.9, "Nine"), (0.3, "Three")):
                r = nb.loc[(o, p_)]
                for col, cc in (("nb_warn_all", "All"), ("nb_planning", "Plan"), ("nb_25", "A"), ("nb_50", "B")):
                    put(f"nb{OUTC[o]}{pc}{cc}", num(r[col]))
                for col, cc in (("breakeven_25", "A"), ("breakeven_50", "B")):
                    put(f"be{OUTC[o]}{pc}{cc}", "--" if pd.isna(r[col]) else f"{r[col]:.2f}")
        put("NbN", f"{int(nb.n.iloc[0])}")

    rcf = R / "reconstruction_check.csv"
    if rcf.exists():
        rc_ = pd.read_csv(rcf).iloc[0]
        put("RecPointsAgree", f"{100 * rc_.points_agree:.1f}")
        put("RecPointsN", f"{int(rc_.points_checked):,}")
        both = int(rc_.same_sprint + rc_.different_known_sprints)
        put("RecSprintBoth", f"{both:,}")
        put("RecSprintAgree", f"{100 * rc_.same_sprint / both:.1f}")
        put("RecExportEmpty", f"{int(rc_.export_empty_log_known_sprint):,}")
        put("RecHistoryPct", f"{100 * rc_.in_sprint_with_history:.0f}")
    hf = R / "robust_history.csv"
    if hf.exists():
        hh = pd.read_csv(hf)
        diff_macros(hh[hh.stage == "planning"], "P", "history", "H")
        diff_macros(hh[hh.stage == "in-sprint"], "I", "history", "H", checkpoint=True)
        dropped = hh.excluded_projects.iloc[0].split("; ") if isinstance(hh.excluded_projects.iloc[0], str) else []
        put("HistProj", f"{f.project.nunique() - len(dropped)}")
        put("HistAddMax", num(np.ceil(hh[hh.comparison == "ours+worki - ours"].delta.abs().max() * 1000) / 1000))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in M.items()))
    print(len(M), "macros")


if __name__ == "__main__":
    main()
