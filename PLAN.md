# Journal study plan (IEEE Access)

This folder is a new study. It reuses the reconstruction code of Phases 1 to 3 but not their results, and it is not part of the two CCECE 2027 papers. The journal paper will be submitted only after the CCECE decision (25 March 2027).

Version 1 of this plan was written on 7 November 2026 before any model in this folder was run. Version 2 (same day) followed a reviewer-style pass over version 1 and the development run; every change is in the deviations log at the end, with the reason. Every result is reported, including the ones that do not support a hypothesis.

## 0. What the paper is

A leakage-aware benchmark of sprint-risk feature families on public Jira data: committed scope, planning-time team history, in-sprint progress counts, burndown shape, and the feature sets of two prior studies, all scored on the same sprints under the same protocol, on the largest public sprint cohort with a reconstructed sprint start, plus ten outside projects. Three new outcome labels and four new planning-time features are one section of that benchmark, reported whatever they show. The paper does not claim a new prediction method.

## 0a. Theory section

The paper has a formal section (`paper/theory.tex`) that defines the event log, the replayed sprint state and the outcomes; states the admissibility condition for a feature (a function of the events up to the prediction time); and derives three results that the experiments test: (i) ROC-AUC on a population with structural negatives equals a prevalence-weighted mix, which accounts for the 0.986 vs 0.852 gap; (ii) Youden's threshold implies a miss-to-false-alarm cost ratio of (1 - prevalence)/prevalence, which is why a fitted threshold does not travel between projects; (iii) a per-issue completion model under which the "any spillover" label is driven by scope and the "serious spillover" label by the team's completion rate. Every number in that section is checked by `jr/theory_checks.py`.

## 1. Data

**TAWOS, all usable projects.** Every TAWOS project with at least 30 usable sprints, where usable is exactly the Phase 1 loader rule: state CLOSED, start, end and completion dates present, end and completion not before start. Then the same cleaning as before (each project's first sprint dropped as a cold start). Projects that pass the rule are all used; none is picked by hand. The export queries are in `data_export/`. Until the full export exists, the code runs on the current eight-project extract as a development run only (Section 8).

**Outside projects.** MariaDB (MaxScale, ColumnStore) and MongoDB (eight projects), already converted to the TAWOS layout (Phase 4 of the course work), kept in `data/raw/external`. They are used only for testing, never for training or tuning.

**No hindsight.** Every feature uses only events time-stamped at or before the prediction time. Issue type, priority and assignee are excluded everywhere, because the export holds only their final values.

**Known hindsight risk, carried over from the CCECE paper.** When an issue has no recorded story-point change, its planning-time points are taken from the static export. The data build records, per sprint, the share of committed issues affected (`sp_fallback_share`). The primary planning-time comparisons for the spillover-family outcomes are repeated on sprints with no such fallback, and the gap is reported.

## 2. Outcomes

Existing (kept for continuity):

| Label | Definition | Population |
|---|---|---|
| Late closure | Jira completion more than 1 day after the planned end | All sprints |
| Spillover | At least one committed issue unresolved at the planned end | Sprints with committed work |

New (defined here for this study):

| Label | Definition | Population | Sensitivity |
|---|---|---|---|
| Serious spillover | Share of committed issues unresolved at the planned end is 30% or more | Sprints with committed work | 20%, 50%, and above the training-set median carry ratio |
| Seriously late | Jira completion more than 3 days after the planned end | All sprints | more than 7 days |
| Scope churn | Issues added after the start and still in the sprint at the planned end, divided by the committed issues, is 30% or more | Sprints with at least 5 committed issues | 50% |

What each new label is for, and its known weakness, stated up front: serious spillover asks "how much" rather than "any", but the median sprint in these projects leaves 75% of its committed issues unfinished, so at 30% the label is still 88% positive and only partly fixes the imbalance of plain spillover; the median-based sensitivity label ("worse than typical", 54% positive) is the balanced alternative and is reported beside it; seriously late is still an administrative event (when the sprint was closed in Jira), only a larger one; scope churn is a planning outcome teams can act on, but it may reflect team practice more than sprint risk, which leave-one-project-out testing will show. Scope churn is predicted at planning time only, because during the sprint the additions so far give most of the answer away.

## 3. Features

**Existing:** the Phase 2 strict planning features (scope, sprint length, parallel sprints, finished-sprint history, capacity, past lateness) and the Phase 3 progress features at 25% and 50% of the planned duration.

**New (defined here for this study), all at sprint start:**

| Feature | Definition |
|---|---|
| `carried_in_share` | Share of committed issues that had been a member of another sprint before this sprint's start, according to the change log. Issues with no sprint history in the change log count as not carried in (an undercount where the change log is incomplete). |
| `log_median_issue_age` | log(1 + median days from issue creation to sprint start) over committed issues. The log is a monotone transform for the sake of the logistic regression; it does not affect the tree models. |
| `unestimated_share` | Share of committed issues with no story points at sprint start. Teams differ in whether they estimate at all, so part of this feature is team identity; leave-one-project-out testing shows how much. |
| `reestimated_share` | Share of committed issues whose story points were changed from an existing value before sprint start (setting a first estimate does not count). On the development run it is zero for 95% of sprints and is expected to add nothing; it is kept and reported. |

**Prior work, implemented on the same sprints for a head-to-head:**

- **Worki-style burndown features** (after Pérez Castillo et al., *Information* 2024): R1 to R11 read off the daily burndown up to the prediction time, using our reading of their verbal definitions and our thresholds, on issue counts rather than hours. This is a burndown-shape feature family in their spirit, not their method, and the paper will say so. Their study graded finished sprints; here the features are scored in-sprint, which is a different task. The comparison is meaningful for the spillover family (burndown shape speaks to unfinished work) and is reported for the late family only as a descriptive result, since a burndown shape has no reason to predict when a sprint is closed in Jira.
- **Choetkiertikul et al. (TSE 2018), iteration features the export supports:** iteration duration, issues and story points at start, issues and story points added and removed since the start, done and to-do issues and story points at the prediction time. Not available, so left out: in-progress counts (no status history), Scrum master and team size (assignee is a final value), and all issue-level features. At planning time their supported set reduces to duration, issues and points at start, which is our scope-only baseline; this is reported as such. Because the subset is incomplete, the comparison does not rank the two studies; it measures what planning-time team history and capacity add on top of in-sprint progress counts.

## 4. Feature sets compared

| Name | Contents | When |
|---|---|---|
| scope | committed issues, story points, sprint length | planning, in-sprint |
| strict | Phase 2 strict set + project | planning |
| strict+new | strict + the four new features | planning |
| choet | Choetkiertikul supported subset | in-sprint |
| worki | R1 to R11 | in-sprint |
| ours | strict + new + Phase 3 progress | in-sprint |
| ours+worki | ours + R1 to R11 | in-sprint |

In-sprint comparisons use sprints with committed work for every outcome, late closure included, because the burndown features need a non-empty sprint and all feature sets must be scored on the same sprints. The planning-time late-closure population (all sprints) therefore differs from the in-sprint one; both tables say which population they use.

## 5. Models and protocols

- Models: logistic regression (balanced), random forest, gradient boosting, with the Phase 2 settings. No hyperparameter search. Seed 42.
- Protocols: (a) per-project time split, first 70% of each project for training; (b) leave-one-project-out with the project feature removed; (c) five time-ordered repeats, training on the first 40, 50, 60, 70 and 80% and testing on the next 20%; (d) outside projects, trained on all TAWOS sprints, without the project feature and without story-point-based features (MariaDB records no story points).
- Metric: ROC-AUC. Decision metrics (sensitivity, specificity, F1) at a threshold fixed on training data only (Youden's J on out-of-fold training predictions).
- Uncertainty: 2,000 bootstrap resamples for every paired difference. Resampling projects as whole units is the main interval; with eight projects it is coarse, so the primary comparisons also report a sprint-level bootstrap interval, and the paper reads the two together.

## 6. Primary analysis and hypotheses

**Primary analysis.** Gradient boosting on the per-project time split. One paired AUC difference per outcome and comparison, with both intervals. These are the only results treated as tests. Every other model, protocol and checkpoint is secondary: reported in full, read as a pattern, with no claim of significance and no correction for multiple comparisons.

**Hypotheses, one prediction per outcome, judged on the primary analysis.**

- **H1 (new features).** strict+new minus strict, planning time. Predicted direction: positive for scope churn and serious spillover; about zero for late closure and seriously late; positive but small for spillover. A hypothesis "holds" only where the project-cluster interval is above zero.
- **H2 (burndown shape).** ours minus worki at 25% and 50%, spillover family only. Predicted: positive at both checkpoints. The late family is reported, not tested.
- **H3 (planning context on top of progress counts).** ours minus choet at 25% and 50%. Predicted: positive and small (under 0.05) for every outcome. This tests whether planning-time context adds to progress counts; it does not rank the two studies.
- **H4 (new labels are rankable).** strict+new minus scope, planning time. Predicted: positive for seriously late and scope churn; about zero for serious spillover.

Expectation, written now so it cannot move later: spillover will stay mostly explained by committed scope, so H1 is most likely to fail for spillover and is more plausible for late closure and scope churn.

## 7. Reporting rule

Every label, feature set, model and protocol above appears in the results files and in the paper's tables or supplement, whatever the outcome. Thresholds are not changed after seeing results; the sensitivity thresholds are the only alternatives reported, and they run through the same models and protocols as the main labels.

## 8. Development run

The code is first run on the current eight-project extract to test it. Those numbers are marked as a development run and are not the paper's results. The paper's results come from the full TAWOS export with the cohort rule above. If the full export cannot be obtained, the paper will say so and report the eight-project cohort.

## 9. Still missing, and not fixable with this data

- **Practitioner relevance.** No one from practice has rated whether flagged sprints were real trouble. Planned as a small follow-up: 10 or more Scrum Masters rate 30 flagged and 30 unflagged sprints from the outside projects, blind to the model, and agreement with the labels is reported. If it cannot be done before submission, the limitation is stated plainly.
- **Issue text.** Titles and descriptions are not in the export.

## 10. Deviations log

| Date | Change | Reason |
|---|---|---|
| 7 Nov 2026 | In-sprint comparisons (Section 4) use sprints with committed work for every outcome, late closure included. | The Worki features need a non-empty burndown; all feature sets must be scored on the same sprints. Clarification, written before the in-sprint run. |
| 7 Nov 2026 | Choetkiertikul "done" and "to-do" counts cover issues in the sprint at the prediction time (committed and added); a committed issue moved out of the sprint counts as removed, not done. | Their definition counts the iteration's issues at prediction time. Phase 3's own done count (committed issues resolved, wherever they are) is kept separately. Written before any run. |
| 7 Nov 2026 | Base rates seen while testing the data build: serious spillover 88% positive, scope churn 64%. Thresholds unchanged. | Recorded so it is clear the thresholds were not moved after seeing these rates. |
| 7 Nov 2026 (v2) | Paper reframed as a benchmark of feature families (Section 0); new labels and features demoted to one section. | Development run: the new features add 0.00 to 0.03 AUC; the head-to-head is the stronger evidence. Framing change, no change to what is run. |
| 7 Nov 2026 (v2) | Hypotheses rewritten as one prediction per outcome on a declared primary analysis (Section 6); sprint-level bootstrap added beside the project-cluster one. | Version 1's "at least one outcome" wording could not fail, and 48 uncorrected intervals per comparison were being read as a tally. Made after the development run, before the full-cohort run. |
| 7 Nov 2026 (v2) | Scope churn population restricted to sprints with at least 5 committed issues. | With the ratio defined over committed issues, a one-issue sprint that gains one issue is 100% churn; small sprints dominated the positives on the development run. Made after seeing the development run. |
| 7 Nov 2026 (v2) | Median issue age entered as log(1 + days). | Tail to 3,213 days on the development run; monotone transform for the logistic regression only. |
| 7 Nov 2026 (v2) | `sp_fallback_share` recorded per sprint; primary spillover-family comparisons repeated on sprints without story-point fallback (Section 1). | Carries over the CCECE paper's provenance caveat; the new unestimated-share feature and the Choetkiertikul point counts both depend on planning-time story points. |
| 7 Nov 2026 (v2) | Worki comparison renamed "Worki-style burndown features" and limited to the spillover family as a test (Section 3). | The features are our reading of underspecified definitions on a different unit (issues, not hours) and a different task (in-sprint, not finished sprints). The late family is reported descriptively. |
| 7 Nov 2026 (v2) | Choetkiertikul comparison reworded as "what planning context adds to progress counts" (Section 3, H3). | Only the supported subset is implemented, so the comparison cannot rank the two studies. Development run: their subset was nearly as good as ours. |
| 7 Nov 2026 (v2) | Sensitivity thresholds run through all three models and both protocols. | Version 1 ran them with one model on one split. |
| 7 Nov 2026 (v2) | Sensitivity label added: carry ratio above the training-set median ("worse than typical"). | The median carry ratio is 0.75, so the fixed 30% and 50% thresholds leave the label 80 to 88% positive. The 30% primary threshold is unchanged; the median label is reported beside it. Made after seeing the development run. |
| 7 Nov 2026 (v2) | Theory section added (Section 0a) with three derived, checkable results. | A journal paper needs the formal setting stated once; the three propositions turn observations from the CCECE paper into predictions the new cohort can test. |
| 7 Nov 2026 (v2) | SQL export rule aligned with the loader (end date not before start, as well as completion). | The two rules differed. |
| 7 Nov 2026 (v2) | Three TAWOS projects excluded from the cohort: MongoDB Compass, the Mongo C++ driver and the Mongo Java driver. | The full TAWOS count (data_export/tawos_sprint_counts.csv: 36 projects, 32 with 30+ usable sprints) showed these three are also in the outside test set pulled from MongoDB's live Jira. Keeping them in training would make the outside test partly a test on the same teams. Cohort is therefore 29 projects (4,347 sprints of all states before the loader's cuts). |
| 7 Nov 2026 (v2) | Export written server-side with SELECT ... INTO OUTFILE instead of the result-grid export. | The grid export was unreliable above a few hundred thousand rows (the eight-project issue file had to be exported in parts). NULL is still written as the word NULL. |
| 7 Nov 2026 (v2) | Two custom change-log fields dropped from the full export: "Actual Story Points" (Spring XD, 541 events) and "Story Points (Obsolete)" (Moodle, 146 events). | The loader treats any field containing "story" and "point" as estimate history. "Actual Story Points" is recorded after the work and is not the planning estimate; the obsolete field is a retired duplicate. Applied in the SQL and to the exported file. |
| 7 Nov 2026 (v2) | Experiments made resumable: each (outcome, model) unit is cached, and each unit seeds its own bootstrap generator from its name. | The full-cohort run takes hours and the cloud session cannot keep one process alive that long. Point estimates are unchanged; bootstrap intervals now come from per-unit seeds instead of one sequential stream, so the development-run intervals will differ slightly if rerun. |
| 7 Nov 2026 (v2) | Theory numbers recomputed on the full cohort (`jr/theory_numbers.py`): Proposition 1 on this study's own time split (strict+new, gradient boosting), Proposition 2 in the outside-project setting of `jr.run external`. | The first draft checked them against the CCECE Phase 1 and Phase 4 files. The journal should stand on its own data. The old checks are replaced by `jr/theory_checks.py` (identities) and `jr/paper_checks.py` (every number in the running text). |
| 7 Nov 2026 (v2) | Calibration added for the primary models (`results/tawos_all/calibration.csv`): Brier score, its prevalence reference, ten-bin ECE, calibration slope and intercept. | The theory section's warning rule needs calibrated probabilities. Not a test; reported in full. |
| 7 Nov 2026 (v2) | Confirmation set added after the full run: every hypothesis comparison repeated on the 21 projects not in the development run, trained and tested on those projects only (`jr/confirm.py`). | The hypotheses were written after a development run on eight projects holding 2,602 of the 4,235 sprints; the other 21 had not been looked at. Added after seeing the full-cohort results, so it is a robustness analysis, not a pre-registered one; its rule (21 projects, same model, same split, same intervals) leaves no room for choice. |
| 7 Nov 2026 (v2) | Binomial and beta-binomial predictors added (`jr/binomial.py`): q from the pooled completion rate of the last three finished sprints known at the start; beta-binomial correlation r fitted on training sprints by maximum likelihood. Proposition 3 (overdispersion) added to the theory section. | Turns the minimal model from a reading aid into a tested predictor, and tests its independence assumption. Added after the full run; reported in full whatever it showed. |
| 8 Nov 2026 (v3, after the second strict review) | **Measurability check; primary cohort changed.** Projects where more than 10% of sprint issues are closed without a resolution date are excluded (`jr/data.py: recording_check`, `JR_EXCLUDE_UNRECORDED=1`, results in `results/tawos_all_clean/`). Three projects are excluded: Atlassian Jira Cloud (70%), Atlassian Confluence Cloud (57%), Apache MXNet (56%); every other project is at or below 0.7%, and all ten outside projects pass. | The label rule counts an issue without a resolution date as never finished, so in those projects most sprints appeared to finish nothing. Found during review, after the full run. The uncleaned 29-project results stay in `results/tawos_all/` and are reported in the paper's robustness table. The change moved the new-features result from serious spillover to spillover. |
| 8 Nov 2026 (v3) | In-sprint set `choet+ctx` (Choetkiertikul counts plus strict+new and project) and comparisons choet+ctx minus choet and ours minus choet+ctx added. | Ours and choet differ in both planning context and progress counts; the new set separates them. H2's fair counterpart is ours+worki minus ours, already computed. |
| 8 Nov 2026 (v3) | Bootstrap p-values (project level) and Holm adjustment over the 22 hypothesis comparisons; average precision for the minority class. | Multiple-testing and class-imbalance concerns raised in review. |
| 8 Nov 2026 (v3) | Robustness (`jr/robust.py`): tuned gradient boosting (grid chosen on a time-ordered validation slice), a single calendar cut, the main comparisons without the two projects whose sprints mostly finish nothing (Appcelerator Daemon, Hyperledger Indy Node), warning budgets, net benefit at four thresholds, reliability bins. Binomial predictor also scored on the confirmation set. | Review: untuned models, per-project split, practical meaning of AUC gains, untested warning rule. |
| 8 Nov 2026 (v3) | Paper retitled; hypotheses named in the text; the 30% serious-spillover threshold described as a poor choice; claims about the median-based label marked as secondary; outside results described as no evidence of transfer. | Review. |
| 8 Nov 2026 (v4, third strict review) | Reconstruction consistency check (`jr/validate.py`): replaying each issue's log forward must end in the exported values; sprint-history coverage per project; main comparisons repeated on projects with at least 85% coverage (`python -m jr.robust history`). | The reconstruction had never been checked. There is no ground truth for the board at sprint start, so consistency with the export is the check available. |
| 8 Nov 2026 (v4) | Hypothesis p-values from 10,000 project-level resamples (`jr/hypotheses_fine.py`) for the Holm adjustment; intervals unchanged (2,000). | With 2,000 resamples the smallest Holm-adjusted p was about 0.011. |
| 8 Nov 2026 (v4) | Title now leads with spillover; seriously late and scope churn reported as negative results; outside-project Jira data no longer redistributed (scripts included in `data_export/outside/`); TAWOS licence noted (Apache 2.0, research use). | Review: title promised late closure, which the paper finds unpredictable; data terms. |
| 8 Nov 2026 (v5, fifth strict review) | **Within-project AUC** (`jr/within.py`, results in `within_project.csv` and `within_differences.csv`): the main comparisons rescored using only pairs of sprints from the same project, same models, split and test sprints, project-level bootstrap. New paper section and table. | Every AUC was pooled over 26 projects, so it also rewarded telling teams apart, while a team only ranks its own sprints. Added after the full run. Result: the in-sprint findings and the new-features gain for spillover hold within projects; the history-over-scope gain for serious spillover falls from 0.088 to 0.015 (interval includes zero), and for late closure history ranks a team's own sprints worse than scope. The abstract, introduction and discussion now lead with this. |
| 8 Nov 2026 (v5) | Text corrections: the measurability check is now dated after the first full run (the paper said "before any modelling"); the two time splits (all sprints for the late labels, nonempty sprints for the spillover labels) are described separately, and Proposition 1's numbers are said to come from the all-sprint split (688 nonempty test sprints, not the 734 of the nonempty split); Proposition 2 no longer claims as a theorem that sensitivity falls with prevalence; Proposition 3 is marked as added after the full run; H4 and the binomial reading, which disagreed in this plan, are reported as disagreeing; the three H3 intervals that end within 0.001 of zero are flagged as unstable; the confirmation set is described as not independent of the full cohort; the data statement no longer says the full TAWOS extract is in the repository; "added after review" became "added after the full run". | Errors and overclaims a reviewer could check against this repository. |
| 8 Nov 2026 (v5) | IEEE Access acknowledgment rewritten: names the AI system, what it did (code, experiments, drafting, review) and what the author did; credits the co-authors of the earlier reconstruction. | IEEE requires the AI system, sections and level of use to be disclosed; the earlier sentence understated it. |
| 14 Nov 2026 (v6) | **Second source: Red Hat public Jira** (redhat.atlassian.net, anonymous REST). Selection rule fixed before any label was computed (`data_export/redhat/SELECTION.md`): 17 projects, 5,507 sprints, May 2014 to November 2026. Pull: `data_export/redhat/pull_jira_cloud.js`; conversion: `convert_jira.py --all-boards`; everything else unchanged. New modules: `jr/replicate.py` (all 22 hypothesis tests rerun on Red Hat, trained and tested there; and `transfer`: trained on TAWOS, scored per Red Hat project with story points kept), `jr/visibility.py` (hidden-issue gap per project, both sources). | The 19-project held-out subset is part of the TAWOS cohort, so it is not an independent replication (review, 14 Nov). The MariaDB/MongoDB outside set was too small (4 to 9 testable projects) and mostly lacks story points. Added after the full run; the screening scan printed rough label rates before the rule was fixed, and the rule does not use them. Result: 15 of 22 tests hold on Red Hat (TAWOS 8); progress counts beat burndown shape and the new features help in both sources and transfer TAWOS to Red Hat; team history adds nothing within projects in either source. |
| 14 Nov 2026 (v6) | "Confirmation set" renamed "held-out subset" in the paper. Title now says "Two-Source Benchmark". Within-project table now separates history alone (strict - scope) from the new features. AI disclosure shortened to: Claude wrote and ran the analysis code and drafted and edited the text; the author set the question, approved the design and changes, and checked everything. | The old "history over scope" rows mixed history with the new features, which hides that the Red Hat gain is the new features. |
| 14 Nov 2026 (v6) | Hidden issues: public Jira hides private issues; the share of missing issue numbers over the sprint era is 0 to 68% in the TAWOS cohort (median 23%) and 5 to 66% in Red Hat (median 44%); RHEL (89%) excluded by the selection rule. Reported as a threat for both sources. | Found while choosing the Red Hat projects; it applies to TAWOS as much as to Red Hat. |
| 14 Nov 2026 (v7) | Framing only, no analysis changed: the four new planning-time features (carried-in share, median issue age, unestimated share, re-estimated share) now lead the abstract, contributions and conclusion, since they are the one positive result that holds in both sources, within projects and in transfer. A literature check found no earlier sprint-outcome study that used them; Pasuksmit et al. (EMSE 2022, story-point changes after sprint assignment) added to related work. Two claim checks added (84 in total). | Raise the paper's main positive result; close a related-work gap |
| 14 Nov 2026 (v7b) | After reading Sprint2Vec in full: Introduction no longer implies every cited study ignores hindsight (Choetkiertikul et al. and Sprint2Vec replay the change log); related work states that Sprint2Vec's text features helped in all its project and outcome pairs, so issue text is out of scope here. No analysis changed. | Accuracy of the related-work claims |

## 11. Model ageing (added 14 Nov 2026, written before any result of this analysis was computed)

Sprint2Vec (TSE 2025) names two open problems: cross-project training for teams with no history, and the effect of time, to be studied with a sliding window. Our transfer test answers the first. This section fixes the test for the second. Only the number of sprints per calendar year in each source was looked at before writing it (to choose test years with enough data); no outcome or score was.

- **Question.** How much ranking quality does a planning-time model lose when it is one, two or three years old?
- **Data.** Both cohorts, separately. Test years: 2017, 2018, 2019 for TAWOS; 2023, 2024, 2025, 2026 for Red Hat. Outcomes: spillover, serious spillover, late closure, with their usual populations.
- **Design.** For a test year Y and an age k in {0, 1, 2, 3}, the model is trained on every sprint whose outcome was known before 1 January of year Y - k (start + length + days late, the rule of the calendar-cut check) and scored on the sprints that start in year Y. The test sprints are the same for every k, so ages are compared on identical sprints. Gradient boosting, no project feature (a stale model may never have seen a project). Feature sets: scope, strict, strict+new. A cell is dropped if its training set has fewer than 200 sprints.
- **Score.** AUC inside each project and test year (at least five sprints in each class), averaged with pair weights as in the within-project analysis. Loss of an aged model = AUC at age k minus AUC at age 0 on the same project-years. 95% intervals from 2,000 resamples of projects.
- **Hypothesis H5.** With strict+new, the three-year-old model ranks spillover and serious spillover worse than the fresh one (interval below zero) in both sources. Secondary, not tested formally: the loss grows with age; scope alone ages less than strict+new; the gain of the new features (strict+new minus strict) is still positive at age 3.
- **Reporting.** Whatever comes out is reported, including no loss. Code: `jr/decay.py`; results: `results/<cohort>/decay_*.csv`.
- **Added after the first results (14 Nov 2026).** An aged model also has less training data (for Red Hat, 905 sprints at age 0 against 209 at age 3), so the loss mixes staleness with training size. Control: a fresh model trained on the same number of sprints as the aged one, taken as the most recent sprints known before the test year. Loss against that model isolates staleness. H5 is still judged on the pre-registered comparison; the control is reported beside it.

## 12. Second feature round (added 14 Nov 2026, written before any result of this analysis was computed)

Same data, labels, per-project 70/30 time split, gradient boosting and project-cluster bootstrap as the paper.
Base set: strict+new. Outcomes: spillover, serious spillover, late closure. Both sources, TAWOS first.

A. Calendar (aimed at late closure): planned end on Friday/Saturday/Sunday (UTC), weekday of planned end,
   weekday of start, sprint spans 24 Dec to 1 Jan.
B. Depth and haste (aimed at spillover labels): mean and max number of earlier sprints a committed issue
   has been in, share of committed issues with two or more earlier sprints, share of committed issues that
   entered this sprint in the last 24 hours before its start.
C. Issue-level model: gradient boosting per committed issue (age, earlier sprints, points, unestimated,
   re-estimated, hours in sprint before start, committed count, sprint length), target "resolved by the
   planned end". Sprint scores: 1 - prod(p) and mean(1 - p). Reported alone and added to the base set
   (out-of-fold on training sprints, 5 folds grouped by sprint).
D. By-product of C: AUC of the issue model inside each test sprint (which issue is left over), against
   story points alone and age alone.

Success rule: a set "helps" an outcome if (set - base) has a 95% interval above zero pooled AND within
projects. Claimed only if it holds in both sources. Everything is reported, including failures.
Issue type and priority are not used: the exports hold only their final values.

- **Result.** Nothing met the rule. Calendar: late closure on TAWOS pooled only. Depth and haste: serious spillover on Red Hat only. Issue-level model: not clear in either source.
- **Added after the first run.** The first scratch run showed +0.013 for the issue-level model on TAWOS serious spillover. Rerunning with the rows in a different order gave +0.006, so the result depended on row order (fold assignment). The issue table is now sorted and read back from file, and the issue-model step is repeated with five seeds; the spread is in `round2_issue_seeds.csv`. Code: `jr/round2.py`; results: `results/<cohort>/round2_*.csv`; issue table: `data/<cohort>/issue_frame.csv`.


## 13. Third feature round (added 15 Nov 2026, plans fixed before results: results/round3/PLAN_status.md, PLAN_twelve_ideas.md)

Same protocol as section 12. Rule: gain counts only if its interval is above zero pooled and within projects in both sources, then confirmed on a third source.
- Issue status at sprint start on Red Hat (active, in review, never touched), rebuilt from the status log. Result: within-project change at most 0.01, every interval includes zero.
- Twelve ideas on strict+new: recency weighting, pooled training, team-relative size, hidden-issue share (TAWOS only), size distribution, dynamics, ensemble, continuous target, maturity, tuned model, age distribution, compact set (11 and 12 added during the run, same rule).
- Result: 69 idea x label x source comparisons; 2 cleared zero pooled, 0 within projects, 0 in both sources. Compact set within 0.025 AUC of the full set in every cell.
- Third source: SonarSource Cloud, 9 projects chosen by a rule fixed before labels (amended once before any label: story-point rule dropped because story points cover under 6% of issues). Mostly one project; four new features +0.016 / +0.046 / +0.006, all intervals include zero. Inconclusive, not a confirmation.
- Numbers for this round are typed in Section 5.4 of the paper and checked in jr/paper_checks.py, not generated as macros (scratch runs; see jr/round3/README.md).
