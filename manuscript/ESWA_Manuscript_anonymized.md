# Do institutional thresholds improve exchange-rate stress early warning? A replication-to-deployment evaluation with a pre-specified confirmation period

## Abstract

Panel threshold regressions suggest that the macroeconomic effects of currency internationalization (CI) depend on institutional quality (IQ). We test whether such evidence improves early warning of exchange-rate stress. A replication-to-deployment framework links a forensic replication of published threshold estimates to a publication-lag-aware pseudo-real-time backtest and a decision layer. With data for nine emerging economies, all 12 published threshold F statistics are reproduced once a degrees-of-freedom convention is identified, but 4 of 8 significant threshold effects disappear under 15% trimming. In a retrospective out-of-time evaluation (2017-2022, 121 high-risk windows), adding CI never raised average precision (AP) by the smallest effect of interest (0.02), and a CI x IQ interaction did not differ from an additive model (Delta AP = -0.006, 95% block-bootstrap interval [-0.026, 0.011]). No learned model beat a persistence rule by more than 0.02 AP with 95% confidence, and in 2021-2022 the persistence rule ranked best (AP 0.535). Short-window recalibration worsened Brier scores for all 7 models, whereas routing low-confidence cases to analysts lowered expected cost relative to random review. In a pre-specified confirmation period (2023-2025, 15 countries) a frozen fallback rule retained the persistence rule in all three years, although XGBoost outperformed it in the nine core economies. Threshold evidence should pass such an audit before it informs deployed early-warning systems.

**Keywords:** Early warning system; Explainable boosting machine; Panel threshold regression; Replication; Pseudo-real-time evaluation; Selective prediction


## 1. Introduction

Early-warning systems for exchange-rate and balance-of-payments stress are decision-support tools. A model ranks countries or months by risk, and analysts decide where to spend limited monitoring capacity (Kaminsky et al., 1998; Holopainen & Sarlin, 2017). Their value depends on out-of-sample ranking quality, on the calibration of the probabilities shown to users and on the cost of the actions they trigger, not on in-sample fit. Candidate early-warning variables are nevertheless often motivated by in-sample panel regressions. A recurring example is the claim that the macroeconomic effects of currency internationalization (CI) depend on a country's institutional quality (IQ), estimated with fixed-effects panel threshold regressions (Hansen, 1999).

This paper asks whether such threshold evidence survives the move from a regression table to an early-warning system. We organise the study around three questions.

- RQ1 (replication): Can the published threshold estimates be reproduced from the original data, and how sensitive are they to estimation choices that are rarely reported, such as the trimming of the threshold grid and the timing of information?
- RQ2 (forecast value): When every input is restricted to what was published at the forecast date, do CI, IQ and their interaction improve the detection of future exchange-rate stress over persistence, country-identity and macro-only benchmarks by at least a pre-specified smallest effect of interest?
- RQ3 (decision value): Which decision rules, covering model choice, calibration, analyst routing and fallback, minimise expected cost, and do they hold in a confirmation period that was scored only after the protocol had been frozen?

We answer these questions with the data behind an earlier, unsubmitted working paper by the authors on CI, IQ and six macroeconomic risks in emerging economies: a SWIFT-share panel of six countries and an FX-turnover-share panel of nine countries. The first stage is a forensic replication of the published threshold tests and regime coefficients. The second stage embeds the same information in a publication-lag-aware pseudo-real-time backtest for three-month real-effective-exchange-rate (REER) stress. Because the period 2021-2022 had been examined while the study was designed, we treat it as a retrospective out-of-time evaluation and add a confirmation period, 2023-2025, that was scored once under a protocol whose SHA-256 hash was recorded beforehand.

The answers are largely negative, and we report them as such. The published F statistics are reproduced exactly once an unusual degrees-of-freedom convention is recognised, but several thresholds sit at the edge of the data and lose significance under conventional trimming. CI and IQ do not add detectable forecast value, an institution-conditioned interaction is indistinguishable from an additive model, and a persistence rule is as good as or better than the learned models out of time. The contributions are:

- A replication-to-deployment framework that connects a scored replication audit of published panel threshold estimates to a leakage-checked forecasting and decision layer, with every number regenerated from row-level predictions and cross-checked by an automated audit.
- Evidence on the three questions above, including equivalence tests against a smallest effect of interest, event-level and onset evaluation, country-identity baselines and a within/between decomposition of the CI signal.
- A decision-rule table for teams that build early-warning systems from published economic evidence, and a pre-specified test of a fallback policy on 2023-2025 data.

Section 2 reviews related work. Section 3 describes the data and the replication design, Section 4 the forecasting and decision framework and Section 5 the results. Section 6 discusses the decision rules and limitations, and Section 7 concludes.


## 2. Related work


### 2.1. Currency internationalization, institutions and exchange-rate risk

The international use of a currency in invoicing, payments and financial transactions changes the exposure of the issuing economy to global capital flows (Eichengreen et al., 2018). Institutional quality, often measured with the Worldwide Governance Indicators (WGI) (Kaufmann et al., 2011), is argued to condition how openness translates into exchange-rate outcomes (Chinn & Ito, 2006; Aman et al., 2024), and policy arrangements that support internationalization affect currency co-movements (An et al., 2024). Threshold models make such conditioning explicit by estimating separate slopes below and above an estimated IQ threshold (Hansen, 1999; Wang, 2015). They are estimated in sample with contemporaneous regressors and annual governance scores spread over the months of the same year, so they describe associations rather than information available in real time (Croushore & Stark, 2001).


### 2.2. Machine-learning early-warning systems

Early-warning research evaluates signals by their out-of-sample ability to anticipate currency or banking stress (Kaminsky et al., 1998; Frankel & Rose, 1996). Comparisons of machine-learning methods with logit benchmarks find that gains depend on the evaluation design and on the number of independent episodes (Holopainen & Sarlin, 2017; Beutel et al., 2019; Bluwstein et al., 2023). Recent work applies recurrent and convolutional networks to currency and financial crises (Barthélémy et al., 2024; Chen et al., 2024) and adds post-hoc explanations (Reimann, 2024); a study that respects autocorrelation and publication lags reports markedly more modest accuracy than earlier work (Ostrensky & Frota, 2023). Imbalanced targets call for precision-recall metrics (Saito & Rehmsmeier, 2015), and decision-oriented evaluation requires explicit costs of missed and false alarms (Elkan, 2001).


### 2.3. Interpretable models, calibration, drift and selective prediction

Explainable boosting machines (EBMs) are generalized additive models with optional pairwise interactions (Lou et al., 2012; Nori et al., 2019) and suit high-stakes settings where post-hoc explanations of black boxes are unreliable (Rudin, 2019). Random forests (Breiman, 2001) and gradient-boosted trees (Chen & Guestrin, 2016) are strong tabular baselines. Probabilities shown to decision makers should be calibrated on held-out data (Platt, 1999; Niculescu-Mizil & Caruana, 2005), and deployed models need monitoring and fallback rules when the data-generating process drifts (Gama et al., 2014). Selective prediction lets a system defer uncertain cases to humans (Chow, 1970; Geifman & El-Yaniv, 2017). Claims of 'no improvement' require equivalence tests against a smallest effect of interest rather than non-significant differences (Schuirmann, 1987; Lakens, 2017).


## 3. Data and replication design


### 3.1. Original study and data

The replication uses the two regression datasets of the authors' earlier working paper, which was circulated internally and never submitted. The CI series and macro controls were exported from the Wind Economic Database and compiled into the regression datasets on 13 June 2023; the original Wind series codes were not retained, so Supplementary Table S15 documents the variables by their dataset column names; SHA-256 checksums of the files are recorded in the replication package. Panel A measures CI by the currency's share of SWIFT payments for China, Hungary, Mexico, Poland, the Russian Federation and South Africa (2012-08 to 2021-12, N = 678). Panel B measures CI by the domestic currency's share of FX-turnover and adds Brazil, India and Korea (2012-01 to 2022-12, N = 1,188). IQ is the mean of the six WGI dimensions. The six risk indicators are CPI volatility (CPI_Vol), FX-reserve volatility (FX_Vol), consumption volatility (CE_Vol), real exchange-rate volatility (ER_Vol), the credit-to-GDP gap (CG_Gap) and unemployment (Unemp). The Panel B ER_Vol series is available for only 8 of the nine countries, so that regression uses N = 1056. Table 1 summarises the samples.

**Table 1. Samples.**

| Sample | Countries | Period | N | CI measure | Use |
|---|---|---|---|---|---|
| Panel A | CHN, HUN, MEX, POL, RUS, ZAF | 2012-08 to 2021-12 | 678 | SWIFT payment share | Threshold replication |
| Panel B | Panel A + BRA, IND, KOR | 2012-01 to 2022-12 | 1,188 | FX-turnover share | Threshold replication |
| Core-9 | Panel B countries | 2012-01 to 2022-12 | 1,188 origins | FX share (released t-1) | Forecasting, 2017-2022 folds |
| External-6 | CHL, COL, IDN, MYS, THA, TUR | 2012-01 to 2022-12 | 792 origins | none | Transfer |
| Confirmation | Core-9 + External-6 | 2023-01 to 2025-12 | 540 origins | none | Pre-specified confirmation |

*Note:* The Panel B ER_Vol regression uses 1056 observations from 8 countries.


### 3.2. Threshold model and replication protocol

For risk indicator $y$ the single-threshold fixed-effects model is

$$
y_{it} = \mu_i + \beta_1\, CI_{it}\, \mathbf{1}(q_{it} \le \gamma) + \beta_2\, CI_{it}\, \mathbf{1}(q_{it} > \gamma) + \rho\, y_{i,t-6} + \theta^{\top} X_{it} + \delta^{\top} R_{it} + \varepsilon_{it}
$$

where $q_{it}$ is IQ, $X_{it}$ are the controls and $R_{it}$ the other five risk indicators. The threshold $\gamma$ is estimated by concentrated least squares over the IQ values inside the trimmed range. The test of no threshold uses

$$
F = \frac{S_0 - S_1(\hat\gamma)}{\hat\sigma^2}, \qquad \hat\sigma^2 = \frac{S_1(\hat\gamma)}{N(T-1)}
$$

where $S_0$ and $S_1$ are the residual sums of squares without and with the threshold. Bootstrap p-values come from $B = 1999$ country-block residual bootstraps under the linear null and are computed as

$$
\hat p = \frac{1 + \#\{b : F^{*}_b \ge F\}}{B + 1}
$$

so the smallest attainable value is 0.0005 (Davison & Hinkley, 1997); Monte Carlo standard errors are reported in the replication package. Three choices are not stated in the original paper: the dataset columns behind CE_Vol and ER_Vol, the timing of the other-risk controls and the trimming fraction. We resolve them with a fully reported specification search that scores every candidate against the published F statistics, thresholds and regime t statistics (Supplementary Table S2) and apply the selected option to all twelve regressions: full-coverage series, contemporaneous other risks and 1% trimming, the default of a widely used Stata implementation (Wang, 2015).


### 3.3. Publication-lag-aware pseudo-real-time panel

For forecasting we build a country-by-month panel for the nine Panel B economies (Core-9) and six further emerging markets (Chile, Colombia, Indonesia, Malaysia, Thailand, Turkey) used for external transfer and confirmation. REER indices, the US nominal effective exchange rate, CPI, policy rates and credit come from the BIS, reserves from the IMF and governance and macro controls from the World Bank. Each input enters as it would have been published at the end of forecast month $t$: monthly REER, CPI, reserves and CI with a one-month lag, so that features use months up to $t-1$; quarterly credit two months after the quarter; and year-$Y$ WGI and macro controls from September of year $Y+1$, with the age of the latest release as a feature (Supplementary Table S12). Two limits apply. First, the WGI are revised retroactively and we use the current vintage, so the IQ series is pseudo-real-time in timing but not in values. Second, the construction and release calendar of the Wind FX-share series are not documented, so we assess CI release lags of 3, 6 and 12 months and a CI frozen at the training cut-off (Section 5.7). When the CI coverage ends the last release is held forward with its age. Fig. 1 summarises the information set and the folds.

![Fig. 1. Information set at the forecast origin (a) and expanding-window folds (b).](figures/Fig1.png){width=100%}


### 3.4. Targets and events

The primary target is forward three-month REER stress,

$$
V^{(3)}_{i,t} = \sqrt{\tfrac{1}{3}\left(r_{i,t+1}^2 + r_{i,t+2}^2 + r_{i,t+3}^2\right)}
$$

where $r_{i,t}$ is the monthly REER log change in percent. Because consecutive windows share up to two months, high-risk windows overlap and are not independent events; inference therefore resamples blocks of months. A window is high-risk when $V^{(3)}_{i,t}$ is at or above the 80th percentile of the training targets of its fold; the thresholds range from 2.43% to 2.69%. Table 2 reports the samples and events of every fold: the development folds (2017-2020) contain 85 high-risk windows in 432 country-months and the retrospective test (2021-2022) 36 in 216 (10 in 2021 and 26 in 2022). The secondary target is the maximum three-month reserve drawdown, $D^{(3)}_{i,t} = \max\{0, 1 - \min_{k \le 3} R_{i,t+k}/R_{i,t}\}$. Scoring the main evaluation required outcome data up to 2023-04. An earlier data-availability audit computed target means through 2024-03, but no model was evaluated on origins after 2022-12 before the confirmation protocol was frozen. Fig. 2 shows the stress windows and IQ trajectories.

**Table 2. Folds, samples and events (Core-9, h = 3).**

| Fold | Role | Threshold % | Train origins | N train (pos.) | Calibration (pos.) | N test | Test pos. | Episodes |
|---|---|---|---|---|---|---|---|---|
| 2017 | development | 2.43 | 2012-01 to 2015-08 | 396 (80) | 72 (23) | 108 | 18 | 6 |
| 2018 | development | 2.65 | 2012-01 to 2016-08 | 504 (101) | 72 (9) | 108 | 25 | 7 |
| 2019 | development | 2.63 | 2012-01 to 2017-08 | 612 (123) | 72 (22) | 108 | 8 | 6 |
| 2020 | development | 2.69 | 2012-01 to 2018-08 | 720 (144) | 72 (4) | 108 | 34 | 5 |
| 2021 | retrospective | 2.57 | 2012-01 to 2019-08 | 828 (166) | 72 (29) | 108 | 10 | 5 |
| 2022 | retrospective | 2.63 | 2012-01 to 2020-08 | 936 (188) | 72 (6) | 108 | 26 | 5 |

*Note:* Thresholds are the 80th percentile of the training targets of each fold. Training origins are truncated so that every target is published before the test year. Positives by country are listed in the replication package.

![Fig. 2. High-risk windows in the Core-9 panel (a) and pseudo-real-time institutional quality (b). In the test years the evaluation labels of each fold are shown; before 2017 the first-fold threshold is used for illustration.](figures/Fig2.png){width=100%}


## 4. Forecasting and decision framework


### 4.1. System architecture

The framework runs as scripts in a fixed order. (i) A vintage-aware data module applies each publication lag, holds the last release forward and records data age. (ii) A replication auditor re-estimates the published regressions and classifies each discrepancy as a convention, a suspected transcription error or a non-reproduction. (iii) A forecasting module fits all models on frozen splits and writes row-level predictions to a single prediction store. (iv) A decision module converts probabilities into alerts, review decisions and fallback choices. An audit script recomputes every reported metric from the prediction store and blocks the manuscript build on any mismatch.


### 4.2. Temporal protocol

Four expanding development folds test the years 2017-2020 and two retrospective folds test 2021 and 2022. In fold $T$, training origins run from 2012-01 to August of $T-2$, calibration origins from January to August of $T-1$ and test origins over year $T$. Every origin $s$ used for fitting or calibration satisfies

$$
s + h + \ell < \text{first test month}
$$

with horizon $h$ and REER release lag $\ell = 1$, so every target used before the test year was published before it; the condition is asserted in code for $h = 3$ and $h = 6$. Imputation, scaling, thresholds and hyperparameters are estimated on training data only, and hyperparameters are chosen by AP on three inner expanding folds (grids in Supplementary Table S13).


### 4.3. Models

B0 is a persistence rule, a one-variable logistic map from the lagged three-month REER volatility. B1 is ridge regression for the continuous target and L2-regularised logistic regression for the binary target. B2 is a threshold forecaster that estimates an IQ threshold in the training window and fits regime-specific CI slopes. B3 and B4 are a random forest and XGBoost. M0 is an additive EBM, and M1 adds a single CI × IQ pairwise term, the forecasting analogue of the threshold hypothesis. Two country-identity baselines test whether learned models merely recognise countries: C0 is a logistic regression on country indicators and C1 adds the lagged REER volatility. The interaction ablation adds a placebo EBM with a macro-only pair, an unrestricted EBM with ten selected pairs and a linear CI × IQ model. Stochastic learners are averaged over five seeds.


### 4.4. Calibration

Each model produces raw probabilities and two calibrated versions: Platt scaling on the eight-month calibration window, and Platt scaling on all earlier out-of-sample predictions whose targets had matured ('expanding'). For each model the scheme with the lowest pooled Brier score on the development folds is locked before the retrospective folds are examined; it was raw for 6 of the 7 models. All decision analyses use the locked probabilities.


### 4.5. Metrics and inference

Average precision summarises the precision-recall curve,

$$
\mathrm{AP} = \sum_{k} (R_k - R_{k-1})\, P_k
$$

where $P_k$ and $R_k$ are precision and recall at the $k$-th threshold. We report pooled AP over all predictions of a window and the mean of the fold-specific APs; tables state which is shown. Alerts are issued when the probability $p$ reaches $\tau = C_{FP}/(C_{FP} + C_{FN})$, and the expected cost per 100 forecasts is

$$
\mathrm{Cost} = \frac{100}{n} \sum_{i} \left[ C_{FP}\, \mathbf{1}(p_i \ge \tau,\, y_i = 0) + C_{FN}\, \mathbf{1}(p_i < \tau,\, y_i = 1) \right]
$$

with $C_{FP} = 1$ and $C_{FN} = 5$ unless stated. Paired differences are assessed with a moving-block bootstrap that resamples calendar months jointly across countries (1,000 replications) (Kunsch, 1989). We use blocks of 12 months for the 72-month window and of 6 months for 24-month windows, because a 24-month window contains only 13 distinct 12-month blocks; results for other lengths are in the replication package. We set the smallest effect of interest to $\Delta\mathrm{AP} = 0.02$, about a tenth of the typical gap between a skilled model and the base rate, and call two models equivalent when the 90% interval lies within $\pm 0.02$, the two one-sided tests procedure (Schuirmann, 1987; Lakens, 2017).


### 4.6. Event-level evaluation

Consecutive high-risk origins of a country form an episode. An episode counts as detected when an alert is issued between three months before its first origin and its last origin; lead time is the distance from the first such alert to the first origin, so it is capped at three. False alarms are alerts at normal origins outside the three months before an episode, per country-year. Onset evaluation removes origins whose lagged volatility already exceeds the fold threshold, so it measures the prediction of new stress. The direction analysis splits high-risk windows by the sign of the three-month REER change (real depreciation versus appreciation).


### 4.7. Decision layer

The review experiment is a scenario simulation, not an observed workflow. Each month analysts review $k$ country cases; a reviewed case costs a fee $c$ and is resolved correctly with probability one (an upper bound) or 0.8, and the remaining cases are decided automatically at $\tau = 1/6$. Every automated policy (never alert, B0, macro-only EBM, M0, M1 with each calibration, B3, B4) is crossed with four routing rules: least confident first (smallest $|\mathrm{logit}\,p - \mathrm{logit}\,\tau|$), highest probability first, highest lagged volatility first and random. Cost differences carry paired block-bootstrap intervals.


### 4.8. Confirmation protocol

Before any outcome after 2022 was evaluated we froze a protocol (SHA-256 910490582b8d...) that fixes the sample (Core-9 and the six external economies), the features (macro and IQ; the CI export ends before 2023), the folds (test years 2023-2025, with 2021-2022 as warm-up folds), the models (B0, B1, macro EBM and XGBoost), raw probabilities, the costs and a fallback policy. The policy deploys the learned model, chosen on the development folds as the macro EBM, in year $T$ only if, on the latest twelve matured origins, its AP exceeds that of B0 by at least $\delta = 0.02$ and its expected calibration error is at most 0.11 (the largest per-fold ECE of B0 in the development folds); otherwise it deploys B0. Applied once to the retrospective folds, the rule chose 2021: B0; 2022: B0. A post-freeze change to the scoring script, needed to read the frozen file, is logged in the package; the protocol itself was not changed.


## 5. Results


### 5.1. Replication of the threshold evidence

Table 3 compares the replicated threshold tests with the published values. With Hansen's residual variance the replicated F statistics exceed the published ones by a constant factor within each panel (published/replicated = 0.841 in Panel A and 0.896 in Panel B). Dividing instead by $T(N-1)$ reproduces 12 of the 12 published F statistics to two decimals, which identifies the convention used. 10 of 12 thresholds are reproduced to four decimals. Of the 24 published regime coefficients, 11 are reproduced in coefficient and t statistic, 3 in the coefficient only and 7 are not reproduced; 3 differ from our estimates only by a digit or a sign and are classified as suspected transcription errors, although we cannot rule out other causes without the original code (Supplementary Table S1).

**Table 3. Replication of the published threshold tests (threshold variable: IQ).**

| Panel | Risk | N | F publ. | F T(N-1) | F Hansen | p | Thr. publ. | Thr. repl. | Low regime % | p 15% trim | p real-time |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | CPI_Vol | 678 | 400.68 | 400.68 | 476.56 | 0.0005 | -0.7870 | -0.7870 | 1.8 | 0.8910 | 0.6190 |
| A | FX_Vol | 678 | 54.62 | 54.62 | 64.97 | 0.0195 | 0.4481 | 0.4481 | 68.4 | 0.0175 | 0.3830 |
| A | CE_Vol | 678 | 120.64 | 120.64 | 143.49 | 0.0180 | -0.7116 | -0.7116 | 7.8 | 0.1650 | 0.0720 |
| A | ER_Vol | 678 | 27.24 | 27.24 | 32.40 | 0.8885 | -0.4764 | -0.4764 | 22.7 | 0.8085 | 0.0600 |
| A | CG_Gap | 678 | 83.12 | 83.12 | 98.86 | 0.0375 | -0.3692 | -0.3692 | 33.3 | 0.0300 | 0.0125 |
| A | Unemp | 678 | 103.64 | 103.64 | 123.27 | 0.0005 | 0.0240 | 0.0240 | 51.8 | 0.0005 | 0.6380 |
| B | CPI_Vol | 1188 | 276.57 | 276.57 | 308.79 | 0.0450 | -0.2560 | -0.2560 | 35.4 | 0.0030 | 0.0310 |
| B | FX_Vol | 1188 | 79.31 | 79.31 | 88.55 | 0.0295 | -0.7541 | -0.7870 | 1.0 | 0.1390 | 0.0135 |
| B | CE_Vol | 1188 | 219.67 | 219.67 | 245.25 | 0.0005 | -0.7234 | -0.7116 | 5.1 | 0.1595 | 0.0005 |
| B | ER_Vol | 1056 | 104.28 | 104.28 | 118.28 | 0.0605 | -0.7039 | -0.7039 | 8.0 | 0.7235 | 0.5365 |
| B | CG_Gap | 1188 | 34.61 | 34.61 | 38.64 | 0.6500 | -0.1554 | -0.1554 | 44.4 | 0.4705 | 0.7400 |
| B | Unemp | 1188 | 54.34 | 54.34 | 60.67 | 0.1325 | -0.1416 | -0.1416 | 46.5 | 0.0630 | 0.4970 |

*Note:* p-values from 1999 country-block bootstraps, (1 + k)/(B + 1). Main specification: 1% trimming, contemporaneous other risks.


### 5.2. How robust are the thresholds?

The thresholds are often extreme. In 5 of 12 regressions fewer than 10% of observations fall in the low-IQ regime; for Panel A CPI_Vol the low regime contains 1.8% of observations. With 1% trimming 8 of 12 tests are significant at 5%; with 15% trimming 4 of these lose significance (Panel A CPI_Vol: p = 0.891), leaving Panel A FX_Vol, Panel A CG_Gap, Panel A Unemp, Panel B CPI_Vol. In a pseudo-real-time version that lags CI by one month and uses IQ and annual controls only after their release, 4 tests are significant and 4 of the originally significant ones survive (Panel A CG_Gap, Panel B CPI_Vol, Panel B FX_Vol, Panel B CE_Vol). With single WGI dimensions as threshold variables, 6 of 36 Panel A and 9 of 36 Panel B tests are significant (Supplementary Tables S3-S5). Fig. 3 summarises the evidence. The answer to RQ1 is that the threshold evidence is reproducible as computed but not robust enough to be treated as a stable mechanism.

![Fig. 3. Replicated versus published threshold F statistics (a) and bootstrap p-values under 1% trimming, 15% trimming and the pseudo-real-time specification (b).](figures/Fig3.png){width=100%}


### 5.3. Forecasting benchmark

Table 4 reports the benchmark. Over all six folds (pooled AP, base rate 0.187) the random forest leads with 0.506, followed by C1 (0.471), XGBoost (0.460) and the persistence rule B0 (0.440); the EBMs reach 0.386 (M0) and 0.381 (M1). The ranking is not stable. In the development folds the random forest is best (0.535) and B0 weak (0.405); in the retrospective test B0 reaches 0.535 and C1 0.574, above every learned model (at most 0.489), and the EBMs fall to about 0.307. Paired bootstrap intervals show that no learned model beats B0 by more than 0.02 AP with 95% confidence over the six folds; the random forest's gain is 0.066 [0.001, 0.187], an interval that excludes zero but also includes gains below 0.02. Country identity alone (C0) reaches 0.378, close to the EBMs, which indicates that much of the learned models' skill is cross-country level information (Fig. 4).

**Table 4. Forecasting benchmark for three-month REER stress (Core-9).**

| Model | AP all (pooled) | AP all (fold mean) | AP dev (pooled) | AP retro (pooled) | AP retro (fold mean) | Brier retro | Cost retro | Calibration |
|---|---|---|---|---|---|---|---|---|
| B0 Persistence | 0.440 | 0.377 | 0.405 | 0.535 | 0.475 | 0.111 | 41.2 | raw |
| C0 Country identity | 0.378 | 0.434 |  | 0.480 | 0.474 | 0.126 | 50.0 | raw |
| C1 Country + persistence | 0.471 | 0.436 |  | 0.574 | 0.531 | 0.116 | 50.0 | raw |
| B1 Ridge / logistic | 0.372 | 0.398 | 0.444 | 0.349 | 0.349 | 0.194 | 54.2 | raw |
| B2 Threshold model | 0.396 | 0.466 | 0.427 | 0.365 | 0.396 | 0.141 | 53.7 | platt expanding |
| B3 Random forest | 0.506 | 0.420 | 0.535 | 0.489 | 0.394 | 0.117 | 47.7 | raw |
| B4 XGBoost | 0.460 | 0.416 | 0.517 | 0.424 | 0.375 | 0.121 | 52.8 | raw |
| M0 EBM additive | 0.386 | 0.406 | 0.482 | 0.306 | 0.354 | 0.148 | 66.7 | raw |
| M1 EBM + CI x IQ | 0.381 | 0.400 | 0.447 | 0.307 | 0.358 | 0.148 | 66.7 | raw |

*Note:* 'all': six folds, 648 country-months, 121 positives; 'dev': 2017-2020; 'retro': 2021-2022, 216 country-months, 36 positives. Cost: expected cost per 100 forecasts at C_FN = 5. Calibration: scheme locked on the development folds. C0 and C1 calibration not locked separately (raw shown).

![Fig. 4. (a) Pooled AP in the development and retrospective folds with fold-mean AP marked; dotted lines give the base rates. (b) Pooled AP over six folds by feature set. (c) Paired block-bootstrap intervals (L = 12) for M1 against each benchmark over six folds; the shaded band is the smallest effect of interest.](figures/Fig4.png){width=100%}


### 5.4. Do CI and IQ add information?

Table 5 isolates CI and IQ. Adding CI to the macro feature set lowers pooled AP in 6 of 6 model-window cells, and no addition of CI, IQ or both raises AP by 0.02 or more in any of 18 cells. Relative to M0, the CI × IQ interaction changes AP by -0.006 over all folds and +0.000 in the retrospective test, a placebo macro interaction by +0.004 and +0.009, and an unrestricted EBM by +0.025 and +0.033. The paired bootstrap gives M1 minus M0 = -0.006 [-0.026, 0.011] over six folds; in the retrospective test the 90% interval [-0.005, 0.009] lies within $\pm 0.02$, so the two models are equivalent there. Over six folds the lower 90% bound (-0.022) just crosses $-0.02$, so equivalence is not established, but a gain is excluded.

**Table 5. Contribution of CI, IQ and interactions (pooled AP).**

| Model / specification | Macro AP (all) | +CI | +IQ | +CI+IQ | Macro AP (retro) | +CI | +IQ | +CI+IQ |
|---|---|---|---|---|---|---|---|---|
| B1 Ridge / logistic | 0.379 | -0.039 | +0.004 | -0.007 | 0.364 | -0.021 | -0.046 | -0.015 |
| B4 XGBoost | 0.454 | -0.005 | -0.004 | +0.005 | 0.433 | -0.010 | -0.003 | -0.008 |
| M0 EBM additive | 0.402 | -0.018 | +0.011 | -0.015 | 0.359 | -0.033 | +0.004 | -0.053 |
| M1 CI x IQ pair vs M0 | 0.381 |  |  | -0.006 | 0.307 |  |  | +0.000 |
| Placebo macro pair vs M0 | 0.390 |  |  | +0.004 | 0.315 |  |  | +0.009 |
| Unrestricted EBM vs M0 | 0.412 |  |  | +0.025 | 0.340 |  |  | +0.033 |
| Linear CI x IQ vs M0 | 0.351 |  |  | -0.035 | 0.312 |  |  | +0.005 |

*Note:* Upper rows: AP of the macro-only set and changes from adding CI, IQ or both. Lower rows: AP of the interaction specification (first column of each block) and change relative to M0 with all features (last column). Paired block bootstrap for M1 minus M0: six folds -0.006 [-0.026, 0.011] (L = 12); retrospective 0.000 [-0.006, 0.011] (L = 6). Smallest effect of interest: 0.02.

Why does the CI signal not help? The EBM explanations (Fig. 5) rank the FX share 4 of 24 terms and the CI × IQ pair 20; the CI response is almost parallel across IQ levels. Replacing the FX share level by an expanding country mean (between) and the deviation from it (within) raises M0's pooled AP from 0.386 to 0.415, slightly above the macro-only M0 (0.402); adding a within × IQ or a between × IQ pair gives 0.419 and 0.413. The between component carries 5.6% of total EBM importance against 2.1% for the within component (Supplementary Table S14). The CI level therefore acts mainly as a country identifier that partly duplicates and partly distorts the macro information; its time variation carries little stress information, and no CI × IQ pair adds 0.02 AP.

![Fig. 5. EBM CI × IQ surface with sparse cells masked (a), CI response at three IQ levels with fold variability (b) and raw M1 probabilities with high-risk labels for four countries (c).](figures/Fig5.png){width=100%}


### 5.5. Events, onsets and direction

Table 6 moves from windows to episodes. Over six folds there are 31 episodes (10 in 2021-2022). At $C_{FN} = 5$, B0 detects 90% of episodes with 2.17 false alarms per country-year, XGBoost 94% with 2.13 and M1 87% with 1.76; in the retrospective test M1 detects only 70%. When origins already in stress are removed, AP falls for every model, and in the retrospective test C1 (0.509) and B0 (0.295) still lead M1 (0.269) in predicting onsets (20 onset windows). Over six folds most models predict depreciation and appreciation windows with similar AP (B0 0.277 and 0.345, M1 0.234 and 0.254). In 2021-2022 the persistence-based models detect the 15 depreciation windows much better (B0 0.488, C1 0.511) than the EBMs (M1 0.165), so the EBMs' weakness in that period is concentrated in real depreciations.

**Table 6. Episode-level, onset and direction results.**

| Model | Episode recall % (all) | False alarms / country-year | Onset AP | Depr. AP | Appr. AP | Episode recall % (retro) | False alarms | Onset AP | Depr. AP | Appr. AP |
|---|---|---|---|---|---|---|---|---|---|---|
| B0 Persistence | 90 | 2.17 | 0.217 | 0.277 | 0.345 | 90 | 2.94 | 0.295 | 0.488 | 0.357 |
| C1 Country + persistence | 90 | 2.06 | 0.306 | 0.323 | 0.331 | 80 | 3.06 | 0.509 | 0.511 | 0.401 |
| B1 Ridge / logistic | 94 | 1.78 | 0.350 | 0.216 | 0.261 | 90 | 2.89 | 0.414 | 0.197 | 0.260 |
| B3 Random forest | 94 | 2.57 | 0.324 | 0.366 | 0.350 | 90 | 4.17 | 0.297 | 0.450 | 0.299 |
| B4 XGBoost | 94 | 2.13 | 0.371 | 0.309 | 0.317 | 90 | 3.28 | 0.354 | 0.297 | 0.302 |
| M0 EBM additive | 87 | 1.70 | 0.332 | 0.241 | 0.252 | 70 | 2.22 | 0.268 | 0.166 | 0.226 |
| M1 EBM + CI x IQ | 87 | 1.76 | 0.322 | 0.234 | 0.254 | 70 | 2.22 | 0.269 | 0.165 | 0.228 |

*Note:* Alerts at tau = 1/6. Episodes: 31 (all folds), 10 (2021-2022). Onset windows: 67 (all), 20 (retro). Depr./Appr.: high-risk windows with negative / non-negative three-month REER change evaluated against all normal windows.


### 5.6. Calibration and the decision layer

Platt scaling on the eight-month window worsens the pooled Brier score for 7 of 7 models (M1: 0.133 raw, 0.201 with eight-month Platt, 0.141 with expanding Platt); calibration windows contain as few as 4 events. In the automated setting M1 costs 43.4 per 100 forecasts against 53.4 for B0 over six folds (difference -10.0 [-36.3, 4.9]), and 66.7 against 41.2 in the retrospective test (Fig. 6). Table 7 reports the review simulation with two reviews per month and a fee of 0.5. Routing the least confident M1 cases beats random routing in both windows (-7.8 [-16.5, -0.3] and -13.0 [-30.0, -3.3]), and review also helps B0 (-6.5 [-14.2, -0.3]). Whether M1 with review beats B0 with review depends on the window: -9.9 [-30.9, 0.5] over six folds but 13.9 [-4.6, 22.2] in 2021-2022. Replacing M1 by the macro-only EBM changes the cost by 0.6 [-8.6, 3.5].

**Table 7. Selective-review scenario simulation: expected cost per 100 forecasts and paired differences.**

| Window | Policy A | Policy B | Cost A | Cost B | A - B, accuracy 1.0 [95% CI] | A - B, accuracy 0.8 [95% CI] |
|---|---|---|---|---|---|---|
| all | M1 + LC review | B0 + LC review | 37.0 | 46.9 | -9.9 [-30.9, 0.5] | -9.1 [-29.1, 0.8] |
| all | M1 + LC review | B0 automated | 37.0 | 53.4 | -16.4 [-42.7, -3.4] | -8.3 [-33.3, 3.5] |
| all | M1 + LC review | Never alert + vol. review | 37.0 | 60.5 | -23.5 [-49.4, -3.5] | -26.9 [-53.7, -6.6] |
| all | M1 + LC review | M1 + random review | 37.0 | 44.8 | -7.8 [-16.5, -0.3] | -7.5 [-15.4, -0.2] |
| all | M1 + LC review | Macro EBM + LC review | 37.0 | 36.4 | +0.6 [-8.6, 3.5] | -0.7 [-9.3, 2.3] |
| all | M1 automated | B0 automated | 43.4 | 53.4 | -10.0 [-36.3, 4.9] | -10.0 [-36.3, 4.9] |
| all | M1 Platt 8m automated | M1 raw automated | 70.5 | 43.4 | +27.2 [13.9, 57.9] | +27.2 [13.9, 57.9] |
| all | B0 + LC review | B0 automated | 46.9 | 53.4 | -6.5 [-14.2, -0.3] | +0.8 [-5.7, 5.9] |
| all | B0 + LC review | Never alert + vol. review | 46.9 | 60.5 | -13.6 [-23.8, 4.2] | -17.8 [-29.4, 0.4] |
| all | B0 automated | Never alert | 53.4 | 93.4 | -40.0 [-63.1, -13.9] | -40.0 [-63.1, -13.9] |
| retro | M1 + LC review | B0 + LC review | 50.0 | 36.1 | +13.9 [-4.6, 22.2] | +13.9 [-3.8, 22.3] |
| retro | M1 + LC review | B0 automated | 50.0 | 41.2 | +8.8 [-9.3, 14.8] | +17.3 [0.3, 23.1] |
| retro | M1 + LC review | Never alert + vol. review | 50.0 | 43.5 | +6.5 [-22.2, 18.1] | +2.4 [-27.2, 14.6] |
| retro | M1 + LC review | M1 + random review | 50.0 | 63.0 | -13.0 [-30.0, -3.3] | -11.9 [-28.0, -2.1] |
| retro | M1 + LC review | Macro EBM + LC review | 50.0 | 44.4 | +5.6 [-4.2, 10.6] | +4.1 [-4.9, 8.8] |
| retro | M1 automated | B0 automated | 66.7 | 41.2 | +25.5 [-1.4, 40.3] | +25.5 [-1.4, 40.3] |
| retro | M1 Platt 8m automated | M1 raw automated | 74.1 | 66.7 | +7.4 [-2.8, 24.1] | +7.4 [-2.8, 24.1] |
| retro | B0 + LC review | B0 automated | 36.1 | 41.2 | -5.1 [-15.7, 1.9] | +3.4 [-4.7, 8.5] |
| retro | B0 + LC review | Never alert + vol. review | 36.1 | 43.5 | -7.4 [-32.4, 12.0] | -11.5 [-36.5, 8.9] |
| retro | B0 automated | Never alert | 41.2 | 83.3 | -42.1 [-78.2, -5.6] | -42.1 [-78.2, -5.6] |

*Note:* LC review: least-confident cases reviewed first; vol. review: highest lagged volatility first. Two reviews per month (k = 2), review fee 0.5, C_FN = 5. M1 uses its locked calibration. Block bootstrap: L = 12 (all), L = 6 (retro). Accuracy 1.0 is an upper bound. The full grid of policies, routing rules, budgets and fees is in the replication package.

![Fig. 6. Reliability of M1 under three calibration schemes and of B0 in the retrospective test (a), expected cost under asymmetric losses over six folds (b) and recall under monthly review quotas over six folds (c).](figures/Fig6.png){width=100%}

![Fig. 7. Expected cost against the share of cases reviewed (six folds, review fee 0.5) for selected automated policies and routing rules, with reviewer accuracy 1.0 (a, upper bound) and 0.8 (b).](figures/Fig7.png){width=100%}


### 5.7. Robustness and information timing

Information timing matters more than model choice. Using month-$t$ REER values, which are not published at the end of month $t$, raises the pooled AP of M1 from 0.381 to 0.474 and of M0 from 0.386 to 0.468; an evaluation without the one-month REER lag would therefore overstate the EBMs' skill. Longer CI release lags do not hurt: with lags of 3, 6 and 12 months M1 reaches 0.415, 0.395 and 0.403 over six folds, and freezing CI at the training cut-off gives 0.376. Other variations (Supplementary Table S6) leave the conclusions unchanged: with a q75 threshold B0, XGBoost and M1 reach 0.541, 0.583 and 0.538; with q90 0.182, 0.244 and 0.287; at a six-month horizon 0.493, 0.413 and 0.378. Single WGI dimensions give M1 an AP between 0.353 and 0.391, and in the matched Core-6 sample M1 reaches 0.430 with SWIFT features and 0.394 without CI. Under leave-one-country-out validation the equal-weighted AP is 0.414 for B0 and 0.405 for M1, and deleting any single country moves the M1-M0 difference only between -0.011 and -0.001. Sub-period results, external transfer and adaptive training weights are reported in Supplementary Tables S7-S9; none of them reverses the ranking of B0 against the learned models. The answer to RQ2 is negative: CI and IQ add no detectable forecast value beyond persistence and country identity.


### 5.8. Pre-specified confirmation, 2023-2025

Table 8 reports the confirmation period (84 high-risk windows in 540 country-months). The fallback rule deployed B0 in every year (2023: B0, 2024: B0, 2025: B0), so its cost equals that of B0, 53.7 per 100 forecasts against 77.8 for never alerting. The rule was conservative: ex post, XGBoost had the highest AP (0.437 against 0.383 for B0) and a lower cost (41.7), but the cost difference is not significant (-12.0 [-31.1, 2.4]). In the Core-9 countries the AP gain of XGBoost over B0 is 0.168 [0.063, 0.312], a clear gain that the rule could not capture because it monitored the macro EBM chosen on the development folds; in the six external economies B0 remains best (0.433 against 0.311). The macro EBM selected for the rule on the development folds reaches 0.301, below B0. The confirmation thus supports the conclusion that no learned model dominates persistence across samples and periods, and shows that a fallback rule protects against weak models at the price of missing gains of models it does not monitor; a rule that monitored several candidates would have been a reasonable alternative, but it was not pre-specified.

**Table 8. Pre-specified confirmation period, forecast origins 2023-2025 (macro and IQ features).**

| Model | AP (15) | Cost (15) | AP (Core-9) | Cost (Core-9) | AP (External-6) | Cost (External-6) |
|---|---|---|---|---|---|---|
| Never alert |  | 77.8 |  | 72.5 |  | 85.6 |
| B0 Persistence | 0.383 | 53.7 | 0.378 | 52.8 | 0.433 | 55.1 |
| B1 Ridge / logistic | 0.261 | 55.4 | 0.412 | 42.6 | 0.221 | 74.5 |
| M0 EBM additive | 0.301 | 49.1 | 0.401 | 40.4 | 0.229 | 62.0 |
| B4 XGBoost | 0.437 | 41.7 | 0.545 | 37.3 | 0.311 | 48.1 |
| Fallback policy | 0.383 | 53.7 | 0.378 | 52.8 | 0.433 | 55.1 |

*Note:* 84 high-risk windows in 540 country-months (47 Core-9, 37 External-6). Pooled AP; cost per 100 forecasts at C_FN = 5; raw probabilities. Fallback deployments: 2023: B0, 2024: B0, 2025: B0. Protocol SHA-256: 910490582b8dc40cfef8880dfcbc67bfa0786ea3867fead9de8d8ccf3718f65d.


## 6. Discussion


### 6.1. Decision rules

Table 9 condenses the evidence into decision rules for teams that build early-warning systems from published economic evidence. The common thread is that the reference point for any learned model should be a persistence rule and a country-identity model, evaluated with the information that was actually available, with costs and calibration in view. Under these conditions an institution-conditioned interaction that is significant in sample adds nothing, and the gains of flexible learners are real in some periods but not stable enough to deploy without a monitored fallback. This answers RQ3.

**Table 9. Decision rules derived from the evidence.**

| Decision | Rule | Evidence |
|---|---|---|
| Feature set | Use macro-financial (and optionally IQ) features; do not add the CI level | Adding CI lowered AP in 6 of 6 cells; no addition gained 0.02 AP |
| Interaction | Do not hard-code the CI x IQ interaction | M1 - M0: -0.006 [-0.026, 0.011]; equivalent within +/-0.02 in 2021-2022 |
| Benchmarks | Always report persistence (B0) and country identity plus persistence (C1) | Retrospective AP: B0 0.535, C1 0.574, best learned 0.489 |
| Timing | Lag REER and other monthly inputs to their release; test release-lag sensitivity | Month-t REER raises M1 AP from 0.381 to 0.474 |
| Calibration | Prefer raw or expanding-window calibration; avoid short windows | Eight-month Platt worsened Brier for 7 of 7 models |
| Analyst review | Route least-confident cases first | vs random routing: -7.8 [-16.5, -0.3] per 100 |
| Deployment | Deploy a learned model only if it beats B0 by delta on recent matured data and is calibrated; else B0 | 2023-2025: rule kept B0 (53.7 vs 77.8 never-alert); XGBoost cost 41.7 (n.s.), Core-9 AP gain 0.168 [0.063, 0.312] |

*Note:* Numbers are pooled over six folds unless stated; intervals are 95% paired block-bootstrap intervals.


### 6.2. Implications for expert and decision-support systems

First, in-sample mechanism evidence and forecast value are different objects; variable selection for an early-warning system should be validated in a forecasting design. Second, timing errors are a larger threat than model choice: a one-month misalignment of the REER inflated EBM skill by more than any feature set changed it. Third, the decision layer deserves as much attention as the learner. Short-window recalibration made probabilities worse, review helped both automated policies tested, and a simple fallback rule avoided the poorly performing models in 2023-2025. Fourth, a replication audit with recorded checksums, a scored specification search and an automated consistency check turned a set of significant results into a calibrated statement of what the evidence supports.


### 6.3. Limitations

The panels are small: nine countries and eleven years in the main evaluation, with 31 overlapping episodes, so AP estimates are noisy and intervals wide; the 24-month intervals in particular rest on few independent blocks. The 2021-2022 folds had been examined while the study was designed and are therefore retrospective, which is why we add the confirmation period; the confirmation itself covers only three years and cannot test CI. The WGI are used in their current vintage. The construction of the Wind CI series could not be re-verified, and the lag sensitivity only bounds its timing. The dynamic threshold regressions with fixed effects are subject to Nickell bias (Nickell, 1981); we keep the original specification for replication. The review experiment uses stylised costs and reviewer accuracies.


## 7. Conclusion

We traced an institution-conditioned currency-internationalization hypothesis from published threshold estimates to an operational early-warning task. The published tests are reproducible but fragile, and the information they encode does not improve the out-of-sample detection of exchange-rate stress once publication lags, persistence and country identity are taken into account. A pre-specified confirmation period supports this conclusion for the institutional variables, while showing that flexible learners can beat persistence in some samples, which is why a monitored fallback rule is preferable to a fixed model choice. The framework, including its decision rules and consistency audit, can be reused to vet other regression-derived early-warning variables before deployment.


## Data availability

BIS, IMF and World Bank data are public; the Wind-based regression datasets (compiled on 13 June 2023) are licensed and cannot be redistributed, but their variables are documented in Supplementary Table S15 and their SHA-256 checksums are included in the replication package. Code, split definitions, the confirmation protocol and all row-level predictions are provided in the replication package [repository link withheld for double-anonymous review].


## References

Aman, Z., Granville, B., Mallick, S. K., & Nemlioglu, I. (2024). Does greater financial openness promote external competitiveness in emerging markets? The role of institutional quality. International Journal of Finance & Economics, 29(1), 486-510. https://doi.org/10.1002/ijfe.2695

An, J., Kim, H. S., & Park, B. (2024). Do China's policy measures for RMB internationalization foster currency co-movements? International Review of Economics & Finance, 91, 1033-1050. https://doi.org/10.1016/j.iref.2024.01.019

Barthélémy, S., Gautier, V., & Rondeau, F. (2024). Early warning system for currency crises using long short-term memory and gated recurrent unit neural networks. Journal of Forecasting. https://doi.org/10.1002/for.3069

Beutel, J., List, S., & von Schweinitz, G. (2019). Does machine learning help us predict banking crises? Journal of Financial Stability, 45, 100693. https://doi.org/10.1016/j.jfs.2019.100693

Bluwstein, K., Buckmann, M., Joseph, A., Kapadia, S., & Simsek, O. (2023). Credit growth, the yield curve and financial crisis prediction: Evidence from a machine learning approach. Journal of International Economics, 145, 103773. https://doi.org/10.1016/j.jinteco.2023.103773

Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5-32.

Chen, S., Huang, Y., & Ge, L. (2024). An early warning system for financial crises: A temporal convolutional network approach. Technological and Economic Development of Economy. https://doi.org/10.3846/tede.2024.20555

Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. In Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (pp. 785-794).

Chinn, M. D., & Ito, H. (2006). What matters for financial development? Capital controls, institutions, and interactions. Journal of Development Economics, 81(1), 163-192.

Chow, C. K. (1970). On optimum recognition error and reject tradeoff. IEEE Transactions on Information Theory, 16(1), 41-46.

Croushore, D., & Stark, T. (2001). A real-time data set for macroeconomists. Journal of Econometrics, 105(1), 111-130.

Davison, A. C., & Hinkley, D. V. (1997). Bootstrap methods and their application. Cambridge University Press.

Eichengreen, B., Mehl, A., & Chitu, L. (2018). How global currencies work: Past, present, and future. Princeton University Press.

Elkan, C. (2001). The foundations of cost-sensitive learning. In Proceedings of the 17th International Joint Conference on Artificial Intelligence (pp. 973-978).

Frankel, J. A., & Rose, A. K. (1996). Currency crashes in emerging markets: An empirical treatment. Journal of International Economics, 41(3-4), 351-366.

Gama, J., Zliobaite, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014). A survey on concept drift adaptation. ACM Computing Surveys, 46(4), 44.

Geifman, Y., & El-Yaniv, R. (2017). Selective classification for deep neural networks. In Advances in Neural Information Processing Systems 30.

Hansen, B. E. (1999). Threshold effects in non-dynamic panels: Estimation, testing, and inference. Journal of Econometrics, 93(2), 345-368.

Holopainen, M., & Sarlin, P. (2017). Toward robust early-warning models: A horse race, ensembles and model uncertainty. Quantitative Finance, 17(12), 1933-1963.

Kaminsky, G., Lizondo, S., & Reinhart, C. M. (1998). Leading indicators of currency crises. IMF Staff Papers, 45(1), 1-48.

Kaufmann, D., Kraay, A., & Mastruzzi, M. (2011). The Worldwide Governance Indicators: Methodology and analytical issues. Hague Journal on the Rule of Law, 3(2), 220-246.

Kunsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. The Annals of Statistics, 17(3), 1217-1241.

Lakens, D. (2017). Equivalence tests: A practical primer for t tests, correlations, and meta-analyses. Social Psychological and Personality Science, 8(4), 355-362.

Lou, Y., Caruana, R., & Gehrke, J. (2012). Intelligible models for classification and regression. In Proceedings of the 18th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (pp. 150-158).

Nickell, S. (1981). Biases in dynamic models with fixed effects. Econometrica, 49(6), 1417-1426.

Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised learning. In Proceedings of the 22nd International Conference on Machine Learning (pp. 625-632).

Nori, H., Jenkins, S., Koch, P., & Caruana, R. (2019). InterpretML: A unified framework for machine learning interpretability. arXiv preprint arXiv:1909.09223.

Ostrensky, V. P., & Frota, L. M. da (2023). Early warning systems via machine learning: A study of currency crises. Economia Aplicada, 27(3). https://doi.org/10.11606/1980-5330/ea189768

Platt, J. (1999). Probabilistic outputs for support vector machines and comparisons to regularized likelihood methods. In Advances in Large Margin Classifiers (pp. 61-74). MIT Press.

Reimann, C. (2024). Predicting financial crises: An evaluation of machine learning algorithms and model explainability for early warning systems. Review of Evolutionary Political Economy. https://doi.org/10.1007/s43253-024-00114-4

Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions and use interpretable models instead. Nature Machine Intelligence, 1(5), 206-215.

Saito, T., & Rehmsmeier, M. (2015). The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets. PLoS ONE, 10(3), e0118432.

Schuirmann, D. J. (1987). A comparison of the two one-sided tests procedure and the power approach for assessing the equivalence of average bioavailability. Journal of Pharmacokinetics and Biopharmaceutics, 15(6), 657-680.

Wang, Q. (2015). Fixed-effect panel threshold model using Stata. The Stata Journal, 15(1), 121-134.
