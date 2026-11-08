# Review log

## Fourth pass (8 Nov 2026)

Fixed: title now leads with spillover; reconstruction consistency check (story points 99.7%, sprint field 99.6% where both name a cohort sprint, 79% of in-sprint issues have sprint history) and the main comparisons on the 15 projects with at least 85% history coverage (results hold; planning context gains more there); TAWOS licence (Apache 2.0, research use) noted and outside Jira data no longer redistributed; the two failed labels reported as negative results; Holm adjustment from 10,000 resamples (5 of 22 survive; H4 serious spillover does not, but replicates on the confirmation set and holds under every other variant, which the paper now says); hair-splitting wording removed; two tables moved to the appendix; a sentence on when the measurability rule was fixed.

Still open: practitioner validation; data only to 2020 and open source; IEEE Access template, bios and authorship.

## Third pass (8 Nov 2026)

Fixed:

1. **Data validity.** In three TAWOS projects most sprint issues are closed without a resolution date, so they counted as never finished. A measurability rule (Definition 2 in the theory section) and a per-project check now exclude them; any cut-off between 1% and 56% gives the same three. The paper's cohort is 26 projects, 3,676 sprints. The change moved the new-features result from serious spillover to spillover, so it is reported as a contribution, with the uncleaned results in the robustness table.
2. **Strawman comparisons.** The fair tests are now the headline: burndown shape added to ours (about zero everywhere), planning context added to the Choetkiertikul counts (choet+ctx, new), and our progress counts beyond theirs given the same context.
3. **Weak primary label.** The 30% serious-spillover threshold is called a poor choice in the paper; the median version is reported as secondary.
4. **Statistics.** Holm-adjusted bootstrap p-values over the 22 hypothesis tests; minority-class average precision; tuned model; single calendar cut; the binomial "no learning" result phrased as "cannot be told apart" and also scored on the confirmation set.
5. **So what.** Warning budgets and net benefit (decision-curve form) at four thresholds, with the break-even rule for waiting until mid-sprint; reliability figure.
6. **Polishing.** New title, named hypotheses, carry-ratio figure, robustness and calibration tables in an appendix, every number in the text generated as a macro from the result files (`jr/macros.py`), 48 verbal claims checked (`jr/paper_checks.py`), 45 references all verified.

What a reviewer can still raise:

- Several analysis choices came after the full run (all logged, all reported both ways).
- The prior feature sets are partial versions; the paper says so.
- No practitioner validation.
- Format: ieeeaccess.cls, author bios and photos, authorship.
- Overlap with the CCECE paper (not addressed here by request).

Effect on the CCECE paper: Confluence Cloud is one of its eight projects. Without it, the headline scope-only spillover AUC (logistic regression, time split) moves from 0.885 to 0.903 on the same models and 0.908 when retrained; no conclusion changes. A one-sentence limitation is worth adding before submission.
