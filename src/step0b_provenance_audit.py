#!/usr/bin/env python3
"""
Step 0b: Provenance audit of the original data exports
=======================================================
Input: data/raw/original_exports/*.xlsx, the Wind / BIS / SAFE exports from which the authors compiled the two
regression datasets of the working paper (data/raw/historylab). The exports are licensed and not redistributed;
SHA256SUMS.txt records their checksums. Export dates come from the workbook metadata (docProps/core.xml) because
file-system timestamps change on copying.

Outputs (outputs/tables):
  tableS18_export_inventory.csv   file, source, indicators, frequency, coverage, workbook dates, SHA-256
  tableS18b_column_checks.csv     reconstruction of regression-dataset columns from the exports, with match rates
"""

import glob
import hashlib
import os
import re
import warnings
import zipfile

import numpy as np
import pandas as pd

from common import BASE_DIR, TAB_DIR

warnings.filterwarnings("ignore")
EXP = os.path.join(BASE_DIR, "data", "raw", "original_exports")
HIS = os.path.join(BASE_DIR, "data", "raw", "historylab")
DATASETS = {"Panel A": "reg_swiftnew_20230613.xlsx", "Panel B": "reg_fxshare_20230613.xlsx"}
RTOL = 1e-6

LABEL = {
    "全球外汇衍生品交易份额_货币_月度频率.xlsx": "FX-derivatives turnover by currency",
    "国际债券和票据_未偿余额和发行量.xlsx": "International bonds and notes: outstanding and announced issuance",
    "外汇储备总额_币种.xlsx": "Allocated official FX reserves by currency (COFER)",
    "全球对外信贷其它货币份额.xlsx": "Cross-border credit by currency denomination",
    "境外贷款人民币.xlsx": "Overseas RMB loans of Chinese financial institutions",
    "直接投资结算.xlsx": "RMB direct-investment settlement and OFDI stock",
    "中国国际投资头寸表.xlsx": "China international investment position",
    "中国季度GDP.xlsx": "China quarterly GDP (USD)",
    "货币与国家.xlsx": "Currency-country mapping with emerging flag and income group",
}


def core_dates(path):
    core = zipfile.ZipFile(path).read("docProps/core.xml").decode()
    get = lambda k: (re.search(rf"<{k}[^>]*>([^<]*)<", core) or [None, ""])[1][:10]
    return get("dcterms:created"), get("dcterms:modified")


def source_of(path, sheets):
    cells = " ".join(str(v) for df in sheets.values() for v in df.astype(str).values.ravel())
    if any(s.startswith("statx-") for s in sheets):
        return "BIS Statistics Explorer"
    if "数据来源：Wind" in cells:
        return "Wind"
    if "国际投资头寸表" in cells:
        return "SAFE (published table)"
    if "Currency denomination" in cells:
        return "BIS (reformatted export)"
    if "指标名称" in cells:
        return "Wind (indicator-name layout)"
    if "GDP(" in cells:
        return "Wind (reformatted)"
    return "authors' mapping"


def dates_in(values):
    d = pd.to_datetime(pd.Series([v for v in values if not isinstance(v, (int, float)) or pd.isna(v)]), errors="coerce", dayfirst=True).dropna()
    return d[(d.dt.year > 1970) & (d.dt.year < 2030)]


def inventory():
    rows = []
    for path in sorted(glob.glob(os.path.join(EXP, "*.xlsx"))):
        f = os.path.basename(path)
        sheets = pd.read_excel(path, sheet_name=None, header=None)
        created, modified = core_dates(path)
        first = next(iter(sheets.values()))
        d = pd.concat([dates_in(first.iloc[:, 0].tolist()), dates_in(first.iloc[0, :].tolist())])
        names = [str(v) for v in first.iloc[0, 1:].tolist() if ":" in str(v)] or [str(v) for v in first.iloc[1:, 0].tolist() if ":" in str(v)]
        steps = d.sort_values().diff().dt.days.dropna()
        freq = "" if steps.empty else ("monthly" if steps.median() < 40 else "quarterly" if steps.median() < 100 else "annual")
        if first.shape[1] == 2 and (first.iloc[1:, 1] == 0).mean() > 0.5:
            freq = "quarterly (zeros in other months)"
        if d.empty:
            yrs = [int(y) for df in sheets.values() for y in re.findall(r"(\d{4})年(?:\d+月)?末", " ".join(map(str, df.values.ravel())))]
            if yrs:
                d = pd.to_datetime(pd.Series([f"{min(yrs)}-12-31", f"{max(yrs)}-12-31"]))
                freq = "annual and quarterly (year-end positions)"
        rows.append(dict(file=f, content=LABEL.get(f, ""), source=source_of(path, sheets), sheets=len(sheets),
                         n_series=max(len(names), first.shape[0] - 1 if not names else len(names)),
                         example_indicator=names[0] if names else "", frequency=freq,
                         coverage_from=d.min().strftime("%Y-%m") if len(d) else "", coverage_to=d.max().strftime("%Y-%m") if len(d) else "",
                         workbook_created=created, workbook_modified=modified,
                         sha256=hashlib.sha256(open(path, "rb").read()).hexdigest()))
    return pd.DataFrame(rows)


def ym(x):
    return pd.to_datetime(pd.Series(x), errors="coerce").dt.strftime("%Y-%m").values


def bis_wide(path, key="货币"):
    x = pd.read_excel(path, header=0).set_index(key)
    x = x[[c for c in x.columns if c not in ("Issue currency", "Country", "Currency denomination")]]
    x.columns = [pd.to_datetime(c, format="%d/%m/%Y" if isinstance(c, str) else None).strftime("%Y-%m") for c in x.columns]
    return x.astype(float)


def wind_long(path):
    x = pd.read_excel(path, header=0)
    x["ym"] = ym(x["指标名称"])
    return x.dropna(subset=["ym"]).set_index("ym").drop(columns=["指标名称"]).astype(float)


def compare(a, b):
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    return len(j), (float(np.isclose(j.a, j.b, rtol=RTOL, atol=1e-12).mean()) if len(j) else np.nan)


def interp_ok(s):
    """Share of non-quarter-end months equal to linear interpolation between adjacent quarter-ends."""
    s = s.dropna()
    q = s[[m[-2:] in ("03", "06", "09", "12") for m in s.index]]
    lin = pd.Series(np.interp(np.arange(len(s)), [s.index.get_loc(i) for i in q.index], q.values), index=s.index)
    inner = [i for i in s.index if i not in q.index and q.index.min() < i < q.index.max()]
    return len(inner), (float(np.isclose(s[inner], lin[inner], rtol=RTOL).mean()) if inner else np.nan)


def column_checks():
    fx = bis_wide(os.path.join(EXP, "全球外汇衍生品交易份额_货币_月度频率.xlsx"))
    credit = bis_wide(os.path.join(EXP, "全球对外信贷其它货币份额.xlsx"))
    bonds = wind_long(os.path.join(EXP, "国际债券和票据_未偿余额和发行量.xlsx"))
    res = wind_long(os.path.join(EXP, "外汇储备总额_币种.xlsx"))
    loans = wind_long(os.path.join(EXP, "境外贷款人民币.xlsx")).iloc[:, 0]
    cmap = pd.read_excel(os.path.join(EXP, "货币与国家.xlsx")).set_index("货币")
    rows = []
    for panel, fname in DATASETS.items():
        d = pd.read_excel(os.path.join(HIS, fname))
        d["ym"] = ym(d["date"])
        # CI of Panel B (also shipped in Panel A): currency turnover / total turnover of all currencies
        n_tot = n_ok = 0
        for cur, g in d.groupby("货币"):
            n, s = compare(g.set_index("ym")["本国货币外汇衍生品交易额"], fx.loc[cur] / fx.loc["全部"])
            n_tot, n_ok = n_tot + n, n_ok + n * s
        rows.append(dict(dataset=panel, column="本国货币外汇衍生品交易额", role="CI, Panel B" if panel == "Panel B" else "not used",
                         source_file="全球外汇衍生品交易份额_货币_月度频率.xlsx", construction="currency turnover / TO1 total, same month",
                         countries=d["货币"].nunique(), n_compared=n_tot, share_matched=n_ok / n_tot, interpolation=""))
        cn = d[d["货币"] == "人民币"].set_index("ym")
        for col, src, series, cons in [
            ("未偿余额", "国际债券和票据_未偿余额和发行量.xlsx", bonds["国际债券和票据:未偿余额:发行货币:人民币"], "RMB outstanding, quarter-end"),
            ("公布发行额", "国际债券和票据_未偿余额和发行量.xlsx", bonds["国际债券和票据:公布发行额:发行货币:人民币"], "RMB announced issuance, quarter-end"),
            ("外汇储备总额", "外汇储备总额_币种.xlsx", res["外汇储备总额:全球:币种确认官方储备:人民币"] / res["外汇储备总额:全球:币种确认官方储备:全部"], "RMB / all allocated reserves, quarter-end"),
        ]:
            n, s = compare(cn[col], series)
            ni, si = interp_ok(cn[col])
            rows.append(dict(dataset=panel, column=col, role="not used", source_file=src, construction=cons, countries=1,
                             n_compared=n, share_matched=s, interpolation=f"linear interpolation within quarters ({int(round(si * ni))} of {ni} other months)" if ni else ""))
        total = credit.loc["全部"].reindex(sorted(set(credit.columns) | set(loans.index))).bfill()
        n, s = compare(cn["对外贷款"], loans / total)
        rows.append(dict(dataset=panel, column="对外贷款", role="not used", source_file="境外贷款人民币.xlsx; 全球对外信贷其它货币份额.xlsx",
                         construction="monthly overseas RMB loans (CNY 100 m) / all-currency cross-border credit (USD m); no unit conversion",
                         countries=1, n_compared=n, share_matched=s, interpolation="quarterly denominator backward-filled to months"))
        m = d.drop_duplicates("货币").set_index("货币")
        ok = [(m.loc[c, "新兴国家"] == cmap.loc[c, "新兴国家"]) and (m.loc[c, "收入组别"] == cmap.loc[c, "收入组别"]) for c in m.index]
        rows.append(dict(dataset=panel, column="新兴国家 / 收入组别", role="not used", source_file="货币与国家.xlsx", construction="currency-country lookup",
                         countries=len(m), n_compared=len(m), share_matched=float(np.mean(ok)), interpolation=""))
    return pd.DataFrame(rows)


def main():
    if not glob.glob(os.path.join(EXP, "*.xlsx")):
        print("Licensed exports not present; keeping the archived tableS18 files.")
        return
    inv = inventory()
    chk = column_checks()
    inv.to_csv(os.path.join(TAB_DIR, "tableS18_export_inventory.csv"), index=False)
    chk.to_csv(os.path.join(TAB_DIR, "tableS18b_column_checks.csv"), index=False)
    print(inv.drop(columns="sha256").to_string())
    print(chk.to_string())
    ci = chk[chk.column == "本国货币外汇衍生品交易额"]
    assert (ci.share_matched == 1.0).all(), "CI is not reproduced from the BIS export"


if __name__ == "__main__":
    main()
