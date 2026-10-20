# MacroRisk ESWA replication package

Code, data and outputs for the manuscript (repository: https://github.com/reneverland/MacroRisk)

> *Do institutional thresholds improve exchange-rate stress early warning? A replication-to-deployment evaluation with a pre-specified confirmation period* (target journal: Expert Systems with Applications).

The study has three parts:

1. **Replication of the reported panel threshold regressions** (Hansen fixed-effects single threshold, IQ as threshold variable) from an unpublished working paper (M. Xu and X. Niu, *Does Currency Internationalization increase Macro Risk in Emerging Markets? Nonlinear Evidence from Institutional Quality*, drafts 2023-2025). Its datasets (stored in `data/raw/historylab/`) were exported from the Wind Economic Database: Panel A uses the SWIFT payment share as CI (6 countries, N = 678), Panel B the FX-turnover share (9 countries, N = 1,188; ER_Vol only for 8 countries, N = 1,056).
2. **Publication-lag-aware pseudo-real-time early warning** of three-month REER stress: development folds 2017-2020 and a retrospective out-of-time evaluation 2021-2022, with persistence, country-identity, linear, threshold, random forest, XGBoost and EBM models, equivalence tests against a smallest effect of interest (ΔAP = 0.02), event-level and onset evaluation, and a decision layer (calibration, costs, analyst-review scenario simulation).
3. **A pre-specified confirmation period, 2023-2025** (15 countries, macro and IQ features, frozen fallback rule), frozen with a recorded SHA-256 hash and scored once.

Every number in the manuscript comes from `outputs/manuscript_numbers.json`, which `src/step8_consistency_audit.py` recomputes from the row-level prediction store and checks against every result table. `src/step7_write_manuscript.py` refuses to build unless `outputs/AUDIT_STATUS` reads `PASS`.

## Layout

```
data/raw/                     BIS, IMF and World Bank downloads; vintage_202610/ holds the IMF IRFCL reserve extension
data/raw/historylab/          original regression datasets (compiled from Wind on 2023-06-13; licensed, not in the public repository) + SHA256SUMS.txt
data/processed/               panel_pseudo_realtime.csv (country x month, publication lags applied), 2010-01 to 2026-08
src/                          pipeline (see below); common.py holds shared settings, splits and metrics
outputs/tables/               all result tables (CSV)
outputs/figures/              fig1-fig8 (PDF + PNG)
outputs/predictions/master/   row-level predictions of every experiment; predictions_master.parquet assembles them
outputs/confirmation/         frozen protocol, its hash, SCORED.lock, confirmation predictions, post-freeze change log
outputs/manuscript_numbers.json, consistency_audit_checks.csv, AUDIT_STATUS
outputs/split_manifest.csv, experiment_config.yaml, data_dictionary.csv, availability_audit.csv
manuscript/                   ESWA_Manuscript_anonymized.tex (elsarticle) / .docx / .md / _preview.pdf,
                              Supplementary_Material.docx/.md, Title_Page.docx, Highlights.docx, highlights.txt, figures/
MANIFEST.sha256               checksums of every file in the package
```

## Environment

Python 3.12; exact versions in `requirements.txt` (`pypandoc_binary` bundles pandoc for the Word files).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash run_all.sh            # MACRORISK_NJOBS sets the number of worker processes (default 8)
```

Every process runs single-threaded (`OMP_NUM_THREADS=1` etc.); parallelism is across joblib worker processes only. Steps 3, 5 and 6 are the expensive ones.

## Pipeline

| Step | Script | Content | Main outputs |
|---|---|---|---|
| 1 | `step1_fetch_and_build_panel.py` | Builds the country-month panel; REER, NEER, CPI, reserves and CI lagged one month; quarterly credit +2 months; year-Y WGI and annual controls from September Y+1; reserves extended with IMF IRFCL after the last DBnomics month | `data/processed/panel_pseudo_realtime.csv`, `data_dictionary.csv` |
| 2 | `step2_e01_e02_audit_and_feasibility.py` | E01 discrepancy audit of the original drafts, E02 feasibility, frozen splits | `e01_*`, `e02_*`, `split_manifest.csv` |
| 2b | `step2b_threshold_replication.py` | Threshold replication: specification search, 12 regressions, regime coefficients, WGI dimensions, pseudo-real-time version, trimming sensitivity; bootstrap p = (1+k)/(B+1), B = 1,999 | `e01b_*`, `table2a-2c`, `tableA1-A3`, `fig8` |
| 3 | `step3_e03_e05_benchmarks_and_ablations.py` | E03 benchmarks (B0-B4, M0, M1), E04 feature ablation, E05 interaction ablation; calibration scheme locked per model on development folds | `table3`, `table4a/4b` |
| 4 | `step4_e06_e08_loco_calib_decision.py` | E06 leave-one-country-out, E07 calibration diagnostics, E08 costs and review quotas | `table5a/5b`, `table6`, `table7a/7b` |
| 5 | `step5_e09_e12_explain_robust_figs.py` | E09 EBM explanations, E10 sub-periods, E11 robustness and timing sensitivity, E12 moving-block bootstrap with TOST, fig1-fig5 | `table8`, `e12_*` |
| 6 | `step6_eswa_enhancements.py` | E13 external transfer (fixed labels), E14 training weights, E15 review scenario simulation with paired cost differences, fig6-fig7 | `table9-11b` |
| 6b | `step6b_event_level.py` | E16 country-identity baselines (C0, C1), E17/E19 onset and direction, E18 episodes, E20 CI within/between decomposition | `table12-14b` |
| 9 | `step9_confirmation.py protocol` / `score` | Freezes and scores the 2023-2025 confirmation (each runs once only) | `table15*`, `outputs/confirmation/` |
| 8 | `step8_consistency_audit.py` | Assembles the prediction store, recomputes all reported metrics, writes the numbers file and the audit status | `manuscript_numbers.json`, `AUDIT_STATUS` |
| 7 | `step7_write_manuscript.py` | Builds the submission files from the audited numbers and tables | `manuscript/*` |

## Key design decisions

- **Threshold replication.** Main specification: 1% trimming, contemporaneous other risks, full-coverage CE_Vol and ER_Vol series, 6-month lagged dependent variable; chosen by a scored specification search against the published values. F statistics are reported under the T(N-1) convention that reproduces the published values and under Hansen's N(T-1).
- **Information timing.** A target window t+1..t+3 is published in t+4; training and calibration origins satisfy s + h + 1 < first test month (asserted in `common.fold_frames`). Month-t REER values are used only in a labelled sensitivity run.
- **Evaluation.** Pooled and fold-mean AP are both reported. Block bootstrap over months (L = 12 for the six-fold window, L = 6 for 24-month windows, 1,000 replications); equivalence = 90% interval within ±0.02.

## Honesty notes

- The main findings are negative: CI and IQ do not add detectable forecast value, the CI x IQ interaction is indistinguishable from the additive EBM, and no learned model beats persistence by more than 0.02 AP with 95% confidence. In the confirmation the fallback rule kept the persistence rule in all three years; XGBoost would have improved AP in the Core-9 countries.
- An earlier internal version used month-t REER values in the features; correcting this lowered the EBMs' AP markedly (the uncorrected run is reported as a sensitivity).
- 2021-2022 had been examined while the study was designed, so it is called a retrospective evaluation; the 2023-2025 confirmation was added for this reason.
- Three published coefficients are classified as suspected transcription errors and seven regime cells are not reproduced (`table2c_published_vs_replicated.csv`).
- After the protocol was frozen, the loader in `step9_confirmation.py` was changed once (see `outputs/confirmation/post_freeze_changes.log`); `common.py` and step 3 still match the hashes recorded in the protocol. The confirmation can no longer be rescored (`SCORED.lock`).

## Placeholders to complete before submission

- CRediT roles, funding and acknowledgements (`Title_Page.docx`).
- `elsarticle.cls` was not installed on the build server; `ESWA_Manuscript_anonymized_preview.pdf` was compiled with the article class to check the LaTeX source.

## Data integrity

```bash
sha256sum -c MANIFEST.sha256                                  # all files except the licensed Wind exports
cd data/raw/historylab && sha256sum -c SHA256SUMS.txt          # Wind exports, if you hold a licensed copy
```
