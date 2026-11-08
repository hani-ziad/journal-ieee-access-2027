# Review log

## Fifth pass (8 Nov 2026)

Fixed: (1) pooled AUC hid that the history gain is between teams; new within-project analysis (`jr/within.py`, Section 6.5, Table 8) and the abstract, introduction, H4 text, outside-project reading, discussion and conclusion rewritten around it. (2) Section 5.3 said "1,118 test sprints, 734 of them nonempty", but those come from two different splits; Proposition 1 used the all-sprint split (688 nonempty), which is why its 0.885 differed from Table 4's 0.869. Both now explained. (3) "Before any modelling we checked" was false; the check came after the first full run. (4) Proposition 2's "sensitivity falls with prevalence" is not a consequence of the proposition; moved to the text with the actual mechanism. (5) The plan held H4 (no gain for serious spillover) and the binomial reading (a gain) at once; the paper now says so. (6) Three H3 intervals end within 0.001 of zero and flip between 2,000 and 10,000 resamples; flagged. (7) H3's 0.05 ceiling was exceeded in 5 of 8 comparisons; now said. (8) Confirmation set described as overlapping the full cohort. (9) Data statement claimed the full TAWOS extract is in the repository; it is not. (10) AI disclosure made specific. 67 claim checks, all pass.

Still open: practitioner validation; full extract on Zenodo with a DOI; author's own rewrite of the introduction and discussion; the bio wording (see below).

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

## Sync with the CCECE audit (8 Nov 2026, evening)

The CCECE sprint-risk paper was rewritten on 8 Nov as an audit, with a new title, because rebuilding iteration state from the change log is not new (Choetkiertikul et al., TSE 2018). Four edits follow here; no number changed.

- Reference `abusharkh2027` now uses the new title, "Predicting sprint outcomes from reconstructed Jira state: Count baselines and a leakage audit" (`jr/build_paper.py`). The co-authors still have to agree to it.
- Introduction: "Our earlier work rebuilt the board..." now adds "following the change-log reconstruction of iteration state by Choetkiertikul et al. [choet2018]", so the paper no longer reads as if the reconstruction were ours.
- Acknowledgment (`jr/build_access.py`): "first built for" became "code ... was written for", for the same reason.
- `guide/Paper_Explained.html`: one sentence saying the replay idea dates from 2018.
- Related work: the earlier paper's "shuffling added 0.07 AUC" now says part of that gap is drift between time windows, as the CCECE audit found (test windows 27% to 47% late).

`main.tex` and `ieee_access/access_paper.tex` were patched with the same strings instead of rebuilt, so they match what `jr.build_paper` and `jr.build_access` now produce. A stand-in compile of main.tex gives 15 pages with no undefined references. `main_preview.pdf` was not regenerated. The CCECE audit's other findings (within-project scores, count baselines) are already in this paper's Section 6.5 and its burndown and count comparisons, so nothing else needed changing.
