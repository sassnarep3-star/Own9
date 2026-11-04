"""Download pinned upstream snapshots into data/cache and verify integrity.

* nflverse/nfldata at a pinned commit (GitHub codeload tarball). The git blob
  SHA of each extracted file is recomputed and compared with the blob SHA that
  the GitHub API reports for that path at the pinned commit.
* nflgame-redux 3.0.0 wheel from PyPI, checked against the PyPI-published
  SHA-256. The wheel contains archived NFL.com GameCenter JSON feeds
  (2009-2019 seasons), used here as an official-feed cross-check and as the
  player-level data source for prop-combo correlations.
"""
import hashlib, io, json, tarfile, urllib.request
from datetime import datetime, timezone
from . import config as C

FILES = ["data/games.csv", "data/initial_lines.csv", "data/sc_lines.csv"]


def _get(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "own9lab", **({"Accept": accept} if accept else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main():
    C.CACHE.mkdir(parents=True, exist_ok=True)
    manifest = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sources": []}
    # --- nfldata ---
    tar = tarfile.open(fileobj=io.BytesIO(_get(C.NFLDATA_TARBALL)), mode="r:gz")
    prefix = tar.getnames()[0].split("/")[0]
    tree = json.loads(_get(f"https://api.github.com/repos/{C.NFLDATA_REPO}/git/trees/{C.NFLDATA_COMMIT}?recursive=1"))
    blob_by_path = {t["path"]: t["sha"] for t in tree["tree"] if t["type"] == "blob"}
    for path in FILES:
        data = tar.extractfile(f"{prefix}/{path}").read()
        out = C.CACHE / path.split("/")[-1]
        out.write_bytes(data)
        sha = git_blob_sha(data)
        ok = sha == blob_by_path[path]
        manifest["sources"].append({
            "name": f"nflverse/nfldata {path}", "url": f"{C.NFLDATA_BLOB}/{path}",
            "commit": C.NFLDATA_COMMIT, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha": sha, "github_api_blob_sha": blob_by_path[path], "integrity_ok": ok})
        if not ok:
            raise SystemExit(f"Integrity failure for {path}")
    # --- GameCenter archive wheel ---
    whl = _get(C.GC_WHEEL_URL)
    sha = hashlib.sha256(whl).hexdigest()
    (C.CACHE / C.GC_WHEEL_NAME).write_bytes(whl)
    manifest["sources"].append({
        "name": "NFL.com GameCenter JSON feeds (archived in nflgame-redux 3.0.0 wheel)", "url": C.GC_PYPI_PAGE,
        "download_url": C.GC_WHEEL_URL, "bytes": len(whl), "sha256": sha,
        "pypi_published_sha256": C.GC_WHEEL_SHA256, "integrity_ok": sha == C.GC_WHEEL_SHA256})
    if sha != C.GC_WHEEL_SHA256:
        raise SystemExit("Integrity failure for GameCenter wheel")
    (C.DATA / "sources.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
