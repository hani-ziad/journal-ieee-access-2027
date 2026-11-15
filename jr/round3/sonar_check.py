import sys, os, numpy as np, pandas as pd
sys.argv = ["r5", "sonar", "sonar_clean"]; os.environ["NOSP"] = "1"; os.environ["ONLY"] = "zz"
src = open("/home/claude/exp/r4.py").read().split("frames = {d: load(d)")[0]
exec(src)
from phase2.data import STRICT_NUMERIC
f = pd.read_csv(ROOT / "data" / "sonar_clean" / "planning_frame.csv", parse_dates=["start_date"])
print(f.groupby("project").size().to_dict())
STRICT = [c for c in STRICT_NUMERIC if c not in SPC]; NEWF = [c for c in NEW_FEATURES if c not in SPC]
SCOPEC = ["committed_issue_count", "sprint_length_days"]
rng = np.random.default_rng(20261115); rows = []
for o in ("spillover", "serious_spillover", "late_closure"):
    pop, y = OUTCOMES[o]; fr = population(f, pop).dropna(subset=[y]).copy(); fr[y] = fr[y].astype(int)
    split = "split_full" if pop == "full" else "split_nonempty"; tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
    print(o, "train", len(tr), "test", len(te), "test projects", te.project.nunique(), "pos rate", round(te[y].mean(), 3))
    S = {k: pd.Series(fitpred(c, True if k != "scope" else False, tr, te, y), index=te.index) for k, c in (("scope", SCOPEC), ("strict", STRICT), ("strict+new", STRICT + NEWF))}
    for a, b in (("strict+new", "strict"), ("strict+new", "scope"), ("strict", "scope")):
        d, lo, hi = cluster_diff(te, y, S[a], S[b], rng)
        _, slo, shi = cluster_diff(te, y, S[a], S[b], rng, level="sprint")
        pa, pb = per_project(te, y, S[a]), per_project(te, y, S[b])
        wd, wl, wh, k = boot_diff(pa, pb, f"r5_{o}_{a}_{b}")
        rows.append({"outcome": o, "comparison": f"{a} - {b}", "pooled_auc_a": safe_auc(te[y], S[a]), "pooled_d": d, "p_lo": lo, "p_hi": hi, "sprint_lo": slo, "sprint_hi": shi, "within_d": wd, "w_lo": wl, "w_hi": wh, "projects": k})
r = pd.DataFrame(rows); r.to_csv("/home/claude/exp/r5_sonar.csv", index=False); print(r.round(3).to_string())
