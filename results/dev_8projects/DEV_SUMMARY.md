# Development run on the current 8-project extract (7 Nov 2026, plan version 2)

These numbers test the code. They are not the paper's results, which come from the full TAWOS export (PLAN.md Section 8). Primary analysis: gradient boosting, per-project time split, one paired difference per outcome and comparison, with a project-cluster interval and a sprint-level interval. Everything else is secondary.

## Hypotheses on the primary analysis (PLAN.md Section 6)

| Hypothesis | Prediction | Result | Holds? |
|---|---|---|---|
| H1, new features (strict+new minus strict) | Positive for scope churn and serious spillover; about zero for the late labels; small positive for spillover | Spillover +0.026 [0.002, 0.055]; serious spillover +0.026 [-0.051, 0.149]; scope churn +0.034 [-0.022, 0.089]; late closure +0.002; seriously late +0.001 | Only for spillover. The predicted gains for scope churn and serious spillover are in the right direction but their intervals include zero. |
| H2, burndown shape (ours minus Worki-style, spillover family) | Positive at 25% and 50% | Spillover +0.216 [0.154, 0.274] and +0.167 [0.030, 0.343]; serious spillover +0.082 [-0.010, 0.247] and +0.125 [-0.002, 0.349] | Yes for spillover; serious spillover just misses on the cluster interval, the sprint interval at 50% is positive. |
| H3, planning context on top of progress counts (ours minus Choetkiertikul subset) | Positive and under 0.05 everywhere | Between -0.009 and +0.060; every interval includes zero | Direction mostly as predicted, no interval clears zero. Progress counts carry the in-sprint signal. |
| H4, new labels rankable (strict+new minus scope) | Positive for seriously late and scope churn; about zero for serious spillover | Seriously late +0.061 [-0.036, 0.158] (sprint interval [0.014, 0.107]); scope churn -0.011 [-0.153, 0.162]; serious spillover +0.035 [-0.023, 0.100] | Seriously late only on the sprint-level interval; scope churn no. |

## Other things the run shows

- With scope churn restricted to sprints of 5+ committed issues (1,032 sprints, 64% positive), scope alone ranks it as well as the history features (0.637 vs 0.625). Churn looks like team practice rather than sprint risk: under leave-one-project-out every set is at 0.58 to 0.60.
- The median-based serious-spillover label ("worse than typical", 54% positive) is the most balanced spillover label and the one where history helps most under leave-one-project-out: 0.690 with the new features against 0.605 for scope only.
- Provenance check (sprints with no story-point fallback, n = 212): the spillover gain from the new features is +0.044 [-0.007, 0.065], so the primary +0.026 is not an artefact of fallback values, but it is also not established there.
- Outside projects: late closure reproduces Phase 4 (0.620 ± 0.090, 8 projects); serious spillover is testable in 9 projects but sits at 0.54 to 0.57, near chance; scope churn is testable in 5 and scope-only scores 0.38, below chance.
- Five time-ordered repeats agree with the time split within their spread.
- Theory checks (`python -m jr.theory_checks`): all 15 pass against the Phase 1, Phase 4 and development-run files.

## What this means for the paper, if the full cohort repeats it

The defensible claims are: (1) under one leakage-aware protocol, in-sprint progress counts dominate every other family, and burndown-shape features are clearly weaker for spillover and near chance for the late labels; (2) planning-time team history adds little once progress counts are in; (3) the four new features add about 0.03 AUC for spillover and nothing elsewhere; (4) of the three new labels, only the median-based serious-spillover label is both balanced and rankable, and only within TAWOS. The paper's abstract will say (3) and (4) in those words.
