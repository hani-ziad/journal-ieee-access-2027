# Time-valid re-evaluation (15 Nov 2026, 21:15). Scratch only. Written before any result.
Problem (outside referee report, comment 1, reproduced): the main model pools every project's training split, so 638/734 TAWOS and
1,021/1,536 Red Hat nonempty test sprints start before some training sprint of another project.
Fix tested: rolling origin by calendar quarter. Test sprints = the paper's test split, grouped by the quarter they start in.
For each quarter, train only on the paper's training-split sprints (any project) whose outcome was known before the quarter began
(known = start + sprint length + days late, as in jr/decay.py). A quarter is scored only with >=150 such training sprints and both classes.
Same learner, features, labels, bootstrap (projects, 2,000) as the paper. No tuning.
Reported on the SAME scorable test sprints: paper protocol vs time-valid protocol, pooled AUC and within-project AUC, for
planning (scope, strict, strict+new; spillover, serious spillover, late closure) and in-sprint at 25% and 50% (ours - worki, ours+worki - ours).
Reading fixed now: a headline claim survives if the time-valid interval is still above zero where the paper's was; it is weakened if the
point estimate keeps its sign but the interval now includes zero; it fails if the sign flips or the estimate falls below a third of the paper's.
Everything is reported, whichever way it goes.
