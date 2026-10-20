#!/usr/bin/env python3
"""
Step 4: E06 (leave-one-country-out and country-deletion sensitivity),
        E07 (calibration diagnostics for raw, 8-month Platt and expanding-window Platt probabilities),
        E08 (asymmetric-cost decisions and monthly top-k monitoring quotas).
Decision analyses use prob_dec, the calibration scheme locked per model on the development folds.
"""

import os
import warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
from common import (TAB_DIR, N_JOBS, WINDOWS, CAL_SCHEMES, fold_frames, seeds_for, add_expanding_calibration,
                    lock_calibration, compute_metrics, summarize, save_predictions, load_predictions, load_panel, load_splits)
from step3_e03_e05_benchmarks_and_ablations import MACRO_COLS, CI_COLS_CORE9, IQ_COLS, inner_temporal_tune_and_fit, core9_sample

warnings.filterwarnings("ignore")

LOCO_MODELS = ["B0_Historical_Rule", "B1_Regularized_Linear", "B2_Threshold_Model", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]


def _loco_task(other, held, sp, m_code, fcols, seed):
    tr, cal, _ = fold_frames(other, sp)
    _, _, te = fold_frames(held, sp)
    thr = float(tr["target_reer_vol_3m"].quantile(0.80))
    hist = held[(held["ym"] >= sp["train_start"]) & (held["ym"] <= sp["train_end_origin"])]
    thr_cty = float(hist["target_reer_vol_3m"].quantile(0.80))
    y_tr = tr["target_reer_vol_3m"].values
    c, pr, pc, _ = inner_temporal_tune_and_fit(m_code, tr, y_tr, (y_tr >= thr).astype(int), cal,
                                               (cal["target_reer_vol_3m"].values >= thr).astype(int), te, fcols, seed=seed)
    return dict(key=(held["country"].iloc[0], sp["split_id"], m_code), role=sp["role"], ym=te["ym"].values,
                y=te["target_reer_vol_3m"].values, thr=thr, thr_cty=thr_cty, c=c, pr=pr, pc=pc,
                cutoff=te["feature_info_cutoff_ym"].values)


def run_e06_cross_country_and_deletion(panel, splits):
    print("[E06] Leave-one-country-out and country-deletion sensitivity...")
    sub = core9_sample(panel)
    fcols = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    countries = sorted(sub["country"].unique())
    tasks = [delayed(_loco_task)(sub[sub["country"] != c], sub[sub["country"] == c], sp.to_dict(), m, fcols, sd)
             for c in countries for _, sp in splits.iterrows() for m in LOCO_MODELS for sd in seeds_for(m)]
    res = Parallel(n_jobs=N_JOBS, backend="loky")(tasks)
    groups = {}
    for r in res:
        groups.setdefault(r["key"], []).append(r)
    rows = []
    for (c, split_id, m), rs in groups.items():
        r0 = rs[0]
        rows.append(pd.DataFrame({
            "variant": "LOCO", "model": m, "split_id": split_id, "role": r0["role"], "country": c, "ym": r0["ym"],
            "threshold": r0["thr"], "y_true_cont": r0["y"], "y_true_bin": (r0["y"] >= r0["thr"]).astype(int),
            "y_true_bin_cty_thresh": (r0["y"] >= r0["thr_cty"]).astype(int),
            "pred_cont": np.mean([r["c"] for r in rs], axis=0), "prob_raw": np.mean([r["pr"] for r in rs], axis=0),
            "prob_cal": np.mean([r["pc"] for r in rs], axis=0), "n_seeds": len(rs),
            "seed_agg": f"mean_of_{len(rs)}_seeds" if len(rs) > 1 else "single_seed_42", "feature_info_cutoff_ym": r0["cutoff"]}))
    loco = pd.concat(rows, ignore_index=True)
    loco = add_expanding_calibration(loco, splits, keys=("variant", "model", "country"))
    loco = lock_calibration(loco, keys=("variant", "model", "country"))
    loco = save_predictions(loco, "e06_loco")
    loco.to_csv(os.path.join(os.path.dirname(TAB_DIR), "predictions", "e06_loco_predictions.csv"), index=False)

    out = []
    oot = loco[WINDOWS["all"][1](loco)]
    for c in countries:
        for m in LOCO_MODELS:
            mc = oot[(oot["country"] == c) & (oot["model"] == m)]
            met = compute_metrics(mc, prob_col="prob_raw")
            yb = mc["y_true_bin_cty_thresh"]
            out.append({"country": c, "model": m, "N_months": met["N"], "N_pos": met["N_pos"], "Pos_Rate_Pooled": met["Pos_Rate"],
                        "AP_Pooled": met["AP"],
                        "AP_CountryHistThresh": round(float(average_precision_score(yb, mc["prob_raw"])), 4) if yb.nunique() > 1 else np.nan,
                        "Brier_raw": met["Brier"]})
    tab = pd.DataFrame(out)
    agg = []
    for m in LOCO_MODELS:
        s = tab[tab["model"] == m]
        mall = oot[oot["model"] == m]
        agg.append({"country": "EQUAL_WEIGHTED_MEAN", "model": m, "N_months": int(s["N_months"].sum()), "N_pos": int(s["N_pos"].sum()),
                    "Pos_Rate_Pooled": round(float(s["Pos_Rate_Pooled"].mean()), 4), "AP_Pooled": round(float(s["AP_Pooled"].dropna().mean()), 4),
                    "AP_CountryHistThresh": round(float(s["AP_CountryHistThresh"].dropna().mean()), 4), "Brier_raw": round(float(s["Brier_raw"].mean()), 4)})
        met = compute_metrics(mall, prob_col="prob_raw")
        agg.append({"country": "POOLED_ALL_COUNTRIES", "model": m, "N_months": met["N"], "N_pos": met["N_pos"], "Pos_Rate_Pooled": met["Pos_Rate"],
                    "AP_Pooled": met["AP"], "AP_CountryHistThresh": round(float(average_precision_score(mall["y_true_bin_cty_thresh"], mall["prob_raw"])), 4),
                    "Brier_raw": met["Brier"]})
    pd.concat([tab, pd.DataFrame(agg)], ignore_index=True).to_csv(os.path.join(TAB_DIR, "table5a_e06_loco_by_country.csv"), index=False)

    e03 = load_predictions("e03")
    e03 = e03[WINDOWS["all"][1](e03)]
    rows = []
    for drop in ["NONE (Full Core-9)"] + countries:
        d = e03 if drop.startswith("NONE") else e03[e03["country"] != drop]
        ap = {m: compute_metrics(d[d["model"] == m])["AP"] for m in ["M0_EBM_Additive", "M1_EBM_CIxIQ", "B0_Historical_Rule", "B1_Regularized_Linear", "B4_XGBoost"]}
        rows.append({"dropped_country": drop, "remaining_N": int((d["model"] == "M1_EBM_CIxIQ").sum()),
                     "Pos_Rate": round(float(d[d["model"] == "M1_EBM_CIxIQ"]["y_true_bin"].mean()), 4),
                     "M1_AP": ap["M1_EBM_CIxIQ"], "M0_AP": ap["M0_EBM_Additive"], "B0_AP": ap["B0_Historical_Rule"],
                     "B1_AP": ap["B1_Regularized_Linear"], "B4_AP": ap["B4_XGBoost"],
                     "Delta_AP_M1_vs_M0": round(ap["M1_EBM_CIxIQ"] - ap["M0_EBM_Additive"], 4)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table5b_e06_country_deletion_sensitivity.csv"), index=False)
    print("  - Saved table5a/5b")


def ece(y, p, n_bins=8):
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    out, bins = 0.0, []
    for b in range(n_bins):
        m = idx == b
        if m.sum():
            out += m.mean() * abs(p[m].mean() - y[m].mean())
        bins.append({"bin_idx": b + 1, "bin_range": f"[{edges[b]:.2f}, {edges[b + 1]:.2f}]", "count": int(m.sum()),
                     "mean_pred_prob": round(float(p[m].mean()), 4) if m.sum() else np.nan,
                     "empirical_pos_rate": round(float(y[m].mean()), 4) if m.sum() else np.nan})
    return round(float(out), 4), bins


def run_e07_calibration_diagnostics():
    print("[E07] Calibration diagnostics (raw, Platt 8-month window, Platt expanding window)...")
    e03 = load_predictions("e03")
    rows, bins = [], []
    for key in ["all", "locked", "dev"]:
        label, fn = WINDOWS[key]
        w = e03[fn(e03)]
        for m, mp in w.groupby("model", sort=False):
            y = mp["y_true_bin"].values
            r = {"evaluation_window": label, "model": m, "N": len(y), "Empirical_Pos_Rate": round(float(y.mean()), 4),
                 "cal_scheme_locked": mp["cal_scheme"].iloc[0]}
            for k, c in CAL_SCHEMES.items():
                p = np.clip(mp[c].values, 1e-5, 1 - 1e-5)
                e, b = ece(y, p)
                r.update({f"Brier_{k}": round(float(brier_score_loss(y, p)), 4), f"LogLoss_{k}": round(float(log_loss(y, p, labels=[0, 1])), 4),
                          f"ECE_{k}": e, f"Mean_Prob_{k}": round(float(p.mean()), 4)})
                if key == "locked":
                    bins += [{"model": m, "scheme": k, **bb} for bb in b]
            rows.append(r)
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table6_e07_calibration_diagnostics.csv"), index=False)
    pd.DataFrame(bins).to_csv(os.path.join(TAB_DIR, "e07_reliability_bins.csv"), index=False)
    print("  - Saved table6_e07_calibration_diagnostics.csv and e07_reliability_bins.csv")


def false_alarm_streak(mp, alert):
    streaks = []
    for _, g in mp.assign(a=alert).sort_values("ym").groupby("country"):
        cur = 0
        for v in ((g["a"].values == 1) & (g["y_true_bin"].values == 0)):
            if v:
                cur += 1
            elif cur:
                streaks.append(cur); cur = 0
        if cur:
            streaks.append(cur)
    return round(float(np.mean(streaks)), 2) if streaks else 0.0


def run_e08_decision_evaluation():
    print("[E08] Asymmetric-cost decisions and monthly top-k quotas (prob_dec)...")
    e03 = load_predictions("e03")
    cost_rows, topk_rows = [], []
    for key in ["all", "locked"]:
        label, fn = WINDOWS[key]
        w = e03[fn(e03)]
        y0 = w[w["model"] == "B0_Historical_Rule"]["y_true_bin"].values
        pos = float(y0.mean())
        for c_fn in [2.0, 5.0, 10.0]:
            tau = 1 / (1 + c_fn)
            never, always = 100 * c_fn * pos, 100 * (1 - pos)
            env = min(never, always)
            for name, cost, ar in [("Rule_Never_Alert", never, 0.0), ("Rule_Always_Alert", always, 100.0)]:
                cost_rows.append({"evaluation_window": label, "C_FN": c_fn, "threshold_tau": round(tau, 4), "model": name, "Alert_Rate_pct": ar,
                                  "Total_Cost_per100": round(cost, 2), "Normalized_Utility_Gain": round((env - cost) / env, 4)})
            for m, mp in w.groupby("model", sort=False):
                a = (mp["prob_dec"].values >= tau).astype(int)
                y = mp["y_true_bin"].values
                fp, fn_ = 100 * np.mean((a == 1) & (y == 0)), 100 * np.mean((a == 0) & (y == 1))
                tot = fp + c_fn * fn_
                cost_rows.append({"evaluation_window": label, "C_FN": c_fn, "threshold_tau": round(tau, 4), "model": m,
                                  "cal_scheme": mp["cal_scheme"].iloc[0], "Alert_Rate_pct": round(100 * a.mean(), 2),
                                  "FP_per100": round(fp, 2), "FN_per100": round(fn_, 2), "Total_Cost_per100": round(tot, 2),
                                  "Normalized_Utility_Gain": round((env - tot) / env, 4), "Mean_FP_Streak_Months": false_alarm_streak(mp, a)})
        for k in [1, 2, 3]:
            for m, mp in w.groupby("model", sort=False):
                hits = pos_tot = 0
                for _, gm in mp.groupby("ym"):
                    hits += int(gm.nlargest(k, "prob_dec")["y_true_bin"].sum())
                    pos_tot += int(gm["y_true_bin"].sum())
                years = mp["ym"].nunique() / 12
                topk_rows.append({"evaluation_window": label, "monthly_quota_k": k, "model": m,
                                  "Precision_at_k": round(hits / (k * mp["ym"].nunique()), 4), "Recall_at_k": round(hits / max(pos_tot, 1), 4),
                                  "Lift_over_Random": round(hits / (k * mp["ym"].nunique()) / max(mp["y_true_bin"].mean(), 1e-9), 3),
                                  "True_Alerts_per_Year": round(hits / years, 2), "Missed_Stress_per_Year": round((pos_tot - hits) / years, 2)})
    pd.DataFrame(cost_rows).to_csv(os.path.join(TAB_DIR, "table7a_e08_cost_decision_evaluation.csv"), index=False)
    pd.DataFrame(topk_rows).to_csv(os.path.join(TAB_DIR, "table7b_e08_topk_monitoring_capacity.csv"), index=False)
    print("  - Saved table7a/7b")


if __name__ == "__main__":
    panel, splits = load_panel(), load_splits()
    run_e06_cross_country_and_deletion(panel, splits)
    run_e07_calibration_diagnostics()
    run_e08_decision_evaluation()
    print("DONE: Step 4 (E06, E07, E08) completed successfully.")
