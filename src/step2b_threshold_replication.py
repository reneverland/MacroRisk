#!/usr/bin/env python3
"""
Step 2b: Replication of the original fixed-effects panel threshold regressions (Hansen, 1999)
==============================================================================================
Data: the authors' two historical regression datasets (data/raw/historylab, verbatim copies).
  Panel A: SWIFT payment share, 6 countries x 113 months (2012-08..2021-12), N = 678
  Panel B: FX derivatives turnover share, 9 countries x 132 months (2012-01..2022-12), N = 1188

Original specification (contemporaneous):
  y_it = mu_i + b1 CI_it 1(q_it <= g) + b2 CI_it 1(q_it > g) + rho y_i,t-L + theta' X_it + delta' R_it + e_it
  q = ins_quality (mean of six WGI dimensions); X = ln per-capita GDP (PPP), GDP growth, ln population,
  financial depth, financial openness, trade openness; R = other macro risks; y_i,t-L = the *_lag1
  column shipped with the dataset (a 6-month lag, see e01b_specification_search.csv).

Outputs (outputs/tables):
  e01b_specification_search.csv      candidate mappings / controls scored against the published table
  table2a_threshold_tests.csv        F statistic, bootstrap p, threshold, 95% CI (both panels, 6 risks)
  table2b_threshold_coefficients.csv regime-dependent CI coefficients and controls
  tableA1_threshold_wgi_dimensions.csv threshold tests with each WGI dimension as threshold variable
  tableA2_threshold_pseudo_realtime.csv lagged pseudo-real-time robustness version
  tableA3_threshold_trimming.csv     sensitivity of the main specification to the trimming fraction
"""

import os
import time
import warnings
from joblib import Parallel, delayed
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HL_DIR = os.path.join(BASE_DIR, "data", "raw", "historylab")
TAB_DIR = os.path.join(BASE_DIR, "outputs", "tables")
os.makedirs(TAB_DIR, exist_ok=True)

N_BOOT = int(os.environ.get("THRESH_NBOOT", 1999))
N_JOBS = int(os.environ.get("MACRORISK_NJOBS", 48))
LR_CRIT_95 = 7.35

PANELS = {
    "A_SWIFT": ("reg_swiftnew_20230613.xlsx", "SWIFT交易份额", "Swift Share"),
    "B_FX": ("reg_fxshare_20230613.xlsx", "本国货币外汇衍生品交易额", "FX Share"),
}

# Each risk lists candidate source columns; the first candidate is the full-coverage series.
RISKS = {
    "CPI_Vol": ["cpi_vol"],
    "FX_Vol": ["fxr_vol"],
    "CE_Vol": ["consump_volnew", "consump_vol"],
    "ER_Vol": ["real_ex_vol", "ex_vol"],
    "CG_Gap": ["credit_gdp_gap"],
    "Unemp": ["unemp"],
}
LAG_OF = {
    "cpi_vol": "cpi_vol_lag1", "fxr_vol": "fxr_vol_lag1", "consump_volnew": "consump_volnew_lag1",
    "consump_vol": "consump_volnew_lag1", "real_ex_vol": "real_ex_vol_lag1", "ex_vol": "ex_vol_lag1",
    "credit_gdp_gap": "credit_gdp_gap_lag1", "unemp": "unemp_lag1",
}
CONTROLS = ["pergdp_ppp", "gdp_grow", "pop", "stockvalue_gdp", "fin_open1", "tra"]
CONTROL_LABELS = {
    "pergdp_ppp": "Ln Per Capita GDP", "gdp_grow": "GDP Growth Rate", "pop": "Ln Population",
    "stockvalue_gdp": "Financial Depth", "fin_open1": "Financial Openness", "tra": "Trading Openness",
}
WGI_DIMS = {
    "VoiceandAccountability": "Voice and Accountability",
    "Political StabilityNoViolence": "Political Stability No Violence",
    "GovernmentEffectiveness": "Government Effectiveness",
    "RegulatoryQuality": "Regulatory Quality",
    "RuleofLaw": "Rule of Law",
    "ControlofCorruption": "Control of Corruption",
}

# Published values (Currency Internationalization.docx, Tables 2-4) used only to score the replication.
PUBLISHED = {
    "A_SWIFT": {
        "F": [400.68, 54.62, 120.64, 27.24, 83.12, 103.64],
        "gamma": [-0.7870, 0.4481, -0.7116, -0.4764, -0.3692, 0.0240],
        "t1": [12.37, 1.68, 9.10, 0.39, 0.94, -0.88],
        "t2": [-3.13, -7.16, -8.15, 0.25, -4.27, -1.20],
    },
    "B_FX": {
        "F": [276.57, 79.31, 219.67, 104.28, 34.61, 54.34],
        "gamma": [-0.2560, -0.7541, -0.7234, -0.7039, -0.1554, -0.1416],
        "t1": [2.19, 9.89, 14.50, 9.96, 2.15, 3.53],
        "t2": [2.23, 1.12, 1.86, -2.42, 1.26, -2.36],
    },
}


PUBLISHED_COEF = {
    ("A_SWIFT", "ci_regime1"): [(49.0647, 12.37), (0.0060, 1.68), (0.0455, 9.10), (0.3396, 0.39), (0.5579, 0.94), (-0.1582, -0.88)],
    ("A_SWIFT", "ci_regime2"): [(-1.0075, -3.13), (-0.1116, -7.16), (-0.0201, -8.15), (0.0863, 0.25), (-2.5950, -4.27), (-6.0032, -1.20)],
    ("B_FX", "ci_regime1"): [(84.6554, 2.19), (1.5950, 9.89), (1.5209, 14.50), (4.2070, 9.96), (14.5626, 2.15), (1.2196, 3.53)],
    ("B_FX", "ci_regime2"): [(52.1320, 2.23), (0.0335, 1.12), (0.0297, 1.86), (-1.1321, 2.42), (3.9821, 1.26), (-7.6749, -2.36)],
}


def replication_comparison(coefs):
    """Published vs replicated regime coefficients; classifies each published cell."""
    rows = []
    for (panel, term), pubs in PUBLISHED_COEF.items():
        for risk, (b_pub, t_pub) in zip(RISKS, pubs):
            r = coefs[(coefs["panel"] == panel) & (coefs["risk"] == risk) & (coefs["term"] == term)].iloc[0]
            b, tc, tcl = float(r["coef"]), float(r["t_conv"]), float(r["t_cluster"])
            coef_match = abs(b - b_pub) <= 0.005 * max(abs(b_pub), 1e-4) + 1e-4
            t_match = "cluster" if abs(tcl - t_pub) <= 0.015 else ("conventional" if abs(tc - t_pub) <= 0.015 else "none")
            digits_b = f"{abs(b):.4f}".replace(".", "")
            digits_p = f"{abs(b_pub):.4f}".replace(".", "")
            dropped_digit = (not coef_match) and len(digits_b) == len(digits_p) + 1 and any(
                digits_b[:i] + digits_b[i + 1:] == digits_p for i in range(len(digits_b)))
            if coef_match and t_match != "none":
                status = "reproduced"
            elif coef_match:
                status = "coefficient reproduced; t differs"
            elif dropped_digit or abs(abs(b) - abs(b_pub)) <= 0.005 * abs(b_pub):
                status = "suspected transcription error (digit/sign)"
            elif t_match != "none":
                status = "t reproduced; coefficient differs"
            else:
                status = "not reproduced"
            rows.append({"panel": panel, "risk": risk, "term": term, "coef_published": b_pub, "t_published": t_pub,
                         "coef_replicated": round(b, 4), "t_conventional": tc, "t_cluster": tcl,
                         "t_matches": t_match, "status": status})
    return pd.DataFrame(rows)


def load_panel(key):
    fname, ci_src, _ = PANELS[key]
    df = pd.read_excel(os.path.join(HL_DIR, fname))
    df = df.rename(columns={ci_src: "ci"})
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["country", "date"]).reset_index(drop=True)


def demean(a, codes, n_groups):
    a = np.asarray(a, dtype=float)
    if a.ndim == 1:
        a = a[:, None]
    sums = np.zeros((n_groups, a.shape[1]))
    np.add.at(sums, codes, a)
    counts = np.bincount(codes, minlength=n_groups)[:, None]
    return a - (sums / counts)[codes]


def ssr_of(X, y):
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    r = y - X @ beta
    return float(r @ r), beta, r


def threshold_grid(q, trim):
    qs = np.sort(q)
    n = len(qs)
    lo, hi = qs[int(np.floor(trim * n))], qs[int(np.ceil((1 - trim) * n)) - 1]
    cand = np.unique(q[(q >= lo) & (q <= hi)])
    # the largest value would leave regime 2 empty
    return cand[cand < q.max()]


def scan(ci, q, Z_dm, y_dm, codes, n_groups, grid):
    best = (np.inf, None)
    ssrs = np.empty(len(grid))
    for j, g in enumerate(grid):
        low = q <= g
        R = demean(np.column_stack([ci * low, ci * (~low)]), codes, n_groups)
        s, _, _ = ssr_of(np.column_stack([R, Z_dm]), y_dm)
        ssrs[j] = s
        if s < best[0]:
            best = (s, g)
    return best[0], best[1], ssrs


def hansen_threshold(df, y_col, ci_col, q_col, z_cols, trim=0.01, n_boot=N_BOOT, seed=20230613):
    cols = ["country", y_col, ci_col, q_col] + z_cols
    sub = df[cols].dropna().reset_index(drop=True)
    codes, uniq = pd.factorize(sub["country"])
    n_groups = len(uniq)
    n = len(sub)
    y = sub[y_col].values.astype(float)
    ci = sub[ci_col].values.astype(float)
    q = sub[q_col].values.astype(float)
    Z = sub[z_cols].values.astype(float)
    y_dm = demean(y, codes, n_groups).ravel()
    Z_dm = demean(Z, codes, n_groups)
    ci_dm = demean(ci, codes, n_groups)

    grid = threshold_grid(q, trim)
    if len(grid) < 2:
        return None
    X0 = np.column_stack([ci_dm, Z_dm])
    s0, b0, _ = ssr_of(X0, y_dm)
    s1, gamma, ssrs = scan(ci, q, Z_dm, y_dm, codes, n_groups, grid)
    sigma2 = s1 / (n - n_groups)
    f_stat = (s0 - s1) / sigma2
    n_periods = int(np.bincount(codes).max())
    # The published F statistics equal this value: residual variance divided by T(N-1) instead of N(T-1).
    f_stat_published_convention = (s0 - s1) / (s1 / (n - n_periods))
    lr = (ssrs - s1) / sigma2
    in_ci = grid[lr <= LR_CRIT_95]

    low = q <= gamma
    R = demean(np.column_stack([ci * low, ci * (~low)]), codes, n_groups)
    X1 = np.column_stack([R, Z_dm])
    _, b1, e1 = ssr_of(X1, y_dm)
    k = X1.shape[1]
    XtX_inv = np.linalg.pinv(X1.T @ X1)
    se_conv = np.sqrt(np.diag(XtX_inv) * (e1 @ e1) / (n - n_groups - k))
    meat = np.zeros((k, k))
    for gi in range(n_groups):
        m = codes == gi
        sg = X1[m].T @ e1[m]
        meat += np.outer(sg, sg)
    adj = (n_groups / (n_groups - 1)) * ((n - 1) / (n - k))
    se_cl = np.sqrt(np.diag(XtX_inv @ meat @ XtX_inv) * adj)

    # Hansen (1999) bootstrap under the null of no threshold: country blocks of residuals from the
    # threshold model are resampled with replacement and added to the linear-model fit.
    fit0 = X0 @ b0
    blocks = [np.where(codes == gi)[0] for gi in range(n_groups)]
    balanced = len({len(b) for b in blocks}) == 1

    def boot_chunk(chunk_seed, n_rep):
        rng = np.random.RandomState(chunk_seed)
        out = np.empty(n_rep)
        for bi in range(n_rep):
            if balanced:
                draw = rng.randint(0, n_groups, n_groups)
                e_star = np.concatenate([e1[blocks[d]] for d in draw])
            else:
                e_star = rng.choice(e1, size=n, replace=True)
            y_star = demean(fit0 + e_star, codes, n_groups).ravel()
            s0b, _, _ = ssr_of(X0, y_star)
            s1b, _, _ = scan(ci, q, Z_dm, y_star, codes, n_groups, grid)
            out[bi] = (s0b - s1b) / (s1b / (n - n_groups))
        return out

    if n_boot > 0:
        sizes = [len(c) for c in np.array_split(np.arange(n_boot), min(N_JOBS, n_boot))]
        parts = Parallel(n_jobs=N_JOBS, backend="loky")(delayed(boot_chunk)(seed + 7919 * j, m) for j, m in enumerate(sizes))
        boot_f = np.concatenate(parts)
        k_exceed = int(np.sum(boot_f >= f_stat))
        p_boot = (1 + k_exceed) / (n_boot + 1)
    else:
        k_exceed, p_boot = 0, np.nan

    names = ["ci_regime1", "ci_regime2"] + z_cols
    return {
        "n_obs": n, "n_countries": n_groups, "trim": trim, "grid_size": len(grid),
        "f_stat": f_stat, "f_stat_tn1": f_stat_published_convention, "p_boot": p_boot, "k_exceed": k_exceed,
        "p_mc_se": float(np.sqrt(p_boot * (1 - p_boot) / n_boot)) if n_boot > 0 else np.nan, "gamma": float(gamma),
        "ci_low": float(in_ci.min()), "ci_high": float(in_ci.max()),
        "share_regime1": float(low.mean()),
        "coef": dict(zip(names, b1)), "se_conv": dict(zip(names, se_conv)), "se_cl": dict(zip(names, se_cl)),
    }


def stars(p):
    return "***" if p < 0.01 else ("**" if p < 0.05 else ("*" if p < 0.10 else ""))


def t_stars(t, dof):
    from scipy import stats
    return stars(2 * (1 - stats.t.cdf(abs(t), dof)))


def other_risk_cols(df, own_risk, variant):
    others = [RISKS[r][0] for r in RISKS if r != own_risk]
    if variant == "none":
        return []
    if variant == "others_lag":
        return [LAG_OF[c] for c in others if LAG_OF[c] in df.columns and df[LAG_OF[c]].notna().mean() > 0.95]
    if variant == "others_contemp":
        return others
    raise ValueError(variant)


def run_spec(df, risk, y_col, variant, trim, n_boot):
    z = [LAG_OF[y_col]] + CONTROLS + other_risk_cols(df, risk, variant)
    return hansen_threshold(df, y_col, "ci", "ins_quality", z, trim=trim, n_boot=n_boot)


def specification_search(data):
    """Score candidate mappings against the published F statistics, thresholds and regime t statistics.
    Uses no bootstrap; the chosen variant is applied uniformly to every risk."""
    rows = []
    for key, df in data.items():
        pub = PUBLISHED[key]
        for variant in ["none", "others_lag", "others_contemp"]:
            for trim in [0.01, 0.05, 0.15]:
                for i, (risk, cands) in enumerate(RISKS.items()):
                    for y_col in cands:
                        res = run_spec(df, risk, y_col, variant, trim, n_boot=0)
                        if res is None:
                            continue
                        dof = res["n_obs"] - res["n_countries"] - len(res["coef"])
                        t1 = res["coef"]["ci_regime1"] / res["se_conv"]["ci_regime1"]
                        t2 = res["coef"]["ci_regime2"] / res["se_conv"]["ci_regime2"]
                        rows.append({
                            "panel": key, "risk": risk, "y_col": y_col, "other_risks": variant, "trim": trim,
                            "n_obs": res["n_obs"], "f_stat": round(res["f_stat"], 2),
                            "f_stat_tn1_convention": round(res["f_stat_tn1"], 2), "f_published": pub["F"][i],
                            "gamma": round(res["gamma"], 4), "gamma_published": pub["gamma"][i],
                            "t1": round(t1, 2), "t1_published": pub["t1"][i],
                            "t2": round(t2, 2), "t2_published": pub["t2"][i],
                            "abs_log_f_ratio": abs(np.log(max(res["f_stat"], 1e-6) / pub["F"][i])),
                            "abs_gamma_gap": abs(res["gamma"] - pub["gamma"][i]),
                            "abs_t_gap": abs(t1 - pub["t1"][i]) + abs(t2 - pub["t2"][i]),
                        })
    return pd.DataFrame(rows)


def choose_variant(search):
    s = search.copy()
    s["score"] = s["abs_log_f_ratio"] + s["abs_gamma_gap"] + 0.1 * s["abs_t_gap"]
    # y mapping per risk: the candidate whose best score (over variants) is lowest
    y_choice = s.groupby(["panel", "risk", "y_col"])["score"].min().reset_index()
    y_choice = y_choice.loc[y_choice.groupby(["panel", "risk"])["score"].idxmin()]
    y_map = {(r.panel, r.risk): r.y_col for r in y_choice.itertuples()}
    s_y = s[[y_map[(r.panel, r.risk)] == r.y_col for r in s.itertuples()]]
    agg = s_y.groupby(["other_risks", "trim"])["score"].mean().sort_values()
    variant, trim = agg.index[0]
    return y_map, variant, trim, agg


def build_tables(data, y_map, variant, trim):
    tests, coefs = [], []
    for key, df in data.items():
        label = PANELS[key][2]
        for risk in RISKS:
            y_col = y_map[(key, risk)]
            res = run_spec(df, risk, y_col, variant, trim, N_BOOT)
            if res is None:
                continue
            dof = res["n_obs"] - res["n_countries"] - len(res["coef"])
            tests.append({
                "panel": key, "ci_indicator": label, "risk": risk, "y_col": y_col,
                "n_obs": res["n_obs"], "n_countries": res["n_countries"],
                "f_stat": round(res["f_stat"], 2), "f_stat_tn1_convention": round(res["f_stat_tn1"], 2),
                "p_boot": round(res["p_boot"], 4), "k_exceed": res["k_exceed"], "p_mc_se": round(res["p_mc_se"], 4),
                "p_stars": stars(res["p_boot"]), "threshold": round(res["gamma"], 4),
                "ci95_low": round(res["ci_low"], 4), "ci95_high": round(res["ci_high"], 4),
                "share_obs_regime1": round(res["share_regime1"], 3),
                "f_published": PUBLISHED[key]["F"][list(RISKS).index(risk)],
                "threshold_published": PUBLISHED[key]["gamma"][list(RISKS).index(risk)],
                "trim": trim, "other_risks": variant, "n_boot": N_BOOT,
            })
            for name, b in res["coef"].items():
                t_c = b / res["se_conv"][name]
                t_cl = b / res["se_cl"][name]
                coefs.append({
                    "panel": key, "ci_indicator": label, "risk": risk, "term": name,
                    "term_label": {"ci_regime1": f"{label} x 1(IQ<=gamma)", "ci_regime2": f"{label} x 1(IQ>gamma)"}.get(
                        name, CONTROL_LABELS.get(name, "Lagged dep." if name == LAG_OF[y_col] else f"Other risk: {name}")),
                    "coef": b, "t_conv": round(t_c, 2), "stars_conv": t_stars(t_c, dof),
                    "t_cluster": round(t_cl, 2), "stars_cluster": t_stars(t_cl, res["n_countries"] - 1),
                    "n_obs": res["n_obs"],
                })
    return pd.DataFrame(tests), pd.DataFrame(coefs)


def wgi_dimension_tables(data, y_map, variant, trim):
    rows = []
    for key, df in data.items():
        for wgi, wlabel in WGI_DIMS.items():
            for risk in RISKS:
                y_col = y_map[(key, risk)]
                z = [LAG_OF[y_col]] + CONTROLS + other_risk_cols(df, risk, variant)
                res = hansen_threshold(df, y_col, "ci", wgi, z, trim=trim, n_boot=N_BOOT)
                if res is None:
                    continue
                dof = res["n_obs"] - res["n_countries"] - len(res["coef"])
                t1 = res["coef"]["ci_regime1"] / res["se_conv"]["ci_regime1"]
                t2 = res["coef"]["ci_regime2"] / res["se_conv"]["ci_regime2"]
                rows.append({
                    "panel": key, "wgi_dimension": wlabel, "risk": risk, "n_obs": res["n_obs"], "n_countries": res["n_countries"],
                    "f_stat": round(res["f_stat"], 2), "p_boot": round(res["p_boot"], 4), "p_stars": stars(res["p_boot"]),
                    "threshold": round(res["gamma"], 4), "ci95_low": round(res["ci_low"], 4), "ci95_high": round(res["ci_high"], 4),
                    "coef_regime1": res["coef"]["ci_regime1"], "t_regime1": round(t1, 2),
                    "coef_regime2": res["coef"]["ci_regime2"], "t_regime2": round(t2, 2),
                })
    return pd.DataFrame(rows)


def pseudo_realtime_version(df):
    """Lagged robustness: CI from month t-1; annual variables (WGI, controls) for year Y become usable in
    September of Y+1, so month m of year T uses year T-1 if m >= 9 else year T-2."""
    df = df.copy()
    df["ci_rt"] = df.groupby("country")["ci"].shift(1)
    annual = ["ins_quality"] + CONTROLS
    yearly = df.groupby(["country", "year"])[annual].mean().reset_index()
    df["src_year"] = np.where(df["date"].dt.month >= 9, df["year"] - 1, df["year"] - 2)
    yearly = yearly.rename(columns={"year": "src_year", **{c: c + "_rt" for c in annual}})
    df = df.merge(yearly, on=["country", "src_year"], how="left")
    return df


def pseudo_realtime_tables(data, y_map, variant, trim):
    rows = []
    for key, df in data.items():
        d = pseudo_realtime_version(df)
        # gdp_grow varies within year in the source, so it is treated as a monthly series released with a 1-month lag
        d["gdp_grow"] = df.groupby("country")["gdp_grow"].shift(1).values
        for risk in RISKS:
            y_col = y_map[(key, risk)]
            z = [LAG_OF[y_col]] + [c + "_rt" for c in CONTROLS if c != "gdp_grow"] + ["gdp_grow"] + other_risk_cols(d, risk, variant)
            res = hansen_threshold(d, y_col, "ci_rt", "ins_quality_rt", z, trim=trim, n_boot=N_BOOT)
            if res is None:
                continue
            t1 = res["coef"]["ci_regime1"] / res["se_conv"]["ci_regime1"]
            t2 = res["coef"]["ci_regime2"] / res["se_conv"]["ci_regime2"]
            rows.append({
                "panel": key, "risk": risk, "y_col": y_col, "n_obs": res["n_obs"], "n_countries": res["n_countries"],
                "f_stat": round(res["f_stat"], 2), "p_boot": round(res["p_boot"], 4), "p_stars": stars(res["p_boot"]),
                "threshold": round(res["gamma"], 4), "ci95_low": round(res["ci_low"], 4), "ci95_high": round(res["ci_high"], 4),
                "coef_regime1": res["coef"]["ci_regime1"], "t_regime1": round(t1, 2),
                "t_regime1_cluster": round(res["coef"]["ci_regime1"] / res["se_cl"]["ci_regime1"], 2),
                "coef_regime2": res["coef"]["ci_regime2"], "t_regime2": round(t2, 2),
                "t_regime2_cluster": round(res["coef"]["ci_regime2"] / res["se_cl"]["ci_regime2"], 2),
            })
    return pd.DataFrame(rows)


def trimming_sensitivity(data, y_map, variant):
    rows = []
    for key, df in data.items():
        for trim in [0.01, 0.05, 0.10, 0.15]:
            for risk in RISKS:
                res = run_spec(df, risk, y_map[(key, risk)], variant, trim, N_BOOT)
                if res is None:
                    continue
                rows.append({
                    "panel": key, "risk": risk, "trim": trim, "n_obs": res["n_obs"], "n_countries": res["n_countries"], "f_stat": round(res["f_stat"], 2),
                    "p_boot": round(res["p_boot"], 4), "threshold": round(res["gamma"], 4),
                    "share_obs_regime1": round(res["share_regime1"], 3),
                    "coef_regime1": res["coef"]["ci_regime1"],
                    "t_regime1_cluster": round(res["coef"]["ci_regime1"] / res["se_cl"]["ci_regime1"], 2),
                    "coef_regime2": res["coef"]["ci_regime2"],
                    "t_regime2_cluster": round(res["coef"]["ci_regime2"] / res["se_cl"]["ci_regime2"], 2),
                })
    return pd.DataFrame(rows)


def threshold_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig_dir = os.path.join(BASE_DIR, "outputs", "figures")
    os.makedirs(fig_dir, exist_ok=True)
    tests = pd.read_csv(os.path.join(TAB_DIR, "table2a_threshold_tests.csv"))
    trim = pd.read_csv(os.path.join(TAB_DIR, "tableA3_threshold_trimming.csv"))
    prt = pd.read_csv(os.path.join(TAB_DIR, "tableA2_threshold_pseudo_realtime.csv"))

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0), gridspec_kw={"width_ratios": [1, 1.5]})
    ax = axes[0]
    for key, mk, col in [("A_SWIFT", "o", "#C0392B"), ("B_FX", "s", "#2874A6")]:
        g = tests[tests["panel"] == key]
        ax.scatter(g["f_published"], g["f_stat_tn1_convention"], marker=mk, color=col, label=f"{PANELS[key][2]}: T(N-1) convention")
        ax.scatter(g["f_published"], g["f_stat"], marker=mk, facecolors="none", edgecolors=col, label=f"{PANELS[key][2]}: Hansen N(T-1)")
    lim = [10, 600]
    ax.plot(lim, lim, "k--", linewidth=1)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Published F statistic"); ax.set_ylabel("Replicated F statistic")
    ax.set_title("(a) Threshold F statistics", fontweight="bold")
    ax.legend(fontsize=7, loc="upper left"); ax.grid(True, linestyle=":", alpha=0.5)

    ax = axes[1]
    labels, x = [], 0
    for key in ["A_SWIFT", "B_FX"]:
        for risk in RISKS:
            vals = [trim[(trim["panel"] == key) & (trim["risk"] == risk) & (trim["trim"] == t)]["p_boot"].iloc[0] for t in [0.01, 0.15]]
            pr = prt[(prt["panel"] == key) & (prt["risk"] == risk)]["p_boot"]
            vals.append(float(pr.iloc[0]) if len(pr) else np.nan)
            for j, (v, col) in enumerate(zip(vals, ["#5D6D7E", "#F39C12", "#27AE60"])):
                ax.bar(x + (j - 1) * 0.27, v, 0.27, color=col, label=["Original spec, 1% trim", "Original spec, 15% trim", "Pseudo-real-time, 1% trim"][j] if x == 0 else None)
            labels.append(f"{'A' if key == 'A_SWIFT' else 'B'}:{risk}")
            x += 1
    ax.axhline(0.05, color="black", linestyle="--", linewidth=1)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7.5)
    ax.set_ylabel(f"Bootstrap p-value ({N_BOOT:,} draws)", fontsize=10)
    ax.set_title("(b) Fragility of the threshold effect", fontweight="bold")
    ax.legend(fontsize=7, loc="upper left"); ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    for ext in ["pdf", "png"]:
        fig.savefig(os.path.join(fig_dir, f"fig8_threshold_replication.{ext}"), bbox_inches="tight", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    t0 = time.time()
    data = {k: load_panel(k) for k in PANELS}
    for k, d in data.items():
        print(f"[2b] {k}: {len(d)} rows, {d['country'].nunique()} countries, {d['date'].min():%Y-%m}..{d['date'].max():%Y-%m}")

    search = specification_search(data)
    y_map, variant, trim, agg = choose_variant(search)
    search.to_csv(os.path.join(TAB_DIR, "e01b_specification_search.csv"), index=False)
    print("[2b] Mean replication score by (other_risks, trim):\n", agg.round(3).to_string())
    print(f"[2b] Chosen: other_risks={variant}, trim={trim}, y_map={y_map}")

    tests, coefs = build_tables(data, y_map, variant, trim)
    tests.to_csv(os.path.join(TAB_DIR, "table2a_threshold_tests.csv"), index=False)
    coefs.to_csv(os.path.join(TAB_DIR, "table2b_threshold_coefficients.csv"), index=False)
    replication_comparison(coefs).to_csv(os.path.join(TAB_DIR, "table2c_published_vs_replicated.csv"), index=False)
    print(tests[["panel", "risk", "n_obs", "f_stat", "f_stat_tn1_convention", "f_published", "p_boot", "threshold", "threshold_published", "share_obs_regime1"]].to_string())
    print(f"[2b] main tables done ({time.time() - t0:.0f}s)")

    trimming_sensitivity(data, y_map, variant).to_csv(os.path.join(TAB_DIR, "tableA3_threshold_trimming.csv"), index=False)
    pseudo_realtime_tables(data, y_map, variant, trim).to_csv(os.path.join(TAB_DIR, "tableA2_threshold_pseudo_realtime.csv"), index=False)
    print(f"[2b] trimming + pseudo-real-time done ({time.time() - t0:.0f}s)")
    wgi_dimension_tables(data, y_map, variant, trim).to_csv(os.path.join(TAB_DIR, "tableA1_threshold_wgi_dimensions.csv"), index=False)
    threshold_figure()
    print(f"DONE: Step 2b completed in {time.time() - t0:.0f}s")
