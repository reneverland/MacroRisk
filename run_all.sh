#!/usr/bin/env bash
# Full pipeline. Run from the package root after creating .venv (see README).
set -euo pipefail
cd "$(dirname "$0")"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MACRORISK_NJOBS="${MACRORISK_NJOBS:-8}"
PY="$(pwd)/.venv/bin/python"
mkdir -p outputs/logs
run() { echo "== $*"; (cd src && "$PY" -u "$@") 2>&1 | tee "outputs/logs/$(echo "$*" | tr ' ' '_').txt"; }

run step1_fetch_and_build_panel.py
run step2_e01_e02_audit_and_feasibility.py
run step2b_threshold_replication.py
run step3_e03_e05_benchmarks_and_ablations.py
run step4_e06_e08_loco_calib_decision.py
run step5_e09_e12_explain_robust_figs.py
run step6_eswa_enhancements.py
run step6b_event_level.py

# The confirmation protocol is frozen once and scored once; both commands refuse to run again.
[ -f outputs/confirmation/confirmation_protocol.sha256 ] || run step9_confirmation.py protocol
[ -f outputs/confirmation/SCORED.lock ] || run step9_confirmation.py score
# Post-hoc (exploratory) rerun of 2023-2025 with the corrected tuning; reads but never rescores the frozen result.
run step10_posthoc_confirmation.py

run step8_consistency_audit.py
run step7_write_manuscript.py
