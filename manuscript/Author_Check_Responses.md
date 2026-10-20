# Responses to the AUTHOR CHECK comments (revision of 20 October 2026)

Not for submission. Every number below is read from outputs/manuscript_numbers.json, which the consistency audit (step8_consistency_audit.py, status PASS) recomputes from the row-level predictions.

## 1. Working paper and data provenance

- Versions: long draft, file created 15 November 2023 and last revised 14 October 2024; shortened draft dated 23 July 2025. Both report the threshold estimates replicated in the manuscript; Supplementary Table S11 maps every discrepancy found in them.
- Sources stated in the drafts: SWIFT monthly reports (SWIFT share), BIS and World Bank (FX-turnover share), World Bank and Wind (other macro series); quarterly GDP backward-filled to months.
- Files: reg_fxshare_20230613.xlsx (SHA-256 c74aa39b54eda74482b067765a94ae4abeea6f8bbacd39f98cdd009d0c9702cf) and reg_swiftnew_20230613.xlsx (SHA-256 74f746775af0b94679847cbd23899917b2c59afdddb18a236a5f75b1554e51b1), compiled 13 June 2023 (file metadata).
- Not recoverable: the Wind series codes, the exact turnover definition and any interpolation. The Panel B CI column (labelled domestic-currency FX-derivatives turnover) varies monthly in every country (Russia has runs of zeros), so it is not a step-filled triennial survey value, but its construction is stated as unverified (Sections 3.1, 6.3; Table S15).

## 2. Episode counts (34 vs 31)

- Table 2 counts runs of consecutive high-risk origins within each fold: sum 38. 7 of these runs continue from December of the previous fold. The pooled event evaluation joins them, giving 31 episodes; in 2021-2022, 13 fold-level runs minus 3 continuation give 10. The audit checks both identities.
- The figure of 34 in the previous draft came from a different rule (runs separated by a two-month cool-down, counted within folds). All counts now use the contiguous-run rule; Section 4.7 and the Table 2 note state the merging rule.

## 3. M1 - M0 (-0.006 vs -0.005) and intervals shown as -0.000

- Unrounded six-fold M1 - M0 = -0.01034 after the inner-threshold correction (-0.00553 before it). Table 5 and the bootstrap table report the same original-sample estimate (audit check); the earlier -0.005 arose from rounding an already rounded difference. Tables now store 6-8 decimals and are formatted once.
- The bootstrap supplies intervals only; the text no longer reports a bootstrap centre. Six folds [-0.055, 0.044], 2021-2022 [-0.018, 0.062]. A nonzero limit that would round to zero is printed with more digits.

## 4. Inner-fold thresholds, stage audit and final-period data

- Inner tuning labels previously used the outer-fold threshold, whose estimation sample includes the inner validation ranges. Each inner fold now uses the 80th percentile of its own training targets (country-specific and reference-subset rules analogously). Steps 3-6b and the corrected extension (step 10) were rerun; the change is disclosed in Section 4.5 and Appendix A1.
- Supplementary Table S16 adds the column 'Event threshold from' for every stage; all 102 checks of the main and corrected runs pass, and the 15 failures of the archived run are listed.
- REER data run through 2026-08 for all 15 economies. The last origin 2025-12 needs outcomes through 2026-03, published under the one-month lag in 2026-04; all 15 targets are observed (audit check).
- S1-S17 are in Supplementary_Material.docx; S12-S17 are regenerated from the corrected outputs.

## 5. Expanding calibration: scores or labels?

- Only the labels are recomputed with the current fold's threshold; the historical scores are the stored out-of-sample predictions and are not regenerated. Section 4.4 states the score-transfer assumption and Section 6.3 lists it as a limitation.

## 6. Why the macro EBM is the single monitored candidate

- The protocol fixes the candidate as the highest development-fold mean AP among B1, the macro EBM and XGBoost with macro + IQ features: 0.4405 (EBM), 0.4397 (XGBoost), 0.4380 (B1), a near tie (margin 0.0008); Section 4.9 now says so.
- The fallback compares the macro + IQ EBM with B0, as the protocol specifies. The exploratory monitor considers every refitted model other than B0 (C1, B1 and the macro-only and macro + IQ EBMs and XGBoost models). Both use the latest twelve matured origins, up to August of T-1, whose targets are published by December.

## 7. Submission package

- MacroRisk_reproduction_anonymized.zip (code, splits, protocol, timing audit, row-level predictions, S1-S17) is rebuilt with this revision. The manuscript is generated from code, so the editorial comments are not carried over. Title_Page.docx is separate; the declarations and the anonymous mirror link still need the authors.

## 8. Archived XGBoost cost interval

- The archived comparison is [-31.1, 2.4] from the original scoring. The alternative [-29.6, 3.3] came from recomputing the same comparison with a different bootstrap seed. Step 10 now reuses the original seed for archived comparisons, and the audit checks that Table A2 reproduces the original table.

## 9. Fig. 4

- Panel (a) legend moved below the bars, outside the plotting area, font size 10.5.

## Results that changed with the inner-threshold correction

- 2023-2025, macro EBM +IQ: AP 0.040 [-0.060, 0.106] over 15 countries (previously +0.029 [0.002, 0.042]); expected cost -9.1 [-19.1, -3.7]. The abstract, Section 5.9, Table 12 and the conclusion now describe a cost reduction with an AP interval that includes zero.
- Macro+IQ XGBoost vs B0 in Core-9: 0.196 [0.082, 0.326]; over 15 countries 0.064 [-0.009, 0.177]. The exploratory monitor switches to macro-only XGBoost only in 2025.
- Main FX-share ablation: IQ in M0 over six folds is now 0.021 [-0.001, 0.037], the only one of 18 additions to reach the 0.02 margin in point estimate (previously none). M1 - M0 is -0.010; 6 of 18 intervals cannot exclude a 0.02 gain (previously 9). The abstract, a highlight, Sections 1, 5.4, 6.1 and 7 and Table 12 were reworded accordingly; the build stops if any stated direction is contradicted by the numbers.
- Of 766 audited numbers, 468 differ from the first draft (table_change_v1_v2.csv).
