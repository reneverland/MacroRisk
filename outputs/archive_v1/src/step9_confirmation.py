#!/usr/bin/env python3
"""
Step 9: pre-registered confirmation period (forecast origins 2023-01 to 2025-12)
================================================================================
`python step9_confirmation.py protocol` writes outputs/confirmation/confirmation_protocol.yaml using only
information from the main study (origins <= 2022-12) and records its SHA-256 hash.
`python step9_confirmation.py score` verifies the hash, refuses to run twice, fits the pre-specified
models in expanding folds and scores the 2023-2025 test years once.

The confirmation uses macro and institutional-quality features only, because the FX-share (CI) series
of the original data export ends before 2023. It covers the Core-9 and the six external economies.
"""

import os
import sys
import json
import hashlib
import datetime
import warnings
import yaml
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score

from common import (BASE_DIR, OUT_DIR, TAB_DIR, N_JOBS, SEEDS, SESOI_AP, TAU_C5, fold_frames, seeds_for, maturity_cap,
                    summarize, expected_cost, load_predictions, load_panel)
from step3_e03_e05_benchmarks_and_ablations import MACRO_COLS, IQ_COLS, inner_temporal_tune_and_fit
from step4_e06_e08_loco_calib_decision import ece
from step5_e09_e12_explain_robust_figs import block_indices

warnings.filterwarnings("ignore")
CONF_DIR = os.path.join(OUT_DIR, "confirmation")
os.makedirs(CONF_DIR, exist_ok=True)
PROTO = os.path.join(CONF_DIR, "confirmation_protocol.yaml")
HASH = os.path.join(CONF_DIR, "confirmation_protocol.sha256")
LOCK = os.path.join(CONF_DIR, "SCORED.lock")
CORE9 = ["BRA", "CHN", "HUN", "IND", "KOR", "MEX", "POL", "RUS", "ZAF"]
EXT6 = ["TUR", "IDN", "THA", "MYS", "CHL", "COL"]
CANDIDATES = ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive"]
RAW_FILES = ["bis_reer.csv", "bis_neer_us.csv", "bis_cpi.csv", "bis_cbpol.csv", "bis_credit_tc.csv", "bis_credit_gap.csv",
             "imf_ifs_reserves_monthly.csv", "vintage_202610/imf_irfcl_reserves_monthly.csv", "worldbank_annual.csv"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def conf_splits():
    rows = []
    for T in range(2021, 2026):
        rows.append({"split_id": f"CONF_{T}", "role": "warmup" if T <= 2022 else "confirmation", "train_start": "2012-01",
                     "train_end_origin": f"{T - 2}-08", "calib_start": f"{T - 1}-01", "calib_end_origin": f"{T - 1}-08",
                     "test_start": f"{T}-01", "test_end": f"{T}-12"})
    return pd.DataFrame(rows)


def fallback_decision(hist, learned, delta, ece_cap):
    """hist: matured out-of-sample predictions of the last 12 origins (both models). Returns the model to deploy."""
    hl, hb = hist[hist["model"] == learned], hist[hist["model"] == "B0_Historical_Rule"]
    y = hl["y_true_bin"].values
    if len(hl) == 0 or y.min() == y.max():
        return "B0_Historical_Rule", np.nan, np.nan
    gain = average_precision_score(y, hl["prob_raw"]) - average_precision_score(hb["y_true_bin"], hb["prob_raw"])
    e = ece(y, np.clip(hl["prob_raw"].values, 1e-5, 1 - 1e-5))[0]
    return (learned if (gain >= delta and e <= ece_cap) else "B0_Historical_Rule"), round(float(gain), 4), e


# ------------------------------------------------------------------------------------------------
# Protocol (uses only main-study information)
# ------------------------------------------------------------------------------------------------
def write_protocol():
    if os.path.exists(HASH):
        sys.exit("Protocol already frozen; refusing to overwrite.")
    e45 = load_predictions("e04_e05")
    e03 = load_predictions("e03")
    f2 = e45[(e45["variant"] == "F2_Macro_plus_IQ") & (e45["role"] == "dev_expanding")]
    dev_ap = {m: summarize(f2[f2["model"] == m], "prob_raw")["AP_fold_mean"] for m in CANDIDATES}
    learned = max(dev_ap, key=dev_ap.get)
    b0dev = e03[(e03["model"] == "B0_Historical_Rule") & (e03["role"] == "dev_expanding")]
    b0_ece = [ece(g["y_true_bin"].values, np.clip(g["prob_raw"].values, 1e-5, 1 - 1e-5))[0] for _, g in b0dev.groupby("split_id")]
    ece_cap = float(np.ceil(max(b0_ece) * 100) / 100)

    # one evaluation of the rule on the retrospective test (main-study predictions, Core-9)
    both = pd.concat([e45[(e45["variant"] == "F2_Macro_plus_IQ") & (e45["model"] == learned)], e03[e03["model"] == "B0_Historical_Rule"]])
    retro = []
    for T in (2021, 2022):
        cap = maturity_cap(f"{T}-01", 3)
        lo = (pd.Period(cap, "M") - 11).strftime("%Y-%m")
        hist = both[(both["ym"] >= lo) & (both["ym"] <= cap)]
        dep, gain, e = fallback_decision(hist, learned, SESOI_AP, ece_cap)
        te = both[(both["ym"] >= f"{T}-01") & (both["ym"] <= f"{T}-12") & (both["model"] == dep)]
        retro.append({"test_year": T, "deployed": dep, "hist_AP_gain": gain, "hist_ECE": e,
                      "cost_C5_per100": round(expected_cost(te["y_true_bin"], te["prob_raw"]), 3)})

    proto = {
        "title": "Confirmation protocol, frozen before any 2023-2025 outcome is evaluated",
        "frozen_at_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"),
        "forecast_origins": "2023-01 to 2025-12 (test years 2023, 2024, 2025); 2021-2022 are warm-up folds that only supply history for the fallback rule",
        "countries": {"core9": CORE9, "external6": EXT6},
        "features": MACRO_COLS + IQ_COLS,
        "feature_note": "FX-share (CI) features excluded: the CI export ends before 2023",
        "target": "target_reer_vol_3m; high-risk if >= 80th percentile of the pooled training targets of the fold",
        "folds": conf_splits().to_dict("records"),
        "maturity_rule": "training and calibration origins satisfy origin + h + 1 < first test month (h = 3)",
        "models": ["B0_Historical_Rule", "B1_Regularized_Linear", "M0_EBM_Additive (macro + IQ)", "B4_XGBoost"],
        "seeds": SEEDS,
        "probabilities": "raw (the calibration scheme locked for B0, B1, B4, M0 in the main study)",
        "decision_threshold": {"C_FN": 5, "C_FP": 1, "tau": TAU_C5},
        "review_budget_k_per_month": 2,
        "fallback_policy": {
            "learned_model": learned,
            "learned_model_choice": f"highest development-fold mean AP among {CANDIDATES} with macro + IQ features: {dev_ap}",
            "rule": "for test year T, compute AP gain over B0 and ECE of the learned model on the latest 12 matured origins (origins up to August of T-1); deploy the learned model only if gain >= delta and ECE <= cap, otherwise deploy B0",
            "delta": SESOI_AP, "ece_cap": ece_cap,
            "ece_cap_choice": "maximum per-fold ECE of B0 on the development folds 2017-2020, rounded up to 0.01",
            "single_evaluation_on_retrospective_test": retro,
        },
        "primary_comparisons": ["fallback policy vs B0 (cost C_FN=5)", "learned model vs B0 (AP, Brier, cost)", "every model vs never-alert"],
        "inference": "paired moving-block bootstrap over months, L = 6, 1000 replications",
        "reporting": "all models, all years and both country groups are reported regardless of outcome",
        "data_vintage_sha256": {f: sha256(os.path.join(BASE_DIR, "data", "raw", f)) for f in RAW_FILES
                                if os.path.exists(os.path.join(BASE_DIR, "data", "raw", f))},
        "panel_sha256": sha256(os.path.join(BASE_DIR, "data", "processed", "panel_pseudo_realtime.csv")),
        "code_sha256": {f: sha256(os.path.join(BASE_DIR, "src", f)) for f in ["step9_confirmation.py", "common.py", "step3_e03_e05_benchmarks_and_ablations.py"]},
    }
    with open(PROTO, "w", encoding="utf-8") as f:
        yaml.dump(proto, f, sort_keys=False, allow_unicode=True, width=120)
    h = sha256(PROTO)
    with open(HASH, "w") as f:
        f.write(f"{h}  confirmation_protocol.yaml\n")
    print(f"Protocol frozen. SHA-256 = {h}\nLearned model: {learned}; ECE cap {ece_cap}; retrospective evaluation: {retro}")


# ------------------------------------------------------------------------------------------------
# Scoring (run once)
# ------------------------------------------------------------------------------------------------
def _task(sub, sp, m, seed, fcols):
    tr, cal, te = fold_frames(sub, sp)
    tr, cal, te = (d.dropna(subset=["target_reer_vol_3m"]) for d in (tr, cal, te))
    thr = float(tr["target_reer_vol_3m"].quantile(0.80))
    y = tr["target_reer_vol_3m"].values
    c, pr, pc, _ = inner_temporal_tune_and_fit(m, tr, y, (y >= thr).astype(int), cal, (cal["target_reer_vol_3m"].values >= thr).astype(int),
                                               te, fcols, ci_col="__none__", iq_col="iq_mean_rt", seed=seed)
    return pd.DataFrame({"split_id": sp["split_id"], "role": sp["role"], "model": m, "seed": seed, "country": te["country"].values,
                         "ym": te["ym"].values, "threshold": thr, "y_true_cont": te["target_reer_vol_3m"].values,
                         "y_true_bin": (te["target_reer_vol_3m"].values >= thr).astype(int), "pred_cont": c, "prob_raw": pr, "prob_cal": pc})


def boot_diff(a, b, fn, L=6, n_boot=1000, seed=20261019):
    a, b = a.sort_values(["ym", "country"]).reset_index(drop=True), b.sort_values(["ym", "country"]).reset_index(drop=True)
    months = np.array(sorted(a["ym"].unique()))
    rows_of = [np.where(a["ym"].values == m)[0] for m in months]
    rng = np.random.RandomState(seed)
    pt = fn(a) - fn(b)
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([rows_of[j] for j in block_indices(months, L, rng)])
        if a["y_true_bin"].values[idx].min() != a["y_true_bin"].values[idx].max():
            draws.append(fn(a.iloc[idx]) - fn(b.iloc[idx]))
    return round(float(pt), 4), round(float(np.percentile(draws, 2.5)), 4), round(float(np.percentile(draws, 97.5)), 4)


def score():
    if not os.path.exists(HASH):
        sys.exit("Protocol not frozen.")
    if os.path.exists(LOCK):
        sys.exit("Confirmation already scored; refusing to score again.")
    recorded = open(HASH).read().split()[0]
    if sha256(PROTO) != recorded:
        sys.exit("Protocol hash mismatch.")
    # the frozen file contains numpy scalar tags, hence the unsafe loader (file written by this script)
    proto = yaml.load(open(PROTO), Loader=yaml.UnsafeLoader)
    panel = load_panel()
    sub = panel[panel["country"].isin(CORE9 + EXT6) & (panel["ym"] >= "2012-01") & (panel["ym"] <= "2025-12")].copy()
    fcols = proto["features"]
    splits = conf_splits()
    models = ["B0_Historical_Rule", "B1_Regularized_Linear", "M0_EBM_Additive", "B4_XGBoost"]
    tasks = [delayed(_task)(sub, sp.to_dict(), m, sd, fcols) for _, sp in splits.iterrows() for m in models for sd in seeds_for(m)]
    df = pd.concat(Parallel(n_jobs=N_JOBS, backend="loky")(tasks), ignore_index=True)
    keys = ["split_id", "role", "model", "country", "ym", "threshold", "y_true_cont", "y_true_bin"]
    df = df.groupby(keys, as_index=False).agg(pred_cont=("pred_cont", "mean"), prob_raw=("prob_raw", "mean"), prob_cal=("prob_cal", "mean"))
    df["prob_dec"] = df["prob_raw"]
    df["group"] = np.where(df["country"].isin(CORE9), "Core-9", "External-6")

    fb = proto["fallback_policy"]
    learned = fb["learned_model"]
    pol_rows, decisions = [], []
    for T in range(2023, 2026):
        cap = maturity_cap(f"{T}-01", 3)
        lo = (pd.Period(cap, "M") - 11).strftime("%Y-%m")
        dep, gain, e = fallback_decision(df[(df["ym"] >= lo) & (df["ym"] <= cap)], learned, fb["delta"], fb["ece_cap"])
        decisions.append({"test_year": T, "history_origins": f"{lo}..{cap}", "deployed": dep, "hist_AP_gain": gain, "hist_ECE": e})
        d = df[(df["split_id"] == f"CONF_{T}") & (df["model"] == dep)].copy()
        d["model"] = "Fallback_policy"
        pol_rows.append(d)
    df = pd.concat([df] + pol_rows, ignore_index=True)
    df.to_parquet(os.path.join(CONF_DIR, "confirmation_predictions.parquet"), index=False)
    pd.DataFrame(decisions).to_csv(os.path.join(TAB_DIR, "table15b_confirmation_fallback_decisions.csv"), index=False)

    conf = df[df["role"] == "confirmation"]
    rows = []
    for gname, gmask in [("All 15 countries", conf["country"].notna()), ("Core-9", conf["group"] == "Core-9"), ("External-6", conf["group"] == "External-6")]:
        for wname, wmask in [("2023-2025", conf["ym"].notna())] + [(str(T), conf["ym"].str.startswith(str(T))) for T in range(2023, 2026)]:
            w = conf[gmask & wmask]
            ref = w[w["model"] == "B0_Historical_Rule"]
            pos = float(ref["y_true_bin"].mean())
            rows.append({"countries": gname, "window": wname, "model": "Rule_Never_Alert", "N": len(ref), "N_pos": int(ref["y_true_bin"].sum()),
                         "Pos_Rate": round(pos, 4), "Cost_C5_per100": round(500 * pos, 3)})
            for m in models + ["Fallback_policy"]:
                g = w[w["model"] == m]
                if len(g) and g["y_true_bin"].nunique() > 1:
                    rows.append({"countries": gname, "window": wname, "model": m, **summarize(g)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table15_confirmation_2023_2025.csv"), index=False)

    ap = lambda d: average_precision_score(d["y_true_bin"], d["prob_dec"])
    cost = lambda d: expected_cost(d["y_true_bin"], d["prob_dec"])
    comp = []
    for gname, gmask in [("All 15 countries", conf["country"].notna()), ("Core-9", conf["group"] == "Core-9")]:
        w = conf[gmask]
        b0 = w[w["model"] == "B0_Historical_Rule"]
        for m in ["B1_Regularized_Linear", "M0_EBM_Additive", "B4_XGBoost", "Fallback_policy"]:
            a = w[w["model"] == m]
            for metric, fn in [("AP", ap), ("Cost_C5_per100", cost)]:
                pt, lo_, hi_ = boot_diff(a, b0, fn)
                comp.append({"countries": gname, "model_A": m, "model_B": "B0_Historical_Rule", "metric": metric, "Delta": pt, "CI95_Low": lo_, "CI95_High": hi_})
    pd.DataFrame(comp).to_csv(os.path.join(TAB_DIR, "table15c_confirmation_differences.csv"), index=False)
    with open(LOCK, "w") as f:
        f.write(json.dumps({"scored_at_utc": datetime.datetime.utcnow().isoformat(timespec="seconds"), "protocol_sha256": recorded}) + "\n")
    print(pd.DataFrame(rows)[lambda d: (d.window == "2023-2025")].to_string())
    print(pd.DataFrame(decisions).to_string())
    print(pd.DataFrame(comp).to_string())


if __name__ == "__main__":
    {"protocol": write_protocol, "score": score}[sys.argv[1]]()
