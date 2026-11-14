# Red Hat replication cohort: how the projects were chosen (14 Nov 2026)

Source: Red Hat's public Jira (issues.redhat.com, now redhat.atlassian.net, Jira Cloud), read through the
public REST API without logging in. Field ids: Sprint = customfield_10020, Story Points = customfield_10028.

## Rule (written before any label was computed on the pulled data)

1. Public projects with at least 300 issues that were ever in a sprint (97 of 293 projects).
2. At least 100 closed sprints of at most 60 days whose visible issues are at least 80% the project's own.
3. At most 20% of those sprints shared with another project (main project under 80% of the sprint's issues).
4. Story points on at least 50% of the project's sprint issues.
5. Sprint-era issue-number gap no worse than the worst project of the TAWOS cohort (0.68). The gap is the
   share of issue numbers, from the first sprint issue to the latest issue, that an anonymous reader cannot
   see (private, deleted or moved). TAWOS has the same problem: its cohort gaps run from 0.00 to 0.68,
   median 0.23.
6. Not a TAWOS project.

Steps 2 to 4 select 18 projects; step 5 removes RHEL (gap 0.89). Result, 17 projects:
OSPRH, CNV, ACM, RHCLOUD, SRVKP, SAT, NEXUS (repository.jboss.org/nexus, not Sonatype Nexus), GITOPS,
RHDEVDOCS, HMS, JBIDE, RHODS, TRACING, KATA, CLE, FDP, CONSOLE.

## What was seen before the rule was fixed

The screening scan (current Sprint field only, no change log) also printed rough rates of spillover,
serious spillover and late closure per project. The rule above does not use them, and no project was
added or removed because of them. We record it because a reader cannot check it otherwise.

## Known limits

- Private issues are invisible, so a sprint's committed scope can be undercounted. The gap in step 5
  bounds how much of a project is hidden, not how much of each sprint.
- Sprint reports (the board's own record of scope) need a login, so they could not be used as a check.
- Red Hat is one company, though its projects belong to many separate engineering teams.
