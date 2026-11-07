# Full-cohort run (7 Nov 2026, plan version 2)

These are the paper's results. Cohort: 29 TAWOS projects with 30+ usable sprints (three MongoDB projects removed because they overlap the outside set), 4,235 sprints after the loader's cuts, 2,671 of them with committed issues. Outside test: the 10 MariaDB and MongoDB projects. Primary analysis: gradient boosting, per-project time split, one paired difference per outcome and comparison, project-cluster interval (the test) and sprint-level interval (reported beside it). Everything else is secondary.

## Hypotheses on the primary analysis (PLAN.md Section 6)

| Hypothesis | Prediction | Result (cluster interval; sprint interval where it differs) | Holds? |
|---|---|---|---|
| H1, new features (strict+new minus strict) | Positive for scope churn and serious spillover; about zero for the late labels; small positive for spillover | Spillover +0.028 [0.007, 0.047]; serious spillover +0.026 [0.004, 0.050]; scope churn +0.042 [-0.003, 0.084] (sprint [0.007, 0.076]); late closure -0.006 [-0.016, 0.004]; seriously late 0.000 [-0.009, 0.006] | Yes for spillover and serious spillover; the late labels are about zero as predicted; scope churn just misses on the cluster interval. |
| H2, burndown shape (ours minus Worki-style, spillover family) | Positive at 25% and 50% | Spillover +0.118 [0.069, 0.175] and +0.223 [0.145, 0.297]; serious spillover +0.167 [0.104, 0.248] and +0.178 [0.098, 0.251] | Yes, all four. |
| H3, planning context on top of progress counts (ours minus Choetkiertikul subset) | Positive and under 0.05 everywhere | Spillover +0.051 [0.020, 0.083] and +0.046 [0.011, 0.088]; serious spillover +0.066 [0.025, 0.119] and +0.067 [0.017, 0.120]; late closure +0.057 [-0.001, 0.123] and +0.043 [-0.012, 0.112]; seriously late +0.036 and +0.038, both intervals include zero | Direction yes everywhere. Size no: the gain clears zero for the spillover family and is above 0.05 for serious spillover, so planning context adds more than predicted. The development run (8 projects) had suggested it added nothing; the larger cohort overturns that. |
| H4, new labels rankable (strict+new minus scope) | Positive for seriously late and scope churn; about zero for serious spillover | Serious spillover +0.104 [0.036, 0.179]; seriously late +0.033 [-0.015, 0.088] (sprint [0.003, 0.064]); scope churn +0.088 [-0.016, 0.222] (sprint [0.016, 0.157]) | Wrong where it was most specific. Serious spillover, predicted about zero, is the label where history helps most. Seriously late and scope churn are positive only on the sprint-level interval. |

Note on H4: the serious-spillover prediction contradicts the theory section (Section 0a, minimal model), which predicts the opposite, and the theory is what the data support. Both were written on the same day before this run. The paper must report H4 as failed for serious spillover and say that the theory, not the hypothesis, predicted the result.

## The theory's spillover prediction

The binomial model predicts that history-aware features should beat scope-only by more for serious spillover than for plain spillover. Observed (strict minus scope): spillover +0.012, serious spillover +0.079; (strict+new minus scope): +0.040 against +0.104; under leave-one-project-out the AUC gap is 0.05 against 0.17. The prediction holds. On this cohort the median carry ratio is 0.71 (q = 0.29), so a three-issue sprint spills with probability 0.976, and 90.6% of nonempty sprints spill.

## Other results

- **Burndown shape is worse than doing nothing for the late labels.** Worki-style minus scope is negative with intervals below zero for late closure at 25% (-0.102) and seriously late at both checkpoints (-0.095, -0.068), and for spillover at 50% (-0.102). Adding the Worki-style features to ours changes nothing (every ours+worki minus ours difference within ±0.012).
- **Late closure is hard at every stage.** Planning time: scope 0.718, strict+new 0.729. In-sprint at 50%: 0.722. Progress counts barely move it.
- **The spillover family is where the signal is.** Serious spillover goes from 0.775 at planning time to 0.851 at 25% and 0.891 at 50% with our in-sprint set.
- **Sensitivity labels agree with the primary ones.** The median-based serious-spillover label (52% positive): strict+new 0.720 vs scope 0.572, gain from new features +0.032 [0.007, 0.056]. The 50% threshold (73% positive): +0.032 [0.006, 0.061]. Scope churn at 50%: new features +0.054 [0.015, 0.087].
- **Provenance check (sprints with no story-point fallback).** New features: spillover +0.023 [-0.007, 0.051], serious spillover +0.027 [-0.001, 0.053]. Same size as the primary result, interval just touches zero. Not an artefact of fallback values, but not established on that subset alone.
- **Five time-ordered repeats agree with the time split** (spillover strict+new 0.860 ± 0.016, serious spillover 0.769 ± 0.022, late closure 0.728 ± 0.013).
- **Outside projects: no reliable transfer.** Late closure: scope 0.655, strict+new 0.651 (8 projects). Spillover: scope 0.785, strict+new 0.729 (4 projects). Serious spillover: scope 0.592, strict+new 0.573 (9 projects). Seriously late: 0.571 vs 0.617 (8), but the spread across projects is about ±0.2. Scope churn: scope 0.425 (below chance), strict+new 0.593 (5). For the two spillover labels, where history helps most inside TAWOS, it does not help outside. That fits the theory's reading that history features estimate one team's completion rate, which does not carry to another organisation's teams.
- **Decision metrics (Youden from training folds, gradient boosting, strict+new).** Serious spillover sensitivity 0.73 at specificity 0.69; spillover 0.68 at 0.85; late closure 0.62 at 0.76.

## What this means for the paper

The full cohort is stronger than the development run. The defensible claims are: (1) under one leakage-aware protocol, in-sprint progress counts dominate, and burndown-shape features are weaker than committed scope alone for the late labels; (2) planning-time team context adds a small, real gain on top of progress counts for the spillover family (about 0.05 to 0.07 AUC); (3) the four new features add about 0.03 AUC for spillover and serious spillover and nothing for the late labels; (4) serious spillover is the most useful new label: balanced in its median form, clearly rankable beyond scope (+0.10 to +0.15), and behaving as the binomial model predicts; (5) none of the history gains transfer to outside organisations. H4 failed for serious spillover in the direction the theory predicted, and the paper says so.

## Still to do before writing

- Rerun `jr/theory_checks.py` against this cohort (the minimal-model checks currently read the development frame) and update the numbers in `paper/theory.tex` (q = 0.29, three-issue spill probability 0.976, nonempty spillover rate 0.906).
- Calibration beside AUC for the in-sprint models (theory.tex promises it; not yet computed).
