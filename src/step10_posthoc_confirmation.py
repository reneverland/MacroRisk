#!/usr/bin/env python3
"""
Step 10: post-hoc (exploratory) analyses of the 2023-2025 period
===============================================================
Not part of the frozen confirmation protocol. The frozen result (step 9, SCORED.lock) is read but never
rescored. This step refits the models with the corrected inner tuning folds, adds a paired macro versus
macro+IQ ablation, compares always-on policies with the fallback rule, reports the yearly fallback inputs
and evaluates a multi-candidate monitor that was defined after the frozen result had been seen.
"""

import os
import warnings
import yaml
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import average_precision_score, brier_score_loss

from common import TAB_DIR, N_JOBS, fold_frames, seeds_for, maturity_cap, summarize, expected_cost, load_panel, confirmation_splits, save_predictions
from step3_e03_e05_benchmarks_and_ablations import MACRO_COLS, IQ_COLS, inner_temporal_tune_and_fit
from step4_e06_e08_loco_calib_decision import ece
from step5_e09_e12_explain_robust_figs import block_indices
from step9_confirmation import CORE9, EXT6, PROTO, CONF_DIR, fallback_decision

warnings.filterwarnings("ignore")
TARGET = "target_reer_vol_3m"
SPECS = [("B0_Historical_Rule", "Macro+IQ", MACRO_COLS + IQ_COLS), ("C1_Country_plus_Persistence", "Macro+IQ", MACRO_COLS + IQ_COLS),
         ("B1_Regularized_Linear", "Macro+IQ", MACRO_COLS + IQ_COLS), ("M0_EBM_Additive", "Macro", MACRO_COLS),
         ("M0_EBM_Additive", "Macro+IQ", MACRO_COLS + IQ_COLS), ("B4_XGBoost", "Macro", MACRO_COLS), ("B4_XGBoost", "Macro+IQ", MACRO_COLS + IQ_COLS)]
GROUPS = [("All 15 countries", None), ("Core-9", CORE9), ("External-6", EXT6)]


def _task(sub, sp, m, fs, fcols, seed):
    tr, cal, te = fold_frames(sub, sp)
    tr, cal, te = (d.dropna(subset=[TARGET]) for d in (tr, cal, te))
    thr = float(tr[TARGET].quantile(0.80))
    y = tr[TARGET].values
    c, pr, pc, _ = inner_temporal_tune_and_fit(m, tr, y, (y >= thr).astype(int), cal, (cal[TARGET].values >= thr).astype(int),
                                               te, fcols, ci_col="__none__", iq_col="iq_mean_rt", seed=seed, h=3)
    return pd.DataFrame({"split_id": sp["split_id"], "role": sp["role"], "model": m, "variant": fs, "seed": seed, "country": te["country"].values,
                         "ym": te["ym"].values, "threshold": thr, "y_true_cont": te[TARGET].values,
                         "y_true_bin": (te[TARGET].values >= thr).astype(int), "pred_cont": c, "prob_raw": pr, "prob_cal": pc})


def boot(a, b, L=6, n_boot=1000, seed=20261020):
    """Paired block bootstrap over months of A minus B for AP, Brier and expected cost (probabilities in prob_dec)."""
    a, b = a.sort_values(["ym", "country"]).reset_index(drop=True), b.sort_values(["ym", "country"]).reset_index(drop=True)
    assert (a["country"].values == b["country"].values).all() and (a["ym"].values == b["ym"].values).all()
    y, pa, pb = a["y_true_bin"].values, a["prob_dec"].values, b["prob_dec"].values
    fns = {"AP": lambda i: average_precision_score(y[i], pa[i]) - average_precision_score(y[i], pb[i]),
           "Brier": lambda i: brier_score_loss(y[i], pa[i]) - brier_score_loss(y[i], pb[i]),
           "Cost_C5_per100": lambda i: expected_cost(y[i], pa[i]) - expected_cost(y[i], pb[i])}
    months = np.array(sorted(a["ym"].unique()))
    rows_of = [np.where(a["ym"].values == m)[0] for m in months]
    rng = np.random.RandomState(seed)
    idx = [np.concatenate([rows_of[j] for j in block_indices(months, L, rng)]) for _ in range(n_boot)]
    idx = [i for i in idx if y[i].min() != y[i].max()]
    full = np.arange(len(a))
    return {k: (round(float(f(full)), 4), round(float(np.percentile([f(i) for i in idx], 2.5)), 4),
                round(float(np.percentile([f(i) for i in idx], 97.5)), 4)) for k, f in fns.items()}


def monitor_decision(hist, candidates, delta, ece_cap):
    """Exploratory: deploy the candidate with the largest recent AP gain over B0 if it passes the frozen delta and ECE cap."""
    hb = hist[hist["model_key"] == "B0_Historical_Rule|Macro+IQ"]
    best, best_gain, best_e = "B0_Historical_Rule|Macro+IQ", np.nan, np.nan
    if hb.empty or hb["y_true_bin"].nunique() < 2:
        return best, best_gain, best_e
    ap_b0 = average_precision_score(hb["y_true_bin"], hb["prob_raw"])
    for c in candidates:
        hc = hist[hist["model_key"] == c]
        gain = average_precision_score(hc["y_true_bin"], hc["prob_raw"]) - ap_b0
        e = ece(hc["y_true_bin"].values, np.clip(hc["prob_raw"].values, 1e-5, 1 - 1e-5))[0]
        if gain >= delta and e <= ece_cap and (np.isnan(best_gain) or gain > best_gain):
            best, best_gain, best_e = c, round(float(gain), 4), e
    return best, best_gain, best_e


def main():
    proto = yaml.load(open(PROTO), Loader=yaml.UnsafeLoader)
    fb = proto["fallback_policy"]
    panel = load_panel()
    sub = panel[panel["country"].isin(CORE9 + EXT6) & (panel["ym"] >= "2012-01") & (panel["ym"] <= "2025-12")].copy()
    splits = confirmation_splits()
    tasks = [delayed(_task)(sub, sp.to_dict(), m, fs, fc, sd) for _, sp in splits.iterrows() for m, fs, fc in SPECS for sd in seeds_for(m)]
    df = pd.concat(Parallel(n_jobs=N_JOBS, backend="loky")(tasks), ignore_index=True)
    keys = ["split_id", "role", "model", "variant", "country", "ym", "threshold", "y_true_cont", "y_true_bin"]
    df = df.groupby(keys, as_index=False).agg(pred_cont=("pred_cont", "mean"), prob_raw=("prob_raw", "mean"), prob_cal=("prob_cal", "mean"))
    df["prob_dec"] = df["prob_raw"]
    df["model_key"] = df["model"] + "|" + df["variant"]
    df["group"] = np.where(df["country"].isin(CORE9), "Core-9", "External-6")

    frozen = pd.read_parquet(os.path.join(CONF_DIR, "confirmation_predictions.parquet"))
    frozen["model_key"] = "FROZEN " + frozen["model"]

    learned = fb["learned_model"] + "|Macro+IQ"
    cands = [k for k in df["model_key"].unique() if not k.startswith("B0_")]
    trig, pol = [], []
    for T in range(2023, 2026):
        cap = maturity_cap(f"{T}-01", 3)
        lo = (pd.Period(cap, "M") - 11).strftime("%Y-%m")
        hist = df[(df["ym"] >= lo) & (df["ym"] <= cap)]
        h2 = hist.assign(model=hist["model_key"].where(hist["model_key"] != "B0_Historical_Rule|Macro+IQ", "B0_Historical_Rule"))
        dep, gain, e = fallback_decision(h2, learned, fb["delta"], fb["ece_cap"])
        dep = "B0_Historical_Rule|Macro+IQ" if dep == "B0_Historical_Rule" else dep
        mdep, mgain, me = monitor_decision(hist, cands, fb["delta"], fb["ece_cap"])
        hb = hist[hist["model_key"] == "B0_Historical_Rule|Macro+IQ"]
        row = {"test_year": T, "history_origins": f"{lo}..{cap}", "history_n": len(hb), "history_pos": int(hb["y_true_bin"].sum())}
        for k in ["B0_Historical_Rule|Macro+IQ"] + cands:
            hk = hist[hist["model_key"] == k]
            row[f"histAP_{k}"] = round(float(average_precision_score(hk["y_true_bin"], hk["prob_raw"])), 4) if hk["y_true_bin"].nunique() > 1 else np.nan
            row[f"histECE_{k}"] = ece(hk["y_true_bin"].values, np.clip(hk["prob_raw"].values, 1e-5, 1 - 1e-5))[0]
        row.update({"fallback_rule_deployed": dep, "fallback_gain": gain, "fallback_ECE": e,
                    "monitor_deployed (exploratory)": mdep, "monitor_gain": mgain, "monitor_ECE": me})
        trig.append(row)
        for name, k in [("Post-hoc fallback rule (frozen settings)", dep), ("Exploratory multi-candidate monitor", mdep)]:
            d = df[(df["split_id"] == f"CONF_{T}") & (df["model_key"] == k)].copy()
            d["model_key"], d["model"], d["variant"] = name, name, "policy"
            pol.append(d)
    df = pd.concat([df] + pol, ignore_index=True)
    save_predictions(df, "posthoc_2023_2025")
    pd.DataFrame(trig).to_csv(os.path.join(TAB_DIR, "table15f_posthoc_fallback_triggers.csv"), index=False)

    allp = pd.concat([df, frozen[frozen["role"] == "confirmation"]], ignore_index=True)
    conf = allp[allp["role"] == "confirmation"]
    rows = []
    for gname, cs in GROUPS:
        for wname in ["2023-2025", "2023", "2024", "2025"]:
            w = conf[(conf["country"].isin(cs) if cs else conf["country"].notna()) & (conf["ym"].str.startswith(wname) if wname != "2023-2025" else True)]
            for k, g in w.groupby("model_key"):
                if g["y_true_bin"].nunique() > 1:
                    rows.append({"countries": gname, "window": wname, "model": k, **summarize(g)})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table15d_posthoc_confirmation.csv"), index=False)

    comps = [("Macro+IQ vs macro (EBM)", "M0_EBM_Additive|Macro+IQ", "M0_EBM_Additive|Macro"),
             ("Macro+IQ vs macro (XGBoost)", "B4_XGBoost|Macro+IQ", "B4_XGBoost|Macro"),
             ("XGBoost vs B0 (corrected tuning)", "B4_XGBoost|Macro+IQ", "B0_Historical_Rule|Macro+IQ"),
             ("Macro EBM vs B0 (corrected tuning)", "M0_EBM_Additive|Macro+IQ", "B0_Historical_Rule|Macro+IQ"),
             ("C1 vs B0", "C1_Country_plus_Persistence|Macro+IQ", "B0_Historical_Rule|Macro+IQ"),
             ("Always macro EBM vs frozen fallback", "FROZEN M0_EBM_Additive", "FROZEN Fallback_policy"),
             ("Always XGBoost vs frozen fallback", "FROZEN B4_XGBoost", "FROZEN Fallback_policy"),
             ("Always B1 vs frozen fallback", "FROZEN B1_Regularized_Linear", "FROZEN Fallback_policy"),
             ("Always B0 vs frozen fallback", "FROZEN B0_Historical_Rule", "FROZEN Fallback_policy"),
             ("Exploratory monitor vs B0 (corrected tuning)", "Exploratory multi-candidate monitor", "B0_Historical_Rule|Macro+IQ"),
             ("Exploratory monitor vs XGBoost (corrected tuning)", "Exploratory multi-candidate monitor", "B4_XGBoost|Macro+IQ")]
    out = []
    for gname, cs in GROUPS:
        w = conf[conf["country"].isin(cs)] if cs else conf
        for lab, ka, kb in comps:
            a, b = w[w["model_key"] == ka], w[w["model_key"] == kb]
            r = boot(a, b)
            for metric, (pt, lo_, hi_) in r.items():
                out.append({"countries": gname, "comparison": lab, "model_A": ka, "model_B": kb, "metric": metric, "N": len(a),
                            "N_pos": int(a["y_true_bin"].sum()), "Delta": pt, "CI95_Low": lo_, "CI95_High": hi_})
    pd.DataFrame(out).to_csv(os.path.join(TAB_DIR, "table15e_posthoc_differences.csv"), index=False)
    print(pd.DataFrame(out)[lambda d: d.metric == "AP"].to_string())
    print(pd.DataFrame(trig)[["test_year", "fallback_rule_deployed", "fallback_gain", "monitor_deployed (exploratory)", "monitor_gain"]].to_string())


if __name__ == "__main__":
    main()
