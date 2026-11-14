"""How much of each project an anonymous reader of public Jira cannot see (added 14 Nov 2026).

Private, deleted and moved issues keep their issue numbers, so the share of numbers missing from a
project's export bounds how much of it is hidden. A hidden issue that sat in a sprint makes that sprint's
committed scope look smaller than it was. The gap is measured over the sprint era: from the first issue
number that ever entered a sprint to the highest number in the project.

TAWOS: computed from the exported issue table. Red Hat: measured on the live site during the pull
(data_export/redhat/pull_jira_cloud.js, eraGap) and stored in the pull file.

    python -m jr.visibility      writes results/visibility_gaps.csv
"""
from __future__ import annotations

import json

import pandas as pd

import jr


def tawos():
    f = pd.read_csv(jr.ROOT / "data" / "tawos_all_clean" / "planning_frame.csv", usecols=["project"])
    i = pd.read_csv(jr.ROOT / "data" / "raw" / "tawos_all" / "tawos_issue.csv",
                    usecols=["Issue_Key", "Project_Name", "Sprint_ID"], na_values=["NULL"], low_memory=False)
    i = i[i.Project_Name.isin(f.project.unique())].copy()
    i["prefix"] = i.Issue_Key.str.rsplit("-", n=1).str[0]
    i["num"] = pd.to_numeric(i.Issue_Key.str.rsplit("-", n=1).str[1], errors="coerce")
    rows = []
    for (p, pre), g in i.groupby(["Project_Name", "prefix"]):
        if len(g) < 200:  # stray keys of issues moved in from other projects
            continue
        lo, hi = g[g.Sprint_ID.notna()].num.min(), g.num.max()
        era = g[(g.num >= lo) & (g.num <= hi)]
        rows.append({"source": "TAWOS", "project": p, "gap": 1 - len(era) / (hi - lo + 1)})
    return pd.DataFrame(rows)


def redhat():
    d = json.loads((jr.ROOT / "data" / "raw" / "redhat_pull" / "redhat_pull.json").read_text())
    # rows: key, first sprint-issue number, highest number, visible issues in that range, gap
    used = set(pd.read_csv(jr.ROOT / "data" / "redhat_clean" / "planning_frame.csv", usecols=["project"]).project)
    return pd.DataFrame([{"source": "Red Hat", "project": f"Red Hat {r[0]}", "gap": r[4]} for r in d["selection"]
                         if f"Red Hat {r[0]}" in used])  # RHEL (gap 0.89) was dropped by the selection rule


if __name__ == "__main__":
    out = pd.concat([tawos(), redhat()], ignore_index=True)
    out.to_csv(jr.ROOT / "results" / "visibility_gaps.csv", index=False)
    print(out.groupby("source").gap.describe().round(2).to_string())
