"""Round 3 scratch (PLAN_round3.md): status at sprint start. Usage: round3.py <issues.csv> <status.json.gz> <tag>"""
import sys, gzip, json, numpy as np, pandas as pd
import jr
from jr.data import OUTCOMES
from jr.run import PLAN_SETS, PRIMARY_MODEL, scores, cluster_diff, safe_auc
from jr.within import per_project, within, boot_diff
from phase2.data import population
iss = pd.read_csv(sys.argv[1]); st = json.load(gzip.open(sys.argv[2]))["issues"]; tag = sys.argv[3]
f = pd.read_csv(jr.DATA / "planning_frame.csv", parse_dates=["start_date"])
t0 = {r.sprint_id: pd.Timestamp(r.start_date).tz_localize(None) if pd.Timestamp(r.start_date).tzinfo is None else pd.Timestamp(r.start_date).tz_convert(None) for r in f.itertuples()}
STARTED = {"In Progress", "Coding In Progress", "ON_DEV"}
REVIEW = {"Review", "Code Review", "Pull Request Sent", "Testing", "ON_QA", "On QA", "QA In Progress", "Dev Complete", "POST", "MODIFIED",
          "Ready for QA", "Under Review", "In Review", "Needs Review", "QE Review", "Review in Progress"}
ACTIVE = STARTED | REVIEW
tr = {k: sorted((pd.to_datetime(a, utc=True).tz_convert(None), b, c) for a, b, c in v[2]) for k, v in st.items()}
rows = []; miss = 0
for r in iss.itertuples():
    t = tr.get(str(r.issue))
    if t is None: miss += 1; continue
    s0 = t0[r.sprint_id]; before = [x for x in t if x[0] <= s0]
    cur = before[-1][2] if before else (t[0][1] if t else None)
    first_act = next((x[0] for x in before if x[2] in ACTIVE), None)
    if first_act is None and cur in ACTIVE: first_act = s0  # initial status already active
    rows.append((r.sprint_id, int(cur in ACTIVE), int(cur in REVIEW), int(len(before) == 0), int(first_act is not None),
                 (s0 - first_act).total_seconds() / 86400 if first_act is not None else 0.0))
print("issues without status", miss, "of", len(iss))
d = pd.DataFrame(rows, columns=["sprint_id", "act", "rev", "notouch", "ever", "days"])
g = d.groupby("sprint_id")
ft = pd.DataFrame({"st_active": g.act.mean(), "st_review": g.rev.mean(), "st_notouch": g.notouch.mean(), "st_ever": g.ever.mean(),
                   "st_days": g.days.mean()}).reset_index()
ST = ["st_active", "st_review", "st_notouch", "st_ever", "st_days"]
f = f.merge(ft, on="sprint_id", how="left"); print(f[ST].describe().round(3).T)
f[ST] = f[ST].fillna(0.0)
BASE = list(PLAN_SETS["strict+new"][0]); rng = np.random.default_rng(20261115)
rows, drows = [], []
for oname in ("spillover", "serious_spillover", "late_closure"):
    pop, y = OUTCOMES[oname]
    fr = population(f, pop).dropna(subset=[y]).copy(); fr[y] = fr[y].astype(int)
    split = "split_full" if pop == "full" else "split_nonempty"
    sets = {"base": (BASE, True), "+status": (BASE + ST, True)}
    te, s = scores(fr, y, PRIMARY_MODEL, sets, "time", split)
    pp = {k: per_project(te, y, v) for k, v in s.items()}
    for k in s:
        rows.append({"cohort": tag, "outcome": oname, "set": k, "pooled": safe_auc(te[y], s[k]), "within": within(pp[k]), "n": len(te)})
    d_, lo, hi = cluster_diff(te, y, s["+status"], s["base"], rng)
    wd, wlo, whi, kk = boot_diff(pp["+status"], pp["base"], f"r3_{tag}_{oname}")
    drows.append({"cohort": tag, "outcome": oname, "pooled_d": d_, "p_lo": lo, "p_hi": hi, "within_d": wd, "w_lo": wlo, "w_hi": whi, "projects": kk})
    print(tag, oname, "done", flush=True)
pd.DataFrame(rows).to_csv(f"/home/claude/exp/r3_{tag}_auc.csv", index=False); pd.DataFrame(drows).to_csv(f"/home/claude/exp/r3_{tag}_diff.csv", index=False)
print(pd.DataFrame(drows).round(3).to_string())
