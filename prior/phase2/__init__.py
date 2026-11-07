"""Phase 2 package (planning-time features, models), vendored for the journal study.

Only the path constants differ from the course repository: the Phase 1 ``src``
package sits next to this one under ``prior/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

PRIOR = Path(__file__).resolve().parents[1]
ROOT = PRIOR.parent
PHASE1_ROOT = PRIOR
RESULTS_DIR = ROOT / "results"

if str(PRIOR) not in sys.path:
    sys.path.append(str(PRIOR))
