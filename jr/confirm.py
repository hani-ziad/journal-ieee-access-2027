"""Confirmation set: the primary analysis on the 21 projects that were not in the development run.

The study plan and hypotheses were written after a development run on eight projects. The other
21 projects of the cohort had not been looked at when the hypotheses were written, so the
primary analysis restricted to them (models trained and tested on those 21 only) is a
confirmation of the hypotheses on data that did not shape them.

    python -m jr.confirm        writes results/<cohort>/confirm_*.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import jr
from jr.data import OUTCOMES
from jr.run import (IN_DIFFS, IN_OUTCOMES, IN_SETS, PLAN_DIFFS, PLAN_SETS, PRIMARY_MODEL, diff_row, safe_auc,
                    save, scores, unit)
from phase2.data import population

DEV_PROJECTS = sorted(pd.read_csv(jr.ROOT / "data" / "dev_8projects" / "planning_frame.csv").project.unique())


def keep(frame):
    return frame[~frame.project.isin(DEV_PROJECTS)].copy()


def main():
    f = keep(pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"]))
    aucs, diffs = [], []
    for oname, (pop, y) in OUTCOMES.items():
        fr = population(f, pop).dropna(subset=[y]).copy()
        fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"

        def work(rng):
            ua, ud = [], []
            te, s = scores(fr, y, PRIMARY_MODEL, PLAN_SETS, "time", split)
            for name in PLAN_SETS:
                ua.append({"stage": "planning", "outcome": oname, "checkpoint": np.nan, "features": name,
                           "n": len(te), "projects": te.project.nunique(), "positives": int(te[y].sum()),
                           "auc": safe_auc(te[y], s[name])})
            for a, b in PLAN_DIFFS:
                ud.append(diff_row({"stage": "planning", "outcome": oname, "checkpoint": np.nan}, te, y, s, a, b, rng, True))
            return ua, ud

        ua, ud = unit(f"confirm_planning_{oname}", work)
        aucs += ua; diffs += ud
        print("confirm planning", oname, flush=True)
    c = keep(pd.read_csv(jr.DATA / "checkpoint_frame.csv", parse_dates=["start_date"]))
    for oname in IN_OUTCOMES:
        y = OUTCOMES[oname][1]
        for cp in (0.25, 0.5):
            fr = c[c.checkpoint == cp].dropna(subset=[y]).copy()
            fr[y] = fr[y].astype(int)

            def work(rng):
                ua, ud = [], []
                te, s = scores(fr, y, PRIMARY_MODEL, IN_SETS, "time", "split_nonempty")
                for name in IN_SETS:
                    ua.append({"stage": "in-sprint", "outcome": oname, "checkpoint": cp, "features": name,
                               "n": len(te), "projects": te.project.nunique(), "positives": int(te[y].sum()),
                               "auc": safe_auc(te[y], s[name])})
                for a, b in IN_DIFFS:
                    ud.append(diff_row({"stage": "in-sprint", "outcome": oname, "checkpoint": cp}, te, y, s, a, b, rng, True))
                return ua, ud

            ua, ud = unit(f"confirm_insprint_{oname}_{cp}", work)
            aucs += ua; diffs += ud
            print("confirm insprint", oname, cp, flush=True)
    save(pd.DataFrame(aucs), "confirm_auc.csv")
    save(pd.DataFrame(diffs), "confirm_differences.csv")


if __name__ == "__main__":
    main()
