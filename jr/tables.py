"""Write the paper's tables straight from the result files, so no number is typed by hand.

    python -m jr.tables      writes paper/tables/*.tex for the current cohort
"""
from __future__ import annotations

import json

import pandas as pd

import jr
from jr.data import OUTCOMES

OUT = jr.ROOT / "paper" / "tables"
NAMES = {"late_closure": "Late closure", "seriously_late": "Seriously late", "spillover": "Spillover",
         "serious_spillover": "Serious spillover", "scope_churn": "Scope churn"}
ORDER = ["spillover", "serious_spillover", "late_closure", "seriously_late", "scope_churn"]
GB = "Gradient boosting"


def f3(x):
    return "--" if pd.isna(x) else f"{x:.3f}"


def d3(x):
    if pd.isna(x):
        return "--"
    x = round(float(x), 3) + 0.0  # no negative zero
    return (f"{x:+.3f}" if x != 0 else "0.000").replace("-", "$-$")


def ci(lo, hi):
    return f"[{d3(lo)}, {d3(hi)}]"


def write(name, body):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.tex").write_text(body)


def labels_table():
    f = pd.read_csv(jr.DATA / "planning_frame.csv")
    pops = {"full": ("All", f), "nonempty": ("Nonempty", f[f.nonempty])}
    rows = []
    for o in ORDER:
        pop, y = OUTCOMES[o]
        d = pops[pop][1].dropna(subset=[y])
        popname = "Nonempty, 5+" if o == "scope_churn" else pops[pop][0]
        rows.append(f"{NAMES[o]} & {popname} & {len(d):,} & {100 * d[y].mean():.0f}\\% \\\\")
    for lab, y, pop in [("Serious sp., median", "label_serious_spillover_median", "nonempty"),
                        ("Serious sp., 20\\%", "label_serious_spillover_20", "nonempty"),
                        ("Serious sp., 50\\%", "label_serious_spillover_50", "nonempty"),
                        ("Seriously late, 7 days", "label_seriously_late_7", "full"),
                        ("Scope churn, 50\\%", "label_scope_churn_50", "churn")]:
        d = (f if pop == "full" else f[f.nonempty]).dropna(subset=[y])
        rows.append(f"\\quad {lab} & same & {len(d):,} & {100 * d[y].mean():.0f}\\% \\\\")
    write("labels", "\n".join(rows) + "\n")


def planning_auc_table():
    a = pd.read_csv(jr.RESULTS / "planning_auc.csv")
    a = a[a.model == GB]
    rows = []
    for o in ORDER:
        t = a[a.outcome == o].pivot_table(index="protocol", columns="features", values="auc")
        cells = [f3(t.loc[p, s]) for p in ("time", "lopo") for s in ("scope", "strict", "strict+new")]
        rows.append(f"{NAMES[o]} & " + " & ".join(cells) + " \\\\")
    write("planning_auc", "\n".join(rows) + "\n")


def primary_planning_table():
    d = pd.read_csv(jr.RESULTS / "planning_differences.csv")
    d = d[d.primary == True]  # noqa: E712
    rows = []
    for comp, h in (("strict+new - strict", "H1"), ("strict+new - scope", "H4")):
        for o in ORDER:
            r = d[(d.outcome == o) & (d.comparison == comp)]
            if r.empty:
                continue
            r = r.iloc[0]
            rows.append(f"{h} & {NAMES[o]} & {d3(r.delta)} & {ci(r.ci_low, r.ci_high)} & "
                        f"{ci(r.sprint_ci_low, r.sprint_ci_high)} \\\\")
        rows.append("\\midrule")
    write("primary_planning", "\n".join(rows[:-1]) + "\n")


def insprint_auc_table():
    a = pd.read_csv(jr.RESULTS / "insprint_auc.csv")
    a = a[(a.model == GB) & (a.protocol == "time")]
    rows = []
    for o in ["spillover", "serious_spillover", "late_closure", "seriously_late"]:
        for cp in (0.25, 0.5):
            t = a[(a.outcome == o) & (a.checkpoint == cp)].set_index("features").auc
            rows.append(f"{NAMES[o] if cp == 0.25 else ''} & {int(cp * 100)}\\% & " +
                        " & ".join(f3(t[s]) for s in ("scope", "worki", "choet", "ours", "ours+worki")) + " \\\\")
    write("insprint_auc", "\n".join(rows) + "\n")


def primary_insprint_table():
    d = pd.read_csv(jr.RESULTS / "insprint_differences.csv")
    d = d[d.primary == True]  # noqa: E712
    rows = []
    for comp, h, outs in (("ours - worki", "H2", ["spillover", "serious_spillover"]),
                          ("ours - choet", "H3", ["spillover", "serious_spillover", "late_closure", "seriously_late"]),
                          ("worki - scope", "--", ["spillover", "serious_spillover", "late_closure", "seriously_late"])):
        for o in outs:
            for cp in (0.25, 0.5):
                r = d[(d.outcome == o) & (d.comparison == comp) & (d.checkpoint == cp)].iloc[0]
                rows.append(f"{h} & {comp.replace(' - ', ' $-$ ')} & {NAMES[o]} & {int(cp * 100)}\\% & {d3(r.delta)} & "
                            f"{ci(r.ci_low, r.ci_high)} & {ci(r.sprint_ci_low, r.sprint_ci_high)} \\\\")
        rows.append("\\midrule")
    write("primary_insprint", "\n".join(rows[:-1]) + "\n")


def external_table():
    e = pd.read_csv(jr.RESULTS / "external_summary.csv")
    e = e[e.model == GB]
    rows = []
    for o in ORDER:
        t = e[e.outcome == o].set_index("features")
        n = int(t["count"].iloc[0])
        rows.append(f"{NAMES[o]} & {n} & " +
                    " & ".join(f"{t.loc[s, 'mean']:.3f} $\\pm$ {t.loc[s, 'std']:.3f}" for s in ("scope", "strict", "strict+new"))
                    + " \\\\")
    write("external", "\n".join(rows) + "\n")


def calibration_table():
    c = pd.read_csv(jr.RESULTS / "calibration.csv")
    rows = []
    keep = [("planning", "strict+new"), ("in-sprint 25%", "ours"), ("in-sprint 50%", "ours")]
    for o in ["spillover", "serious_spillover", "late_closure", "seriously_late"]:
        for st, fs in keep:
            r = c[(c.outcome == o) & (c.stage == st) & (c.features == fs)].iloc[0]
            rows.append(f"{NAMES[o] if st == 'planning' else ''} & {st.replace('%', chr(92) + '%')} & "
                        f"{r.brier:.3f} & {r.brier_reference:.3f} & {r.ece:.3f} & {r.slope:.2f} \\\\")
    write("calibration", "\n".join(rows) + "\n")


def theory_numbers():
    t = json.loads((jr.RESULTS / "theory_numbers.json").read_text())
    p1, p2, m = t["prop1"], t["prop2"], t["minimal_model"]
    macros = {
        "PiZero": f"{p1['pi0']:.3f}", "NegAll": f"{p1['negatives']}", "NegStruct": f"{p1['structural_negatives']}",
        "AucNonempty": f"{p1['auc_nonempty']:.3f}", "AucAll": f"{p1['auc_all']:.3f}",
        "AucPred": f"{p1['auc_all_if_A0_is_1']:.3f}", "AZero": f"{p1['A0']:.3f}",
        "Inflation": f"{p1['inflation_if_A0_is_1']:.3f}",
        "TrainPrev": f"{p2['train_prevalence']:.2f}", "TrainRatio": f"{p2['implied_ratio_train']:.1f}",
        "ExtProjects": f"{p2['n_projects']}", "PrevMin": f"{p2['prev_min']:.2f}", "PrevMax": f"{p2['prev_max']:.2f}",
        "RatioMin": f"{p2['ratio_at_min_prev']:.0f}", "RatioMax": f"{p2['ratio_at_max_prev']:.1f}",
        "SensMin": f"{p2['sens_min']:.2f}", "SensMax": f"{p2['sens_max']:.2f}",
        "SpearmanPS": f"{p2['spearman_prev_sens']:.2f}",
        "CarryMedian": f"{m['median_carry_ratio']:.2f}", "Qhat": f"{m['q']:.2f}",
        "PSpillThree": f"{m['p_spill_n3']:.3f}", "NonemptySpill": f"{100 * m['nonempty_spillover_rate']:.1f}",
        "MedianIssues": f"{m['median_committed_issues']:.0f}",
    }
    f = pd.read_csv(jr.DATA / "planning_frame.csv")
    te = f[f.nonempty & (f.split_nonempty == "test")]
    macros.update({"OverlapShare": f"{100 * (f.n_concurrent_sprints > 0).mean():.0f}",
                   "NoFallbackTest": f"{int((te.sp_fallback_share == 0).sum())}",
                   "FallbackMean": f"{100 * f.sp_fallback_share.mean():.1f}"})
    write("numbers", "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items()))


def binomial_tables():
    a = pd.read_csv(jr.RESULTS / "binomial_auc.csv").set_index(["outcome", "model"]).auc
    c = pd.read_csv(jr.RESULTS / "binomial_calibration.csv")
    sc = pd.read_csv(jr.RESULTS / "calibration.csv")  # same model and test sprints for the scope set
    sc = sc[(sc.stage == "planning") & (sc.features == "scope")].rename(columns={"features": "model"})
    c = pd.concat([c, sc[c.columns.intersection(sc.columns)]]).set_index(["outcome", "model"])
    rows = []
    for m, lab in (("scope", "Gradient boosting, scope"), ("binomial", "Binomial, no learning"),
                   ("beta-binomial", "Beta-binomial, one parameter"), ("strict+new", "Gradient boosting, strict+new")):
        cells = []
        for o in ("spillover", "serious_spillover"):
            cells.append(f3(a[(o, m)]))
            cells.append(f"{c.loc[(o, m), 'slope']:.2f}" if (o, m) in c.index else "--")
        rows.append(f"{lab} & " + " & ".join(cells) + " \\\\")
    write("binomial", "\n".join(rows) + "\n")
    v = pd.read_csv(jr.RESULTS / "binomial_variance.csv")
    rows = [f"{r.n_band.replace('-', '--')} & {r.sprints} & {r.var_observed:.3f} & {r.var_binomial:.3f} & {r.var_betabinomial:.3f} \\\\"
            for r in v.itertuples()]
    write("binomial_variance", "\n".join(rows) + "\n")
    info = json.loads((jr.RESULTS / "binomial.json").read_text())
    with open(OUT / "numbers.tex", "a") as fh:
        fh.write(f"\\newcommand{{\\Rhat}}{{{info['r_hat']:.2f}}}\n")
        fh.write(f"\\newcommand{{\\DispRatio}}{{{info['dispersion_ratio_train']:.1f}}}\n")
        fh.write(f"\\newcommand{{\\LRstat}}{{{info['lr_stat']:,.0f}}}\n")


def confirm_table():
    d = pd.read_csv(jr.RESULTS / "confirm_differences.csv")
    full_p = pd.read_csv(jr.RESULTS / "planning_differences.csv")
    full_i = pd.read_csv(jr.RESULTS / "insprint_differences.csv")
    rows = []
    spec = [("H1", "planning", "strict+new - strict", list(NAMES), [None]),
            ("H4", "planning", "strict+new - scope", list(NAMES), [None]),
            ("H2", "in-sprint", "ours - worki", ["spillover", "serious_spillover"], [0.25, 0.5]),
            ("H3", "in-sprint", "ours - choet", ["spillover", "serious_spillover", "late_closure", "seriously_late"], [0.25, 0.5])]
    for h, st, comp, outs, cps in spec:
        for o in outs:
            for cp in cps:
                q = d[(d.stage == st) & (d.outcome == o) & (d.comparison == comp)]
                if cp is not None:
                    q = q[q.checkpoint == cp]
                    fq = full_i[(full_i.primary == True) & (full_i.outcome == o) & (full_i.comparison == comp) & (full_i.checkpoint == cp)]  # noqa: E712
                else:
                    fq = full_p[(full_p.primary == True) & (full_p.outcome == o) & (full_p.comparison == comp)]  # noqa: E712
                r, fr = q.iloc[0], fq.iloc[0]
                lab = NAMES[o] + ("" if cp is None else f", {int(cp * 100)}\\%")
                mark = lambda lo: "$\\checkmark$" if lo > 0 else ""
                rows.append(f"{h} & {lab} & {d3(fr.delta)} & {mark(fr.ci_low)} & {d3(r.delta)} & "
                            f"{ci(r.ci_low, r.ci_high)} & {mark(r.ci_low)} \\\\")
        rows.append("\\midrule")
    write("confirm", "\n".join(rows[:-1]) + "\n")


if __name__ == "__main__":
    labels_table(); planning_auc_table(); primary_planning_table(); insprint_auc_table()
    primary_insprint_table(); external_table(); calibration_table(); theory_numbers()
    binomial_tables()
    if (jr.RESULTS / "confirm_differences.csv").exists():
        confirm_table()
    for p in sorted(OUT.glob("*.tex")):
        print("==", p.name); print(p.read_text())
