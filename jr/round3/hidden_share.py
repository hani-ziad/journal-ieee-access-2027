"""Per-sprint hidden-issue share: 1 - visible/(max-min+1) over the issue numbers spanned by the sprint's committed issues.
Usage: hidden.py <cohort_dir> <issue_csv_or_pull> <keys_json_or_none>"""
import sys, json, gzip, re, numpy as np, pandas as pd
from collections import Counter
coh, src, keysf = sys.argv[1], sys.argv[2], sys.argv[3]
ii = pd.read_csv(f"/home/claude/journal/data/{coh}/issue_frame.csv")
if src.endswith(".csv"):
    t = pd.read_csv(src, usecols=["ID", "Issue_Key"]); idkey = dict(zip(t.ID.astype(str), t.Issue_Key))
    vis = {}
    for k in t.Issue_Key:
        p, n = k.rsplit("-", 1); vis.setdefault(p, []).append(int(n))
else:
    d = json.load(gzip.open(src)); idkey = {i["id"]: i["k"] for i in d["issues"]}
    kj = json.load(open(keysf)) if keysf.endswith(".json") else json.load(gzip.open(keysf)); vis = kj
vis = {p: np.sort(np.array(v)) for p, v in vis.items()}
rows = []
for sid, g in ii.groupby("sprint_id"):
    ks = [idkey.get(str(x)) for x in g.issue]; ks = [k for k in ks if k]
    if not ks: rows.append((sid, 0.0)); continue
    pref = Counter(k.rsplit("-", 1)[0] for k in ks).most_common(1)[0][0]
    nums = [int(k.rsplit("-", 1)[1]) for k in ks if k.rsplit("-", 1)[0] == pref]
    lo, hi = min(nums), max(nums); v = vis.get(pref)
    if v is None: rows.append((sid, 0.0)); continue
    present = np.searchsorted(v, hi, "right") - np.searchsorted(v, lo, "left")
    rows.append((sid, float(max(0.0, 1 - present / (hi - lo + 1)))))
out = pd.DataFrame(rows, columns=["sprint_id", "hidden_share"]); out.to_csv(f"/home/claude/journal/data/{coh}/hidden_share.csv", index=False)
print(coh, len(out), out.hidden_share.describe().round(3).to_dict())
