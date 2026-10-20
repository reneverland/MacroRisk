#!/usr/bin/env python3
"""
Step 7: build the ESWA submission files from the audited numbers.
Every number in the text comes from outputs/manuscript_numbers.json (written by step 8) and every table from
outputs/tables; the build stops unless outputs/AUDIT_STATUS reads PASS.
Outputs (manuscript/): ESWA_Manuscript_anonymized.tex/.md/.docx/_preview.pdf, Supplementary_Material.md/.docx,
Title_Page.docx, Highlights.docx/.txt, figures/Fig*.pdf|png.
"""

import os
import re
import json
import shutil
import subprocess
import pandas as pd
import pypandoc

from common import fmt_num

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTD = os.path.join(BASE_DIR, "outputs")
TAB = os.path.join(OUTD, "tables")
FIG = os.path.join(OUTD, "figures")
OUT = os.path.join(BASE_DIR, "manuscript")

status = open(os.path.join(OUTD, "AUDIT_STATUS")).read().split("\n")[0].strip()
if status != "PASS":
    raise SystemExit("Consistency audit did not pass; run step8_consistency_audit.py and fix the reported issues first.")
V = json.load(open(os.path.join(OUTD, "manuscript_numbers.json")))


def rd(name):
    return pd.read_csv(os.path.join(TAB, name))


def fill(t):
    def sub(m):
        if re.search(r"(\\[A-Za-z]+|[_^])$", t[:m.start()]):
            return m.group(0)
        if m.group(1) not in V:
            raise KeyError(f"number '{m.group(1)}' missing from manuscript_numbers.json")
        return str(V[m.group(1)])
    return re.sub(r"\{([A-Za-z0-9_]+)\}", sub, t)


# ------------------------------------------------------------------------------------------
# Front matter
# ------------------------------------------------------------------------------------------
TITLE = "Do institutional thresholds improve exchange-rate stress early warning? An auditable replication-to-prediction evaluation"

ABSTRACT = fill(
    "Institutional thresholds estimated in panel regressions may motivate early-warning features without establishing their predictive or "
    "decision value. We present an auditable workflow linking internal replication, release-lag-adjusted prediction and decision-cost "
    "simulation. Across panels of six and nine emerging economies, a compatible calculation reproduces all {n_f_exact} reported threshold F "
    "statistics, while {n_lost15} of {n_sig1} nominally significant tests lose significance under 15% trimming. The forecasting evaluation over "
    "2017-2022 contains {n_pos_all} high-risk real-effective-exchange-rate windows. In the main FX-share comparisons, only one of 18 "
    "currency-internationalization or institutional-quality additions, institutional quality in the additive model, reaches a point-estimate "
    "gain of {sesoi} average precision (AP), with an interval that includes zero; {e21_n_not_excl_plus} paired intervals cannot exclude such a gain. Equivalence between the institution-conditioned interaction and the "
    "additive model is not established. In 2021-2022, country identity plus persistence achieves AP {c1_lock}, compared with {b0_lock} for "
    "persistence alone. Eight-month recalibration worsens Brier scores for all {n_models_cal} benchmark models. Simulated review benefits depend "
    "on reviewer errors, fees and the comparison policy. In an exploratory 2023-2025 rerun with corrected tuning, institutional quality lowers "
    "the additive model's expected cost, but its AP interval includes zero, and XGBoost shows no detected increment. The refitted fallback retains "
    "persistence throughout, while corrected XGBoost achieves higher AP in the core economies. The findings support explicit audits of "
    "information timing and decision assumptions; they do not establish real-time deployment performance or a general absence of "
    "institutional information.")

KEYWORDS = ["Early warning system", "Explainable boosting machine", "Panel threshold regression", "Replication",
            "Pseudo-real-time evaluation", "Selective prediction"]

HIGHLIGHTS = [
    "A reproducibility audit connects threshold evidence with stress prediction",
    "Only one of 18 CI or IQ additions reaches a 0.02 gain in average precision",
    "Model rankings change across periods, countries and stress definitions",
    "Simulated review gains depend on reviewer errors, fees and the comparison policy",
    "A refitted fallback keeps persistence and misses XGBoost gains in core economies",
]

# ------------------------------------------------------------------------------------------
# References (verified bibliographic records)
# ------------------------------------------------------------------------------------------
REFS = {
    "aman2024": ("Aman et al., 2024", "Aman, Z., Granville, B., Mallick, S. K., & Nemlioglu, I. (2024). Does greater financial openness promote external competitiveness in emerging markets? The role of institutional quality. International Journal of Finance & Economics, 29(1), 486-510. https://doi.org/10.1002/ijfe.2695"),
    "an2024": ("An et al., 2024", "An, J., Kim, H. S., & Park, B. (2024). Do China's policy measures for RMB internationalization foster currency co-movements? International Review of Economics & Finance, 91, 1033-1050. https://doi.org/10.1016/j.iref.2024.01.019"),
    "barthelemy2024": ("Barthélémy et al., 2024", "Barthélémy, S., Gautier, V., & Rondeau, F. (2024). Early warning system for currency crises using long short-term memory and gated recurrent unit neural networks. Journal of Forecasting, 43(5), 1235-1262. https://doi.org/10.1002/for.3069"),
    "beutel2019": ("Beutel et al., 2019", "Beutel, J., List, S., & von Schweinitz, G. (2019). Does machine learning help us predict banking crises? Journal of Financial Stability, 45, 100693. https://doi.org/10.1016/j.jfs.2019.100693"),
    "bluwstein2023": ("Bluwstein et al., 2023", "Bluwstein, K., Buckmann, M., Joseph, A., Kapadia, S., & Simsek, O. (2023). Credit growth, the yield curve and financial crisis prediction: Evidence from a machine learning approach. Journal of International Economics, 145, 103773. https://doi.org/10.1016/j.jinteco.2023.103773"),
    "breiman2001": ("Breiman, 2001", "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5-32."),
    "chen2016": ("Chen & Guestrin, 2016", "Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. In Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (pp. 785-794)."),
    "chen2024": ("Chen et al., 2024", "Chen, S., Huang, Y., & Ge, L. (2024). An early warning system for financial crises: A temporal convolutional network approach. Technological and Economic Development of Economy, 30(3), 688-711. https://doi.org/10.3846/tede.2024.20555"),
    "chinn2006": ("Chinn & Ito, 2006", "Chinn, M. D., & Ito, H. (2006). What matters for financial development? Capital controls, institutions, and interactions. Journal of Development Economics, 81(1), 163-192."),
    "chow1970": ("Chow, 1970", "Chow, C. K. (1970). On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory, 16(1), 41-46."),
    "croushore2001": ("Croushore & Stark, 2001", "Croushore, D., & Stark, T. (2001). A real-time data set for macroeconomists. Journal of Econometrics, 105(1), 111-130."),
    "davison1997": ("Davison & Hinkley, 1997", "Davison, A. C., & Hinkley, D. V. (1997). Bootstrap methods and their application. Cambridge University Press."),
    "eichengreen2018": ("Eichengreen et al., 2018", "Eichengreen, B., Mehl, A., & Chitu, L. (2018). How global currencies work: Past, present, and future. Princeton University Press."),
    "elkan2001": ("Elkan, 2001", "Elkan, C. (2001). The foundations of cost-sensitive learning. In Proceedings of the 17th International Joint Conference on Artificial Intelligence (pp. 973-978)."),
    "frankel1996": ("Frankel & Rose, 1996", "Frankel, J. A., & Rose, A. K. (1996). Currency crashes in emerging markets: An empirical treatment. Journal of International Economics, 41(3-4), 351-366."),
    "gama2014": ("Gama et al., 2014", "Gama, J., Zliobaite, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014). A survey on concept drift adaptation. ACM Computing Surveys, 46(4), 44."),
    "geifman2017": ("Geifman & El-Yaniv, 2017", "Geifman, Y., & El-Yaniv, R. (2017). Selective classification for deep neural networks. In Advances in Neural Information Processing Systems 30."),
    "hansen1999": ("Hansen, 1999", "Hansen, B. E. (1999). Threshold effects in non-dynamic panels: Estimation, testing, and inference. Journal of Econometrics, 93(2), 345-368."),
    "holopainen2017": ("Holopainen & Sarlin, 2017", "Holopainen, M., & Sarlin, P. (2017). Toward robust early-warning models: A horse race, ensembles and model uncertainty. Quantitative Finance, 17(12), 1933-1963."),
    "kaminsky1998": ("Kaminsky et al., 1998", "Kaminsky, G., Lizondo, S., & Reinhart, C. M. (1998). Leading indicators of currency crises. IMF Staff Papers, 45(1), 1-48."),
    "kaufmann2011": ("Kaufmann et al., 2011", "Kaufmann, D., Kraay, A., & Mastruzzi, M. (2011). The Worldwide Governance Indicators: Methodology and analytical issues. Hague Journal on the Rule of Law, 3(2), 220-246."),
    "kunsch1989": ("Kunsch, 1989", "Kunsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. The Annals of Statistics, 17(3), 1217-1241."),
    "lakens2017": ("Lakens, 2017", "Lakens, D. (2017). Equivalence tests: A practical primer for t tests, correlations, and meta-analyses. Social Psychological and Personality Science, 8(4), 355-362."),
    "lou2012": ("Lou et al., 2012", "Lou, Y., Caruana, R., & Gehrke, J. (2012). Intelligible models for classification and regression. In Proceedings of the 18th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (pp. 150-158)."),
    "nickell1981": ("Nickell, 1981", "Nickell, S. (1981). Biases in dynamic models with fixed effects. Econometrica, 49(6), 1417-1426."),
    "niculescu2005": ("Niculescu-Mizil & Caruana, 2005", "Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised learning. In Proceedings of the 22nd International Conference on Machine Learning (pp. 625-632)."),
    "nori2019": ("Nori et al., 2019", "Nori, H., Jenkins, S., Koch, P., & Caruana, R. (2019). InterpretML: A unified framework for machine learning interpretability. arXiv preprint arXiv:1909.09223."),
    "ostrensky2023": ("Ostrensky & Frota, 2023", "Ostrensky, V. P., & Frota, L. M. da (2023). Early warning systems via machine learning: A study of currency crises. Economia Aplicada, 27(3), 407-423. https://doi.org/10.11606/1980-5330/ea189768"),
    "platt1999": ("Platt, 1999", "Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In Advances in Large Margin Classifiers (pp. 61-74). MIT Press."),
    "reimann2024": ("Reimann, 2024", "Reimann, C. (2024). Predicting financial crises: An evaluation of machine learning algorithms and model explainability for early warning systems. Review of Evolutionary Political Economy, 5(1), 51-83. https://doi.org/10.1007/s43253-024-00114-4"),
    "rudin2019": ("Rudin, 2019", "Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. Nature Machine Intelligence, 1(5), 206-215."),
    "saito2015": ("Saito & Rehmsmeier, 2015", "Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. PLoS ONE, 10(3), e0118432."),
    "schuirmann1987": ("Schuirmann, 1987", "Schuirmann, D. J. (1987). A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability. Journal of Pharmacokinetics and Biopharmaceutics, 15(6), 657-680."),
    "wang2015": ("Wang, 2015", "Wang, Q. (2015). Fixed-effect panel threshold model using Stata. The Stata Journal, 15(1), 121-134."),
}

# ------------------------------------------------------------------------------------------
# Body (a small markup: $math$, [key; key] citations, [[fig:x]], [[tab:x]], [[sup:x]])
# ------------------------------------------------------------------------------------------
S = []


def H1(t): S.append(("h1", t))
def H2(t): S.append(("h2", t))
def P(t): S.append(("p", fill(t)))
def EQ(latex, label): S.append(("eq", latex, label))
def TBL(k): S.append(("table", k))
def FIGR(k): S.append(("fig", k))
def BUL(items): S.append(("bul", [fill(i) for i in items]))
def APPX(t): S.append(("appendix", t))
def DATA(t): S.append(("data", fill(t)))


_e21 = rd("table16_e21_paired_intervals.csv")
_x0 = _e21[(_e21.family == "Feature ablation") & _e21.AP_CI95_excludes_zero]
_lab = {"B1_Regularized_Linear": "B1", "B4_XGBoost": "XGBoost", "M0_EBM_Additive": "M0"}
_items = [f"{r.comparison.split(' vs ')[0]} in {_lab[r.model]}, {'all folds' if r.evaluation_window.startswith('All') else '2021-2022'}: "
          f"{fmt_num(r.Delta_AP_Point, 3, sign=True)} [{fmt_num(r.Delta_AP_CI95_Low, 3)}, {fmt_num(r.Delta_AP_CI95_High, 3)}]" for r in _x0.itertuples()]
assert (_x0.Delta_AP_CI95_High < 0).all(), "an ablation interval lies above zero; revise the text"
_c6 = (f"none of the {V['e21_c6_n']} Core-6 CI comparisons excludes zero" if V["e21_c6_n_excl0"] == 0 else
       f"{V['e21_c6_n_excl0']} of {V['e21_c6_n']} Core-6 CI comparisons exclude zero (both CI measures in B1: {V['e21_c6_b1_both']} "
       f"[{V['e21_c6_b1_both_lo']}, {V['e21_c6_b1_both_hi']}])")
_mon_lo = float(V["pd_core9_mon_b0_ap_lo"])
MON_NOTE = (" The Core-9 lower limit is exactly zero, so that interval does not exclude zero." if _mon_lo == 0 else
            " The Core-9 interval does not exclude zero." if _mon_lo < 0 else "")
_nw = V["e23_n_lc_none_worse"]
LC_WORSE = "none indicates higher cost" if _nw == 0 else ("one indicates higher cost" if _nw == 1 else f"{_nw} indicate higher cost")
EXCL0_SENTENCE = ("No interval excludes zero." if not _items else
                  f"{'Only one interval excludes zero' if len(_items) == 1 else ['Two', 'Three', 'Four', 'Five', 'Six'][len(_items) - 2] + ' intervals exclude zero'}, indicating "
                  f"{'a loss' if len(_items) == 1 else 'losses'} ({'; '.join(_items)}).")

H1("Introduction")
P("Early-warning systems for exchange-rate and balance-of-payments stress are decision-support tools. A model ranks countries or months by "
  "risk, and analysts decide where to spend limited monitoring capacity [kaminsky1998; holopainen2017]. Their value depends on out-of-sample "
  "ranking quality, on the calibration of the probabilities shown to users and on the cost of the actions they trigger, not on in-sample fit. "
  "Candidate early-warning variables are nevertheless often motivated by in-sample regressions. The unpublished study examined here uses "
  "fixed-effects panel threshold models to investigate whether the association between currency internationalization (CI) and macroeconomic "
  "risk varies with institutional quality (IQ). [hansen1999] provides the non-dynamic threshold framework used as its starting point.")
P("This paper asks whether such threshold evidence survives the move from a regression table to an early-warning system. We organise the study "
  "around three questions.")
BUL(["RQ1 (replication): Can the reported threshold estimates be reproduced from the original data, and how sensitive are they to estimation "
     "choices that are rarely reported, such as the trimming of the threshold grid and the timing of information?",
     "RQ2 (forecast value): Under explicit information-release assumptions, do CI, IQ and their interaction improve the prediction of future REER "
     "stress relative to persistence, country-identity and macro-only benchmarks, using {sesoi} AP as a smallest effect of interest?",
     "RQ3 (decision value): How do calibration, analyst-routing and fallback policies compare under explicit decision-cost assumptions, and how do "
     "their rankings change in a later retrospective evaluation period?"])
P("We use data from an earlier unpublished working paper on CI, IQ and six macroeconomic risks, with overlapping authorship: a SWIFT-share panel "
  "of six countries and an FX-turnover-share panel of nine countries. This is an internal replication. We reconstruct the reported threshold "
  "tests and regime coefficients, then evaluate related features in a release-lag-adjusted backtest for three-month real-effective-exchange-rate "
  "(REER) stress. The 2017-2020 folds support development; 2021-2022 had been inspected during study design and are treated as retrospective "
  "test folds. A later evaluation covers 2023-2025. An implementation audit identified timing problems in its original run, so the extension "
  "evidence in the main text uses a corrected, explicitly exploratory rerun. The original run and protocol chronology are retained in Appendix A. "
  "None of these historical samples is represented as an untouched prospective test.")
P("The evidence is heterogeneous. The reported F statistics can be reconstructed, but sensitivity to trimming and inference assumptions limits "
  "their use as predictive justification. In the main FX-share comparisons, estimated gains reach the chosen {sesoi} AP margin only for IQ in "
  "the additive model, and uncertainty often remains too large to exclude or confirm such gains. Equivalence of the interaction and additive models is not established. Benchmark "
  "rankings also change across evaluation periods and target definitions. The study makes three contributions:")
BUL(["An auditable workflow linking reconstruction of regression evidence to information-timing checks, out-of-time prediction and simulated "
     "decisions. The contribution is the integrated evaluation and documentation of these stages.",
     "A matched assessment of CI and IQ information using persistence and country-identity benchmarks, feature and interaction ablations, paired "
     "uncertainty intervals and event-level warning measures.",
     "A comparative evaluation of calibration, analyst-routing assumptions and fallback policies, showing how predictive gains and simulated "
     "decision benefits depend on the target, period and policy design."])
P("Section 2 reviews related work. Section 3 describes the data and the replication design, Section 4 the forecasting and decision framework and "
  "Section 5 the results. Section 6 discusses the decision rules and limitations, and Section 7 concludes.")

H1("Related work")
H2("Currency internationalization, institutions and exchange-rate risk")
P("The international use of a currency in invoicing, payments and financial transactions changes the exposure of the issuing economy to global "
  "capital flows [eichengreen2018]. Institutional quality, often measured with the Worldwide Governance Indicators (WGI) [kaufmann2011], is argued "
  "to condition how openness translates into exchange-rate outcomes [chinn2006; aman2024], and policy arrangements that support "
  "internationalization affect currency co-movements [an2024]. Threshold models make such conditioning explicit by estimating separate slopes below "
  "and above an estimated IQ threshold [hansen1999; wang2015]. In the earlier working paper examined here, the models use contemporaneous "
  "regressors and annual governance scores assigned to months of the same year. Such estimates describe within-sample associations; a forecasting "
  "design additionally needs an explicit information set and release chronology [croushore2001]. These studies motivate candidate variables, but "
  "do not establish that a CI-by-IQ threshold predicts future REER stress.")
H2("Machine-learning early-warning systems")
P("Early-warning research evaluates signals by their out-of-sample ability to anticipate currency or banking stress [kaminsky1998; frankel1996]. "
  "Comparisons of machine-learning methods with logit benchmarks find that gains depend on the evaluation design and on the number of independent "
  "episodes [holopainen2017; beutel2019; bluwstein2023]. Recent work applies recurrent and convolutional networks to currency and financial "
  "crises [barthelemy2024; chen2024] and adds post-hoc explanations [reimann2024]; a study that respects autocorrelation and publication lags "
  "reports markedly more modest accuracy than earlier work [ostrensky2023]. Imbalanced targets call for precision-recall metrics [saito2015], and "
  "decision-oriented evaluation requires explicit costs of missed and false alarms [elkan2001].")
H2("Interpretable models, calibration, drift and selective prediction")
P("Explainable boosting machines (EBMs) are generalized additive models with optional pairwise interactions [lou2012; nori2019] and suit "
  "high-stakes settings where post-hoc explanations of black boxes are unreliable [rudin2019]. Random forests [breiman2001] and gradient-boosted "
  "trees [chen2016] are strong tabular baselines. Probabilities shown to decision makers should be calibrated on held-out data "
  "[platt1999; niculescu2005], and deployed models need monitoring and fallback rules when the data-generating process drifts [gama2014]. "
  "Selective prediction lets a system defer uncertain cases to humans [chow1970; geifman2017]. A non-significant difference does not establish "
  "practical equivalence. We interpret paired intervals against a stated smallest effect of interest and distinguish evidence of equivalence from "
  "inconclusive estimates [schuirmann1987; lakens2017].")

H1("Data and replication design")
H2("Original study and data")
P("The internal replication uses the two regression datasets of the earlier unpublished working paper. The working paper exists as a long draft "
  "(file created 15 November 2023, last revised 14 October 2024) and a shortened draft (23 July 2025); both report the threshold estimates "
  "replicated here, and Supplementary Table S11 lists the discrepancies identified in them. According to the drafts, the SWIFT shares come from "
  "SWIFT's monthly reports, the FX-turnover shares from the BIS and the World Bank, and the other macro series from the World Bank and the Wind "
  "Economic Database; quarterly GDP was converted to months by backward filling. The series were compiled into the two regression datasets on "
  "13 June 2023 (file metadata). The Wind series codes, the exact definition of the turnover share and any interpolation were not retained. The "
  "Panel B CI column is labelled as domestic-currency FX-derivatives turnover and varies from month to month in every country (apart from runs "
  "of zeros for Russia), so it is not a step-filled triennial survey value, but its construction cannot be verified. Supplementary Table S15 "
  "documents the variables by their dataset column names, and SHA-256 checksums of the files are recorded in the reproduction archive.")
P("Panel A measures CI by the currency's share of SWIFT payments for China, Hungary, Mexico, Poland, the Russian Federation and South Africa "
  "(2012-08 to 2021-12, N = 678). Panel B measures CI by the domestic currency's share of FX-turnover and adds Brazil, India and Korea (2012-01 to "
  "2022-12, N = 1,188). IQ is the mean of the six WGI dimensions. The six risk indicators are CPI volatility (CPI_Vol), FX-reserve volatility "
  "(FX_Vol), consumption volatility (CE_Vol), real exchange-rate volatility (ER_Vol), the credit-to-GDP gap (CG_Gap) and unemployment (Unemp). "
  "The Panel B ER_Vol series is available for only {B_er_countries} of the nine countries, so that regression uses N = {B_er_n}. [[tab:data]] "
  "summarises the samples.")
TBL("data")
H2("Threshold model and replication protocol")
P("For risk indicator $y$ the single-threshold fixed-effects model is")
EQ(r"y_{it} = \mu_i + \beta_1\, CI_{it}\, \mathbf{1}(q_{it} \le \gamma) + \beta_2\, CI_{it}\, \mathbf{1}(q_{it} > \gamma) + \rho\, y_{i,t-6} + \theta^{\top} X_{it} + \delta^{\top} R_{it} + \varepsilon_{it}", "eq:thr")
P("where $q_{it}$ is IQ, $X_{it}$ are the controls and $R_{it}$ the other five risk indicators. The threshold $\\gamma$ is estimated by "
  "concentrated least squares over the IQ values inside the trimmed range. The test of no threshold uses")
EQ(r"F = \frac{S_0 - S_1(\hat\gamma)}{\hat\sigma^2}, \qquad \hat\sigma^2 = \frac{S_1(\hat\gamma)}{N(T-1)}", "eq:F")
P("where $S_0$ and $S_1$ are the residual sums of squares without and with the threshold. In the variance formula, $N$ denotes the number of "
  "countries and $T$ the number of monthly observations per country; the N column in the sample tables denotes total observations. The "
  "reconstruction also evaluates the alternative denominator $T(N-1)$. Matching a reported statistic under this denominator identifies a "
  "compatible calculation, not proof of the unavailable original code or of valid dynamic-panel inference. Bootstrap p-values come from "
  "$B = {n_boot_thresh}$ replications and are computed as")
EQ(r"\hat p = \frac{1 + \#\{b : F^{*}_b \ge F\}}{B + 1}", "eq:p")
P("so the smallest attainable value is {p_min} [davison1997]; Monte Carlo standard errors are reported in the reproduction archive. Each "
  "replication draws whole country series of threshold-model residuals with replacement, adds them to the fitted values of the linear "
  "(no-threshold) model, demeans by country and recomputes both models over the same grid. The lagged dependent variable and the other "
  "regressors are held at their observed values, so the null is static rather than a re-simulated dynamic process. Whole-series resampling "
  "retains within-country temporal ordering but does not generally preserve the joint dependence of contemporaneous cross-country shocks. The "
  "effective number of resampling units is six, eight or nine, depending on the regression. Three choices are not stated in the original "
  "paper: the dataset columns behind CE_Vol and ER_Vol, the timing of the other-risk controls and the trimming fraction. We reconstruct a "
  "compatible implementation through a specification search that scores every candidate against the reported F statistics, thresholds and "
  "regime t statistics (Supplementary Table S2) and apply the selected option to all twelve regressions: the selected outcome series, "
  "contemporaneous other risks and 1% trimming, the default of a widely used Stata implementation [wang2015].")
P("Because this search targets agreement with the earlier tables, the resulting fit is evidence about reproducibility under a compatible "
  "specification, not an independent confirmation of the economic hypothesis. The selected specification retains a lagged dependent variable; "
  "the non-dynamic assumptions underlying [hansen1999] therefore do not automatically establish the validity of the reported threshold-test "
  "p-values, and the static bootstrap above does not repair this.")
H2("Release-lag-adjusted panel")
P("For forecasting we build a country-by-month panel for the nine Panel B economies (Core-9) and six further emerging markets (Chile, Colombia, "
  "Indonesia, Malaysia, Thailand, Turkey; External-6). REER indices, the US nominal effective exchange rate, CPI, policy rates and credit come "
  "from the BIS, reserves from the IMF and governance and macro controls from the World Bank. The backtest approximates availability at the end "
  "of forecast month $t$: monthly REER, CPI, reserves and CI with a one-month lag, so that features use months up to $t-1$; quarterly credit two "
  "months after the quarter; and year-$Y$ WGI and macro controls from September of year $Y+1$, with the age of the latest release as a feature "
  "(Supplementary Table S12). These are release-lag assumptions rather than a reconstruction of every historical release. Two specific limits "
  "apply. First, the WGI are revised retroactively and we use the current vintage, so the IQ series is pseudo-real-time in timing but not in "
  "values. Second, the construction and release calendar of the FX-share series are not documented, so we assess assumed CI release lags of "
  "3, 6 and 12 months and a CI frozen at the training cut-off (Section 5.7). When the CI coverage ends the last release is held forward with its "
  "age. [[fig:fig1]] summarises the information set and the folds.")
P("The analysis is a release-lag-adjusted backtest using available data vintages. Shifting a revised series by a nominal lag does not "
  "reconstruct the values known at that date. Consequently, the estimates should not be interpreted as performance in a fully vintage-correct "
  "real-time deployment; uncertain release dates and retrospective revisions remain sources of measurement and timing risk.")
FIGR("fig1")
H2("Targets and events")
P("The primary target is forward three-month REER stress,")
EQ(r"V^{(3)}_{i,t} = \sqrt{\tfrac{1}{3}\left(r_{i,t+1}^2 + r_{i,t+2}^2 + r_{i,t+3}^2\right)}", "eq:V")
P("where $r_{i,t}$ is the monthly REER log change in percent. This root-mean-square measure captures large movements in either direction; it is "
  "not a demeaned volatility estimator or a dated currency-crisis label. Because consecutive windows share up to two months, high-risk windows "
  "overlap and are not independent events; inference therefore resamples blocks of months. A window is high-risk when $V^{(3)}_{i,t}$ is at or "
  "above the 80th percentile of the training targets of its fold; the thresholds range from {thr_min}% to {thr_max}%. [[tab:folds]] reports "
  "the samples and events of every fold: the development folds (2017-2020) contain {n_pos_dev} high-risk windows in {n_test_dev} "
  "country-months and the retrospective test (2021-2022) {n_pos_lock} in {n_test_lock} ({pos_2021} in 2021 and {pos_2022} in 2022). A "
  "secondary target is the maximum three-month reserve drawdown, $D^{(3)}_{i,t} = \\max\\{0, 1 - \\min_{k \\le 3} R_{i,t+k}/R_{i,t}\\}$. "
  "Scoring the main evaluation required outcome data up to {outcome_to}. An earlier data-availability audit computed target means through "
  "2024-03; no model prediction for origins after 2022-12 was scored before the extension protocol was recorded. [[fig:fig2]] shows the stress "
  "windows and IQ trajectories.")
P("The main results concern REER stress; reserve-drawdown comparisons are treated as sensitivity analyses in Section 5.7 and the supplementary "
  "results. Neither a target definition nor one favourable sensitivity comparison establishes general transfer to reserve-pressure forecasting. "
  "Positive windows and economic episodes are distinct counting units.")
TBL("folds")
FIGR("fig2")

H1("Forecasting and decision framework")
H2("System architecture")
P("The framework runs as scripts in a fixed order. (i) An information-timing module applies each publication lag, holds the last release "
  "forward and records data age. (ii) A replication auditor re-estimates the reported regressions and classifies each discrepancy as a "
  "convention, a suspected transcription error or a non-reproduction. (iii) A forecasting module fits all models on frozen splits and writes "
  "row-level predictions to a single prediction store. (iv) A decision module converts probabilities into alerts, review decisions and fallback "
  "choices. An audit script recomputes every reported metric from the prediction store, checks the timing of every estimation stage and blocks "
  "the manuscript build on any mismatch. Such checks complement, rather than replace, validation of the target, information set and estimation "
  "protocol.")
H2("Temporal protocol")
P("Four expanding development folds test the years 2017-2020 and two retrospective folds test 2021 and 2022. In fold $T$, training origins run "
  "from 2012-01 to August of $T-2$, calibration origins from January to August of $T-1$ and test origins over year $T$. Every origin $s$ used "
  "for fitting or calibration satisfies")
EQ(r"s + h + \ell < \text{first evaluated month}", "eq:mat")
P("with horizon $h$ and REER release lag $\\ell = 1$, so every target used before an evaluation was published before it. The calendar cut-offs in "
  "[[tab:folds]] describe the three-month task; for $h = 6$ the training and calibration ranges are truncated further. The same condition is "
  "imposed inside the training window: hyperparameters are chosen by AP on three inner expanding folds (grids in Supplementary Table S13), each "
  "inner training range ends at least $h + \\ell$ months before its validation range, and imputation and scaling are fitted on the inner "
  "training range only. Event thresholds are estimated on the training targets of each outer fold; the labels used for inner tuning are defined "
  "by the 80th percentile of the inner training targets alone, so no inner validation outcome enters an inner threshold. Supplementary Table S16 "
  "lists, for every fold, horizon and stage (outer training, calibration, inner folds and the calibration history described below), the last "
  "origin used, the month its target was published, the first evaluated month and the targets that define the event threshold; all "
  "{timing_n_checked} stage checks of the main evaluation and of the corrected extension in Sections 5.8-5.9 pass. Development-fold performance "
  "is used for selection and should not be interpreted as an untouched test estimate.")
H2("Models")
P("B0 maps the lagged three-month REER root-mean-square change to risk using a one-variable logistic regression. B1 is ridge regression for the "
  "continuous target and L2-regularised logistic regression for the binary target. B2 estimates an IQ threshold in the training window and fits "
  "regime-specific CI slopes. B3 and B4 are a random forest and XGBoost. M0 is an additive EBM; M1 adds one CI x IQ pairwise term as a "
  "predictive representation of the conditioning hypothesis. C0 is logistic regression on country indicators, while C1 adds the lagged REER "
  "stress measure. These two baselines assess the predictive contribution of persistent country differences. Interaction ablations include a "
  "placebo EBM with a macro-only pair, an unrestricted EBM with ten selected pairs and a linear CI x IQ model. Stochastic learners are averaged "
  "over five seeds.")
H2("Calibration")
P("Each model produces raw probabilities and two calibrated versions: Platt scaling on the eight-month calibration window, and Platt scaling on "
  "earlier out-of-sample scores whose targets have matured (expanding calibration). The historical scores are the stored out-of-sample "
  "predictions of earlier folds and are not regenerated. Because event thresholds change across folds, their outcome labels are recomputed "
  "using the current fold's threshold before the Platt map is fitted. This aligns the calibration targets; it does not turn a score learned for "
  "an earlier threshold into a calibrated probability for the current event. Expanding calibration therefore assumes that the historical "
  "score-to-risk relationship can be transferred to the current target. For each model, the scheme with the lowest pooled development-fold "
  "Brier score is selected; raw probabilities are selected for {n_raw_locked} of the {n_models_cal} benchmark models. Decision analyses use "
  "these selected probabilities unless a calibration comparison is explicitly stated. The 2021-2022 estimates remain retrospective because that "
  "period had been inspected during study design.")
H2("Implementation audit")
P("An internal audit identified four implementation departures: insufficient maturity gaps in inner tuning folds, preprocessing fitted before "
  "inner splitting, inner tuning labels defined by the outer-fold threshold (which is estimated on targets that include the inner validation "
  "ranges) and expanding-calibration labels based on earlier event thresholds. The main 2017-2022 learned-model experiments were rerun after "
  "correction. The original 2023-2025 extension used the earlier tuning implementation and failed {timing_frozen_fail} stage-level timing "
  "checks; it is retained only as analysis history in Appendix A. [[tab:ext]] and [[tab:extdiff]] report the corrected extension as an "
  "exploratory post-hoc rerun. The detailed changes, archived outputs and stage-level timing checks remain part of the reproduction record.")
H2("Metrics and inference")
P("Average precision summarises the precision-recall curve,")
EQ(r"\mathrm{AP} = \sum_{k} (R_k - R_{k-1})\, P_k", "eq:ap")
P("where $P_k$ and $R_k$ are precision and recall at the $k$-th threshold. We report pooled AP over all predictions of a window and the mean of "
  "the fold-specific APs; tables state which is shown. Alerts are issued when the probability $p$ reaches $\\tau = C_{FP}/(C_{FP} + C_{FN})$, "
  "and the expected cost per 100 forecasts is")
EQ(r"\mathrm{Cost} = \frac{100}{n} \sum_{i} \left[ C_{FP}\, \mathbf{1}(p_i \ge \tau,\, y_i = 0) + C_{FN}\, \mathbf{1}(p_i < \tau,\, y_i = 1) \right]", "eq:cost")
P("with $C_{FP} = 1$ and $C_{FN} = 5$ unless stated. Paired differences are assessed with a moving-block bootstrap that resamples calendar months "
  "jointly across countries (1,000 replications) [kunsch1989]. We use blocks of 12 months for the 72-month window and of 6 months for 24- and "
  "36-month windows, because a 24-month window contains only 13 distinct 12-month blocks; results for other lengths are in the reproduction "
  "archive. Reported differences are original-sample estimates; the bootstrap supplies only their intervals. We set the smallest effect of "
  "interest to $\\Delta\\mathrm{AP} = {sesoi}$, as an operational comparison margin, and call two models equivalent when the 90% interval lies "
  "within $\\pm {sesoi}$, the two one-sided tests procedure [schuirmann1987; lakens2017].")
P("The {sesoi} margin is an operational tolerance for this comparison, not an externally validated economic utility threshold. Intervals are "
  "conditional on the fitted predictions and do not incorporate all uncertainty from model selection or refitting. Unless an adjustment is "
  "explicitly reported, the many model and sensitivity comparisons are exploratory. AP differences must be compared within matched samples "
  "because AP depends on event prevalence. The cost threshold of 1/6 is Bayes-optimal only when the probabilities are calibrated for the stated "
  "event and the assumed losses are appropriate.")
H2("Event-level evaluation")
P("Consecutive high-risk origins of a country form an episode. Episodes are formed after the folds of an evaluation window are pooled, so a run "
  "that continues from December into January of the next fold counts once. Episode coverage counts an episode as covered when an alert is "
  "issued between three months before its first origin and its last origin. False alarms are alerts at normal origins outside the three months "
  "before an episode, per country-year. Because coverage permits alerts after an episode has started, it is not the fraction of episodes warned "
  "about in advance. We therefore add a strict early-warning measure: an episode is eligible when its three preceding origins are observed in "
  "the window, and it is detected only if an alert is issued at one of those three origins; the lead is the distance from the first such alert "
  "to the first high-risk origin. Besides the cost threshold $\\tau$ we apply fixed alert quotas of the top one, two or three countries per "
  "month. Leads are relative to the first labelled origin, not to an independently dated crisis. Onset evaluation removes origins whose lagged "
  "volatility already exceeds the fold threshold; it evaluates predictions conditional on the absence of elevated lagged volatility. The "
  "direction analysis splits high-risk windows by the sign of the three-month REER change (real depreciation versus appreciation).")
H2("Decision layer")
P("The review experiment is a scenario simulation, not an observed workflow. Each month analysts review up to $k$ country cases; a reviewed case "
  "costs a fee $c$, and the remaining cases are decided automatically at $\\tau = 1/6$. In the baseline grid a reviewed case is resolved "
  "correctly with probability one (an oracle bound) or 0.8, and every automated policy (never alert, B0, macro-only EBM, M0, M1 with each "
  "calibration, B3, B4) is crossed with four routing rules: least confident first (smallest $|\\mathrm{logit}\\,p - \\mathrm{logit}\\,\\tau|$, "
  "the distance to the cost-sensitive boundary rather than to 0.5), highest probability first, highest lagged volatility first and random. "
  "Random routing is evaluated as its exact expectation, so no simulation seed is involved.")
P("A single accuracy does not determine the expected loss, so a second grid varies the reviewer-error model: errors independent of class with "
  "accuracy 0.8; more missed events (error rate 0.3 on events, 0.1 on non-events); more false alarms (0.1 and 0.3); and confidence-dependent "
  "errors that reach 0.4 at the decision boundary and decline with the logit distance from it. Errors are independent of country, and an error "
  "turns a reviewed case into the wrong decision. This grid adds expected-loss routing, which reviews up to $k$ cases with the largest "
  "model-implied reduction in expected loss, $\\mathrm{EL}_{auto} - \\mathrm{EL}_{review}$, computed from the model probability and the same "
  "error model, and only when that reduction is positive. The rule uses no outcome information. Perfect review is an oracle bound, the "
  "imperfect-reviewer models are assumptions, and neither is evidence of observed human forecasting performance. Cost differences carry paired "
  "block-bootstrap intervals.")
H2("Retrospective extension and fallback policies")
P("The 2023-2025 extension began with an author-recorded protocol that specifies the sample (Core-9 and External-6), the features (macro and "
  "IQ; no updated post-2022 CI observations are available), the folds (test years 2023-2025, with 2021-2022 as warm-up folds), the initial model "
  "set (B0, B1, macro EBM and XGBoost), raw probabilities, the costs and a fallback policy. All models are trained on the pooled 15-country "
  "history, so External-6 is evaluated out of time but is not an unseen-country transfer (Supplementary Table S17). The last forecast origin, "
  "{ext_last_origin}, needs REER outcomes for the following three months, which are published under the assumed lag in {ext_outcome_to}; the "
  "BIS REER data used contain observations through {reer_last_obs} for all 15 economies, so every extension target was observable when scored.")
P("The policy monitors a single learned candidate, fixed in the protocol as the model with the highest mean development-fold AP among B1, the "
  "macro EBM and XGBoost. The macro EBM was selected with {fb_dev_ap_m0}, against {fb_dev_ap_b4} for XGBoost and {fb_dev_ap_b1} for B1, a "
  "margin of {fb_dev_margin} that amounts to a near tie. The rule deploys this candidate in year $T$ only if, on the latest twelve matured origins (up to "
  "August of year $T-1$), its AP exceeds that of B0 by at least $\\delta = {fb_delta}$ and its expected calibration "
  "error is at most {fb_ece_cap} (the largest per-fold ECE of B0 in the development folds); otherwise it deploys B0. Both the monitored "
  "candidate and B0 use the protocol features (macro and IQ). The original implementation and its outcomes are archived in Appendix A because "
  "its inner tuning did not meet the timing condition. The corrected rerun retains the single-candidate rule and evaluates additional model and "
  "IQ comparisons.")
P("The extension is retrospective and was not independently preregistered. The protocol hash identifies a file, not an independently verified "
  "freeze date. Prior target-summary inspection and a post-freeze scoring-code change are disclosed in Appendix A. After the code corrections in "
  "Section 4.5 we added a post-hoc rerun of the same folds that is explicitly exploratory: it refits B0, C1, B1, the macro-only and macro+IQ "
  "EBMs and the macro-only and macro+IQ XGBoost models with the corrected tuning, estimates the paired IQ increment, compares corrected always-on "
  "policies with the refitted fallback, reports the yearly inputs of the fallback rule and evaluates a multi-candidate monitor that deploys "
  "whichever candidate has the largest recent AP gain over B0 subject to the same $\\delta$ and ECE cap. The monitor was defined after the "
  "frozen result was known and is a new policy, not part of the protocol.")

H1("Results")
H2("Replication of the threshold evidence")
P("[[tab:thresh]] compares the replicated threshold tests with the reported values. With Hansen's residual variance the replicated F statistics "
  "exceed the reported ones by a factor determined by the panel dimensions: reported/replicated = {ratio_A} in all six Panel A regressions, "
  "{ratio_B_other} in the five nine-country Panel B regressions and {ratio_B_er} in the eight-country Panel B ER_Vol regression. Dividing "
  "instead by $T(N-1)$ reproduces {n_f_exact} of the 12 reported F statistics to two decimals, which identifies a compatible convention without "
  "recovering the unavailable original code. {n_thr_exact} of 12 thresholds are reproduced to four decimals. Of the {n_cells} reported regime "
  "coefficients, {n_repro} are reproduced in coefficient and t statistic, {n_tdiff} in the coefficient only and {n_notrep} are not reproduced; "
  "{n_trans} differ from our estimates only by a digit or a sign and are classified as suspected transcription errors, although we cannot rule "
  "out other causes without the original code (Supplementary Table S1).")
TBL("thresh")
H2("Threshold robustness")
P("The thresholds are often extreme. In {n_edge} of 12 regressions fewer than 10% of observations fall in the low-IQ regime; for Panel A CPI_Vol "
  "the low regime contains {A_cpi_share}% of observations. With 1% trimming {n_sig1} of 12 tests are significant at 5%; with 15% trimming "
  "{n_lost15} of these lose significance (Panel A CPI_Vol: p = {A_cpi_p15}), leaving {robust_list}. In a pseudo-real-time version that lags CI by "
  "one month and uses IQ and annual controls only after their release, {n_sig_prt} tests are significant and {n_both} of the originally "
  "significant ones survive ({both_list}). With single WGI dimensions as threshold variables, {wgi_sig_A} of {wgi_n} Panel A and {wgi_sig_B} of "
  "{wgi_n} Panel B tests are significant (Supplementary Tables S3-S5). [[fig:fig8]] summarises the evidence. The answer to RQ1 is that the "
  "reported statistics can be reconstructed under a compatible calculation, but their specification sensitivity and inferential limitations "
  "prevent them from establishing a stable predictive or causal mechanism.")
FIGR("fig8")
H2("Forecasting benchmark")
P("[[tab:bench]] reports the benchmark. Over all six folds (pooled AP, base rate {base_all}) the random forest leads with {b3_all}, followed by "
  "C1 ({c1_all}), XGBoost ({b4_all}) and the persistence rule B0 ({b0_all}); the EBMs reach {m0_all} (M0) and {m1_all} (M1). The ranking is not "
  "stable. In the development folds the random forest is best ({b3_dev}) and B0 weak ({b0_dev}); in the retrospective test C1 reaches "
  "{c1_lock} and B0 {b0_lock}, above the other multivariable models in [[tab:bench]] (at most {max_learned_lock}), and the EBMs fall to about "
  "{m1_lock}. Paired bootstrap intervals over the six folds show no AP gain over B0 whose lower 95% limit exceeds zero: the random forest's "
  "gain is {bt_b3b0_all_L12} [{bt_b3b0_all_L12_lo}, {bt_b3b0_all_L12_hi}] and XGBoost's {bt_b4b0_all_L12} [{bt_b4b0_all_L12_lo}, "
  "{bt_b4b0_all_L12_hi}]. Country identity alone (C0) reaches {c0_all}, close to the EBMs, which is consistent with cross-country differences "
  "contributing to discrimination, without quantifying how much of each model's skill is attributable to country identity ([[fig:fig3]]).")
TBL("bench")
FIGR("fig3")
H2("Incremental information from CI and IQ")
P("[[tab:ablation]] compares CI and IQ additions in the main FX-share specification. Adding CI to the macro feature set lowers pooled AP in "
  "{n_ci_neg} of 6 model-window cells. Only one of the 18 additions raises AP by {sesoi} or more: IQ in M0 over six folds ({d_m0_iq_all}), "
  "with a paired 95% interval of [{e21_m0_iq_all_lo}, {e21_m0_iq_all_hi}] ([[tab:intervals]]). Relative to M0, the "
  "CI x IQ interaction changes AP by {e05_m1_all} over all folds and {e05_m1_lock} in the retrospective test, a placebo macro interaction by "
  "{e05_plac_all} and {e05_plac_lock}, and an unrestricted EBM by {e05_unr_all} and {e05_unr_lock}. These are original-sample differences "
  "(unrounded, the six-fold M1 minus M0 difference is {m1m0_all_unrounded}). The paired 95% bootstrap intervals for M1 minus M0 are "
  "[{bt_m1m0_all_L12_lo}, {bt_m1m0_all_L12_hi}] over six folds and [{bt_m1m0_lock_L6_lo}, {bt_m1m0_lock_L6_hi}] in the retrospective test. "
  "Neither 90% interval ([{bt_m1m0_all_L12_lo90}, {bt_m1m0_all_L12_hi90}] and [{bt_m1m0_lock_L6_lo90}, {bt_m1m0_lock_L6_hi90}]) lies within "
  "$\\pm {sesoi}$, so equivalence is not established in either window.")
TBL("ablation")
P("Point estimates below {sesoi} do not show that the underlying effects are below {sesoi}, and the one estimate above it is not "
  "distinguishable from zero. [[tab:intervals]] therefore gives paired intervals "
  "for all 18 increments. In {e21_n_excl_plus} of {e21_n_abl} the 95% interval excludes a gain of {sesoi} and in {e21_n_tost} the 90% interval "
  "lies within $\\pm {sesoi}$; the remaining {e21_n_not_excl_plus} intervals, mostly involving IQ and the 24-month retrospective window, reach "
  "upper limits of up to {e21_max_hi}, so a gain of that size cannot be excluded there. " + EXCL0_SENTENCE + " Interval limits are reported "
  "with additional digits where a nonzero limit would otherwise round to zero. The evidence is therefore an absence of detected gains with "
  "limited precision, not a demonstrated absence of value.")
TBL("intervals")
P("The EBM explanations ([[fig:fig5]]) rank the FX share {e09_rank_fx} of {e09_nterms} terms and the CI x IQ pair {e09_rank_inter}; the CI "
  "response is almost parallel across IQ levels. Replacing the FX share level by an expanding country mean (between) and the deviation from it "
  "(within) moves M0's pooled AP from {m0_all} to {dec_m0_all}, compared with {m0_macro_all} for the macro-only M0; adding a within x IQ or a "
  "between x IQ pair gives {dec_within_all} and {dec_between_all}. The between component carries {imp_between}% of total EBM importance against "
  "{imp_within}% for the within component (Supplementary Table S14). This decomposition is consistent with part of the CI signal reflecting "
  "persistent country differences; importance shares do not establish that CI is only a country identifier or identify a causal channel.")
FIGR("fig5")
H2("Events, onsets and direction")
P("[[tab:events]] moves from windows to episodes. Over six folds there are {n_episodes_all} episodes ({n_episodes_lock} in 2021-2022); the "
  "fold-specific counts in [[tab:folds]] sum to {n_ep_fold_sum} because {n_ep_cont} runs continue across a year boundary and are counted once "
  "here. At $C_{FN} = 5$, B0 covers {ep_rec_b0_all}% of episodes with {ep_fa_b0_all} false alarms per country-year, XGBoost {ep_rec_b4_all}% "
  "with {ep_fa_b4_all} and M1 {ep_rec_m1_all}% with {ep_fa_m1_all}; in the retrospective test M1 covers {ep_rec_m1_lock}%. Under the strict "
  "definition, {e22_n_el_all} episodes are eligible ({e22_n_el_lock} in 2021-2022). B0 warns before the start of {e22_b0_tau_all}% of them, "
  "XGBoost {e22_b4_tau_all}%, C1 {e22_c1_tau_all}% and M1 {e22_m1_tau_all}%, with a median lead of {e22_b0_tau_all_lead} months, the maximum "
  "the definition allows; in 2021-2022 the shares are {e22_b0_tau_lock}%, {e22_b4_tau_lock}%, {e22_c1_tau_lock}% and {e22_m1_tau_lock}%. With "
  "a fixed quota of two countries per month, false alarms fall to below one per country-year, and B0 detects {e22_b0_top2_all}% of episodes in "
  "advance against {e22_b4_top2_all}% for XGBoost and {e22_m1_top2_all}% for M1. When origins already in stress are removed, AP falls for every "
  "model, and in the retrospective test C1 ({on_c1_lock}) leads M1 ({on_m1_lock}) and B0 ({on_b0_lock}) in the onset-restricted sample "
  "({on_npos_lock} onset windows). Over six folds B0 and M1 predict depreciation and appreciation windows with AP {dep_b0_all} and "
  "{app_b0_all} (B0) and {dep_m1_all} and {app_m1_all} (M1). In 2021-2022 the persistence-based models detect the {dep_npos_lock} "
  "depreciation windows better (B0 {dep_b0_lock}, C1 {dep_c1_lock}) than the EBMs (M1 {dep_m1_lock}).")
TBL("events")
H2("Calibration and the decision layer")
P("Platt scaling on the eight-month window worsens the pooled Brier score for {n_platt8_worse_all} of {n_models_cal} models (M1: "
  "{m1_brier_raw_all} raw, {m1_brier_platt_8m_all} with eight-month Platt, {m1_brier_platt_expanding_all} with expanding Platt); calibration "
  "windows contain as few as {cal_pos_2020} events. In the automated setting M1 costs {e15_m1auto_b0auto_all_A} per 100 forecasts against "
  "{e15_m1auto_b0auto_all_B} for B0 over six folds (difference {e15_m1auto_b0auto_all} [{e15_m1auto_b0auto_all_lo}, "
  "{e15_m1auto_b0auto_all_hi}]), and {e15_m1auto_b0auto_lock_A} against {e15_m1auto_b0auto_lock_B} in the retrospective test "
  "({e15_m1auto_b0auto_lock} [{e15_m1auto_b0auto_lock_lo}, {e15_m1auto_b0auto_lock_hi}]; [[fig:fig4]]). [[tab:review]] reports the review "
  "simulation with two reviews per month and a fee of 0.5. Routing the least confident M1 cases beats random routing in both windows "
  "({e15_m1rev_rand_all} [{e15_m1rev_rand_all_lo}, {e15_m1rev_rand_all_hi}] and {e15_m1rev_rand_lock} [{e15_m1rev_rand_lock_lo}, "
  "{e15_m1rev_rand_lock_hi}]), and oracle review also helps B0 ({e15_b0rev_b0auto_all} [{e15_b0rev_b0auto_all_lo}, "
  "{e15_b0rev_b0auto_all_hi}]). Whether M1 with review beats B0 with review depends on the window: {e15_m1rev_b0rev_all} "
  "[{e15_m1rev_b0rev_all_lo}, {e15_m1rev_b0rev_all_hi}] over six folds and {e15_m1rev_b0rev_lock} [{e15_m1rev_b0rev_lock_lo}, "
  "{e15_m1rev_b0rev_lock_hi}] in 2021-2022.")
TBL("review")
P("[[tab:reviewerr]] examines the reviewer-error assumptions. With perfect review, expected-loss routing reduces cost relative to "
  "low-confidence routing for B0 ({e23_all_perf_b0_el_lc} [{e23_all_perf_b0_el_lc_lo}, {e23_all_perf_b0_el_lc_hi}]); the M1 difference is "
  "{e23_all_perf_m1_el_lc} [{e23_all_perf_m1_el_lc_lo}, {e23_all_perf_m1_el_lc_hi}]. For M1 in 2021-2022 the difference is "
  "{e23_lock_perf_m1_el_lc} [{e23_lock_perf_m1_el_lc_lo}, {e23_lock_perf_m1_el_lc_hi}], consistent with sensitivity to poorly calibrated "
  "probabilities, although this comparison does not isolate calibration as the cause. Under each imperfect-reviewer specification at a fee of "
  "0.5, expected-loss routing reviews no cases in the evaluated grid. For the three fixed class-error models this follows algebraically from the "
  "assumptions: false-negative and false-positive error rates sum to 0.4, making the maximum model-implied net benefit zero at the cost boundary "
  "$p = 1/6$. The no-review outcome is therefore not evidence that human review is intrinsically unhelpful. Across the {e23_n_lc_rand} "
  "imperfect-review comparisons, low-confidence routing beats random routing in {e23_n_lc_rand_better}, but none of its intervals establishes a "
  "reduction relative to no review and " + LC_WORSE + ". Review value depends on the fee, error model, calibration and "
  "comparison policy.")
TBL("reviewerr")
FIGR("fig4")
FIGR("fig7")
H2("Robustness and information timing")
P("The reported EBM results are sensitive to information timing. Using month-$t$ REER values, which are not published at the end of month $t$, "
  "raises the pooled AP of M1 from {m1_all} to {spot_m1_all} and of M0 from {m0_all} to {spot_m0_all}; an evaluation without the one-month "
  "REER lag would therefore overstate the EBMs' skill. Under longer assumed CI release lags of 3, 6 and 12 months M1 reaches {cilag3_m1_all}, "
  "{cilag6_m1_all} and {cilag12_m1_all} over six folds, and freezing CI at the training cut-off gives {cifrozen_m1_all}. Other variations "
  "(Supplementary Table S6) change model rankings: with a q75 threshold B0, XGBoost and M1 reach {q75_b0_all}, {q75_b4_all} and {q75_m1_all}; "
  "with q90 ({q90_npos_all} high-risk windows) {q90_b0_all}, {q90_b4_all} and {q90_m1_all}; with country-specific q80 thresholds "
  "{cty_b0_all}, {cty_b4_all} and {cty_m1_all}; at a six-month horizon {h6_b0_all}, {h6_b4_all} and {h6_m1_all}. Single WGI dimensions give M1 "
  "an AP between {wgi_ap_min} and {wgi_ap_max}. Under leave-one-country-out validation the equal-weighted AP is {loco_b0} for B0 and {loco_m1} "
  "for M1, and deleting any single country moves the M1-M0 difference only between {del_min} and {del_max}. Sub-period results, external "
  "transfer and adaptive training weights are reported in Supplementary Tables S7-S9.")
P("Paired intervals qualify these comparisons. Of {e21_rob_n} model-versus-B0 contrasts across the robustness specifications, {e21_rob_n_pos} "
  "favour the model with a 95% interval above zero and none favours B0: {e21_rob_pos_list}. These exploratory contrasts are not "
  "multiplicity-adjusted evidence of general superiority. In the matched Core-6 sample ({c6_npos_all} high-risk windows in {c6_n_all} "
  "country-months) M1 reaches {c6_sw_m1_all} with SWIFT features and {c6_noci_m1_all} without CI, a difference of {e21_c6_m1_swift} "
  "[{e21_c6_m1_swift_lo}, {e21_c6_m1_swift_hi}]; " + _c6 + ". The main FX-share ablations do not show a {sesoi} AP gain from CI, but this result "
  "should not be generalized to every CI measure or risk definition.")
H2("Corrected retrospective extension for 2023-2025")
P("The corrected extension covers {conf_all15_n} country-months and {conf_all15_npos} high-risk windows across 15 economies ([[tab:ext]]). All "
  "estimates in this section are exploratory because the rerun followed inspection of earlier extension outputs. Macro-only XGBoost has pooled "
  "AP {ph_all15_b4mac} and cost {ph_all15_b4mac_cost} per 100 forecasts, compared with {ph_all15_b0} and {ph_all15_b0_cost} for B0. Macro+IQ "
  "XGBoost has AP {ph_all15_b4} and cost {ph_all15_b4_cost}. Its paired differences from B0 are {pd_all15_b4_b0_ap} [{pd_all15_b4_b0_ap_lo}, "
  "{pd_all15_b4_b0_ap_hi}] in AP and {pd_all15_b4_b0_cost} [{pd_all15_b4_b0_cost_lo}, {pd_all15_b4_b0_cost_hi}] in cost ([[tab:extdiff]]), so "
  "the full-sample intervals do not establish superiority. In Core-9, however, macro+IQ XGBoost exceeds B0 by {pd_core9_b4_b0_ap} AP "
  "[{pd_core9_b4_b0_ap_lo}, {pd_core9_b4_b0_ap_hi}]; in External-6 the difference is {pd_ext6_b4_b0_ap} [{pd_ext6_b4_b0_ap_lo}, "
  "{pd_ext6_b4_b0_ap_hi}]. External-6 is an out-of-time subset of the pooled training design, not a set of unseen training countries.")
TBL("ext")
H2("Institutional information and fallback policies in the extension")
P("Adding IQ to the corrected macro EBM changes pooled AP by {pd_all15_iq_m0_ap} [{pd_all15_iq_m0_ap_lo}, {pd_all15_iq_m0_ap_hi}] over 15 "
  "countries, {pd_core9_iq_m0_ap} [{pd_core9_iq_m0_ap_lo}, {pd_core9_iq_m0_ap_hi}] in Core-9 and {pd_ext6_iq_m0_ap} [{pd_ext6_iq_m0_ap_lo}, "
  "{pd_ext6_iq_m0_ap_hi}] in External-6; only the External-6 interval excludes zero. The XGBoost increment is {pd_all15_iq_b4_ap} "
  "[{pd_all15_iq_b4_ap_lo}, {pd_all15_iq_b4_ap_hi}]. For the EBM, the Brier difference is {pd_all15_iq_m0_brier} [{pd_all15_iq_m0_brier_lo}, "
  "{pd_all15_iq_m0_brier_hi}] and the expected-cost difference is {pd_all15_iq_m0_cost} [{pd_all15_iq_m0_cost_lo}, {pd_all15_iq_m0_cost_hi}] "
  "per 100 forecasts. These exploratory estimates suggest that IQ helps the additive model in this period more clearly at the cost threshold "
  "than in ranking; the AP intervals are wide, the result does not carry over to XGBoost, and macro+IQ EBM AP remains below B0 "
  "({ph_all15_m0} versus {ph_all15_b0}).")
P("The refitted single-candidate fallback deploys B0 in every year and therefore yields no improvement over always using B0. The monitored macro "
  "EBM's AP differences from B0 on the latest matured origins are {ph_fb_gain_list} for {ph_fb_years}, none reaching $\\delta$. The exploratory multi-candidate monitor "
  "{ph_mon_switch}. Its AP difference from B0 is {pd_all15_mon_b0_ap} [{pd_all15_mon_b0_ap_lo}, {pd_all15_mon_b0_ap_hi}] over 15 countries and "
  "{pd_core9_mon_b0_ap} [{pd_core9_mon_b0_ap_lo}, {pd_core9_mon_b0_ap_hi}] in Core-9." + MON_NOTE + " Relative to always using macro+IQ XGBoost, its Core-9 "
  "difference is {pd_core9_mon_b4_ap} [{pd_core9_mon_b4_ap_lo}, {pd_core9_mon_b4_ap_hi}]. With annual updates and a lagged monitoring window, "
  "response depends on when model rankings change and when outcomes mature; these results do not establish a universal one-year delay or the "
  "performance of more frequent monitoring.")
TBL("extdiff")

H1("Discussion")
H2("Decision rules")
P("[[tab:rules]] translates the results into conditional design considerations. Persistence and country-identity models provide useful "
  "reference points, while release assumptions, probability calibration and decision costs influence the evaluation. The CI-by-IQ interaction "
  "does not provide the chosen AP gain in the main comparison, CI does not in the main FX-share ablations, and the IQ gain for the EBM reaches "
  "the margin only in point estimate. The paired intervals, the sensitivity results and the post-hoc IQ results for the EBM prevent a blanket "
  "rejection of institutional or CI "
  "information. The policy results answer RQ3 comparatively: no evaluated decision rule is uniformly best across periods and assumptions.")
TBL("rules")
H2("Implications for expert and decision-support systems")
P("The applied contribution is a workflow for assessing whether regression-motivated variables deserve a role in predictive decision support. "
  "It separates reconstruction of the original estimates, out-of-time feature evaluation and policy comparisons under explicit loss "
  "assumptions. Information timing changes the EBM estimates materially and must be checked within nested tuning and calibration as well as at "
  "the outer test boundary. Ranking, calibration and cost can support different model choices. Review policies inherit uncertainty from "
  "probability estimates and assumed human errors; some no-review outcomes follow directly from the loss parameters. Fallback policies also "
  "depend on the monitored candidate set and update schedule. These findings support transparent comparative evaluation, but do not validate an "
  "optimal algorithm or a deployed warning service.")
H2("Limitations")
P("The primary forecasting panel contains nine countries over eleven years, with {n_episodes_all} labelled episodes in the evaluated folds. "
  "Overlapping targets, common shocks and the limited number of country clusters constrain inference; short evaluation windows yield few "
  "independent time blocks, and {e21_n_not_excl_plus} of the {e21_n_abl} ablation intervals are too wide to exclude a gain of the chosen size. Development-period model "
  "selection and retrospective inspection of 2021-2022 limit claims of untouched testing. The 2023-2025 extension is historical and cannot test "
  "updated CI. Its primary estimates come from a corrected exploratory rerun after prior target-summary and model-output inspection; the "
  "superseded implementation is retained in Appendix A solely as an audit record. The data are release-lag adjusted rather than fully vintage "
  "reconstructed; current-vintage revisions and uncertain source calendars remain limitations. The Wind series codes and the construction of "
  "the CI series could not be re-verified, and changing a nominal lag does not resolve provenance or measurement validity. The replication "
  "preserves a dynamic fixed-effects specification, so Nickell bias [nickell1981] and the applicability of non-dynamic threshold-test inference "
  "require caution; the country-block bootstrap holds the lagged dependent variable fixed and rests on six, eight or nine resampling units. A "
  "search for specifications that reproduce earlier tables is not an independent hypothesis test. Expanding calibration assumes that scores "
  "learned under earlier event thresholds can be mapped to the current target. The policy simulation assumes costs and reviewer-error "
  "mechanisms; it is neither a field trial nor evidence that real analysts can achieve the simulated gains. AP equivalence is local to a stated "
  "margin and comparison, and is not evidence of economic equivalence or policy causality.")

H1("Conclusion")
P("This study traces institution-conditioned currency-internationalization evidence from internal replication to predictive and simulated "
  "decision evaluation. A compatible implementation reconstructs the reported threshold statistics, but several findings are sensitive to "
  "trimming and inference assumptions. In the main FX-share comparisons, adding CI lowers AP, and only the IQ gain for the additive EBM reaches "
  "the chosen AP margin in point estimate, while uncertainty frequently prevents either the exclusion or the confirmation of such gains. Results vary with the target, model and sample, including an exploratory reduction in the "
  "additive EBM's expected cost from IQ in the corrected 2023-2025 evaluation. Persistence remains a strong benchmark, but neither it nor the evaluated review and "
  "fallback policies is uniformly preferable. The contribution is an auditable workflow that separates reproducibility, predictive value and "
  "decision assumptions, with explicit information-timing checks and bounded conclusions.")

DATA("BIS, IMF and World Bank data are public. The regression datasets of the original working paper, compiled on 13 June 2023, include "
     "licensed Wind series and are not redistributed here. Supplementary Table S15 documents their variables, and the reproduction archive "
     "records file checksums; the original Wind series codes were not retained. The anonymized reproduction materials are organized as "
     "MacroRisk_reproduction_anonymized.zip and comprise code, split definitions, the protocol and change log, timing audits, row-level "
     "predictions and labels, archived outputs, Supplementary Tables S1-S17 and the run_all.sh entry script. The BIS REER data used run through "
     "{reer_last_obs}. Public-source forecasting components and archived predictions support parts of the evaluation; full reconstruction of the "
     "historical regressions additionally requires authorized access to the exact licensed inputs. The manuscript's audit history distinguishes "
     "corrected results from superseded outputs.")

APPX("Implementation history and archived extension results")
P("This appendix preserves the superseded implementation for auditability. Its 2023-2025 inner tuning failed {timing_frozen_fail} timing "
  "checks. The estimates below are not primary evidence for forecasting or decision performance; [[tab:ext]] and [[tab:extdiff]] contain the "
  "corrected exploratory results.")
H2("Implementation corrections")
P("An internal code audit after the first draft found two departures from the protocol in Section 4.2. The inner tuning folds used a fixed gap "
  "of three months, shorter than the $h + \\ell$ months required (four for $h = 3$, seven for $h = 6$), and the imputer and scaler were fitted "
  "on the whole training window before the inner split. In addition, the expanding calibration history kept each earlier fold's own event "
  "threshold. A later audit found that the inner tuning labels used the outer-fold threshold, whose estimation sample includes the inner "
  "validation ranges; inner labels now use a threshold estimated on the inner training targets only. These departures were corrected and the "
  "main 2017-2022 learned-model experiments and the corrected extension were rerun; the first-draft outputs are archived in the reproduction "
  "archive. Of {chg_n_keys} audited numbers, {chg_n_changed} differ from the first draft; the largest change in a headline pooled AP is "
  "{chg_ap_max_abs}, and the persistence and country-identity baselines are unchanged. Two conclusions of the first draft changed: the CI x IQ "
  "interaction is no longer equivalent to the additive model in 2021-2022 (90% interval [{bt_m1m0_lock_L6_lo90}, {bt_m1m0_lock_L6_hi90}], "
  "previously [{v1_bt_m1m0_lock_L6_lo90}, {v1_bt_m1m0_lock_L6_hi90}]), and the random forest's gain over B0 is no longer distinguishable from "
  "zero ({bt_b3b0_all_L12} [{bt_b3b0_all_L12_lo}, {bt_b3b0_all_L12_hi}], previously {v1_bt_b3b0_all_L12} [{v1_bt_b3b0_all_L12_lo}, "
  "{v1_bt_b3b0_all_L12_hi}]). The original 2023-2025 extension had already been scored with the earlier tuning code and was not rescored; its "
  "inner tuning folds fail the timing check ({timing_frozen_fail} stage checks), and Sections 5.8-5.9 report the corrected exploratory "
  "extension.")
H2("Recorded protocol and superseded extension")
P("The recorded protocol (SHA-256 {proto_hash12}...) predates scoring of the original extension predictions, but prior audits had examined some "
  "target summaries. Applied once to the retrospective folds, its fallback rule chose {fb_retro}. A scoring-code change needed to read the "
  "protocol file was logged after recording it; the protocol itself was not changed. The protocol hash identifies the file; it does not "
  "independently establish its creation chronology. This record is not an independent preregistration or a prospective test. [[tab:arch]] "
  "reproduces the archived results and [[tab:archdiff]] the archived policy comparisons.")
TBL("arch")
TBL("archdiff")


# Directional statements in the text; the build stops if a rerun reverses one of them.
num = lambda k: float(V[k])
excl0 = lambda k: num(k + "_lo") > 0 or num(k + "_hi") < 0
CLAIMS = {
    "all F statistics reproduced": V["n_f_exact"] == 12,
    "only IQ in M0 over six folds reaches sesoi, interval includes zero": V["n_any_gain_sesoi"] == 1 and num("d_m0_iq_all") >= num("sesoi") and num("e21_m0_iq_all_lo") <= 0,
    "adding CI lowers AP in every cell": V["n_ci_neg"] == 6,
    "eight-month Platt worse for all models": V["n_platt8_worse_all"] == V["n_models_cal"],
    "random forest leads over six folds, then C1, XGBoost, B0": num("b3_all") > num("c1_all") > num("b4_all") > num("b0_all") > max(num("m0_all"), num("m1_all")),
    "random forest best in development folds": num("b3_dev") >= max(num(k) for k in ["b0_dev", "b1_dev", "b2_dev", "b4_dev", "m0_dev", "m1_dev"]),
    "C1 > B0 > other models in 2021-2022": num("c1_lock") > num("b0_lock") > num("max_learned_lock"),
    "no six-fold AP gain over B0 excludes zero": num("bt_b3b0_all_L12_lo") <= 0 and num("bt_b4b0_all_L12_lo") <= 0,
    "M1-M0 equivalence not established": not (num("bt_m1m0_all_L12_lo90") > -num("sesoi") and num("bt_m1m0_all_L12_hi90") < num("sesoi"))
                                         and not (num("bt_m1m0_lock_L6_lo90") > -num("sesoi") and num("bt_m1m0_lock_L6_hi90") < num("sesoi")),
    "C1 leads onset AP in 2021-2022": num("on_c1_lock") > max(num("on_m1_lock"), num("on_b0_lock")),
    "persistence models better on depreciation in 2021-2022": min(num("dep_b0_lock"), num("dep_c1_lock")) > num("dep_m1_lock"),
    "LC beats random for M1 in both windows": num("e15_m1rev_rand_all_hi") < 0 and num("e15_m1rev_rand_lock_hi") < 0,
    "oracle review helps B0": num("e15_b0rev_b0auto_all_hi") < 0,
    "M1+review vs B0+review changes sign": num("e15_m1rev_b0rev_all") * num("e15_m1rev_b0rev_lock") < 0,
    "EL routing beats LC for B0 under oracle review": num("e23_all_perf_b0_el_lc_hi") < 0,
    "EL routing reviews nothing under imperfect review": V["e23_n_el_eq_none"] == V["e23_n_lc_rand"],
    "LC never beats no review under imperfect review": V["e23_n_lc_none_better"] == 0,
    "no robustness contrast favours B0": V["e21_rob_n_neg"] == 0,
    "extension: XGBoost vs B0 not significant over 15": not excl0("pd_all15_b4_b0_ap") and not excl0("pd_all15_b4_b0_cost"),
    "extension: XGBoost beats B0 in Core-9": num("pd_core9_b4_b0_ap_lo") > 0,
    "extension: EBM IQ AP interval includes zero over 15, excludes it only in External-6": not excl0("pd_all15_iq_m0_ap") and not excl0("pd_core9_iq_m0_ap") and num("pd_ext6_iq_m0_ap_lo") > 0,
    "extension: IQ lowers EBM cost": num("pd_all15_iq_m0_cost_hi") < 0,
    "extension: no IQ increment for XGBoost": not excl0("pd_all15_iq_b4_ap"),
    "extension: macro+IQ EBM below B0": num("ph_all15_m0") < num("ph_all15_b0"),
    "extension: refitted fallback keeps B0": all(x.endswith("B0") for x in V["ph_fb_deployed"].split(", ")),
}
bad = [k for k, ok in CLAIMS.items() if not ok]
if bad:
    raise SystemExit("Text claims contradicted by the numbers: " + "; ".join(bad))

# ------------------------------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------------------------------
def f3(x):
    return "" if pd.isna(x) else fmt_num(x, 3)


def f1(x):
    return "" if pd.isna(x) else fmt_num(x, 1)


def s3(x):
    return "" if pd.isna(x) else fmt_num(x, 3, sign=True)


def s1(x):
    return "" if pd.isna(x) else fmt_num(x, 1, sign=True)


MLAB = {"B0_Historical_Rule": "B0 Persistence", "B1_Regularized_Linear": "B1 Ridge / logistic", "B2_Threshold_Model": "B2 Threshold model",
        "B3_Random_Forest": "B3 Random forest", "B4_XGBoost": "B4 XGBoost", "M0_EBM_Additive": "M0 EBM additive", "M1_EBM_CIxIQ": "M1 EBM + CI x IQ",
        "C0_Country_Dummies": "C0 Country identity", "C1_Country_plus_Persistence": "C1 Country + persistence", "Fallback_policy": "Fallback policy",
        "Rule_Never_Alert": "Never alert"}
WA, WL, WD = "All six out-of-time folds 2017-2022", "Retrospective test 2021-2022", "Development folds 2017-2020"
TABLES, SUPP = {}, {}

TABLES["data"] = dict(caption="Samples.", header=["Sample", "Countries", "Period", "N", "CI measure", "Use"], rows=[
    ["Panel A", "CHN, HUN, MEX, POL, RUS, ZAF", "2012-08 to 2021-12", "678", "SWIFT payment share", "Threshold replication"],
    ["Panel B", "Panel A + BRA, IND, KOR", "2012-01 to 2022-12", "1,188", "FX-turnover share", "Threshold replication"],
    ["Core-9", "Panel B countries", "2012-01 to 2022-12", "1,188 origins", "FX share; assumed 1-month lag", "Forecasting, 2017-2022 folds"],
    ["External-6", "CHL, COL, IDN, MYS, THA, TUR", "2012-01 to 2022-12", "792 origins", "none", "Transfer"],
    ["Later evaluation", "Core-9 + External-6", "2023-01 to 2025-12", "540 origins", "none", "Retrospective extension"]],
    notes=f"The Panel B ER_Vol regression uses {V['B_er_n']} observations from {V['B_er_countries']} countries. Training, calibration and test countries of every design and fold are listed in Supplementary Table S17.")

tf = rd("table_folds_samples_events.csv")
TABLES["folds"] = dict(caption="Folds, samples and events (Core-9, h = 3).",
                       header=["Fold", "Role", "Threshold %", "Train origins", "N train (pos.)", "Calibration (pos.)", "N test", "Test pos.", "Episodes"],
                       rows=[[r.split_id[-4:], "development" if r.role == "dev_expanding" else "retrospective", f"{r.threshold_q80:.2f}", r.train_origins,
                              f"{r.n_train} ({r.n_train_pos})", f"{r.n_calib} ({r.n_calib_pos})", str(r.n_test), str(r.n_test_pos), str(r.test_episodes)]
                             for r in tf.itertuples()],
                       notes=f"Thresholds are the 80th percentile of each fold's training targets. The maturity condition applies before the next estimation or evaluation stage; the h = 6 task uses earlier cut-offs (Supplementary Table S16). Episodes are runs of consecutive high-risk origins within each fold (sum {V['n_ep_fold_sum']}); {V['n_ep_cont']} of them continue a run from December of the previous fold, so the pooled event evaluation in Section 5.5 counts {V['n_episodes_all']} episodes ({V['n_episodes_lock']} in 2021-2022). Positives by country are listed in the reproduction archive.")

t2a = rd("table2a_threshold_tests.csv")
trim = rd("tableA3_threshold_trimming.csv")
prt = rd("tableA2_threshold_pseudo_realtime.csv")
ra, rb_ = [], []
for r in t2a.itertuples():
    p15 = trim[(trim.panel == r.panel) & (trim.risk == r.risk) & (trim.trim == 0.15)]["p_boot"].iloc[0]
    pr = prt[(prt.panel == r.panel) & (prt.risk == r.risk)]["p_boot"].iloc[0]
    pn = "A" if r.panel == "A_SWIFT" else "B"
    ra.append([pn, r.risk, str(r.n_obs), f"{r.f_published:.2f}", f"{r.f_stat_tn1_convention:.2f}", f"{r.f_stat:.2f}", f"{r.p_boot:.4f}"])
    rb_.append([pn, r.risk, f"{r.threshold_published:.4f}", f"{r.threshold:.4f}", f"{100 * r.share_obs_regime1:.1f}", f"{p15:.4f}", f"{pr:.4f}"])
TABLES["thresh"] = dict(caption="Replication of the reported threshold tests (threshold variable: IQ).", panels=[
    dict(title="Panel A. Reconstructed statistics", header=["Panel", "Risk", "N", "Reported F", "Matched F, T(N-1)", "Hansen F", "p"], rows=ra),
    dict(title="Panel B. Threshold location and sensitivity", header=["Panel", "Risk", "Reported threshold", "Reconstructed threshold", "Low regime %", "p 15% trim", "p lag adjusted"], rows=rb_)],
    notes=f"p-values from {V['n_boot_thresh']} country-block residual bootstraps under the linear null, (1 + k)/(B + 1). Main specification: 1% trimming, contemporaneous other risks.")

t3 = rd("table3_e03_benchmark_comparison.csv")
e16 = rd("table12_e17_e19_onset_direction.csv")
pa, pb = [], []
for m in ["B0_Historical_Rule", "C0_Country_Dummies", "C1_Country_plus_Persistence", "B1_Regularized_Linear", "B2_Threshold_Model", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
    if m.startswith("C"):
        g = e16[(e16.subset == "All origins") & (e16.model == m)].set_index("evaluation_window")
        a, l = g.loc[WA], g.loc[WL]
        pa.append([MLAB[m], f3(a.AP), f3(a.AP_fold_mean), "", f3(l.AP), f3(l.AP_fold_mean)])
        pb.append([MLAB[m], f3(l.Brier), f1(l.Cost_C5_per100), "raw"])
    else:
        g = t3[t3.model == m].set_index("evaluation_window")
        a, d, l = g.loc[WA], g.loc[WD], g.loc[WL]
        pa.append([MLAB[m], f3(a.AP), f3(a.AP_fold_mean), f3(d.AP), f3(l.AP), f3(l.AP_fold_mean)])
        pb.append([MLAB[m], f3(l.Brier), f1(l.Cost_C5_per100), l.cal_scheme.replace("_", " ")])
TABLES["bench"] = dict(caption="Forecasting benchmark for three-month REER stress (Core-9).", panels=[
    dict(title="Panel A. Ranking performance", header=["Model", "AP all pooled", "AP all mean", "AP dev pooled", "AP retro pooled", "AP retro mean"], rows=pa),
    dict(title="Panel B. Retrospective probability and cost performance", header=["Model", "Brier retro", "Cost retro", "Calibration"], rows=pb)],
    notes=f"'all': six folds, 648 country-months, {V['n_pos_all']} positives; 'dev': 2017-2020; 'retro': 2021-2022, {V['n_test_lock']} country-months, {V['n_pos_lock']} positives. Cost: expected cost per 100 forecasts at C_FN = 5. Calibration: scheme selected on the development folds; C0 and C1 calibration not selected separately (raw shown).")

t4 = rd("table4a_e04_feature_ablation.csv")
t4b = rd("table4b_e05_interaction_ablation.csv")
panels = []
for w, title in [(WA, "Panel A. All six folds"), (WL, "Panel B. Retrospective folds")]:
    rows = []
    for m in ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive"]:
        g = t4[(t4.model == m) & (t4.evaluation_window == w)].set_index("feature_set")
        rows.append([MLAB[m], f3(g.loc["F0_Macro_Only", "AP"])] + [f"{s3(g.loc[f, 'Delta_AP_vs_Macro'])}" for f in ["F1_Macro_plus_CI", "F2_Macro_plus_IQ", "F3_Macro_plus_CI_plus_IQ"]])
    g = t4b[t4b.evaluation_window == w].set_index("interaction_spec")
    for spec, labl in [("M1_EBM_CIxIQ", "M1 CI x IQ pair vs M0"), ("M_Placebo_MacroInter", "Placebo macro pair vs M0"), ("M_Unrestricted_EBM", "Unrestricted EBM vs M0"), ("B1_Linear_CIxIQ", "Linear CI x IQ vs M0")]:
        rows.append([labl, f3(g.loc[spec, "AP"]), "", "", f"{s3(g.loc[spec, 'Delta_AP_vs_M0'])}"])
    panels.append(dict(title=title, header=["Model or specification", "Macro or model AP", "Delta +CI", "Delta +IQ", "Delta +CI+IQ or vs M0"], rows=rows))
TABLES["ablation"] = dict(caption="Contribution of CI, IQ and interactions (pooled AP).", panels=panels,
                          notes=f"Upper rows: AP of the macro-only set and changes from adding CI, IQ or both. Lower rows: AP of the interaction specification and change relative to M0 with all features. Differences are original-sample estimates. The paired 95% block-bootstrap intervals for M1 minus M0 are [{V['bt_m1m0_all_L12_lo']}, {V['bt_m1m0_all_L12_hi']}] over six folds (L = 12) and [{V['bt_m1m0_lock_L6_lo']}, {V['bt_m1m0_lock_L6_hi']}] in 2021-2022 (L = 6). The smallest effect of interest is {V['sesoi']}.")

e21 = rd("table16_e21_paired_intervals.csv")
fa = e21[e21.family == "Feature ablation"]
rows = []
for m in ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive"]:
    for inc in ["+CI vs macro", "+IQ vs macro", "+CI+IQ vs macro"]:
        rr = [MLAB[m], inc.replace(" vs macro", "")]
        for w in [WA, WL]:
            x = fa[(fa.model == m) & (fa.comparison == inc) & (fa.evaluation_window == w)].iloc[0]
            rr += [f"{s3(x.Delta_AP_Point)} [{f3(x.Delta_AP_CI95_Low)}, {f3(x.Delta_AP_CI95_High)}]",
                   "yes" if x.AP_CI95_excludes_plus_SESOI else "no", "yes" if x.AP_equivalent_TOST_90 else "no"]
        rows.append(rr)
TABLES["intervals"] = dict(caption="Paired intervals for the feature-set increments of Table 5 (Delta AP relative to the macro-only set).",
                           header=["Model", "Increment", "All folds Delta [95% CI]", "Excl. +0.02", "TOST", "Retro Delta [95% CI]", "Excl. +0.02", "TOST"],
                           rows=rows, notes=f"Moving-block bootstrap over months, 1,000 replications; L = 12 (all folds, {V['n_pos_all']} positives) and L = 6 (retrospective, {V['n_pos_lock']} positives). 'Excl. +0.02': the 95% interval lies below +{V['sesoi']}. 'TOST': the 90% interval lies within +/-{V['sesoi']}. Intervals for the Core-6 CI measures and for every robustness specification are in the replication package (table16_e21_paired_intervals.csv).")

ep = rd("table13_e18_episode_level.csv")
e22 = rd("table13b_e22_strict_early_warning.csv")
panels = []
for w, title in [(WA, "Panel A. All six folds"), (WL, "Panel B. Retrospective folds")]:
    rows = []
    for m in ["B0_Historical_Rule", "C1_Country_plus_Persistence", "B1_Regularized_Linear", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
        e = ep[(ep.evaluation_window == w) & (ep.model == m)].iloc[0]
        s = e22[(e22.evaluation_window == w) & (e22.model == m)].set_index("alert_rule")
        o = e16[(e16.evaluation_window == w) & (e16.model == m)].set_index("subset")
        rows.append([MLAB[m], f"{100 * e.episode_recall:.0f}", f"{e.false_alarms_per_country_year:.2f}",
                     f"{100 * s.loc['threshold tau = 1/6', 'strict_detection_rate']:.0f}", f"{100 * s.loc['top-2 countries per month', 'strict_detection_rate']:.0f}",
                     f"{s.loc['top-2 countries per month', 'false_alarms_per_country_year']:.2f}",
                     f3(o.loc["Onset (not in stress at origin)", "AP"]), f3(o.loc["Depreciation episodes vs normal", "AP"]), f3(o.loc["Appreciation episodes vs normal", "AP"])])
    panels.append(dict(title=title, header=["Model", "Episode coverage %", "False alarms / country-year", "Strict detection % (tau)", "Strict detection % (top-2)",
                                            "False alarms (top-2)", "Onset AP", "Depr. AP", "Appr. AP"], rows=rows))
TABLES["events"] = dict(caption="Episode coverage, strict early warning, onset and direction results.", panels=panels,
                        notes=f"Coverage and the first false-alarm column use alerts at tau = 1/6 and count alerts issued up to the end of an episode. Strict detection: share of eligible episodes ({V['e22_n_el_all']} all folds, {V['e22_n_el_lock']} retrospective) with an alert in the three origins before the first high-risk origin, at tau = 1/6 or with the top two countries per month. Episodes: {V['n_episodes_all']} (all folds), {V['n_episodes_lock']} (2021-2022). Onset windows: {V['on_npos_all']} (all), {V['on_npos_lock']} (retro). Lead-time distributions and top-1/top-3 quotas are in the replication package.")

cd = rd("table11b_e15_cost_differences.csv")
short = lambda x: x.replace(" (k=2)", "").replace("low-confidence review", "LC review").replace("volatility review", "vol. review").replace("Macro-only EBM", "Macro EBM")
rows = []
for r in cd[cd.reviewer_acc == 1.0].itertuples():
    r8 = cd[(cd.reviewer_acc == 0.8) & (cd.evaluation_window == r.evaluation_window) & (cd.policy_A == r.policy_A) & (cd.policy_B == r.policy_B)].iloc[0]
    rows.append(["all" if r.evaluation_window == WA else "retro", short(r.policy_A), short(r.policy_B), f1(r.cost_A_per100), f1(r.cost_B_per100),
                 f"{s1(r.Delta_cost_per100)} [{f1(r.CI95_Low)}, {f1(r.CI95_High)}]", f"{s1(r8.Delta_cost_per100)} [{f1(r8.CI95_Low)}, {f1(r8.CI95_High)}]"])
TABLES["review"] = dict(caption="Selective-review scenario simulation: expected cost per 100 forecasts and paired differences.",
                        header=["Period", "Policy A", "Policy B", "Cost A", "Cost B", "A - B, accuracy 1.0 [95% CI]", "A - B, accuracy 0.8 [95% CI]"],
                        rows=rows, notes="LC review: least-confident cases (closest to the cost threshold) reviewed first; vol. review: highest lagged volatility first. Two reviews per month (k = 2), review fee 0.5, C_FN = 5. M1 uses its development-selected calibration. Block bootstrap: L = 12 (all), L = 6 (retro). Accuracy 1.0 is an oracle bound. The full grid of policies, routing rules, budgets and fees is in the replication package.")

e23 = pd.read_csv(os.path.join(TAB, "table11c_e23_review_assumptions.csv"), keep_default_na=False)
ea = e23[e23.evaluation_window == WA]
rows = []
for em in ea.error_model.unique():
    for pol in ["B0 persistence", "M1 EBM (locked scheme)", "Macro-only EBM", "B4 XGBoost"]:
        g = ea[(ea.error_model == em) & (ea.automated_policy == pol)]
        cell = lambda a, b: (lambda x: f"{s1(x.Delta_cost_per100)} [{f1(x.CI95_Low)}, {f1(x.CI95_High)}]")(g[(g.routing_A == a) & (g.routing_B == b)].iloc[0])
        rows.append([em.split(" (")[0] if em.startswith(("Perfect", "Confidence")) else em, pol.replace(" (locked scheme)", ""),
                     cell("Low confidence first", "Random"), cell("Expected loss reduction", "Low confidence first"), cell("Low confidence first", "None")])
TABLES["reviewerr"] = dict(caption="Review routing under alternative reviewer-error models (all six folds; cost per 100 forecasts, A - B [95% CI]).",
                           header=["Reviewer-error model", "Automated policy", "LC - random", "Expected-loss - LC", "LC - no review"], rows=rows,
                           notes="Two reviews per month, fee 0.5, C_FN = 5, C_FP = 1. Confidence-dependent: error rate 0.4 exp(-|logit p - logit tau|). Expected-loss routing reviews the cases with the largest positive model-implied reduction in expected loss under the same error model; when no case has a positive reduction it reviews none and equals no review. Random routing is the exact expectation. L = 12. Retrospective results are in the replication package.")

t15 = rd("table15_confirmation_2023_2025.csv")
t15d = rd("table15d_posthoc_confirmation.csv")
ra = []
for m in ["Rule_Never_Alert", "B0_Historical_Rule", "B1_Regularized_Linear", "M0_EBM_Additive", "B4_XGBoost", "Fallback_policy"]:
    rr = [MLAB[m]]
    for g in ["All 15 countries", "Core-9", "External-6"]:
        x = t15[(t15.countries == g) & (t15.window == "2023-2025") & (t15.model == m)].iloc[0]
        rr += [f3(x.AP) if m != "Rule_Never_Alert" else "", f1(x.Cost_C5_per100)]
    ra.append(rr)
PH = [("B0_Historical_Rule|Macro+IQ", "B0 Persistence"), ("C1_Country_plus_Persistence|Macro+IQ", "C1 Country + persistence"),
      ("B1_Regularized_Linear|Macro+IQ", "B1 Ridge / logistic"), ("M0_EBM_Additive|Macro", "Macro EBM (macro only)"),
      ("M0_EBM_Additive|Macro+IQ", "Macro EBM (macro + IQ)"), ("B4_XGBoost|Macro", "B4 XGBoost (macro only)"), ("B4_XGBoost|Macro+IQ", "B4 XGBoost (macro + IQ)"),
      ("Post-hoc fallback rule (frozen settings)", "Fallback rule, refitted"), ("Exploratory multi-candidate monitor", "Multi-candidate monitor (exploratory)")]
rb_ = []
for k, lab in PH:
    rr = [lab]
    for g in ["All 15 countries", "Core-9", "External-6"]:
        x = t15d[(t15d.countries == g) & (t15d.window == "2023-2025") & (t15d.model == k)].iloc[0]
        rr += [f3(x.AP), f1(x.Cost_C5_per100)]
    rb_.append(rr)
hdr = ["Model", "AP (15)", "Cost (15)", "AP (Core-9)", "Cost (Core-9)", "AP (External-6)", "Cost (External-6)"]
TABLES["ext"] = dict(caption="Corrected exploratory extension for forecast origins 2023-2025.", header=hdr, rows=rb_,
    notes=f"{V['conf_all15_npos']} high-risk windows in {V['conf_all15_n']} country-months ({V['conf_core9_npos']} Core-9, {V['conf_ext6_npos']} External-6). AP is pooled; costs are per 100 forecasts at C_FN = 5 using raw probabilities. All models use the pooled 15-country history and corrected tuning. Refitted single-candidate fallback: {V['ph_fb_deployed']}; exploratory monitor: {V['ph_mon_deployed']}. The archived implementation is reported only in Appendix A.")
TABLES["arch"] = dict(caption="Archived 2023-2025 extension before correction of the tuning implementation.", header=hdr, rows=ra,
    notes=f"Historical outputs are reproduced unchanged (scored once; macro and IQ features). The original single-candidate fallback selected B0 in all three years ({V['conf_deployed']}), so it improved neither AP nor cost relative to B0. Its AP exceeded that of the monitored EBM, but its cost was higher ({V['conf_all15_fb_cost']} versus {V['conf_all15_m0_cost']}), so ranking protection did not imply cost protection. These estimates document the analysis history only.")

pe = rd("table15e_posthoc_differences.csv")


def diff_rows(spec):
    out = []
    for comp, lab in spec:
        rr = [lab]
        for g in ["All 15 countries", "Core-9", "External-6"]:
            x = pe[(pe.comparison == comp) & (pe.countries == g) & (pe.metric == "AP")].iloc[0]
            rr.append(f"{s3(x.Delta)} [{f3(x.CI95_Low)}, {f3(x.CI95_High)}]")
        x = pe[(pe.comparison == comp) & (pe.countries == "All 15 countries") & (pe.metric == "Cost_C5_per100")].iloc[0]
        rr.append(f"{s1(x.Delta)} [{f1(x.CI95_Low)}, {f1(x.CI95_High)}]")
        out.append(rr)
    return out


dhdr = ["Comparison", "Delta AP (15)", "Delta AP (Core-9)", "Delta AP (External-6)", "Delta cost (15)"]
TABLES["extdiff"] = dict(caption="Corrected exploratory comparisons for 2023-2025 with paired 95% intervals.", header=dhdr,
    rows=diff_rows([("Macro+IQ vs macro (EBM)", "Macro EBM: +IQ vs macro only"), ("Macro+IQ vs macro (XGBoost)", "XGBoost: +IQ vs macro only"),
                    ("XGBoost vs B0 (corrected tuning)", "Macro+IQ XGBoost vs B0"), ("Macro EBM vs B0 (corrected tuning)", "Macro+IQ EBM vs B0"),
                    ("C1 vs B0", "C1 vs B0"), ("Exploratory monitor vs B0 (corrected tuning)", "Monitor vs B0"),
                    ("Exploratory monitor vs XGBoost (corrected tuning)", "Monitor vs macro+IQ XGBoost")]),
    notes="All rows use corrected exploratory predictions. XGBoost comparisons against B0 or the monitor use macro+IQ features; the +IQ rows compare macro+IQ with macro-only features. The refitted single-candidate fallback selects B0 in all years, so its difference from B0 is identically zero. Moving-block bootstrap over months, L = 6, 1,000 replications. Brier differences and annual policy inputs are in the reproduction archive (table15e, table15f).")
TABLES["archdiff"] = dict(caption="Archived policy comparisons from the superseded implementation.", header=dhdr,
    rows=diff_rows([("Always XGBoost vs frozen fallback", "Always XGBoost vs frozen fallback"), ("Always macro EBM vs frozen fallback", "Always macro EBM vs frozen fallback"),
                    ("Always B1 vs frozen fallback", "Always B1 vs frozen fallback")]),
    notes=f"All rows use the archived predictions of the superseded implementation, with the original fallback equal to B0. The bootstrap reuses the seed of the original scoring, so the AP and cost intervals reproduce the original comparison table (Monte Carlo variation between bootstrap seeds is of the order of 1-2 cost units for these intervals). Protocol SHA-256: {V['proto_hash']}. Corrected comparisons are in Table 11.")

TABLES["rules"] = dict(caption="Conditional design considerations derived from the reported evaluation.", header=["Decision", "Rule", "Evidence"], rows=[
    [fill(x) for x in row] for row in [
        ["Feature set", "Evaluate incremental CI and IQ information against a matched macro baseline with paired intervals", "Main FX-share ablations: 1 of 18 point estimates reaches {sesoi} (IQ in M0: {e21_m0_iq_all} [{e21_m0_iq_all_lo}, {e21_m0_iq_all_hi}]); {e21_n_not_excl_plus} of {e21_n_abl} intervals cannot exclude such a gain; post-hoc 2023-2025 IQ effect for the EBM: AP {pd_all15_iq_m0_ap} [{pd_all15_iq_m0_ap_lo}, {pd_all15_iq_m0_ap_hi}], cost {pd_all15_iq_m0_cost} [{pd_all15_iq_m0_cost_lo}, {pd_all15_iq_m0_cost_hi}]"],
        ["Interaction", "Validate the CI-by-IQ term before retaining it", "M1 - M0: {e05_m1_all}, paired 95% interval [{bt_m1m0_all_L12_lo}, {bt_m1m0_all_L12_hi}]; equivalence within +/-{sesoi} not established"],
        ["Benchmarks", "Include persistence and country identity plus persistence", "Retrospective AP: C1 {c1_lock}; B0 {b0_lock}; highest other multivariable AP {max_learned_lock}"],
        ["Timing", "Document release assumptions; enforce the maturity condition in every nested tuning and calibration stage", "Using month-t REER changes M1 AP from {m1_all} to {spot_m1_all}; {chg_n_changed} of {chg_n_keys} audited numbers changed after the nested-stage corrections"],
        ["Calibration", "Select calibration using earlier out-of-sample predictions relabelled to the current event", "Eight-month Platt worsens Brier in {n_platt8_worse_all} of {n_models_cal} models"],
        ["Analyst review", "Compare routing at explicit fees and reviewer-error rates; distinguish capacity from actual review volume", "LC vs random under oracle review: {e15_m1rev_rand_all} [{e15_m1rev_rand_all_lo}, {e15_m1rev_rand_all_hi}]; fixed imperfect-review scenarios can imply zero review benefit algebraically"],
        ["Fallback", "Evaluate the opportunity cost of the monitored candidate set, not only protection against weak models", "Corrected 2023-2025 fallback selects B0 throughout; macro+IQ XGBoost gains {pd_core9_b4_b0_ap} AP [{pd_core9_b4_b0_ap_lo}, {pd_core9_b4_b0_ap_hi}] in Core-9"],
    ]], notes="Numbers are pooled over six folds unless stated; intervals are 95% paired block-bootstrap intervals.")

# Supplementary tables
t2c = rd("table2c_published_vs_replicated.csv")
SUPP["S1"] = dict(caption="Regime coefficients: reported versus replicated.", header=["Panel", "Risk", "Regime", "Reported (t)", "Replicated", "t cluster", "t conv.", "Classification"],
                  rows=[["A" if r.panel == "A_SWIFT" else "B", r.risk, "low IQ" if r.term == "ci_regime1" else "high IQ", f"{r.coef_published:.4f} ({r.t_published:.2f})",
                         f"{r.coef_replicated:.4f}", f"{r.t_cluster:.2f}", f"{r.t_conventional:.2f}", r.status] for r in t2c.itertuples()],
                  notes="'suspected transcription error': the reported value differs from the replicated one by a digit or a sign; other causes cannot be ruled out without the original code.")
ss = rd("e01b_specification_search.csv")
SUPP["S2"] = dict(caption="Specification search scored against the reported values.", header=["Panel", "Risk", "Series", "Other risks", "Trim", "N", "F T(N-1)", "F rep.", "gamma", "gamma rep."],
                  rows=[[r.panel[0], r.risk, r.y_col, r.other_risks, f"{r.trim:.2f}", str(r.n_obs), f"{r.f_stat_tn1_convention:.2f}", f"{r.f_published:.2f}", f"{r.gamma:.4f}", f"{r.gamma_published:.4f}"] for r in ss.itertuples()], notes="")
SUPP["S3"] = dict(caption="Threshold tests by trimming fraction.", header=["Panel", "Risk", "Trim", "N", "F Hansen", "p", "Threshold", "Low regime %"],
                  rows=[[r.panel[0], r.risk, f"{r.trim:.2f}", str(r.n_obs), f"{r.f_stat:.2f}", f"{r.p_boot:.4f}", f"{r.threshold:.4f}", f"{100 * r.share_obs_regime1:.1f}"] for r in trim.itertuples()], notes="")
SUPP["S4"] = dict(caption="Pseudo-real-time threshold regressions.", header=["Panel", "Risk", "N", "F Hansen", "p", "Threshold", "b low IQ", "t cl.", "b high IQ", "t cl."],
                  rows=[[r.panel[0], r.risk, str(r.n_obs), f"{r.f_stat:.2f}", f"{r.p_boot:.4f}", f"{r.threshold:.4f}", f"{r.coef_regime1:.4f}", f"{r.t_regime1_cluster:.2f}", f"{r.coef_regime2:.4f}", f"{r.t_regime2_cluster:.2f}"] for r in prt.itertuples()],
                  notes="CI lagged one month; IQ and annual controls from their September release.")
wgi = rd("tableA1_threshold_wgi_dimensions.csv")
SUPP["S5"] = dict(caption="Threshold tests with single WGI dimensions.", header=["Panel", "WGI dimension", "Risk", "N", "F", "p", "Threshold"],
                  rows=[[r.panel[0], r.wgi_dimension, r.risk, str(r.n_obs), f"{r.f_stat:.2f}", f"{r.p_boot:.4f}", f"{r.threshold:.4f}"] for r in wgi.itertuples()], notes="")
rob = rd("table8_e11_robustness_matrix.csv")
SUPP["S6"] = dict(caption="Robustness matrix.", header=["Window", "Specification", "Model", "N", "Pos.", "AP pooled", "AP fold mean", "Brier", "Cost"],
                  rows=[["all" if r.evaluation_window == WA else "retro", r.specification, MLAB.get(r.model, r.model), str(r.N), str(r.N_pos), f3(r.AP), f3(r.AP_fold_mean), f3(r.Brier), f1(r.Cost_C5_per100)] for r in rob.itertuples()], notes="")
e10 = rd("e10_subperiod_analysis.csv")
SUPP["S7"] = dict(caption="Sub-periods.", header=["Period", "Model", "N", "Pos.", "AP", "Brier"],
                  rows=[[r.regime_period, MLAB.get(r.model, r.model), str(r.N), str(r.N_pos), f3(r.AP), f3(r.Brier)] for r in e10.itertuples()], notes="")
e13 = rd("table9_e13_external_transfer.csv")
e13 = e13[e13.evaluation_window != WD]
SUPP["S8"] = dict(caption="External transfer to six economies without CI data.", header=["Window", "Regime", "Target", "Model", "N", "Pos.", "AP", "AP fold mean", "Brier"],
                  rows=[["all" if r.evaluation_window == WA else "retro", r.regime.replace("_", " "), "REER" if "reer" in r.target else "reserves", MLAB.get(r.model, r.model), str(r.N), str(r.N_pos), f3(r.AP), f3(r.AP_fold_mean), f3(r.Brier)] for r in e13.itertuples()],
                  notes="Transfer and pooled regimes use the Core-9 training threshold, so they share labels; the pool-specific threshold regime is a sensitivity.")
e14 = rd("table10_e14_adaptive_weighting.csv")
SUPP["S9"] = dict(caption="Training-weight schemes.", header=["Learner", "Scheme", "Dev AP (fold mean)", "Retro AP", "Retro Brier", "Selected"],
                  rows=[[r.learner, r.scheme.replace("_", " "), f3(r.Dev_AP_fold_mean), f3(r.Test_AP), f3(r.Test_Brier), "yes" if r.Selected_on_dev else ""] for r in e14.itertuples()],
                  notes="Equal-country weights coincide with uniform weights because the Core-9 panel is balanced.")
cal = rd("table6_e07_calibration_diagnostics.csv")
SUPP["S10"] = dict(caption="Calibration diagnostics.", header=["Window", "Model", "Locked", "Brier raw", "Brier Platt 8m", "Brier expanding", "ECE raw", "ECE Platt 8m", "ECE expanding"],
                   rows=[[r.evaluation_window.split(" ")[0], MLAB.get(r.model, r.model), r.cal_scheme_locked, f3(r.Brier_raw), f3(r.Brier_platt_8m), f3(r.Brier_platt_expanding), f3(r.ECE_raw), f3(r.ECE_platt_8m), f3(r.ECE_platt_expanding)] for r in cal.itertuples()], notes="")
aud = rd("e01_manuscript_discrepancy_audit.csv")
SUPP["S11"] = dict(caption="Discrepancies identified in the original drafts.", header=["ID", "Category", "Finding", "Resolution"],
                   rows=[[r.issue_id, r.category, r.root_cause_identified, r.reconstructed_resolution] for r in aud.itertuples()], notes="")
dd = pd.read_csv(os.path.join(OUTD, "data_dictionary.csv"))
SUPP["S12"] = dict(caption="Feature and target dictionary.", header=["Series", "Source", "Frequency", "Publication lag rule", "Description"],
                   rows=[[r.series_id, r.source, r.native_frequency, r.publication_lag_rule, r.description] for r in dd.itertuples()], notes="")
SUPP["S13"] = dict(caption="Hyperparameter grids, seeds and software.", header=["Item", "Setting"], rows=[
    ["B1", "Ridge alpha in {0.5, 2, 5, 15, 50}; logistic C in {0.05, 0.1, 0.3, 1, 3}"],
    ["B3", "100 trees; (depth, min leaf, max features) in {(3,12,sqrt), (4,8,sqrt), (5,6,0.5), (6,10,0.6)}"],
    ["B4", "Four configurations: depth 2-4, learning rate 0.03-0.05, 80-110 trees, subsample 0.75-0.85, lambda 5-12"],
    ["M0/M1", "learning rate in {0.01, 0.02, 0.03}, rounds 50-600, min leaf 8-20, max leaves 2-3; 32 bins, 2 outer bags"],
    ["Tuning", "AP on three inner expanding folds within the training window; each inner training range ends at least h + 1 months before its validation range; median imputation and scaling fitted on the inner training range; inner event labels from the 80th percentile of the inner training targets"],
    ["Seeds", "42, 1024, 2024, 3407, 7777 (probabilities averaged for B3, B4 and EBMs)"],
    ["Bootstrap", f"threshold tests B = {V['n_boot_thresh']}; moving-block bootstrap 1,000 replications"],
    ["Software", "Python 3.12, scikit-learn 1.9.1, xgboost 3.4.1, interpret 0.7.8, numpy 1.26.4, pandas 3.0.6, scipy 1.17.1"]], notes="")
dc = rd("table14_e20_ci_decomposition.csv")
SUPP["S14"] = dict(caption="Within/between decomposition of the FX share.", header=["Window", "Variant", "Model", "AP pooled", "AP fold mean", "Brier", "Cost"],
                   rows=[["all" if r.evaluation_window == WA else "retro", r.variant.replace("_", " "), MLAB.get(r.model, r.model), f3(r.AP), f3(r.AP_fold_mean), f3(r.Brier), f1(r.Cost_C5_per100)] for r in dc.itertuples()], notes="")
WIND_COLS = [
    ("货币", "Currency", "identifier"), ("date", "Month", "identifier"), ("国家 / country", "Country", "identifier"),
    ("SWIFT交易份额", "Share of the currency in SWIFT payments (%)", "CI, Panel A"),
    ("本国货币外汇衍生品交易额", "Domestic-currency FX-derivatives turnover (share)", "CI, Panel B"),
    ("未偿余额", "Outstanding balance (literal translation)", "not used"), ("公布发行额", "Announced issuance amount (literal translation)", "not used"),
    ("对外贷款", "External lending (literal translation)", "not used"), ("外汇储备总额", "Total FX reserves", "not used"),
    ("新兴国家 / 收入组别", "Emerging-market flag / income group", "not used"),
    ("cpi_vol, fxr_vol, consump_volnew, real_ex_vol, credit_gdp_gap, unemp", "Risk indicators CPI_Vol, FX_Vol, CE_Vol, ER_Vol, CG_Gap, Unemp", "dependent variables / other risks"),
    ("consump_vol, ex_vol", "Alternative CE_Vol and ER_Vol series", "specification search"),
    ("*_lag1", "Six-month lagged risk indicators", "lagged dependent variable"),
    ("pergdp_ppp, gdp_grow, pop, stockvalue_gdp, fin_open1, tra", "GDP per capita (PPP), GDP growth, population, financial depth, financial openness, trade openness", "controls"),
    ("gdp_gvol, cpi, tra_ad, ka_open, IFS_Code, year", "Other macro series and identifiers", "not used"),
    ("VoiceandAccountability ... ControlofCorruption", "Six WGI dimensions", "threshold variable (single dimensions)"),
    ("ins_quality", "Mean of the six WGI dimensions (IQ)", "threshold variable"),
]
SUPP["S15"] = dict(caption="Variables of the original regression datasets (compiled on 13 June 2023).", header=["Column name(s)", "Content", "Use in this study"],
                   rows=[list(r) for r in WIND_COLS],
                   notes="Files: reg_swiftnew_20230613.xlsx (Panel A) and reg_fxshare_20230613.xlsx (Panel B); creation date from the file metadata; SHA-256 checksums in the reproduction archive. Sources stated in the working-paper drafts: SWIFT monthly reports (SWIFT share), BIS and World Bank (FX-turnover share), World Bank and Wind (other macro series); quarterly GDP backward-filled to months. The Wind series codes, the definition of the turnover share and any interpolation were not retained, so the construction of the CI series cannot be verified. The Panel B CI column varies from month to month in every country (Russia has runs of zeros).")
ta = rd("tableS16_timing_audit.csv")
SUPP["S16"] = dict(caption="Timing audit of every estimation stage.", header=["Scope", "Fold", "h", "Stage", "Last origin", "Target published", "First evaluated month", "Event threshold from", "Passes"],
                   rows=[[r.scope, r.split_id, str(r.h), r.stage, r.last_origin, r.target_published, r.first_evaluated_month, r.event_threshold_from, "yes" if r.published_before else "no"] for r in ta.itertuples()],
                   notes="A stage passes when the target of its last origin (origin + h + 1-month REER release lag) is published before the first month it is evaluated on. 'Event threshold from' names the targets whose 80th percentile defines the labels of the stage. The frozen confirmation rows document the inner tuning folds of the original code (fixed three-month gap, outer-fold threshold), which were corrected after scoring; the original extension was not rescored (Section 4.5 and Appendix A).")
s17 = rd("tableS17_countries_by_fold.csv")
SUPP["S17"] = dict(caption="Training, calibration and test countries by design and fold.", header=["Design", "Fold", "Train countries", "Train origins", "Calibration origins", "Test countries", "Test origins", "Threshold"],
                   rows=[[r.design, r.split_id, r.train_countries, r.train_origins, r.calibration_origins, r.test_countries, r.test_origins, r.threshold] for r in s17.itertuples()],
                   notes="Calibration countries equal the training countries in every design. Origin ranges are truncated to the h = 3 maturity cap. Because the 2023-2025 designs train on all 15 countries, External-6 is evaluated out of time but is not an unseen-country transfer; the E13 Transfer_Core9_only regime is the only unseen-country design.")
SUPP_FIGS = {"S1": ("fig6_e14_adaptive_weighting", "Training-weight schemes: development-fold mean AP and retrospective AP.")}

FIGS = {
    "fig1": ("fig1_timeline_protocol", "Information set at the forecast origin (a) and expanding-window folds (b)."),
    "fig2": ("fig2_data_coverage_stress_windows", "High-risk windows in the Core-9 panel (a) and pseudo-real-time institutional quality (b). In the test years the evaluation labels of each fold are shown; before 2017 the first-fold threshold is used for illustration."),
    "fig8": ("fig8_threshold_replication", "Replicated versus reported threshold F statistics (a) and bootstrap p-values under 1% trimming, 15% trimming and the pseudo-real-time specification (b)."),
    "fig3": ("fig3_model_comparison_bootstrap_ci", "(a) Pooled AP in the development and retrospective folds with fold-mean AP marked; dotted lines give the base rates. (b) Pooled AP over six folds by feature set. (c) Paired block-bootstrap intervals (L = 12) for M1 against each benchmark over six folds; the shaded band is the smallest effect of interest."),
    "fig5": ("fig5_ci_iq_interaction_explainability", "EBM CI x IQ surface with sparse cells masked (a), CI response at three IQ levels with fold variability (b) and raw M1 probabilities with high-risk labels for four countries (c)."),
    "fig4": ("fig4_calibration_and_decision_cost", "Reliability of M1 under three calibration schemes and of B0 in the retrospective test (a), expected cost under asymmetric losses over six folds (b) and recall under monthly review quotas over six folds (c)."),
    "fig7": ("fig7_e15_risk_workload", "Expected cost against the share of cases reviewed (six folds, review fee 0.5) for selected automated policies and routing rules, with reviewer accuracy 1.0 (a, upper bound) and 0.8 (b)."),
}
FIG_NUM, TAB_NUM = {}, {}
n_main = n_app = 0
in_app = False
for it in S:
    if it[0] == "appendix":
        in_app = True
    if it[0] == "fig":
        FIG_NUM.setdefault(it[1], len(FIG_NUM) + 1)
    if it[0] == "table" and it[1] not in TAB_NUM:
        if in_app:
            n_app += 1
            TAB_NUM[it[1]] = f"A{n_app}"
        else:
            n_main += 1
            TAB_NUM[it[1]] = n_main

# ------------------------------------------------------------------------------------------
# Renderers
# ------------------------------------------------------------------------------------------
CITE_RE = re.compile(r"\[([a-z]+\d{4}(?:; [a-z]+\d{4})*)\]")


def refs_plain(t):
    t = re.sub(r"\[\[fig:(\w+)\]\]", lambda m: f"Fig. {FIG_NUM[m.group(1)]}", t)
    t = re.sub(r"\[\[tab:(\w+)\]\]", lambda m: f"Table {TAB_NUM[m.group(1)]}", t)
    return CITE_RE.sub(lambda m: "(" + "; ".join(REFS[k][0] for k in m.group(1).split("; ")) + ")", t)


def tex_text(t):
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")]:
        t = t.replace(a, b)
    return re.sub(r"(?<=\w) x (?=\w)", r" $\\times$ ", t)


def to_tex(t):
    out = []
    for p in re.split(r"(\$[^$]*\$)", t):
        if p.startswith("$") and p.endswith("$") and len(p) > 1:
            out.append(p)
            continue
        p = CITE_RE.sub(lambda m: "\x00citep{" + m.group(1).replace("; ", ",") + "}\x00", p)
        p = re.sub(r"\[\[fig:(\w+)\]\]", lambda m: "\x00Fig.~\\ref{fig:" + m.group(1) + "}\x00", p)
        p = re.sub(r"\[\[tab:(\w+)\]\]", lambda m: "\x00Table~\\ref{tab:" + m.group(1) + "}\x00", p)
        segs = p.split("\x00")
        out.append("".join(s.replace("citep{", "\\citep{", 1) if s.startswith("citep{") else (s if s.startswith(("Fig.~", "Table~")) else tex_text(s)) for s in segs))
    return "".join(out)


def to_md(t):
    t = refs_plain(t)
    return re.sub(r"(?<=\w) x (?=\w)", " × ", t)


def tex_panels(tb, label):
    wide = any(len(p["header"]) > 6 for p in tb["panels"])
    env = "table*" if wide else "table"
    lines = [f"\\begin{{{env}}}[!htbp]", "\\centering", "\\scriptsize", "\\setlength{\\tabcolsep}{3pt}",
             f"\\caption{{{tex_text(tb['caption'])}}}", f"\\label{{tab:{label}}}"]
    for p in tb["panels"]:
        ncol = len(p["header"])
        spec = "l" * min(2, ncol) + "r" * max(0, ncol - 2)
        body = [f"\\begin{{tabular}}{{{spec}}}", "\\toprule", " & ".join(tex_text(h) for h in p["header"]) + " \\\\", "\\midrule"]
        body += [" & ".join(tex_text(str(c)) for c in r) + " \\\\" for r in p["rows"]] + ["\\bottomrule", "\\end{tabular}"]
        lines += [f"\\par\\smallskip{{\\textit{{{tex_text(p['title'])}}}}}\\par\\smallskip"]
        lines += ["\\begin{adjustbox}{max width=\\textwidth}"] + body + ["\\end{adjustbox}"]
    if tb.get("notes"):
        lines.append(f"\\par\\vspace{{2pt}}\\parbox{{0.95\\linewidth}}{{\\scriptsize Note: {tex_text(tb['notes'])}}}")
    lines.append(f"\\end{{{env}}}")
    return "\n".join(lines)


def tex_table(tb, label, num_prefix=""):
    if "panels" in tb:
        return tex_panels(tb, label)
    ncol = len(tb["header"])
    wide = ncol > 6 or label in ("rules", "S11", "S12")
    env = "table*" if wide else "table"
    if label in ("rules", "S11", "S12"):
        spec = "p{0.16\\linewidth}" + "p{0.38\\linewidth}" * (ncol - 2) + "p{0.38\\linewidth}" if label == "rules" else "l" + "p{0.2\\linewidth}" * (ncol - 1)
    else:
        spec = "l" * min(3, ncol) + "r" * max(0, ncol - 3)
    long = len(tb["rows"]) > 40
    lines = [f"\\begin{{{env}}}[!htbp]" if not long else "", "\\centering" if not long else "", "\\scriptsize", "\\setlength{\\tabcolsep}{3pt}"]
    if long:
        lines += [f"\\begin{{longtable}}{{{spec}}}", f"\\caption{{{tex_text(tb['caption'])}}}\\label{{tab:{label}}}\\\\", "\\toprule",
                  " & ".join(tex_text(h) for h in tb["header"]) + " \\\\", "\\midrule\\endhead"]
    else:
        lines += [f"\\caption{{{tex_text(tb['caption'])}}}", f"\\label{{tab:{label}}}", f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
                  " & ".join(tex_text(h) for h in tb["header"]) + " \\\\", "\\midrule"]
    lines += [" & ".join(tex_text(str(c)) for c in r) + " \\\\" for r in tb["rows"]]
    lines += ["\\bottomrule"]
    if long:
        lines += ["\\end{longtable}"]
        if tb.get("notes"):
            lines.append(f"{{\\scriptsize Note: {tex_text(tb['notes'])}}}")
    else:
        lines += ["\\end{tabular}"]
        if wide:
            lines.insert(lines.index(f"\\begin{{tabular}}{{{spec}}}"), "\\begin{adjustbox}{max width=\\textwidth}")
            lines.append("\\end{adjustbox}")
        if tb.get("notes"):
            lines.append(f"\\par\\vspace{{2pt}}\\parbox{{0.95\\linewidth}}{{\\scriptsize Note: {tex_text(tb['notes'])}}}")
        lines.append(f"\\end{{{env}}}")
    return "\n".join(x for x in lines if x)


def md_table(tb, title):
    esc = lambda s: str(s).replace("|", "/").replace("\n", " ")
    lines = [f"**{title}**", ""]
    for p in tb.get("panels", [dict(title=None, header=tb.get("header"), rows=tb.get("rows"))]):
        if p["title"]:
            lines += [f"*{p['title']}*", ""]
        lines += ["| " + " | ".join(esc(h) for h in p["header"]) + " |", "|" + "---|" * len(p["header"])]
        lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in p["rows"]] + [""]
    if tb.get("notes"):
        lines += ["", f"*Note:* {tb['notes']}"]
    return "\n".join(lines) + "\n"


def used_refs():
    txt = " ".join(it[1] if it[0] == "p" else " ".join(it[1]) for it in S if it[0] in ("p", "bul"))
    return sorted({k for m in CITE_RE.finditer(txt) for k in m.group(1).split("; ")}, key=lambda k: REFS[k][1])


def build_tex(preview=False):
    used = used_refs()
    cls = r"\documentclass[12pt]{article}" + "\n" + r"\usepackage[authoryear,round]{natbib}" if preview else r"\documentclass[preprint,12pt,authoryear]{elsarticle}"
    L = [cls, r"\usepackage[utf8]{inputenc}", r"\usepackage[T1]{fontenc}", r"\usepackage{amsmath,amssymb,graphicx,booktabs,longtable,adjustbox}",
         r"\usepackage[margin=1in]{geometry}", r"\usepackage{hyperref}"]
    if not preview:
        L += [r"\journal{Expert Systems with Applications}"]
    L += [r"\begin{document}"]
    if preview:
        L += [f"\\title{{{tex_text(TITLE)}}}", r"\date{}", r"\maketitle", r"\begin{abstract}", tex_text(ABSTRACT), r"\end{abstract}",
              r"\noindent\textbf{Keywords:} " + "; ".join(KEYWORDS)]
    else:
        L += [r"\begin{frontmatter}", f"\\title{{{tex_text(TITLE)}}}", r"\begin{abstract}", tex_text(ABSTRACT), r"\end{abstract}",
              r"\begin{highlights}"] + [f"\\item {tex_text(h)}" for h in HIGHLIGHTS] + [r"\end{highlights}", r"\begin{keyword}", " \\sep ".join(KEYWORDS), r"\end{keyword}", r"\end{frontmatter}"]
    for it in S:
        k = it[0]
        if k == "h1":
            L.append(f"\\section{{{tex_text(it[1])}}}")
        elif k == "h2":
            L.append(f"\\subsection{{{tex_text(it[1])}}}")
        elif k == "appendix":
            L += [r"\appendix", f"\\section{{{tex_text(it[1])}}}", r"\setcounter{table}{0}\renewcommand{\thetable}{A\arabic{table}}",
                  r"\renewcommand{\thesubsection}{A\arabic{subsection}}"]
        elif k == "data":
            L += [r"\section*{Data availability}", to_tex(it[1]) + "\n"]
        elif k == "p":
            L.append(to_tex(it[1]) + "\n")
        elif k == "bul":
            L += ["\\begin{itemize}"] + [f"\\item {to_tex(i)}" for i in it[1]] + ["\\end{itemize}"]
        elif k == "eq":
            L.append(f"\\begin{{equation}}\\label{{{it[2]}}}\n{it[1]}\n\\end{{equation}}")
        elif k == "table":
            L.append(tex_table(TABLES[it[1]], it[1]))
        elif k == "fig":
            fn, cap = FIGS[it[1]]
            L.append(f"\\begin{{figure*}}[!htbp]\\centering\\includegraphics[width=\\textwidth]{{figures/Fig{FIG_NUM[it[1]]}.pdf}}"
                     f"\\caption{{{to_tex(cap)}}}\\label{{fig:{it[1]}}}\\end{{figure*}}")
    L.append(r"\begin{thebibliography}{99}")
    for k in used:
        au, yr = REFS[k][0].rsplit(",", 1)
        L.append(f"\\bibitem[{tex_text(au).replace(' et al.', ' et~al.')}({yr.strip()})]{{{k}}} {tex_text(REFS[k][1])}")
    L += [r"\end{thebibliography}", r"\end{document}"]
    return "\n".join(L)


def build_md():
    out = [f"# {TITLE}", "", "## Abstract", "", ABSTRACT, "", "**Keywords:** " + "; ".join(KEYWORDS), ""]
    sec = sub = 0
    app = False
    for it in S:
        k = it[0]
        if k == "h1":
            sec += 1; sub = 0
            out.append(f"\n## {sec}. {it[1]}\n")
        elif k == "h2":
            sub += 1
            out.append(f"\n### {'A' if app else str(sec) + '.'}{sub}. {it[1]}\n")
        elif k == "appendix":
            app, sub = True, 0
            out.append(f"\n## Appendix A. {it[1]}\n")
        elif k == "data":
            out += ["\n## Data availability\n", to_md(it[1]) + "\n"]
        elif k == "p":
            out.append(to_md(it[1]) + "\n")
        elif k == "bul":
            out += [f"- {to_md(i)}" for i in it[1]] + [""]
        elif k == "eq":
            out.append(f"$$\n{it[1]}\n$$\n")
        elif k == "table":
            out.append(md_table(TABLES[it[1]], f"Table {TAB_NUM[it[1]]}. {TABLES[it[1]]['caption']}"))
        elif k == "fig":
            fn, cap = FIGS[it[1]]
            out.append(f"![Fig. {FIG_NUM[it[1]]}. {to_md(cap)}](figures/Fig{FIG_NUM[it[1]]}.png){{width=100%}}\n")
    out += ["\n## References\n"]
    out += [REFS[k][1] + "\n" for k in used_refs()]
    return "\n".join(out)


def build_supp_md():
    out = ["# Supplementary material", "", f"*{TITLE}*", ""]
    for k, tb in SUPP.items():
        out.append(md_table(tb, f"Table {k}. {tb['caption']}"))
    for k, (fn, cap) in SUPP_FIGS.items():
        out.append(f"![Fig. {k}. {cap}](figures/Fig{k}.png){{width=100%}}\n")
    out += ["## Changes between the first draft and this version", "",
            fill("The inner tuning folds (maturity gap, preprocessing and event threshold) and the expanding calibration history were corrected after the first draft (Section 4.5 and Appendix A of the manuscript). "
                 "Of {chg_n_keys} audited numbers, {chg_n_changed} changed; the persistence and country-identity baselines are unchanged. Every audited "
                 "number of both versions is listed in table_change_v1_v2.csv of the replication package, and the first-draft outputs are archived in "
                 "outputs/archive_v1."), ""]
    out += ["## Post-freeze change log of the confirmation protocol", "", "```",
            open(os.path.join(OUTD, "confirmation", "post_freeze_changes.log")).read().strip(), "```", ""]
    return "\n".join(out)


def md_to_docx(md, path):
    pypandoc.convert_text(md, "docx", format="markdown+pipe_tables+tex_math_dollars", outputfile=path, extra_args=[f"--resource-path={OUT}"])


def title_page_md():
    return "\n".join([f"# {TITLE}", "", "**Renda Shi**^a,\\*^ and **Mengxia Xu**^b^", "",
                      "^a^ School of Management and Economics, The Chinese University of Hong Kong, Shenzhen, Shenzhen, China  ",
                      "^b^ Shanghai Advanced Institute of Finance, Shanghai Jiao Tong University, Shanghai, China", "",
                      "\\* Corresponding author: Renda Shi, renshi@cuhk.edu.cn", "",
                      "E-mail addresses: renshi@cuhk.edu.cn (R. Shi), mxxu.21@saif.sjtu.edu.cn (M. Xu)", "",
                      "## Declarations", "",
                      "**CRediT authorship contribution statement.** [To be completed by the authors.]", "",
                      "**Declaration of competing interest.** [To be completed and confirmed by the authors.]", "",
                      "**Funding.** [To be completed by the authors.]", "",
                      "**Acknowledgements.** [To be completed by the authors.]", "",
                      "**Data availability.** BIS, IMF and World Bank data are public. The regression datasets of the original working paper were compiled on 13 June 2023 from SWIFT reports, BIS, World Bank and Wind series (variables documented by column name in Supplementary Table S15; the original Wind series codes were not retained); Wind data are licensed and cannot be redistributed. Code, split definitions, the frozen confirmation protocol and all row-level predictions are available at https://github.com/reneverland/MacroRisk.", "",
                      "**Original study.** The threshold estimates replicated in this paper come from an earlier working paper involving the second author, 'Does Currency Internationalization increase Macro Risk in Emerging Markets? Nonlinear Evidence from Institutional Quality' (drafts dated November 2023 to July 2025), which was neither submitted nor published.", "",
                      "**Declaration of generative AI and AI-assisted technologies in the writing process.** [Draft for the authors to confirm or edit:] During the preparation of this work the authors used an AI coding and writing assistant to write and audit analysis scripts, run consistency checks and draft and revise parts of the text. After using this tool, the authors reviewed and edited the content as needed and take full responsibility for the content of the publication.", ""])


def author_responses_md():
    sums = dict(reversed(l.split()) for l in open(os.path.join(BASE_DIR, "data", "raw", "historylab", "SHA256SUMS.txt")) if l.strip())
    R = lambda t: fill(t)
    return "\n".join([
        "# Responses to the AUTHOR CHECK comments (revision of 20 October 2026)", "",
        "Not for submission. Every number below is read from outputs/manuscript_numbers.json, which the consistency audit "
        "(step8_consistency_audit.py, status PASS) recomputes from the row-level predictions.", "",
        "## 1. Working paper and data provenance", "",
        "- Versions: long draft, file created 15 November 2023 and last revised 14 October 2024; shortened draft dated 23 July 2025. Both report "
        "the threshold estimates replicated in the manuscript; Supplementary Table S11 maps every discrepancy found in them.",
        "- Sources stated in the drafts: SWIFT monthly reports (SWIFT share), BIS and World Bank (FX-turnover share), World Bank and Wind (other "
        "macro series); quarterly GDP backward-filled to months.",
        f"- Files: reg_fxshare_20230613.xlsx (SHA-256 {sums['reg_fxshare_20230613.xlsx']}) and reg_swiftnew_20230613.xlsx "
        f"(SHA-256 {sums['reg_swiftnew_20230613.xlsx']}), compiled 13 June 2023 (file metadata).",
        "- Not recoverable: the Wind series codes, the exact turnover definition and any interpolation. The Panel B CI column (labelled "
        "domestic-currency FX-derivatives turnover) varies monthly in every country (Russia has runs of zeros), so it is not a step-filled "
        "triennial survey value, but its construction is stated as unverified (Sections 3.1, 6.3; Table S15).", "",
        "## 2. Episode counts (34 vs 31)", "",
        R("- Table 2 counts runs of consecutive high-risk origins within each fold: sum {n_ep_fold_sum}. {n_ep_cont} of these runs continue from "
          "December of the previous fold. The pooled event evaluation joins them, giving {n_episodes_all} episodes; in 2021-2022, "
          "{n_ep_fold_sum_lock} fold-level runs minus {n_ep_cont_lock} continuation give {n_episodes_lock}. The audit checks both identities."),
        "- The figure of 34 in the previous draft came from a different rule (runs separated by a two-month cool-down, counted within folds). "
        "All counts now use the contiguous-run rule; Section 4.7 and the Table 2 note state the merging rule.", "",
        "## 3. M1 - M0 (-0.006 vs -0.005) and intervals shown as -0.000", "",
        R("- Unrounded six-fold M1 - M0 = {m1m0_all_unrounded} after the inner-threshold correction (-0.00553 before it). Table 5 and the bootstrap table report the same original-sample estimate (audit "
          "check); the earlier -0.005 arose from rounding an already rounded difference. Tables now store 6-8 decimals and are formatted once."),
        R("- The bootstrap supplies intervals only; the text no longer reports a bootstrap centre. Six folds [{bt_m1m0_all_L12_lo}, "
          "{bt_m1m0_all_L12_hi}], 2021-2022 [{bt_m1m0_lock_L6_lo}, {bt_m1m0_lock_L6_hi}]. A nonzero limit that would round to zero is printed "
          "with more digits."), "",
        "## 4. Inner-fold thresholds, stage audit and final-period data", "",
        "- Inner tuning labels previously used the outer-fold threshold, whose estimation sample includes the inner validation ranges. Each inner "
        "fold now uses the 80th percentile of its own training targets (country-specific and reference-subset rules analogously). Steps 3-6b and "
        "the corrected extension (step 10) were rerun; the change is disclosed in Section 4.5 and Appendix A1.",
        R("- Supplementary Table S16 adds the column 'Event threshold from' for every stage; all {timing_n_checked} checks of the main and "
          "corrected runs pass, and the {timing_frozen_fail} failures of the archived run are listed."),
        R("- REER data run through {reer_last_obs} for all 15 economies. The last origin {ext_last_origin} needs outcomes through 2026-03, "
          "published under the one-month lag in {ext_outcome_to}; all 15 targets are observed (audit check)."),
        "- S1-S17 are in Supplementary_Material.docx; S12-S17 are regenerated from the corrected outputs.", "",
        "## 5. Expanding calibration: scores or labels?", "",
        "- Only the labels are recomputed with the current fold's threshold; the historical scores are the stored out-of-sample predictions and "
        "are not regenerated. Section 4.4 states the score-transfer assumption and Section 6.3 lists it as a limitation.", "",
        "## 6. Why the macro EBM is the single monitored candidate", "",
        R("- The protocol fixes the candidate as the highest development-fold mean AP among B1, the macro EBM and XGBoost with macro + IQ "
          "features: {fb_dev_ap_m0} (EBM), {fb_dev_ap_b4} (XGBoost), {fb_dev_ap_b1} (B1), a near tie (margin {fb_dev_margin}); Section 4.9 now "
          "says so."),
        "- The fallback compares the macro + IQ EBM with B0, as the protocol specifies. The exploratory monitor considers every refitted model other "
        "than B0 (C1, B1 and the macro-only and macro + IQ EBMs and XGBoost models). Both use the latest twelve matured origins, up to August of "
        "T-1, whose targets are published by December.", "",
        "## 7. Submission package", "",
        "- MacroRisk_reproduction_anonymized.zip (code, splits, protocol, timing audit, row-level predictions, S1-S17) is rebuilt with this "
        "revision. The manuscript is generated from code, so the editorial comments are not carried over. Title_Page.docx is separate; the "
        "declarations and the anonymous mirror link still need the authors.", "",
        "## 8. Archived XGBoost cost interval", "",
        R("- The archived comparison is [{cd_all15_b4_cost_lo}, {cd_all15_b4_cost_hi}] from the original scoring. The alternative [-29.6, 3.3] "
          "came from recomputing the same comparison with a different bootstrap seed. Step 10 now reuses the original seed for archived "
          "comparisons, and the audit checks that Table A2 reproduces the original table."), "",
        "## 9. Fig. 4", "",
        "- Panel (a) legend moved below the bars, outside the plotting area, font size 10.5.", "",
        "## Results that changed with the inner-threshold correction", "",
        R("- 2023-2025, macro EBM +IQ: AP {pd_all15_iq_m0_ap} [{pd_all15_iq_m0_ap_lo}, {pd_all15_iq_m0_ap_hi}] over 15 countries (previously "
          "+0.029 [0.002, 0.042]); expected cost {pd_all15_iq_m0_cost} [{pd_all15_iq_m0_cost_lo}, {pd_all15_iq_m0_cost_hi}]. The abstract, "
          "Section 5.9, Table 12 and the conclusion now describe a cost reduction with an AP interval that includes zero."),
        R("- Macro+IQ XGBoost vs B0 in Core-9: {pd_core9_b4_b0_ap} [{pd_core9_b4_b0_ap_lo}, {pd_core9_b4_b0_ap_hi}]; over 15 countries "
          "{pd_all15_b4_b0_ap} [{pd_all15_b4_b0_ap_lo}, {pd_all15_b4_b0_ap_hi}]. The exploratory monitor {ph_mon_switch}."),
        R("- Main FX-share ablation: IQ in M0 over six folds is now {e21_m0_iq_all} [{e21_m0_iq_all_lo}, {e21_m0_iq_all_hi}], the only one of 18 "
          "additions to reach the {sesoi} margin in point estimate (previously none). M1 - M0 is {e05_m1_all}; {e21_n_not_excl_plus} of 18 "
          "intervals cannot exclude a {sesoi} gain (previously 9). The abstract, a highlight, Sections 1, 5.4, 6.1 and 7 and Table 12 were "
          "reworded accordingly; the build stops if any stated direction is contradicted by the numbers."),
        R("- Of {chg_n_keys} audited numbers, {chg_n_changed} differ from the first draft (table_change_v1_v2.csv)."), ""])


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(OUT, "figures"))
    for k, (fn, _) in FIGS.items():
        for ext in ["pdf", "png"]:
            shutil.copy(os.path.join(FIG, f"{fn}.{ext}"), os.path.join(OUT, "figures", f"Fig{FIG_NUM[k]}.{ext}"))
    for k, (fn, _) in SUPP_FIGS.items():
        for ext in ["pdf", "png"]:
            shutil.copy(os.path.join(FIG, f"{fn}.{ext}"), os.path.join(OUT, "figures", f"Fig{k}.{ext}"))
    tex = build_tex()
    assert not re.search(r"\{[a-z][a-z0-9_]*_(all|lock|lo|hi)\}", tex), "unfilled number token"
    open(os.path.join(OUT, "ESWA_Manuscript_anonymized.tex"), "w", encoding="utf-8").write(tex)
    prev = build_tex(preview=True)
    open(os.path.join(OUT, "preview.tex"), "w", encoding="utf-8").write(prev)
    for _ in range(2):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "preview.tex"], cwd=OUT, capture_output=True, text=True)
    if r.returncode == 0:
        os.replace(os.path.join(OUT, "preview.pdf"), os.path.join(OUT, "ESWA_Manuscript_anonymized_preview.pdf"))
    else:
        print("pdflatex preview failed:\n", r.stdout[-3000:])
    for f in os.listdir(OUT):
        if f.startswith("preview."):
            os.remove(os.path.join(OUT, f))
    md = build_md()
    open(os.path.join(OUT, "ESWA_Manuscript_anonymized.md"), "w", encoding="utf-8").write(md)
    md_to_docx(md, os.path.join(OUT, "ESWA_Manuscript_anonymized.docx"))
    supp = build_supp_md()
    open(os.path.join(OUT, "Supplementary_Material.md"), "w", encoding="utf-8").write(supp)
    md_to_docx(supp, os.path.join(OUT, "Supplementary_Material.docx"))
    md_to_docx(title_page_md(), os.path.join(OUT, "Title_Page.docx"))
    resp = author_responses_md()
    open(os.path.join(OUT, "Author_Check_Responses.md"), "w", encoding="utf-8").write(resp)
    md_to_docx(resp, os.path.join(OUT, "Author_Check_Responses.docx"))
    for h in HIGHLIGHTS:
        assert len(h) <= 85, (len(h), h)
    open(os.path.join(OUT, "highlights.txt"), "w", encoding="utf-8").write("\n".join(HIGHLIGHTS) + "\n")
    md_to_docx("# Highlights\n\n" + "\n".join(f"- {h}" for h in HIGHLIGHTS), os.path.join(OUT, "Highlights.docx"))
    n_abs = len(ABSTRACT.split())
    assert n_abs <= 230, f"abstract has {n_abs} words"
    body = sum(len(to_md(it[1]).split()) for it in S if it[0] == "p") + sum(len(to_md(b).split()) for it in S if it[0] == "bul" for b in it[1])
    print(f"Abstract words: {n_abs}; body words: {body}; tables: {len(TAB_NUM)}; figures: {len(FIG_NUM)}; references: {len(used_refs())}")
    print("DONE: manuscript written to", OUT)
