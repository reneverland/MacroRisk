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
TITLE = "Do institutional thresholds improve exchange-rate stress early warning? A replication-to-deployment evaluation with a pre-specified confirmation period"

ABSTRACT = fill(
    "Panel threshold regressions suggest that the macroeconomic effects of currency internationalization (CI) depend on institutional "
    "quality (IQ). We test whether such evidence improves early warning of exchange-rate stress. A replication-to-deployment framework links "
    "a forensic replication of reported threshold estimates to a publication-lag-aware pseudo-real-time backtest and a decision layer. "
    "With data for nine emerging economies, all {n_f_exact} reported threshold F statistics are reproduced once a degrees-of-freedom "
    "convention is identified, but {n_lost15} of {n_sig1} significant threshold effects disappear under 15% trimming. In a retrospective "
    "out-of-time evaluation (2017-2022, {n_pos_all} high-risk windows), adding CI never raised average precision (AP) by the smallest effect "
    "of interest ({sesoi}), and a CI x IQ interaction did not differ from an additive model (Delta AP = {bt_m1m0_all_L12}, 95% "
    "block-bootstrap interval [{bt_m1m0_all_L12_lo}, {bt_m1m0_all_L12_hi}]). No learned model beat a persistence rule by more than {sesoi} AP "
    "with 95% confidence, and in 2021-2022 the persistence rule ranked best (AP {b0_lock}). Short-window recalibration worsened Brier "
    "scores for all {n_models_cal} models, whereas routing low-confidence cases to analysts lowered expected cost relative to random review. "
    "In a pre-specified confirmation period (2023-2025, 15 countries) a frozen fallback rule retained the persistence rule in all three "
    "years, although XGBoost outperformed it in the nine core economies. Threshold evidence should pass such an audit before it informs deployed early-warning systems.")

KEYWORDS = ["Early warning system", "Explainable boosting machine", "Panel threshold regression", "Replication",
            "Pseudo-real-time evaluation", "Selective prediction"]

HIGHLIGHTS = [
    "Reported panel threshold F statistics are reproduced exactly from the original data",
    "Threshold effects weaken under standard trimming and publication lags",
    "Currency and institution features do not add detectable forecast value",
    "No learned model beats a persistence rule by a meaningful margin",
    "A pre-specified fallback rule is tested on 2023-2025 data",
]

# ------------------------------------------------------------------------------------------
# References (verified bibliographic records)
# ------------------------------------------------------------------------------------------
REFS = {
    "aman2024": ("Aman et al., 2024", "Aman, Z., Granville, B., Mallick, S. K., & Nemlioglu, I. (2024). Does greater financial openness promote external competitiveness in emerging markets? The role of institutional quality. International Journal of Finance & Economics, 29(1), 486-510. https://doi.org/10.1002/ijfe.2695"),
    "an2024": ("An et al., 2024", "An, J., Kim, H. S., & Park, B. (2024). Do China's policy measures for RMB internationalization foster currency co-movements? International Review of Economics & Finance, 91, 1033-1050. https://doi.org/10.1016/j.iref.2024.01.019"),
    "barthelemy2024": ("Barthélémy et al., 2024", "Barthélémy, S., Gautier, V., & Rondeau, F. (2024). Early warning system for currency crises using long short-term memory and gated recurrent unit neural networks. Journal of Forecasting. https://doi.org/10.1002/for.3069"),
    "beutel2019": ("Beutel et al., 2019", "Beutel, J., List, S., & von Schweinitz, G. (2019). Does machine learning help us predict banking crises? Journal of Financial Stability, 45, 100693. https://doi.org/10.1016/j.jfs.2019.100693"),
    "bluwstein2023": ("Bluwstein et al., 2023", "Bluwstein, K., Buckmann, M., Joseph, A., Kapadia, S., & Simsek, O. (2023). Credit growth, the yield curve and financial crisis prediction: Evidence from a machine learning approach. Journal of International Economics, 145, 103773. https://doi.org/10.1016/j.jinteco.2023.103773"),
    "breiman2001": ("Breiman, 2001", "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5-32."),
    "chen2016": ("Chen & Guestrin, 2016", "Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. In Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (pp. 785-794)."),
    "chen2024": ("Chen et al., 2024", "Chen, S., Huang, Y., & Ge, L. (2024). An early warning system for financial crises: A temporal convolutional network approach. Technological and Economic Development of Economy. https://doi.org/10.3846/tede.2024.20555"),
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
    "ostrensky2023": ("Ostrensky & Frota, 2023", "Ostrensky, V. P., & Frota, L. M. da (2023). Early warning systems via machine learning: A study of currency crises. Economia Aplicada, 27(3). https://doi.org/10.11606/1980-5330/ea189768"),
    "platt1999": ("Platt, 1999", "Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In Advances in Large Margin Classifiers (pp. 61-74). MIT Press."),
    "reimann2024": ("Reimann, 2024", "Reimann, C. (2024). Predicting financial crises: An evaluation of machine learning algorithms and model explainability for early warning systems. Review of Evolutionary Political Economy. https://doi.org/10.1007/s43253-024-00114-4"),
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
     "RQ2 (forecast value): When every input is restricted to what was published at the forecast date, do CI, IQ and their interaction improve the "
     "detection of future exchange-rate stress over persistence, country-identity and macro-only benchmarks by at least a pre-specified smallest "
     "effect of interest?",
     "RQ3 (decision value): Which decision rules, covering model choice, calibration, analyst routing and fallback, minimise expected cost, and do "
     "they hold in a confirmation period that was scored only after the protocol had been frozen?"])
P("We answer these questions with the data behind an earlier, unpublished working paper co-authored by one of us on CI, IQ and six macroeconomic risks in "
  "emerging economies: a SWIFT-share panel of six countries and an FX-turnover-share panel of nine countries. The first stage is a forensic "
  "replication of the reported threshold tests and regime coefficients. The second stage embeds the same information in a "
  "publication-lag-aware pseudo-real-time backtest for three-month real-effective-exchange-rate (REER) stress. Because the period 2021-2022 had "
  "been examined while the study was designed, we treat it as a retrospective out-of-time evaluation and add a confirmation period, 2023-2025, "
  "that was scored once under a protocol whose SHA-256 hash was recorded beforehand.")
P("The answers are largely negative, and we report them as such. The reported F statistics are reproduced exactly once an unusual "
  "degrees-of-freedom convention is recognised, but several thresholds sit at the edge of the data and lose significance under conventional "
  "trimming. CI and IQ do not add detectable forecast value, an institution-conditioned interaction is indistinguishable from an additive model, "
  "and a persistence rule is as good as or better than the learned models out of time. The contributions are:")
BUL(["A replication-to-deployment framework that connects a scored replication audit of reported panel threshold estimates to a leakage-checked "
     "forecasting and decision layer, with every number regenerated from row-level predictions and cross-checked by an automated audit.",
     "Evidence on the three questions above, including equivalence tests against a smallest effect of interest, event-level and onset "
     "evaluation, country-identity baselines and a within/between decomposition of the CI signal.",
     "A decision-rule table for teams that build early-warning systems from published economic evidence, and a pre-specified test of a "
     "fallback policy on 2023-2025 data."])
P("Section 2 reviews related work. Section 3 describes the data and the replication design, Section 4 the forecasting and decision framework and "
  "Section 5 the results. Section 6 discusses the decision rules and limitations, and Section 7 concludes.")

H1("Related work")
H2("Currency internationalization, institutions and exchange-rate risk")
P("The international use of a currency in invoicing, payments and financial transactions changes the exposure of the issuing economy to global "
  "capital flows [eichengreen2018]. Institutional quality, often measured with the Worldwide Governance Indicators (WGI) [kaufmann2011], is argued "
  "to condition how openness translates into exchange-rate outcomes [chinn2006; aman2024], and policy arrangements that support "
  "internationalization affect currency co-movements [an2024]. Threshold models make such conditioning explicit by estimating separate slopes below "
  "and above an estimated IQ threshold [hansen1999; wang2015]. They are estimated in sample with contemporaneous regressors and annual governance "
  "scores spread over the months of the same year, so they describe associations rather than information available in real time [croushore2001].")
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
P("The replication uses the two regression datasets of that earlier working paper, which has not been published. "
  "The CI series and macro controls were exported from the Wind Economic Database and compiled into the regression datasets on 13 June 2023; the original Wind series codes were not "
  "retained, so Supplementary Table S15 documents the variables by their dataset column names; "
  "SHA-256 checksums of the files are recorded in the replication package. Panel A measures CI by the currency's share of SWIFT payments for "
  "China, Hungary, Mexico, Poland, the Russian Federation and South Africa (2012-08 to 2021-12, N = 678). Panel B measures CI by the domestic "
  "currency's share of FX-turnover and adds Brazil, India and Korea (2012-01 to 2022-12, N = 1,188). IQ is the mean of the six WGI dimensions. The "
  "six risk indicators are CPI volatility (CPI_Vol), FX-reserve volatility (FX_Vol), consumption volatility (CE_Vol), real exchange-rate "
  "volatility (ER_Vol), the credit-to-GDP gap (CG_Gap) and unemployment (Unemp). The Panel B ER_Vol series is available for only {B_er_countries} "
  "of the nine countries, so that regression uses N = {B_er_n}. [[tab:data]] summarises the samples.")
TBL("data")
H2("Threshold model and replication protocol")
P("For risk indicator $y$ the single-threshold fixed-effects model is")
EQ(r"y_{it} = \mu_i + \beta_1\, CI_{it}\, \mathbf{1}(q_{it} \le \gamma) + \beta_2\, CI_{it}\, \mathbf{1}(q_{it} > \gamma) + \rho\, y_{i,t-6} + \theta^{\top} X_{it} + \delta^{\top} R_{it} + \varepsilon_{it}", "eq:thr")
P("where $q_{it}$ is IQ, $X_{it}$ are the controls and $R_{it}$ the other five risk indicators. The threshold $\\gamma$ is estimated by "
  "concentrated least squares over the IQ values inside the trimmed range. The test of no threshold uses")
EQ(r"F = \frac{S_0 - S_1(\hat\gamma)}{\hat\sigma^2}, \qquad \hat\sigma^2 = \frac{S_1(\hat\gamma)}{N(T-1)}", "eq:F")
P("where $S_0$ and $S_1$ are the residual sums of squares without and with the threshold. Bootstrap p-values come from $B = {n_boot_thresh}$ "
  "country-block residual bootstraps under the linear null and are computed as")
EQ(r"\hat p = \frac{1 + \#\{b : F^{*}_b \ge F\}}{B + 1}", "eq:p")
P("so the smallest attainable value is {p_min} [davison1997]; Monte Carlo standard errors are reported in the replication package. Three choices "
  "are not stated in the original paper: the dataset columns behind CE_Vol and ER_Vol, the timing of the other-risk controls and the trimming "
  "fraction. We resolve them with a fully reported specification search that scores every candidate against the reported F statistics, "
  "thresholds and regime t statistics (Supplementary Table S2) and apply the selected option to all twelve regressions: full-coverage series, "
  "contemporaneous other risks and 1% trimming, the default of a widely used Stata implementation [wang2015].")
H2("Publication-lag-aware pseudo-real-time panel")
P("For forecasting we build a country-by-month panel for the nine Panel B economies (Core-9) and six further emerging markets (Chile, Colombia, "
  "Indonesia, Malaysia, Thailand, Turkey) used for external transfer and confirmation. REER indices, the US nominal effective exchange rate, CPI, "
  "policy rates and credit come from the BIS, reserves from the IMF and governance and macro controls from the World Bank. Each input enters as it "
  "would have been published at the end of forecast month $t$: monthly REER, CPI, reserves and CI with a one-month lag, so that features use "
  "months up to $t-1$; quarterly credit two months after the quarter; and year-$Y$ WGI and macro controls from September of year $Y+1$, with the "
  "age of the latest release as a feature (Supplementary Table S12). Two limits apply. First, the WGI are revised retroactively and we use the "
  "current vintage, so the IQ series is pseudo-real-time in timing but not in values. Second, the construction and release calendar of the "
  "Wind FX-share series are not documented, so we assess CI release lags of 3, 6 and 12 months and a CI frozen at the training cut-off (Section 5.7). "
  "When the CI coverage ends the last release is held forward with its age. [[fig:fig1]] summarises the information set and the folds.")
FIGR("fig1")
H2("Targets and events")
P("The primary target is forward three-month REER stress,")
EQ(r"V^{(3)}_{i,t} = \sqrt{\tfrac{1}{3}\left(r_{i,t+1}^2 + r_{i,t+2}^2 + r_{i,t+3}^2\right)}", "eq:V")
P("where $r_{i,t}$ is the monthly REER log change in percent. Because consecutive windows share up to two months, high-risk windows overlap and "
  "are not independent events; inference therefore resamples blocks of months. A window is high-risk when $V^{(3)}_{i,t}$ is at or above the 80th "
  "percentile of the training targets of its fold; the thresholds range from {thr_min}% to {thr_max}%. [[tab:folds]] reports the samples and events "
  "of every fold: the development folds (2017-2020) contain {n_pos_dev} high-risk windows in {n_test_dev} country-months and the retrospective "
  "test (2021-2022) {n_pos_lock} in {n_test_lock} ({pos_2021} in 2021 and {pos_2022} in 2022). The secondary target is the maximum three-month "
  "reserve drawdown, $D^{(3)}_{i,t} = \\max\\{0, 1 - \\min_{k \\le 3} R_{i,t+k}/R_{i,t}\\}$. Scoring the main evaluation required outcome data up "
  "to {outcome_to}. An earlier data-availability audit computed target means through 2024-03, but no model was evaluated on origins after "
  "2022-12 before the confirmation protocol was frozen. [[fig:fig2]] shows the stress windows and IQ trajectories.")
TBL("folds")
FIGR("fig2")

H1("Forecasting and decision framework")
H2("System architecture")
P("The framework runs as scripts in a fixed order. (i) A vintage-aware data module applies each publication lag, holds the last release forward "
  "and records data age. (ii) A replication auditor re-estimates the reported regressions and classifies each discrepancy as a convention, a "
  "suspected transcription error or a non-reproduction. (iii) A forecasting module fits all models on frozen splits and writes row-level "
  "predictions to a single prediction store. (iv) A decision module converts probabilities into alerts, review decisions and fallback choices. "
  "An audit script recomputes every reported metric from the prediction store and blocks the manuscript build on any mismatch.")
H2("Temporal protocol")
P("Four expanding development folds test the years 2017-2020 and two retrospective folds test 2021 and 2022. In fold $T$, training origins run "
  "from 2012-01 to August of $T-2$, calibration origins from January to August of $T-1$ and test origins over year $T$. Every origin $s$ used "
  "for fitting or calibration satisfies")
EQ(r"s + h + \ell < \text{first test month}", "eq:mat")
P("with horizon $h$ and REER release lag $\\ell = 1$, so every target used before the test year was published before it; the condition is "
  "asserted in code for $h = 3$ and $h = 6$. Imputation, scaling, thresholds and hyperparameters are estimated on training data only, and "
  "hyperparameters are chosen by AP on three inner expanding folds (grids in Supplementary Table S13).")
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
  "all earlier out-of-sample predictions whose targets had matured ('expanding'). For each model the scheme with the lowest pooled Brier score "
  "on the development folds is locked before the retrospective folds are examined; it was raw for {n_raw_locked} of the 7 models. All decision "
  "analyses use the locked probabilities.")
H2("Metrics and inference")
P("Average precision summarises the precision-recall curve,")
EQ(r"\mathrm{AP} = \sum_{k} (R_k - R_{k-1})\, P_k", "eq:ap")
P("where $P_k$ and $R_k$ are precision and recall at the $k$-th threshold. We report pooled AP over all predictions of a window and the mean of "
  "the fold-specific APs; tables state which is shown. Alerts are issued when the probability $p$ reaches $\\tau = C_{FP}/(C_{FP} + C_{FN})$, "
  "and the expected cost per 100 forecasts is")
EQ(r"\mathrm{Cost} = \frac{100}{n} \sum_{i} \left[ C_{FP}\, \mathbf{1}(p_i \ge \tau,\, y_i = 0) + C_{FN}\, \mathbf{1}(p_i < \tau,\, y_i = 1) \right]", "eq:cost")
P("with $C_{FP} = 1$ and $C_{FN} = 5$ unless stated. Paired differences are assessed with a moving-block bootstrap that resamples calendar months "
  "jointly across countries (1,000 replications) [kunsch1989]. We use blocks of 12 months for the 72-month window and of 6 months for 24-month "
  "windows, because a 24-month window contains only 13 distinct 12-month blocks; results for other lengths are in the replication package. We set "
  "the smallest effect of interest to $\\Delta\\mathrm{AP} = {sesoi}$, about a tenth of the typical gap between a skilled model and the base "
  "rate, and call two models equivalent when the 90% interval lies within $\\pm {sesoi}$, the two one-sided tests procedure [schuirmann1987; "
  "lakens2017].")
H2("Event-level evaluation")
P("Consecutive high-risk origins of a country form an episode. An episode counts as detected when an alert is issued between three months before "
  "its first origin and its last origin; lead time is the distance from the first such alert to the first origin, so it is capped at three. "
  "False alarms are alerts at normal origins outside the three months before an episode, per country-year. Onset evaluation removes origins whose "
  "lagged volatility already exceeds the fold threshold, so it measures the prediction of new stress. The direction analysis splits high-risk "
  "windows by the sign of the three-month REER change (real depreciation versus appreciation).")
H2("Decision layer")
P("The review experiment is a scenario simulation, not an observed workflow. Each month analysts review $k$ country cases; a reviewed case costs "
  "a fee $c$ and is resolved correctly with probability one (an upper bound) or 0.8, and the remaining cases are decided automatically at "
  "$\\tau = 1/6$. Every automated policy (never alert, B0, macro-only EBM, M0, M1 with each calibration, B3, B4) is crossed with four routing "
  "rules: least confident first (smallest $|\\mathrm{logit}\\,p - \\mathrm{logit}\\,\\tau|$), highest probability first, highest lagged volatility first "
  "and random. Cost differences carry paired block-bootstrap intervals.")
H2("Confirmation protocol")
P("Before any outcome after 2022 was evaluated we froze a protocol (SHA-256 {proto_hash12}...) that fixes the sample (Core-9 and the six external "
  "economies), the features (macro and IQ; the CI export ends before 2023), the folds (test years 2023-2025, with 2021-2022 as warm-up folds), "
  "the models (B0, B1, macro EBM and XGBoost), raw probabilities, the costs and a fallback policy. The policy deploys the learned model, chosen on "
  "the development folds as the macro EBM, in year $T$ only if, on the latest twelve matured origins, its AP exceeds that of B0 by at least "
  "$\\delta = {fb_delta}$ and its expected calibration error is at most {fb_ece_cap} (the largest per-fold ECE of B0 in the development folds); "
  "otherwise it deploys B0. Applied once to the retrospective folds, the rule chose {fb_retro}. A post-freeze change to the scoring script, needed "
  "to read the frozen file, is logged in the package; the protocol itself was not changed.")

H1("Results")
H2("Replication of the threshold evidence")
P("[[tab:thresh]] compares the replicated threshold tests with the reported values. With Hansen's residual variance the replicated F statistics "
  "exceed the reported ones by a constant factor within each panel (reported/replicated = {ratio_A} in Panel A and {ratio_B} in Panel B). "
  "Dividing instead by $T(N-1)$ reproduces {n_f_exact} of the 12 reported F statistics to two decimals, which identifies the convention used. "
  "{n_thr_exact} of 12 thresholds are reproduced to four decimals. Of the {n_cells} reported regime coefficients, {n_repro} are reproduced in "
  "coefficient and t statistic, {n_tdiff} in the coefficient only and {n_notrep} are not reproduced; {n_trans} differ from our estimates only by a "
  "digit or a sign and are classified as suspected transcription errors, although we cannot rule out other causes without the original code "
  "(Supplementary Table S1).")
TBL("thresh")
H2("How robust are the thresholds?")
P("The thresholds are often extreme. In {n_edge} of 12 regressions fewer than 10% of observations fall in the low-IQ regime; for Panel A CPI_Vol "
  "the low regime contains {A_cpi_share}% of observations. With 1% trimming {n_sig1} of 12 tests are significant at 5%; with 15% trimming "
  "{n_lost15} of these lose significance (Panel A CPI_Vol: p = {A_cpi_p15}), leaving {robust_list}. In a pseudo-real-time version that lags CI by "
  "one month and uses IQ and annual controls only after their release, {n_sig_prt} tests are significant and {n_both} of the originally "
  "significant ones survive ({both_list}). With single WGI dimensions as threshold variables, {wgi_sig_A} of {wgi_n} Panel A and {wgi_sig_B} of "
  "{wgi_n} Panel B tests are significant (Supplementary Tables S3-S5). [[fig:fig8]] summarises the evidence. The answer to RQ1 is that the "
  "threshold evidence is reproducible as computed but not robust enough to be treated as a stable mechanism.")
FIGR("fig8")
H2("Forecasting benchmark")
P("[[tab:bench]] reports the benchmark. Over all six folds (pooled AP, base rate 0.187) the random forest leads with {b3_all}, followed by "
  "C1 ({c1_all}), XGBoost ({b4_all}) and the persistence rule B0 ({b0_all}); the EBMs reach {m0_all} (M0) and {m1_all} (M1). The ranking is not "
  "stable. In the development folds the random forest is best ({b3_dev}) and B0 weak ({b0_dev}); in the retrospective test B0 reaches {b0_lock} "
  "and C1 {c1_lock}, above every learned model (at most {max_learned_lock}), and the EBMs fall to about {m1_lock}. Paired bootstrap intervals "
  "show that no learned model beats B0 by more than {sesoi} AP with 95% confidence over the six folds; the random forest's gain is "
  "{bt_b3b0_all_L12} [{bt_b3b0_all_L12_lo}, {bt_b3b0_all_L12_hi}], an interval that excludes zero but also includes gains below {sesoi}. Country identity alone (C0) reaches {c0_all}, close to the EBMs, which "
  "indicates that much of the learned models' skill is cross-country level information ([[fig:fig3]]).")
TBL("bench")
FIGR("fig3")
H2("Do CI and IQ add information?")
P("[[tab:ablation]] isolates CI and IQ. Adding CI to the macro feature set lowers pooled AP in {n_ci_neg} of 6 model-window cells, and no "
  "addition of CI, IQ or both raises AP by {sesoi} or more in any of 18 cells. Relative to M0, the CI x IQ interaction changes AP by {e05_m1_all} "
  "over all folds and {e05_m1_lock} in the retrospective test, a placebo macro interaction by {e05_plac_all} and {e05_plac_lock}, and an "
  "unrestricted EBM by {e05_unr_all} and {e05_unr_lock}. The paired bootstrap gives M1 minus M0 = {bt_m1m0_all_L12} [{bt_m1m0_all_L12_lo}, "
  "{bt_m1m0_all_L12_hi}] over six folds; in the retrospective test the 90% interval [{bt_m1m0_lock_L6_lo90}, {bt_m1m0_lock_L6_hi90}] lies within "
  "$\\pm {sesoi}$, so the two models are equivalent there. Over six folds the lower 90% bound ({bt_m1m0_all_L12_lo90}) just crosses "
  "$-{sesoi}$, so equivalence is not established, but a gain is excluded.")
TBL("ablation")
P("Why does the CI signal not help? The EBM explanations ([[fig:fig5]]) rank the FX share {e09_rank_fx} of {e09_nterms} terms and the CI x IQ "
  "pair {e09_rank_inter}; the CI response is almost parallel across IQ levels. Replacing the FX share level by an expanding country mean (between) and the deviation from it (within) raises M0's pooled AP from "
  "{m0_all} to {dec_m0_all}, slightly above the macro-only M0 ({m0_macro_all}); adding a within x IQ or a between x IQ pair gives "
  "{dec_within_all} and {dec_between_all}. The between component carries {imp_between}% of total EBM importance against {imp_within}% for "
  "the within component (Supplementary Table S14). The CI level therefore acts mainly as a country identifier that partly duplicates and "
  "partly distorts the macro information; its time variation carries little stress information, and no CI x IQ pair adds {sesoi} AP.")
FIGR("fig5")
H2("Events, onsets and direction")
P("[[tab:events]] moves from windows to episodes. Over six folds there are {n_episodes_all} episodes ({n_episodes_lock} in 2021-2022). At "
  "$C_{FN} = 5$, B0 detects {ep_rec_b0_all}% of episodes with {ep_fa_b0_all} false alarms per country-year, XGBoost {ep_rec_b4_all}% with "
  "{ep_fa_b4_all} and M1 {ep_rec_m1_all}% with {ep_fa_m1_all}; in the retrospective test M1 detects only {ep_rec_m1_lock}%. When origins "
  "already in stress are removed, AP falls for every model, and in the retrospective test C1 ({on_c1_lock}) and B0 ({on_b0_lock}) still lead "
  "M1 ({on_m1_lock}) in predicting onsets ({on_npos_lock} onset windows). Over six folds most models predict depreciation and appreciation windows with similar AP (B0 {dep_b0_all} and {app_b0_all}, M1 "
  "{dep_m1_all} and {app_m1_all}). In 2021-2022 the persistence-based models detect the {dep_npos_lock} depreciation windows much better "
  "(B0 {dep_b0_lock}, C1 {dep_c1_lock}) than the EBMs (M1 {dep_m1_lock}), so the EBMs' weakness in that period is concentrated in real "
  "depreciations.")
TBL("events")
H2("Calibration and the decision layer")
P("Platt scaling on the eight-month window worsens the pooled Brier score for {n_platt8_worse_all} of {n_models_cal} models (M1: {m1_brier_raw_all} "
  "raw, {m1_brier_platt_8m_all} with eight-month Platt, {m1_brier_platt_expanding_all} with expanding Platt); calibration windows contain as few "
  "as {cal_pos_2020} events. In the automated setting M1 costs {e15_m1auto_b0auto_all_A} per 100 forecasts against {e15_m1auto_b0auto_all_B} for "
  "B0 over six folds (difference {e15_m1auto_b0auto_all} [{e15_m1auto_b0auto_all_lo}, {e15_m1auto_b0auto_all_hi}]), and {e15_m1auto_b0auto_lock_A} "
  "against {e15_m1auto_b0auto_lock_B} in the retrospective test ([[fig:fig4]]). [[tab:review]] reports the review simulation with two reviews per "
  "month and a fee of 0.5. Routing the least confident M1 cases beats random routing in both windows ({e15_m1rev_rand_all} [{e15_m1rev_rand_all_lo}, "
  "{e15_m1rev_rand_all_hi}] and {e15_m1rev_rand_lock} [{e15_m1rev_rand_lock_lo}, {e15_m1rev_rand_lock_hi}]), and review also helps B0 "
  "({e15_b0rev_b0auto_all} [{e15_b0rev_b0auto_all_lo}, {e15_b0rev_b0auto_all_hi}]). Whether M1 with review beats B0 with review depends on "
  "the window: {e15_m1rev_b0rev_all} [{e15_m1rev_b0rev_all_lo}, {e15_m1rev_b0rev_all_hi}] over six folds but {e15_m1rev_b0rev_lock} "
  "[{e15_m1rev_b0rev_lock_lo}, {e15_m1rev_b0rev_lock_hi}] in 2021-2022. Replacing M1 by the macro-only EBM changes the cost by "
  "{e15_m1rev_macro_all} [{e15_m1rev_macro_all_lo}, {e15_m1rev_macro_all_hi}].")
TBL("review")
FIGR("fig4")
FIGR("fig7")
H2("Robustness and information timing")
P("Information timing matters more than model choice. Using month-$t$ REER values, which are not published at the end of month $t$, raises the "
  "pooled AP of M1 from {m1_all} to {spot_m1_all} and of M0 from {m0_all} to {spot_m0_all}; an evaluation without the one-month REER lag would "
  "therefore overstate the EBMs' skill. Longer CI release lags do not hurt: with lags of 3, 6 and 12 months M1 reaches {cilag3_m1_all}, "
  "{cilag6_m1_all} and {cilag12_m1_all} over six folds, and freezing CI at the training cut-off gives {cifrozen_m1_all}. Other variations "
  "(Supplementary Table S6) leave the conclusions unchanged: with a q75 threshold B0, XGBoost and M1 reach {q75_b0_all}, {q75_b4_all} and "
  "{q75_m1_all}; with q90 {q90_b0_all}, {q90_b4_all} and {q90_m1_all}; at a six-month horizon {h6_b0_all}, {h6_b4_all} and {h6_m1_all}. Single WGI "
  "dimensions give M1 an AP between {wgi_ap_min} and {wgi_ap_max}, and in the matched Core-6 sample M1 reaches {c6_sw_m1_all} with SWIFT "
  "features and {c6_noci_m1_all} without CI. Under leave-one-country-out validation the equal-weighted AP is {loco_b0} for B0 and {loco_m1} for "
  "M1, and deleting any single country moves the M1-M0 difference only between {del_min} and {del_max}. Sub-period results, external transfer "
  "and adaptive training weights are reported in Supplementary Tables S7-S9; none of them reverses the ranking of B0 against the learned models. "
  "The answer to RQ2 is negative: CI and IQ add no detectable forecast value beyond persistence and country identity.")
H2("Pre-specified confirmation, 2023-2025")
P("[[tab:confirm]] reports the confirmation period ({conf_all15_npos} high-risk windows in {conf_all15_n} country-months). The fallback rule "
  "deployed B0 in every year ({conf_deployed}), so its cost equals that of B0, {conf_all15_fb_cost} per 100 forecasts against "
  "{conf_all15_never} for never alerting. The rule was conservative: ex post, XGBoost had the highest AP ({conf_all15_b4} against {conf_all15_b0} "
  "for B0) and a lower cost ({conf_all15_b4_cost}), but the cost difference is not significant ({cd_all15_b4_cost} [{cd_all15_b4_cost_lo}, "
  "{cd_all15_b4_cost_hi}]). In the Core-9 countries the AP gain of XGBoost over B0 is {cd_core9_b4_ap} [{cd_core9_b4_ap_lo}, {cd_core9_b4_ap_hi}], a "
  "clear gain that the rule could not capture because it monitored the macro EBM chosen on the development folds; in the six external economies B0 remains best ({conf_ext6_b0} against {conf_ext6_b4}). The macro EBM selected for the rule on the "
  "development folds reaches {conf_all15_m0}, below B0. The confirmation thus supports the conclusion that no learned model dominates "
  "persistence across samples and periods, and shows that a fallback rule protects against weak models at the price of missing gains of "
  "models it does not monitor; a rule that monitored several candidates would have been a reasonable alternative, but it was not pre-specified.")
TBL("confirm")

H1("Discussion")
H2("Decision rules")
P("[[tab:rules]] condenses the evidence into decision rules for teams that build early-warning systems from published economic evidence. The "
  "common thread is that the reference point for any learned model should be a persistence rule and a country-identity model, evaluated with "
  "the information that was actually available, with costs and calibration in view. Under these conditions an institution-conditioned "
  "interaction that is significant in sample adds nothing, and the gains of flexible learners are real in some periods but not stable enough to "
  "deploy without a monitored fallback. This answers RQ3.")
TBL("rules")
H2("Implications for expert and decision-support systems")
P("First, in-sample mechanism evidence and forecast value are different objects; variable selection for an early-warning system should be "
  "validated in a forecasting design. Second, timing errors are a larger threat than model choice: a one-month misalignment of the REER inflated "
  "EBM skill by more than any feature set changed it. Third, the decision layer deserves as much attention as the learner. Short-window "
  "recalibration made probabilities worse, review helped both automated policies tested, and a simple fallback rule avoided the poorly performing models "
  "in 2023-2025. Fourth, a replication audit with recorded checksums, a scored specification search and an automated consistency check turned a set "
  "of significant results into a calibrated statement of what the evidence supports.")
H2("Limitations")
P("The panels are small: nine countries and eleven years in the main evaluation, with {n_episodes_all} overlapping episodes, so AP estimates are "
  "noisy and intervals wide; the 24-month intervals in particular rest on few independent blocks. The 2021-2022 folds had been examined while "
  "the study was designed and are therefore retrospective, which is why we add the confirmation period; the confirmation itself covers only three "
  "years and cannot test CI. The WGI are used in their current vintage. The construction of the Wind CI series could not be re-verified, and the "
  "lag sensitivity only bounds its timing. The dynamic threshold regressions with fixed effects are subject to Nickell bias [nickell1981]; we keep "
  "the original specification for replication. The review experiment uses stylised costs and reviewer accuracies.")

H1("Conclusion")
P("We traced an institution-conditioned currency-internationalization hypothesis from reported threshold estimates to an operational "
  "early-warning task. The reported tests are reproducible but fragile, and the information they encode does not improve the out-of-sample "
  "detection of exchange-rate stress once publication lags, persistence and country identity are taken into account. A pre-specified "
  "confirmation period supports this conclusion for the institutional variables, while showing that flexible learners can beat persistence "
  "in some samples, which is why a monitored fallback rule is preferable to a fixed model choice. The framework, including its decision rules and consistency audit, can be reused to vet other "
  "regression-derived early-warning variables before deployment.")

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
    ["Core-9", "Panel B countries", "2012-01 to 2022-12", "1,188 origins", "FX share (released t-1)", "Forecasting, 2017-2022 folds"],
    ["External-6", "CHL, COL, IDN, MYS, THA, TUR", "2012-01 to 2022-12", "792 origins", "none", "Transfer"],
    ["Confirmation", "Core-9 + External-6", "2023-01 to 2025-12", "540 origins", "none", "Pre-specified confirmation"]],
    notes=f"The Panel B ER_Vol regression uses {V['B_er_n']} observations from {V['B_er_countries']} countries.")

tf = rd("table_folds_samples_events.csv")
TABLES["folds"] = dict(caption="Folds, samples and events (Core-9, h = 3).",
                       header=["Fold", "Role", "Threshold %", "Train origins", "N train (pos.)", "Calibration (pos.)", "N test", "Test pos.", "Episodes"],
                       rows=[[r.split_id[-4:], "development" if r.role == "dev_expanding" else "retrospective", f"{r.threshold_q80:.2f}", r.train_origins,
                              f"{r.n_train} ({r.n_train_pos})", f"{r.n_calib} ({r.n_calib_pos})", str(r.n_test), str(r.n_test_pos), str(r.test_episodes)]
                             for r in tf.itertuples()],
                       notes="Thresholds are the 80th percentile of the training targets of each fold. Training origins are truncated so that every target is published before the test year. Positives by country are listed in the replication package.")

t2a = rd("table2a_threshold_tests.csv")
trim = rd("tableA3_threshold_trimming.csv")
prt = rd("tableA2_threshold_pseudo_realtime.csv")
rows = []
for r in t2a.itertuples():
    p15 = trim[(trim.panel == r.panel) & (trim.risk == r.risk) & (trim.trim == 0.15)]["p_boot"].iloc[0]
    pr = prt[(prt.panel == r.panel) & (prt.risk == r.risk)]["p_boot"].iloc[0]
    rows.append(["A" if r.panel == "A_SWIFT" else "B", r.risk, str(r.n_obs), f"{r.f_published:.2f}", f"{r.f_stat_tn1_convention:.2f}", f"{r.f_stat:.2f}",
                 f"{r.p_boot:.4f}", f"{r.threshold_published:.4f}", f"{r.threshold:.4f}", f"{100 * r.share_obs_regime1:.1f}", f"{p15:.4f}", f"{pr:.4f}"])
TABLES["thresh"] = dict(caption="Replication of the reported threshold tests (threshold variable: IQ).",
                        header=["Panel", "Risk", "N", "F rep.", "F T(N-1)", "F Hansen", "p", "Thr. rep.", "Thr. repl.", "Low regime %", "p 15% trim", "p real-time"],
                        rows=rows, notes=f"p-values from {V['n_boot_thresh']} country-block bootstraps, (1 + k)/(B + 1). Main specification: 1% trimming, contemporaneous other risks.")

t3 = rd("table3_e03_benchmark_comparison.csv")
e16 = rd("table12_e17_e19_onset_direction.csv")
rows = []
for m in ["B0_Historical_Rule", "C0_Country_Dummies", "C1_Country_plus_Persistence", "B1_Regularized_Linear", "B2_Threshold_Model", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
    if m.startswith("C"):
        g = e16[(e16.subset == "All origins") & (e16.model == m)].set_index("evaluation_window")
        a, l = g.loc[WA], g.loc[WL]
        rows.append([MLAB[m], f3(a.AP), f3(a.AP_fold_mean), "", f3(l.AP), f3(l.AP_fold_mean), f3(l.Brier), f1(l.Cost_C5_per100), "raw"])
    else:
        g = t3[t3.model == m].set_index("evaluation_window")
        a, d, l = g.loc[WA], g.loc[WD], g.loc[WL]
        rows.append([MLAB[m], f3(a.AP), f3(a.AP_fold_mean), f3(d.AP), f3(l.AP), f3(l.AP_fold_mean), f3(l.Brier), f1(l.Cost_C5_per100), l.cal_scheme.replace("_", " ")])
TABLES["bench"] = dict(caption="Forecasting benchmark for three-month REER stress (Core-9).",
                       header=["Model", "AP all (pooled)", "AP all (fold mean)", "AP dev (pooled)", "AP retro (pooled)", "AP retro (fold mean)", "Brier retro", "Cost retro", "Calibration"],
                       rows=rows, notes=f"'all': six folds, 648 country-months, {V['n_pos_all']} positives; 'dev': 2017-2020; 'retro': 2021-2022, {V['n_test_lock']} country-months, {V['n_pos_lock']} positives. Cost: expected cost per 100 forecasts at C_FN = 5. Calibration: scheme locked on the development folds. C0 and C1 calibration not locked separately (raw shown).")

t4 = rd("table4a_e04_feature_ablation.csv")
t4b = rd("table4b_e05_interaction_ablation.csv")
rows = []
for m in ["B1_Regularized_Linear", "B4_XGBoost", "M0_EBM_Additive"]:
    rr = [MLAB[m]]
    for w in [WA, WL]:
        g = t4[(t4.model == m) & (t4.evaluation_window == w)].set_index("feature_set")
        rr += [f3(g.loc["F0_Macro_Only", "AP"])] + [f"{g.loc[f, 'Delta_AP_vs_Macro']:+.3f}" for f in ["F1_Macro_plus_CI", "F2_Macro_plus_IQ", "F3_Macro_plus_CI_plus_IQ"]]
    rows.append(rr)
for spec, labl in [("M1_EBM_CIxIQ", "M1 CI x IQ pair vs M0"), ("M_Placebo_MacroInter", "Placebo macro pair vs M0"), ("M_Unrestricted_EBM", "Unrestricted EBM vs M0"), ("B1_Linear_CIxIQ", "Linear CI x IQ vs M0")]:
    rr = [labl]
    for w in [WA, WL]:
        g = t4b[(t4b.evaluation_window == w)].set_index("interaction_spec")
        rr += [f3(g.loc[spec, "AP"]), "", "", f"{g.loc[spec, 'Delta_AP_vs_M0']:+.3f}"]
    rows.append(rr)
TABLES["ablation"] = dict(caption="Contribution of CI, IQ and interactions (pooled AP).",
                          header=["Model / specification", "Macro AP (all)", "+CI", "+IQ", "+CI+IQ", "Macro AP (retro)", "+CI", "+IQ", "+CI+IQ"],
                          rows=rows, notes=f"Upper rows: AP of the macro-only set and changes from adding CI, IQ or both. Lower rows: AP of the interaction specification (first column of each block) and change relative to M0 with all features (last column). Paired block bootstrap for M1 minus M0: six folds {V['bt_m1m0_all_L12']} [{V['bt_m1m0_all_L12_lo']}, {V['bt_m1m0_all_L12_hi']}] (L = 12); retrospective {V['bt_m1m0_lock_L6']} [{V['bt_m1m0_lock_L6_lo']}, {V['bt_m1m0_lock_L6_hi']}] (L = 6). Smallest effect of interest: {V['sesoi']}.")

ep = rd("table13_e18_episode_level.csv")
rows = []
for m in ["B0_Historical_Rule", "C1_Country_plus_Persistence", "B1_Regularized_Linear", "B3_Random_Forest", "B4_XGBoost", "M0_EBM_Additive", "M1_EBM_CIxIQ"]:
    rr = [MLAB[m]]
    for w in [WA, WL]:
        e = ep[(ep.evaluation_window == w) & (ep.model == m)].iloc[0]
        o = e16[(e16.evaluation_window == w) & (e16.model == m)].set_index("subset")
        rr += [f"{100 * e.episode_recall:.0f}", f"{e.false_alarms_per_country_year:.2f}", f3(o.loc["Onset (not in stress at origin)", "AP"]),
               f3(o.loc["Depreciation episodes vs normal", "AP"]), f3(o.loc["Appreciation episodes vs normal", "AP"])]
    rows.append(rr)
TABLES["events"] = dict(caption="Episode-level, onset and direction results.",
                        header=["Model", "Episode recall % (all)", "False alarms / country-year", "Onset AP", "Depr. AP", "Appr. AP", "Episode recall % (retro)", "False alarms", "Onset AP", "Depr. AP", "Appr. AP"],
                        rows=rows, notes=f"Alerts at tau = 1/6. Episodes: {V['n_episodes_all']} (all folds), {V['n_episodes_lock']} (2021-2022). Onset windows: {V['on_npos_all']} (all), {V['on_npos_lock']} (retro). Depr./Appr.: high-risk windows with negative / non-negative three-month REER change evaluated against all normal windows.")

cd = rd("table11b_e15_cost_differences.csv")
short = lambda x: x.replace(" (k=2)", "").replace("low-confidence review", "LC review").replace("volatility review", "vol. review").replace("Macro-only EBM", "Macro EBM")
rows = []
for r in cd[cd.reviewer_acc == 1.0].itertuples():
    r8 = cd[(cd.reviewer_acc == 0.8) & (cd.evaluation_window == r.evaluation_window) & (cd.policy_A == r.policy_A) & (cd.policy_B == r.policy_B)].iloc[0]
    rows.append(["all" if r.evaluation_window == WA else "retro", short(r.policy_A), short(r.policy_B), f1(r.cost_A_per100), f1(r.cost_B_per100),
                 f"{r.Delta_cost_per100:+.1f} [{r.CI95_Low:.1f}, {r.CI95_High:.1f}]", f"{r8.Delta_cost_per100:+.1f} [{r8.CI95_Low:.1f}, {r8.CI95_High:.1f}]"])
TABLES["review"] = dict(caption="Selective-review scenario simulation: expected cost per 100 forecasts and paired differences.",
                        header=["Window", "Policy A", "Policy B", "Cost A", "Cost B", "A - B, accuracy 1.0 [95% CI]", "A - B, accuracy 0.8 [95% CI]"],
                        rows=rows, notes="LC review: least-confident cases reviewed first; vol. review: highest lagged volatility first. Two reviews per month (k = 2), review fee 0.5, C_FN = 5. M1 uses its locked calibration. Block bootstrap: L = 12 (all), L = 6 (retro). Accuracy 1.0 is an upper bound. The full grid of policies, routing rules, budgets and fees is in the replication package.")

t15 = rd("table15_confirmation_2023_2025.csv")
rows = []
for m in ["Rule_Never_Alert", "B0_Historical_Rule", "B1_Regularized_Linear", "M0_EBM_Additive", "B4_XGBoost", "Fallback_policy"]:
    rr = [MLAB[m]]
    for g in ["All 15 countries", "Core-9", "External-6"]:
        x = t15[(t15.countries == g) & (t15.window == "2023-2025") & (t15.model == m)].iloc[0]
        rr += [f3(x.AP) if m != "Rule_Never_Alert" else "", f1(x.Cost_C5_per100)]
    rows.append(rr)
TABLES["confirm"] = dict(caption="Pre-specified confirmation period, forecast origins 2023-2025 (macro and IQ features).",
                         header=["Model", "AP (15)", "Cost (15)", "AP (Core-9)", "Cost (Core-9)", "AP (External-6)", "Cost (External-6)"],
                         rows=rows, notes=f"{V['conf_all15_npos']} high-risk windows in {V['conf_all15_n']} country-months ({V['conf_core9_npos']} Core-9, {V['conf_ext6_npos']} External-6). Pooled AP; cost per 100 forecasts at C_FN = 5; raw probabilities. Fallback deployments: {V['conf_deployed']}. Protocol SHA-256: {V['proto_hash']}.")

TABLES["rules"] = dict(caption="Decision rules derived from the evidence.", header=["Decision", "Rule", "Evidence"], rows=[
    [fill(x) for x in row] for row in [
        ["Feature set", "Use macro-financial (and optionally IQ) features; do not add the CI level", "Adding CI lowered AP in {n_ci_neg} of 6 cells; no addition gained {sesoi} AP"],
        ["Interaction", "Do not hard-code the CI x IQ interaction", "M1 - M0: {bt_m1m0_all_L12} [{bt_m1m0_all_L12_lo}, {bt_m1m0_all_L12_hi}]; equivalent within +/-{sesoi} in 2021-2022"],
        ["Benchmarks", "Always report persistence (B0) and country identity plus persistence (C1)", "Retrospective AP: B0 {b0_lock}, C1 {c1_lock}, best learned {max_learned_lock}"],
        ["Timing", "Lag REER and other monthly inputs to their release; test release-lag sensitivity", "Month-t REER raises M1 AP from {m1_all} to {spot_m1_all}"],
        ["Calibration", "Prefer raw or expanding-window calibration; avoid short windows", "Eight-month Platt worsened Brier for {n_platt8_worse_all} of {n_models_cal} models"],
        ["Analyst review", "Route least-confident cases first", "vs random routing: {e15_m1rev_rand_all} [{e15_m1rev_rand_all_lo}, {e15_m1rev_rand_all_hi}] per 100"],
        ["Deployment", "Deploy a learned model only if it beats B0 by delta on recent matured data and is calibrated; else B0", "2023-2025: rule kept B0 ({conf_all15_fb_cost} vs {conf_all15_never} never-alert); XGBoost cost {conf_all15_b4_cost} (n.s.), Core-9 AP gain {cd_core9_b4_ap} [{cd_core9_b4_ap_lo}, {cd_core9_b4_ap_hi}]"],
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
    ["Tuning", "AP on three inner expanding folds within the training window"],
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


def tex_table(tb, label, num_prefix=""):
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
            lines.insert(lines.index(f"\\begin{{tabular}}{{{spec}}}"), "\\resizebox{\\textwidth}{!}{%")
            lines.append("}")
        if tb.get("notes"):
            lines.append(f"\\par\\vspace{{2pt}}\\parbox{{0.95\\linewidth}}{{\\scriptsize Note: {tex_text(tb['notes'])}}}")
        lines.append(f"\\end{{{env}}}")
    return "\n".join(x for x in lines if x)


def md_table(tb, title):
    esc = lambda s: str(s).replace("|", "/").replace("\n", " ")
    lines = [f"**{title}**", "", "| " + " | ".join(esc(h) for h in tb["header"]) + " |", "|" + "---|" * len(tb["header"])]
    lines += ["| " + " | ".join(esc(c) for c in r) + " |" for r in tb["rows"]]
    if tb.get("notes"):
        lines += ["", f"*Note:* {tb['notes']}"]
    return "\n".join(lines) + "\n"


def used_refs():
    txt = " ".join(it[1] if it[0] == "p" else " ".join(it[1]) for it in S if it[0] in ("p", "bul"))
    return sorted({k for m in CITE_RE.finditer(txt) for k in m.group(1).split("; ")}, key=lambda k: REFS[k][1])


def build_tex(preview=False):
    used = used_refs()
    cls = r"\documentclass[12pt]{article}" + "\n" + r"\usepackage[authoryear,round]{natbib}" if preview else r"\documentclass[preprint,12pt,authoryear]{elsarticle}"
    L = [cls, r"\usepackage[utf8]{inputenc}", r"\usepackage[T1]{fontenc}", r"\usepackage{amsmath,amssymb,graphicx,booktabs,longtable}",
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
    L.append(tex_text("BIS, IMF and World Bank data are public; the Wind-based regression datasets (compiled on 13 June 2023) are licensed and cannot be redistributed, but their variables are documented in Supplementary Table S15 and their SHA-256 checksums are included in the replication package. Code, split definitions, the confirmation protocol and all row-level predictions are provided in the replication package [repository link withheld for double-anonymous review]."))
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
    out += ["\n## Data availability\n", "BIS, IMF and World Bank data are public; the Wind-based regression datasets (compiled on 13 June 2023) are licensed and cannot be redistributed, but their variables are documented in Supplementary Table S15 and their SHA-256 checksums are included in the replication package. Code, split definitions, the confirmation protocol and all row-level predictions are provided in the replication package [repository link withheld for double-anonymous review].\n", "\n## References\n"]
    out += [REFS[k][1] + "\n" for k in used_refs()]
    return "\n".join(out)


def build_supp_md():
    out = ["# Supplementary material", "", f"*{TITLE}*", ""]
    for k, tb in SUPP.items():
        out.append(md_table(tb, f"Table {k}. {tb['caption']}"))
    for k, (fn, cap) in SUPP_FIGS.items():
        out.append(f"![Fig. {k}. {cap}](figures/Fig{k}.png){{width=100%}}\n")
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
                      "**Declaration of competing interest.** The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.", "",
                      "**Funding.** [To be completed by the authors.]", "",
                      "**Acknowledgements.** [To be completed by the authors.]", "",
                      "**Data availability.** BIS, IMF and World Bank data are public. The CI series and macro controls of the original working paper were exported from the Wind Economic Database and compiled into the regression datasets on 13 June 2023 (variables documented by column name in Supplementary Table S15; the original Wind series codes were not retained); Wind data are licensed and cannot be redistributed. Code, split definitions, the frozen confirmation protocol and all row-level predictions are available at https://github.com/reneverland/MacroRisk.", "",
                      "**Original study.** The threshold estimates replicated in this paper come from an unpublished working paper by M. Xu and X. Niu, 'Does Currency Internationalization increase Macro Risk in Emerging Markets? Nonlinear Evidence from Institutional Quality' (drafts dated November 2023 to July 2025).", "",
                      "**Declaration of generative AI and AI-assisted technologies in the writing process.** During the preparation of this work the authors used an AI coding and writing assistant to write analysis scripts and draft parts of the text. After using this tool, the authors reviewed and edited the content as needed and take full responsibility for the content of the publication.", ""])


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
