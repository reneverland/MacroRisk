#!/usr/bin/env python3
"""
Step 3: Unified Temporal Evaluation Framework for E03 (Benchmarks B0-B4, M0, M1),
        E04 (Feature Incremental Ablations), and E05 (CI x IQ Interaction Ablations)
====================================================================================
Training origins end in August of year T-2 and calibration origins run January-August of year T-1, so
every target used for fitting is published before the test year T (asserted in common.fold_frames).
Development folds test 2017-2020; the retrospective test covers 2021-2022. All row-level predictions
go to outputs/predictions/master/*.parquet; E04 and E05 reuse the E03 predictions of identical models.
"""

import os
import time
import yaml
import warnings
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, ElasticNet, LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    root_mean_squared_error,
)
from xgboost import XGBRegressor, XGBClassifier
from joblib import Parallel, delayed
from common import (SEEDS, N_JOBS, MAIN_END, TAB_DIR, PRED_DIR, OUT_DIR, PROC_DIR, fold_frames, platt_calibrate, seeds_for,
                    add_expanding_calibration, lock_calibration, compute_metrics, summarize, save_predictions, WINDOWS,
                    load_panel, load_splits)
from interpret.glassbox import ExplainableBoostingRegressor, ExplainableBoostingClassifier

warnings.filterwarnings("ignore")

# Feature groups (all strictly available at forecast origin t under pseudo-real-time protocol)
MACRO_COLS = [
    "reer_vol_hist_3m",
    "reer_vol_hist_6m",
    "reer_vol_hist_12m",
    "reer_ret_cum_3m",
    "cpi_yoy_lag1",
    "cpi_vol_rt",
    "fx_res_vol_rt",
    "fx_res_yoy_rt",
    "cg_gap_rt",
    "fin_depth_rt",
    "ln_gdp_pc_rt",
    "gdp_growth_rate_rt",
    "ln_pop_rt",
    "trade_openness_wb_rt",
    "fin_openness_proxy_rt",
    "unemp_rate_wb_rt",
    "policy_rate_diff_us",
    "usd_neer_ret_1m",
    "usd_neer_vol_3m",
]

CI_COLS_CORE9 = [
    "fx_share_rt",
    "fx_share_chg_12m_rt",
]

SWIFT_COLS = [
    "swift_share_rt",
    "swift_share_chg_12m_rt",
]

IQ_COLS = [
    "iq_mean_rt",
    "iq_data_age_m",
]


def build_feature_matrix(df, feature_cols, fit_imputer=None, fit_scaler=None):
    """Impute and standardize features strictly within the training window."""
    X_raw = df[feature_cols].copy()
    if fit_imputer is None:
        fit_imputer = SimpleImputer(strategy="median")
        X_imp = fit_imputer.fit_transform(X_raw)
    else:
        X_imp = fit_imputer.transform(X_raw)

    if fit_scaler is None:
        fit_scaler = StandardScaler()
        X_scaled = fit_scaler.fit_transform(X_imp)
    else:
        X_scaled = fit_scaler.transform(X_imp)

    return pd.DataFrame(X_scaled, columns=feature_cols, index=df.index), fit_imputer, fit_scaler


# EBM hyperparameter grid is pre-specified and selected only by inner temporal AP within the training window.
EBM_FIXED = dict(max_bins=32, max_interaction_bins=16, outer_bags=2, inner_bags=0, n_jobs=1)
EBM_GRID = [
    {"learning_rate": 0.01, "max_rounds": 50, "min_samples_leaf": 20, "max_leaves": 2},
    {"learning_rate": 0.01, "max_rounds": 150, "min_samples_leaf": 15, "max_leaves": 2},
    {"learning_rate": 0.02, "max_rounds": 300, "min_samples_leaf": 10, "max_leaves": 3},
    {"learning_rate": 0.03, "max_rounds": 600, "min_samples_leaf": 8, "max_leaves": 3},
]
EBM_MODELS = ["M0_EBM_Additive", "M1_EBM_CIxIQ", "M_Placebo_MacroInter", "M_Unrestricted_EBM"]


def make_inner_splits(df_train):
    """3 inner expanding temporal folds inside the training window with a 3-month maturity gap."""
    ym_unique = sorted(df_train["ym"].unique())
    n_ym = len(ym_unique)
    inner_splits = []
    for k in range(3):
        cut_idx = int(n_ym * (0.55 + 0.12 * k))
        val_end_idx = min(n_ym - 1, cut_idx + 8)
        tr_ym = ym_unique[: max(12, cut_idx - 3)]
        va_ym = ym_unique[cut_idx:val_end_idx]
        tr_mask = (df_train["ym"].isin(tr_ym)).values
        va_mask = (df_train["ym"].isin(va_ym)).values
        if tr_mask.sum() >= 30 and va_mask.sum() >= 10:
            inner_splits.append((tr_mask, va_mask))
    return inner_splits


def ebm_interaction_spec(model_code, columns, ci_col="fx_share_rt", iq_col="iq_mean_rt"):
    if model_code == "M1_EBM_CIxIQ":
        return [(ci_col, iq_col)] if (ci_col in columns and iq_col in columns) else 0
    if model_code == "M_Placebo_MacroInter":
        pair = ("ln_gdp_pc_rt", "trade_openness_wb_rt")
        return [pair] if all(c in columns for c in pair) else 0
    if model_code == "M_Unrestricted_EBM":
        return 10
    return 0


def select_ebm_config(X_tr, y_bin_tr, inner_splits, inter_spec, seed):
    best_cfg, best_ap = EBM_GRID[0], -np.inf
    for cfg in EBM_GRID:
        aps = []
        for tr_m, va_m in inner_splits:
            if len(np.unique(y_bin_tr[tr_m])) < 2 or len(np.unique(y_bin_tr[va_m])) < 2:
                continue
            c = ExplainableBoostingClassifier(interactions=inter_spec, random_state=seed, **EBM_FIXED, **cfg)
            c.fit(X_tr.iloc[tr_m], y_bin_tr[tr_m])
            aps.append(average_precision_score(y_bin_tr[va_m], c.predict_proba(X_tr.iloc[va_m])[:, 1]))
        if aps and np.mean(aps) > best_ap:
            best_ap, best_cfg = float(np.mean(aps)), cfg
    return best_cfg


def fit_predict_threshold_model(df_train, y_train_cont, y_train_bin, df_eval, feature_cols, ci_col="fx_share_rt", iq_col="iq_mean_rt"):
    """
    B2 Benchmark: Panel Threshold Forecasting Model (continuous & binary).
    Searches over IQ threshold gamma in training window, then fits regime-specific CI slopes + Ridge/Logit controls.
    """
    imp = SimpleImputer(strategy="median")
    scl = StandardScaler()
    X_tr = pd.DataFrame(scl.fit_transform(imp.fit_transform(df_train[feature_cols])), columns=feature_cols, index=df_train.index)
    X_ev = pd.DataFrame(scl.transform(imp.transform(df_eval[feature_cols])), columns=feature_cols, index=df_eval.index)

    q_tr = df_train[iq_col].fillna(df_train[iq_col].median()).values
    q_ev = df_eval[iq_col].fillna(df_train[iq_col].median()).values
    ci_tr = X_tr[ci_col].values if ci_col in X_tr.columns else np.zeros(len(X_tr))
    ci_ev = X_ev[ci_col].values if ci_col in X_ev.columns else np.zeros(len(X_ev))

    qs = np.quantile(q_tr, np.linspace(0.15, 0.85, 25))
    best_gamma = float(np.median(q_tr))
    best_loss = np.inf

    base_tr = X_tr.values
    for g in np.unique(qs):
        r1 = ci_tr * (q_tr <= g)
        r2 = ci_tr * (q_tr > g)
        Aug = np.column_stack([base_tr, r1, r2, (q_tr <= g).astype(float)])
        reg = Ridge(alpha=10.0).fit(Aug, y_train_cont)
        loss = np.mean((y_train_cont - reg.predict(Aug)) ** 2)
        if loss < best_loss:
            best_loss = loss
            best_gamma = float(g)

    Aug_tr = np.column_stack([base_tr, ci_tr * (q_tr <= best_gamma), ci_tr * (q_tr > best_gamma), (q_tr <= best_gamma).astype(float)])
    Aug_ev = np.column_stack([X_ev.values, ci_ev * (q_ev <= best_gamma), ci_ev * (q_ev > best_gamma), (q_ev <= best_gamma).astype(float)])

    reg_final = Ridge(alpha=10.0).fit(Aug_tr, y_train_cont)
    pred_cont = np.maximum(0.05, reg_final.predict(Aug_ev))

    if len(np.unique(y_train_bin)) > 1:
        clf_final = LogisticRegression(C=0.3, class_weight="balanced", max_iter=300).fit(Aug_tr, y_train_bin)
        pred_prob = clf_final.predict_proba(Aug_ev)[:, 1]
    else:
        pred_prob = np.full(len(df_eval), float(np.mean(y_train_bin)))

    return pred_cont, pred_prob, best_gamma


def inner_temporal_tune_and_fit(model_code, df_train, y_cont_tr, y_bin_tr, df_calib, y_bin_cal, df_test, feature_cols, ci_col="fx_share_rt", iq_col="iq_mean_rt", seed=42):
    """
    Tune hyperparameters using 3 inner expanding temporal folds inside `df_train` (budget <= 30 trials),
    fit on `df_train`, calibrate probabilities on `df_calib`, and predict on `df_test`.
    """
    t0 = time.time()

    # B0: Historical Persistence & Base Rate
    if model_code == "B0_Historical_Rule":
        med_tr = float(np.median(y_cont_tr))
        pred_cont_test = df_test["reer_vol_hist_3m"].fillna(med_tr).values
        # Probability proxy from empirical CDF of historical 3m volatility in training set
        hist_tr = df_train["reer_vol_hist_3m"].fillna(med_tr).values
        hist_cal = df_calib["reer_vol_hist_3m"].fillna(med_tr).values
        hist_te = pred_cont_test
        # Fit simple 1-variable logistic on historical risk in training window
        lr0 = LogisticRegression(C=1.0).fit(hist_tr.reshape(-1, 1), y_bin_tr)
        p_raw_cal = lr0.predict_proba(hist_cal.reshape(-1, 1))[:, 1]
        p_raw_te = lr0.predict_proba(hist_te.reshape(-1, 1))[:, 1]
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_test, p_raw_te, p_cal_te, time.time() - t0

    # Country-identity baselines: country fixed effects only, and fixed effects plus lagged REER volatility
    if model_code in ("C0_Country_Dummies", "C1_Country_plus_Persistence"):
        cats = sorted(df_train["country"].unique())

        def design(d):
            X = (np.asarray(d["country"], dtype=object)[:, None] == np.array(cats, dtype=object)[None, :]).astype(float)
            if model_code == "C1_Country_plus_Persistence":
                h = d["reer_vol_hist_3m"].fillna(float(df_train["reer_vol_hist_3m"].median())).values
                X = np.column_stack([X, (h - df_train["reer_vol_hist_3m"].mean()) / df_train["reer_vol_hist_3m"].std()])
            return X
        clf = LogisticRegression(C=1.0, max_iter=500).fit(design(df_train), y_bin_tr)
        p_raw_cal, p_raw_te = clf.predict_proba(design(df_calib))[:, 1], clf.predict_proba(design(df_test))[:, 1]
        cmean = pd.Series(y_cont_tr, index=df_train["country"].values).groupby(level=0).mean()
        pred_cont_te = df_test["country"].map(cmean).fillna(float(np.mean(y_cont_tr))).values
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_te, p_raw_te, p_cal_te, time.time() - t0

    # B2: Panel Threshold Forecasting Model
    if model_code == "B2_Threshold_Model":
        _, p_raw_cal, _ = fit_predict_threshold_model(df_train, y_cont_tr, y_bin_tr, df_calib, feature_cols, ci_col, iq_col)
        pred_cont_te, p_raw_te, _ = fit_predict_threshold_model(df_train, y_cont_tr, y_bin_tr, df_test, feature_cols, ci_col, iq_col)
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_te, p_raw_te, p_cal_te, time.time() - t0

    # Standardize features strictly on df_train
    X_tr, imp, scl = build_feature_matrix(df_train, feature_cols)
    X_cal, _, _ = build_feature_matrix(df_calib, feature_cols, imp, scl)
    X_te, _, _ = build_feature_matrix(df_test, feature_cols, imp, scl)

    inner_splits = make_inner_splits(df_train)

    # B1: Regularized Linear (ElasticNet/Ridge) & Logistic
    if model_code in ["B1_Regularized_Linear", "B1_Linear_CIxIQ"]:
        if model_code == "B1_Linear_CIxIQ" and (ci_col in X_tr.columns) and (iq_col in X_tr.columns):
            for X_mat in (X_tr, X_cal, X_te):
                X_mat["ci_x_iq_linear"] = X_mat[ci_col] * X_mat[iq_col]
                X_mat["ci_sq"] = X_mat[ci_col] ** 2
                X_mat["iq_sq"] = X_mat[iq_col] ** 2

        best_alpha = 10.0
        best_mae = np.inf
        for alpha in [0.5, 2.0, 5.0, 15.0, 50.0]:
            maes = []
            for tr_m, va_m in inner_splits:
                m = Ridge(alpha=alpha, random_state=seed).fit(X_tr.iloc[tr_m], y_cont_tr[tr_m])
                maes.append(mean_absolute_error(y_cont_tr[va_m], m.predict(X_tr.iloc[va_m])))
            if np.mean(maes) < best_mae:
                best_mae = np.mean(maes)
                best_alpha = alpha

        reg = Ridge(alpha=best_alpha, random_state=seed).fit(X_tr, y_cont_tr)
        pred_cont_te = np.maximum(0.05, reg.predict(X_te))

        best_C = 0.2
        best_ap = -np.inf
        for C_val in [0.05, 0.1, 0.3, 1.0, 3.0]:
            aps = []
            for tr_m, va_m in inner_splits:
                if len(np.unique(y_bin_tr[tr_m])) < 2 or len(np.unique(y_bin_tr[va_m])) < 2:
                    continue
                clf = LogisticRegression(C=C_val, penalty="l2", solver="lbfgs", max_iter=300, random_state=seed)
                clf.fit(X_tr.iloc[tr_m], y_bin_tr[tr_m])
                aps.append(average_precision_score(y_bin_tr[va_m], clf.predict_proba(X_tr.iloc[va_m])[:, 1]))
            if aps and np.mean(aps) > best_ap:
                best_ap = np.mean(aps)
                best_C = C_val

        clf = LogisticRegression(C=best_C, penalty="l2", solver="lbfgs", max_iter=300, random_state=seed)
        clf.fit(X_tr, y_bin_tr)
        p_raw_cal = clf.predict_proba(X_cal)[:, 1]
        p_raw_te = clf.predict_proba(X_te)[:, 1]
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_te, p_raw_te, p_cal_te, time.time() - t0

    # B3: Random Forest
    if model_code == "B3_Random_Forest":
        rf_grid = [
            {"max_depth": 3, "min_samples_leaf": 12, "max_features": "sqrt"},
            {"max_depth": 4, "min_samples_leaf": 8, "max_features": "sqrt"},
            {"max_depth": 5, "min_samples_leaf": 6, "max_features": 0.5},
            {"max_depth": 6, "min_samples_leaf": 10, "max_features": 0.6},
        ]
        best_cfg = rf_grid[1]
        best_ap = -np.inf
        for cfg in rf_grid:
            aps = []
            for tr_m, va_m in inner_splits:
                if len(np.unique(y_bin_tr[va_m])) < 2:
                    continue
                c = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1, **cfg)
                c.fit(X_tr.iloc[tr_m], y_bin_tr[tr_m])
                aps.append(average_precision_score(y_bin_tr[va_m], c.predict_proba(X_tr.iloc[va_m])[:, 1]))
            if aps and np.mean(aps) > best_ap:
                best_ap = np.mean(aps)
                best_cfg = cfg

        reg = RandomForestRegressor(n_estimators=100, random_state=seed, n_jobs=1, **best_cfg).fit(X_tr, y_cont_tr)
        pred_cont_te = np.maximum(0.05, reg.predict(X_te))

        clf = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=1, **best_cfg).fit(X_tr, y_bin_tr)
        p_raw_cal = clf.predict_proba(X_cal)[:, 1]
        p_raw_te = clf.predict_proba(X_te)[:, 1]
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_te, p_raw_te, p_cal_te, time.time() - t0

    # B4: XGBoost Strong Benchmark
    if model_code == "B4_XGBoost":
        xgb_grid = [
            {"max_depth": 2, "learning_rate": 0.03, "n_estimators": 90, "subsample": 0.8, "colsample_bytree": 0.7, "reg_lambda": 5.0, "min_child_weight": 8},
            {"max_depth": 3, "learning_rate": 0.04, "n_estimators": 110, "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 8.0, "min_child_weight": 10},
            {"max_depth": 2, "learning_rate": 0.05, "n_estimators": 80, "subsample": 0.75, "colsample_bytree": 0.7, "reg_lambda": 12.0, "min_child_weight": 12},
            {"max_depth": 4, "learning_rate": 0.03, "n_estimators": 100, "subsample": 0.85, "colsample_bytree": 0.75, "reg_lambda": 10.0, "min_child_weight": 10},
        ]
        best_cfg = xgb_grid[0]
        best_ap = -np.inf
        for cfg in xgb_grid:
            aps = []
            for tr_m, va_m in inner_splits:
                if len(np.unique(y_bin_tr[va_m])) < 2:
                    continue
                c = XGBClassifier(random_state=seed, eval_metric="logloss", verbosity=0, n_jobs=1, **cfg)
                c.fit(X_tr.iloc[tr_m], y_bin_tr[tr_m])
                aps.append(average_precision_score(y_bin_tr[va_m], c.predict_proba(X_tr.iloc[va_m])[:, 1]))
            if aps and np.mean(aps) > best_ap:
                best_ap = np.mean(aps)
                best_cfg = cfg

        reg = XGBRegressor(random_state=seed, verbosity=0, n_jobs=1, **best_cfg).fit(X_tr, y_cont_tr)
        pred_cont_te = np.maximum(0.05, reg.predict(X_te))

        clf = XGBClassifier(random_state=seed, eval_metric="logloss", verbosity=0, n_jobs=1, **best_cfg).fit(X_tr, y_bin_tr)
        p_raw_cal = clf.predict_proba(X_cal)[:, 1]
        p_raw_te = clf.predict_proba(X_te)[:, 1]
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_te, p_raw_te, p_cal_te, time.time() - t0

    # M0 / M1 / E05 Explainable Boosting Machine (EBM) variants
    if model_code in EBM_MODELS:
        inter_spec = ebm_interaction_spec(model_code, list(X_tr.columns), ci_col, iq_col)
        best_cfg = select_ebm_config(X_tr, y_bin_tr, inner_splits, inter_spec, seed)

        reg = ExplainableBoostingRegressor(interactions=inter_spec, random_state=seed, **EBM_FIXED, **best_cfg)
        reg.fit(X_tr, y_cont_tr)
        pred_cont_te = np.maximum(0.05, reg.predict(X_te))

        clf = ExplainableBoostingClassifier(interactions=inter_spec, random_state=seed, **EBM_FIXED, **best_cfg)
        clf.fit(X_tr, y_bin_tr)
        p_raw_cal = clf.predict_proba(X_cal)[:, 1]
        p_raw_te = clf.predict_proba(X_te)[:, 1]
        p_cal_te, _ = platt_calibrate(p_raw_cal, y_bin_cal, p_raw_te)
        return pred_cont_te, p_raw_te, p_cal_te, time.time() - t0

    raise ValueError(f"Unknown model_code: {model_code}")



def _fit_task(sub, sp, variant, m_code, fcols, seed, h, target, ci_col, iq_col, q=0.80, cty=False, freeze_cols=None):
    df_tr, df_cal, df_te = fold_frames(sub, sp, h)
    df_tr, df_cal, df_te = (d.dropna(subset=[target]) for d in (df_tr, df_cal, df_te))
    if freeze_cols:
        # CI held at its value at the last training origin (no CI update after the training cut-off)
        last = df_tr.sort_values("ym").groupby("country")[freeze_cols].last()
        for d in (df_cal, df_te):
            d[freeze_cols] = last.reindex(d["country"]).values
    if cty:
        thr_map = df_tr.groupby("country")[target].quantile(q)
        thr_tr, thr_cal, thr_te = (d["country"].map(thr_map).values for d in (df_tr, df_cal, df_te))
    else:
        thr_tr = thr_cal = thr_te = np.full(1, float(df_tr[target].quantile(q)))
    y_tr, y_cal, y_te = (d[target].values for d in (df_tr, df_cal, df_te))
    c_te, pr_te, pc_te, el = inner_temporal_tune_and_fit(
        m_code, df_tr, y_tr, (y_tr >= thr_tr).astype(int), df_cal, (y_cal >= thr_cal).astype(int), df_te, fcols,
        ci_col=ci_col, iq_col=iq_col, seed=seed)
    meta = df_te[["country", "ym", "in_swift6", "in_core9", "feature_info_cutoff_ym"]].reset_index(drop=True)
    return dict(variant=variant, model=m_code, split_id=sp["split_id"], role=sp["role"], seed=seed, meta=meta,
                threshold=np.broadcast_to(thr_te, len(df_te)).copy(), y_true_cont=y_te, pred_cont=c_te, prob_raw=pr_te,
                prob_cal=pc_te, sec=el)


def run_grid(sub, splits, specs, h=3, target="target_reer_vol_3m", n_jobs=N_JOBS):
    """specs: list of dicts with keys variant, model, fcols and optional ci_col / iq_col.
    Fits every (spec, split, seed) in parallel and returns seed-averaged predictions plus a runtime log."""
    tasks = []
    specs_h = {spec["variant"]: spec.get("h", h) for spec in specs}
    for spec in specs:
        for _, sp in splits.iterrows():
            for sd in seeds_for(spec["model"]):
                tasks.append(delayed(_fit_task)(spec.get("sub", sub), sp.to_dict(), spec["variant"], spec["model"], spec["fcols"], sd,
                                                spec.get("h", h), spec.get("target", target),
                                                spec.get("ci_col", "fx_share_rt"), spec.get("iq_col", "iq_mean_rt"),
                                                spec.get("q", 0.80), spec.get("cty", False), spec.get("freeze_cols")))
    res = Parallel(n_jobs=n_jobs, backend="loky", verbose=0)(tasks)
    groups = {}
    for r in res:
        groups.setdefault((r["variant"], r["model"], r["split_id"]), []).append(r)
    rows, runtime = [], []
    for (variant, model, split_id), rs in groups.items():
        rs = sorted(rs, key=lambda r: r["seed"])
        d = rs[0]["meta"].copy()
        d["variant"], d["model"], d["split_id"], d["role"] = variant, model, split_id, rs[0]["role"]
        d["threshold"] = rs[0]["threshold"]
        d["y_true_cont"] = rs[0]["y_true_cont"]
        d["y_true_bin"] = (d["y_true_cont"] >= d["threshold"]).astype(int)
        for k in ("pred_cont", "prob_raw", "prob_cal"):
            d[k] = np.mean([r[k] for r in rs], axis=0)
        d["prob_cal_seed_std"] = np.std([r["prob_cal"] for r in rs], axis=0)
        d["n_seeds"] = len(rs)
        d["seed_agg"] = f"mean_of_{len(rs)}_seeds" if len(rs) > 1 else "single_seed_42"
        rows.append(d)
        runtime.append({"variant": variant, "split_id": split_id, "model": model, "n_seeds": len(rs),
                        "mean_sec_per_seed": round(float(np.mean([r["sec"] for r in rs])), 3),
                        "total_sec": round(float(np.sum([r["sec"] for r in rs])), 3)})
    pred = pd.concat(rows, ignore_index=True)
    pred = pd.concat([add_expanding_calibration(g, splits, h=specs_h.get(v, h)) for v, g in pred.groupby("variant", sort=False)])
    pred = pred.reset_index(drop=True)
    pred = lock_calibration(pred)
    return pred, pd.DataFrame(runtime)


def summary_table(pred, by, extra_windows=()):
    rows = []
    windows = list(WINDOWS.values()) + list(extra_windows)
    for label, fn in windows:
        w = pred[fn(pred)]
        for key, g in w.groupby(by, sort=False):
            key = key if isinstance(key, tuple) else (key,)
            rows.append({"evaluation_window": label, **dict(zip(by, key)), **summarize(g), "cal_scheme": g["cal_scheme"].iloc[0]})
    return pd.DataFrame(rows)


E03_MODELS = ["B0_Historical_Rule", "B1_Regularized_Linear", "B2_Threshold_Model", "B3_Random_Forest",
              "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]


def core9_sample(panel):
    return panel[(panel["in_core9"] == 1) & (panel["ym"] >= "2012-01") & (panel["ym"] <= MAIN_END)].copy()


def run_e03_benchmarks(panel, splits):
    print("[E03] Benchmarks B0-B4, M0, M1 over six out-of-time folds (5 seeds for stochastic learners)...")
    sub = core9_sample(panel)
    full = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    pred, runtime = run_grid(sub, splits, [dict(variant="F3_Macro_plus_CI_plus_IQ", model=m, fcols=full) for m in E03_MODELS])
    pred = save_predictions(pred, "e03")
    pred.to_csv(os.path.join(PRED_DIR, "e03_oos_predictions.csv"), index=False)
    runtime.to_csv(os.path.join(TAB_DIR, "e12_computational_runtime.csv"), index=False)
    core6 = ("Retrospective test 2021-2022, Core-6 SWIFT countries", lambda d: (d["role"] == "locked_test") & (d["in_swift6"] == 1))
    tab = summary_table(pred, ["model"], extra_windows=[core6])
    tab.to_csv(os.path.join(TAB_DIR, "table3_e03_benchmark_comparison.csv"), index=False)
    print(tab[tab.evaluation_window.str.startswith("Retro")][["evaluation_window", "model", "N", "N_pos", "AP", "AP_fold_mean", "Brier", "cal_scheme"]].to_string())
    return pred


def run_e04_e05_ablations(panel, splits, e03):
    print("[E04 & E05] Feature and interaction ablations (identical models reuse the E03 predictions)...")
    sub = core9_sample(panel)
    feature_sets = {
        "F0_Macro_Only": MACRO_COLS,
        "F1_Macro_plus_CI": MACRO_COLS + CI_COLS_CORE9,
        "F2_Macro_plus_IQ": MACRO_COLS + IQ_COLS,
    }
    e04_models = ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]
    specs = [dict(variant=f, model=m, fcols=c) for f, c in feature_sets.items() for m in e04_models]
    full = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    specs += [dict(variant="F3_Macro_plus_CI_plus_IQ", model=m, fcols=full) for m in ["B1_Linear_CIxIQ", "M_Placebo_MacroInter", "M_Unrestricted_EBM"]]
    new, _ = run_grid(sub, splits, specs)
    pred = pd.concat([e03, new], ignore_index=True)
    pred = save_predictions(pred.drop(columns=["experiment"], errors="ignore"), "e04_e05")
    pred.to_csv(os.path.join(PRED_DIR, "e04_feature_ablation_predictions.csv"), index=False)

    e04 = pred[pred["model"].isin(e04_models)]
    rows = []
    for label, fn in [WINDOWS["all"], WINDOWS["locked"]]:
        w = e04[fn(e04)]
        for m in e04_models:
            base = summarize(w[(w["model"] == m) & (w["variant"] == "F0_Macro_Only")])
            for f in list(feature_sets) + ["F3_Macro_plus_CI_plus_IQ"]:
                met = summarize(w[(w["model"] == m) & (w["variant"] == f)])
                rows.append({"evaluation_window": label, "model": m, "feature_set": f, **met,
                             "Delta_AP_vs_Macro": round(met["AP"] - base["AP"], 4),
                             "Delta_AP_fold_mean_vs_Macro": round(met["AP_fold_mean"] - base["AP_fold_mean"], 4),
                             "Delta_CostC5_vs_Macro": round(met["Cost_C5_per100"] - base["Cost_C5_per100"], 3)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table4a_e04_feature_ablation.csv"), index=False)

    inter = ["M0_EBM_Additive", "B1_Regularized_Linear", "B1_Linear_CIxIQ", "M_Placebo_MacroInter", "M_Unrestricted_EBM", "M1_EBM_CIxIQ"]
    e05 = pred[(pred["variant"] == "F3_Macro_plus_CI_plus_IQ") & pred["model"].isin(inter)]
    rows = []
    for label, fn in [WINDOWS["all"], WINDOWS["locked"]]:
        w = e05[fn(e05)]
        m0 = summarize(w[w["model"] == "M0_EBM_Additive"])
        for m in inter:
            met = summarize(w[w["model"] == m])
            rows.append({"evaluation_window": label, "interaction_spec": m, **met,
                         "Delta_AP_vs_M0": round(met["AP"] - m0["AP"], 4),
                         "Delta_AP_fold_mean_vs_M0": round(met["AP_fold_mean"] - m0["AP_fold_mean"], 4),
                         "Delta_CostC5_vs_M0": round(met["Cost_C5_per100"] - m0["Cost_C5_per100"], 3)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table4b_e05_interaction_ablation.csv"), index=False)
    print("  - Saved table4a_e04_feature_ablation.csv and table4b_e05_interaction_ablation.csv")
    return pred


if __name__ == "__main__":
    panel = load_panel()
    splits = load_splits()
    e03 = run_e03_benchmarks(panel, splits)
    run_e04_e05_ablations(panel, splits, e03)
    print("DONE: Step 3 (E03, E04, E05) completed successfully.")
