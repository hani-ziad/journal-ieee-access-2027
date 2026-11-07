"""Build the two study frames from a TAWOS-layout raw folder.

planning frame  one row per sprint: Phase 2 strict features, the four new features
                (PLAN.md Section 3), all five outcomes.
checkpoint frame one row per (sprint, checkpoint) at 25% and 50% of the planned
                duration, for sprints with committed work still open at that point:
                Phase 3 progress features, the Choetkiertikul supported subset,
                Worki R1-R11, and the outcomes.

Every feature uses only events time-stamped at or before its prediction time.
``sp_fallback_share`` records, per sprint, the share of committed issues whose story
points come from the static export (no recorded change), the hindsight risk the
CCECE paper's provenance section describes; it is a flag, not a feature.

    python -m jr.data                (uses JR_TAWOS_DIR, see jr/__init__.py)
"""
from __future__ import annotations

import functools
from bisect import bisect_right
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

import jr
import phase3
import phase2.data as p2d
from phase2.data import STRICT_NUMERIC, population, time_ordered_split
from phase3.data import PROGRESS_FEATURES, add_progress_features, build_checkpoint_state
from src.data.load_tawos import load_change_log, load_issues, load_sprints
from src.data.planning_snapshot import (
    _field_kind,
    _parse_change_sprint_set,
    _project_maps,
    _story_after,
    _story_before,
)
from jr.worki_features import R_COLS, r_features

DAY = 86_400 * 10**9
CHECKPOINTS = (0.25, 0.5)
_ORIG_LOADER = p2d.load_reconstructed_sprints

NEW_FEATURES = ["carried_in_share", "log_median_issue_age", "unestimated_share", "reestimated_share"]
MIN_COMMITTED_CHURN = 5  # scope churn is defined only on sprints with at least this many committed issues
CHOET = ["sprint_length_days", "committed_n", "committed_sp", "added_n", "added_sp", "removed_n",
         "removed_sp", "done_n", "done_sp", "todo_n", "todo_sp"]
OUTCOMES = {  # name: (population, column)
    "late_closure": ("full", "label_delay"),
    "seriously_late": ("full", "label_seriously_late"),
    "spillover": ("nonempty", "label_spillover"),
    "serious_spillover": ("nonempty", "label_serious_spillover"),
    "scope_churn": ("nonempty", "label_scope_churn"),
}
SENSITIVITY = {  # extra thresholds reported for the new labels (PLAN.md Section 2)
    "serious_spillover_20": ("nonempty", "label_serious_spillover_20"),
    "serious_spillover_50": ("nonempty", "label_serious_spillover_50"),
    "seriously_late_7": ("full", "label_seriously_late_7"),
    "scope_churn_50": ("nonempty", "label_scope_churn_50"),
    "serious_spillover_median": ("nonempty", "label_serious_spillover_median"),
}


def use_raw(raw: Path) -> None:
    """Point the frozen Phase 1-3 loaders at another raw folder (no code is changed)."""
    p2d.load_reconstructed_sprints = functools.partial(_ORIG_LOADER, raw)
    phase3.RAW_DIR = raw


def _issue_events(issues, change_log, sprints):
    jira_maps, raw_maps, name_maps = _project_maps(sprints)
    rel = change_log[change_log["field"].map(_field_kind).notna()].dropna(subset=["raw_issue_id", "change_date"])
    rel = rel.sort_values(["raw_issue_id", "change_date", "change_id"])
    events = defaultdict(list)
    for r in rel.itertuples(index=False):
        events[r.raw_issue_id].append(r)
    return (jira_maps, raw_maps, name_maps), events


def issue_level(raw: Path, cohort: pd.DataFrame, checkpoints=(0.25, 0.5, 1.0)):
    """Per sprint: the new planning-time features, and per checkpoint the counts and points
    behind the Choetkiertikul subset and the scope-churn label."""
    sprints = load_sprints(raw, modeling_only=True)
    issues = load_issues(raw)
    change_log = load_change_log(raw, required=True)
    (jira_maps, raw_maps, name_maps), events = _issue_events(issues, change_log, sprints)
    info = cohort.set_index("sprint_id")[["start_date", "end_date"]]
    start = {s: r.start_date.value for s, r in info.iterrows()}
    times = {s: [start[s] + f * (r.end_date.value - start[s]) for f in checkpoints] for s, r in info.iterrows()}
    ids = set(start)
    plan = {s: {"n": 0, "carried": 0, "ages": [], "unest": 0, "reest": 0, "sp_fallback": 0} for s in ids}
    K = len(checkpoints)
    acc = {s: [defaultdict(float) for _ in range(K)] for s in ids}

    for issue in issues.itertuples(index=False):
        p = issue.project
        if p not in jira_maps:
            continue
        jm, rm, nm = jira_maps[p], raw_maps[p], name_maps[p]
        ev = events.get(issue.raw_issue_id, [])
        sp_ev = [e for e in ev if _field_kind(e.field) == "sprint"]
        st_ev = [e for e in ev if _field_kind(e.field) == "story_point"]
        sp_times = [e.change_date.value for e in sp_ev]
        sp_from = [_parse_change_sprint_set(e.from_value, e.from_string, jira_map=jm, name_map=nm)[0] for e in sp_ev]
        sp_to = [_parse_change_sprint_set(e.to_value, e.to_string, jira_map=jm, name_map=nm)[0] for e in sp_ev]
        if sp_ev:
            terminal = sp_to[-1]
            cand = set(terminal)
            for a, b in zip(sp_from, sp_to):
                cand |= a | b
        else:
            terminal = set()
            if not pd.isna(issue.raw_sprint_id):
                key = str(int(float(issue.raw_sprint_id)))
                if key in rm:
                    terminal = {rm[key]}
            cand = set(terminal)
        cand &= ids
        if not cand:
            continue
        st_times = [e.change_date.value for e in st_ev]
        static = None if pd.isna(issue.story_point) else float(issue.story_point)
        st_term = _story_after(st_ev[-1]) if st_ev else static

        def members(t):
            i = bisect_right(sp_times, t)
            return sp_from[i] if i < len(sp_times) else terminal

        def story(t):
            i = bisect_right(st_times, t)
            return _story_before(st_ev[i]) if i < len(st_times) else st_term

        created = None if pd.isna(issue.creation_date) else issue.creation_date.value
        resolved = None if pd.isna(issue.resolution_date) else issue.resolution_date.value

        for sid in cand:
            t0 = start[sid]
            if resolved is not None and resolved < t0:
                continue
            in0 = sid in members(t0) and (created is None or created <= t0)
            sp0 = story(t0) if in0 else None
            if in0:
                pl = plan[sid]
                pl["n"] += 1
                # carried in: a sprint-field event at or before t0 names another sprint
                pl["carried"] += int(any(t <= t0 and ((a | b) - {sid}) for t, a, b in zip(sp_times, sp_from, sp_to)))
                if created is not None:
                    pl["ages"].append((t0 - created) / DAY)
                pl["unest"] += int(sp0 is None)
                # story points taken from the static export because no change is recorded (hindsight risk)
                pl["sp_fallback"] += int(not st_ev and static is not None)
                pl["reest"] += int(any(e.change_date.value <= t0 and _story_before(e) is not None
                                       and _story_before(e) != _story_after(e) for e in st_ev))
            for k, tk in enumerate(times[sid]):
                a = acc[sid][k]
                in_k = sid in members(tk) and (created is None or created <= tk)
                done_k = resolved is not None and resolved <= tk
                spk = story(tk) or 0.0
                if in0:
                    a["committed_n"] += 1
                    a["committed_sp"] += sp0 or 0.0
                    if not in_k:
                        a["removed_n"] += 1
                        a["removed_sp"] += sp0 or 0.0
                    elif done_k:
                        a["done_n"] += 1
                        a["done_sp"] += spk
                    else:
                        a["todo_n"] += 1
                        a["todo_sp"] += spk
                elif in_k:
                    a["added_n"] += 1
                    a["added_sp"] += spk
                    if done_k:
                        a["done_n"] += 1
                        a["done_sp"] += spk
                    else:
                        a["todo_n"] += 1
                        a["todo_sp"] += spk

    prow = []
    for s, pl in plan.items():
        n = pl["n"]
        age = float(np.median(pl["ages"])) if pl["ages"] else 0.0
        prow.append({"sprint_id": s,
                     "carried_in_share": pl["carried"] / n if n else 0.0,
                     "median_issue_age_days": age,
                     "log_median_issue_age": float(np.log1p(max(age, 0.0))),
                     "sp_fallback_share": pl["sp_fallback"] / n if n else 0.0,
                     "unestimated_share": pl["unest"] / n if n else 0.0,
                     "reestimated_share": pl["reest"] / n if n else 0.0})
    crow = []
    for s in ids:
        for k, f in enumerate(checkpoints):
            row = {"sprint_id": s, "checkpoint": f}
            row.update({c: acc[s][k].get(c, 0.0) for c in
                        ("committed_n", "committed_sp", "added_n", "added_sp", "removed_n", "removed_sp",
                         "done_n", "done_sp", "todo_n", "todo_sp")})
            crow.append(row)
    return pd.DataFrame(prow), pd.DataFrame(crow)


def add_labels(f: pd.DataFrame, churn: pd.Series) -> pd.DataFrame:
    """The three new labels and their sensitivity thresholds (PLAN.md Section 2)."""
    ne = f["nonempty"]
    late = f["late_days"]
    f["label_seriously_late"] = (late > 3).astype(int)
    f["label_seriously_late_7"] = (late > 7).astype(int)
    for thr, col in ((0.30, "label_serious_spillover"), (0.20, "label_serious_spillover_20"),
                     (0.50, "label_serious_spillover_50")):
        f[col] = np.where(ne, (f["carry_ratio"] >= thr).astype(float), np.nan)
    # "worse than typical": carry ratio above the median of the TRAINING nonempty sprints (v2 sensitivity label)
    tr, _ = time_ordered_split(population(f, "nonempty"))
    med = float(tr["carry_ratio"].median())
    f["label_serious_spillover_median"] = np.where(ne, (f["carry_ratio"] > med).astype(float), np.nan)
    f.attrs["carry_ratio_train_median"] = med
    ch = f["sprint_id"].map(churn)
    big = ne & (f["committed_issue_count"] >= MIN_COMMITTED_CHURN)
    f["churn_ratio"] = np.where(ne, ch, np.nan)
    f["label_scope_churn"] = np.where(big, (f["churn_ratio"] >= 0.30).astype(float), np.nan)
    f["label_scope_churn_50"] = np.where(big, (f["churn_ratio"] >= 0.50).astype(float), np.nan)
    return f


def add_split(f: pd.DataFrame) -> pd.DataFrame:
    for name in ("full", "nonempty"):
        tr, te = time_ordered_split(population(f, name))
        side = pd.concat([pd.Series("train", index=tr["sprint_id"]), pd.Series("test", index=te["sprint_id"])])
        f[f"split_{name}"] = f["sprint_id"].map(side)
    return f


def planning_frame(raw: Path):
    use_raw(raw)
    base = p2d.load_phase2_frame()
    info = p2d.load_reconstructed_sprints()[["sprint_id", "start_date", "end_date", "complete_date"]]
    cohort = base[["sprint_id"]].merge(info, on="sprint_id", how="left")
    plan, ck = issue_level(raw, cohort)
    f = base.merge(plan, on="sprint_id", how="left")
    end = ck[ck.checkpoint == 1.0].set_index("sprint_id")
    churn = end["added_n"] / end["committed_n"].clip(lower=1)
    f = add_split(add_labels(f, churn))
    return f, ck, cohort


def burndown(raw: Path, cohort: pd.DataFrame) -> pd.DataFrame:
    """Day-by-day scope and done counts per sprint (same rules as the critique repository)."""
    sprints = load_sprints(raw, modeling_only=True)
    issues = load_issues(raw)
    change_log = load_change_log(raw, required=True)
    (jira_maps, raw_maps, name_maps), events = _issue_events(issues, change_log, sprints)
    times, start_ns = {}, {}
    for r in cohort.itertuples(index=False):
        s, stop = r.start_date.value, min(r.end_date.value, r.complete_date.value)
        n = int((stop - s) // DAY)
        t = [s + k * DAY for k in range(n + 1)]
        if t[-1] < stop:
            t.append(stop)
        times[r.sprint_id], start_ns[r.sprint_id] = t, s
    ids = set(times)
    acc = {sid: [[0, 0] for _ in times[sid]] for sid in ids}
    for issue in issues.itertuples(index=False):
        p = issue.project
        if p not in jira_maps:
            continue
        jm, rm, nm = jira_maps[p], raw_maps[p], name_maps[p]
        ev = events.get(issue.raw_issue_id, [])
        sp_ev = [e for e in ev if _field_kind(e.field) == "sprint"]
        sp_times = [e.change_date.value for e in sp_ev]
        sp_from = [_parse_change_sprint_set(e.from_value, e.from_string, jira_map=jm, name_map=nm)[0] for e in sp_ev]
        if sp_ev:
            terminal = _parse_change_sprint_set(sp_ev[-1].to_value, sp_ev[-1].to_string, jira_map=jm, name_map=nm)[0]
            cand = set(terminal)
            for e in sp_ev:
                for val, sv in ((e.from_value, e.from_string), (e.to_value, e.to_string)):
                    cand |= _parse_change_sprint_set(val, sv, jira_map=jm, name_map=nm)[0]
        else:
            terminal = set()
            if not pd.isna(issue.raw_sprint_id):
                key = str(int(float(issue.raw_sprint_id)))
                if key in rm:
                    terminal = {rm[key]}
            cand = set(terminal)
        cand &= ids
        if not cand:
            continue

        def members(t):
            i = bisect_right(sp_times, t)
            return sp_from[i] if i < len(sp_times) else terminal

        created = None if pd.isna(issue.creation_date) else issue.creation_date.value
        resolved = None if pd.isna(issue.resolution_date) else issue.resolution_date.value
        for sid in cand:
            if resolved is not None and resolved < start_ns[sid]:
                continue
            for k, tk in enumerate(times[sid]):
                if sid in members(tk) and (created is None or created <= tk):
                    acc[sid][k][0] += 1
                    if resolved is not None and resolved <= tk:
                        acc[sid][k][1] += 1
    rows = []
    for sid, t in times.items():
        for k, tk in enumerate(t):
            scope, done = acc[sid][k]
            rows.append({"sprint_id": sid, "day": k, "elapsed_days": (tk - t[0]) / DAY,
                         "scope_n": scope, "done_n": done, "remaining_n": scope - done})
    return pd.DataFrame(rows)


def checkpoint_frame(raw: Path, plan_f: pd.DataFrame, ck: pd.DataFrame, cohort: pd.DataFrame) -> pd.DataFrame:
    use_raw(raw)
    ne = population(plan_f, "nonempty")
    state = build_checkpoint_state(CHECKPOINTS, cohort_ids=ne["sprint_id"])
    keep = ["sprint_id", "project", "start_date", "nonempty", "split_nonempty", "carry_ratio", "late_days",
            "sp_fallback_share"] + list(STRICT_NUMERIC) + NEW_FEATURES + [c for _, c in {**OUTCOMES, **SENSITIVITY}.values()]
    d = add_progress_features(state, ne[list(dict.fromkeys(keep))])
    d = d[d["open_at_checkpoint"]].copy()
    # Choetkiertikul supported subset (own counts, prefixed to keep them apart from Phase 3's)
    c = ck[ck.checkpoint.isin(CHECKPOINTS)].rename(columns={k: "ch_" + k for k in CHOET if k != "sprint_length_days"})
    d = d.merge(c, on=["sprint_id", "checkpoint"], how="left")
    # Worki R1-R11 from the daily burndown, on the planned clock
    coh = cohort[cohort.sprint_id.isin(d.sprint_id.unique())]
    daily = burndown(raw, coh)
    planned = ((coh.set_index("sprint_id")["end_date"] - coh.set_index("sprint_id")["start_date"])
               .dt.total_seconds() / 86400.0)
    rows = []
    for sid, g in daily.groupby("sprint_id", sort=False):
        g = g.sort_values("day").copy()
        g["n_days"] = planned[sid]
        for frac in CHECKPOINTS:
            rows.append({"sprint_id": sid, "checkpoint": frac, **r_features(g, frac)})
    d = d.merge(pd.DataFrame(rows), on=["sprint_id", "checkpoint"], how="left")
    return d.sort_values(["checkpoint", "project", "start_date", "sprint_id"]).reset_index(drop=True)


CHOET_COLS = ["sprint_length_days"] + ["ch_" + k for k in CHOET if k != "sprint_length_days"]


def build(raw: Path = None, out_dir: Path = None):
    raw = raw or jr.RAW
    out_dir = out_dir or jr.DATA
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_f, ck, cohort = planning_frame(raw)
    cp = checkpoint_frame(raw, plan_f, ck, cohort)
    plan_f.to_csv(out_dir / "planning_frame.csv", index=False)
    cp.to_csv(out_dir / "checkpoint_frame.csv", index=False)
    return plan_f, cp


if __name__ == "__main__":
    p, c = build()
    print("planning:", p.shape, "projects:", p.project.nunique(), "nonempty:", int(p.nonempty.sum()))
    for name, (pop, col) in {**OUTCOMES, **SENSITIVITY}.items():
        s = population(p, pop)[col]
        print(f"  {name:22s} n={s.notna().sum():5d} positive rate={s.mean():.3f}")
    print("checkpoint:", c.shape, c.groupby("checkpoint").size().to_dict())
    print("new features:\n", p[NEW_FEATURES + ["sp_fallback_share"]].describe().round(3).T[["mean", "50%", "max"]])
