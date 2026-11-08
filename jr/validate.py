"""Internal-consistency check of the reconstruction.

    python -m jr.validate        writes results/<cohort>/reconstruction_check.csv

The replay starts from each issue's change log. If the log is complete, replaying it forward must end
in the values the export shows. For every issue of the cohort's projects:
  sprint   the last Sprint change event's new value contains the exported sprint (or both are empty)
  points   the last story-point change event's new value equals the exported story points
We also report how many issues placed in a sprint have any sprint history at all; for the rest the
replay has to assume the exported sprint was the sprint at the start.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

import jr
from prior.src.data.planning_snapshot import _field_kind  # noqa: F401  (same field rule as the replay)


def _num(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    t = str(x).strip()
    if not t or t.lower() in {"null", "none", "nan"}:
        return None
    m = re.search(r"[-+]?\d+(?:\.\d+)?", t)
    return float(m.group(0)) if m else None


def main():
    raw = jr.RAW
    keep = set(pd.read_csv(jr.DATA / "planning_frame.csv").project.unique())
    s = pd.read_csv(raw / "tawos_sprint.csv", na_values=["NULL"])
    s["project"] = s.Project_Name.astype(str).str.strip()
    i = pd.read_csv(raw / "tawos_issue.csv", na_values=["NULL"], low_memory=False)
    i["project"] = i.Project_Name.astype(str).str.strip()
    i = i[i.project.isin(keep)]
    c = pd.read_csv(raw / "tawos_change_log.csv", na_values=["NULL"], low_memory=False)
    c = c[c.Issue_ID.isin(i.ID)]
    c["kind"] = c.Field.map(_field_kind)
    c["Creation_Date"] = pd.to_datetime(c.Creation_Date)
    c = c.sort_values(["Issue_ID", "Creation_Date", "ID"])
    jmap = {(r.project, str(int(r.JiraID))): int(r.ID) for r in s.itertuples() if not pd.isna(r.JiraID)}
    proj = i.set_index("ID").project

    rows = []
    last_sp = c[c.kind == "sprint"].groupby("Issue_ID").tail(1).set_index("Issue_ID")
    for iss in i.itertuples():
        p = iss.project
        has = iss.ID in last_sp.index
        out = {"project": p, "issue": iss.ID, "in_sprint": not pd.isna(iss.Sprint_ID), "sprint_history": has}
        if has:
            ev = last_sp.loc[iss.ID]
            toks = re.findall(r"\d+", str(ev.To_Value)) if not pd.isna(ev.To_Value) else []
            mapped = {jmap[(p, t)] for t in toks if (p, t) in jmap}
            if pd.isna(iss.Sprint_ID):
                out["case"] = "both empty" if not toks else ("export empty, log names a known sprint" if mapped
                                                           else "export empty, log names a sprint outside the export")
            elif not toks:
                out["case"] = "log empty, export names a sprint"
            elif int(iss.Sprint_ID) in mapped:
                out["case"] = "same sprint"
            elif mapped:
                out["case"] = "different known sprints"
            else:
                out["case"] = "log names a sprint outside the export"
        rows.append(out)
    d = pd.DataFrame(rows)

    sp = c[c.kind == "story_point"].groupby("Issue_ID").tail(1).set_index("Issue_ID")
    st = []
    for iss in i[i.ID.isin(sp.index)].itertuples():
        ev = sp.loc[iss.ID]
        after = _num(ev.To_Value) if _num(ev.To_Value) is not None else _num(ev.To_String)
        exported = None if pd.isna(iss.Story_Point) else float(iss.Story_Point)
        st.append({"project": iss.project, "points_agree": (after is None and exported is None)
                   or (after is not None and exported is not None and abs(after - exported) < 1e-6)})
    st = pd.DataFrame(st)

    cases = d[d.sprint_history].case.value_counts()
    both_known = cases.get("same sprint", 0) + cases.get("different known sprints", 0)
    insp = d[d.in_sprint]
    summary = {
        "issues": len(d), "issues_with_sprint_history": int(d.sprint_history.sum()),
        "same_sprint": int(cases.get("same sprint", 0)), "different_known_sprints": int(cases.get("different known sprints", 0)),
        "agree_when_both_name_a_known_sprint": cases.get("same sprint", 0) / both_known,
        "export_empty_log_known_sprint": int(cases.get("export empty, log names a known sprint", 0)),
        "export_empty_log_outside_sprint": int(cases.get("export empty, log names a sprint outside the export", 0)),
        "log_empty_export_sprint": int(cases.get("log empty, export names a sprint", 0)),
        "both_empty": int(cases.get("both empty", 0)),
        "points_checked": len(st), "points_agree": float(st.points_agree.mean()),
        "in_sprint_issues": int(insp.shape[0]), "in_sprint_with_history": float(insp.sprint_history.mean()),
    }
    cov = insp.groupby("project").sprint_history.mean().rename("in_sprint_with_history").reset_index()
    cov.to_csv(jr.RESULTS / "reconstruction_coverage.csv", index=False)
    out = pd.DataFrame([summary])
    out.to_csv(jr.RESULTS / "reconstruction_check.csv", index=False)
    print(out.T.to_string())


if __name__ == "__main__":
    main()
