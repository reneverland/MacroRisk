#!/usr/bin/env python3
"""
Step 2: E01 (Data & Original Manuscript Forensic Audit; threshold replication lives in step2b)
        & E02 (Forecasting Task Feasibility, Stress Episodes & Split Manifest)
================================================================================
Outputs:
- outputs/tables/table1_data_summary.csv
- outputs/tables/e01_manuscript_discrepancy_audit.csv
- outputs/tables/e02_stress_window_feasibility.csv
- outputs/split_manifest.csv
"""

import os
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
TAB_DIR = os.path.join(OUT_DIR, "tables")
os.makedirs(TAB_DIR, exist_ok=True)


def run_e01_audit(panel):
    print("[E01] Running data summary and forensic discrepancy audit...")

    # 1. Table 1: Summary statistics for the Core-9 forecasting panel (2012-01 to 2022-12) and its Core-6 SWIFT subsample
    sub_core9 = panel[(panel["in_core9"] == 1) & (panel["ym"] >= "2012-01") & (panel["ym"] <= "2022-12")].copy()
    sub_swift6 = sub_core9[sub_core9["in_swift6"] == 1].copy()

    summary_vars = [
        ("swift_share_rt", "SWIFT Payment Share (%, released t-1)", sub_swift6),
        ("fx_share_rt", "FX Derivatives Turnover Share (released t-1)", sub_core9),
        ("iq_mean_rt", "Institutional Quality (WGI 6-Dim Mean)", sub_core9),
        ("target_reer_vol_3m", "Future 3M Exchange-Rate Stress V_{i,t}^{(3)} (%)", sub_core9),
        ("target_reer_vol_6m", "Future 6M Exchange-Rate Stress V_{i,t}^{(6)} (%)", sub_core9),
        ("target_res_drawdown_3m", "Future 3M Reserve Max Drawdown D_{i,t}^{(3)} (%)", sub_core9),
        ("reer_vol_hist_3m", "Historical 3M REER Stress (%)", sub_core9),
        ("cpi_vol_rt", "CPI Inflation Volatility (12M Rolling Std, %)", sub_core9),
        ("fx_res_vol_rt", "FX Reserve Volatility (12M Log-Chg Std)", sub_core9),
        ("cg_gap_rt", "Credit-to-GDP Gap (%)", sub_core9),
        ("unemp_rate_wb_rt", "Unemployment Rate (%)", sub_core9),
        ("ln_gdp_pc_rt", "Log Per Capita GDP (Const 2015 USD)", sub_core9),
        ("gdp_growth_rate_rt", "Real GDP Growth Rate (Decimal)", sub_core9),
        ("ln_pop_rt", "Log Population", sub_core9),
        ("fin_depth_rt", "Financial Depth (Private Credit / GDP, %)", sub_core9),
        ("fin_openness_proxy_rt", "Financial Openness Index (% of GDP)", sub_core9),
        ("trade_openness_wb_rt", "Trade Openness (Imports+Exports / GDP, %)", sub_core9),
        ("policy_rate_diff_us", "Policy Rate Spread vs. US Fed (%)", sub_core9),
        ("usd_neer_ret_1m", "Global USD Broad NEER 1M Log Change (%)", sub_core9),
    ]

    t1_rows = []
    for col, label, dset in summary_vars:
        s = dset[col].dropna()
        t1_rows.append({
            "variable_code": col,
            "variable_name": label,
            "panel_scope": "Core-6 (SWIFT)" if len(dset) == len(sub_swift6) else "Core-9 (All)",
            "N": int(len(s)),
            "Mean": round(float(s.mean()), 4),
            "Std": round(float(s.std()), 4),
            "Min": round(float(s.min()), 4),
            "P25": round(float(s.quantile(0.25)), 4),
            "Median": round(float(s.median()), 4),
            "P75": round(float(s.quantile(0.75)), 4),
            "Max": round(float(s.max()), 4),
        })
    df_t1 = pd.DataFrame(t1_rows)
    df_t1.to_csv(os.path.join(TAB_DIR, "table1_data_summary.csv"), index=False)

    # 2. Forensic Audit of Original Manuscript Discrepancies
    discrepancy_rows = [
        {
            "issue_id": "D01",
            "category": "Sample Period Mismatch",
            "original_long_draft": "Jan 2012 - Dec 2022 (132 months); SWIFT Max = 2.790% (Jan 2022)",
            "original_short_draft": "Text claims Jan 2012 - Dec 2023, but Table 1 N=1188 = 9 countries x 132 months (11 yrs); SWIFT Max updated to 4.610% (Nov 2023)",
            "root_cause_identified": "Short draft updated only the SWIFT summary max to Nov 2023 (4.61%) while retaining the 11-year (132-month) panel for all other variables (9 x 132 = 1188).",
            "reconstructed_resolution": "Forecasting grid 2012-01 to 2022-12 (132 origins, the FX-share coverage); the SWIFT panel is reported with its own coverage (2012-08 to 2021-12)."
        },
        {
            "issue_id": "D02",
            "category": "Sample Size Mismatch (678 vs 1188)",
            "original_long_draft": "Panel A (SWIFT 6 countries): N = 678 across all variables; Panel B (FX 9 countries): N = 1188",
            "original_short_draft": "Table 1 merges Panels A & B: reports N = 678 for SWIFT Share and N = 1188 for all other variables",
            "root_cause_identified": "The historical SWIFT regression dataset is a balanced panel of 6 countries x 113 months (2012-08 to 2021-12) = 678; the FX dataset is 9 countries x 132 months (2012-01 to 2022-12) = 1188. The two panels have different calendar coverage, not missing ranks.",
            "reconstructed_resolution": "Report the two panels separately with their own coverage; in forecasting, Core-6 SWIFT results are a matched subsample of the Core-9 FX panel."
        },
        {
            "issue_id": "D03",
            "category": "Regression Coefficient Discrepancies (49.0647 vs 9.06; 84.6554 vs 8.65)",
            "original_long_draft": "Table 3 SWIFT->CPI_Vol Regime 1 = 49.0647*** (t=12.37); Table 4 FX->CPI_Vol Regime 1 = 84.6554** (t=2.19), Regime 2 = 52.1320** (t=2.23)",
            "original_short_draft": "Table 3 SWIFT->CPI_Vol Regime 1 = 9.06*** (t=12.37); Appendix Table A1 FX->CPI_Vol Regime 1 = 8.65** (t=2.19), Regime 2 = 5.13** (t=2.23)",
            "root_cause_identified": "The t-statistics are identical while the coefficients differ by a dropped digit ([4]9.06, 8[4].65, 5[2].13); this pattern is consistent with a suspected transcription error during manual table editing; without the original estimation files a re-estimation or unit rescaling cannot be ruled out.",
            "reconstructed_resolution": "All coefficients are re-estimated from the historical datasets (step2b) and exported programmatically; any unit rescaling of CI is stated in table notes."
        },
        {
            "issue_id": "D04",
            "category": "Backward Filling & Look-Ahead Leakage in Annual Variables",
            "original_long_draft": "Annual WGI and GDP backward-filled into Jan-Dec of the same calendar year.",
            "original_short_draft": "Same contemporaneous monthlyization without release lags.",
            "root_cause_identified": "Year-Y WGI is released in Sept of Year Y+1; using Year-Y WGI in Jan-Dec of Year Y leaks 9 to 20 months of future institutional information.",
            "reconstructed_resolution": "Strict pseudo-real-time alignment: Year-Y WGI enters in Sept Y+1 (recording iq_data_age_m); CI enters with a 1-month publication lag and is held forward with its data age."
        },
        {
            "issue_id": "D05",
            "category": "Risk Indicator & Target Definition Ambiguity",
            "original_long_draft": "Six contemporaneous volatility/level proxies (CPI_Vol, FX_Vol, CE_Vol, ER_Vol, CG_Gap, Unemp) regressed on contemporaneous CI and IQ.",
            "original_short_draft": "Same 6 contemporaneous indicators; high lagged dependent variable coefficients (0.80-0.86) due to overlapping rolling windows.",
            "root_cause_identified": "Rolling 12-month standard deviations share 11 of 12 months with their 1-month lag, inflating in-sample R^2 and t-statistics without testing future forecasting.",
            "reconstructed_resolution": "Define forward rolling h-month RMS exchange-rate stress V_{i,t}^{(h)} and reserve drawdown D_{i,t}^{(h)}. Windows of adjacent origins overlap (they share h-1 months), so inference uses moving-block bootstraps over calendar months, and fold boundaries keep a target-maturity buffer so that no training or calibration target is published after the first test month."
        },
    ]
    pd.DataFrame(discrepancy_rows).to_csv(os.path.join(TAB_DIR, "e01_manuscript_discrepancy_audit.csv"), index=False)

    print("  - Saved table1_data_summary.csv, e01_manuscript_discrepancy_audit.csv")


def count_contiguous_episodes(binary_series, cooldown=0):
    """
    Count high-risk episodes in a binary 0/1 series ordered in time: runs of consecutive positive windows, the
    definition used by the event-level evaluation (step 6b). Positive windows separated by <= cooldown months
    would be merged; every call uses cooldown = 0.
    """
    vals = np.asarray(binary_series, dtype=int)
    n_episodes = 0
    in_ep = False
    gap = 0
    for v in vals:
        if v == 1:
            if not in_ep:
                n_episodes += 1
                in_ep = True
            gap = 0
        else:
            if in_ep:
                gap += 1
                if gap > cooldown:
                    in_ep = False
                    gap = 0
    return n_episodes


def run_e02_feasibility_and_splits(panel):
    print("[E02] Running task feasibility audit, stress episode statistics, and split manifest generation...")

    # Forecasting sample: 2012-01 to 2022-12 (FX-share coverage of the Core-9 panel).
    # Expanding folds: train origins end in August of year T-2, calibration origins run Jan-Aug of year T-1,
    # test covers year T. The 4-month buffer guarantees every h=3 target in a window is released before
    # the next window starts. Dev folds test 2017-2020; the locked test covers 2021-2022.
    splits = [
        {"split_id": "DEV_FOLD_2017", "role": "dev_expanding", "train_start": "2012-01", "train_end_origin": "2015-08",
         "calib_start": "2016-01", "calib_end_origin": "2016-08", "test_start": "2017-01", "test_end": "2017-12", "maturity_buffer_months": 4},
        {"split_id": "DEV_FOLD_2018", "role": "dev_expanding", "train_start": "2012-01", "train_end_origin": "2016-08",
         "calib_start": "2017-01", "calib_end_origin": "2017-08", "test_start": "2018-01", "test_end": "2018-12", "maturity_buffer_months": 4},
        {"split_id": "DEV_FOLD_2019", "role": "dev_expanding", "train_start": "2012-01", "train_end_origin": "2017-08",
         "calib_start": "2018-01", "calib_end_origin": "2018-08", "test_start": "2019-01", "test_end": "2019-12", "maturity_buffer_months": 4},
        {"split_id": "DEV_FOLD_2020", "role": "dev_expanding", "train_start": "2012-01", "train_end_origin": "2018-08",
         "calib_start": "2019-01", "calib_end_origin": "2019-08", "test_start": "2020-01", "test_end": "2020-12", "maturity_buffer_months": 4},
        {"split_id": "LOCKED_TEST_2021", "role": "locked_test", "train_start": "2012-01", "train_end_origin": "2019-08",
         "calib_start": "2020-01", "calib_end_origin": "2020-08", "test_start": "2021-01", "test_end": "2021-12", "maturity_buffer_months": 4},
        {"split_id": "LOCKED_TEST_2022", "role": "locked_test", "train_start": "2012-01", "train_end_origin": "2020-08",
         "calib_start": "2021-01", "calib_end_origin": "2021-08", "test_start": "2022-01", "test_end": "2022-12", "maturity_buffer_months": 4},
    ]
    df_splits = pd.DataFrame(splits)
    df_splits.to_csv(os.path.join(OUT_DIR, "split_manifest.csv"), index=False)

    # Pooled 80% threshold on the training window of the first locked split (origins <= 2019-08), Core-9
    sub_all = panel[(panel["ym"] >= "2012-01") & (panel["ym"] <= "2022-12")].copy()
    dev_train_c9 = sub_all[(sub_all["in_core9"] == 1) & (sub_all["ym"] <= "2019-08")]
    q80_reer_pooled = float(dev_train_c9["target_reer_vol_3m"].quantile(0.80))
    q80_res_pooled = float(dev_train_c9["target_res_drawdown_3m"].quantile(0.80))

    feas_rows = []
    for c, g in sub_all.groupby("country"):
        g = g.sort_values("ym")
        g_dev = g[g["ym"] <= "2020-12"]
        g_test = g[g["ym"] >= "2021-01"]

        q80_cty = float(g[g["ym"] <= "2019-08"]["target_reer_vol_3m"].quantile(0.80))
        y_pooled = (g["target_reer_vol_3m"] >= q80_reer_pooled).astype(int)
        y_cty = (g["target_reer_vol_3m"] >= q80_cty).astype(int)
        y_res_pooled = (g["target_res_drawdown_3m"] >= q80_res_pooled).astype(int)

        feas_rows.append({
            "country": c,
            "country_name": g["name"].iloc[0],
            "group": "Core-6" if g["in_swift6"].iloc[0] == 1 else ("Core-9" if g["in_core9"].iloc[0] == 1 else "Extended-6"),
            "n_origins_total": len(g),
            "n_origins_dev": len(g_dev),
            "n_origins_test24m": len(g_test),
            "reer_vol_3m_mean": round(float(g["target_reer_vol_3m"].mean()), 3),
            "reer_vol_3m_p80_cty": round(q80_cty, 3),
            "reer_stress_windows_pooled": int(y_pooled.sum()),
            "reer_stress_rate_pooled": round(float(y_pooled.mean()), 3),
            "reer_stress_windows_dev": int((g_dev["target_reer_vol_3m"] >= q80_reer_pooled).sum()),
            "reer_stress_windows_test24m": int((g_test["target_reer_vol_3m"] >= q80_reer_pooled).sum()),
            "reer_distinct_episodes_pooled": count_contiguous_episodes(y_pooled, cooldown=0),
            "reer_distinct_episodes_cty_thresh": count_contiguous_episodes(y_cty, cooldown=0),
            "res_stress_windows_pooled": int(y_res_pooled.sum()),
            "res_distinct_episodes_pooled": count_contiguous_episodes(y_res_pooled, cooldown=0),
        })

    df_feas = pd.DataFrame(feas_rows).sort_values(["group", "country"]).reset_index(drop=True)

    # Evaluation labels per fold, built exactly as in the forecasting experiments (common.fold_frames)
    from common import fold_frames
    core9 = sub_all[sub_all["in_core9"] == 1]
    fold_rows, prev_dec = [], {}
    for _, sp in df_splits.iterrows():
        tr, cal, te = fold_frames(core9, sp, h=3)
        thr = float(tr["target_reer_vol_3m"].quantile(0.80))
        y_te = (te.sort_values(["country", "ym"])["target_reer_vol_3m"] >= thr).astype(int)
        te = te.sort_values(["country", "ym"]).assign(y=y_te.values)
        fold_rows.append({
            "split_id": sp["split_id"], "role": sp["role"], "threshold_q80": round(thr, 4),
            "train_origins": f"{tr['ym'].min()} to {tr['ym'].max()}", "n_train": len(tr), "n_train_pos": int((tr["target_reer_vol_3m"] >= thr).sum()),
            "calib_origins": f"{cal['ym'].min()} to {cal['ym'].max()}", "n_calib": len(cal), "n_calib_pos": int((cal["target_reer_vol_3m"] >= thr).sum()),
            "test_origins": f"{te['ym'].min()} to {te['ym'].max()}", "n_test": len(te), "n_test_pos": int(te["y"].sum()),
            "test_episodes": int(sum(count_contiguous_episodes(g["y"].values, cooldown=0) for _, g in te.groupby("country"))),
            # runs that start in January while the previous fold's December window was high-risk; the pooled
            # event evaluation concatenates the folds and counts such a run once
            "episodes_continuing_previous_fold": int(sum(int(g["y"].values[0] == 1 and prev_dec.get(c, 0) == 1) for c, g in te.groupby("country"))),
            "test_pos_by_country": "; ".join(f"{c} {int(v)}" for c, v in te.groupby("country")["y"].sum().sort_values(ascending=False).items() if v > 0),
            "outcome_data_needed_to": te["target_3m_release_ym"].max(),
        })
        prev_dec = {c: int(g["y"].values[-1]) for c, g in te.groupby("country")}
    pd.DataFrame(fold_rows).to_csv(os.path.join(TAB_DIR, "table_folds_samples_events.csv"), index=False)
    df_feas.to_csv(os.path.join(TAB_DIR, "e02_stress_window_feasibility.csv"), index=False)
    print(f"  - Pooled 80% threshold (Core-9 Dev): REER V_3m = {q80_reer_pooled:.3f}%, Reserve Drawdown D_3m = {q80_res_pooled:.3f}%")
    print(f"  - Core-9 total REER stress windows: {df_feas[df_feas['group'].str.startswith('Core')]['reer_stress_windows_pooled'].sum()} "
          f"| Distinct episodes: {df_feas[df_feas['group'].str.startswith('Core')]['reer_distinct_episodes_pooled'].sum()}")


if __name__ == "__main__":
    panel = pd.read_csv(os.path.join(PROC_DIR, "panel_pseudo_realtime.csv"))
    run_e01_audit(panel)
    run_e02_feasibility_and_splits(panel)
    print("DONE: Step 2 (E01 & E02) completed successfully.")
