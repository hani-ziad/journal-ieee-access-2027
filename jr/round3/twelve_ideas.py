"""Round 4 scratch (PLAN_round4.md). Usage: r4.py <out_tag> <cohort_dir>[,<cohort_dir>...]  (data/<dir>/planning_frame.csv)."""
import sys, os, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier as HGBC, HistGradientBoostingRegressor as HGBR
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import jr
from jr.data import OUTCOMES, NEW_FEATURES
from jr.run import PLAN_SETS, cluster_diff, safe_auc
from jr.within import per_project, within, boot_diff
from phase2.data import population
from phase2.models import make_classifier, feature_columns, _prep
from sklearn.pipeline import Pipeline
ROOT = Path(jr.ROOT); BASE = list(PLAN_SETS["strict+new"][0])
SPC = {"committed_story_points", "hist_avg_delivered_sp_3", "unestimated_share", "reestimated_share"}
if os.environ.get("NOSP") == "1": BASE = [c for c in BASE if c not in SPC]
COH = sys.argv[2].split(","); TAG = sys.argv[1]; ONLY = os.environ.get("ONLY", ""); want = lambda n: (not ONLY) or n.startswith(ONLY)
NOSP = os.environ.get("NOSP") == "1"
CONT = {"spillover": "carry_ratio", "serious_spillover": "carry_ratio", "late_closure": "late_days_capped"}

def load(d):
    f = pd.read_csv(ROOT / "data" / d / "planning_frame.csv", parse_dates=["start_date"]); f["cohort"] = d
    f = f.sort_values(["project", "start_date", "sprint_id"]).reset_index(drop=True)
    # idea 3 team-relative, 6 dynamics, 9 maturity
    g = f.groupby("project", sort=False)
    for c, n in (("committed_issue_count", "cnt"), ("committed_story_points", "pts")):
        med = g[c].transform(lambda x: x.shift(1).rolling(5, min_periods=2).median())
        sd = g[c].transform(lambda x: x.shift(1).rolling(5, min_periods=3).std())
        f[f"rel_{n}"] = (f[c] / med.replace(0, np.nan)).fillna(1.0)
        f[f"z_{n}"] = ((f[c] - med) / sd.replace(0, np.nan)).fillna(0.0).clip(-5, 5)
    f["d_count"] = (f.committed_issue_count - g.committed_issue_count.shift(1)).fillna(0.0)
    vol = np.zeros(len(f)); cr = f.carry_ratio.to_numpy(float); st = f.start_date.to_numpy("datetime64[ns]")
    en = (f.start_date + pd.to_timedelta(f.sprint_length_days.fillna(14), unit="D")).to_numpy("datetime64[ns]")
    for p, idx in g.indices.items():
        for k, i in enumerate(idx):
            prev = [cr[j] for j in idx[:k] if en[j] <= st[i] and not np.isnan(cr[j])][-5:]
            vol[i] = np.std(prev) if len(prev) >= 3 else 0.0
    f["vol5"] = vol
    f["ordinal"] = g.cumcount(); f["days_since_first"] = (f.start_date - g.start_date.transform("min")).dt.days
    # idea 5 size distribution
    p = ROOT / "data" / d / "issue_frame.csv"
    if p.exists():
        ii = pd.read_csv(p); gi = ii.groupby("sprint_id")
        def gini(x):
            x = np.sort(x.dropna().to_numpy(float)); n = len(x)
            return 0.0 if n < 2 or x.sum() == 0 else float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))
        ag = pd.DataFrame({"age_p75": gi.age_days.quantile(0.75), "age_p90": gi.age_days.quantile(0.90),
                           "age_gt90": gi.age_days.apply(lambda x: (x > 90).mean()), "age_new3d": gi.age_days.apply(lambda x: (x < 3).mean())}).reset_index()
        sz = pd.DataFrame({"sz_max": gi.sp.apply(lambda x: (x.max() / x.sum()) if x.sum() > 0 else 0.0),
                           "sz_gini": gi.sp.apply(gini), "sz_gt8": gi.sp.apply(lambda x: (x > 8).mean()),
                           "sz_mean": gi.sp.mean()}).reset_index()
        f = f.merge(sz, on="sprint_id", how="left").merge(ag, on="sprint_id", how="left")
    h = ROOT / "data" / d / "hidden_share.csv"
    if h.exists(): f = f.merge(pd.read_csv(h), on="sprint_id", how="left")
    return f

SETS = {"3 team-relative": ["rel_cnt", "rel_pts", "z_cnt", "z_pts"], "4 hidden share": ["hidden_share"],
        "5 size distribution": ["sz_max", "sz_gini", "sz_gt8", "sz_mean"], "6 dynamics": ["d_count", "vol5"],
        "9 maturity": ["ordinal", "days_since_first"], "11 age distribution": ["age_p75", "age_p90", "age_gt90", "age_new3d"]}
COMPACT = [c for c in ["committed_issue_count", "committed_story_points", "sprint_length_days", "hist_avg_completion_ratio_3", "hist_last_carryover"] + NEW_FEATURES if c in BASE]

def fitpred(cols, proj, tr, te, y, w=None, kind="gb", **hp):
    X = feature_columns(cols, proj)
    prep = _prep(cols, proj)
    try: prep.set_params(sparse_threshold=0)
    except Exception: pass
    if kind == "gb":
        est = HGBC(max_depth=hp.get("depth", 3), learning_rate=hp.get("lr", 0.05), max_iter=hp.get("it", 200), random_state=42)
    else:
        est = LogisticRegression(max_iter=1000, class_weight="balanced")
    pipe = Pipeline([("prep", prep), ("model", est)])
    kw = {"model__sample_weight": w} if w is not None else {}
    pipe.fit(tr[X], tr[y].astype(int), **kw)
    return pipe.predict_proba(te[X])[:, 1]

def regpred(cols, proj, tr, te, c):
    X = feature_columns(cols, proj); t = tr.dropna(subset=[c])
    pipe = Pipeline([("prep", _prep(cols, proj)), ("model", HGBR(max_depth=3, learning_rate=0.05, max_iter=200, random_state=42))])
    pipe.fit(t[X], t[c].astype(float)); return pipe.predict(te[X])

def tuned(cols, proj, tr, te, y):
    tr = tr.sort_values(["start_date", "sprint_id"]); inner, val = [], []
    for _, g in tr.groupby("project"):
        k = int(len(g) * 0.8); inner.append(g.iloc[:k]); val.append(g.iloc[k:])
    inner, val = pd.concat(inner), pd.concat(val); best, bh = -1, None
    if val[y].nunique() < 2: return fitpred(cols, proj, tr, te, y)
    for d in (2, 3, 4):
        for lr in (0.03, 0.05, 0.1):
            for it in (100, 200, 300):
                a = safe_auc(val[y], fitpred(cols, proj, inner, val, y, depth=d, lr=lr, it=it))
                if a > best: best, bh = a, dict(depth=d, lr=lr, it=it)
    return fitpred(cols, proj, tr, te, y, **bh)

frames = {d: load(d) for d in COH}
rng = np.random.default_rng(20261115); rows = []; aucs = []
def record(coh, o, name, te, y, s_idea, s_base):
    pp_i, pp_b = per_project(te, y, s_idea), per_project(te, y, s_base)
    d, lo, hi = cluster_diff(te, y, s_idea, s_base, rng)
    wd, wl, wh, k = boot_diff(pp_i, pp_b, f"r4_{coh}_{o}_{name}")
    rows.append({"cohort": coh, "outcome": o, "idea": name, "pooled_d": d, "p_lo": lo, "p_hi": hi, "within_d": wd, "w_lo": wl, "w_hi": wh, "projects": k,
                 "pooled_auc": safe_auc(te[y], s_idea), "within_auc": within(pp_i)})
    print(coh, o, name, round(d, 3), [round(lo, 3), round(hi, 3)], round(wd, 3), [round(wl, 3), round(wh, 3)], flush=True)
pooled_store = {}
for coh, f in frames.items():
    for o in ("spillover", "serious_spillover", "late_closure"):
        pop, y = OUTCOMES[o]; fr = population(f, pop).dropna(subset=[y]).copy(); fr[y] = fr[y].astype(int)
        split = "split_full" if pop == "full" else "split_nonempty"
        tr, te = fr[fr[split] == "train"], fr[fr[split] == "test"]
        base = pd.Series(fitpred(BASE, True, tr, te, y), index=te.index)
        aucs.append({"cohort": coh, "outcome": o, "idea": "base", "pooled_auc": safe_auc(te[y], base), "within_auc": within(per_project(te, y, base))})
        for name, extra in SETS.items():
            if any(c not in fr for c in extra) or not want(name): continue
            cols = BASE + extra; s = pd.Series(fitpred(cols, True, tr.fillna({c: 0 for c in extra}), te.fillna({c: 0 for c in extra}), y), index=te.index)
            record(coh, o, name, te, y, s, base)
        if want("12"):
            sc = pd.Series(fitpred(COMPACT, True, tr, te, y), index=te.index); record(coh, o, "12 compact set", te, y, sc, base)
        # 1 recency
        if want("1"): age = (tr.start_date.max() - tr.start_date).dt.days / 365.25; w = (0.5 ** (age / 2)).to_numpy()
        if want("1"): record(coh, o, "1 recency weighting", te, y, pd.Series(fitpred(BASE, True, tr, te, y, w=w), index=te.index), base)
        # 7 ensemble
        if want("7"):
            a = fitpred(BASE, True, tr, te, y); b = fitpred(BASE, True, tr, te, y, kind="lr")
            record(coh, o, "7 ensemble gb+logreg", te, y, pd.Series((rankdata(a) + rankdata(b)) / 2, index=te.index), base)
        # 8 continuous target
        if want("8"): record(coh, o, "8 continuous target", te, y, pd.Series(regpred(BASE, True, tr, te, CONT[o]), index=te.index), base)
        # 10 tuned
        if want("10"): record(coh, o, "10 tuned model", te, y, pd.Series(tuned(BASE, True, tr, te, y), index=te.index), base)
        pooled_store[(coh, o)] = (tr, te, y, base)
# 2 pooled training (only if more than one cohort)
if len(frames) > 1 and want("2"):
    for o in ("spillover", "serious_spillover", "late_closure"):
        trs = []
        for k, coh in enumerate(frames):
            tr, te, y, base = pooled_store[(coh, o)]; t = tr.copy(); t["src"] = k; trs.append(t)
        big = pd.concat(trs, ignore_index=True)
        for k, coh in enumerate(frames):
            tr, te, y, base = pooled_store[(coh, o)]; t2 = te.copy(); t2["src"] = k
            s = pd.Series(fitpred(BASE + ["src"], True, big, t2, y), index=te.index)
            record(coh, o, "2 pooled training", te, y, s, base)
pd.DataFrame(rows).to_csv(f"/home/claude/exp/r4_{TAG}_diff.csv", index=False); pd.DataFrame(aucs).to_csv(f"/home/claude/exp/r4_{TAG}_base.csv", index=False)
