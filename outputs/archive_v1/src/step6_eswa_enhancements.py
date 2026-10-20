#!/usr/bin/env python3
"""
Step 6: ESWA decision-system extensions
=======================================
E13  External transfer to TUR, IDN, THA, MYS, CHL, COL with macro + IQ features (no CI series exists for
     these economies). In every fold the high-risk threshold is the 80th percentile of the Core-9
     training targets, so the transfer and the pooled regime are scored on identical labels. A pooled
     regime with a pool-specific threshold is reported as a sensitivity only.
E14  Training-weight schemes on the Core-9 panel (global, equal-country, time decay, IQ similarity);
     the scheme is selected on the development folds.
E15  Scenario simulation of selective review under a monthly review budget. Every automated policy
     (never alert, persistence B0, macro-only EBM, M0, M1 raw / Platt / expanding Platt, XGBoost, random
     forest) is crossed with every routing rule (low confidence first, highest probability first,
     historical volatility first, random). Differences in expected cost carry paired moving-block
     bootstrap intervals. Reviewer accuracy 1.0 is an upper bound; 0.8 is a stress scenario.
"""

import os
import warnings
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from xgboost import XGBClassifier
from interpret.glassbox import ExplainableBoostingClassifier
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from common import (OUT_DIR, TAB_DIR, N_JOBS, TAU_C5, WINDOWS, MAIN_END, fold_frames, seeds_for, platt_calibrate, summarize,
                    add_expanding_calibration, lock_calibration, save_predictions, load_predictions, load_panel, load_splits)
from step3_e03_e05_benchmarks_and_ablations import (MACRO_COLS, CI_COLS_CORE9, IQ_COLS, EBM_FIXED, build_feature_matrix,
                                                    inner_temporal_tune_and_fit, make_inner_splits, select_ebm_config, core9_sample)
from step5_e09_e12_explain_robust_figs import block_indices

warnings.filterwarnings("ignore")
FIG_DIR = os.path.join(OUT_DIR, "figures")
EXT6 = ["TUR", "IDN", "THA", "MYS", "CHL", "COL"]
plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11, "legend.fontsize": 9.5,
                     "xtick.labelsize": 10, "ytick.labelsize": 10})


def save_fig(fig, name):
    for ext in ["pdf", "png"]:
        fig.savefig(os.path.join(FIG_DIR, f"{name}.{ext}"), bbox_inches="tight", dpi=300)
    plt.close(fig)


# ----------------------------------------------------------------------------------------------
# E13 external transfer
# ----------------------------------------------------------------------------------------------
def _e13_task(sp, regime, target, m_code, core9, ext6, fcols, seed):
    tr_c, cal_c, _ = fold_frames(core9, sp)
    tr_e, cal_e, te_e = fold_frames(ext6, sp)
    tr_c, cal_c, tr_e, cal_e, te_e = (d.dropna(subset=[target]) for d in (tr_c, cal_c, tr_e, cal_e, te_e))
    thr_core = float(tr_c[target].quantile(0.80))
    if regime != "Transfer_Core9_only":
        tr_c, cal_c = pd.concat([tr_c, tr_e]), pd.concat([cal_c, cal_e])
    thr = float(tr_c[target].quantile(0.80)) if regime == "Pooled_pool_specific_threshold" else thr_core
    y_tr = tr_c[target].values
    c_te, p_raw, p_cal, _ = inner_temporal_tune_and_fit(
        m_code, tr_c, y_tr, (y_tr >= thr).astype(int), cal_c, (cal_c[target].values >= thr).astype(int),
        te_e, fcols, ci_col="__none__", iq_col="iq_mean_rt", seed=seed)
    return pd.DataFrame({"split_id": sp["split_id"], "role": sp["role"], "variant": f"{regime}|{target}", "regime": regime,
                         "target": target, "model": m_code, "seed": seed, "country": te_e["country"].values, "ym": te_e["ym"].values,
                         "threshold": thr, "y_true_cont": te_e[target].values, "y_true_bin": (te_e[target].values >= thr).astype(int),
                         "pred_cont": c_te, "prob_raw": p_raw, "prob_cal": p_cal})


def run_e13(panel, splits):
    print("[E13] External transfer (fixed Core-9 thresholds)...")
    sub = panel[(panel["ym"] >= "2012-01") & (panel["ym"] <= MAIN_END)]
    core9, ext6 = sub[sub["in_core9"] == 1], sub[sub["country"].isin(EXT6)]
    fcols = MACRO_COLS + IQ_COLS
    tasks = []
    for _, sp in splits.iterrows():
        for regime in ["Transfer_Core9_only", "Pooled_with_target_history", "Pooled_pool_specific_threshold"]:
            for target, models in [("target_reer_vol_3m", ["B0_Historical_Rule", "B1_Regularized_Linear", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive"]),
                                   ("target_res_drawdown_3m", ["B1_Regularized_Linear", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive"])]:
                for m in models:
                    for sd in seeds_for(m):
                        tasks.append(delayed(_e13_task)(sp.to_dict(), regime, target, m, core9, ext6, fcols, sd))
    df = pd.concat(Parallel(n_jobs=N_JOBS, backend="loky")(tasks), ignore_index=True)
    keys = ["variant", "regime", "target", "model", "split_id", "role", "country", "ym", "threshold", "y_true_cont", "y_true_bin"]
    df = df.groupby(keys, as_index=False).agg(pred_cont=("pred_cont", "mean"), prob_raw=("prob_raw", "mean"),
                                              prob_cal=("prob_cal", "mean"), n_seeds=("seed", "nunique"))
    df = lock_calibration(add_expanding_calibration(df, splits, keys=("variant", "model")), keys=("variant", "model"))
    df = save_predictions(df, "e13_external")

    rows, cty_rows = [], []
    for (regime, target, model), g in df.groupby(["regime", "target", "model"]):
        for key in ["all", "locked", "dev"]:
            label, fn = WINDOWS[key]
            rows.append({"evaluation_window": label, "regime": regime, "target": target, "model": model,
                         **summarize(g[fn(g)]), "cal_scheme": g["cal_scheme"].iloc[0]})
        for c, gc in g[WINDOWS["all"][1](g)].groupby("country"):
            m = summarize(gc)
            cty_rows.append({"evaluation_window": WINDOWS["all"][0], "regime": regime, "target": target, "model": model, "country": c,
                             "N": m["N"], "N_pos": m["N_pos"], "Pos_Rate": m["Pos_Rate"], "AP": m["AP"], "Brier": m["Brier"]})
    pd.DataFrame(rows).to_csv(os.path.join(TAB_DIR, "table9_e13_external_transfer.csv"), index=False)
    pd.DataFrame(cty_rows).to_csv(os.path.join(TAB_DIR, "table9b_e13_external_by_country.csv"), index=False)
    print("  - Saved table9_e13_external_transfer.csv")


# ----------------------------------------------------------------------------------------------
# E14 training-weight schemes
# ----------------------------------------------------------------------------------------------
XGB_CFG = {"max_depth": 2, "learning_rate": 0.03, "n_estimators": 90, "subsample": 0.8,
           "colsample_bytree": 0.7, "reg_lambda": 5.0, "min_child_weight": 8}
SCHEMES = ["Global", "Equal_Country", "Time_Decay_H24", "Time_Decay_H48", "IQ_Similarity_Regularized"]


def months_between(ym_a, ym_b):
    a = pd.to_datetime(pd.Series(ym_a) + "-01")
    b = pd.to_datetime(ym_b + "-01")
    return ((b.year - a.dt.year) * 12 + (b.month - a.dt.month)).values


def scheme_weights(scheme, df_tr, train_end, target_iq=None, iq_bw=None):
    n = len(df_tr)
    if scheme == "Global":
        w = np.ones(n)
    elif scheme == "Equal_Country":
        w = 1.0 / df_tr.groupby("country")["country"].transform("size").values
    elif scheme.startswith("Time_Decay_H"):
        w = 0.5 ** (months_between(df_tr["ym"].values, train_end) / float(scheme.split("H")[-1]))
    elif scheme == "IQ_Similarity_Regularized":
        iq = df_tr["iq_mean_rt"].fillna(df_tr["iq_mean_rt"].median()).values
        w = 0.5 + 0.5 * np.exp(-0.5 * ((iq - target_iq) / iq_bw) ** 2)
    else:
        raise ValueError(scheme)
    return w * n / w.sum()


def _fit_weighted(learner, X_tr, y_tr, w, ebm_cfg, seed):
    if learner == "XGBoost":
        m = XGBClassifier(random_state=seed, eval_metric="logloss", verbosity=0, n_jobs=1, **XGB_CFG)
    else:
        m = ExplainableBoostingClassifier(interactions=0, random_state=seed, **EBM_FIXED, **ebm_cfg)
    m.fit(X_tr, y_tr, sample_weight=w)
    return m


def _e14_task(sp, scheme, learner, core9, fcols, seed):
    tr, cal, te = fold_frames(core9, sp)
    thr = float(tr["target_reer_vol_3m"].quantile(0.80))
    y_tr = (tr["target_reer_vol_3m"].values >= thr).astype(int)
    y_cal = (cal["target_reer_vol_3m"].values >= thr).astype(int)
    X_tr, imp, scl = build_feature_matrix(tr, fcols)
    X_cal, _, _ = build_feature_matrix(cal, fcols, imp, scl)
    X_te, _, _ = build_feature_matrix(te, fcols, imp, scl)
    ebm_cfg = select_ebm_config(X_tr, y_tr, make_inner_splits(tr), 0, 42) if learner == "EBM" else None
    out = []
    targets = [None] if scheme != "IQ_Similarity_Regularized" else sorted(te["country"].unique())
    iq_bw = 0.5 * float(tr["iq_mean_rt"].std())
    for c in targets:
        if c is None:
            w, mte = scheme_weights(scheme, tr, sp["train_end_origin"]), np.ones(len(te), bool)
        else:
            last = tr[tr["country"] == c].sort_values("ym")["iq_mean_rt"].dropna()
            tiq = float(last.iloc[-1]) if len(last) else float(tr["iq_mean_rt"].median())
            w, mte = scheme_weights(scheme, tr, sp["train_end_origin"], tiq, iq_bw), te["country"].values == c
        m = _fit_weighted(learner, X_tr, y_tr, w, ebm_cfg, seed)
        p_te = m.predict_proba(X_te[mte])[:, 1]
        out.append(pd.DataFrame({"country": te["country"].values[mte], "ym": te["ym"].values[mte], "prob_raw": p_te,
                                 "prob_cal": platt_calibrate(m.predict_proba(X_cal)[:, 1], y_cal, p_te)[0]}))
    df = pd.concat(out, ignore_index=True).merge(te[["country", "ym", "target_reer_vol_3m"]], on=["country", "ym"])
    df["y_true_cont"] = df.pop("target_reer_vol_3m")
    df["threshold"], df["y_true_bin"] = thr, (df["y_true_cont"] >= thr).astype(int)
    df["split_id"], df["role"], df["model"], df["variant"], df["seed"] = sp["split_id"], sp["role"], learner, scheme, seed
    return df


def run_e14(panel, splits):
    print("[E14] Training-weight schemes...")
    core9 = core9_sample(panel)
    fcols = MACRO_COLS + CI_COLS_CORE9 + IQ_COLS
    tasks = [delayed(_e14_task)(sp.to_dict(), s, l, core9, fcols, sd) for _, sp in splits.iterrows() for s in SCHEMES
             for l in ["XGBoost", "EBM"] for sd in [42, 1024, 2024, 3407, 7777]]
    df = pd.concat(Parallel(n_jobs=N_JOBS, backend="loky")(tasks), ignore_index=True)
    keys = ["variant", "model", "split_id", "role", "country", "ym", "threshold", "y_true_cont", "y_true_bin"]
    df = df.groupby(keys, as_index=False).agg(prob_raw=("prob_raw", "mean"), prob_cal=("prob_cal", "mean"), n_seeds=("seed", "nunique"))
    df["pred_cont"] = df["prob_raw"]
    df = lock_calibration(add_expanding_calibration(df, splits, keys=("variant", "model")), keys=("variant", "model"))
    df = save_predictions(df, "e14_weighting")
    rows = []
    for (learner, scheme), g in df.groupby(["model", "variant"]):
        row = {"learner": learner, "scheme": scheme, "cal_scheme": g["cal_scheme"].iloc[0]}
        for key, tag in [("dev", "Dev"), ("locked", "Test"), ("all", "All")]:
            m = summarize(g[WINDOWS[key][1](g)])
            row.update({f"{tag}_AP": m["AP"], f"{tag}_AP_fold_mean": m["AP_fold_mean"], f"{tag}_Brier": m["Brier"], f"{tag}_CostC5": m["Cost_C5_per100"]})
        rows.append(row)
    tab = pd.DataFrame(rows)
    tab["Selected_on_dev"] = False
    for _, g in tab.groupby("learner"):
        tab.loc[g["Dev_AP_fold_mean"].idxmax(), "Selected_on_dev"] = True
    tab.to_csv(os.path.join(TAB_DIR, "table10_e14_adaptive_weighting.csv"), index=False)
    print(tab[["learner", "scheme", "Dev_AP_fold_mean", "Test_AP", "Selected_on_dev"]].to_string())
    return tab


# ----------------------------------------------------------------------------------------------
# E15 selective review scenario simulation
# ----------------------------------------------------------------------------------------------
def logit(p):
    p = np.clip(p, 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p))


def e15_bases(panel):
    e03 = load_predictions("e03")
    e45 = load_predictions("e04_e05")
    hv = panel[["country", "ym", "reer_vol_hist_3m"]]
    base = e03[e03["model"] == "B0_Historical_Rule"][["country", "ym", "split_id", "role", "y_true_bin"]].merge(hv, on=["country", "ym"])
    def col(df, model, c, variant=None):
        d = df[(df["model"] == model) & ((df["variant"] == variant) if variant else True)]
        return base[["country", "ym"]].merge(d[["country", "ym", c]], on=["country", "ym"], how="left")[c].values
    probs = {
        "B0 persistence": col(e03, "B0_Historical_Rule", "prob_dec"),
        "Macro-only EBM": col(e45, "M0_EBM_Additive", "prob_dec", "F0_Macro_Only"),
        "M0 EBM": col(e03, "M0_EBM_Additive", "prob_dec"),
        "M1 EBM (locked scheme)": col(e03, "M1_EBM_CIxIQ", "prob_dec"),
        "M1 EBM raw": col(e03, "M1_EBM_CIxIQ", "prob_raw"),
        "M1 EBM Platt 8m": col(e03, "M1_EBM_CIxIQ", "prob_cal"),
        "M1 EBM Platt expanding": col(e03, "M1_EBM_CIxIQ", "prob_cal_exp"),
        "B4 XGBoost": col(e03, "B4_XGBoost", "prob_dec"),
        "B3 Random forest": col(e03, "B3_Random_Forest", "prob_dec"),
    }
    return base.reset_index(drop=True), probs


def policy_costs(base, p, routing, k, c_review, acc, c_fn=5.0, c_fp=1.0):
    """Per-case expected cost of an automated policy (probability p, or never-alert when p is None) whose k
    cases per month selected by the routing rule are decided by an analyst."""
    y = base["y_true_bin"].values
    alert = np.zeros(len(y), bool) if p is None else p >= TAU_C5
    auto = np.where(alert & (y == 0), c_fp, 0.0) + np.where(~alert & (y == 1), c_fn, 0.0)
    rev = c_review + (1.0 - acc) * np.where(y == 1, c_fn, c_fp)
    if k == 0 or routing == "None":
        return auto, 0.0
    if routing == "Random":
        share = np.minimum(1.0, k / base.groupby("ym")["country"].transform("size").values)
        return share * rev + (1 - share) * auto, float(share.mean())
    key = {"Low confidence first": -np.abs(logit(p) - logit(TAU_C5)) if p is not None else None,
           "Highest probability first": p, "Historical volatility first": base["reer_vol_hist_3m"].values}[routing]
    if key is None:
        return None, None
    rank = pd.Series(key).groupby(base["ym"].values).rank(method="first", ascending=False).values
    reviewed = rank <= k
    return np.where(reviewed, rev, auto), float(reviewed.mean())


def boot_mean_diff(base, ca, cb, L=12, n_boot=1000, seed=20261019):
    months = np.array(sorted(base["ym"].unique()))
    rows_of = [np.where(base["ym"].values == m)[0] for m in months]
    d = ca - cb
    rng = np.random.RandomState(seed)
    draws = [d[np.concatenate([rows_of[j] for j in block_indices(months, L, rng)])].mean() for _ in range(n_boot)]
    return 100 * d.mean(), 100 * np.percentile(draws, 2.5), 100 * np.percentile(draws, 97.5)


ROUTINGS = ["Low confidence first", "Highest probability first", "Historical volatility first", "Random"]


def run_e15(panel):
    print("[E15] Selective-review scenario simulation...")
    base_all, probs_all = e15_bases(panel)
    policies = {"Never alert": None, **probs_all}
    grid, comps = [], []
    for wkey in ["all", "locked"]:
        label, fn = WINDOWS[wkey]
        msk = fn(base_all).values
        base = base_all[msk].reset_index(drop=True)
        P = {n: (None if p is None else p[msk]) for n, p in policies.items()}
        for c_review in [0.25, 0.5, 1.0]:
            for acc in [1.0, 0.8]:
                for name, p in P.items():
                    for routing in ["None"] + ROUTINGS:
                        for k in ([0] if routing == "None" else range(1, 6)):
                            c, rate = policy_costs(base, p, routing, k, c_review, acc)
                            if c is None:
                                continue
                            grid.append({"evaluation_window": label, "c_review": c_review, "reviewer_acc": acc, "automated_policy": name,
                                         "routing": routing, "k_per_month": k, "review_rate": round(rate, 4),
                                         "total_cost_per100": round(100 * c.mean(), 3)})
        for acc in [1.0, 0.8]:
            def C(name, routing, k):
                return policy_costs(base, P[name], routing, k, 0.5, acc)[0]
            M1 = "M1 EBM (locked scheme)"
            pairs = [
                ("M1 + low-confidence review (k=2)", C(M1, "Low confidence first", 2), "B0 + low-confidence review (k=2)", C("B0 persistence", "Low confidence first", 2)),
                ("M1 + low-confidence review (k=2)", C(M1, "Low confidence first", 2), "B0 automated", C("B0 persistence", "None", 0)),
                ("M1 + low-confidence review (k=2)", C(M1, "Low confidence first", 2), "Never alert + volatility review (k=2)", C("Never alert", "Historical volatility first", 2)),
                ("M1 + low-confidence review (k=2)", C(M1, "Low confidence first", 2), "M1 + random review (k=2)", C(M1, "Random", 2)),
                ("M1 + low-confidence review (k=2)", C(M1, "Low confidence first", 2), "Macro-only EBM + low-confidence review (k=2)", C("Macro-only EBM", "Low confidence first", 2)),
                ("M1 automated", C(M1, "None", 0), "B0 automated", C("B0 persistence", "None", 0)),
                ("M1 Platt 8m automated", C("M1 EBM Platt 8m", "None", 0), "M1 raw automated", C("M1 EBM raw", "None", 0)),
                ("B0 + low-confidence review (k=2)", C("B0 persistence", "Low confidence first", 2), "B0 automated", C("B0 persistence", "None", 0)),
                ("B0 + low-confidence review (k=2)", C("B0 persistence", "Low confidence first", 2), "Never alert + volatility review (k=2)", C("Never alert", "Historical volatility first", 2)),
                ("B0 automated", C("B0 persistence", "None", 0), "Never alert", C("Never alert", "None", 0)),
            ]
            for na, ca, nb, cb in pairs:
                pt, lo, hi = boot_mean_diff(base, ca, cb, L=12 if wkey == "all" else 6)
                comps.append({"evaluation_window": label, "block_length_months": 12 if wkey == "all" else 6, "reviewer_acc": acc, "c_review": 0.5, "policy_A": na, "policy_B": nb,
                              "cost_A_per100": round(100 * ca.mean(), 3), "cost_B_per100": round(100 * cb.mean(), 3),
                              "Delta_cost_per100": round(pt, 3), "CI95_Low": round(lo, 3), "CI95_High": round(hi, 3)})
    df = pd.DataFrame(grid)
    df.to_csv(os.path.join(TAB_DIR, "table11_e15_selective_review.csv"), index=False)
    pd.DataFrame(comps).to_csv(os.path.join(TAB_DIR, "table11b_e15_cost_differences.csv"), index=False)
    print(pd.DataFrame(comps)[lambda d: d.reviewer_acc == 1.0][["evaluation_window", "policy_A", "policy_B", "Delta_cost_per100", "CI95_Low", "CI95_High"]].to_string())
    return df


def make_figures(tab14, df15):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))
    for ax, learner in zip(axes, ["EBM", "XGBoost"]):
        g = tab14[tab14["learner"] == learner].set_index("scheme").loc[SCHEMES]
        x = np.arange(len(SCHEMES))
        ax.bar(x - 0.2, g["Dev_AP_fold_mean"], 0.4, label="Development folds (fold-mean AP)", color="#5D6D7E")
        ax.bar(x + 0.2, g["Test_AP"], 0.4, label="Retrospective test (pooled AP)", color="#C0392B")
        for i, sel in enumerate(g["Selected_on_dev"].values):
            if sel:
                ax.annotate("selected", (i, max(g["Dev_AP_fold_mean"].iloc[i], g["Test_AP"].iloc[i]) + 0.01), ha="center", fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels(["Global", "Equal\ncountry", "Decay\nH=24", "Decay\nH=48", "IQ\nsimilarity"])
        ax.set_title(f"({'a' if learner == 'EBM' else 'b'}) {learner}", fontweight="bold"); ax.set_ylabel("Average precision")
        ax.grid(axis="y", linestyle=":", alpha=0.5)
    axes[0].legend(loc="lower left", fontsize=9)
    fig.tight_layout()
    save_fig(fig, "fig6_e14_adaptive_weighting")

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))
    styles = {("B0 persistence", "Low confidence first"): ("#2C3E50", "-", "o"), ("B0 persistence", "Historical volatility first"): ("#7F8C8D", "--", "s"),
              ("M1 EBM (locked scheme)", "Low confidence first"): ("#C0392B", "-", "o"), ("M1 EBM (locked scheme)", "Random"): ("#F39C12", ":", "^"),
              ("Never alert", "Historical volatility first"): ("#95A5A6", "-.", "D"), ("Macro-only EBM", "Low confidence first"): ("#8E44AD", "-", "v")}
    for ax, (acc, ttl) in zip(axes, [(1.0, "(a) Reviewer accuracy 1.0 (upper bound)"), (0.8, "(b) Reviewer accuracy 0.8")]):
        g = df15[(df15["evaluation_window"] == WINDOWS["all"][0]) & (df15["c_review"] == 0.5) & (df15["reviewer_acc"] == acc)]
        for (pol, rout), (col, ls, mk) in styles.items():
            gp = g[(g["automated_policy"] == pol) & (g["routing"].isin([rout, "None"]))].sort_values("k_per_month")
            if pol == "Never alert":
                gp = gp[(gp["routing"] == rout) | (gp["k_per_month"] == 0)]
            ax.plot(100 * gp["review_rate"], gp["total_cost_per100"], color=col, linestyle=ls, marker=mk, label=f"{pol.split(' (')[0]}: {rout.lower()}")
        ax.set_xlabel("Cases routed to analysts (%)"); ax.set_ylabel("Expected cost per 100 forecasts")
        ax.set_title(ttl + ", review cost 0.5", fontweight="bold"); ax.grid(True, linestyle=":", alpha=0.5)
    axes[0].legend(fontsize=8.5)
    fig.tight_layout()
    save_fig(fig, "fig7_e15_risk_workload")


if __name__ == "__main__":
    import sys
    panel, splits = load_panel(), load_splits()
    parts = sys.argv[1:] or ["e13", "e14", "e15", "figs"]
    if "e13" in parts:
        run_e13(panel, splits)
    if "e14" in parts:
        run_e14(panel, splits)
    if "e15" in parts:
        run_e15(panel)
    if "figs" in parts:
        make_figures(pd.read_csv(os.path.join(TAB_DIR, "table10_e14_adaptive_weighting.csv")),
                     pd.read_csv(os.path.join(TAB_DIR, "table11_e15_selective_review.csv")))
    print("DONE: Step 6 (E13-E15) completed successfully.")
