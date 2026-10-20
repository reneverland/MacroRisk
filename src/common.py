"""
Shared evaluation utilities: fold construction with target-maturity assertions, calibration schemes,
pooled and fold-mean metrics, and the row-level prediction store that feeds every table and figure.
"""

import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, roc_auc_score, brier_score_loss, log_loss,
                             mean_absolute_error, root_mean_squared_error)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
TAB_DIR = os.path.join(OUT_DIR, "tables")
PRED_DIR = os.path.join(OUT_DIR, "predictions")
MASTER_DIR = os.path.join(PRED_DIR, "master")
for _d in (TAB_DIR, PRED_DIR, MASTER_DIR):
    os.makedirs(_d, exist_ok=True)

SEEDS = [42, 1024, 2024, 3407, 7777]
STOCHASTIC = {"B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ", "M_Placebo_MacroInter", "M_Unrestricted_EBM"}
REER_RELEASE_LAG = 1          # the BIS releases the monthly REER of month m during month m+1
MAIN_END = "2022-12"          # last forecast origin of the main (retrospective) evaluation
N_JOBS = int(os.environ.get("MACRORISK_NJOBS", 48))
SESOI_AP = 0.02               # smallest AP improvement regarded as practically meaningful
TAU_C5 = 1.0 / 6.0


def ym_add(ym, k):
    return (pd.Period(ym, freq="M") + k).strftime("%Y-%m")


def maturity_cap(test_start, h, lag=REER_RELEASE_LAG):
    """Last forecast origin whose h-month target is complete and published before test_start."""
    return ym_add(test_start, -(h + lag + 1))


def assert_no_target_overlap(frames, test_start, h, lag=REER_RELEASE_LAG):
    for d in frames:
        if len(d):
            last = d["ym"].max()
            assert ym_add(last, h + lag) < test_start, f"target of origin {last} (h={h}) not published before {test_start}"


def seeds_for(model):
    return SEEDS if model in STOCHASTIC else [42]


def fold_frames(sub, sp, h=3):
    """Training, calibration and test frames of one split, capped so that no h-month target used for
    fitting or calibration is published on or after the first test month."""
    cap = maturity_cap(sp["test_start"], h)
    tr_end = min(sp["train_end_origin"], cap)
    cal_end = min(sp["calib_end_origin"], cap)
    df_tr = sub[(sub["ym"] >= sp["train_start"]) & (sub["ym"] <= tr_end)].copy()
    df_cal = sub[(sub["ym"] >= sp["calib_start"]) & (sub["ym"] <= cal_end)].copy()
    df_te = sub[(sub["ym"] >= sp["test_start"]) & (sub["ym"] <= sp["test_end"])].copy()
    assert_no_target_overlap([df_tr, df_cal], sp["test_start"], h)
    return df_tr, df_cal, df_te


def platt_calibrate(probs_calib, y_calib, probs_test):
    """Platt scaling on held-out probabilities; raw probabilities are returned when fewer than three
    events or non-events are available or when the fitted slope would invert the ranking."""
    probs_calib = np.clip(np.asarray(probs_calib, dtype=float), 1e-5, 1 - 1e-5)
    probs_test = np.clip(np.asarray(probs_test, dtype=float), 1e-5, 1 - 1e-5)
    y_calib = np.asarray(y_calib)
    if len(y_calib) < 15 or np.sum(y_calib == 1) < 3 or np.sum(y_calib == 0) < 3:
        return probs_test, False
    lc = np.log(probs_calib / (1 - probs_calib)).reshape(-1, 1)
    lt = np.log(probs_test / (1 - probs_test)).reshape(-1, 1)
    try:
        cal = LogisticRegression(C=1.0, solver="lbfgs", max_iter=200).fit(lc, y_calib)
        if cal.coef_[0][0] <= 0.05:
            return probs_test, False
        return np.clip(cal.predict_proba(lt)[:, 1], 1e-5, 1 - 1e-5), True
    except Exception:
        return probs_test, False


def add_expanding_calibration(pred, splits, h=3, keys=("experiment", "variant", "model")):
    """prob_cal_exp: Platt scaling fitted on all earlier out-of-sample predictions of the same model whose
    targets were published before the fold's first test month (raw probabilities in the first fold)."""
    pred = pred.copy()
    pred["prob_cal_exp"] = pred["prob_raw"]
    order = splits.sort_values("test_start")
    keys = [k for k in keys if k in pred.columns]
    for _, g in pred.groupby(keys, sort=False):
        for _, sp in order.iterrows():
            te = g.index[g["split_id"] == sp["split_id"]]
            if len(te) == 0:
                continue
            hist = g[(g["ym"] < sp["test_start"]) & (g["ym"] <= maturity_cap(sp["test_start"], h))]
            if len(hist):
                pred.loc[te, "prob_cal_exp"] = platt_calibrate(hist["prob_raw"], hist["y_true_bin"], g.loc[te, "prob_raw"])[0]
    return pred


CAL_SCHEMES = {"raw": "prob_raw", "platt_8m": "prob_cal", "platt_expanding": "prob_cal_exp"}


def lock_calibration(pred, keys=("experiment", "variant", "model")):
    """For each model choose the calibration scheme with the lowest pooled Brier score on the development
    folds and store the chosen probabilities in prob_dec (used by every decision analysis)."""
    pred = pred.copy()
    keys = [k for k in keys if k in pred.columns]
    pred["cal_scheme"] = "raw"
    pred["prob_dec"] = pred["prob_raw"]
    for _, g in pred.groupby(keys, sort=False):
        dev = g[g["role"] == "dev_expanding"]
        if dev.empty:
            continue
        briers = {k: brier_score_loss(dev["y_true_bin"], np.clip(dev[c], 1e-5, 1 - 1e-5)) for k, c in CAL_SCHEMES.items()}
        best = min(briers, key=briers.get)
        pred.loc[g.index, "cal_scheme"] = best
        pred.loc[g.index, "prob_dec"] = g[CAL_SCHEMES[best]]
    return pred


def expected_cost(y, p, c_fn=5.0, c_fp=1.0):
    tau = c_fp / (c_fp + c_fn)
    a = (np.asarray(p) >= tau).astype(int)
    y = np.asarray(y)
    return 100.0 * (c_fp * np.mean((a == 1) & (y == 0)) + c_fn * np.mean((a == 0) & (y == 1)))


def compute_metrics(df_pred, prob_col="prob_dec", cont_col="pred_cont"):
    y = df_pred["y_true_bin"].values
    p = np.clip(df_pred[prob_col].values, 1e-5, 1 - 1e-5)
    two = len(np.unique(y)) > 1
    out = {
        "N": len(df_pred),
        "N_pos": int(y.sum()),
        "Pos_Rate": round(float(np.mean(y)), 4),
        "AP": round(float(average_precision_score(y, p)), 4) if two else np.nan,
        "ROC_AUC": round(float(roc_auc_score(y, p)), 4) if two else np.nan,
        "Brier": round(float(brier_score_loss(y, p)), 4),
        "LogLoss": round(float(log_loss(y, p, labels=[0, 1])), 4),
        "Cost_C5_per100": round(expected_cost(y, p), 3),
    }
    if cont_col in df_pred.columns and df_pred[cont_col].notna().all():
        out["MAE"] = round(float(mean_absolute_error(df_pred["y_true_cont"], df_pred[cont_col])), 4)
        out["RMSE"] = round(float(root_mean_squared_error(df_pred["y_true_cont"], df_pred[cont_col])), 4)
    return out


def fold_mean_ap(df_pred, prob_col="prob_dec"):
    aps = [average_precision_score(g["y_true_bin"], g[prob_col]) for _, g in df_pred.groupby("split_id")
           if g["y_true_bin"].nunique() > 1]
    return round(float(np.mean(aps)), 4) if aps else np.nan


def summarize(df_pred, prob_col="prob_dec"):
    """Pooled metrics (all predictions of the window together) plus the fold-mean AP."""
    m = compute_metrics(df_pred, prob_col)
    m["AP_fold_mean"] = fold_mean_ap(df_pred, prob_col)
    if "prob_raw" in df_pred.columns:
        y = df_pred["y_true_bin"]
        for k, c in CAL_SCHEMES.items():
            if c in df_pred.columns:
                m[f"Brier_{k}"] = round(float(brier_score_loss(y, np.clip(df_pred[c], 1e-5, 1 - 1e-5))), 4)
    return m


WINDOWS = {
    "locked": ("Retrospective test 2021-2022", lambda d: d["role"] == "locked_test"),
    "dev": ("Development folds 2017-2020", lambda d: d["role"] == "dev_expanding"),
    "all": ("All six out-of-time folds 2017-2022", lambda d: d["role"].isin(["dev_expanding", "locked_test"])),
}

PRED_COLS = ["experiment", "variant", "model", "split_id", "role", "country", "ym", "threshold", "y_true_cont",
             "y_true_bin", "pred_cont", "prob_raw", "prob_cal", "prob_cal_exp", "prob_dec", "cal_scheme",
             "seed_agg", "n_seeds", "feature_info_cutoff_ym"]


def save_predictions(df, experiment):
    df = df.copy()
    df["experiment"] = experiment
    for c in PRED_COLS:
        if c not in df.columns:
            df[c] = np.nan
    extra = [c for c in df.columns if c not in PRED_COLS]
    df[PRED_COLS + extra].to_parquet(os.path.join(MASTER_DIR, f"{experiment}.parquet"), index=False)
    return df


def load_predictions(experiment):
    return pd.read_parquet(os.path.join(MASTER_DIR, f"{experiment}.parquet"))


def load_panel():
    return pd.read_csv(os.path.join(PROC_DIR, "panel_pseudo_realtime.csv"))


def load_splits():
    return pd.read_csv(os.path.join(OUT_DIR, "split_manifest.csv"))
