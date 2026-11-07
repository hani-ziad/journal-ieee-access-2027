"""Checks of the claims in paper/theory.tex for the current cohort.

    python -m jr.theory_numbers     (computes results/<cohort>/theory_numbers.json)
    python -m jr.theory_checks

Checks the identities themselves (not just the printed numbers): Proposition 1's mixture
equals the observed AUC, Proposition 2's implied ratios follow from the prevalences, and the
binomial model's numbers follow from the frame. The printed macros come from jr/tables.py.
"""
from __future__ import annotations

import json

import pandas as pd

import jr

t = json.loads((jr.RESULTS / "theory_numbers.json").read_text())
p1, p2, m, gaps = t["prop1"], t["prop2"], t["minimal_model"], t["gaps"]
fails = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)


# Proposition 1
check("pi0 = structural / all negatives", abs(p1["pi0"] - p1["structural_negatives"] / p1["negatives"]) < 1e-12)
check("mixture identity: AUC_all = pi0*A0 + (1-pi0)*AUC_N1", abs(p1["auc_all"] - p1["auc_all_from_mixture"]) < 1e-9)
check("inflation = AUC_all - AUC_N1 when A0 = 1",
      p1["A0"] < 1 or abs((p1["auc_all"] - p1["auc_nonempty"]) - p1["inflation_if_A0_is_1"]) < 1e-9)

# Proposition 2
pp = pd.DataFrame(p2["per_project"])
check("implied ratio (1-pi)/pi on training data", abs(p2["implied_ratio_train"] - (1 - p2["train_prevalence"]) / p2["train_prevalence"]) < 1e-12)
check("ratio at min prevalence", abs(p2["ratio_at_min_prev"] - (1 - pp.prevalence.min()) / pp.prevalence.min()) < 1e-12)
check("ratio at max prevalence", abs(p2["ratio_at_max_prev"] - (1 - pp.prevalence.max()) / pp.prevalence.max()) < 1e-12)
check("sensitivity rises with prevalence (Spearman > 0.5)", p2["spearman_prev_sens"] > 0.5)
check("outside prevalences straddle the training prevalence",
      pp.prevalence.min() < p2["train_prevalence"] < pp.prevalence.max())

# Minimal model
f = pd.read_csv(jr.DATA / "planning_frame.csv")
ne = f[f.nonempty]
check("q = 1 - median carry ratio", abs(m["q"] - (1 - ne.carry_ratio.median())) < 1e-12)
check("P(spill | n=3) = 1 - q^3", abs(m["p_spill_n3"] - (1 - m["q"] ** 3)) < 1e-12)
check("nonempty spillover rate", abs(m["nonempty_spillover_rate"] - ne.label_spillover.mean()) < 1e-12)
check("prediction: history-minus-scope gap larger for serious spillover (time split)",
      gaps["serious_spillover_time_strict_minus_scope"] > gaps["spillover_time_strict_minus_scope"])
check("prediction: history-minus-scope gap larger for serious spillover (LOPO)",
      gaps["serious_spillover_lopo_strict_minus_scope"] > gaps["spillover_lopo_strict_minus_scope"])

# Printed macros match the json
tex = (jr.ROOT / "paper" / "tables" / "numbers.tex").read_text()
for macro, val in (("PiZero", f"{p1['pi0']:.3f}"), ("AucAll", f"{p1['auc_all']:.3f}"),
                   ("AucNonempty", f"{p1['auc_nonempty']:.3f}"), ("Qhat", f"{m['q']:.2f}"),
                   ("SpearmanPS", f"{p2['spearman_prev_sens']:.2f}")):
    check(f"macro {macro} = {val}", f"\\newcommand{{\\{macro}}}{{{val}}}" in tex)

# Proposition 3 (beta-binomial variance), checked by simulation, and the variance table
import numpy as np  # noqa: E402
rng = np.random.default_rng(jr.SEED)
for qq, nn, rr in ((0.3, 10, 0.18), (0.6, 4, 0.05), (0.2, 25, 0.4)):
    a, b = (1 - qq) * (1 - rr) / rr, qq * (1 - rr) / rr
    rho = rng.binomial(nn, rng.beta(a, b, 400_000)) / nn
    theory = qq * (1 - qq) / nn * (1 + (nn - 1) * rr)
    check(f"Var[rho] formula q={qq} n={nn} r={rr}", abs(rho.var() - theory) / theory < 0.01)
b = json.loads((jr.RESULTS / "binomial.json").read_text())
v = pd.read_csv(jr.RESULTS / "binomial_variance.csv")
check("r_hat > 0 (issues of a sprint are positively correlated)", b["r_hat"] > 0)
check("observed variance above binomial in every size band", bool((v.var_observed > v.var_binomial).all()))
check("observed/binomial variance ratio grows with sprint size", bool((v.var_observed / v.var_binomial).is_monotonic_increasing))

print("FAILS:", fails)
