# MacroRisk ESWA replication package

Code, data and outputs for the manuscript

> *Do institutional thresholds improve exchange-rate stress early warning? An auditable replication-to-prediction evaluation* (target journal: Expert Systems with Applications).

The study has three parts:

1. **Internal replication of the reported panel threshold regressions** (Hansen fixed-effects single threshold, IQ as threshold variable) from an earlier, unpublished working paper with overlapping authorship (*Does Currency Internationalization increase Macro Risk in Emerging Markets? Nonlinear Evidence from Institutional Quality*, drafts 2023-2025). Its datasets (stored in `data/raw/historylab/`, not redistributed) were exported from the Wind Economic Database: Panel A uses the SWIFT payment share as CI (6 countries, N = 678), Panel B the FX-turnover share (9 countries, N = 1,188; ER_Vol only for 8 countries, N = 1,056).
2. **Release-lag-adjusted early warning** of three-month REER stress: development folds 2017-2020 and retrospective test folds 2021-2022, with persistence, country-identity, linear, threshold, random forest, XGBoost and EBM models, paired block-bootstrap intervals and equivalence tests against a smallest effect of interest (ΔAP = 0.02), episode coverage, strict early warning, onset evaluation, and a decision layer (calibration, costs, analyst-review scenarios under several reviewer-error models).
3. **A retrospective extension, 2023-2025** (15 countries, macro and IQ features, frozen fallback rule), frozen with a recorded SHA-256 hash and scored once, plus a separately labelled post-hoc rerun with the corrected tuning code.

Every number in the manuscript comes from `outputs/manuscript_numbers.json`, which `src/step8_consistency_audit.py` recomputes from the row-level prediction store and checks against every result table and the timing audit. `src/step7_write_manuscript.py` refuses to build unless `outputs/AUDIT_STATUS` reads `PASS`.

## Layout

```
data/raw/                     BIS, IMF and World Bank downloads; vintage_202610/ holds the IMF IRFCL reserve extension
data/raw/historylab/          original regression datasets (compiled from Wind on 2023-06-13; licensed, not included) + SHA256SUMS.txt
data/processed/               panel_pseudo_realtime.csv (country x month, publication lags applied), 2010-01 to 2026-08
src/                          pipeline (see below); common.py holds shared settings, splits, maturity rules, metrics and the timing audit
outputs/tables/               all result tables (CSV), including tableS16_timing_audit.csv, tableS17_countries_by_fold.csv, table_change_v1_v2.csv
outputs/figures/              fig1-fig8 (PDF + PNG)
outputs/predictions/master/   row-level predictions with labels of every experiment; predictions_master.parquet assembles them
outputs/confirmation/         frozen protocol, its hash, SCORED.lock, frozen predictions, post-freeze change log
outputs/archive_v1/           first-draft tables, predictions, numbers and source code (before the corrections below)
outputs/manuscript_numbers.json, consistency_audit_checks.csv, AUDIT_STATUS
outputs/split_manifest.csv, experiment_config.yaml, data_dictionary.csv, availability_audit.csv
manuscript/                   ESWA_Manuscript_anonymized.tex (elsarticle) / .docx / .md / _preview.pdf,
                              Supplementary_Material.docx/.md (Tables S1-S17), Title_Page.docx, Highlights.docx, highlights.txt, figures/
MANIFEST.sha256               checksums of every file in the package
```

## Environment

Python 3.12; exact versions in `requirements.txt` (`pypandoc_binary` bundles pandoc for the Word files).

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash run_all.sh            # MACRORISK_NJOBS sets the number of worker processes (default 8)
```

Every process runs single-threaded (`OMP_NUM_THREADS=1` etc.); parallelism is across joblib worker processes only. Steps 3, 5 and 6 are the expensive ones. Steps 1, 2 and 2b need the licensed Wind exports for the threshold replication; all later steps run from `data/processed/` and the stored tables. Seeds: 42, 1024, 2024, 3407, 7777 (models); bootstrap seeds are fixed in the code.

## Pipeline

| Step | Script | Content | Main outputs |
|---|---|---|---|
| 1 | `step1_fetch_and_build_panel.py` | Builds the country-month panel; REER, NEER, CPI, reserves and CI lagged one month; quarterly credit +2 months; year-Y WGI and annual controls from September Y+1 | `data/processed/panel_pseudo_realtime.csv`, `data_dictionary.csv` |
| 2 | `step2_e01_e02_audit_and_feasibility.py` | E01 discrepancy audit of the original drafts, E02 feasibility, frozen splits | `e01_*`, `e02_*`, `split_manifest.csv` |
| 2b | `step2b_threshold_replication.py` | Threshold replication: specification search, 12 regressions, regime coefficients, WGI dimensions, lag-adjusted version, trimming sensitivity; country-block residual bootstrap, p = (1+k)/(B+1), B = 1,999 | `e01b_*`, `table2a-2c`, `tableA1-A3`, `fig8` |
| 3 | `step3_e03_e05_benchmarks_and_ablations.py` | E03 benchmarks (B0-B4, M0, M1), E04 feature ablation, E05 interaction ablation; inner tuning folds with an h + 1 month gap, imputer and scaler fitted per inner fold; calibration scheme selected per model on development folds | `table3`, `table4a/4b` |
| 4 | `step4_e06_e08_loco_calib_decision.py` | E06 leave-one-country-out, E07 calibration diagnostics, E08 costs and review quotas | `table5a/5b`, `table6`, `table7a/7b` |
| 5 | `step5_e09_e12_explain_robust_figs.py` | E09 EBM explanations, E10 sub-periods, E11 robustness and timing sensitivity, E12 moving-block bootstrap with TOST, E21 paired intervals for every ablation increment, Core-6 CI measure and robustness contrast, fig1-fig5 | `table8`, `e12_*`, `table16_e21_*` |
| 6 | `step6_eswa_enhancements.py` | E13 external transfer, E14 training weights, E15 review scenario simulation, E23 reviewer-error models and expected-loss routing, S17 country table, fig6-fig7 | `table9-11c`, `tableS17_*` |
| 6b | `step6b_event_level.py` | E16 country-identity baselines (C0, C1), E17/E19 onset and direction, E18 episode coverage, E22 strict early warning (alerts before episode start, leads, fixed quotas), E20 CI within/between decomposition | `table12-14b`, `table13b_e22_*` |
| 9 | `step9_confirmation.py protocol` / `score` | Freezes and scores the 2023-2025 extension (each runs once only) | `table15`, `table15b/c`, `outputs/confirmation/` |
| 10 | `step10_posthoc_confirmation.py` | Post-hoc 2023-2025 rerun with corrected tuning: macro vs macro+IQ ablation, always-on policies vs the frozen fallback, yearly fallback inputs, exploratory multi-candidate monitor | `table15d-f` |
| 8 | `step8_consistency_audit.py` | Assembles the prediction store, recomputes reported metrics, checks the timing audit, writes the numbers file, the v1-v2 change table and the audit status | `manuscript_numbers.json`, `AUDIT_STATUS`, `table_change_v1_v2.csv` |
| 7 | `step7_write_manuscript.py` | Builds the submission files from the audited numbers and tables | `manuscript/*` |

## Key design decisions

- **Threshold replication.** Main specification: 1% trimming, contemporaneous other risks, full-coverage CE_Vol and ER_Vol series, 6-month lagged dependent variable; chosen by a scored specification search against the reported values. F statistics are reported under the T(N-1) convention that reproduces the reported values and under Hansen's N(T-1). The bootstrap resamples whole country residual series under the static linear null (lagged dependent variable held fixed).
- **Information timing.** A target window t+1..t+3 is published in t+4; every training, calibration, inner-tuning and calibration-history origin satisfies s + h + 1 < first evaluated month. `common.timing_audit()` writes the check for every fold, horizon and stage (Table S16).
- **Evaluation.** Pooled and fold-mean AP are both reported. Block bootstrap over months (L = 12 for the six-fold window, L = 6 for 24- and 36-month windows, 1,000 replications); equivalence = 90% interval within ±0.02.

## Honesty notes

- **Corrections after the first draft (v1 to v2).** The inner tuning folds used a fixed 3-month gap (h = 3 needs 4 months, h = 6 needs 7) and the imputer and scaler were fitted on the whole training window; the expanding calibration history kept each earlier fold's own event threshold. Both were corrected and every learned-model experiment was rerun. `outputs/tables/table_change_v1_v2.csv` lists every audited number of both versions; `outputs/archive_v1/` holds the v1 outputs and code. Two v1 conclusions changed: the CI x IQ interaction is no longer equivalent to the additive EBM in 2021-2022, and the random forest's gain over persistence is no longer distinguishable from zero.
- **Main findings.** No CI or IQ addition in the main FX-share specification raises AP by 0.02, but 9 of 18 paired intervals cannot exclude such a gain; the CI x IQ interaction is not shown to be equivalent to the additive model; no learned model beats persistence over six folds with an interval above zero; C1 and B0 lead in 2021-2022. Learned models do beat persistence under q90 and country-specific thresholds.
- **Retrospective extension.** The frozen fallback kept the persistence rule in all three years; XGBoost would have improved AP in the Core-9 countries. The frozen result was scored with the v1 tuning code and was not rescored (its inner folds fail the timing audit, disclosed in Table S16). The post-hoc rerun with corrected tuning finds an IQ gain for the macro EBM (+0.029 AP, 95% interval 0.002 to 0.042) but not for XGBoost; the multi-candidate monitor was defined after the frozen result and is labelled exploratory.
- 2021-2022 had been examined while the study was designed, so it is called a retrospective test; 2023-2025 is also historical and is called a retrospective extension.
- Three reported coefficients are classified as suspected transcription errors and seven regime cells are not reproduced (`table2c_published_vs_replicated.csv`).
- After the protocol was frozen, the loader in `step9_confirmation.py` was changed once (see `outputs/confirmation/post_freeze_changes.log`). The extension cannot be rescored (`SCORED.lock`).
- An earlier internal version used month-t REER values in the features; correcting this lowered the EBMs' AP markedly (the uncorrected run is reported as a sensitivity).

## Placeholders to complete before submission

- CRediT roles, funding, competing interests, acknowledgements and the AI-use statement (`Title_Page.docx`).
- The anonymous mirror link in the data-availability statement.
- `elsarticle.cls` was not installed on the build server; `ESWA_Manuscript_anonymized_preview.pdf` was compiled with the article class to check the LaTeX source.

## Data integrity

```bash
sha256sum -c MANIFEST.sha256                                  # all files except the licensed Wind exports
cd data/raw/historylab && sha256sum -c SHA256SUMS.txt          # Wind exports, if you hold a licensed copy
```
