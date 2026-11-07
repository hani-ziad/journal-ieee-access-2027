"""The minimal model of Section III as a predictor with no learning.

Each sprint's completion rate q is estimated from the team's last three finished sprints known at
the start (pooled: completed / committed issues; the strict history window of Phase 2, so the
estimate is admissible). The binomial model then gives the risk of spillover and of serious
spillover in closed form. The beta-binomial model adds one overdispersion parameter, the
intra-sprint correlation r, fitted by maximum likelihood on the training sprints only.

    python -m jr.binomial      writes results/<cohort>/binomial_*.csv and binomial.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy import optimize, stats

import jr
from jr.run import PLAN_SETS, PRIMARY_MODEL, diff_row, fit_predict, safe_auc, save, unit
from jr.theory_numbers import calibration_row

TAU = 0.30


def q_hat(f: pd.DataFrame, fallback: float) -> np.ndarray:
    q = f.hist_avg_completed_issues_3 / f.hist_avg_committed_issues_3
    return q.fillna(fallback).clip(0.01, 0.99).to_numpy()


def k_star(n: np.ndarray, tau: float) -> np.ndarray:
    """Smallest number of unfinished issues with carry ratio >= tau."""
    return np.ceil(tau * n - 1e-9).astype(int)


def risk_binomial(n, q, label):
    p = 1 - q  # chance an issue is left unfinished
    if label == "spillover":
        return 1 - q ** n
    return stats.binom.sf(k_star(n, TAU) - 1, n, p)


def ab(p, r):
    a = p * (1 - r) / r
    b = (1 - p) * (1 - r) / r
    return a, b


def risk_betabinom(n, q, r, label):
    a, b = ab(1 - q, r)
    if label == "spillover":
        return 1 - stats.betabinom.pmf(0, n, a, b)
    return stats.betabinom.sf(k_star(n, TAU) - 1, n, a, b)


def fit_r(x, n, q):
    nll = lambda r: -stats.betabinom.logpmf(x, n, *ab(1 - q, r)).sum()
    res = optimize.minimize_scalar(nll, bounds=(1e-4, 0.95), method="bounded")
    ll_bb = -res.fun
    ll_b = stats.binom.logpmf(x, n, 1 - q).sum()
    lr = 2 * (ll_bb - ll_b)
    return float(res.x), float(lr), float(0.5 * stats.chi2.sf(lr, 1))  # boundary: half chi-square


def main():
    f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
    ne = f[f.nonempty].copy()
    tr, te = ne[ne.split_nonempty == "train"], ne[ne.split_nonempty == "test"]
    pooled = float(tr.completed_issue_count.sum() / tr.committed_issue_count.sum())
    n_tr, n_te = tr.committed_issue_count.to_numpy(int), te.committed_issue_count.to_numpy(int)
    q_tr, q_te = q_hat(tr, pooled), q_hat(te, pooled)
    x_tr = tr.not_completed_count.to_numpy(int)

    r, lr, pval = fit_r(x_tr, n_tr, q_tr)
    p_tr = 1 - q_tr
    disp = float(((x_tr - n_tr * p_tr) ** 2).sum() / (n_tr * p_tr * (1 - p_tr)).sum())
    info = {"pooled_q_train": pooled, "r_hat": r, "lr_stat": lr, "lr_pvalue": pval, "dispersion_ratio_train": disp,
            "n_train": int(len(tr)), "n_test": int(len(te)), "q_missing_test": float(te.hist_avg_completed_issues_3.isna().mean()),
            "mean_q_hat_test": float(q_te.mean()), "mean_completion_test": float(1 - te.carry_ratio.mean())}

    aucs, diffs, cals = [], [], []
    for label, y in (("spillover", "label_spillover"), ("serious_spillover", "label_serious_spillover")):
        yy = te[y].astype(int)

        def work(rng, label=label, y=y, yy=yy):
            s = {"binomial": pd.Series(risk_binomial(n_te, q_te, label), index=te.index),
                 "beta-binomial": pd.Series(risk_betabinom(n_te, q_te, r, label), index=te.index)}
            for name in ("scope", "strict+new"):
                num, proj = PLAN_SETS[name]
                s[name] = pd.Series(fit_predict(PRIMARY_MODEL, num, proj, tr, te, y), index=te.index)
            ua = [{"outcome": label, "model": k, "n": len(te), "auc": safe_auc(yy, v)} for k, v in s.items()]
            ud = [diff_row({"outcome": label}, te.assign(**{y: yy}), y, s, a, b, rng, True)
                  for a, b in (("binomial", "scope"), ("beta-binomial", "scope"), ("strict+new", "binomial"),
                               ("strict+new", "beta-binomial"), ("beta-binomial", "binomial"))]
            uc = [calibration_row(yy, s[k], outcome=label, model=k) for k in ("binomial", "beta-binomial", "strict+new")]
            return ua, ud, uc

        ua, ud, uc = unit(f"binomial_{label}_v1", work)
        aucs += ua; diffs += ud; cals += uc
        print("binomial", label, flush=True)

    # variance check by committed-scope band: observed Var(rho) against binomial and beta-binomial
    bands = []
    t = tr.assign(q=q_tr, n=n_tr, rho=tr.carry_ratio)
    for lo, hi in ((1, 3), (4, 7), (8, 15), (16, 10_000)):
        g = t[(t.n >= lo) & (t.n <= hi)]
        resid = g.rho - (1 - g.q)
        vb = (g.q * (1 - g.q) / g.n).mean()
        bands.append({"n_band": f"{lo}-{hi}" if hi < 10_000 else f"{lo}+", "sprints": len(g),
                      "var_observed": float((resid ** 2).mean()), "var_binomial": float(vb),
                      "var_betabinomial": float((g.q * (1 - g.q) / g.n * (1 + (g.n - 1) * r)).mean())})
    save(pd.DataFrame(aucs), "binomial_auc.csv")
    save(pd.DataFrame(diffs), "binomial_differences.csv")
    save(pd.DataFrame(cals), "binomial_calibration.csv")
    save(pd.DataFrame(bands), "binomial_variance.csv")
    (jr.RESULTS / "binomial.json").write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))
    for name in ("binomial_auc", "binomial_differences", "binomial_calibration", "binomial_variance"):
        print(pd.read_csv(jr.RESULTS / f"{name}.csv").round(4).to_string())


if __name__ == "__main__":
    main()
