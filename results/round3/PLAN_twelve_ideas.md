# Round 4 plan (15 Nov 2026, ~00:40). Scratch only. Written before any round-4 result.
Base: strict+new (the paper's best planning set). Same labels, per-project 70/30 time split, project-cluster bootstrap (2,000).
Outcomes: spillover, serious spillover, late closure. Cohorts: TAWOS (26), Red Hat (17), then a third public Jira cohort.
Ten ideas, fixed now (parameters fixed too, no tuning on test data):
 1 Recency weighting: training sprints weighted 0.5^(age_years/2) where age is measured back from the newest training sprint of the whole training set.
 2 Pooled training: train on TAWOS+Red Hat(+third) training splits together, source flag added, score each cohort's test split.
 3 Team-relative features: committed count and points divided by the median of the team's previous 5 sprints (known at planning), and their z-scores.
 4 Hidden-issue share per sprint: share of issue numbers missing between the lowest and highest committed issue key.
 5 Issue-size distribution: largest issue share of points, Gini of points, share of issues >8 points, mean points of estimated issues.
 6 Dynamics: change in committed count vs previous sprint; std of the team's last 5 spillover rates (sprints whose planned end is before this start).
 7 Ensemble: mean rank of gradient boosting and logistic regression on the same features.
 8 Continuous target: gradient-boosting regressor on carry_ratio (spillover, serious spillover) or capped late days (late closure), used as the risk score.
 9 Maturity: sprint ordinal within the project and days since the project's first sprint.
10 Tuned model: depth in {2,3,4}, learning rate in {0.03,0.05,0.1}, 100-300 iterations, chosen by the last 20% of each project's TRAINING sprints (time order), then refit on all training.
Success rule: (set - base) 95% interval above zero both pooled and within projects, in BOTH TAWOS and Red Hat; then confirmed (point estimate > 0 and interval not below zero) on the third cohort.
With ten ideas tried, a pass by chance is possible; the third cohort is the guard. Everything is reported, failures too.
Third cohort rule (fixed before any label): public Jira, anonymous REST, not TAWOS/Red Hat/MariaDB/MongoDB; projects with >=300 issues ever in a sprint, >=60 closed sprints of <=60 days, story points on >=50% of sprint issues, home-board sprints >=80% own issues.

AMENDMENT (15 Nov 2026, ~01:15, before any third-cohort label was computed): OpenMRS has no story points and fewer than 50 closed sprints per project;
SonarSource Cloud (sonarsource.atlassian.net) has story points on <6% of sprint issues. The story-point rule is dropped for the third cohort: its
base set is strict+new WITHOUT the story-point columns (as the earlier external transfer did). Rule for the third cohort: >=50 closed sprints of <=60 days,
>=80 issues ever in a sprint, home-board sprints >=80% own issues. Selected: SONAR, ECHOES, SLCORE, SLI, SLVS, SLVSCODE, SLE, SLLS, PLUGINAPI.

RESULT (15 Nov 2026, 01:10). Twelve ideas tried (11 age distribution and 12 compact set added during the run, same rule). None met the rule.
Of 69 idea x outcome x source cells, 2 cleared zero pooled, 0 within projects, 0 in both sources. Idea 4 was run on TAWOS only (null), so not pulled for Red Hat.
Third cohort (SonarSource, no story points, 8 projects, 577 sprints, mostly one project): the four features +0.016 / +0.046 / +0.006 AUC, all intervals include zero. Inconclusive.
