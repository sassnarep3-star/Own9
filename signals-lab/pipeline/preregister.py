"""Writes registry/preregistration.json (machine-readable pre-registration: hashes of code, parameters and the written protocol)."""
import hashlib, json, datetime
from pathlib import Path
from gates import PREREG_FILES, sha, ALPHA, PREC_MAX_HALFWIDTH, COV_MEAN_TOL, COV_MAX_TOL, BOOT_B, CAL_B
LAB = Path(__file__).resolve().parents[1]
reg = dict(
    session="efe45667", written_utc=datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    splits=dict(burn_in="2015-2017 (fit only)", dev="2018-2022 (hyper-parameter selection)", sealed_test="2023-2025 (single run)", forward_holdout="2026 weeks 1-8 (game level only)"),
    thresholds=dict(alpha_holm=ALPHA, ci_halfwidth_max=PREC_MAX_HALFWIDTH, coverage_mean_abs_err_max=COV_MEAN_TOL, coverage_max_abs_err_max=COV_MAX_TOL, bootstrap_resamples=BOOT_B, calibration_bootstrap=CAL_B,
                    seasons_positive_sealed="at least 2 of 3", seasons_positive_dev="at least 3 of 5"),
    n_strategies_in_family=31, sha256={f: sha(f) for f in PREREG_FILES},
)
(LAB / "registry" / "preregistration.json").write_text(json.dumps(reg, indent=1))
print(json.dumps(reg["sha256"], indent=1))
