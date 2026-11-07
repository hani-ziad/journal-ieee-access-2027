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
