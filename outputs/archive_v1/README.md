# Archive of version 1 results

This folder holds the tables, predictions, audited manuscript numbers and source code of version 1, kept before the corrections of version 2:

1. Inner tuning folds now leave a gap of h + 1 months between the last inner-training origin and the first inner-validation month (h = 3 needs 4 months and h = 6 needs 7), instead of a fixed 3-month gap. The imputer and scaler are now fitted inside each inner training fold.
2. Expanding-window calibration now relabels the pooled history with the current fold's threshold instead of each earlier fold's own threshold.

`outputs/tables/table_change_v1_v2.csv` compares every audited number across the two versions.

The frozen 2023-2025 confirmation (`outputs/confirmation/`, `SCORED.lock`) was produced with the version 1 tuning code and was not rescored. The post-hoc rerun of the same period with the corrected code is in step 10 and is labelled exploratory.
