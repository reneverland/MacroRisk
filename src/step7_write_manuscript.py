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
    "Institutional thresholds in panel regressions may motivate early-warning features without establishing their predictive value. We evaluate "
    "this transition using an internal replication, a release-lag-adjusted backtest and decision-cost simulations. Across panels of six and nine "
    "emerging economies, an alternative degrees-of-freedom convention reproduces all {n_f_exact} reported threshold F statistics, but {n_lost15} of "
    "{n_sig1} significant tests lose significance with 15% trimming. The forecasting evaluation comprises development folds (2017-2020) and "
    "retrospective test folds (2021-2022) with {n_pos_all} high-risk windows. In the main FX-share specification, no addition of currency "
    "internationalization (CI) or institutional quality (IQ) raises average precision (AP) by the chosen {sesoi} margin, although "
    "{e21_n_not_excl_plus} of {e21_n_abl} paired intervals cannot exclude such a gain. The CI-by-IQ interaction changes AP by {bt_m1m0_all_L12} "
    "(95% block-bootstrap interval {bt_m1m0_all_L12_lo} to {bt_m1m0_all_L12_hi}). In 2021-2022, country identity plus persistence ranks first "
    "(AP {c1_lock}), followed by persistence alone ({b0_lock}). Short-window recalibration worsens Brier scores for all {n_models_cal} models. "
    "Simulated review gains depend on reviewer accuracy, costs and the comparison policy. In a retrospective 2023-2025 extension covering 15 "
    "economies, XGBoost improves on persistence in the nine core economies but not in the six external ones, and a frozen fallback rule retains "
    "persistence throughout. A post-hoc paired ablation finds an IQ gain for the additive boosting model but not for XGBoost. Conclusions are "
    "limited to the specified targets, samples and decision assumptions.")

KEYWORDS = ["Early warning system", "Explainable boosting machine", "Panel threshold regression", "Replication",
            "Pseudo-real-time evaluation", "Selective prediction"]

HIGHLIGHTS = [
    "A reproducibility audit connects threshold evidence with stress prediction",
    "No FX-share ablation reaches a 0.02 gain in average precision",
    "Model rankings change across periods, countries and stress definitions",
    "Simulated review gains depend on accuracy, costs and the comparison policy",
    "A frozen fallback misses gains from an unmonitored model in the core sample",
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


H1("Introduction")
P("Early-warning systems for exchange-rate and balance-of-payments stress are decision-support tools. A model ranks countries or months by "
  "risk, and analysts decide where to spend limited monitoring capacity [kaminsky1998; holopainen2017]. Their value depends on out-of-sample "
  "ranking quality, on the calibration of the probabilities shown to users and on the cost of the actions they trigger, not on in-sample fit. "
  "Candidate early-warning variables are nevertheless often motivated by in-sample panel regressions. A recurring example is the claim that the "
  "macroeconomic effects of currency internationalization (CI) depend on a country's institutional quality (IQ), estimated with fixed-effects "
  "panel threshold regressions [hansen1999].")
P("This paper asks whether such threshold evidence survives the move from a regression table to an early-warning system. We organise the study "
  "around three questions.")
BUL(["RQ1 (replication): Can the reported threshold estimates be reproduced from the original data, and how sensitive are they to estimation "
     "choices that are rarely reported, such as the trimming of the threshold grid and the timing of information?",
     "RQ2 (forecast value): Under explicit information-release assumptions, do CI, IQ and their interaction improve the prediction of future REER "
     "stress relative to persistence, country-identity and macro-only benchmarks, using {sesoi} AP as a smallest effect of interest?",
     "RQ3 (decision value): How do calibration, analyst-routing and fallback policies compare under explicit decision-cost assumptions, and how do "
     "their rankings change in a later retrospective evaluation period?"])
P("We use data from an earlier unpublished working paper on CI, IQ and six macroeconomic risks, with overlapping authorship: a SWIFT-share panel "
  "of six countries and an FX-turnover-share panel of nine countries. This is an internal replication, not an independent replication of a "
  "published result. We first reconstruct the reported threshold tests and regime coefficients, then evaluate related features in a "
  "release-lag-adjusted backtest for three-month real-effective-exchange-rate (REER) stress. The 2017-2020 folds support development; 2021-2022 "
  "had been inspected during study design and are treated as retrospective test folds. The 2023-2025 extension uses an author-recorded frozen "
  "protocol. It is also retrospective: these historical outcomes were already available when the study was conducted, and a preliminary audit "
  "had inspected some target summaries. Protocol integrity, the chronology of analysis and protection from prior outcome exposure are distinct "
  "issues.")
P("The findings are heterogeneous. A degrees-of-freedom convention reproduces the reported F statistics, while trimming sensitivity questions "
  "the stability of several thresholds. The main FX-share ablations do not show a gain of {sesoi} AP from CI or IQ, but half of the paired "
  "intervals are too wide to exclude one. The CI-by-IQ interaction is not equivalent to the additive model within the chosen margin in either "
  "evaluation window. Country-identity and persistence benchmarks are competitive, but model rankings change across periods, countries and "
  "stress definitions. We make three contributions:")
BUL(["An auditable evaluation workflow connecting reconstruction of panel-threshold evidence, explicit information-timing assumptions, "
     "out-of-time prediction and decision-cost assessment, including a stage-by-stage timing audit. The methodological contribution is the "
     "integration and evaluation of these stages, rather than a new learning algorithm.",
     "Empirical evidence on when institutional and currency-internationalization features do and do not improve prediction, using persistence "
     "and country-identity controls, interaction ablations, paired intervals against an equivalence margin and event-level evaluation with a "
     "strict early-warning definition.",
     "A comparison of calibration, simulated analyst review under several reviewer-error models and a frozen fallback policy, including the "
     "opportunity cost of retaining a baseline when an unmonitored model performs better in a later sample."])
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
  "design additionally needs an explicit information set and release chronology [croushore2001].")
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
  "Selective prediction lets a system defer uncertain cases to humans [chow1970; geifman2017]. Claims of 'no improvement' require equivalence tests "
  "against a smallest effect of interest rather than non-significant differences [schuirmann1987; lakens2017].")

H1("Data and replication design")
H2("Original study and data")
P("The internal replication uses the two regression datasets of the earlier unpublished working paper. The CI series and macro controls were "
  "exported from the Wind Economic Database and compiled into the regression datasets on 13 June 2023; the original Wind series codes were not "
  "retained, so Supplementary Table S15 documents the variables by their dataset column names; SHA-256 checksums of the files are recorded in the "
  "replication package. Panel A measures CI by the currency's share of SWIFT payments for China, Hungary, Mexico, Poland, the Russian Federation "
  "and South Africa (2012-08 to 2021-12, N = 678). Panel B measures CI by the domestic currency's share of FX-turnover and adds Brazil, India and "
  "Korea (2012-01 to 2022-12, N = 1,188). IQ is the mean of the six WGI dimensions. The six risk indicators are CPI volatility (CPI_Vol), "
  "FX-reserve volatility (FX_Vol), consumption volatility (CE_Vol), real exchange-rate volatility (ER_Vol), the credit-to-GDP gap (CG_Gap) and "
  "unemployment (Unemp). The Panel B ER_Vol series is available for only {B_er_countries} of the nine countries, so that regression uses "
  "N = {B_er_n}. [[tab:data]] summarises the samples.")
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
P("so the smallest attainable value is {p_min} [davison1997]; Monte Carlo standard errors are reported in the replication package. Each "
  "replication draws whole country series of threshold-model residuals with replacement, adds them to the fitted values of the linear "
  "(no-threshold) model, demeans by country and recomputes both models over the same grid. The lagged dependent variable and the other "
  "regressors are held at their observed values, so the null is static rather than a re-simulated dynamic process, serial and cross-country "
  "dependence within a country series is preserved, and the effective number of resampling units is the number of countries (six or nine). "
  "Three choices are not stated in the original paper: the dataset columns behind CE_Vol and ER_Vol, the timing of the other-risk controls and "
  "the trimming fraction. We reconstruct a compatible implementation through a specification search that scores every candidate against the "
  "reported F statistics, thresholds and regime t statistics (Supplementary Table S2) and apply the selected option to all twelve regressions: "
  "full-coverage series, contemporaneous other risks and 1% trimming, the default of a widely used Stata implementation [wang2015].")
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
  "values. Second, the construction and release calendar of the Wind FX-share series are not documented, so we assess assumed CI release lags of "
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
  "2024-03; no model prediction for origins after 2022-12 was scored before the extension protocol was frozen. [[fig:fig2]] shows the stress "
  "windows and IQ trajectories.")
P("The results presented below focus on the REER target. A reserve-drawdown definition alone does not provide evidence that the findings "
  "transfer to reserve pressure. Likewise, positive forecasting windows and the underlying economic episodes are different counting units.")
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
  "training range only. Thresholds are estimated on the training targets of each outer fold. Supplementary Table S16 lists, for every fold, "
  "horizon and stage (outer training, calibration, inner folds and the calibration history described below), the last origin used, the "
  "month its target was published and the first evaluated month; all {timing_n_checked} stage checks of the main evaluation and of the "
  "post-hoc rerun in Section 5.9 pass. Development-fold performance is used for selection and should not be interpreted as an untouched test "
  "estimate.")
H2("Models")
P("B0 is a persistence rule, a one-variable logistic map from the lagged three-month REER volatility. B1 is ridge regression for the continuous "
  "target and L2-regularised logistic regression for the binary target. B2 is a threshold forecaster that estimates an IQ threshold in the training "
  "window and fits regime-specific CI slopes. B3 and B4 are a random forest and XGBoost. M0 is an additive EBM, and M1 adds a single CI x IQ "
  "pairwise term, the forecasting analogue of the threshold hypothesis. Two country-identity baselines test whether learned models merely "
  "recognise countries: C0 is a logistic regression on country indicators and C1 adds the lagged REER volatility. The interaction ablation adds a "
  "placebo EBM with a macro-only pair, an unrestricted EBM with ten selected pairs and a linear CI x IQ model. Stochastic learners are averaged "
  "over five seeds.")
H2("Calibration")
P("Each model produces raw probabilities and two calibrated versions: Platt scaling on the eight-month calibration window, and Platt scaling on "
  "all earlier out-of-sample predictions whose targets had matured ('expanding'). Because the event threshold changes from fold to fold, the "
  "expanding history is relabelled with the current fold's threshold before the Platt map is fitted, so that every pooled prediction refers to "
  "the event being forecast. For each model the scheme with the lowest pooled Brier score on the development folds is designated as the "
  "development-selected scheme; it was raw for {n_raw_locked} of the 7 models. All decision analyses use these probabilities. Because the "
  "2021-2022 period had already been inspected during study design, its estimates are retrospective even when this calibration rule is held fixed.")
H2("Code corrections after the first draft")
P("An internal code audit after the first draft found two departures from the protocol above. The inner tuning folds used a fixed gap of three "
  "months, shorter than the $h + \\ell$ months required (four for $h = 3$, seven for $h = 6$), and the imputer and scaler were fitted on the whole "
  "training window before the inner split. In addition, the expanding calibration history kept each earlier fold's own event threshold. Both "
  "issues were corrected and every learned-model experiment was rerun; the earlier outputs are archived in the replication package. Of "
  "{chg_n_keys} audited numbers, {chg_n_changed} changed; the largest change in a headline pooled AP is {chg_ap_max_abs}, and the persistence "
  "and country-identity baselines are unchanged. Two conclusions of the first draft changed: the CI x IQ interaction is no longer equivalent to "
  "the additive model in 2021-2022 (90% interval [{bt_m1m0_lock_L6_lo90}, {bt_m1m0_lock_L6_hi90}], previously [{v1_bt_m1m0_lock_L6_lo90}, "
  "{v1_bt_m1m0_lock_L6_hi90}]), and the random forest's gain over B0 is no longer distinguishable from zero ({bt_b3b0_all_L12} "
  "[{bt_b3b0_all_L12_lo}, {bt_b3b0_all_L12_hi}], previously {v1_bt_b3b0_all_L12} [{v1_bt_b3b0_all_L12_lo}, {v1_bt_b3b0_all_L12_hi}]). The "
  "frozen 2023-2025 extension (Section 4.9) had already been scored with the earlier tuning code and was not rescored; its inner tuning folds "
  "fail the timing check ({timing_frozen_fail} stage checks), and Section 5.9 reports a post-hoc rerun with the corrected code.")
H2("Metrics and inference")
P("Average precision summarises the precision-recall curve,")
EQ(r"\mathrm{AP} = \sum_{k} (R_k - R_{k-1})\, P_k", "eq:ap")
P("where $P_k$ and $R_k$ are precision and recall at the $k$-th threshold. We report pooled AP over all predictions of a window and the mean of "
  "the fold-specific APs; tables state which is shown. Alerts are issued when the probability $p$ reaches $\\tau = C_{FP}/(C_{FP} + C_{FN})$, "
  "and the expected cost per 100 forecasts is")
EQ(r"\mathrm{Cost} = \frac{100}{n} \sum_{i} \left[ C_{FP}\, \mathbf{1}(p_i \ge \tau,\, y_i = 0) + C_{FN}\, \mathbf{1}(p_i < \tau,\, y_i = 1) \right]", "eq:cost")
P("with $C_{FP} = 1$ and $C_{FN} = 5$ unless stated. Paired differences are assessed with a moving-block bootstrap that resamples calendar months "
  "jointly across countries (1,000 replications) [kunsch1989]. We use blocks of 12 months for the 72-month window and of 6 months for 24- and "
  "36-month windows, because a 24-month window contains only 13 distinct 12-month blocks; results for other lengths are in the replication "
  "package. We set the smallest effect of interest to $\\Delta\\mathrm{AP} = {sesoi}$, about a tenth of the typical gap between a skilled model "
  "and the base rate, and call two models equivalent when the 90% interval lies within $\\pm {sesoi}$, the two one-sided tests procedure "
  "[schuirmann1987; lakens2017].")
P("The {sesoi} margin is an operational tolerance for this comparison, not an externally validated economic utility threshold. Intervals are "
  "conditional on the fitted predictions and do not incorporate all uncertainty from model selection or refitting. Unless an adjustment is "
  "explicitly reported, the many model and sensitivity comparisons are exploratory. AP differences must be compared within matched samples "
  "because AP depends on event prevalence. The cost threshold of 1/6 is Bayes-optimal only when the probabilities are calibrated for the stated "
  "event and the assumed losses are appropriate.")
H2("Event-level evaluation")
P("Consecutive high-risk origins of a country form an episode. Episode coverage counts an episode as covered when an alert is issued between "
  "three months before its first origin and its last origin. False alarms are alerts at normal origins outside the three months before an "
  "episode, per country-year. Because coverage permits alerts after an episode has started, it is not the fraction of episodes warned about in "
  "advance. We therefore add a strict early-warning measure: an episode is eligible when its three preceding origins are observed in the window, "
  "and it is detected only if an alert is issued at one of those three origins; the lead is the distance from the first such alert to the first "
  "high-risk origin. Besides the cost threshold $\\tau$ we apply fixed alert quotas of the top one, two or three countries per month. Leads are "
  "relative to the first labelled origin, not to an independently dated crisis. Onset evaluation removes origins whose lagged volatility "
  "already exceeds the fold threshold; it evaluates predictions conditional on the absence of elevated lagged volatility. The direction analysis "
  "splits high-risk windows by the sign of the three-month REER change (real depreciation versus appreciation).")
H2("Decision layer")
P("The review experiment is a scenario simulation, not an observed workflow. Each month analysts review $k$ country cases; a reviewed case costs "
  "a fee $c$, and the remaining cases are decided automatically at $\\tau = 1/6$. In the baseline grid a reviewed case is resolved correctly "
  "with probability one (an oracle bound) or 0.8, and every automated policy (never alert, B0, macro-only EBM, M0, M1 with each calibration, B3, "
  "B4) is crossed with four routing rules: least confident first (smallest $|\\mathrm{logit}\\,p - \\mathrm{logit}\\,\\tau|$, the distance to the "
  "cost-sensitive boundary rather than to 0.5), highest probability first, highest lagged volatility first and random. Random routing is "
  "evaluated as its exact expectation, so no simulation seed is involved.")
P("A single accuracy does not determine the expected loss, so a second grid varies the reviewer-error model: errors independent of class with "
  "accuracy 0.8; more missed events (error rate 0.3 on events, 0.1 on non-events); more false alarms (0.1 and 0.3); and confidence-dependent "
  "errors that reach 0.4 at the decision boundary and decline with the logit distance from it. Errors are independent of country, and an error "
  "turns a reviewed case into the wrong decision. This grid adds expected-loss routing, which reviews the $k$ cases with the largest "
  "model-implied reduction in expected loss, $\\mathrm{EL}_{auto} - \\mathrm{EL}_{review}$, computed from the model probability and the same "
  "error model, and only when that reduction is positive. The rule uses no outcome information. Perfect review is an oracle bound, the "
  "imperfect-reviewer models are assumptions, and neither is evidence of observed human forecasting performance. Cost differences carry paired "
  "block-bootstrap intervals.")
H2("Frozen protocol for the retrospective extension")
P("Before scoring model predictions in the 2023-2025 extension, we recorded a frozen protocol (SHA-256 {proto_hash12}...) that fixes the sample "
  "(Core-9 and External-6), the features (macro and IQ; no updated post-2022 CI observations are available), the folds (test years 2023-2025, "
  "with 2021-2022 as warm-up folds), the models (B0, B1, macro EBM and XGBoost), raw probabilities, the costs and a fallback policy. All models "
  "are trained on the pooled 15-country history, so External-6 is evaluated out of time but is not an unseen-country transfer (Supplementary "
  "Table S17). The policy deploys the learned model, chosen on the development folds as the macro EBM, in year $T$ only if, on the latest twelve "
  "matured origins, its AP exceeds that of B0 by at least $\\delta = {fb_delta}$ and its expected calibration error is at most {fb_ece_cap} (the "
  "largest per-fold ECE of B0 in the development folds); otherwise it deploys B0. Applied once to the retrospective folds, the rule chose "
  "{fb_retro}. A post-freeze change to the scoring script, needed to read the frozen file, is logged in the package; the protocol itself was not "
  "changed.")
P("The hash identifies the protocol file but does not independently establish when it was fixed. The extension is not described as a "
  "prospective or independently preregistered trial; the earlier target-summary audit and the post-freeze code change form part of its analysis "
  "history. After the code corrections in Section 4.5 we added a post-hoc rerun of the same folds that is explicitly exploratory: it refits B0, "
  "C1, B1, the macro-only and macro+IQ EBMs and the macro-only and macro+IQ XGBoost models with the corrected tuning, estimates the paired IQ "
  "increment, compares always-on policies with the frozen fallback, reports the yearly inputs of the fallback rule and evaluates a "
  "multi-candidate monitor that deploys whichever candidate has the largest recent AP gain over B0 subject to the frozen $\\delta$ and ECE cap. "
  "The monitor was defined after the frozen result was known and is a new policy, not part of the protocol.")

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
H2("How robust are the thresholds?")
P("The thresholds are often extreme. In {n_edge} of 12 regressions fewer than 10% of observations fall in the low-IQ regime; for Panel A CPI_Vol "
  "the low regime contains {A_cpi_share}% of observations. With 1% trimming {n_sig1} of 12 tests are significant at 5%; with 15% trimming "
  "{n_lost15} of these lose significance (Panel A CPI_Vol: p = {A_cpi_p15}), leaving {robust_list}. In a pseudo-real-time version that lags CI by "
  "one month and uses IQ and annual controls only after their release, {n_sig_prt} tests are significant and {n_both} of the originally "
  "significant ones survive ({both_list}). With single WGI dimensions as threshold variables, {wgi_sig_A} of {wgi_n} Panel A and {wgi_sig_B} of "
  "{wgi_n} Panel B tests are significant (Supplementary Tables S3-S5). [[fig:fig8]] summarises the evidence. The answer to RQ1 is that the "
  "threshold evidence is reproducible as computed but sensitive to specification and insufficient, on its own, to establish a stable predictive "
  "or causal mechanism.")
FIGR("fig8")
H2("Forecasting benchmark")
P("[[tab:bench]] reports the benchmark. Over all six folds (pooled AP, base rate 0.187) the random forest leads with {b3_all}, followed by "
  "C1 ({c1_all}), XGBoost ({b4_all}) and the persistence rule B0 ({b0_all}); the EBMs reach {m0_all} (M0) and {m1_all} (M1). The ranking is not "
  "stable. In the development folds the random forest is best ({b3_dev}) and B0 weak ({b0_dev}); in the retrospective test C1 reaches "
  "{c1_lock} and B0 {b0_lock}, above the other multivariable models in [[tab:bench]] (at most {max_learned_lock}), and the EBMs fall to about "
  "{m1_lock}. Paired bootstrap intervals over the six folds show no AP gain over B0 whose lower 95% limit exceeds zero: the random forest's "
  "gain is {bt_b3b0_all_L12} [{bt_b3b0_all_L12_lo}, {bt_b3b0_all_L12_hi}] and XGBoost's {bt_b4b0_all_L12} [{bt_b4b0_all_L12_lo}, "
  "{bt_b4b0_all_L12_hi}]. Country identity alone (C0) reaches {c0_all}, close to the EBMs, which is consistent with cross-country differences "
  "contributing to discrimination, without quantifying how much of each model's skill is attributable to country identity ([[fig:fig3]]).")
TBL("bench")
FIGR("fig3")
H2("Do CI and IQ add information?")
P("[[tab:ablation]] compares CI and IQ additions in the main FX-share specification. Adding CI to the macro feature set lowers pooled AP in "
  "{n_ci_neg} of 6 model-window cells, and no addition of CI, IQ or both raises AP by {sesoi} or more in any of 18 cells. Relative to M0, the "
  "CI x IQ interaction changes AP by {e05_m1_all} over all folds and {e05_m1_lock} in the retrospective test, a placebo macro interaction by "
  "{e05_plac_all} and {e05_plac_lock}, and an unrestricted EBM by {e05_unr_all} and {e05_unr_lock}. The paired bootstrap gives M1 minus M0 = "
  "{bt_m1m0_all_L12} [{bt_m1m0_all_L12_lo}, {bt_m1m0_all_L12_hi}] over six folds and {bt_m1m0_lock_L6} [{bt_m1m0_lock_L6_lo}, "
  "{bt_m1m0_lock_L6_hi}] in the retrospective test. Neither 90% interval ([{bt_m1m0_all_L12_lo90}, {bt_m1m0_all_L12_hi90}] and "
  "[{bt_m1m0_lock_L6_lo90}, {bt_m1m0_lock_L6_hi90}]) lies within $\\pm {sesoi}$, so equivalence is not established in either window.")
TBL("ablation")
P("Point estimates below {sesoi} do not show that the underlying effects are below {sesoi}. [[tab:intervals]] therefore gives paired intervals "
  "for all 18 increments. In {e21_n_excl_plus} of {e21_n_abl} the 95% interval excludes a gain of {sesoi} and in {e21_n_tost} the 90% interval "
  "lies within $\\pm {sesoi}$; the remaining {e21_n_not_excl_plus} intervals, mostly for IQ and for the 24-month retrospective window, reach "
  "upper limits of up to {e21_max_hi}, so a gain of that size cannot be excluded there. Only {e21_n_excl0} interval excludes zero, a loss from "
  "adding IQ to B1 in 2021-2022 ({e21_b1_iq_lock} [{e21_b1_iq_lock_lo}, {e21_b1_iq_lock_hi}]). The evidence is therefore an absence of "
  "detected gains with limited precision, not a demonstrated absence of value.")
TBL("intervals")
P("Why does the CI signal not help? The EBM explanations ([[fig:fig5]]) rank the FX share {e09_rank_fx} of {e09_nterms} terms and the CI x IQ "
  "pair {e09_rank_inter}; the CI response is almost parallel across IQ levels. Replacing the FX share level by an expanding country mean "
  "(between) and the deviation from it (within) moves M0's pooled AP from {m0_all} to {dec_m0_all}, compared with {m0_macro_all} for the "
  "macro-only M0; adding a within x IQ or a between x IQ pair gives {dec_within_all} and {dec_between_all}. The between component carries "
  "{imp_between}% of total EBM importance against {imp_within}% for the within component (Supplementary Table S14). This decomposition is "
  "consistent with part of the CI signal reflecting persistent country differences; importance shares do not establish that CI is only a "
  "country identifier or identify a causal channel.")
FIGR("fig5")
H2("Events, onsets and direction")
P("[[tab:events]] moves from windows to episodes. Over six folds there are {n_episodes_all} episodes ({n_episodes_lock} in 2021-2022). At "
  "$C_{FN} = 5$, B0 covers {ep_rec_b0_all}% of episodes with {ep_fa_b0_all} false alarms per country-year, XGBoost {ep_rec_b4_all}% with "
  "{ep_fa_b4_all} and M1 {ep_rec_m1_all}% with {ep_fa_m1_all}; in the retrospective test M1 covers only {ep_rec_m1_lock}%. Under the strict "
  "definition, {e22_n_el_all} episodes are eligible ({e22_n_el_lock} in 2021-2022). B0 warns before the start of {e22_b0_tau_all}% of them, "
  "XGBoost {e22_b4_tau_all}%, C1 {e22_c1_tau_all}% and M1 {e22_m1_tau_all}%, with a median lead of {e22_b0_tau_all_lead} months, the maximum "
  "the definition allows; in 2021-2022 the shares are {e22_b0_tau_lock}%, {e22_b4_tau_lock}%, {e22_c1_tau_lock}% and {e22_m1_tau_lock}%. With "
  "a fixed quota of two countries per month, false alarms fall to below one per country-year, and B0 still detects {e22_b0_top2_all}% "
  "of episodes in advance against {e22_b4_top2_all}% for XGBoost and {e22_m1_top2_all}% for M1. When origins already in stress are removed, "
  "AP falls for every model, and in the retrospective test C1 ({on_c1_lock}) still leads M1 ({on_m1_lock}) and B0 ({on_b0_lock}) in the "
  "onset-restricted sample ({on_npos_lock} onset windows). Over six folds most models predict depreciation and appreciation windows with "
  "similar AP (B0 {dep_b0_all} and {app_b0_all}, M1 {dep_m1_all} and {app_m1_all}). In 2021-2022 the persistence-based models detect the "
  "{dep_npos_lock} depreciation windows much better (B0 {dep_b0_lock}, C1 {dep_c1_lock}) than the EBMs (M1 {dep_m1_lock}).")
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
P("[[tab:reviewerr]] varies the reviewer-error model. With perfect review, expected-loss routing beats low-confidence routing for B0 "
  "({e23_all_perf_b0_el_lc} [{e23_all_perf_b0_el_lc_lo}, {e23_all_perf_b0_el_lc_hi}]) but not for M1 ({e23_all_perf_m1_el_lc} "
  "[{e23_all_perf_m1_el_lc_lo}, {e23_all_perf_m1_el_lc_hi}]), and in 2021-2022 it is worse for M1 ({e23_lock_perf_m1_el_lc} "
  "[{e23_lock_perf_m1_el_lc_lo}, {e23_lock_perf_m1_el_lc_hi}]), because the rule trusts probabilities that were poorly calibrated in that "
  "period. With any of the four imperfect-reviewer models and a fee of 0.5, the model-implied gain of review is never positive, so "
  "expected-loss routing reviews no case and equals no review in all {e23_n_el_eq_none} policy-error combinations. Low-confidence routing "
  "still beats random routing in {e23_n_lc_rand_better} of {e23_n_lc_rand} combinations, but it never significantly beats no review and is "
  "significantly worse in {e23_n_lc_none_worse}. The value of review therefore depends on reviewer accuracy, fees, calibration and the "
  "comparison policy; it is not a general property of the routing rule.")
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
  "favour the model with a 95% interval above zero and none favours B0: {e21_rob_pos_list}. Learned models thus beat persistence for rarer "
  "events, for country-specific thresholds, under which persistence is weak, and, for XGBoost, for the reserve target. In the matched Core-6 sample ({c6_npos_all} high-risk windows "
  "in {c6_n_all} country-months) M1 reaches {c6_sw_m1_all} with SWIFT features and {c6_noci_m1_all} without CI, a difference of "
  "{e21_c6_m1_swift} [{e21_c6_m1_swift_lo}, {e21_c6_m1_swift_hi}]; only {e21_c6_n_excl0} of {e21_c6_n} Core-6 CI comparisons excludes zero "
  "(both CI measures in B1, {e21_c6_b1_both} [{e21_c6_b1_both_lo}, {e21_c6_b1_both_hi}]). The main FX-share ablations do not show a {sesoi} AP "
  "gain, but this result should not be generalized to every CI measure or risk definition.")
H2("Frozen retrospective extension, 2023-2025")
P("[[tab:confirm]] reports the extension ({conf_all15_npos} high-risk windows in {conf_all15_n} country-months). The fallback rule deployed B0 "
  "in every year ({conf_deployed}), so its cost equals that of B0, {conf_all15_fb_cost} per 100 forecasts against {conf_all15_never} for never "
  "alerting. Ex post, XGBoost had the highest AP ({conf_all15_b4} against {conf_all15_b0} for B0) and a lower cost ({conf_all15_b4_cost}), "
  "but the cost difference is not significant ({cd_all15_b4_cost} [{cd_all15_b4_cost_lo}, {cd_all15_b4_cost_hi}]). In the Core-9 countries the "
  "AP gain of always using XGBoost over the fallback is {pd_core9_alw_b4_ap} [{pd_core9_alw_b4_ap_lo}, {pd_core9_alw_b4_ap_hi}], a gain the rule "
  "could not capture because it monitored the macro EBM; always using the macro EBM gives {pd_core9_alw_m0_ap} [{pd_core9_alw_m0_ap_lo}, "
  "{pd_core9_alw_m0_ap_hi}]. In the six external economies B0 has the higher AP ({conf_ext6_b0} against {conf_ext6_b4}), whereas XGBoost has "
  "the lower simulated cost ({conf_ext6_b4_cost} versus {conf_ext6_b0_cost}), illustrating the distinction between ranking and decisions at a "
  "fixed threshold. Because the fallback equalled B0 in every year, it did not improve on always using B0; its value in this period is "
  "limited to having avoided the weaker macro EBM and B1.")
TBL("confirm")
H2("Post-hoc rerun of 2023-2025 with corrected tuning")
P("The post-hoc rerun (lower panel of [[tab:confirm]] and [[tab:posthoc]]) is exploratory. With the corrected tuning, adding IQ to the macro "
  "EBM raises pooled AP by {pd_all15_iq_m0_ap} [{pd_all15_iq_m0_ap_lo}, {pd_all15_iq_m0_ap_hi}] over the 15 countries, {pd_core9_iq_m0_ap} "
  "[{pd_core9_iq_m0_ap_lo}, {pd_core9_iq_m0_ap_hi}] in Core-9 and {pd_ext6_iq_m0_ap} [{pd_ext6_iq_m0_ap_lo}, {pd_ext6_iq_m0_ap_hi}] in "
  "External-6, while for XGBoost the increment is {pd_all15_iq_b4_ap} [{pd_all15_iq_b4_ap_lo}, {pd_all15_iq_b4_ap_hi}]. The EBM gain also "
  "lowers the Brier score ({pd_all15_iq_m0_brier} [{pd_all15_iq_m0_brier_lo}, {pd_all15_iq_m0_brier_hi}]) but not the expected cost "
  "({pd_all15_iq_m0_cost} [{pd_all15_iq_m0_cost_lo}, {pd_all15_iq_m0_cost_hi}]). IQ therefore adds ranking information to the additive model "
  "in this later period, of about the size of the chosen margin, but not to the stronger XGBoost model, and the macro+IQ EBM ({ph_all15_m0}) "
  "remains below B0 ({ph_all15_b0}). The refitted fallback rule again deploys B0 in every year: the AP gain of the macro EBM over B0 on the "
  "latest matured origins is {ph_fb_gains}. The exploratory multi-candidate monitor deploys {ph_mon_deployed}. It ties with B0 over the 15 "
  "countries ({pd_all15_mon_b0_ap} [{pd_all15_mon_b0_ap_lo}, {pd_all15_mon_b0_ap_hi}]) and recovers part of the Core-9 gain "
  "({pd_core9_mon_b0_ap} [{pd_core9_mon_b0_ap_lo}, {pd_core9_mon_b0_ap_hi}]), but stays below always using XGBoost there "
  "({pd_core9_mon_b4_ap} [{pd_core9_mon_b4_ap_lo}, {pd_core9_mon_b4_ap_hi}]), because recent history favoured B0 until 2025 (recent AP of B0: "
  "{ph_hist_b0_ap}; of XGBoost: {ph_hist_b4_ap}). A monitored fallback reacts with a lag of at least one year to a change in model ranking.")
TBL("posthoc")

H1("Discussion")
H2("Decision rules")
P("[[tab:rules]] translates the results into conditional design considerations. Persistence and country-identity models provide useful "
  "reference points, while release assumptions, probability calibration and decision costs influence the evaluation. The CI-by-IQ interaction "
  "does not provide the chosen AP gain in the main comparison, and neither CI nor IQ does in the main FX-share ablations, but the paired "
  "intervals, the sensitivity results and the post-hoc IQ increment for the EBM prevent a blanket rejection of institutional or CI "
  "information. The policy results answer RQ3 comparatively: no evaluated decision rule is uniformly best across periods and assumptions.")
TBL("rules")
H2("Implications for expert and decision-support systems")
P("The applied contribution is an audit workflow for moving from regression-based motivation to a predictive decision-support task. First, an "
  "in-sample association does not establish forecasting value. Second, the reported EBM estimates change materially when the REER availability "
  "assumption changes; publication timing is therefore part of the model specification, and the timing condition must hold in every nested "
  "stage, not only at the outer test boundary, as the corrections in Section 4.5 illustrate. Third, ranking quality, probability quality and "
  "decision cost are separate criteria: a model may lead on one and not another. Fourth, decision rules that rely on model probabilities, such "
  "as expected-loss routing, inherit their calibration errors. Fifth, the later evaluation reveals a limitation of a single-candidate fallback: "
  "it can retain a competitive baseline while missing improvement from a different candidate, and monitoring several candidates reacts only "
  "after the ranking has changed. These findings motivate transparent validation and monitoring. They do not establish a new optimal learning "
  "algorithm or demonstrate the effectiveness of a deployed early-warning service.")
H2("Limitations")
P("The primary forecasting panel contains nine countries over eleven years, with {n_episodes_all} labelled episodes in the evaluated folds. "
  "Overlapping targets, common shocks and the limited number of country clusters constrain inference; short evaluation windows yield few "
  "independent time blocks, and half of the ablation intervals are too wide to exclude a gain of the chosen size. Development-period model "
  "selection and retrospective inspection of 2021-2022 limit claims of untouched testing. The 2023-2025 extension is historical, uses a frozen "
  "protocol with an analysis history that includes prior target-summary inspection and a tuning error corrected after scoring, and cannot test "
  "updated CI; its IQ ablation is post hoc. The data are release-lag adjusted rather than fully vintage reconstructed; current-vintage revisions "
  "and uncertain source calendars remain limitations. The Wind CI construction could not be re-verified, and changing a nominal lag does not "
  "resolve provenance or measurement validity. The replication preserves a dynamic fixed-effects specification, so Nickell bias "
  "[nickell1981] and the applicability of non-dynamic threshold-test inference require caution; the country-block bootstrap holds the lagged "
  "dependent variable fixed and rests on six or nine resampling units. A search for specifications that reproduce earlier tables is not an "
  "independent hypothesis test. The policy simulation assumes costs and reviewer-error mechanisms; it is neither a field trial nor evidence "
  "that real analysts can achieve the simulated gains. AP equivalence is local to a stated margin and comparison, and is not evidence of "
  "economic equivalence or policy causality.")

H1("Conclusion")
P("This study evaluates whether institution-conditioned currency-internationalization evidence can inform exchange-rate stress prediction and "
  "decision support. A compatible calculation reproduces the reported threshold tests, but several results are sensitive to trimming and model "
  "assumptions. In the main FX-share forecasting comparisons, CI and IQ additions do not achieve the chosen {sesoi} AP gain, but the paired "
  "intervals are often too wide to exclude it, and interaction equivalence is not established. Alternative CI measures, stress thresholds and "
  "later country samples yield heterogeneous results, including a post-hoc IQ gain for the additive model in 2023-2025. The retrospective "
  "extension evaluates model and fallback performance rather than confirming a null contribution from CI or IQ; its single-candidate fallback "
  "retains persistence in every year and misses the core-sample improvement from XGBoost. The practical contribution is a transparent audit "
  "workflow that separates reproducibility, predictive value and simulated decision value, checks the timing of every estimation stage and "
  "makes the limits of the evidence explicit before deployment.")

# ------------------------------------------------------------------------------------------
# Tables
# ------------------------------------------------------------------------------------------
def f3(x):
    return "" if pd.isna(x) else f"{float(x):.3f}"


def f1(x):
    return "" if pd.isna(x) else f"{float(x):.1f}"


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
                       notes="Thresholds are the 80th percentile of the training targets of each fold. Training origins are truncated so that every target is published before the test year; the h = 6 task uses earlier cut-offs (Supplementary Table S16). Positives by country are listed in the replication package.")

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
        rows.append([MLAB[m], f3(g.loc["F0_Macro_Only", "AP"])] + [f"{g.loc[f, 'Delta_AP_vs_Macro']:+.3f}" for f in ["F1_Macro_plus_CI", "F2_Macro_plus_IQ", "F3_Macro_plus_CI_plus_IQ"]])
    g = t4b[t4b.evaluation_window == w].set_index("interaction_spec")
    for spec, labl in [("M1_EBM_CIxIQ", "M1 CI x IQ pair vs M0"), ("M_Placebo_MacroInter", "Placebo macro pair vs M0"), ("M_Unrestricted_EBM", "Unrestricted EBM vs M0"), ("B1_Linear_CIxIQ", "Linear CI x IQ vs M0")]:
        rows.append([labl, f3(g.loc[spec, "AP"]), "", "", f"{g.loc[spec, 'Delta_AP_vs_M0']:+.3f}"])
    panels.append(dict(title=title, header=["Model or specification", "Macro or model AP", "Delta +CI", "Delta +IQ", "Delta +CI+IQ or vs M0"], rows=rows))
TABLES["ablation"] = dict(caption="Contribution of CI, IQ and interactions (pooled AP).", panels=panels,
                          notes=f"Upper rows: AP of the macro-only set and changes from adding CI, IQ or both. Lower rows: AP of the interaction specification and change relative to M0 with all features. Paired block bootstrap for M1 minus M0: six folds {V['bt_m1m0_all_L12']} [{V['bt_m1m0_all_L12_lo']}, {V['bt_m1m0_all_L12_hi']}] (L = 12); retrospective {V['bt_m1m0_lock_L6']} [{V['bt_m1m0_lock_L6_lo']}, {V['bt_m1m0_lock_L6_hi']}] (L = 6). Smallest effect of interest: {V['sesoi']}.")

e21 = rd("table16_e21_paired_intervals.csv")
fa = e21[e21.family == "Feature ablation"]
rows = []
for m in ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive"]:
    for inc in ["+CI vs macro", "+IQ vs macro", "+CI+IQ vs macro"]:
        rr = [MLAB[m], inc.replace(" vs macro", "")]
        for w in [WA, WL]:
            x = fa[(fa.model == m) & (fa.comparison == inc) & (fa.evaluation_window == w)].iloc[0]
            rr += [f"{x.Delta_AP_Point:+.3f} [{x.Delta_AP_CI95_Low:.3f}, {x.Delta_AP_CI95_High:.3f}]",
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
                 f"{r.Delta_cost_per100:+.1f} [{r.CI95_Low:.1f}, {r.CI95_High:.1f}]", f"{r8.Delta_cost_per100:+.1f} [{r8.CI95_Low:.1f}, {r8.CI95_High:.1f}]"])
TABLES["review"] = dict(caption="Selective-review scenario simulation: expected cost per 100 forecasts and paired differences.",
                        header=["Period", "Policy A", "Policy B", "Cost A", "Cost B", "A - B, accuracy 1.0 [95% CI]", "A - B, accuracy 0.8 [95% CI]"],
                        rows=rows, notes="LC review: least-confident cases (closest to the cost threshold) reviewed first; vol. review: highest lagged volatility first. Two reviews per month (k = 2), review fee 0.5, C_FN = 5. M1 uses its development-selected calibration. Block bootstrap: L = 12 (all), L = 6 (retro). Accuracy 1.0 is an oracle bound. The full grid of policies, routing rules, budgets and fees is in the replication package.")

e23 = pd.read_csv(os.path.join(TAB, "table11c_e23_review_assumptions.csv"), keep_default_na=False)
ea = e23[e23.evaluation_window == WA]
rows = []
for em in ea.error_model.unique():
    for pol in ["B0 persistence", "M1 EBM (locked scheme)", "Macro-only EBM", "B4 XGBoost"]:
        g = ea[(ea.error_model == em) & (ea.automated_policy == pol)]
        cell = lambda a, b: (lambda x: f"{x.Delta_cost_per100:+.1f} [{x.CI95_Low:.1f}, {x.CI95_High:.1f}]")(g[(g.routing_A == a) & (g.routing_B == b)].iloc[0])
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
TABLES["confirm"] = dict(caption="Retrospective extension, forecast origins 2023-2025.", panels=[
    dict(title="Panel A. Frozen protocol (macro and IQ features; scored once)", header=hdr, rows=ra),
    dict(title="Panel B. Post-hoc rerun with corrected tuning (exploratory)", header=hdr, rows=rb_)],
    notes=f"{V['conf_all15_npos']} high-risk windows in {V['conf_all15_n']} country-months ({V['conf_core9_npos']} Core-9, {V['conf_ext6_npos']} External-6). Pooled AP; cost per 100 forecasts at C_FN = 5; raw probabilities. All models are trained on the pooled 15-country history. Frozen fallback deployments: {V['conf_deployed']}; refitted fallback: {V['ph_fb_deployed']}; monitor: {V['ph_mon_deployed']}. Protocol SHA-256: {V['proto_hash']}.")

pe = rd("table15e_posthoc_differences.csv")
rows = []
for comp, lab in [("Macro+IQ vs macro (EBM)", "Macro EBM: +IQ vs macro only"), ("Macro+IQ vs macro (XGBoost)", "XGBoost: +IQ vs macro only"),
                  ("XGBoost vs B0 (corrected tuning)", "XGBoost vs B0"), ("Macro EBM vs B0 (corrected tuning)", "Macro+IQ EBM vs B0"), ("C1 vs B0", "C1 vs B0"),
                  ("Always XGBoost vs frozen fallback", "Always XGBoost vs frozen fallback"), ("Always macro EBM vs frozen fallback", "Always macro EBM vs frozen fallback"),
                  ("Always B1 vs frozen fallback", "Always B1 vs frozen fallback"), ("Exploratory monitor vs B0 (corrected tuning)", "Monitor vs B0"),
                  ("Exploratory monitor vs XGBoost (corrected tuning)", "Monitor vs XGBoost")]:
    rr = [lab]
    for g in ["All 15 countries", "Core-9", "External-6"]:
        x = pe[(pe.comparison == comp) & (pe.countries == g) & (pe.metric == "AP")].iloc[0]
        rr.append(f"{x.Delta:+.3f} [{x.CI95_Low:.3f}, {x.CI95_High:.3f}]")
    x = pe[(pe.comparison == comp) & (pe.countries == "All 15 countries") & (pe.metric == "Cost_C5_per100")].iloc[0]
    rr.append(f"{x.Delta:+.1f} [{x.CI95_Low:.1f}, {x.CI95_High:.1f}]")
    rows.append(rr)
TABLES["posthoc"] = dict(caption="Post-hoc paired comparisons for 2023-2025 (A - B with 95% block-bootstrap intervals).",
                         header=["Comparison", "Delta AP (15)", "Delta AP (Core-9)", "Delta AP (External-6)", "Delta cost (15)"], rows=rows,
                         notes="Rows 1-5 and 9-10 use the post-hoc predictions with corrected tuning; rows 6-8 use the frozen predictions (the frozen fallback deployed B0 in every year, so always-B0 versus the fallback is identically zero). Moving-block bootstrap over months, L = 6, 1,000 replications. Brier differences and yearly fallback inputs are in the replication package (table15e, table15f).")

TABLES["rules"] = dict(caption="Conditional design considerations derived from the reported evaluation.", header=["Decision", "Rule", "Evidence"], rows=[
    [fill(x) for x in row] for row in [
        ["Feature set", "Evaluate incremental CI and IQ information against a matched macro baseline with paired intervals", "Main FX-share ablations: no gain of {sesoi}; {e21_n_not_excl_plus} of {e21_n_abl} intervals cannot exclude one; post-hoc 2023-2025 IQ gain for the EBM {pd_all15_iq_m0_ap} [{pd_all15_iq_m0_ap_lo}, {pd_all15_iq_m0_ap_hi}]"],
        ["Interaction", "Validate the CI-by-IQ term before retaining it", "M1 - M0: {bt_m1m0_all_L12} [{bt_m1m0_all_L12_lo}, {bt_m1m0_all_L12_hi}]; equivalence within +/-{sesoi} not established"],
        ["Benchmarks", "Include persistence and country identity plus persistence", "Retrospective AP: C1 {c1_lock}; B0 {b0_lock}; highest other multivariable AP {max_learned_lock}"],
        ["Timing", "Document release assumptions; enforce the maturity condition in every nested tuning and calibration stage", "Using month-t REER changes M1 AP from {m1_all} to {spot_m1_all}; {chg_n_changed} audited numbers changed after the inner-fold correction"],
        ["Calibration", "Select calibration using earlier out-of-sample predictions relabelled to the current event", "Eight-month Platt worsens Brier in {n_platt8_worse_all} of {n_models_cal} models"],
        ["Analyst review", "Compare routing rules under explicit reviewer-error and fee assumptions with matched budgets", "LC vs random (oracle review): {e15_m1rev_rand_all} [{e15_m1rev_rand_all_lo}, {e15_m1rev_rand_all_hi}]; with imperfect reviewers review never beats no review significantly"],
        ["Fallback", "Evaluate the opportunity cost of the monitored candidate set, not only protection against weak models", "Frozen rule retains B0 throughout; always XGBoost in Core-9: {pd_core9_alw_b4_ap} [{pd_core9_alw_b4_ap_lo}, {pd_core9_alw_b4_ap_hi}] AP"],
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
    ["Tuning", "AP on three inner expanding folds within the training window; each inner training range ends at least h + 1 months before its validation range; median imputation and scaling fitted on the inner training range"],
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
SUPP["S15"] = dict(caption="Variables of the original regression datasets (compiled from Wind on 13 June 2023).", header=["Column name(s)", "Content", "Use in this study"],
                   rows=[list(r) for r in WIND_COLS],
                   notes="Files: reg_swiftnew_20230613.xlsx (Panel A) and reg_fxshare_20230613.xlsx (Panel B); creation date from the file metadata. The original Wind series codes were not retained.")
ta = rd("tableS16_timing_audit.csv")
SUPP["S16"] = dict(caption="Timing audit of every estimation stage.", header=["Scope", "Fold", "h", "Stage", "Last origin", "Target published", "First evaluated month", "Passes"],
                   rows=[[r.scope, r.split_id, str(r.h), r.stage, r.last_origin, r.target_published, r.first_evaluated_month, "yes" if r.published_before else "no"] for r in ta.itertuples()],
                   notes="A stage passes when the target of its last origin (origin + h + 1-month REER release lag) is published before the first month it is evaluated on. The frozen confirmation rows document the inner tuning folds of the original code (fixed three-month gap), which were corrected after scoring; the frozen result was not rescored (Section 4.5).")
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
for it in S:
    if it[0] == "fig":
        FIG_NUM.setdefault(it[1], len(FIG_NUM) + 1)
    if it[0] == "table":
        TAB_NUM.setdefault(it[1], len(TAB_NUM) + 1)

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
    L.append(r"\section*{Data availability}")
    L.append(tex_text("BIS, IMF and World Bank data are public; the Wind-based regression datasets (compiled on 13 June 2023) are licensed and cannot be redistributed, but their variables are documented in Supplementary Table S15 and their SHA-256 checksums are included in the replication package. Code, split definitions, the frozen protocol and its change log, the timing audit, all row-level predictions with labels, the archived first-draft outputs and a single entry script (run_all.sh) are provided as an anonymized reproduction archive submitted with the manuscript (MacroRisk_reproduction_anonymized.zip) and at an anonymous read-only mirror [anonymous mirror link to be inserted before submission]."))
    L.append(r"\begin{thebibliography}{99}")
    for k in used:
        au, yr = REFS[k][0].rsplit(",", 1)
        L.append(f"\\bibitem[{tex_text(au).replace(' et al.', ' et~al.')}({yr.strip()})]{{{k}}} {tex_text(REFS[k][1])}")
    L += [r"\end{thebibliography}", r"\end{document}"]
    return "\n".join(L)


def build_md():
    out = [f"# {TITLE}", "", "## Abstract", "", ABSTRACT, "", "**Keywords:** " + "; ".join(KEYWORDS), ""]
    sec = sub = 0
    for it in S:
        k = it[0]
        if k == "h1":
            sec += 1; sub = 0
            out.append(f"\n## {sec}. {it[1]}\n")
        elif k == "h2":
            sub += 1
            out.append(f"\n### {sec}.{sub}. {it[1]}\n")
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
    out += ["\n## Data availability\n", "BIS, IMF and World Bank data are public; the Wind-based regression datasets (compiled on 13 June 2023) are licensed and cannot be redistributed, but their variables are documented in Supplementary Table S15 and their SHA-256 checksums are included in the replication package. Code, split definitions, the frozen protocol and its change log, the timing audit, all row-level predictions with labels, the archived first-draft outputs and a single entry script (run_all.sh) are provided as an anonymized reproduction archive submitted with the manuscript (MacroRisk_reproduction_anonymized.zip) and at an anonymous read-only mirror [anonymous mirror link to be inserted before submission].\n", "\n## References\n"]
    out += [REFS[k][1] + "\n" for k in used_refs()]
    return "\n".join(out)


def build_supp_md():
    out = ["# Supplementary material", "", f"*{TITLE}*", ""]
    for k, tb in SUPP.items():
        out.append(md_table(tb, f"Table {k}. {tb['caption']}"))
    for k, (fn, cap) in SUPP_FIGS.items():
        out.append(f"![Fig. {k}. {cap}](figures/Fig{k}.png){{width=100%}}\n")
    out += ["## Changes between the first draft and this version", "",
            fill("The inner tuning folds and the expanding calibration history were corrected after the first draft (Section 4.5 of the manuscript). "
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
                      "**Data availability.** BIS, IMF and World Bank data are public. The CI series and macro controls of the original working paper were exported from the Wind Economic Database and compiled into the regression datasets on 13 June 2023 (variables documented by column name in Supplementary Table S15; the original Wind series codes were not retained); Wind data are licensed and cannot be redistributed. Code, split definitions, the frozen confirmation protocol and all row-level predictions are available at https://github.com/reneverland/MacroRisk.", "",
                      "**Original study.** The threshold estimates replicated in this paper come from an earlier working paper involving the second author, 'Does Currency Internationalization increase Macro Risk in Emerging Markets? Nonlinear Evidence from Institutional Quality' (drafts dated November 2023 to July 2025), which was neither submitted nor published.", "",
                      "**Declaration of generative AI and AI-assisted technologies in the writing process.** [Draft for the authors to confirm or edit:] During the preparation of this work the authors used an AI coding and writing assistant to write and audit analysis scripts, run consistency checks and draft and revise parts of the text. After using this tool, the authors reviewed and edited the content as needed and take full responsibility for the content of the publication.", ""])


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
    for h in HIGHLIGHTS:
        assert len(h) <= 85, (len(h), h)
    open(os.path.join(OUT, "highlights.txt"), "w", encoding="utf-8").write("\n".join(HIGHLIGHTS) + "\n")
    md_to_docx("# Highlights\n\n" + "\n".join(f"- {h}" for h in HIGHLIGHTS), os.path.join(OUT, "Highlights.docx"))
    n_abs = len(ABSTRACT.split())
    assert n_abs <= 230, f"abstract has {n_abs} words"
    body = sum(len(to_md(it[1]).split()) for it in S if it[0] == "p") + sum(len(to_md(b).split()) for it in S if it[0] == "bul" for b in it[1])
    print(f"Abstract words: {n_abs}; body words: {body}; tables: {len(TAB_NUM)}; figures: {len(FIG_NUM)}; references: {len(used_refs())}")
    print("DONE: manuscript written to", OUT)
