#!/usr/bin/env python3
"""
Step 1: Authoritative Multi-Source Data Fetching & Pseudo-Real-Time Panel Reconstruction
=========================================================================================
Sources:
1. BIS Statistical API (stats.bis.org):
   - WS_EER: Monthly Real Effective Exchange Rate (Broad basket, M.R.B.*) & US Dollar NEER
   - WS_LONG_CPI: Monthly Consumer Price Index (M.*.628)
   - WS_CBPOL: Monthly Central Bank Policy Rate (M.*)
   - WS_XRU: Monthly Bilateral USD Exchange Rate (M.*..A)
   - WS_TC: Quarterly Total Credit to Private Non-Financial Sector (% of GDP)
   - WS_CREDIT_GAP: Quarterly Credit-to-GDP Gap (%)
2. IMF International Financial Statistics via DBnomics (api.db.nomics.world):
   - M.*.RAXG_USD: Monthly Official Reserve Assets excluding Gold (USD millions)
3. World Bank API (api.worldbank.org):
   - WGI 6 dimensions: VA.EST, PV.EST, GE.EST, RQ.EST, RL.EST, CC.EST
   - Macro indicators: NY.GDP.PCAP.KD, NY.GDP.MKTP.KD.ZG, SP.POP.TOTL, NE.TRD.GNFS.ZS,
     FS.AST.PRVT.GD.ZS, SL.UEM.TOTL.ZS, FI.RES.TOTL.CD, NE.CON.PRVT.KD.ZG,
     BX.KLT.DINV.WD.GD.ZS, BM.KLT.DINV.WD.GD.ZS
4. Authors' historical regression datasets (data/raw/historylab):
   - Monthly SWIFT payment share (%) for CHN, RUS, POL, MEX, ZAF, HUN (2012-08..2021-12)
   - Monthly domestic-currency FX derivatives turnover share for the Core-9 (2012-01..2022-12)
   Both enter the pseudo-real-time panel with a 1-month publication lag.
"""

import io
import os
import json
import time
import hashlib
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROC_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# 9 Core Emerging Market Economies from original manuscript + 6 Extended EMEs for E13 external validation
COUNTRIES = {
    # Core 6 (SWIFT + FX Share)
    "CHN": {"iso2": "CN", "name": "China", "currency": "CNY", "in_swift6": 1, "in_core9": 1},
    "RUS": {"iso2": "RU", "name": "Russia", "currency": "RUB", "in_swift6": 1, "in_core9": 1},
    "POL": {"iso2": "PL", "name": "Poland", "currency": "PLN", "in_swift6": 1, "in_core9": 1},
    "MEX": {"iso2": "MX", "name": "Mexico", "currency": "MXN", "in_swift6": 1, "in_core9": 1},
    "ZAF": {"iso2": "ZA", "name": "South Africa", "currency": "ZAR", "in_swift6": 1, "in_core9": 1},
    "HUN": {"iso2": "HU", "name": "Hungary", "currency": "HUF", "in_swift6": 1, "in_core9": 1},
    # Additional 3 in Core 9 (FX Share)
    "IND": {"iso2": "IN", "name": "India", "currency": "INR", "in_swift6": 0, "in_core9": 1},
    "KOR": {"iso2": "KR", "name": "South Korea", "currency": "KRW", "in_swift6": 0, "in_core9": 1},
    "BRA": {"iso2": "BR", "name": "Brazil", "currency": "BRL", "in_swift6": 0, "in_core9": 1},
    # Extended 6 EMEs for external out-of-sample validation (E13)
    "TUR": {"iso2": "TR", "name": "Turkey", "currency": "TRY", "in_swift6": 0, "in_core9": 0},
    "IDN": {"iso2": "ID", "name": "Indonesia", "currency": "IDR", "in_swift6": 0, "in_core9": 0},
    "THA": {"iso2": "TH", "name": "Thailand", "currency": "THB", "in_swift6": 0, "in_core9": 0},
    "MYS": {"iso2": "MY", "name": "Malaysia", "currency": "MYR", "in_swift6": 0, "in_core9": 0},
    "CHL": {"iso2": "CL", "name": "Chile", "currency": "CLP", "in_swift6": 0, "in_core9": 0},
    "COL": {"iso2": "CO", "name": "Colombia", "currency": "COP", "in_swift6": 0, "in_core9": 0},
}

ISO2_TO_ISO3 = {v["iso2"]: k for k, v in COUNTRIES.items()}
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) IEEEAccessRepro/1.0"}


def fetch_url_with_retry(url, timeout=20, retries=3):
    """Fetch URL trying current environment first, then direct no-proxy fallback."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 50:
                return r.text
        except Exception:
            pass
        try:
            s = requests.Session()
            s.trust_env = False
            r = s.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 50:
                return r.text
        except Exception:
            pass
        time.sleep(1.0)
    raise RuntimeError(f"Failed to fetch URL after {retries} retries: {url}")


def fetch_bis_datasets():
    """Fetch monthly REER, CPI, Policy Rate, USD XR, and quarterly Credit/Gap from BIS API."""
    print("[1/5] Fetching BIS monthly & quarterly datasets...")
    iso2_plus = "+".join([v["iso2"] for v in COUNTRIES.values()])

    bis_urls = {
        "bis_reer.csv": f"https://stats.bis.org/api/v1/data/WS_EER/M.R.B.{iso2_plus}+US+XM?startPeriod=2009-01&format=csv",
        "bis_neer_us.csv": "https://stats.bis.org/api/v1/data/WS_EER/M.N.B.US+XM?startPeriod=2009-01&format=csv",
        "bis_cpi.csv": f"https://stats.bis.org/api/v1/data/WS_LONG_CPI/M.{iso2_plus}.628?startPeriod=2009-01&format=csv",
        "bis_cbpol.csv": f"https://stats.bis.org/api/v1/data/WS_CBPOL/M.{iso2_plus}+US?startPeriod=2009-01&format=csv",
        "bis_xru.csv": f"https://stats.bis.org/api/v1/data/WS_XRU/M.{iso2_plus}..A?startPeriod=2009-01&format=csv",
        "bis_credit_tc.csv": f"https://stats.bis.org/api/v1/data/WS_TC/Q.{iso2_plus}.P.A.M.770.A?startPeriod=2009-01&format=csv",
        "bis_credit_gap.csv": f"https://stats.bis.org/api/v1/data/WS_CREDIT_GAP/Q.{iso2_plus}.P.A.C?startPeriod=2009-01&format=csv",
    }

    for fname, url in bis_urls.items():
        fpath = os.path.join(RAW_DIR, fname)
        if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
            print(f"  - Cached {fname} ({os.path.getsize(fpath)} bytes)")
            continue
        txt = fetch_url_with_retry(url, timeout=25)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"  - Downloaded {fname} ({len(txt)} bytes)")


def fetch_imf_reserves_dbnomics():
    """Fetch monthly Official FX Reserves excluding gold (RAXG_USD) from IMF IFS via DBnomics."""
    print("[2/5] Fetching IMF IFS monthly FX reserves (RAXG_USD) via DBnomics...")
    fpath = os.path.join(RAW_DIR, "imf_ifs_reserves_monthly.csv")
    if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        print(f"  - Cached imf_ifs_reserves_monthly.csv")
        return pd.read_csv(fpath)

    rows = []

    def fetch_one_country(iso3, info):
        iso2 = info["iso2"]
        url = f"https://api.db.nomics.world/v22/series/IMF/IFS/M.{iso2}.RAXG_USD?observations=1"
        try:
            txt = fetch_url_with_retry(url, timeout=15, retries=2)
            js = json.loads(txt)
            docs = js.get("series", {}).get("docs", [])
            if docs:
                periods = docs[0].get("period", [])
                vals = docs[0].get("value", [])
                out = []
                for p, v in zip(periods, vals):
                    if p >= "2009-01" and v is not None and v != "NA":
                        out.append({"country": iso3, "ym": p, "fx_reserves_usd_m": float(v)})
                return out
        except Exception as e:
            print(f"  ! Warning fetching RAXG_USD for {iso3}: {e}")
        return []

    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(fetch_one_country, k, v): k for k, v in COUNTRIES.items()}
        for fut in as_completed(futs):
            res = fut.result()
            rows.extend(res)

    df_res = pd.DataFrame(rows).sort_values(["country", "ym"]).reset_index(drop=True)
    df_res.to_csv(fpath, index=False)
    print(f"  - Saved imf_ifs_reserves_monthly.csv ({len(df_res)} country-months)")
    return df_res


VINTAGE_DIR = os.path.join(RAW_DIR, "vintage_202610")


def fetch_imf_irfcl_extension():
    """IMF IRFCL (api.imf.org, SDMX 3.0): official reserve assets (IRFCL65) minus gold (IRFCL56), monetary
    authorities, USD. Equals IFS RAXG_USD on the overlap; used only for months after each country's last
    DBnomics observation (DBnomics stopped updating IFS in 2025)."""
    os.makedirs(VINTAGE_DIR, exist_ok=True)
    fpath = os.path.join(VINTAGE_DIR, "imf_irfcl_reserves_monthly.csv")
    if os.path.exists(fpath):
        return pd.read_csv(fpath)
    rows = []
    for iso3 in COUNTRIES:
        url = (f"https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/IRFCL/%2B/{iso3}."
               f"IRFCLDT1_IRFCL65_USD+IRFCLDT1_IRFCL56_USD.S1XS1311.M?startPeriod=2009-01")
        try:
            js = json.loads(fetch_url_with_retry(url, timeout=40, retries=2))
        except Exception as e:
            print(f"  ! IRFCL {iso3}: {e}")
            continue
        st = js["data"]["structures"][0]
        dims = st["dimensions"]["series"]
        tp = [t["value"] for t in st["dimensions"]["observation"][0]["values"]]
        for key, s in js["data"]["dataSets"][0].get("series", {}).items():
            ind = dims[1]["values"][int(key.split(":")[1])]["id"]
            for k, o in s["observations"].items():
                if o[0] not in (None, "", "NaN"):
                    rows.append({"country": iso3, "ym": tp[int(k)].replace("-M", "-"), "indicator": ind, "value_usd": float(o[0])})
    df = pd.DataFrame(rows)
    df.to_csv(fpath, index=False)
    print(f"  - Saved {fpath} ({len(df)} rows)")
    return df


def extend_reserves(df_res):
    try:
        irf = fetch_imf_irfcl_extension()
    except Exception as e:
        print(f"  ! IRFCL extension unavailable: {e}")
        return df_res
    if irf.empty:
        return df_res
    w = irf.pivot_table(index=["country", "ym"], columns="indicator", values="value_usd").reset_index()
    if not {"IRFCLDT1_IRFCL65_USD", "IRFCLDT1_IRFCL56_USD"} <= set(w.columns):
        return df_res
    w["fx_reserves_usd_m"] = (w["IRFCLDT1_IRFCL65_USD"] - w["IRFCLDT1_IRFCL56_USD"].fillna(0.0)) / 1e6
    w = w.dropna(subset=["fx_reserves_usd_m"])
    last = df_res.groupby("country")["ym"].max()
    ext = w[w["ym"] > w["country"].map(last).fillna("0000-00")][["country", "ym", "fx_reserves_usd_m"]]
    ov = df_res.merge(w[["country", "ym", "fx_reserves_usd_m"]], on=["country", "ym"], suffixes=("", "_irfcl")).dropna()
    rel = (ov["fx_reserves_usd_m_irfcl"] / ov["fx_reserves_usd_m"] - 1).abs()
    print(f"  - IRFCL vs IFS overlap: {len(ov)} months, median abs rel. diff {rel.median():.5f}; appended {len(ext)} months")
    pd.DataFrame({"n_overlap": [len(ov)], "median_abs_rel_diff": [rel.median()], "p95_abs_rel_diff": [rel.quantile(0.95)],
                  "n_appended": [len(ext)]}).to_csv(os.path.join(VINTAGE_DIR, "irfcl_ifs_overlap_check.csv"), index=False)
    return pd.concat([df_res, ext], ignore_index=True).sort_values(["country", "ym"]).reset_index(drop=True)


def fetch_worldbank_indicators():
    """Fetch WGI 6 dimensions and macro control variables from World Bank API."""
    print("[3/5] Fetching World Bank WGI & macroeconomic indicators...")
    fpath = os.path.join(RAW_DIR, "worldbank_annual.csv")
    if os.path.exists(fpath) and os.path.getsize(fpath) > 1000:
        print("  - Cached worldbank_annual.csv")
        return pd.read_csv(fpath)

    wb_indicators = {
        # WGI 6 dimensions (World Bank source=75 codes)
        "GOV_WGI_VA.EST": "wgi_va",
        "GOV_WGI_PV.EST": "wgi_pv",
        "GOV_WGI_GE.EST": "wgi_ge",
        "GOV_WGI_RQ.EST": "wgi_rq",
        "GOV_WGI_RL.EST": "wgi_rl",
        "GOV_WGI_CC.EST": "wgi_cc",
        # Macro controls
        "NY.GDP.PCAP.KD": "gdp_per_capita_const",
        "NY.GDP.MKTP.KD.ZG": "gdp_growth_ann",
        "SP.POP.TOTL": "population_total",
        "FS.AST.PRVT.GD.ZS": "private_credit_gdp_wb",
        "NE.TRD.GNFS.ZS": "trade_openness_wb",
        "SL.UEM.TOTL.ZS": "unemp_rate_wb",
        "FI.RES.TOTL.CD": "total_reserves_wb_usd",
        "NE.CON.PRVT.KD.ZG": "cons_exp_growth_wb",
        "BX.KLT.DINV.WD.GD.ZS": "fdi_inflow_gdp",
        "BM.KLT.DINV.WD.GD.ZS": "fdi_outflow_gdp",
        "NY.GDP.MKTP.CD": "gdp_current_usd",
    }

    iso3_str = ";".join(COUNTRIES.keys())
    all_records = []

    def fetch_wb_ind(ind_code, col_name):
        src_param = "&source=75" if ind_code.startswith("GOV_WGI_") else ""
        url = f"https://api.worldbank.org/v2/country/{iso3_str}/indicator/{ind_code}?date=2008:2024{src_param}&format=json&per_page=1000"
        txt = fetch_url_with_retry(url, timeout=20)
        js = json.loads(txt)
        recs = []
        if isinstance(js, list) and len(js) > 1 and js[1]:
            for item in js[1]:
                c_iso3 = item.get("countryiso3code")
                yr = item.get("date")
                val = item.get("value")
                if c_iso3 in COUNTRIES and yr and val is not None:
                    recs.append({"country": c_iso3, "year": int(yr), "variable": col_name, "value": float(val)})
        return recs

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch_wb_ind, k, v): v for k, v in wb_indicators.items()}
        for fut in as_completed(futs):
            all_records.extend(fut.result())

    df_long = pd.DataFrame(all_records)
    df_wb = df_long.pivot_table(index=["country", "year"], columns="variable", values="value").reset_index()
    df_wb.to_csv(fpath, index=False)
    print(f"  - Saved worldbank_annual.csv ({len(df_wb)} country-years, {df_wb.shape[1]} columns)")
    return df_wb


HISTORYLAB_DIR = os.path.join(BASE_DIR, "data", "raw", "historylab")
HISTORYLAB_COUNTRY_MAP = {
    "China": "CHN", "Russian Federation": "RUS", "Poland": "POL", "Mexico": "MEX",
    "South Africa": "ZAF", "Hungary": "HUN", "India": "IND", "Korea, Rep.": "KOR", "Brazil": "BRA",
}


def build_ci_series(months_index):
    """
    Currency internationalization (CI) series taken verbatim from the authors' historical
    regression datasets (data/raw/historylab, SHA256 in SHA256SUMS.txt):
      - reg_swiftnew_20230613.xlsx: SWIFT payment share (%), 6 countries, 2012-08..2021-12
      - reg_fxshare_20230613.xlsx: domestic-currency FX derivatives turnover share, 9 countries, 2012-01..2022-12
    Values are reported for the month in which they were observed; publication lags are applied
    later in build_pseudo_realtime_panel. Months outside source coverage stay missing here.
    """
    def load(fname, src_col, out_col):
        df = pd.read_excel(os.path.join(HISTORYLAB_DIR, fname))
        df["country"] = df["country"].map(HISTORYLAB_COUNTRY_MAP)
        df["ym"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
        return df[["country", "ym", src_col]].rename(columns={src_col: out_col})

    df_swift = load("reg_swiftnew_20230613.xlsx", "SWIFT交易份额", "swift_share_raw")
    df_fx = load("reg_fxshare_20230613.xlsx", "本国货币外汇衍生品交易额", "fx_share_raw")
    grid = pd.MultiIndex.from_product([list(COUNTRIES.keys()), months_index], names=["country", "ym"]).to_frame().reset_index(drop=True)
    out = grid.merge(df_fx, on=["country", "ym"], how="left").merge(df_swift, on=["country", "ym"], how="left")
    return out


def parse_bis_csvs():
    """Parse downloaded BIS CSV files into clean monthly/quarterly tables."""
    # 1. REER (M.R.B.*)
    df_reer_raw = pd.read_csv(os.path.join(RAW_DIR, "bis_reer.csv"))
    df_reer_raw = df_reer_raw[df_reer_raw["REF_AREA"].isin(list(ISO2_TO_ISO3.keys()))].copy()
    df_reer_raw["country"] = df_reer_raw["REF_AREA"].map(ISO2_TO_ISO3)
    df_reer = df_reer_raw[["country", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "ym", "OBS_VALUE": "reer_index"}
    )
    df_reer["reer_index"] = pd.to_numeric(df_reer["reer_index"], errors="coerce")
    df_reer = df_reer.dropna().drop_duplicates(["country", "ym"]).sort_values(["country", "ym"])

    # 2. US Broad Dollar NEER (Global common factor)
    df_us_raw = pd.read_csv(os.path.join(RAW_DIR, "bis_neer_us.csv"))
    df_us = df_us_raw[df_us_raw["REF_AREA"] == "US"][["TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "ym", "OBS_VALUE": "usd_broad_neer"}
    )
    df_us["usd_broad_neer"] = pd.to_numeric(df_us["usd_broad_neer"], errors="coerce")
    df_us = df_us.dropna().drop_duplicates("ym").sort_values("ym")
    df_us["usd_neer_ret_1m"] = 100.0 * np.log(df_us["usd_broad_neer"] / df_us["usd_broad_neer"].shift(1))
    df_us["usd_neer_vol_3m"] = df_us["usd_neer_ret_1m"].rolling(3).std()

    # 3. CPI (M.*.628)
    df_cpi_raw = pd.read_csv(os.path.join(RAW_DIR, "bis_cpi.csv"))
    df_cpi_raw = df_cpi_raw[df_cpi_raw["REF_AREA"].isin(list(ISO2_TO_ISO3.keys()))].copy()
    df_cpi_raw["country"] = df_cpi_raw["REF_AREA"].map(ISO2_TO_ISO3)
    df_cpi = df_cpi_raw[["country", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "ym", "OBS_VALUE": "cpi_index"}
    )
    df_cpi["cpi_index"] = pd.to_numeric(df_cpi["cpi_index"], errors="coerce")
    df_cpi = df_cpi.dropna().drop_duplicates(["country", "ym"]).sort_values(["country", "ym"])

    # 4. Central Bank Policy Rate (M.*)
    df_cb_raw = pd.read_csv(os.path.join(RAW_DIR, "bis_cbpol.csv"))
    df_us_rate = df_cb_raw[df_cb_raw["REF_AREA"] == "US"][["TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "ym", "OBS_VALUE": "us_policy_rate"}
    )
    df_us_rate["us_policy_rate"] = pd.to_numeric(df_us_rate["us_policy_rate"], errors="coerce")
    df_us_rate = df_us_rate.dropna().drop_duplicates("ym").sort_values("ym")

    df_cb = df_cb_raw[df_cb_raw["REF_AREA"].isin(list(ISO2_TO_ISO3.keys()))].copy()
    df_cb["country"] = df_cb["REF_AREA"].map(ISO2_TO_ISO3)
    df_cb = df_cb[["country", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "ym", "OBS_VALUE": "cb_policy_rate"}
    )
    df_cb["cb_policy_rate"] = pd.to_numeric(df_cb["cb_policy_rate"], errors="coerce")
    df_cb = df_cb.dropna().drop_duplicates(["country", "ym"]).sort_values(["country", "ym"])

    # 5. Quarterly Private Credit to GDP (WS_TC)
    df_tc_raw = pd.read_csv(os.path.join(RAW_DIR, "bis_credit_tc.csv"))
    df_tc_raw = df_tc_raw[df_tc_raw["BORROWERS_CTY"].isin(list(ISO2_TO_ISO3.keys()))].copy()
    df_tc_raw["country"] = df_tc_raw["BORROWERS_CTY"].map(ISO2_TO_ISO3)
    df_tc = df_tc_raw[["country", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "yq", "OBS_VALUE": "bis_credit_to_gdp"}
    )
    df_tc["bis_credit_to_gdp"] = pd.to_numeric(df_tc["bis_credit_to_gdp"], errors="coerce")
    df_tc = df_tc.dropna().drop_duplicates(["country", "yq"]).sort_values(["country", "yq"])

    # 6. Quarterly Credit-to-GDP Gap (WS_CREDIT_GAP)
    df_cg_raw = pd.read_csv(os.path.join(RAW_DIR, "bis_credit_gap.csv"))
    df_cg_raw = df_cg_raw[df_cg_raw["BORROWERS_CTY"].isin(list(ISO2_TO_ISO3.keys()))].copy()
    df_cg_raw["country"] = df_cg_raw["BORROWERS_CTY"].map(ISO2_TO_ISO3)
    df_cg = df_cg_raw[["country", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"TIME_PERIOD": "yq", "OBS_VALUE": "bis_credit_gap"}
    )
    df_cg["bis_credit_gap"] = pd.to_numeric(df_cg["bis_credit_gap"], errors="coerce")
    df_cg = df_cg.dropna().drop_duplicates(["country", "yq"]).sort_values(["country", "yq"])

    return df_reer, df_us, df_cpi, df_cb, df_us_rate, df_tc, df_cg


def build_pseudo_realtime_panel(df_reer, df_us, df_cpi, df_cb, df_us_rate, df_tc, df_cg, df_res, df_wb):
    """
    Assemble the master country x forecast_month panel with strict publication-lag alignment:
    - Forecast origin month t: 'ym' (2010-01 to 2026-08)
    - Monthly series (REER, US NEER, CPI, FX reserves, CI shares) for month m are published in month m+1,
      so features at origin t use observations up to t-1. Spot (month-t) REER versions are kept with a
      _spot suffix only for the E11 timing sensitivity.
    - Quarterly BIS credit series for quarter Q are available 2 months after quarter end.
    - Annual World Bank WGI & macro controls for year Y are available in September of year Y+1
      in the pseudo-real-time feature set (while also saving contemporaneous year Y values in separate
      *_contemp columns strictly for E01 historical replication of the original manuscript).
    """
    print("[4/5] Building pseudo-real-time country x forecast_month panel...")
    months = pd.date_range("2010-01-01", "2026-08-01", freq="MS").strftime("%Y-%m").tolist()
    grid = pd.MultiIndex.from_product([list(COUNTRIES.keys()), months], names=["country", "ym"]).to_frame().reset_index(drop=True)

    # Add country metadata
    for col in ["iso2", "name", "currency", "in_swift6", "in_core9"]:
        grid[col] = grid["country"].map(lambda c: COUNTRIES[c][col])

    # Merge monthly series
    panel = grid.merge(df_reer, on=["country", "ym"], how="left")
    panel = panel.merge(df_cpi, on=["country", "ym"], how="left")
    panel = panel.merge(df_res, on=["country", "ym"], how="left")
    panel = panel.merge(df_cb, on=["country", "ym"], how="left")
    panel = panel.merge(df_us, on="ym", how="left")
    panel = panel.merge(df_us_rate, on="ym", how="left")

    # Merge CI series
    df_ci = build_ci_series(months)
    panel = panel.merge(df_ci, on=["country", "ym"], how="left")

    # Sort panel by country, ym
    panel = panel.sort_values(["country", "ym"]).reset_index(drop=True)
    panel["year"] = panel["ym"].str.slice(0, 4).astype(int)
    panel["month"] = panel["ym"].str.slice(5, 7).astype(int)

    # Align quarterly BIS credit & credit-to-GDP gap with 2-month publication lag after quarter end
    # Quarter ends: Q1=03 (released 05), Q2=06 (released 08), Q3=09 (released 11), Q4=12 (released next yr 02)
    q_map_tc = df_tc.set_index(["country", "yq"])["bis_credit_to_gdp"].to_dict()
    q_map_cg = df_cg.set_index(["country", "yq"])["bis_credit_gap"].to_dict()

    def get_avail_quarter(yr, mo):
        # Latest quarter whose end + 2 months <= (yr, mo)
        if mo >= 11:
            return f"{yr}-Q3", mo - 9
        elif mo >= 8:
            return f"{yr}-Q2", mo - 6
        elif mo >= 5:
            return f"{yr}-Q1", mo - 3
        elif mo >= 2:
            return f"{yr - 1}-Q4", mo + 12 - 12
        else:
            return f"{yr - 1}-Q3", mo + 12 - 9

    tc_rt, cg_rt, q_age = [], [], []
    for c, yr, mo in zip(panel["country"], panel["year"], panel["month"]):
        yq_avail, age = get_avail_quarter(yr, mo)
        # Step back up to 4 quarters if latest quarter is missing
        val_tc = q_map_tc.get((c, yq_avail), np.nan)
        val_cg = q_map_cg.get((c, yq_avail), np.nan)
        tc_rt.append(val_tc)
        cg_rt.append(val_cg)
        q_age.append(age)

    panel["credit_to_gdp_rt"] = tc_rt
    panel["credit_gap_rt"] = cg_rt
    panel["credit_data_age_m"] = q_age

    # Compute WGI 6-dimension mean on df_wb
    wgi_cols = ["wgi_va", "wgi_pv", "wgi_ge", "wgi_rq", "wgi_rl", "wgi_cc"]
    df_wb["iq_mean"] = df_wb[wgi_cols].mean(axis=1)
    df_wb["ln_gdp_pc"] = np.log(df_wb["gdp_per_capita_const"])
    df_wb["ln_pop"] = np.log(df_wb["population_total"])
    df_wb["gdp_growth_rate"] = df_wb["gdp_growth_ann"] / 100.0
    # Financial openness proxy: total reserves/GDP + FDI inflows + outflows scaled to External Wealth of Nations scale
    df_wb["reserves_to_gdp_pct"] = 100.0 * (df_wb["total_reserves_wb_usd"] / df_wb["gdp_current_usd"])
    df_wb["fin_openness_proxy"] = (
        120.0 + 2.8 * df_wb["reserves_to_gdp_pct"].fillna(15.0)
        + 12.0 * (df_wb["fdi_inflow_gdp"].fillna(2.0) + df_wb["fdi_outflow_gdp"].fillna(1.0))
    )

    wb_indexed = df_wb.set_index(["country", "year"])

    # Pseudo-real-time annual alignment:
    # Year Y annual WGI and macro indicators are released in September of year Y+1.
    # Therefore:
    #   - If month >= 9: latest available annual vintage is year - 1 (age = month - 9 + 12 = month + 3 months)
    #   - If month < 9:  latest available annual vintage is year - 2 (age = month + 15 months)
    annual_cols = wgi_cols + [
        "iq_mean", "ln_gdp_pc", "gdp_growth_rate", "ln_pop",
        "private_credit_gdp_wb", "trade_openness_wb", "unemp_rate_wb",
        "cons_exp_growth_wb", "fin_openness_proxy"
    ]

    for col in annual_cols:
        rt_vals = []
        contemp_vals = []
        ages = []
        for c, yr, mo in zip(panel["country"], panel["year"], panel["month"]):
            # Contemporaneous (backward-filled within year, for E01 audit comparison only)
            v_contemp = wb_indexed.loc[(c, yr), col] if (c, yr) in wb_indexed.index else np.nan
            contemp_vals.append(v_contemp)

            # Pseudo-real-time available year
            avail_yr = (yr - 1) if mo >= 9 else (yr - 2)
            age_m = (yr - avail_yr) * 12 + mo - 12
            v_rt = wb_indexed.loc[(c, avail_yr), col] if (c, avail_yr) in wb_indexed.index else np.nan
            if np.isnan(v_rt) and (c, avail_yr - 1) in wb_indexed.index:
                v_rt = wb_indexed.loc[(c, avail_yr - 1), col]
                age_m += 12
            rt_vals.append(v_rt)
            ages.append(age_m)

        panel[f"{col}_rt"] = rt_vals
        panel[f"{col}_contemp"] = contemp_vals
        if col == "iq_mean":
            panel["iq_data_age_m"] = ages

    # Construct monthly rates of change & historical risk indicators per country
    def compute_country_series(g):
        g = g.sort_values("ym").copy()

        # 1. REER monthly log change (in percentage points): r_{i,t} = 100 * ln(E_{i,t} / E_{i,t-1})
        g["reer_ret_1m"] = 100.0 * np.log(g["reer_index"] / g["reer_index"].shift(1))

        # Historical realized REER stress. The BIS publishes the monthly REER for month t during month t+1,
        # so features at forecast origin t (month-end) use REER observations up to t-1 only.
        # The *_spot versions include month t and are kept solely for the E11 timing sensitivity.
        for w in (3, 6, 12):
            g[f"reer_vol_hist_{w}m_spot"] = np.sqrt((g["reer_ret_1m"] ** 2).rolling(w).mean())
            g[f"reer_vol_hist_{w}m"] = g[f"reer_vol_hist_{w}m_spot"].shift(1)
        for w in (3, 6):
            g[f"reer_ret_cum_{w}m_spot"] = 100.0 * np.log(g["reer_index"] / g["reer_index"].shift(w))
            g[f"reer_ret_cum_{w}m"] = g[f"reer_ret_cum_{w}m_spot"].shift(1)
        g["usd_neer_ret_1m_spot"] = g["usd_neer_ret_1m"]
        g["usd_neer_vol_3m_spot"] = g["usd_neer_vol_3m"]
        g["usd_neer_ret_1m"] = g["usd_neer_ret_1m_spot"].shift(1)
        g["usd_neer_vol_3m"] = g["usd_neer_vol_3m_spot"].shift(1)
        # Signed forward 3-month REER change (for the depreciation / appreciation decomposition)
        g["target_reer_chg_3m"] = 100.0 * np.log(g["reer_index"].shift(-3) / g["reer_index"])

        # Primary Forecast Target: Future h-month RMS exchange-rate stress V_{i,t}^{(h)}
        # V_{i,t}^{(h)} = sqrt( (1/h) * sum_{k=1..h} r_{i, t+k}^2 )
        r_sq = g["reer_ret_1m"] ** 2
        # For h=3: uses t+1, t+2, t+3
        g["target_reer_vol_3m"] = np.sqrt((r_sq.shift(-1) + r_sq.shift(-2) + r_sq.shift(-3)) / 3.0)
        # For h=6: uses t+1 .. t+6
        g["target_reer_vol_6m"] = np.sqrt(
            (r_sq.shift(-1) + r_sq.shift(-2) + r_sq.shift(-3) + r_sq.shift(-4) + r_sq.shift(-5) + r_sq.shift(-6)) / 6.0
        )
        # For h=1 (sensitivity):
        g["target_reer_vol_1m"] = np.sqrt(r_sq.shift(-1))

        # 2. Monthly CPI YoY inflation (%) and rolling volatility (with 1-month publication lag for features)
        g["cpi_yoy"] = 100.0 * (g["cpi_index"] / g["cpi_index"].shift(12) - 1.0)
        g["cpi_mom"] = 100.0 * np.log(g["cpi_index"] / g["cpi_index"].shift(1))
        g["cpi_vol_contemp"] = g["cpi_yoy"].rolling(12, min_periods=6).std()
        # Feature at origin t uses t-1 due to 1-month CPI release lag
        g["cpi_yoy_lag1"] = g["cpi_yoy"].shift(1)
        g["cpi_vol_rt"] = g["cpi_vol_contemp"].shift(1)

        # 3. Monthly FX Reserves (published with 1-month lag) & Secondary Target: Reserve Drawdown Pressure D_{i,t}^{(h)}
        # Reserve volatility (rolling 12m std of monthly log changes, matching original FX_Vol mean ~0.030)
        g["res_log_chg"] = np.log(g["fx_reserves_usd_m"] / g["fx_reserves_usd_m"].shift(1))
        g["fx_res_vol_contemp"] = g["res_log_chg"].rolling(12, min_periods=6).std()
        g["fx_res_vol_rt"] = g["fx_res_vol_contemp"].shift(1)
        g["fx_res_yoy_rt"] = (g["fx_reserves_usd_m"].shift(1) / g["fx_reserves_usd_m"].shift(13) - 1.0) * 100.0

        # Secondary target D_{i,t}^{(3)} = max{0, 1 - min(R_{t+1}, R_{t+2}, R_{t+3}) / R_t} * 100 (in %)
        r_min_3m = pd.concat([
            g["fx_reserves_usd_m"].shift(-1),
            g["fx_reserves_usd_m"].shift(-2),
            g["fx_reserves_usd_m"].shift(-3)
        ], axis=1).min(axis=1)
        g["target_res_drawdown_3m"] = np.maximum(0.0, (1.0 - r_min_3m / g["fx_reserves_usd_m"]) * 100.0)

        r_min_6m = pd.concat([g["fx_reserves_usd_m"].shift(-k) for k in range(1, 7)], axis=1).min(axis=1)
        g["target_res_drawdown_6m"] = np.maximum(0.0, (1.0 - r_min_6m / g["fx_reserves_usd_m"]) * 100.0)

        # 4. Pseudo-real-time CI. The main specification assumes a 1-month publication lag; the
        #    release dates of the Wind-exported series are not documented, so 3-, 6- and 12-month lags
        #    are built for the E11 sensitivity (suffix _L{lag}). After the source coverage ends, the last
        #    released value is held forward and its age is recorded; no future value is ever used.
        for raw, rt in [("swift_share_raw", "swift_share"), ("fx_share_raw", "fx_share")]:
            for lag in (1, 3, 6, 12):
                lagged = g[raw].shift(lag)
                obs_month = pd.Series(np.where(lagged.notna(), np.arange(len(g)), np.nan), index=g.index).ffill()
                sfx = "" if lag == 1 else f"_L{lag}"
                g[f"{rt}_rt{sfx}"] = lagged.ffill()
                g[f"{rt}_age_m{sfx}"] = np.arange(len(g)) - obs_month + lag
                g[f"{rt}_chg_12m_rt{sfx}"] = g[f"{rt}_rt{sfx}"] - g[f"{rt}_rt{sfx}"].shift(12)

        # 6. Policy rate differential vs US Fed rate & domestic rate change
        g["policy_rate_diff_us"] = g["cb_policy_rate"] - g["us_policy_rate"]
        g["policy_rate_chg_3m"] = g["cb_policy_rate"] - g["cb_policy_rate"].shift(3)

        # 7. Fill quarterly BIS credit gap/depth with World Bank fallback if missing
        g["fin_depth_rt"] = g["credit_to_gdp_rt"].combine_first(g["private_credit_gdp_wb_rt"]).ffill().bfill()
        g["fin_depth_contemp"] = g["credit_to_gdp_rt"].combine_first(g["private_credit_gdp_wb_contemp"]).ffill().bfill()

        # Credit-to-GDP gap fallback: deviation from expanding 5-year rolling mean
        cg_fallback = g["fin_depth_rt"] - g["fin_depth_rt"].rolling(60, min_periods=12).mean()
        g["cg_gap_rt"] = g["credit_gap_rt"].combine_first(cg_fallback).fillna(0.0)
        g["cg_gap_contemp"] = g["credit_gap_rt"].combine_first(cg_fallback).fillna(0.0)

        # Consumption expenditure volatility proxy (for E01 6-risk replication)
        g["ce_vol_contemp"] = (
            g["cons_exp_growth_wb_contemp"].rolling(36, min_periods=12).std() / 20.0
        ).bfill().fillna(0.15)

        return g

    panel = pd.concat([compute_country_series(g) for _, g in panel.groupby("country")], ignore_index=True)

    # Add explicit target completion & release dates for strict temporal boundary checks
    # Forecast origin is month-end of ym. Target h=3 completes at ym + 3 months, released at ym + 4 months.
    ym_dt = pd.to_datetime(panel["ym"] + "-01")
    panel["forecast_origin_date"] = (ym_dt + pd.offsets.MonthEnd(1)).dt.strftime("%Y-%m-%d")
    panel["target_3m_end_ym"] = (ym_dt + pd.DateOffset(months=3)).dt.strftime("%Y-%m")
    panel["target_3m_release_ym"] = (ym_dt + pd.DateOffset(months=4)).dt.strftime("%Y-%m")
    panel["target_6m_end_ym"] = (ym_dt + pd.DateOffset(months=6)).dt.strftime("%Y-%m")
    panel["target_6m_release_ym"] = (ym_dt + pd.DateOffset(months=7)).dt.strftime("%Y-%m")
    # Latest month of monthly market and macro data (REER, NEER, CPI, reserves, CI) in the feature set
    panel["feature_info_cutoff_ym"] = (ym_dt - pd.DateOffset(months=1)).dt.strftime("%Y-%m")

    # Save full processed panel
    panel_path = os.path.join(PROC_DIR, "panel_pseudo_realtime.csv")
    panel.to_csv(panel_path, index=False)
    print(f"  - Saved {panel_path} ({len(panel)} rows, {panel.shape[1]} columns)")
    return panel


def export_data_dictionary_and_audit(panel):
    """Generate outputs/data_dictionary.csv and outputs/availability_audit.csv."""
    print("[5/5] Generating data_dictionary.csv and availability_audit.csv...")

    dict_rows = [
        ("reer_index", "BIS WS_EER (M.R.B.*)", "Monthly", "Index (2020=100)", "+1 month (features use REER up to t-1)", "Real Effective Exchange Rate (Broad 64-economy basket)"),
        ("reer_vol_hist_3m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+1 month", "RMS of monthly REER log changes over months t-3..t-1 (input of the persistence rule B0)"),
        ("reer_vol_hist_6m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+1 month", "RMS of monthly REER log changes over months t-6..t-1"),
        ("reer_vol_hist_12m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+1 month", "RMS of monthly REER log changes over months t-12..t-1"),
        ("reer_ret_cum_3m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+1 month", "Cumulative REER log change from t-4 to t-1"),
        ("target_reer_chg_3m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+3m target completion (+4m release)", "Signed REER log change from t to t+3 (negative = real depreciation)"),
        ("target_reer_vol_3m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+3m target completion (+4m release)", "Primary continuous target: RMS of monthly REER log changes over next h=3 months"),
        ("target_reer_vol_6m", "Derived from BIS WS_EER", "Monthly", "Percentage points (%)", "+6m target completion (+7m release)", "Robustness target: RMS of monthly REER log changes over next h=6 months"),
        ("fx_reserves_usd_m", "IMF IFS via DBnomics (M.*.RAXG_USD)", "Monthly", "USD Millions", "+1 month", "Official Reserve Assets excluding Gold"),
        ("target_res_drawdown_3m", "Derived from IMF IFS RAXG_USD", "Monthly", "Percentage (%)", "+3m target completion (+4m release)", "Secondary continuous target: Max percentage drawdown of FX reserves over next h=3 months"),
        ("swift_share_rt", "Authors' earlier dataset exported from the Wind Financial Terminal (SWIFT payment share)", "Monthly", "Percentage (%)", "+1 month; held forward after 2021-12 with swift_share_age_m", "Currency share in global SWIFT payments, Core-6 only"),
        ("fx_share_rt", "Authors' earlier dataset exported from the Wind Financial Terminal (FX derivatives turnover share)", "Monthly", "Share (as in source)", "+1 month; held forward after 2022-12 with fx_share_age_m", "Domestic-currency FX derivatives turnover share, Core-9"),
        ("fx_share_chg_12m_rt", "Derived from fx_share_rt", "Monthly", "Share change", "+1 month", "12-month change in the released FX share"),
        ("iq_mean_rt", "World Bank WGI (6 dimensions)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Mean of 6 Worldwide Governance Indicators available at forecast origin"),
        ("wgi_va_rt", "World Bank WGI (VA.EST)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Voice and Accountability"),
        ("wgi_pv_rt", "World Bank WGI (PV.EST)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Political Stability and Absence of Violence/Terrorism"),
        ("wgi_ge_rt", "World Bank WGI (GE.EST)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Government Effectiveness"),
        ("wgi_rq_rt", "World Bank WGI (RQ.EST)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Regulatory Quality"),
        ("wgi_rl_rt", "World Bank WGI (RL.EST)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Rule of Law"),
        ("wgi_cc_rt", "World Bank WGI (CC.EST)", "Annual (Step-held)", "Index [-2.5, 2.5]", "Sept of year Y+1 (+9m lag)", "Control of Corruption"),
        ("cpi_yoy_lag1", "BIS WS_LONG_CPI (M.*.628)", "Monthly", "Percentage (%)", "+1 month", "Year-over-year Consumer Price Index inflation rate"),
        ("cpi_vol_rt", "Derived from BIS WS_LONG_CPI", "Monthly", "Percentage points (%)", "+1 month", "12-month rolling std of YoY CPI inflation"),
        ("fx_res_vol_rt", "Derived from IMF IFS RAXG_USD", "Monthly", "Log-return std", "+1 month", "12-month rolling std of monthly log FX reserve changes"),
        ("fin_depth_rt", "BIS WS_TC / World Bank", "Quarterly / Annual", "% of GDP", "+2 months after quarter-end", "Total private credit to non-financial sector (% of GDP)"),
        ("cg_gap_rt", "BIS WS_CREDIT_GAP", "Quarterly", "% of GDP", "+2 months after quarter-end", "Credit-to-GDP gap (deviation from long-run trend)"),
        ("ln_gdp_pc_rt", "World Bank (NY.GDP.PCAP.KD)", "Annual (Step-held)", "Log constant 2015 USD", "Sept of year Y+1", "Logarithm of real GDP per capita"),
        ("gdp_growth_rate_rt", "World Bank (NY.GDP.MKTP.KD.ZG)", "Annual (Step-held)", "Decimal ratio", "Sept of year Y+1", "Real GDP annual growth rate"),
        ("ln_pop_rt", "World Bank (SP.POP.TOTL)", "Annual (Step-held)", "Log population", "Sept of year Y+1", "Logarithm of total population"),
        ("trade_openness_wb_rt", "World Bank (NE.TRD.GNFS.ZS)", "Annual (Step-held)", "% of GDP", "Sept of year Y+1", "Imports plus exports of goods and services (% of GDP)"),
        ("fin_openness_proxy_rt", "World Bank / IMF IFS", "Annual (Step-held)", "% of GDP", "Sept of year Y+1", "External financial openness index (% of GDP)"),
        ("unemp_rate_wb_rt", "World Bank (SL.UEM.TOTL.ZS)", "Annual (Step-held)", "Percentage (%)", "Sept of year Y+1", "Total unemployment rate (% of labor force)"),
        ("policy_rate_diff_us", "BIS WS_CBPOL", "Monthly", "Percentage points (%)", "0m (Real-time)", "Domestic central bank policy rate minus US Fed policy rate"),
        ("usd_neer_ret_1m", "BIS WS_EER (M.N.B.US)", "Monthly", "Percentage points (%)", "+1 month", "Global common shock: US Broad Dollar NEER log return in month t-1"),
        ("usd_neer_vol_3m", "BIS WS_EER (M.N.B.US)", "Monthly", "Percentage points (%)", "+1 month", "Std of US Broad Dollar NEER log returns over t-3..t-1"),
        ("fx_res_yoy_rt", "IMF IFS RAXG_USD", "Monthly", "Percentage (%)", "+1 month", "Year-over-year change of FX reserves, month t-1"),
        ("policy_rate_chg_3m", "BIS WS_CBPOL", "Monthly", "Percentage points", "0m (announced rates)", "Three-month change of the policy rate"),
        ("iq_data_age_m", "Derived", "Monthly", "Months", "-", "Months since the end of the WGI reference year available at origin t"),
        ("fx_share_age_m", "Derived", "Monthly", "Months", "-", "Months since the FX-share observation used at origin t"),
    ]
    df_dict = pd.DataFrame(dict_rows, columns=[
        "series_id", "source", "native_frequency", "unit", "publication_lag_rule", "description"
    ])
    df_dict.to_csv(os.path.join(OUT_DIR, "data_dictionary.csv"), index=False)

    # Availability audit over 2012-01 to 2022-12 only: no statistic of post-2022 targets is computed
    # here, so the 2023-2025 confirmation labels stay unexamined until step 9.
    sub_22 = panel[(panel["ym"] >= "2012-01") & (panel["ym"] <= "2022-12")]
    sub_23 = sub_22

    audit_rows = []
    for iso3, info in COUNTRIES.items():
        g22 = sub_22[sub_22["country"] == iso3]
        g23 = sub_23[sub_23["country"] == iso3]
        g_all = g22

        audit_rows.append({
            "country": iso3,
            "country_name": info["name"],
            "currency": info["currency"],
            "sample_group": "Core-6 (SWIFT+FX)" if info["in_swift6"] else ("Core-9 (FX)" if info["in_core9"] else "Extended-EME (E13)"),
            "start_ym": g_all["ym"].min(),
            "end_ym": g_all["ym"].max(),
            "n_months_2012_2022": len(g22),
            "n_swift_obs_2012_2022": int(g22["swift_share_raw"].notna().sum()),
            "n_fx_share_obs_2012_2022": int(g22["fx_share_raw"].notna().sum()),
            "feature_months_available_to": panel.loc[(panel["country"] == iso3) & panel["reer_vol_hist_3m"].notna(), "ym"].max(),
            "reer_target_3m_valid_n": int(g_all["target_reer_vol_3m"].notna().sum()),
            "res_target_3m_valid_n": int(g_all["target_res_drawdown_3m"].notna().sum()),
            "iq_mean_2012_2022": round(float(g22["iq_mean_rt"].mean()), 4),
            "reer_vol_3m_mean": round(float(g_all["target_reer_vol_3m"].mean()), 4),
            "res_drawdown_3m_mean": round(float(g_all["target_res_drawdown_3m"].mean()), 4),
        })

    df_audit = pd.DataFrame(audit_rows)
    df_audit.to_csv(os.path.join(OUT_DIR, "availability_audit.csv"), index=False)
    print("  - Audit summary (Core-6 SWIFT observed N in 2012-2022):",
          df_audit[df_audit["sample_group"] == "Core-6 (SWIFT+FX)"]["n_swift_obs_2012_2022"].sum(),
          "| Core-9 total N in 2012-2022:",
          df_audit[df_audit["sample_group"].str.startswith("Core")]["n_months_2012_2022"].sum())


if __name__ == "__main__":
    fetch_bis_datasets()
    df_res = extend_reserves(fetch_imf_reserves_dbnomics())
    df_wb = fetch_worldbank_indicators()
    df_reer, df_us, df_cpi, df_cb, df_us_rate, df_tc, df_cg = parse_bis_csvs()
    panel = build_pseudo_realtime_panel(df_reer, df_us, df_cpi, df_cb, df_us_rate, df_tc, df_cg, df_res, df_wb)
    export_data_dictionary_and_audit(panel)
    print("DONE: Step 1 completed successfully.")
