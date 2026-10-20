#!/usr/bin/env python3
"""
Step 8: single-source consistency audit
=======================================
1. Assembles outputs/predictions/predictions_master.parquet from every experiment's row-level predictions.
2. Recomputes the metrics of every forecasting table from those predictions and compares them with the CSV
   tables (tolerance 1e-4 for rounded metrics, exact for counts).
3. Builds outputs/manuscript_numbers.json, the only source of numbers for step 7, and writes AUDIT_STATUS
   (PASS or FAIL). Step 7 refuses to build when the status is not PASS.
"""

import os
import json
import numpy as np
import pandas as pd

from common import (OUT_DIR, TAB_DIR, PRED_DIR, MASTER_DIR, WINDOWS, SESOI_AP, summarize, expected_cost, load_predictions, load_splits)
from step5_e09_e12_explain_robust_figs import paired_bootstrap

CONF_PRED = os.path.join(OUT_DIR, "confirmation", "confirmation_predictions.parquet")
STATUS = os.path.join(OUT_DIR, "AUDIT_STATUS")
issues, checks = [], []


def rd(name):
    return pd.read_csv(os.path.join(TAB_DIR, name))


def check(label, table_val, recomputed, tol=1e-4):
    ok = (pd.isna(table_val) and pd.isna(recomputed)) or abs(float(table_val) - float(recomputed)) <= tol
    checks.append({"check": label, "table": table_val, "recomputed": recomputed, "ok": bool(ok)})
    if not ok:
        issues.append(f"{label}: table {table_val} vs recomputed {recomputed}")


def compare_rows(tag, tab, rows_fn, keys, cols=("AP", "AP_fold_mean", "Brier", "Cost_C5_per100", "N_pos")):
    for _, r in tab.iterrows():
        g = rows_fn(r)
        if g is None or len(g) == 0:
            issues.append(f"{tag}: no predictions for {[r[k] for k in keys]}")
            continue
        m = summarize(g)
        for c in cols:
            if c in tab.columns:
                check(f"{tag} {' | '.join(str(r[k]) for k in keys)} {c}", r[c], m[c], tol=0 if c == "N_pos" else 2e-4)


def win(label):
    for k, (lab, fn) in WINDOWS.items():
        if lab == label:
            return fn
    raise KeyError(label)


# ----------------------------------------------------------------------------------------------
def assemble():
    parts = []
    for f in sorted(os.listdir(MASTER_DIR)):
        if f.endswith(".parquet"):
            parts.append(pd.read_parquet(os.path.join(MASTER_DIR, f)))
    if os.path.exists(CONF_PRED):
        c = pd.read_parquet(CONF_PRED)
        c["experiment"] = "confirmation_2023_2025"
        parts.append(c)
    allp = pd.concat(parts, ignore_index=True, sort=False)
    allp.to_parquet(os.path.join(PRED_DIR, "predictions_master.parquet"), index=False)
    return allp


def audit_tables():
    e03, e45 = load_predictions("e03"), load_predictions("e04_e05")
    t3 = rd("table3_e03_benchmark_comparison.csv")
    core6 = lambda d: (d["role"] == "locked_test") & (d["in_swift6"] == 1)
    compare_rows("table3", t3, lambda r: e03[(core6(e03) if "Core-6" in r["evaluation_window"] else win(r["evaluation_window"])(e03)) & (e03["model"] == r["model"])],
                 ["evaluation_window", "model"])
    t4 = rd("table4a_e04_feature_ablation.csv")
    compare_rows("table4a", t4, lambda r: e45[win(r["evaluation_window"])(e45) & (e45["model"] == r["model"]) & (e45["variant"] == r["feature_set"])],
                 ["evaluation_window", "model", "feature_set"])
    t4b = rd("table4b_e05_interaction_ablation.csv")
    compare_rows("table4b", t4b, lambda r: e45[win(r["evaluation_window"])(e45) & (e45["model"] == r["interaction_spec"]) & (e45["variant"] == "F3_Macro_plus_CI_plus_IQ")],
                 ["evaluation_window", "interaction_spec"])
    e11 = load_predictions("e11_robustness")
    t8 = rd("table8_e11_robustness_matrix.csv")
    compare_rows("table8", t8, lambda r: (e03[win(r["evaluation_window"])(e03) & (e03["model"] == r["model"])] if r["specification"].startswith("Main")
                                          else e11[win(r["evaluation_window"])(e11) & (e11["model"] == r["model"]) & (e11["variant"] == r["specification"])]),
                 ["evaluation_window", "specification", "model"])
    e13 = load_predictions("e13_external")
    t9 = rd("table9_e13_external_transfer.csv")
    compare_rows("table9", t9, lambda r: e13[win(r["evaluation_window"])(e13) & (e13["model"] == r["model"]) & (e13["regime"] == r["regime"]) & (e13["target"] == r["target"])],
                 ["evaluation_window", "regime", "target", "model"])
    e20 = load_predictions("e20_ci_decomposition")
    t14 = rd("table14_e20_ci_decomposition.csv")
    compare_rows("table14", t14, lambda r: (e03 if r["variant"].startswith("FX share level") else e20).pipe(
        lambda d: d[win(r["evaluation_window"])(d) & (d["model"] == r["model"]) & ((d["variant"] == r["variant"]) if not r["variant"].startswith("FX share level") else True)]),
        ["evaluation_window", "variant", "model"])
    e14 = load_predictions("e14_weighting")
    t10 = rd("table10_e14_adaptive_weighting.csv")
    for _, r in t10.iterrows():
        g = e14[(e14["model"] == r["learner"]) & (e14["variant"] == r["scheme"])]
        check(f"table10 {r['learner']} {r['scheme']} Test_AP", r["Test_AP"], summarize(g[win(WINDOWS['locked'][0])(g)])["AP"], 2e-4)
        check(f"table10 {r['learner']} {r['scheme']} Dev_AP_fold_mean", r["Dev_AP_fold_mean"], summarize(g[win(WINDOWS['dev'][0])(g)])["AP_fold_mean"], 2e-4)
    # E07 Brier by scheme, E08 cost at C_FN = 5
    t6 = rd("table6_e07_calibration_diagnostics.csv")
    for _, r in t6.iterrows():
        g = e03[win(r["evaluation_window"])(e03) & (e03["model"] == r["model"])]
        s = summarize(g)
        for k in ["raw", "platt_8m", "platt_expanding"]:
            check(f"table6 {r['evaluation_window']} {r['model']} Brier_{k}", r[f"Brier_{k}"], s[f"Brier_{k}"], 2e-4)
    t7 = rd("table7a_e08_cost_decision_evaluation.csv")
    for _, r in t7[(t7["C_FN"] == 5.0) & ~t7["model"].str.startswith("Rule")].iterrows():
        g = e03[win(r["evaluation_window"])(e03) & (e03["model"] == r["model"])]
        check(f"table7a {r['evaluation_window']} {r['model']} cost", r["Total_Cost_per100"], round(expected_cost(g["y_true_bin"], g["prob_dec"]), 2), 0.011)
    # sample and event counts
    tf = rd("table_folds_samples_events.csv").set_index("split_id")
    b0 = e03[e03["model"] == "B0_Historical_Rule"]
    for sid, g in b0.groupby("split_id"):
        check(f"folds {sid} n_test", tf.loc[sid, "n_test"], len(g), 0)
        check(f"folds {sid} n_test_pos", tf.loc[sid, "n_test_pos"], int(g["y_true_bin"].sum()), 0)
    # confirmation
    if os.path.exists(CONF_PRED):
        c = pd.read_parquet(CONF_PRED)
        c = c[c["role"] == "confirmation"]
        t15 = rd("table15_confirmation_2023_2025.csv")
        for _, r in t15[(t15["window"] == "2023-2025") & (t15["model"] != "Rule_Never_Alert")].iterrows():
            g = c[c["model"] == r["model"]]
            g = g if r["countries"] == "All 15 countries" else g[g["group"] == r["countries"]]
            m = summarize(g)
            for col in ["AP", "Brier", "Cost_C5_per100", "N_pos"]:
                check(f"table15 {r['countries']} {r['model']} {col}", r[col], m[col], 0 if col == "N_pos" else 2e-4)
    # one bootstrap interval recomputed from scratch
    bt = rd("e12_moving_block_bootstrap.csv")
    for wkey in ["all", "locked"]:
        lab, fn = WINDOWS[wkey]
        w = e03[fn(e03)]
        r = paired_bootstrap(w[w["model"] == "M1_EBM_CIxIQ"], w[w["model"] == "M0_EBM_Additive"], 12)
        row = bt[(bt["evaluation_window"] == lab) & (bt["block_length_months"] == 12) & (bt["model_A"] == "M1_EBM_CIxIQ") & (bt["model_B"] == "M0_EBM_Additive")].iloc[0]
        for k in ["Delta_AP_Point", "Delta_AP_CI95_Low", "Delta_AP_CI95_High"]:
            check(f"e12 {lab} M1-M0 {k}", row[k], r[k], 1e-6)


# ----------------------------------------------------------------------------------------------
def f3(x):
    return f"{float(x):.3f}"


def f1(x):
    return f"{float(x):.1f}"


def sgn(x, d=3):
    return f"{float(x):+.{d}f}".replace("+", "+")


def build_numbers():
    V = {}
    e03, e45 = load_predictions("e03"), load_predictions("e04_e05")
    A, L, D = WINDOWS["all"], WINDOWS["locked"], WINDOWS["dev"]

    def met(df, window, model, col="AP", variant=None, extra=None):
        g = df[window[1](df) & (df["model"] == model)]
        if variant is not None:
            g = g[g["variant"] == variant]
        if extra is not None:
            g = g[extra(g)]
        return summarize(g)[col]

    # threshold replication (estimation tables, not predictions)
    t2a, t2c = rd("table2a_threshold_tests.csv"), rd("table2c_published_vs_replicated.csv")
    trim, prt, wgi = rd("tableA3_threshold_trimming.csv"), rd("tableA2_threshold_pseudo_realtime.csv"), rd("tableA1_threshold_wgi_dimensions.csv")
    V["n_boot_thresh"] = int(t2a["n_boot"].iloc[0])
    V["p_min"] = f"{1 / (V['n_boot_thresh'] + 1):.4f}"
    V["n_f_exact"] = int((np.abs(t2a["f_stat_tn1_convention"] - t2a["f_published"]) < 0.006).sum())
    V["n_thr_exact"] = int((np.abs(t2a["threshold"] - t2a["threshold_published"]) < 1e-4).sum())
    V["ratio_A"] = f3((t2a[t2a.panel == "A_SWIFT"]["f_published"] / t2a[t2a.panel == "A_SWIFT"]["f_stat"]).median())
    V["ratio_B"] = f3((t2a[t2a.panel == "B_FX"]["f_published"] / t2a[t2a.panel == "B_FX"]["f_stat"]).median())
    sig = set(map(tuple, t2a[t2a["p_boot"] < 0.05][["panel", "risk"]].values))
    V["n_sig1"] = len(sig)
    t15 = trim[trim["trim"] == 0.15]
    V["n_sig15"] = int((t15["p_boot"] < 0.05).sum())
    V["n_lost15"] = int(sum((r.panel, r.risk) in sig and r.p_boot >= 0.05 for r in t15.itertuples()))
    V["n_sig_prt"] = int((prt["p_boot"] < 0.05).sum())
    V["n_both"] = int(sum((r.panel, r.risk) in sig and r.p_boot < 0.05 for r in prt.itertuples()))
    lab = lambda r: f"{'Panel A' if r.panel == 'A_SWIFT' else 'Panel B'} {r.risk}"
    V["robust_list"] = ", ".join(lab(r) for r in t15.itertuples() if (r.panel, r.risk) in sig and r.p_boot < 0.05) or "none"
    V["both_list"] = ", ".join(lab(r) for r in prt.itertuples() if (r.panel, r.risk) in sig and r.p_boot < 0.05) or "none"
    V["n_edge"] = int((t2a["share_obs_regime1"] < 0.10).sum())
    st = t2c["status"].value_counts()
    V["n_cells"] = len(t2c)
    V["n_repro"] = int(st.get("reproduced", 0))
    V["n_trans"] = int(sum(v for k, v in st.items() if "transcription" in k))
    V["n_tdiff"] = int(st.get("coefficient reproduced; t differs", 0))
    V["n_notrep"] = int(st.get("not reproduced", 0))
    V["wgi_sig_A"] = int((wgi[wgi.panel == "A_SWIFT"]["p_boot"] < 0.05).sum())
    V["wgi_sig_B"] = int((wgi[wgi.panel == "B_FX"]["p_boot"] < 0.05).sum())
    V["wgi_n"] = int((wgi.panel == "A_SWIFT").sum())
    a_cpi = t2a[(t2a.panel == "A_SWIFT") & (t2a.risk == "CPI_Vol")].iloc[0]
    V["A_cpi_share"] = f1(100 * a_cpi.share_obs_regime1)
    V["A_cpi_p15"] = f3(t15[(t15.panel == "A_SWIFT") & (t15.risk == "CPI_Vol")]["p_boot"].iloc[0])
    erv = t2a[(t2a.panel == "B_FX") & (t2a.risk == "ER_Vol")].iloc[0]
    V["B_er_n"], V["B_er_countries"], V["B_er_p"] = int(erv.n_obs), int(erv.n_countries), f3(erv.p_boot)

    # samples and events
    tf = rd("table_folds_samples_events.csv").set_index("split_id")
    lk = tf[tf["role"] == "locked_test"]
    dv = tf[tf["role"] == "dev_expanding"]
    V["n_test_lock"], V["n_pos_lock"] = int(lk["n_test"].sum()), int(lk["n_test_pos"].sum())
    V["n_test_dev"], V["n_pos_dev"] = int(dv["n_test"].sum()), int(dv["n_test_pos"].sum())
    V["n_pos_all"] = V["n_pos_lock"] + V["n_pos_dev"]
    V["pos_lock"] = f3(V["n_pos_lock"] / V["n_test_lock"])
    V["pos_2021"], V["pos_2022"] = int(tf.loc["LOCKED_TEST_2021", "n_test_pos"]), int(tf.loc["LOCKED_TEST_2022", "n_test_pos"])
    V["thr_min"], V["thr_max"] = f"{tf['threshold_q80'].min():.2f}", f"{tf['threshold_q80'].max():.2f}"
    V["cal_pos_2020"], V["cal_pos_2022"] = int(tf.loc["DEV_FOLD_2020", "n_calib_pos"]), int(tf.loc["LOCKED_TEST_2022", "n_calib_pos"])
    V["outcome_to"] = tf["outcome_data_needed_to"].max()

    # E03 benchmark
    M = ["B0_Historical_Rule", "B1_Regularized_Linear", "B2_Threshold_Model", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]
    short = dict(zip(M, ["b0", "b1", "b2", "b3", "b4", "m0", "m1"]))
    for m in M:
        for wtag, w in [("all", A), ("lock", L), ("dev", D)]:
            V[f"{short[m]}_{wtag}"] = f3(met(e03, w, m))
            V[f"{short[m]}_{wtag}_fm"] = f3(met(e03, w, m, "AP_fold_mean"))
            V[f"{short[m]}_{wtag}_brier"] = f3(met(e03, w, m, "Brier"))
            V[f"{short[m]}_{wtag}_cost"] = f1(met(e03, w, m, "Cost_C5_per100"))
    e16 = load_predictions("e16_country_baselines")
    for m, t in [("C0_Country_Dummies", "c0"), ("C1_Country_plus_Persistence", "c1")]:
        for wtag, w in [("all", A), ("lock", L), ("dev", D)]:
            V[f"{t}_{wtag}"] = f3(met(e16, w, m))
    learned = ["B1_Regularized_Linear", "B2_Threshold_Model", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]
    V["max_learned_lock"] = f3(max(met(e03, L, m) for m in learned))
    V["best_dev_model"] = max(M, key=lambda m: met(e03, D, m))
    V["best_dev_ap"] = f3(met(e03, D, V["best_dev_model"]))
    V["cal_locked_list"] = ", ".join(sorted(set(e03.groupby("model")["cal_scheme"].first())))
    V["n_raw_locked"] = int((e03.groupby("model")["cal_scheme"].first() == "raw").sum())

    # E04/E05 ablations
    for m, t in [("B1_Regularized_Linear", "b1"), ("B4_XGBoost", "b4"), ("M0_EBM_Additive", "m0")]:
        for wtag, w in [("all", A), ("lock", L)]:
            V[f"{t}_macro_{wtag}"] = f3(met(e45, w, m, variant="F0_Macro_Only"))
        for f, ft in [("F1_Macro_plus_CI", "ci"), ("F2_Macro_plus_IQ", "iq"), ("F3_Macro_plus_CI_plus_IQ", "ciiq")]:
            for wtag, w in [("all", A), ("lock", L)]:
                V[f"d_{t}_{ft}_{wtag}"] = sgn(met(e45, w, m, variant=f) - met(e45, w, m, variant="F0_Macro_Only"))
    V["n_ci_neg"] = sum(float(V[f"d_{t}_ci_{w}"]) < 0 for t in ["b1", "b4", "m0"] for w in ["all", "lock"])
    V["n_ci_gain_sesoi"] = sum(float(V[f"d_{t}_ci_{w}"]) >= SESOI_AP for t in ["b1", "b4", "m0"] for w in ["all", "lock"])
    V["n_any_gain_sesoi"] = sum(float(V[f"d_{t}_{f}_{w}"]) >= SESOI_AP for t in ["b1", "b4", "m0"] for f in ["ci", "iq", "ciiq"] for w in ["all", "lock"])
    for spec, t in [("M1_EBM_CIxIQ", "m1"), ("M_Placebo_MacroInter", "plac"), ("M_Unrestricted_EBM", "unr"), ("B1_Linear_CIxIQ", "lin")]:
        for wtag, w in [("all", A), ("lock", L)]:
            V[f"e05_{t}_{wtag}"] = sgn(met(e45, w, spec, variant="F3_Macro_plus_CI_plus_IQ") - met(e45, w, "M0_EBM_Additive", variant="F3_Macro_plus_CI_plus_IQ"))

    # E12 bootstrap (table values; M1-M0 recomputed in audit_tables)
    bt = rd("e12_moving_block_bootstrap.csv")
    for wtag, w in [("all", A), ("lock", L)]:
        for Lb in [6, 12]:
            for mb, t in [("M0_EBM_Additive", "m0"), ("B0_Historical_Rule", "b0"), ("B4_XGBoost", "b4")]:
                r = bt[(bt.evaluation_window == w[0]) & (bt.block_length_months == Lb) & (bt.model_A == "M1_EBM_CIxIQ") & (bt.model_B == mb)].iloc[0]
                k = f"bt_m1{t}_{wtag}_L{Lb}"
                V[k], V[k + "_lo"], V[k + "_hi"] = f3(r.Delta_AP_Point), f3(r.Delta_AP_CI95_Low), f3(r.Delta_AP_CI95_High)
                V[k + "_lo90"], V[k + "_hi90"] = f3(r.Delta_AP_CI90_Low), f3(r.Delta_AP_CI90_High)
                V[k + "_cost"], V[k + "_cost_lo"], V[k + "_cost_hi"] = f1(r.Delta_CostC5_Point), f1(r.Delta_CostC5_CI95_Low), f1(r.Delta_CostC5_CI95_High)
            for ma, t in [("B3_Random_Forest", "b3"), ("B4_XGBoost", "b4"), ("M0_EBM_Additive", "m0")]:
                r = bt[(bt.evaluation_window == w[0]) & (bt.block_length_months == Lb) & (bt.model_A == ma) & (bt.model_B == "B0_Historical_Rule")].iloc[0]
                k = f"bt_{t}b0_{wtag}_L{Lb}"
                V[k], V[k + "_lo"], V[k + "_hi"] = f3(r.Delta_AP_Point), f3(r.Delta_AP_CI95_Low), f3(r.Delta_AP_CI95_High)
    V["n_learned_gain_sesoi_all"] = int(sum(bt[(bt.evaluation_window == A[0]) & (bt.block_length_months == 12) & (bt.model_B == "B0_Historical_Rule")]["AP_gain_exceeds_SESOI_95"]))

    # E06/E07/E08
    lo = rd("table5a_e06_loco_by_country.csv")
    lo = lo[lo["country"] == "EQUAL_WEIGHTED_MEAN"].set_index("model") if "EQUAL_WEIGHTED_MEAN" in set(lo["country"]) else None
    if lo is not None:
        for m in ["B0_Historical_Rule", "B1_Regularized_Linear", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
            V[f"loco_{short[m]}"] = f3(lo.loc[m, "AP_Pooled"])
    dele = rd("table5b_e06_country_deletion_sensitivity.csv")
    V["del_min"], V["del_max"] = f3(dele["Delta_AP_M1_vs_M0"].min()), f3(dele["Delta_AP_M1_vs_M0"].max())
    cal = rd("table6_e07_calibration_diagnostics.csv")
    ca = cal[cal.evaluation_window == A[0]].set_index("model")
    V["n_platt8_worse_all"] = int((ca["Brier_platt_8m"] > ca["Brier_raw"]).sum())
    V["n_models_cal"] = len(ca)
    for m in ["M1_EBM_CIxIQ", "B0_Historical_Rule"]:
        for k in ["raw", "platt_8m", "platt_expanding"]:
            V[f"{short[m]}_brier_{k}_all"] = f3(ca.loc[m, f"Brier_{k}"])
            V[f"{short[m]}_ece_{k}_all"] = f3(ca.loc[m, f"ECE_{k}"])
    cost = rd("table7a_e08_cost_decision_evaluation.csv")
    for wtag, w in [("all", A), ("lock", L)]:
        c5 = cost[(cost.C_FN == 5.0) & (cost.evaluation_window == w[0])].set_index("model")
        V[f"cost_never_{wtag}"] = f1(c5.loc["Rule_Never_Alert", "Total_Cost_per100"])
        V[f"cost_always_{wtag}"] = f1(c5.loc["Rule_Always_Alert", "Total_Cost_per100"])
    tk = rd("table7b_e08_topk_monitoring_capacity.csv")
    for wtag, w in [("all", A), ("lock", L)]:
        t2 = tk[(tk.evaluation_window == w[0]) & (tk.monthly_quota_k == 2)].set_index("model")
        for m in ["B0_Historical_Rule", "B4_XGBoost", "M1_EBM_CIxIQ", "B3_Random_Forest"]:
            V[f"rec2_{short[m]}_{wtag}"] = f1(100 * t2.loc[m, "Recall_at_k"])

    # E09 explanations, E10 sub-periods
    e09 = rd("e09_explainability_stability.csv").reset_index(drop=True)
    terms = list(e09["term"])
    V["e09_rank_fx"], V["e09_rank_iq"], V["e09_nterms"] = terms.index("fx_share_rt") + 1, terms.index("iq_mean_rt") + 1, len(terms)
    V["e09_rank_inter"] = terms.index("fx_share_rt & iq_mean_rt") + 1 if "fx_share_rt & iq_mean_rt" in terms else "n/a"
    V["e09_rho"] = f"{e09['cross_fold_spearman_mean'].iloc[0]:.2f}"
    e10 = rd("e10_subperiod_analysis.csv").set_index(["regime_period", "model"])
    for p, t in [("P1 2017-2019", "p1"), ("P2 2020-2021", "p2"), ("P3 2022", "p3"), ("P3 2022 excluding RUS", "p3x")]:
        for m in ["B0_Historical_Rule", "B3_Random_Forest", "B4_XGBoost", "M1_EBM_CIxIQ", "B2_Threshold_Model"]:
            V[f"{t}_{short[m]}"] = f3(e10.loc[(p, m), "AP"])

    # E11 robustness
    rob = rd("table8_e11_robustness_matrix.csv").set_index(["evaluation_window", "specification", "model"])
    def rv(spec, m, w=A):
        return f3(rob.loc[(w[0], spec, m), "AP"])
    V["spot_m1_all"], V["spot_m0_all"], V["spot_b0_all"] = rv("Timing: month-t REER in features (not real-time)", "M1_EBM_CIxIQ"), rv("Timing: month-t REER in features (not real-time)", "M0_EBM_Additive"), rv("Timing: month-t REER in features (not real-time)", "B0_Historical_Rule")
    for lag in (3, 6, 12):
        V[f"cilag{lag}_m1_all"] = rv(f"Timing: CI release lag {lag} months", "M1_EBM_CIxIQ")
        V[f"cilag{lag}_m1_lock"] = rv(f"Timing: CI release lag {lag} months", "M1_EBM_CIxIQ", L)
    V["cifrozen_m1_all"], V["cifrozen_m1_lock"] = rv("Timing: CI frozen at training cut-off", "M1_EBM_CIxIQ"), rv("Timing: CI frozen at training cut-off", "M1_EBM_CIxIQ", L)
    for spec, t in [("Threshold q75 (pooled)", "q75"), ("Threshold q90 (pooled)", "q90"), ("Threshold q80 (country-specific)", "cty"), ("Horizon h=6", "h6")]:
        for m in ["B0_Historical_Rule", "B4_XGBoost", "M1_EBM_CIxIQ"]:
            V[f"{t}_{short[m]}_all"] = rv(spec, m)
    for m in ["B0_Historical_Rule", "B1_Regularized_Linear", "M1_EBM_CIxIQ"]:
        V[f"res_{short[m]}_all"] = rv("Reserve drawdown target (h=3)", m)
    wg = [rob.loc[(A[0], s, "M1_EBM_CIxIQ"), "AP"] for s in [i[1] for i in rob.index if i[0] == A[0] and i[1].startswith("WGI dimension")]]
    V["wgi_ap_min"], V["wgi_ap_max"] = f3(min(wg)), f3(max(wg))
    for spec, t in [("Core-6 matched: SWIFT share", "sw"), ("Core-6 matched: FX share", "fx"), ("Core-6 matched: both CI", "both"), ("Core-6 matched: no CI", "noci")]:
        V[f"c6_{t}_m1_all"] = rv(spec, "M1_EBM_CIxIQ")
    V["c6_b0_all"] = rv("Core-6 matched: no CI", "B0_Historical_Rule")

    # E13 transfer
    e13 = rd("table9_e13_external_transfer.csv").set_index(["evaluation_window", "regime", "target", "model"])
    for reg, t in [("Transfer_Core9_only", "tr"), ("Pooled_with_target_history", "po")]:
        for m in ["B0_Historical_Rule", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "B1_Regularized_Linear"]:
            for wtag, w in [("all", A), ("lock", L)]:
                V[f"e13_{t}_{short[m]}_{wtag}"] = f3(e13.loc[(w[0], reg, "target_reer_vol_3m", m), "AP"])
    V["e13_pos_all"] = f3(e13.loc[(A[0], "Transfer_Core9_only", "target_reer_vol_3m", "B0_Historical_Rule"), "Pos_Rate"])
    V["e13_npos_all"] = int(e13.loc[(A[0], "Transfer_Core9_only", "target_reer_vol_3m", "B0_Historical_Rule"), "N_pos"])

    # E14 weighting
    e14 = rd("table10_e14_adaptive_weighting.csv").set_index(["learner", "scheme"])
    for lrn in ["EBM", "XGBoost"]:
        sel = e14.xs(lrn)[e14.xs(lrn)["Selected_on_dev"]].index[0]
        V[f"e14_{lrn}_sel"] = sel.replace("_", " ")
        V[f"e14_{lrn}_test_sel"], V[f"e14_{lrn}_test_glob"] = f3(e14.loc[(lrn, sel), "Test_AP"]), f3(e14.loc[(lrn, "Global"), "Test_AP"])
        V[f"e14_{lrn}_dev_sel"], V[f"e14_{lrn}_dev_glob"] = f3(e14.loc[(lrn, sel), "Dev_AP_fold_mean"]), f3(e14.loc[(lrn, "Global"), "Dev_AP_fold_mean"])

    # E15 review
    cd = rd("table11b_e15_cost_differences.csv")
    def cdv(w, a, b, acc=1.0):
        r = cd[(cd.evaluation_window == w[0]) & (cd.policy_A == a) & (cd.policy_B == b) & (cd.reviewer_acc == acc)].iloc[0]
        return f1(r.Delta_cost_per100), f1(r.CI95_Low), f1(r.CI95_High), f1(r.cost_A_per100), f1(r.cost_B_per100)
    pairs = {"m1rev_b0rev": ("M1 + low-confidence review (k=2)", "B0 + low-confidence review (k=2)"),
             "m1rev_b0auto": ("M1 + low-confidence review (k=2)", "B0 automated"),
             "m1rev_volrev": ("M1 + low-confidence review (k=2)", "Never alert + volatility review (k=2)"),
             "m1rev_rand": ("M1 + low-confidence review (k=2)", "M1 + random review (k=2)"),
             "m1rev_macro": ("M1 + low-confidence review (k=2)", "Macro-only EBM + low-confidence review (k=2)"),
             "m1auto_b0auto": ("M1 automated", "B0 automated"),
             "platt_raw": ("M1 Platt 8m automated", "M1 raw automated"),
             "b0rev_b0auto": ("B0 + low-confidence review (k=2)", "B0 automated"),
             "b0auto_never": ("B0 automated", "Never alert")}
    for k, (a, b) in pairs.items():
        for wtag, w in [("all", A), ("lock", L)]:
            for acc, at in [(1.0, ""), (0.8, "_acc8")]:
                d, lo_, hi_, ca_, cb_ = cdv(w, a, b, acc)
                V[f"e15_{k}_{wtag}{at}"], V[f"e15_{k}_{wtag}{at}_lo"], V[f"e15_{k}_{wtag}{at}_hi"] = d, lo_, hi_
                V[f"e15_{k}_{wtag}{at}_A"], V[f"e15_{k}_{wtag}{at}_B"] = ca_, cb_

    # E16-E20
    on = rd("table12_e17_e19_onset_direction.csv").set_index(["evaluation_window", "subset", "model"])
    for s, t in [("Onset (not in stress at origin)", "on"), ("Continuation (in stress at origin)", "cont"), ("Depreciation episodes vs normal", "dep"), ("Appreciation episodes vs normal", "app")]:
        for m in ["B0_Historical_Rule", "B4_XGBoost", "M1_EBM_CIxIQ", "C1_Country_plus_Persistence", "B3_Random_Forest"]:
            for wtag, w in [("all", A), ("lock", L)]:
                key = (w[0], s, m)
                V[f"{t}_{short.get(m, 'c1')}_{wtag}"] = f3(on.loc[key, "AP"]) if key in on.index else "n/a"
        V[f"{t}_npos_all"] = int(on.loc[(A[0], s, "B0_Historical_Rule"), "N_pos"])
        V[f"{t}_npos_lock"] = int(on.loc[(L[0], s, "B0_Historical_Rule"), "N_pos"])
    ep = rd("table13_e18_episode_level.csv").set_index(["evaluation_window", "model"])
    V["n_episodes_all"], V["n_episodes_lock"] = int(ep.loc[(A[0], "B0_Historical_Rule"), "n_episodes"]), int(ep.loc[(L[0], "B0_Historical_Rule"), "n_episodes"])
    for m in ["B0_Historical_Rule", "B4_XGBoost", "M1_EBM_CIxIQ", "B1_Regularized_Linear"]:
        for wtag, w in [("all", A), ("lock", L)]:
            V[f"ep_rec_{short[m]}_{wtag}"] = f"{100 * ep.loc[(w[0], m), 'episode_recall']:.0f}"
            V[f"ep_fa_{short[m]}_{wtag}"] = f"{ep.loc[(w[0], m), 'false_alarms_per_country_year']:.2f}"
    dc = rd("table14_e20_ci_decomposition.csv").set_index(["evaluation_window", "variant", "model"])
    V["dec_m0_all"] = f3(dc.loc[(A[0], "CI_decomposed", "M0_EBM_Additive"), "AP"])
    V["dec_within_all"] = f3(dc.loc[(A[0], "CI_decomposed_withinxIQ", "M1_EBM_CIxIQ"), "AP"])
    V["dec_between_all"] = f3(dc.loc[(A[0], "CI_decomposed_betweenxIQ", "M1_EBM_CIxIQ"), "AP"])
    V["dec_m0_lock"] = f3(dc.loc[(L[0], "CI_decomposed", "M0_EBM_Additive"), "AP"])
    di = rd("table14b_e20_decomposition_importance.csv").groupby("term")["share_of_total"].mean()
    V["imp_between"], V["imp_within"] = f1(100 * di["ci_between_rt"]), f1(100 * di["ci_within_rt"])
    V["imp_between_iq"], V["imp_within_iq"] = f1(100 * di["ci_between_rt & iq_mean_rt"]), f1(100 * di["ci_within_rt & iq_mean_rt"])

    # confirmation
    t15c = rd("table15_confirmation_2023_2025.csv").set_index(["countries", "window", "model"])
    for g, gt in [("All 15 countries", "all15"), ("Core-9", "core9"), ("External-6", "ext6")]:
        V[f"conf_{gt}_n"] = int(t15c.loc[(g, "2023-2025", "B0_Historical_Rule"), "N"])
        V[f"conf_{gt}_npos"] = int(t15c.loc[(g, "2023-2025", "B0_Historical_Rule"), "N_pos"])
        V[f"conf_{gt}_never"] = f1(t15c.loc[(g, "2023-2025", "Rule_Never_Alert"), "Cost_C5_per100"])
        for m, t in [("B0_Historical_Rule", "b0"), ("B1_Regularized_Linear", "b1"), ("M0_EBM_Additive", "m0"), ("B4_XGBoost", "b4"), ("Fallback_policy", "fb")]:
            V[f"conf_{gt}_{t}"] = f3(t15c.loc[(g, "2023-2025", m), "AP"])
            V[f"conf_{gt}_{t}_cost"] = f1(t15c.loc[(g, "2023-2025", m), "Cost_C5_per100"])
            V[f"conf_{gt}_{t}_brier"] = f3(t15c.loc[(g, "2023-2025", m), "Brier"])
    fbd = rd("table15b_confirmation_fallback_decisions.csv")
    V["conf_deployed"] = ", ".join(f"{r.test_year}: {'B0' if r.deployed.startswith('B0') else r.deployed}" for r in fbd.itertuples())
    V["conf_n_b0"] = int(fbd["deployed"].str.startswith("B0").sum())
    cc = rd("table15c_confirmation_differences.csv").set_index(["countries", "model_A", "metric"])
    for g, gt in [("All 15 countries", "all15"), ("Core-9", "core9")]:
        for m, t in [("B4_XGBoost", "b4"), ("M0_EBM_Additive", "m0"), ("B1_Regularized_Linear", "b1")]:
            for met_, mt in [("AP", "ap"), ("Cost_C5_per100", "cost")]:
                r = cc.loc[(g, m, met_)]
                fmt = f3 if mt == "ap" else f1
                V[f"cd_{gt}_{t}_{mt}"], V[f"cd_{gt}_{t}_{mt}_lo"], V[f"cd_{gt}_{t}_{mt}_hi"] = fmt(r.Delta), fmt(r.CI95_Low), fmt(r.CI95_High)
    import yaml
    proto = yaml.load(open(os.path.join(OUT_DIR, "confirmation", "confirmation_protocol.yaml")), Loader=yaml.UnsafeLoader)
    V["proto_hash"] = open(os.path.join(OUT_DIR, "confirmation", "confirmation_protocol.sha256")).read().split()[0]
    V["proto_hash12"] = V["proto_hash"][:12]
    V["fb_learned"] = proto["fallback_policy"]["learned_model"]
    V["fb_ece_cap"] = f"{proto['fallback_policy']['ece_cap']:.2f}"
    V["fb_delta"] = f"{proto['fallback_policy']['delta']:.2f}"
    retro = proto["fallback_policy"]["single_evaluation_on_retrospective_test"]
    V["fb_retro"] = "; ".join(f"{r['test_year']}: {'B0' if r['deployed'].startswith('B0') else r['deployed']}" for r in retro)
    V["sesoi"] = f"{SESOI_AP:.2f}"
    return V


if __name__ == "__main__":
    allp = assemble()
    print(f"predictions_master.parquet: {len(allp):,} rows, experiments: {sorted(allp['experiment'].dropna().unique())}")
    audit_tables()
    V = build_numbers()
    with open(os.path.join(OUT_DIR, "manuscript_numbers.json"), "w") as f:
        json.dump({k: (v.item() if hasattr(v, "item") else v) for k, v in V.items()}, f, indent=1, sort_keys=True)
    pd.DataFrame(checks).to_csv(os.path.join(OUT_DIR, "consistency_audit_checks.csv"), index=False)
    status = "PASS" if not issues else "FAIL"
    with open(STATUS, "w") as f:
        f.write(status + "\n" + "\n".join(issues) + "\n")
    print(f"{len(checks)} checks, {len(issues)} issues -> {status}")
    for i in issues[:30]:
        print("  ", i)
