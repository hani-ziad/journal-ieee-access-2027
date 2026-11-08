"""Journal study (IEEE Access): a leakage-aware benchmark of sprint-risk feature families.

This repository is standalone. The change-log reconstruction code of the earlier
course phases is vendored under ``prior/`` (``src`` = Phase 1, ``phase2``, ``phase3``)
with only their path constants changed. See PLAN.md for every definition, fixed
before any run.

The TAWOS data folder is chosen with the environment variable JR_TAWOS_DIR:
  unset                 data/raw/tawos_8projects (the eight-project extract; development run only)
  data/raw/tawos_all    the full export made with data_export/02_export_all_projects.sql
Results go to results/<cohort name>/ and frames to data/<cohort name>/.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 42

_prior = str(ROOT / "prior")
if _prior not in sys.path:
    sys.path.insert(0, _prior)

import phase3  # noqa: E402  (also loads phase2 and the Phase 1 src package)

DEV_RAW = phase3.RAW_DIR
RAW = Path(os.environ.get("JR_TAWOS_DIR", DEV_RAW))
if not RAW.is_absolute():
    RAW = ROOT / RAW
COHORT = "dev_8projects" if RAW == DEV_RAW else RAW.name
# JR_EXCLUDE_UNRECORDED=1 drops projects whose sprint issues are often closed without a resolution date
# (the label rule cannot tell when such an issue was finished). See jr.data.recording_check.
EXCLUDE_UNRECORDED = os.environ.get("JR_EXCLUDE_UNRECORDED", "0") == "1"
if EXCLUDE_UNRECORDED:
    COHORT += "_clean"
RESULTS = ROOT / "results" / COHORT
DATA = ROOT / "data" / COHORT
EXTERNAL_RAW = ROOT / "data" / "raw" / "external"
PRIOR_RESULTS = ROOT / "data" / "prior_results"
