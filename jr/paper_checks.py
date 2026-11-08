"""Check the verbal claims of paper/main_body.tex against the result files.

    python -m jr.paper_checks        (JR_TAWOS_DIR=data/raw/tawos_all JR_EXCLUDE_UNRECORDED=1)

Plain numbers in the paper are macros written by jr/macros.py and jr/tables.py, so they cannot drift.
What remains are statements such as "holds", "about zero", "none of these intervals clears zero" or
"0.13 to 0.19". Each check names the text as it appears in the paper; a check also fails if that text
is no longer in the paper, so the checks cannot silently go stale.
"""
from __future__ import annotations

import re

import pandas as pd

import jr
from jr.data import recording_check
from jr.robust import nothing_finished_projects

TEXT = re.sub(r"\s+", " ", (jr.ROOT / "paper" / "main_body.tex").read_text())
R = jr.RESULTS
GB = "Gradient boosting"
pall = pd.read_csv(R / "planning_differences.csv")
pdf = pall[pall.model == GB]
idf = pd.read_csv(R / "insprint_differences.csv"); idf = idf[idf.model == GB]
cf = pd.read_csv(R / "confirm_differences.csv")
hyp = pd.read_csv(R / "hypotheses.csv")
fails, n = [], 0


def check(text, ok):
    global n
    n += 1
    found = text in TEXT
    good = bool(ok) and found
    print(("PASS " if good else "FAIL ") + text + ("" if found else "  [text not in paper]"))
    if not good:
        fails.append(text)


def P(o, comp, prot="time", col="delta", model=GB):
    q = pall[(pall.outcome == o) & (pall.comparison == comp) & (pall.protocol == prot) & (pall.model == model)]
    return float(q[col].iloc[0])


def I(o, comp, cp, prot="time", col="delta"):
    return float(idf[(idf.outcome == o) & (idf.comparison == comp) & (idf.checkpoint == cp) & (idf.protocol == prot)][col].iloc[0])


def C(stage, o, comp, cp=None, col="delta"):
    q = cf[(cf.stage == stage) & (cf.outcome == o) & (cf.comparison == comp)]
    if cp is not None:
        q = q[q.checkpoint == cp]
    return float(q[col].iloc[0])


SPILL = ("spillover", "serious_spillover")
LATE = ("late_closure", "seriously_late")
ALL4 = SPILL + LATE
CPS = (0.25, 0.5)

# measurability check
rc = pd.read_csv(jr.DATA / "recording_check.csv")
check("Three projects stand out", rc.excluded.sum() == 3)
check("so any cut-off between 1\\% and 56\\% picks the same three projects",
      rc[~rc.excluded].share.max() < 0.01 and rc[rc.excluded].share.min() >= 0.56)
ext = pd.concat([recording_check(jr.EXTERNAL_RAW / inst) for inst in ("mariadb", "mongodb")])
check("All ten pass the measurability check", (~ext.excluded).all() and len(ext) == 10)
f = pd.read_csv(jr.DATA / "planning_frame.csv")
nf = nothing_finished_projects(f)
check("Two other projects, Appcelerator Daemon and Hyperledger Indy Node, also show sprints that finish nothing",
      nf == ["Appcelerator Daemon", "Hyperledger Indy Node"])
check("but their unfinished issues are genuinely open in the export", rc.set_index("project").loc[nf, "share"].max() < 0.01)

# hypotheses
check("which survives the Holm adjustment", hyp[(hyp.h == "H1") & (hyp.outcome == "spillover")].p_holm.iloc[0] < 0.05)
check("with the same sign in all three models",
      all(P("serious_spillover", "strict+new - strict", model=m) > 0 for m in ("Logistic regression", "Random forest", GB)))
check("For the two late labels it is about zero, as predicted", all(abs(P(o, "strict+new - strict")) < 0.01 for o in LATE))
check("We read H1 as a small gain for spillover that we cannot confirm",
      P("spillover", "strict+new - strict", col="ci_low") > 0 and C("planning", "spillover", "strict+new - strict", col="ci_low") < 0)
h2 = [I(o, "ours - worki", cp) for o in SPILL for cp in CPS]
check("Ours beats worki by 0.13 to 0.19 AUC", round(min(h2), 2) == 0.13 and round(max(h2), 2) == 0.19)
check("Burndown-shape features rank sprints worse by 0.13 to 0.19 AUC", round(min(h2), 2) == 0.13 and round(max(h2), 2) == 0.19)
check("in the full cohort and on the confirmation set",
      all(I(o, "ours - worki", cp, col="ci_low") > 0 and C("in-sprint", o, "ours - worki", cp, "ci_low") > 0 for o in SPILL for cp in CPS))
h3 = [I(o, "ours - choet", cp) for o in ALL4 for cp in CPS]
check("Ours beats choet for every outcome, by 0.03 to 0.09", min(h3) > 0 and round(min(h3), 2) == 0.03 and round(max(h3), 2) == 0.09)
los = {(o, cp): I(o, "ours - choet", cp, col="ci_low") for o in ALL4 for cp in CPS}
check("the project-level interval clears zero clearly only for seriously late at 50\\%; for the spillover labels it sits on zero",
      [k for k, v in los.items() if v > 0.005] == [("seriously_late", 0.5)] and all(abs(los[(o, cp)]) < 0.005 for o in SPILL for cp in CPS))
check("On the confirmation set the gain is larger and holds for both spillover labels",
      all(C("in-sprint", o, "ours - choet", cp, "ci_low") > 0 and C("in-sprint", o, "ours - choet", cp) > I(o, "ours - choet", cp)
          for o in SPILL for cp in CPS))
check("Seriously late and scope churn do not hold", all(P(o, "strict+new - scope", col="ci_low") < 0 for o in ("seriously_late", "scope_churn")))
check("but the gain does not hold on the", C("planning", "spillover", "strict+new - strict", col="ci_low") < 0)
check("for seriously late the interval ends just below zero",
      -0.002 < P("seriously_late", "strict+new - strict", col="ci_high") < 0)
fine = pd.read_csv(R / "hypotheses_fine.csv")
fl = lambda o, cp: float(fine[(fine.h == "H3") & (fine.outcome == o) & (fine.checkpoint == cp)].lo.iloc[0])
check("with the 10,000 resamples used for the $p$-values it no longer does, while the one for serious spillover at 50\\% then just clears it",
      I("spillover", "ours - choet", 0.5, col="ci_low") > 0 and fl("spillover", 0.5) < 0
      and I("serious_spillover", "ours - choet", 0.5, col="ci_low") < 0 and fl("serious_spillover", 0.5) > 0)
check("all for H3, end within 0.001 of zero", set(hyp[hyp.lo.abs() < 0.001].h) == {"H3"})

h4 = hyp[(hyp.h == "H4") & (hyp.outcome == "serious_spillover")].iloc[0]
rdv = pd.read_csv(R / "robust_differences.csv")
rrs = pd.read_csv(R / "robust_restricted.csv")
rhs = pd.read_csv(R / "robust_history.csv")
unc = pd.read_csv(jr.ROOT / "results" / "tawos_all" / "planning_differences.csv")
pick = lambda d: d[(d.outcome == "serious_spillover") & (d.comparison == "strict+new - scope")]
variants_lo = ([float(x) for x in pick(rdv).ci_low] + [float(x) for x in pick(rrs[rrs.model == GB] if "model" in rrs else rrs).ci_low]
               + [float(x) for x in pick(rhs[rhs.stage == "planning"]).ci_low]
               + [float(pick(unc[(unc.model == GB) & (unc.protocol == "time")]).ci_low.iloc[0])])
check("It does not survive the Holm adjustment, but it holds under leave-one-project-out testing and every robustness variant, and replicates on the confirmation set",
      h4.p_holm >= 0.05 and h4.c_lo > 0 and P("serious_spillover", "strict+new - scope", "lopo", col="ci_low") > 0
      and P("serious_spillover", "strict+new - scope", "time, no SP fallback", col="ci_low") > 0
      and len(variants_lo) >= 5 and min(variants_lo) > 0)

# within-project analysis (jr/within.py)
wd = pd.read_csv(R / "within_differences.csv")
W = lambda st, o, comp, cp=None, col="delta": float(wd[(wd.stage == st) & (wd.outcome == o) & (wd.comparison == comp)
                                                       & ((wd.checkpoint == cp) if cp is not None else wd.checkpoint.isna())][col].iloc[0])
wk_ok = all(W("in-sprint", o, "ours - worki", cp, "ci_low") > 0 for o in SPILL for cp in CPS)
add_w = max(W("in-sprint", o, "ours+worki - ours", cp) for o in ALL4 for cp in CPS)
check("add nothing when combined with progress counts, across projects and within them", wk_ok and add_w < 0.01)
check("within a team as well as across teams", wk_ok)
check("and burndown shape still adds nothing", add_w < 0.01)
check("but nearly all of that gain comes from telling teams apart",
      W("planning", "serious_spillover", "strict+new - scope") < 0.25 * P("serious_spillover", "strict+new - scope")
      and W("planning", "serious_spillover", "strict+new - scope", col="ci_low") < 0)
check("with an interval that includes zero", W("planning", "serious_spillover", "strict+new - scope", col="ci_low") < 0)
check("within projects too", W("planning", "spillover", "strict+new - strict", col="ci_low") > 0)
check("The new features keep their gain for spillover", W("planning", "spillover", "strict+new - strict", col="ci_low") > 0)
check("Within projects the spillover gain is the same size",
      abs(W("planning", "spillover", "strict+new - strict") - P("spillover", "strict+new - strict")) < 0.01)
check("the history-aware set ranks a team's own sprints worse than scope alone",
      W("planning", "late_closure", "strict+new - scope", col="ci_high") < 0)
check("so the outside test asked history for a gain it does not show at home either",
      W("planning", "serious_spillover", "strict+new - scope", col="ci_low") < 0)
check("Scored only within projects, the in-sprint findings hold but most of the planning-time history gain disappears",
      wk_ok and W("planning", "serious_spillover", "strict+new - scope") < 0.25 * P("serious_spillover", "strict+new - scope"))
check("A single team learns little from its own history that the size of the sprint does not already say",
      all(W("planning", o, "strict+new - scope", col="ci_low") < 0 for o in ("spillover", "serious_spillover", "late_closure")))

# planning time
check("Plain spillover is mostly a matter of how many issues were committed",
      P("serious_spillover", "strict - scope") > P("spillover", "strict - scope")
      and P("serious_spillover", "strict - scope", "lopo") > P("spillover", "strict - scope", "lopo"))
a = pd.read_csv(R / "planning_auc.csv"); a = a[(a.model == GB) & (a.protocol == "time")]
t = a[a.outcome.isin(SPILL)].set_index(["outcome", "features"])
check("is several times the base rate but well below one",
      all(2 * (1 - t.loc[(o, fs), "positives"] / t.loc[(o, fs), "n"]) < t.loc[(o, fs), "ap_negative"] < 0.6
          for o in SPILL for fs in ("scope", "strict", "strict+new")))

# in-sprint fair comparisons
add = idf[(idf.protocol == "time") & (idf.comparison == "ours+worki - ours")].delta.abs().max()
check("changes AUC by at most", add <= 0.0125)
for o, cp in (("late_closure", 0.25), ("seriously_late", 0.25), ("seriously_late", 0.5), ("spillover", 0.5)):
    check("ranks worse than committed scope, with intervals below zero", I(o, "worki - scope", cp, col="ci_high") < 0)
check("none of these intervals clears zero", all(I(o, "choet+ctx - choet", cp, col="ci_low") < 0 for o in SPILL for cp in CPS))
check("Under leave-one-project-out testing it helps serious spillover", I("serious_spillover", "choet+ctx - choet", 0.25, "lopo", "ci_low") > 0)
check("For seriously late at 50\\% it adds", I("seriously_late", "choet+ctx - choet", 0.5, col="ci_low") > 0)
check("Our progress counts add a little beyond theirs for serious spillover", I("serious_spillover", "ours - choet+ctx", 0.5, col="ci_low") > 0)
check("and on the confirmation set at both checkpoints", all(C("in-sprint", "serious_spillover", "ours - choet+ctx", cp, "ci_low") > 0 for cp in CPS))

# binomial
bd = pd.read_csv(R / "binomial_differences.csv")
gb_bin = lambda d, o: d[(d.outcome == o) & (d.comparison == "strict+new - binomial")]
check("The two cannot be told apart", all(gb_bin(bd, o).ci_low.iloc[0] < 0 for o in SPILL))
check("ranks sprints about as well as gradient boosting", all(gb_bin(bd, o).ci_low.iloc[0] < 0 for o in SPILL))
bc = pd.read_csv(R / "binomial_confirm.csv")
check("On the confirmation set the gap to gradient boosting is wider",
      all(gb_bin(bc, o).delta.iloc[0] > gb_bin(bd, o).delta.iloc[0] for o in SPILL))
check("and the binomial model still beats scope for serious spillover",
      bc[(bc.outcome == "serious_spillover") & (bc.comparison == "binomial - scope")].ci_low.iloc[0] > 0)
bv = pd.read_csv(R / "binomial_variance.csv")
check("In every band of sprint size the observed variance of the carry ratio exceeds the binomial variance",
      (bv.var_observed > bv.var_binomial).all())
check("A gap that grows with sprint size", (bv.var_observed / bv.var_binomial).is_monotonic_increasing)
bcal = pd.read_csv(R / "binomial_calibration.csv").set_index(["outcome", "model"])
check("Neither is as well calibrated as gradient boosting",
      all(abs(1 - bcal.loc[(o, "strict+new"), "slope"]) < min(abs(1 - bcal.loc[(o, m), "slope"]) for m in ("binomial", "beta-binomial"))
          for o in SPILL))

# outside
e = pd.read_csv(R / "external_summary.csv"); e = e[e.model == GB].set_index(["outcome", "features"])["mean"]
check("and the history-aware sets score lower", all(e[(o, fs)] < e[(o, "scope")] for o in SPILL for fs in ("strict", "strict+new")))
lc = [e[("late_closure", fs)] for fs in ("scope", "strict", "strict+new")]
check("For late closure all three sets sit between", min(lc) == e[("late_closure", "strict")] and max(lc) == e[("late_closure", "scope")])

# robustness narrative
od = pd.read_csv(jr.ROOT / "results" / "tawos_all" / "planning_differences.csv")
od = od[(od.model == GB) & (od.protocol == "time") & (od.comparison == "strict+new - strict")].set_index("outcome")
check("the new features added more for serious spillover and less for spillover",
      od.loc["serious_spillover", "delta"] > P("serious_spillover", "strict+new - strict")
      and od.loc["spillover", "delta"] < P("spillover", "strict+new - strict"))
check("Removing them changes which of our hypotheses hold",
      (od.loc["serious_spillover", "ci_low"] > 0) != (P("serious_spillover", "strict+new - strict", col="ci_low") > 0))
cal = pd.read_csv(R / "calibration.csv")
check("which are overconfident", (cal[cal.outcome.isin(LATE) & cal.features.isin(["strict+new", "ours"])].slope < 1).all())

# reconstruction check
recf = R / "reconstruction_check.csv"
if recf.exists():
    rcc = pd.read_csv(recf).iloc[0]
    check("the replay follows the log", rcc.export_empty_log_known_sprint > 0)
hf = R / "robust_history.csv"
if hf.exists():
    hh = pd.read_csv(hf)
    check("Burndown shape added to ours changes AUC by at most", hh[hh.comparison == "ours+worki - ours"].delta.abs().max() < 0.015)
    hc = hh[(hh.comparison == "choet+ctx - choet") & (hh.outcome == "spillover") & (hh.checkpoint == 0.25)].iloc[0]
    check("planning context added to the choet counts gains more than on the full cohort",
          hc.delta > I("spillover", "choet+ctx - choet", 0.25) and hc.ci_low > 0)

# decisions
if (R / "robust_net_benefit.csv").exists():
    nb = pd.read_csv(R / "robust_net_benefit.csv").set_index(["outcome", "p_star"])
    r5, r9 = nb.loc[("serious_spillover", 0.5)], nb.loc[("serious_spillover", 0.9)]
    check("warning on every sprint is almost as good as any model unless warnings are costly",
          max(r5.nb_planning, r5.nb_25, r5.nb_50) - r5.nb_warn_all < 0.03)
    check("does the model clearly add value", min(r9.nb_planning, r9.nb_50) > r9.nb_warn_all + 0.01)
    lcn = nb.loc["late_closure"]
    prev = float(nb.loc[("late_closure", 0.3), "prevalence"])
    check("warning on all sprints loses at any threshold above the base rate",
          (lcn[lcn.index > prev].nb_warn_all < 0).all() and (lcn[lcn.index < prev].nb_warn_all > 0).all())
    check("the planning-time model gains a little", (lcn.loc[[0.3, 0.5], "nb_planning"] > 0).all())
    check("the in-sprint models gain no more than the planning model, so waiting never pays",
          all(lcn.loc[p_, "nb_25"] <= lcn.loc[p_, "nb_planning"] + 0.002 and lcn.loc[p_, "nb_50"] <= lcn.loc[p_, "nb_planning"] + 0.002
              for p_ in lcn.index))
    ra = pd.read_csv(R / "robust_auc.csv")
    cuts = pd.to_datetime(ra[ra.protocol == "calendar cut"].best)
    check("in early 2018", (cuts.dt.year == 2018).all() and (cuts.dt.month <= 3).all())
    b = pd.read_csv(R / "robust_budgets.csv")
    pr = lambda o, fs: b[(b.outcome == o) & (b.budget == 0.1) & (b.features == fs)].precision.iloc[0]
    check("the history-aware model raises the hit rate among the top 10\\%",
          pr("serious_spillover_median", "strict+new") > pr("serious_spillover_median", "scope"))

print(f"{n - len(fails)} of {n} checks pass")
print("FAILS:", fails)
