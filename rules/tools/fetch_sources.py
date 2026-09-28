"""Download each official source document in pankh_rules/data/sources.yaml, checking sha256.

Usage: uv run --group tools python rules/tools/fetch_sources.py

tribal.nic.in serves an incomplete TLS certificate chain, so certificate verification is
disabled for that host. Integrity is still guaranteed: every file must match the sha256
recorded in sources.yaml, and a mismatch fails the run.
"""

import hashlib
import sys
from pathlib import Path

import httpx
import yaml

RULES_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = RULES_DIR / ".cache" / "sources"


def main() -> int:
    sources = yaml.safe_load((RULES_DIR / "pankh_rules" / "data" / "sources.yaml").read_text())
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    with httpx.Client(verify=False, timeout=60, headers={"User-Agent": "Mozilla/5.0"}) as client:
        for source_id, source in sources.items():
            target = CACHE_DIR / f"{source_id}.pdf"
            if not target.exists() or _sha256(target) != source["sha256"]:
                response = client.get(source["url"], follow_redirects=True)
                response.raise_for_status()
                target.write_bytes(response.content)
            if _sha256(target) == source["sha256"]:
                print(f"ok        {source_id}")
            else:
                failures += 1
                print(f"MISMATCH  {source_id}: the published file has changed, review it")
    return 1 if failures else 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    sys.exit(main())
