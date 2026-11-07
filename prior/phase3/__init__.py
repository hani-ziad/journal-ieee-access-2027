"""Phase 3 package (in-sprint progress features), vendored for the journal study.

Only the path constants differ from the course repository.
"""
from __future__ import annotations

import sys
from pathlib import Path

PRIOR = Path(__file__).resolve().parents[1]
ROOT = PRIOR.parent
RESULTS_DIR = ROOT / "results"

if str(PRIOR) not in sys.path:
    sys.path.append(str(PRIOR))

import phase2  # noqa: E402,F401

PHASE1_ROOT = phase2.PHASE1_ROOT
RAW_DIR = ROOT / "data" / "raw" / "tawos_8projects"
