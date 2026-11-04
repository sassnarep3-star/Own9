"""Central configuration: paths, pinned upstream sources, season splits and seeds.

Everything that could be tuned is fixed here *before* evaluation so the test
period is never used for selection (see lab/validation.html, gate G0).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = ROOT / "own9lab" / ".cache"  # re-downloadable snapshots, git-ignored
DERIVED = DATA / "derived"
VERIFY = DATA / "verification"
LAB = ROOT / "lab"
LAB_DATA = LAB / "data"

# ---- Pinned upstream sources (provenance) ---------------------------------
NFLDATA_REPO = "nflverse/nfldata"
NFLDATA_COMMIT = "d48ea039e3683aabdf1f1f610320b3e1d1c86409"  # 2026-11-04T20:15:17Z "Automated data update"
NFLDATA_TARBALL = f"https://codeload.github.com/{NFLDATA_REPO}/tar.gz/{NFLDATA_COMMIT}"
NFLDATA_BLOB = f"https://github.com/{NFLDATA_REPO}/blob/{NFLDATA_COMMIT}"

GC_WHEEL_NAME = "nflgame_redux-3.0.0-py3-none-any.whl"
GC_WHEEL_URL = ("https://files.pythonhosted.org/packages/76/fe/"
                "f1234ab8d4906fb0710f40f5295809e034c9f2d50824b3456b31cb4a2f8c/" + GC_WHEEL_NAME)
GC_WHEEL_SHA256 = "92cef44692808ef2f185ed08940a1afde749ea2ef72a20e01e826bb1ecbd883a"  # PyPI-published digest
GC_PYPI_PAGE = "https://pypi.org/project/nflgame-redux/3.0.0/"

# ---- Study design (fixed before any evaluation) ----------------------------
FIRST_SEASON = 2009          # first season loaded (rating burn-in)
DEV_SEASONS = range(2010, 2020)   # development / in-sample: 2010-2019
TEST_SEASONS = range(2020, 2025)  # holdout test: 2020-2024
FORWARD_SEASONS = range(2025, 2027)  # post-design forward data: 2025 and 2026-to-date
OOS_SEASONS = range(2020, 2027)   # all out-of-sample seasons used by the gates
SEED = 20261104
N_BOOT = 4000
ALPHA = 0.05
