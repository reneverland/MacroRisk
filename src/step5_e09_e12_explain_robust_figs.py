#!/usr/bin/env python3
"""
Step 5: E09 (EBM explanations and cross-fold stability), E10 (sub-periods), E11 (robustness matrix,
        including information-timing sensitivities), E12 (paired moving-block bootstrap) and Figures 1-5.
All metrics are computed from the row-level prediction store (outputs/predictions/master).
"""

import os
import yaml
import warnings
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, brier_score_loss
from joblib import Parallel, delayed
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from common import (OUT_DIR, TAB_DIR, PRED_DIR, N_JOBS, SEEDS, SESOI_AP, WINDOWS, fold_frames, summarize, compute_metrics,
                    expected_cost, save_predictions, load_predictions, load_panel, load_splits)
from step3_e03_e05_benchmarks_and_ablations import (MACRO_COLS, CI_COLS_CORE9, SWIFT_COLS, IQ_COLS, build_feature_matrix,
                                                    EBM_FIXED, make_inner_folds, select_ebm_config, run_grid, core9_sample)
from interpret.glassbox import ExplainableBoostingClassifier

warnings.filterwarnings("ignore")
FIG_DIR = os.path.join(OUT_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11,
                     "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9.5, "figure.dpi": 300})

SHORT = {"B0_Historical_Rule": "B0 Persistence", "B1_Regularized_Linear": "B1 Linear", "B2_Threshold_Model": "B2 Threshold",
         "B3_Random_Forest": "B3 Random forest", "B4_XGBoost": "B4 XGBoost", "M0_EBM_Additive": "M0 EBM additive",
         "M1_EBM_CIxIQ": "M1 EBM + CIxIQ"}
E03_MODELS = list(SHORT)


def save_fig(fig, name):
    for ext in ["pdf", "png"]:
        fig.savefig(os.path.join(FIG_DIR, f"{name}.{ext}"), bbox_inches="tight", dpi=300)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------
# E09 explanations
# ------------------------------------------------------------------------------------------------
def run_e09_explainability_and_stability(panel, splits):
    print("[E09] EBM term importances, CI x IQ surface and cross-fold stability...")
    sub = core9_sample(panel)
    full = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    ci_grid, iq_grid = np.linspace(-1.2, 2.5, 25), np.linspace(-1.5, 1.5, 25)
    imps, surfaces = [], []
    for _, sp in splits.iterrows():
        tr, _, _ = fold_frames(sub, sp)
        y = (tr["target_reer_vol_3m"].values >= tr["target_reer_vol_3m"].quantile(0.80)).astype(int)
        X, _, _ = build_feature_matrix(tr, full)
        inter = [("fx_share_rt", "iq_mean_rt")]
        cfg = select_ebm_config(y, make_inner_folds(tr, full), inter, 42)
        ebm = ExplainableBoostingClassifier(interactions=inter, random_state=42, **EBM_FIXED, **cfg).fit(X, y)
        imps.append({**dict(zip(ebm.term_names_, ebm.term_importances())), "split_id": sp["split_id"]})
        grid = pd.DataFrame([{**{c: 0.0 for c in full}, "fx_share_rt": a, "iq_mean_rt": b} for a in ci_grid for b in iq_grid])[list(X.columns)]
        surfaces.append(ebm.decision_function(grid).reshape(len(ci_grid), len(iq_grid)))
    df_imp = pd.DataFrame(imps).set_index("split_id")
    mean_imp = df_imp.mean().sort_values(ascending=False)
    rho = [spearmanr(df_imp.iloc[i], df_imp.iloc[j])[0] for i in range(len(df_imp)) for j in range(i + 1, len(df_imp))]
    pd.DataFrame({"term": mean_imp.index, "mean_importance": mean_imp.values.round(5),
                  "std_across_folds": df_imp.std()[mean_imp.index].values.round(5),
                  "rank": np.arange(1, len(mean_imp) + 1), "n_terms": len(mean_imp),
                  "cross_fold_spearman_mean": round(float(np.mean(rho)), 4)}).to_csv(os.path.join(TAB_DIR, "e09_explainability_stability.csv"), index=False)
    Xall, _, _ = build_feature_matrix(sub, full)
    H, _, _ = np.histogram2d(Xall["fx_share_rt"], Xall["iq_mean_rt"], bins=[np.linspace(-1.3, 2.6, 26), np.linspace(-1.6, 1.6, 26)])
    np.savez(os.path.join(OUT_DIR, "e09_interaction_surface.npz"), ci_grid=ci_grid, iq_grid=iq_grid, mean_surface=np.mean(surfaces, 0),
             std_surface=np.std(surfaces, 0), H_dens=H, ci_obs=Xall["fx_share_rt"].values, iq_obs=Xall["iq_mean_rt"].values)
    print(f"  - mean cross-fold Spearman {np.mean(rho):.3f}")


# ------------------------------------------------------------------------------------------------
# E10 sub-periods
# ------------------------------------------------------------------------------------------------
def run_e10_subperiod_analysis():
    print("[E10] Sub-period analysis...")
    e03 = load_predictions("e03")
    periods = [("P1 2017-2019", (e03["ym"] >= "2017-01") & (e03["ym"] <= "2019-12")),
               ("P2 2020-2021", (e03["ym"] >= "2020-01") & (e03["ym"] <= "2021-12")),
               ("P3 2022", (e03["ym"] >= "2022-01") & (e03["ym"] <= "2022-12")),
               ("P3 2022 excluding RUS", (e03["ym"] >= "2022-01") & (e03["country"] != "RUS"))]
    rows = [{"regime_period": n, "model": m, **summarize(e03[msk & (e03["model"] == m)])} for n, msk in periods for m in E03_MODELS]
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "e10_subperiod_analysis.csv"), index=False)


# ------------------------------------------------------------------------------------------------
# E11 robustness matrix
# ------------------------------------------------------------------------------------------------
def _with_cols(sub, mapping):
    d = sub.copy()
    for dst, src in mapping.items():
        d[dst] = d[src]
    return d


def run_e11_robustness_matrix(panel, splits):
    print("[E11] Robustness matrix (thresholds, horizon, CI measure, WGI dimension, information timing, reserve target)...")
    sub = core9_sample(panel)
    s6 = sub[sub["in_swift6"] == 1].copy()
    full = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    four = ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]
    specs = []
    for name, q, cty in [("Threshold q75 (pooled)", 0.75, False), ("Threshold q90 (pooled)", 0.90, False), ("Threshold q80 (country-specific)", 0.80, True)]:
        specs += [dict(variant=name, model=m, fcols=full, q=q, cty=cty) for m in ["B0_Historical_Rule"] + four]
    specs += [dict(variant="Horizon h=6", model=m, fcols=full, h=6, target="target_reer_vol_6m") for m in ["B0_Historical_Rule"] + four]
    specs += [dict(variant="Reserve drawdown target (h=3)", model=m, fcols=full, target="target_res_drawdown_3m")
              for m in ["B0_Historical_Rule", "B1_Regularized_Linear", "B2_Threshold_Model", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]]
    for col, lab in [("wgi_pv_rt", "PV"), ("wgi_rq_rt", "RQ"), ("wgi_ge_rt", "GE"), ("wgi_rl_rt", "RL"), ("wgi_cc_rt", "CC"), ("wgi_va_rt", "VA")]:
        specs.append(dict(variant=f"WGI dimension {lab} in M1", model="M1_EBM_CIxIQ", fcols=MACRO_COLS + CI_COLS_CORE9 + [col, "iq_data_age_m"], iq_col=col))
    for name, cols, ci in [("Core-6 matched: SWIFT share", SWIFT_COLS, "swift_share_rt"), ("Core-6 matched: FX share", CI_COLS_CORE9, "fx_share_rt"),
                           ("Core-6 matched: both CI", CI_COLS_CORE9 + SWIFT_COLS, "swift_share_rt"), ("Core-6 matched: no CI", [], "fx_share_rt")]:
        specs += [dict(variant=name, model=m, fcols=MACRO_COLS + cols + IQ_COLS, ci_col=ci, sub=s6) for m in ["B0_Historical_Rule", "B1_Regularized_Linear", "M0_EBM_Additive", "M1_EBM_CIxIQ"]]
    spot = _with_cols(sub, {c: c + "_spot" for c in ["reer_vol_hist_3m", "reer_vol_hist_6m", "reer_vol_hist_12m", "reer_ret_cum_3m", "usd_neer_ret_1m", "usd_neer_vol_3m"]})
    specs += [dict(variant="Timing: month-t REER in features (not real-time)", model=m, fcols=full, sub=spot) for m in ["B0_Historical_Rule"] + four]
    for lag in (3, 6, 12):
        d = _with_cols(sub, {"fx_share_rt": f"fx_share_rt_L{lag}", "fx_share_chg_12m_rt": f"fx_share_chg_12m_rt_L{lag}"})
        specs += [dict(variant=f"Timing: CI release lag {lag} months", model=m, fcols=full, sub=d) for m in ["M0_EBM_Additive", "M1_EBM_CIxIQ"]]
    specs += [dict(variant="Timing: CI frozen at training cut-off", model=m, fcols=full, freeze_cols=CI_COLS_CORE9) for m in ["M0_EBM_Additive", "M1_EBM_CIxIQ"]]
    pred, _ = run_grid(sub, splits, specs)
    pred = save_predictions(pred, "e11_robustness")
    base = load_predictions("e03")
    rows = []
    for label, fn in [WINDOWS["all"], WINDOWS["locked"]]:
        b = base[fn(base)]
        for m in ["B0_Historical_Rule"] + four:
            rows.append({"evaluation_window": label, "specification": "Main (q80 pooled, h=3, CI lag 1, REER t-1)", "model": m, **summarize(b[b["model"] == m])})
        w = pred[fn(pred)]
        for (v, m), g in w.groupby(["variant", "model"], sort=False):
            rows.append({"evaluation_window": label, "specification": v, "model": m, **summarize(g)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table8_e11_robustness_matrix.csv"), index=False)
    print("  - Saved table8_e11_robustness_matrix.csv")


# ------------------------------------------------------------------------------------------------
# E12 paired moving-block bootstrap
# ------------------------------------------------------------------------------------------------
def block_indices(months, block_len, rng):
    T = len(months)
    starts = rng.randint(0, T - block_len + 1, int(np.ceil(T / block_len)))
    return np.concatenate([np.arange(s, s + block_len) for s in starts])[:T]


def paired_bootstrap(a, b, block_len, n_boot=1000, seed=20261017, prob="prob_dec"):
    """a, b: prediction frames of two models over identical (country, ym) rows. Months are resampled in
    blocks jointly across countries. Returns point estimates and percentile intervals of A minus B."""
    a = a.sort_values(["ym", "country"]).reset_index(drop=True)
    b = b.sort_values(["ym", "country"]).reset_index(drop=True)
    assert (a["ym"].values == b["ym"].values).all() and (a["country"].values == b["country"].values).all()
    months = np.array(sorted(a["ym"].unique()))
    rows_of = [np.where(a["ym"].values == m)[0] for m in months]
    y = a["y_true_bin"].values

    def stats(idx):
        yy = y[idx]
        if yy.min() == yy.max():
            return None
        pa, pb = a[prob].values[idx], b[prob].values[idx]
        return (average_precision_score(yy, pa) - average_precision_score(yy, pb),
                brier_score_loss(yy, pa) - brier_score_loss(yy, pb),
                expected_cost(yy, pa) - expected_cost(yy, pb))

    point = stats(np.arange(len(a)))
    rng = np.random.RandomState(seed)
    draws = []
    for _ in range(n_boot):
        mi = block_indices(months, block_len, rng)
        r = stats(np.concatenate([rows_of[k] for k in mi]))
        if r is not None:
            draws.append(r)
    d = np.array(draws)
    out = {"n_valid_draws": len(d)}
    for j, k in enumerate(["AP", "Brier", "CostC5"]):
        out[f"Delta_{k}_Point"] = round(float(point[j]), 4)
        out[f"Delta_{k}_CI95_Low"] = round(float(np.percentile(d[:, j], 2.5)), 4)
        out[f"Delta_{k}_CI95_High"] = round(float(np.percentile(d[:, j], 97.5)), 4)
    out["Delta_AP_CI90_Low"] = round(float(np.percentile(d[:, 0], 5)), 4)
    out["Delta_AP_CI90_High"] = round(float(np.percentile(d[:, 0], 95)), 4)
    return out


def run_e12_moving_block_bootstrap():
    print("[E12] Paired moving-block bootstrap (L = 6, 12, 18 months; 1,000 replications)...")
    e03 = load_predictions("e03")
    comps = [("M1_EBM_CIxIQ", "M0_EBM_Additive"), ("M1_EBM_CIxIQ", "B4_XGBoost"), ("M1_EBM_CIxIQ", "B2_Threshold_Model"),
             ("M1_EBM_CIxIQ", "B1_Regularized_Linear"), ("M1_EBM_CIxIQ", "B0_Historical_Rule"), ("M0_EBM_Additive", "B0_Historical_Rule"),
             ("B3_Random_Forest", "B0_Historical_Rule"), ("B4_XGBoost", "B0_Historical_Rule")]
    jobs = []
    for wkey in ["all", "locked"]:
        label, fn = WINDOWS[wkey]
        w = e03[fn(e03)]
        for L in [6, 12, 18]:
            for ma, mb in comps:
                jobs.append(((label, L, ma, mb), delayed(paired_bootstrap)(w[w["model"] == ma], w[w["model"] == mb], L)))
    res = Parallel(n_jobs=min(N_JOBS, len(jobs)), backend="loky")(j for _, j in jobs)
    rows = []
    for (label, L, ma, mb), r in zip([k for k, _ in jobs], res):
        row = {"evaluation_window": label, "block_length_months": L, "model_A": ma, "model_B": mb, **r}
        row["AP_interval_excludes_minus_SESOI"] = bool(r["Delta_AP_CI95_Low"] > -SESOI_AP)
        row["AP_equivalent_TOST_90"] = bool(r["Delta_AP_CI90_Low"] > -SESOI_AP and r["Delta_AP_CI90_High"] < SESOI_AP)
        row["AP_gain_exceeds_SESOI_95"] = bool(r["Delta_AP_CI95_Low"] > SESOI_AP)
        rows.append(row)
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "e12_moving_block_bootstrap.csv"), index=False)

    cfg = {
        "project": "Replication-to-deployment evaluation of institution-conditioned exchange-rate stress early warning",
        "target_journal": "Expert Systems with Applications",
        "primary_target": "target_reer_vol_3m: RMS of monthly REER log changes over t+1..t+3 (forward rolling window)",
        "secondary_target": "target_res_drawdown_3m: maximum FX-reserve drawdown over t+1..t+3",
        "high_risk_threshold_rule": "80th percentile of the training targets of each fold (q75, q90 and country-specific q80 in E11)",
        "publication_lag_rules": {
            "bis_reer_and_us_neer": "+1 month (features use months up to t-1; month-t versions only in the E11 timing sensitivity)",
            "monthly_cpi_reserves": "+1 month",
            "monthly_ci_swift_fx_share": "+1 month in the main specification; 3, 6 and 12 months and a frozen-CI variant in E11",
            "quarterly_bis_credit": "+2 months after quarter end",
            "annual_worldbank_wgi_macro": "year Y from September of Y+1 (current WGI vintage; historical revisions not reconstructed)",
            "policy_rates": "0 months (announced rates)",
        },
        "temporal_protocol": {
            "sample_origins": "2012-01 to 2022-12 (Core-9, 132 months); confirmation origins 2023-01 to 2025-12 (step 9)",
            "development_folds": ["2017", "2018", "2019", "2020"],
            "retrospective_test_folds": ["2021", "2022"],
            "maturity_rule": "training and calibration origins satisfy origin + h + 1 < first test month (asserted)",
            "calibration_window_months": 8,
            "calibration_schemes": ["raw", "platt_8m", "platt_expanding"],
            "calibration_lock": "per model, lowest pooled Brier score on the development folds",
        },
        "random_seeds": SEEDS,
        "moving_block_bootstrap": {"block_lengths": [6, 12, 18], "replications": 1000},
        "smallest_effect_size_of_interest_AP": SESOI_AP,
        "threshold_regression": {"bootstrap_replications": int(os.environ.get("THRESH_NBOOT", 1999)), "p_value": "(1 + k) / (B + 1)",
                                 "trim_main": 0.01, "trim_sensitivity": [0.01, 0.05, 0.10, 0.15]},
    }
    with open(os.path.join(OUT_DIR, "experiment_config.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, sort_keys=False, allow_unicode=True)
    print("  - Saved e12_moving_block_bootstrap.csv and experiment_config.yaml")


def run_e21_paired_intervals():
    """Paired block-bootstrap intervals for every feature-set increment (Table 5), the matched Core-6 CI
    comparisons and the model-versus-persistence gaps of each robustness specification."""
    print("[E21] Paired intervals for ablation increments and robustness exceptions...")
    e45, e11 = load_predictions("e04_e05"), load_predictions("e11_robustness")
    jobs = []
    for wkey, L in [("all", 12), ("locked", 6)]:
        label, fn = WINDOWS[wkey]
        w = e45[fn(e45)]
        for m in ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive"]:
            base = w[(w["model"] == m) & (w["variant"] == "F0_Macro_Only")]
            for f, tag in [("F1_Macro_plus_CI", "+CI"), ("F2_Macro_plus_IQ", "+IQ"), ("F3_Macro_plus_CI_plus_IQ", "+CI+IQ")]:
                jobs.append(((label, L, "Feature ablation", m, f"{tag} vs macro"), w[(w["model"] == m) & (w["variant"] == f)], base))
        r = e11[fn(e11)]
        for m in ["B1_Regularized_Linear", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
            nb = r[(r["model"] == m) & (r["variant"] == "Core-6 matched: no CI")]
            for v in ["Core-6 matched: SWIFT share", "Core-6 matched: FX share", "Core-6 matched: both CI"]:
                jobs.append(((label, L, "Core-6 CI measure", m, f"{v.split(': ')[1]} vs no CI"), r[(r["model"] == m) & (r["variant"] == v)], nb))
        for v in r["variant"].unique():
            b0 = r[(r["variant"] == v) & (r["model"] == "B0_Historical_Rule")]
            if b0.empty:
                continue
            for m in ["B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
                a = r[(r["variant"] == v) & (r["model"] == m)]
                if len(a) == len(b0):
                    jobs.append(((label, L, "Robustness vs persistence", m, f"{v}: model vs B0"), a, b0))
    res = Parallel(n_jobs=min(N_JOBS, len(jobs)), backend="loky")(delayed(paired_bootstrap)(a, b, L) for (_, L, *_), a, b in jobs)
    rows = []
    for ((label, L, fam, m, comp), a, _), r in zip(jobs, res):
        rows.append({"evaluation_window": label, "block_length_months": L, "family": fam, "model": m, "comparison": comp,
                     "N": len(a), "N_pos": int(a["y_true_bin"].sum()), **r,
                     "AP_CI95_excludes_plus_SESOI": bool(r["Delta_AP_CI95_High"] < SESOI_AP),
                     "AP_CI95_excludes_minus_SESOI": bool(r["Delta_AP_CI95_Low"] > -SESOI_AP),
                     "AP_CI95_excludes_zero": bool(r["Delta_AP_CI95_Low"] > 0 or r["Delta_AP_CI95_High"] < 0),
                     "AP_equivalent_TOST_90": bool(r["Delta_AP_CI90_Low"] > -SESOI_AP and r["Delta_AP_CI90_High"] < SESOI_AP)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table16_e21_paired_intervals.csv"), index=False)
    print(f"  - Saved table16_e21_paired_intervals.csv ({len(rows)} comparisons)")


# ------------------------------------------------------------------------------------------------
# Figures 1-5
# ------------------------------------------------------------------------------------------------
def fig1_protocol(splits):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.2), gridspec_kw={"height_ratios": [1.0, 1.3]})
    fig.subplots_adjust(hspace=0.62)
    ax1.set_xlim(-15, 6); ax1.set_ylim(0.4, 4.9)
    ax1.axvline(0, color="#B22222", linestyle="--", linewidth=1.8, label="Forecast origin $t$ (month end)")
    ax1.axvspan(0, 3, color="#FADBD8", alpha=0.55, label="Target window $t+1..t+3$")
    ax1.axvspan(3, 4, color="#FDEBD0", alpha=0.75, label="Target published in $t+4$")
    for y, x0, x1, col in [(4.2, -14, 0, "#2E86C1"), (3.2, -5, 0, "#17A589"), (2.2, -1, 0, "#28B463"), (1.2, 0, 3, "#CB4335")]:
        ax1.broken_barh([(x0, x1 - x0)], (y - 0.3, 0.6), facecolors=col, alpha=0.85, edgecolor="black", linewidth=0.7)
    ax1.set_yticks([1.2, 2.2, 3.2, 4.2])
    ax1.set_yticklabels(["Target $V^{(3)}_{i,t}$", "Monthly: REER, NEER, CPI,\nreserves, CI (up to $t-1$)",
                         "Quarterly credit\n(+2 months)", "Annual WGI, macro\n(year $Y$ from Sept. $Y+1$)"])
    ax1.set_xlabel("Months relative to forecast origin $t$")
    ax1.set_title("(a) Information set at the forecast origin", fontweight="bold")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=3, frameon=False)
    ax1.grid(axis="x", linestyle=":", alpha=0.5)

    def yr(ym):
        return int(ym[:4]) + (int(ym[5:7]) - 1) / 12
    for i, (_, sp) in enumerate(splits.iloc[::-1].iterrows()):
        y = i + 1
        tr_e, cal_s, cal_e, te_s = yr(sp["train_end_origin"]) + 1 / 12, yr(sp["calib_start"]), yr(sp["calib_end_origin"]) + 1 / 12, yr(sp["test_start"])
        for x0, x1, col in [(2012, tr_e, "#2874A6"), (tr_e, cal_s, "#D5DBDB"), (cal_s, cal_e, "#F39C12"), (cal_e, te_s, "#D5DBDB"),
                            (te_s, te_s + 1, "#C0392B" if sp["role"] == "locked_test" else "#27AE60")]:
            ax2.broken_barh([(x0, x1 - x0)], (y - 0.32, 0.64), facecolors=col, edgecolor="black", linewidth=0.5)
    ax2.set_yticks(range(1, len(splits) + 1))
    ax2.set_yticklabels([("Retrospective test " if r == "locked_test" else "Development fold ") + t[:4] for r, t in zip(splits["role"][::-1], splits["test_start"][::-1])])
    ax2.set_xlim(2011.8, 2023.3); ax2.set_xlabel("Calendar year")
    ax2.set_title("(b) Expanding-window folds", fontweight="bold")
    ax2.legend(handles=[mpatches.Patch(color=c, label=l) for c, l in [("#2874A6", "Training origins"), ("#D5DBDB", "Maturity buffer"),
               ("#F39C12", "Calibration origins"), ("#27AE60", "Development test year"), ("#C0392B", "Retrospective test year")]],
               loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False)
    ax2.grid(axis="x", linestyle=":", alpha=0.5)
    save_fig(fig, "fig1_timeline_protocol")


def fig2_stress(panel):
    sub = core9_sample(panel)
    e03 = load_predictions("e03")
    lab = e03[e03["model"] == "B0_Historical_Rule"].set_index(["country", "ym"])["y_true_bin"]
    order = ["CHN", "POL", "HUN", "IND", "KOR", "MEX", "ZAF", "BRA", "RUS"]
    yms = sorted(sub["ym"].unique())
    q_first = float(sub[sub["ym"] <= "2015-08"]["target_reer_vol_3m"].quantile(0.80))
    mat = np.zeros((len(order), len(yms)))
    for i, c in enumerate(order):
        g = sub[sub["country"] == c].set_index("ym")["target_reer_vol_3m"]
        for j, ym in enumerate(yms):
            if (c, ym) in lab.index:
                mat[i, j] = 3 if lab[(c, ym)] == 1 else 2
            else:
                mat[i, j] = 1 if g.get(ym, 0) >= q_first else 0
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.0), gridspec_kw={"width_ratios": [1.45, 1.0]})
    cmap = matplotlib.colors.ListedColormap(["#EBF5FB", "#F5CBA7", "#D6EAF8", "#C0392B"])
    ax1.imshow(mat, aspect="auto", cmap=cmap, interpolation="nearest", vmin=0, vmax=3)
    ax1.set_yticks(range(len(order))); ax1.set_yticklabels(order)
    ticks = list(range(0, len(yms), 24)) + [len(yms) - 1]
    ax1.set_xticks(ticks); ax1.set_xticklabels([yms[k] for k in ticks], rotation=30)
    for ym, ls in [("2017-01", ":"), ("2021-01", "--")]:
        ax1.axvline(yms.index(ym), color="black", linestyle=ls, linewidth=1.3)
    ax1.set_title("(a) High-risk windows ($h=3$)", fontweight="bold"); ax1.set_xlabel("Forecast origin")
    ax1.legend(handles=[mpatches.Patch(color="#F5CBA7", label=f"Training period: above first-fold q80 ({q_first:.2f}%)"),
                        mpatches.Patch(color="#D6EAF8", label="Test years: normal"),
                        mpatches.Patch(color="#C0392B", label="Test years: high-risk evaluation label")],
               loc="upper left", fontsize=8.5, frameon=True)
    pal = dict(zip(order, ["#E74C3C", "#2980B9", "#16A085", "#2C3E50", "#7F8C8D", "#D35400", "#27AE60", "#F39C12", "#8E44AD"]))
    for c in order:
        g = sub[sub["country"] == c].sort_values("ym")
        ax2.plot(range(len(yms)), g["iq_mean_rt"].values, label=c, color=pal[c], linewidth=1.6)
    ax2.set_xticks(ticks); ax2.set_xticklabels([yms[k] for k in ticks], rotation=30)
    ax2.set_ylabel("WGI mean available at origin"); ax2.set_xlabel("Forecast origin")
    ax2.set_title("(b) Pseudo-real-time institutional quality", fontweight="bold")
    ax2.legend(loc="center left", bbox_to_anchor=(1.01, 0.5)); ax2.grid(True, linestyle=":", alpha=0.5)
    save_fig(fig, "fig2_data_coverage_stress_windows")


def fig3_models():
    t3 = pd.read_csv(os.path.join(TAB_DIR, "table3_e03_benchmark_comparison.csv"))
    t4 = pd.read_csv(os.path.join(TAB_DIR, "table4a_e04_feature_ablation.csv"))
    bt = pd.read_csv(os.path.join(TAB_DIR, "e12_moving_block_bootstrap.csv"))
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.5, 5.0))
    fig.subplots_adjust(wspace=0.45)
    y = np.arange(len(E03_MODELS))
    for k, (win, col, off) in enumerate([(WINDOWS["dev"][0], "#85C1E9", -0.2), (WINDOWS["locked"][0], "#C0392B", 0.2)]):
        w = t3[t3["evaluation_window"] == win].set_index("model").loc[E03_MODELS]
        ax1.barh(y + off, w["AP"], height=0.38, color=col, edgecolor="black", linewidth=0.5, label=f"{'Development 2017-20' if k == 0 else 'Retrospective test 2021-22'} (pooled)")
        ax1.scatter(w["AP_fold_mean"], y + off, marker="|", s=120, color="black", zorder=3, label="Fold-mean AP" if k == 0 else None)
        ax1.axvline(w["Pos_Rate"].iloc[0], color=col, linestyle=":", linewidth=1.2)
    ax1.set_yticks(y); ax1.set_yticklabels([SHORT[m] for m in E03_MODELS]); ax1.invert_yaxis()
    ax1.set_xlabel("Average precision"); ax1.set_title("(a) Benchmark (E03)", fontweight="bold")
    ax1.legend(loc="lower right", fontsize=8.5); ax1.grid(axis="x", linestyle=":", alpha=0.5)

    a = t4[t4["evaluation_window"] == WINDOWS["all"][0]]
    fl = ["F0_Macro_Only", "F1_Macro_plus_CI", "F2_Macro_plus_IQ", "F3_Macro_plus_CI_plus_IQ"]
    for m, col, ls in [("B1_Regularized_Linear", "#5D6D7E", "-"), ("B4_XGBoost", "#17A589", "-"), ("M0_EBM_Additive", "#F39C12", "--"), ("M1_EBM_CIxIQ", "#C0392B", "-")]:
        ax2.plot(range(4), [a[(a["model"] == m) & (a["feature_set"] == f)]["AP"].iloc[0] for f in fl], marker="o", color=col, linestyle=ls, linewidth=2, label=SHORT[m])
    ax2.set_xticks(range(4)); ax2.set_xticklabels(["Macro", "+CI", "+IQ", "+CI+IQ"])
    ax2.set_ylabel("Pooled AP, six folds 2017-2022"); ax2.set_title("(b) Feature ablation (E04)", fontweight="bold")
    ax2.legend(fontsize=8.5); ax2.grid(True, linestyle=":", alpha=0.5)

    b = bt[(bt["block_length_months"] == 12) & (bt["evaluation_window"] == WINDOWS["all"][0])]
    b = b[b["model_A"] == "M1_EBM_CIxIQ"]
    yy = np.arange(len(b))
    ax3.axvspan(-SESOI_AP, SESOI_AP, color="#D5D8DC", alpha=0.6, label=f"$\\pm${SESOI_AP} (smallest effect of interest)")
    ax3.errorbar(b["Delta_AP_Point"], yy, xerr=[b["Delta_AP_Point"] - b["Delta_AP_CI95_Low"], b["Delta_AP_CI95_High"] - b["Delta_AP_Point"]],
                 fmt="o", color="#C0392B", ecolor="#2C3E50", capsize=4)
    ax3.axvline(0, color="black", linestyle="--", linewidth=1)
    ax3.set_yticks(yy); ax3.set_yticklabels([f"M1 vs {SHORT[m].split()[0]}" for m in b["model_B"]])
    ax3.set_xlabel("$\\Delta$AP, 95% block-bootstrap interval"); ax3.set_title("(c) Paired bootstrap, $L=12$ (E12)", fontweight="bold")
    ax3.legend(fontsize=8.5, loc="lower left"); ax3.grid(True, linestyle=":", alpha=0.5)
    save_fig(fig, "fig3_model_comparison_bootstrap_ci")


def fig4_decision():
    bins = pd.read_csv(os.path.join(TAB_DIR, "e07_reliability_bins.csv"))
    cost = pd.read_csv(os.path.join(TAB_DIR, "table7a_e08_cost_decision_evaluation.csv"))
    topk = pd.read_csv(os.path.join(TAB_DIR, "table7b_e08_topk_monitoring_capacity.csv"))
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15.5, 5.0))
    fig.subplots_adjust(wspace=0.35)
    ax1.plot([0, 1], [0, 1], "k--", linewidth=1, label="Perfect calibration")
    for (m, sch), col, mk in [(("M1_EBM_CIxIQ", "raw"), "#E67E22", "s"), (("M1_EBM_CIxIQ", "platt_8m"), "#C0392B", "o"),
                              (("M1_EBM_CIxIQ", "platt_expanding"), "#8E44AD", "D"), (("B0_Historical_Rule", "raw"), "#2C3E50", "^")]:
        g = bins[(bins["model"] == m) & (bins["scheme"] == sch)].dropna(subset=["mean_pred_prob"])
        ax1.plot(g["mean_pred_prob"], g["empirical_pos_rate"], marker=mk, color=col, linewidth=1.6,
                 label=f"{SHORT[m].split()[0]} {sch.replace('_', ' ')}")
    ax1.set_xlim(0, 1); ax1.set_ylim(0, 1)
    ax1.set_xlabel("Mean predicted probability"); ax1.set_ylabel("Observed frequency")
    ax1.set_title("(a) Reliability, retrospective test", fontweight="bold"); ax1.legend(fontsize=8.5); ax1.grid(True, linestyle=":", alpha=0.5)

    c = cost[cost["evaluation_window"] == WINDOWS["all"][0]]
    ms = ["Rule_Never_Alert", "B0_Historical_Rule", "B1_Regularized_Linear", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]
    names = ["Never alert", "B0", "B1", "B3", "B4", "M0", "M1"]
    cols = ["#95A5A6", "#2C3E50", "#5D6D7E", "#2E86C1", "#17A589", "#F39C12", "#C0392B"]
    for i, (m, n, col) in enumerate(zip(ms, names, cols)):
        ax2.bar(np.arange(3) + (i - 3) * 0.11, [c[(c["model"] == m) & (c["C_FN"] == f)]["Total_Cost_per100"].iloc[0] for f in [2.0, 5.0, 10.0]],
                0.11, color=col, edgecolor="black", linewidth=0.4, label=n)
    ax2.set_xticks(range(3)); ax2.set_xticklabels(["$C_{FN}=2$", "$C_{FN}=5$", "$C_{FN}=10$"])
    ax2.set_ylabel("Expected cost per 100 forecasts"); ax2.set_title("(b) Asymmetric cost, six folds", fontweight="bold")
    ax2.legend(fontsize=8.5, ncol=2); ax2.grid(axis="y", linestyle=":", alpha=0.5)

    t = topk[topk["evaluation_window"] == WINDOWS["all"][0]]
    for m, col in [("B0_Historical_Rule", "#2C3E50"), ("B1_Regularized_Linear", "#5D6D7E"), ("B4_XGBoost", "#17A589"), ("M0_EBM_Additive", "#F39C12"), ("M1_EBM_CIxIQ", "#C0392B")]:
        ax3.plot([1, 2, 3], [100 * t[(t["model"] == m) & (t["monthly_quota_k"] == k)]["Recall_at_k"].iloc[0] for k in [1, 2, 3]], marker="o", color=col, linewidth=2, label=SHORT[m])
    ax3.plot([1, 2, 3], [100 * k / 9 for k in [1, 2, 3]], "k:", label="Random")
    ax3.set_xticks([1, 2, 3]); ax3.set_xlabel("Countries reviewed per month ($k$)"); ax3.set_ylabel("Recall of high-risk windows (%)")
    ax3.set_title("(c) Monthly review quota, six folds", fontweight="bold"); ax3.legend(fontsize=8.5); ax3.grid(True, linestyle=":", alpha=0.5)
    save_fig(fig, "fig4_calibration_and_decision_cost")


def fig5_explain():
    from scipy.ndimage import uniform_filter
    z = np.load(os.path.join(OUT_DIR, "e09_interaction_surface.npz"))
    ci, iq, surf, sd = z["ci_grid"], z["iq_grid"], z["mean_surface"], z["std_surface"]
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5.0))
    fig.subplots_adjust(wspace=0.42)
    masked = np.ma.masked_where(uniform_filter(z["H_dens"].astype(float), size=3) < 0.15, surf)
    im = ax1.contourf(ci, iq, masked.T, levels=14, cmap="RdYlBu_r")
    ax1.scatter(z["ci_obs"][::4], z["iq_obs"][::4], s=6, c="black", alpha=0.25, label="Observed (CI, IQ)")
    plt.colorbar(im, ax=ax1, fraction=0.046, pad=0.04, label="Log-odds")
    ax1.set_xlabel("Standardized FX share (CI)"); ax1.set_ylabel("Standardized IQ")
    ax1.set_title("(a) EBM CI x IQ surface", fontweight="bold"); ax1.legend(loc="lower right", fontsize=8.5)
    for v, lab, col in [(-0.8, "IQ = -0.8 sd", "#C0392B"), (0.0, "IQ = 0", "#F39C12"), (0.8, "IQ = +0.8 sd", "#2874A6")]:
        k = int(np.argmin(np.abs(iq - v)))
        ax2.plot(ci, surf[:, k], color=col, linewidth=2, label=lab)
        ax2.fill_between(ci, surf[:, k] - sd[:, k], surf[:, k] + sd[:, k], color=col, alpha=0.18)
    ax2.set_xlabel("Standardized FX share (CI)"); ax2.set_ylabel("Log-odds (mean $\\pm$ sd over folds)")
    ax2.set_title("(b) CI response by IQ level", fontweight="bold"); ax2.legend(fontsize=8.5); ax2.grid(True, linestyle=":", alpha=0.5)
    e03 = load_predictions("e03")
    m1 = e03[e03["model"] == "M1_EBM_CIxIQ"]
    yms = sorted(m1["ym"].unique())
    for c, col in [("RUS", "#8E44AD"), ("BRA", "#E67E22"), ("ZAF", "#27AE60"), ("CHN", "#2874A6")]:
        g = m1[m1["country"] == c].sort_values("ym")
        ax3.plot(range(len(yms)), g["prob_raw"].values, color=col, linewidth=1.7, label=c)
        hit = np.where(g["y_true_bin"].values == 1)[0]
        ax3.scatter(hit, np.full(len(hit), 1.02), marker="|", color=col, s=30)
    ax3.axhline(1 / 6, color="black", linestyle="--", linewidth=1, label="Alert threshold $\\tau=1/6$")
    t = list(range(0, len(yms), 12))
    ax3.set_xticks(t); ax3.set_xticklabels([yms[k][:4] for k in t])
    ax3.set_ylabel("M1 raw probability (ticks: high-risk labels)"); ax3.set_title("(c) M1 probabilities, 2017-2022", fontweight="bold")
    ax3.legend(fontsize=8.5, loc="upper left"); ax3.grid(True, linestyle=":", alpha=0.5)
    save_fig(fig, "fig5_ci_iq_interaction_explainability")


def generate_all_figures(panel, splits):
    print("[FIGURES] Figures 1-5...")
    fig1_protocol(splits)
    fig2_stress(panel)
    fig3_models()
    fig4_decision()
    fig5_explain()


if __name__ == "__main__":
    import sys
    panel, splits = load_panel(), load_splits()
    parts = sys.argv[1:] or ["e09", "e10", "e11", "e12", "e21", "figs"]
    if "e09" in parts:
        run_e09_explainability_and_stability(panel, splits)
    if "e10" in parts:
        run_e10_subperiod_analysis()
    if "e11" in parts:
        run_e11_robustness_matrix(panel, splits)
    if "e12" in parts:
        run_e12_moving_block_bootstrap()
    if "e21" in parts:
        run_e21_paired_intervals()
    if "figs" in parts:
        generate_all_figures(panel, splits)
    print("DONE: Step 5 completed successfully.")
