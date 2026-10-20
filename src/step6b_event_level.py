#!/usr/bin/env python3
"""
Step 6b: event-level and decomposition analyses
================================================
E16  Country-identity baselines (country fixed effects; fixed effects plus lagged REER volatility).
E17  Onset evaluation: origins whose lagged 3-month REER volatility is already at or above the fold
     threshold are removed, leaving forecasts of new stress rather than continuation.
E18  Episode-level evaluation: consecutive high-risk origins of a country form an episode; recall, lead time
     and false alarms per country-year at the C_FN = 5 alert threshold.
E19  Direction: high-risk windows split by the sign of the 3-month REER change (real depreciation vs
     appreciation); each direction is evaluated against all non-high-risk windows.
E20  Within/between decomposition of the FX-share signal: expanding country mean (between) and deviation
     from it (within), both computable in real time.
"""

import os
import warnings
import numpy as np
import pandas as pd
from interpret.glassbox import ExplainableBoostingClassifier

from common import (TAB_DIR, TAU_C5, WINDOWS, fold_frames, summarize, save_predictions, load_predictions, load_panel, load_splits)
from step3_e03_e05_benchmarks_and_ablations import (MACRO_COLS, CI_COLS_CORE9, IQ_COLS, EBM_FIXED, build_feature_matrix,
                                                    make_inner_folds, select_ebm_config, run_grid, core9_sample)

warnings.filterwarnings("ignore")
E03_MODELS = ["B0_Historical_Rule", "B1_Regularized_Linear", "B2_Threshold_Model", "B3_Random_Forest", "B4_XGBoost",
              "M0_EBM_Additive", "M1_EBM_CIxIQ"]
C_MODELS = ["C0_Country_Dummies", "C1_Country_plus_Persistence"]


def run_e16_country_baselines(panel, splits):
    print("[E16] Country-identity baselines...")
    sub = core9_sample(panel)
    full = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    pred, _ = run_grid(sub, splits, [dict(variant="Country_identity", model=m, fcols=full) for m in C_MODELS])
    return save_predictions(pred, "e16_country_baselines")


def all_preds():
    e03 = load_predictions("e03")
    e16 = load_predictions("e16_country_baselines")
    return pd.concat([e03, e16], ignore_index=True)


def run_e17_e19_onset_direction(panel, pred):
    print("[E17/E19] Onset and direction evaluation...")
    extra = panel[["country", "ym", "reer_vol_hist_3m", "target_reer_chg_3m"]]
    d = pred.merge(extra, on=["country", "ym"], how="left")
    d["in_stress_at_origin"] = d["reer_vol_hist_3m"] >= d["threshold"]
    rows = []
    for key in ["all", "locked"]:
        label, fn = WINDOWS[key]
        w = d[fn(d)]
        for m in E03_MODELS + C_MODELS:
            g = w[w["model"] == m]
            subsets = {"All origins": g, "Onset (not in stress at origin)": g[~g["in_stress_at_origin"]],
                       "Continuation (in stress at origin)": g[g["in_stress_at_origin"]],
                       "Depreciation episodes vs normal": g[(g["y_true_bin"] == 0) | (g["target_reer_chg_3m"] < 0)],
                       "Appreciation episodes vs normal": g[(g["y_true_bin"] == 0) | (g["target_reer_chg_3m"] >= 0)]}
            for s, gs in subsets.items():
                if len(gs) and gs["y_true_bin"].nunique() > 1:
                    rows.append({"evaluation_window": label, "subset": s, "model": m, **summarize(gs)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table12_e17_e19_onset_direction.csv"), index=False)


def episodes(g):
    """g: one country's rows sorted by ym. Returns list of (start_idx, end_idx) of consecutive positive runs."""
    y = g["y_true_bin"].values
    out, i = [], 0
    while i < len(y):
        if y[i] == 1:
            j = i
            while j + 1 < len(y) and y[j + 1] == 1:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def run_e18_episode_level(pred):
    print("[E18] Episode-level recall, lead time and false alarms...")
    rows = []
    for key in ["all", "locked"]:
        label, fn = WINDOWS[key]
        w = pred[fn(pred)]
        for m in E03_MODELS + C_MODELS:
            n_ep = det = early = fa = n_rows = 0
            leads = []
            for _, g in w[w["model"] == m].groupby("country"):
                g = g.sort_values("ym").reset_index(drop=True)
                a = g["prob_dec"].values >= TAU_C5
                pre = np.zeros(len(g), bool)
                for s, e in episodes(g):
                    n_ep += 1
                    lo = max(0, s - 3)
                    pre[lo:s] = True
                    hits = np.where(a[lo:e + 1])[0]
                    if len(hits):
                        det += 1
                        first = lo + hits[0]
                        leads.append(s - first)
                        early += int(first <= s)
                fa += int((a & (g["y_true_bin"].values == 0) & ~pre).sum())
                n_rows += len(g)
            rows.append({"evaluation_window": label, "model": m, "n_episodes": n_ep, "episodes_detected": det,
                         "episode_recall": round(det / max(n_ep, 1), 4), "detected_by_first_month": early,
                         "early_or_on_time_rate": round(early / max(n_ep, 1), 4),
                         "median_lead_months": float(np.median(leads)) if leads else np.nan,
                         "false_alarms": fa, "false_alarms_per_country_year": round(fa / (n_rows / 12), 3)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table13_e18_episode_level.csv"), index=False)


def _strict_counts(g, alert):
    """Episodes whose three pre-start origins are observed; detected only if an alert precedes the first
    high-risk origin (origins s-3..s-1). Lead = s minus the first such alert."""
    n_el = det = 0
    leads = []
    for s, _ in episodes(g):
        if s < 3:
            continue
        n_el += 1
        hits = np.where(alert[s - 3:s])[0]
        if len(hits):
            det += 1
            leads.append(3 - hits[0])
    return n_el, det, leads


def run_e22_strict_early_warning(pred):
    print("[E22] Strict early warning: alerts before episode start, lead times, fixed alert quotas...")
    rows = []
    for key in ["all", "locked"]:
        label, fn = WINDOWS[key]
        w = pred[fn(pred)]
        for m in E03_MODELS + C_MODELS:
            wm = w[w["model"] == m].copy()
            rank = wm.groupby("ym")["prob_dec"].rank(method="first", ascending=False)
            rules = [("threshold tau = 1/6", wm["prob_dec"].values >= TAU_C5)] + [(f"top-{k} countries per month", (rank <= k).values) for k in (1, 2, 3)]
            for rule, alert_all in rules:
                wm["_a"] = alert_all
                n_el = det = fa = n_rows = n_alerts = 0
                leads = []
                for _, g in wm.groupby("country"):
                    g = g.sort_values("ym").reset_index(drop=True)
                    a = g["_a"].values
                    e_, d_, l_ = _strict_counts(g, a)
                    n_el, det, leads = n_el + e_, det + d_, leads + l_
                    pre = np.zeros(len(g), bool)
                    for s, _ in episodes(g):
                        pre[max(0, s - 3):s] = True
                    fa += int((a & (g["y_true_bin"].values == 0) & ~pre).sum())
                    n_alerts += int(a.sum())
                    n_rows += len(g)
                rows.append({"evaluation_window": label, "model": m, "alert_rule": rule, "eligible_episodes": n_el,
                             "detected_before_start": det, "strict_detection_rate": round(det / max(n_el, 1), 4),
                             "lead_1": leads.count(1), "lead_2": leads.count(2), "lead_3": leads.count(3),
                             "median_lead_months": float(np.median(leads)) if leads else np.nan,
                             "alerts_per_country_year": round(n_alerts / (n_rows / 12), 3),
                             "false_alarms_per_country_year": round(fa / (n_rows / 12), 3)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table13b_e22_strict_early_warning.csv"), index=False)
    print("  - Saved table13b_e22_strict_early_warning.csv")


def add_ci_decomposition(panel):
    p = panel.sort_values(["country", "ym"]).copy()
    p["ci_between_rt"] = p.groupby("country")["fx_share_rt"].transform(lambda s: s.expanding().mean())
    p["ci_within_rt"] = p["fx_share_rt"] - p["ci_between_rt"]
    return p


def run_e20_ci_decomposition(panel, splits):
    print("[E20] Within/between decomposition of the FX share...")
    p = add_ci_decomposition(panel)
    sub = core9_sample(p)
    fc = MACRO_COLS + ["ci_within_rt", "ci_between_rt", "fx_share_chg_12m_rt"] + IQ_COLS
    specs = [dict(variant="CI_decomposed", model="M0_EBM_Additive", fcols=fc),
             dict(variant="CI_decomposed_withinxIQ", model="M1_EBM_CIxIQ", fcols=fc, ci_col="ci_within_rt"),
             dict(variant="CI_decomposed_betweenxIQ", model="M1_EBM_CIxIQ", fcols=fc, ci_col="ci_between_rt")]
    pred, _ = run_grid(sub, splits, specs)
    pred = save_predictions(pred, "e20_ci_decomposition")
    e03 = load_predictions("e03")
    rows = []
    for key in ["all", "locked"]:
        label, fn = WINDOWS[key]
        for m in ["M0_EBM_Additive", "M1_EBM_CIxIQ"]:
            rows.append({"evaluation_window": label, "variant": "FX share level (main)", "model": m, **summarize(e03[fn(e03) & (e03["model"] == m)])})
        w = pred[fn(pred)]
        for (v, m), g in w.groupby(["variant", "model"], sort=False):
            rows.append({"evaluation_window": label, "variant": v, "model": m, **summarize(g)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table14_e20_ci_decomposition.csv"), index=False)

    imps = []
    for _, sp in splits.iterrows():
        tr, _, _ = fold_frames(sub, sp)
        y = (tr["target_reer_vol_3m"].values >= tr["target_reer_vol_3m"].quantile(0.80)).astype(int)
        X, _, _ = build_feature_matrix(tr, fc)
        inter = [("ci_within_rt", "iq_mean_rt"), ("ci_between_rt", "iq_mean_rt")]
        cfg = select_ebm_config(y, make_inner_folds(tr, fc), inter, 42)
        ebm = ExplainableBoostingClassifier(interactions=inter, random_state=42, **EBM_FIXED, **cfg).fit(X, y)
        imp = dict(zip(ebm.term_names_, ebm.term_importances()))
        total = sum(imp.values())
        for t in ["ci_within_rt", "ci_between_rt", "fx_share_chg_12m_rt", "iq_mean_rt", "ci_within_rt & iq_mean_rt", "ci_between_rt & iq_mean_rt"]:
            imps.append({"split_id": sp["split_id"], "term": t, "importance": round(float(imp.get(t, 0.0)), 5),
                         "share_of_total": round(float(imp.get(t, 0.0)) / total, 4)})
    pd.DataFrame(imps).to_csv(os.path.join(TAB_DIR, "table14b_e20_decomposition_importance.csv"), index=False)
    print("  - Saved table14 and table14b")


if __name__ == "__main__":
    import sys
    panel, splits = load_panel(), load_splits()
    parts = sys.argv[1:] or ["e16", "e17", "e18", "e22", "e20"]
    if "e16" in parts:
        run_e16_country_baselines(panel, splits)
    pred = all_preds()
    if "e17" in parts:
        run_e17_e19_onset_direction(panel, pred)
    if "e18" in parts:
        run_e18_episode_level(pred)
    if "e22" in parts:
        run_e22_strict_early_warning(pred)
    if "e20" in parts:
        run_e20_ci_decomposition(panel, splits)
    print("DONE: Step 6b completed successfully.")
