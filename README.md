# Journal study for IEEE Access (2027)

A new study, separate from the two CCECE 2027 papers in the SwEng_202610 repository. This repository is standalone: the change-log reconstruction code of the earlier phases is vendored under `prior/` (only path constants changed), and the eight-project extract plus the ten outside projects are under `data/raw/`. The paper goes to IEEE Access only after the CCECE decision (25 March 2027); if IEEE Access rejects it, the fallback is *Information* (MDPI).

**Read `PLAN.md` first.** It says what the paper is, fixes every label, feature, comparison and hypothesis, names a primary analysis, and logs every change with its reason. Every result is reported whatever it shows.

## What the paper is

A leakage-aware benchmark of sprint-risk feature families on public Jira data, scored on the same sprints under the same protocol:

| Family | Source |
|---|---|
| Committed scope | issues, story points, sprint length |
| Planning-time team history and capacity | Phase 2 strict features |
| In-sprint progress counts | Phase 3 features |
| Burndown shape | Worki-style R1 to R11, after Pérez Castillo et al. (2024), our reading |
| Prior-work iteration features | Choetkiertikul et al. (2018), the subset the data supports |
| Four new planning-time features | carried-in share, issue age, unestimated share, re-estimated share |

Outcomes: late closure and spillover (as before), plus three new labels: serious spillover, seriously late, scope churn. Cohort: every TAWOS project with 30+ usable sprints (after the full export), plus the 10 MariaDB and MongoDB projects as an outside test.

## Folder

| Path | What it is |
|---|---|
| `PLAN.md` | The study plan, primary analysis, hypotheses and a dated log of every change. |
| `data_export/` | SQL for the full TAWOS export (run on your MySQL copy of TAWOS). |
| `jr/data.py` | Builds the planning frame (one row per sprint) and the checkpoint frame (25% and 50%). |
| `jr/worki_features.py` | Worki-style R1 to R11, copied unchanged from the critique repository. |
| `jr/run.py` | Every experiment: planning-time, in-sprint, outside projects. Primary comparisons carry two bootstrap intervals. |
| `jr/theory_checks.py` | Checks every number in the theory section against the result files. |
| `paper/main.tex` | The IEEE Access draft (IEEEtran journal class; still to be moved into the official IEEE Access template). Inputs `theory.tex`, `tables/*.tex` and `fig_primary.pdf`, all generated from the results. `REVIEW.md` lists what a reviewer will still raise. |
| `jr/theory_numbers.py`, `jr/tables.py`, `jr/figures.py` | Theory numbers and calibration, the paper's tables, and its figure, all from the result files. |
| `jr/confirm.py`, `jr/binomial.py` | The confirmation set (19 projects not in the development run) and the binomial and beta-binomial predictors. |
| `jr/paper_checks.py` | Checks every number typed into the paper's text against the result files. |
| `results/dev_8projects/` | Development run on the current 8-project extract, used to test the code. Not the paper's results. |
| `prior/` | Vendored reconstruction code: `src` (Phase 1 loader, planning snapshot, labels), `phase2` (planning-time features, models), `phase3` (in-sprint progress features). |
| `data/raw/tawos_8projects/` | The eight-project TAWOS extract used for development. |
| `data/raw/external/` | The ten MariaDB and MongoDB projects (outside test only). Not in git; rebuild with `data_export/outside/`. See `data/raw/NOTICE.md`. |
| `data/prior_results/` | The four Phase 1 and Phase 4 result files that `jr/theory_checks.py` reads. |
| `data/raw/tawos_all/` | Not in git. The full export you make with `data_export/` (see below). |

## How to run

From this folder:

```
python -m jr.data                 # frames, about 30 seconds on 8 projects
python -m jr.run all              # every experiment, about two hours on 8 projects
```

For the full cohort, first make the export (next section). Then build the two frames the paper also reads (the 8-project frame, which tells `jr.confirm` which projects were used in development, and the uncleaned 29-project frame behind Fig. 2):

```
python -m jr.data                                     (no variables set: data/dev_8projects)
$env:JR_TAWOS_DIR="data/raw/tawos_all"; python -m jr.data   (data/tawos_all, before the measurability check)
```

Then, for the paper's cohort:

```
$env:JR_TAWOS_DIR="data/raw/tawos_all"     (PowerShell, the VS Code default; in cmd: set JR_TAWOS_DIR=data/raw/tawos_all)
$env:JR_EXCLUDE_UNRECORDED="1"             (the paper's cohort: drops the 3 projects that fail the measurability check)
python -m jr.data
python -m jr.run all              # about two hours; resumes where it stopped if interrupted
python -m jr.theory_numbers       # theory numbers and calibration
python -m jr.confirm              # confirmation set, about 20 minutes
python -m jr.binomial             # binomial and beta-binomial predictors
python -m jr.binomial confirm     # the same on the confirmation set
python -m jr.robust               # tuned model, calendar cut, warning budgets, net benefit, about 40 minutes
python -m jr.validate             # reconstruction consistency check and sprint-history coverage
python -m jr.robust history       # main comparisons on projects with good sprint-history coverage
python -m jr.hypotheses_fine      # the 22 hypothesis tests with 10,000 resamples, for the Holm adjustment
python -m jr.tables               # the paper's tables
python -m jr.macros               # every number in the paper's text
python -m jr.build_paper          # assembles paper/main.tex from main_body.tex with the verified references
python -m jr.figures              # the paper's figure
python -m jr.theory_checks        # the theory identities
python -m jr.paper_checks         # every number in the paper's text
```

Then compile `paper/main.tex` (pdflatex twice). Edit `paper/main_body.tex`, not `main.tex`. Results for the paper's cohort are in `results/tawos_all_clean/`; `results/tawos_all/` is the uncleaned 29-project run, kept for comparison.

## Making the full TAWOS export

1. Open your TAWOS database in MySQL Workbench.
2. Run `data_export/01_count_sprints.sql` and save the result as `data_export/tawos_sprint_counts.csv` (done 7 Nov 2026: 36 projects, 32 with 30+ usable sprints, 29 after removing the three that overlap the outside set).
3. Run `data_export/02_export_all_projects.sql`. It writes three files into MySQL's secure_file_priv folder (`C:\ProgramData\MySQL\MySQL Server 8.0\Uploads\` by default). Move them to `data/raw/tawos_all/` as `tawos_sprint.csv`, `tawos_issue.csv` and `tawos_change_log.csv`.

Install with `pip install -r requirements.txt` (pinned to the versions of our run, Python 3.13). Seed 42.

A full step-by-step rebuild manual and an animated explainer of the paper are in `guide/`.
