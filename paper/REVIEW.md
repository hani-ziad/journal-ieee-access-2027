# Review log

## Tenth pass (15 Nov 2026): third feature round, a negative result

Status at sprint start plus twelve further ideas, rule and plans fixed before the runs (PLAN.md section 13). 69 comparisons: 2 cleared zero pooled, none within projects, none in both sources, consistent with chance. SonarSource as a third source was too small to confirm anything (mostly one project, no story points). New subsection "A third round of features" and the conclusion sentence now says two further rounds. Weak points left: the numbers of this round are typed, not macros, and the scripts are scratch copies; the Sonar cohort is inconclusive; many looks at the same data, so any single gain from these rounds would not have been trusted anyway. Overall outlook (my judgment, not computed): borderline, major revision likely, about 40 to 50% eventual acceptance; main risks are the small gains, repeated use of the same data, the unrewritten Introduction and Discussion, and overlap with the CCECE papers.

## Ninth pass (14 Nov 2026, midnight): second feature round, a negative result

Three ideas tried on top of strict+new with a rule fixed beforehand (clear pooled and within projects, in both sources): calendar features, depth and haste, an issue-level model. Nothing met it. Scopus check first: calendar and depth features not found in earlier sprint work; issue-level aggregation is not new (Sprint2Vec's baseline). A first scratch run showed +0.013 for the issue model on TAWOS; it did not survive a change of row order (+0.005 [-0.008, 0.019] in the stored run, 0.001 to 0.008 over five seeds), which the paper states. New subsection "A second round of features" and one conclusion sentence. 114 of 114 claim checks pass.

## Eighth pass (14 Nov 2026, late): two open problems named by Sprint2Vec

1. Cross-project training: the TAWOS to Red Hat transfer test already answers it for tabular features; the transfer paragraph now says so.
2. Effect of time: new analysis `jr/decay.py`, fixed in PLAN.md section 11 before it was run. Red Hat: a three-year-old model loses 0.084 (spillover), 0.058 (serious spillover) and 0.102 (late closure) AUC within project-years, all intervals below zero. TAWOS: same direction, no interval clear; spillover not scorable (2 project-years). So hypothesis H5 (both sources) holds on Red Hat only, and the paper says so. Size-matched control added after the first results (marked as such): spillover -0.067 and late closure -0.053 remain clear, serious spillover -0.027 does not. Weak points left: early Red Hat years hold few projects; 10 project-years for spillover. Scopus query on drift/sliding window for sprint prediction: 3 hits, none on sprint outcomes (titles only). Model ageing and hidden issues are now also named in the abstract (ageing), the contributions (own item) and the conclusion. The new labels and the decision analysis are now in the abstract and the conclusion as well. Abstract 249 words. 104 of 104 claim checks pass.

## Seventh pass (14 Nov 2026): lead with the positive result

The four new planning-time features are the one gain that holds in both sources, within projects and from TAWOS to Red Hat, but the abstract opened with burndown shape. They now lead the abstract, the contributions (new first item) and the conclusion. Literature check: Choetkiertikul et al. (TSE 2018) used iteration counts and issue metadata (priority, description and fix-version changes, readability) but not issue age, carry-in, unestimated or re-estimated shares; Kula et al. (2021, 2022) used team dynamics; Pasuksmit et al. (EMSE 2022) studied story-point changes for single issues, not sprint outcomes, and is now cited. Sprint2Vec (TSE 2025) already uses issue text, so text features would not be new. Abstract 248 words. 84 of 84 claim checks pass.

Sprint2Vec full text read (TSE 51(1), 2025): it predicts at sprint start with a 60:20:20 time-ordered split, reads committed issues from the change log, and its issue-text features beat the same model without text in all ten project and outcome pairs. The Introduction said cited studies suffer from hindsight as a group; it now says Choetkiertikul et al. and Sprint2Vec replay the change log. Related work now states Sprint2Vec's text result and that this paper does not test text. Its feature table (sprint, issue metadata, readability, developer activity) has none of the four new features. Scopus check (Hani's HCT login, five queries) found no study that uses them.

## Sixth pass (14 Nov 2026): independent replication on Red Hat

Weak points from the fifth pass and what was done:
1. Mostly negative results. Fixed by replication: all 22 tests rerun on 17 Red Hat projects (5,507 sprints) chosen by a rule fixed before any label was computed. 15 of 22 hold there (TAWOS 8); 7 hold in both. Paper reframed around what replicates: progress counts beat burndown shape and burndown adds nothing (both sources, within projects too); the four new features help in both sources and transfer TAWOS to Red Hat (serious spillover +0.059 per-project AUC); team history adds nothing within projects in either source.
2. Overlap with CCECE: one paragraph in the Introduction now says what is new. Hani will rework this.
3. "Confirmation set" was not independent: renamed "held-out subset"; Red Hat is the independent test.
4. One data source: Red Hat added as a second source; MariaDB/MongoDB kept as a small outside check, with its limits (4 to 9 testable projects, few story points) stated.
5. AI disclosure: shortened to "write and run the analysis code and draft and edit the text"; add "The author wrote the Introduction and Discussion" once he has.
New threat found and reported for both sources: public Jira hides private issues (missing issue numbers: TAWOS median 23%, Red Hat median 44%; RHEL at 89% excluded). Within table now separates history alone from the new features. 82 claim checks, all pass.

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
