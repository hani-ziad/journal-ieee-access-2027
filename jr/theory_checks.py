"""Numerical checks of the claims in paper/theory.tex against the repository's result files.

    python -m jr.theory_checks
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import jr

P1 = jr.PRIOR_RESULTS
P4 = jr.PRIOR_RESULTS
fails = []


def check(name, claimed, actual, tol):
    ok = abs(claimed - actual) <= tol
    print(("PASS " if ok else "FAIL ") + f"{name}: paper={claimed} computed={actual:.4f}")
    if not ok:
        fails.append(name)


# Proposition 1: AUC on the full population = pi0 * A0 + (1 - pi0) * AUC_nonempty
cmp_ = pd.read_csv(P1 / "assignment_comparison.csv")
late = cmp_[cmp_.task == "late_closure"].iloc[0]
spill = cmp_[cmp_.task == "spillover"].iloc[0]
neg_all = 786 - 453  # full-population spillover test set: 786 sprints, 453 positive (Table II row 8 of the CCECE paper)
neg_ne = int(spill.n_test) - round(spill.n_test * spill.positive_rate)
pi0 = (neg_all - neg_ne) / neg_all
base = json.load(open(P1 / "baseline_results.json"))
cond = json.load(open(P1 / "conditional_spillover.json"))
auc_all = base["label_spillover"]["time_ordered"]["random_forest"]["roc_auc"]
auc_ne = cond["time_ordered"]["random_forest"]["roc_auc"]
check("pi0 = 0.913", 0.913, pi0, 0.001)
check("predicted full AUC with A0=1 is 0.987", 0.987, pi0 + (1 - pi0) * auc_ne, 0.001)
a0 = (auc_all - (1 - pi0) * auc_ne) / pi0
check("implied A0 = 0.999", 0.999, a0, 0.001)
check("inflation pi0(1-AUC_ne) ~ 0.135", 0.135, pi0 * (1 - auc_ne), 0.002)

# Proposition 2: Youden's implied cost ratio and sensitivity on the outside projects
e = pd.read_csv(P4 / "e3_external_per_project.csv")
e = e[(e.task == "Late closure") & (e.model == "Gradient boosting") & e.interpretable].copy()
e["prev"] = e.n_pos / e.n
check("TAWOS implied ratio (1-.313)/.313 = 2.2", 2.2, (1 - 0.313) / 0.313, 0.01)
check("outside prevalence min 0.07", 0.07, e.prev.min(), 0.005)
check("outside prevalence max 0.59", 0.59, e.prev.max(), 0.005)
check("implied ratio at min prevalence 13", 13, (1 - e.prev.min()) / e.prev.min(), 0.2)
check("implied ratio at max prevalence 0.7", 0.7, (1 - e.prev.max()) / e.prev.max(), 0.02)
check("sensitivity min 0.11", 0.11, e.sensitivity.min(), 0.005)
check("sensitivity max 0.86", 0.86, e.sensitivity.max(), 0.005)
check("rank correlation prevalence vs sensitivity 0.93", 0.93, e[["prev", "sensitivity"]].corr("spearman").iloc[0, 1], 0.005)

# Minimal model: q = 1 - median carry ratio; P(spill | n=3) = 1 - q^3
f = pd.read_csv(jr.DATA / "planning_frame.csv")
ne = f[f.nonempty]
q = 1 - ne.carry_ratio.median()
check("median carry ratio 0.75 (q = 0.25)", 0.25, q, 0.005)
check("P(any spill | n=3, q=.25) = 0.98", 0.98, 1 - q ** 3, 0.005)
check("nonempty spillover rate 0.93", 0.93, ne.label_spillover.mean(), 0.005)

print("FAILS:", fails)
