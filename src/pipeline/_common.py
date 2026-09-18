"""Shared helpers for the Two Maps pipeline (Bronze/Silver/Gold)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
BRONZE_DIR = REPO_ROOT / "data" / "bronze"
SILVER_DIR = REPO_ROOT / "data" / "silver"
GOLD_DIR = REPO_ROOT / "data" / "gold"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, timeout: int = 600) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout,
                      headers={"User-Agent": "two-maps-pipeline/0.1"}) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def write_metadata(folder: Path, **fields) -> None:
    fields["downloaded_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (folder / "metadata.json").write_text(json.dumps(fields, indent=2))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- RTT quirks
#
# Two corrections I had to make after auditing the July 2026 join. Both are
# here rather than inline so every script that touches RTT sees the same rule.

#: Commissioner code used in the RTT full extract for activity with no
#: identified commissioner. NHS England's published provider workbook excludes
#: these rows: the July 2026 extract totals 7,162,692 incomplete pathways with
#: them and 7,131,685 without, and the workbook says 7,131,685. I keep the rows
#: in Bronze and drop them when reporting the published measure.
RTT_UNIDENTIFIED_COMMISSIONER = "NONC"

#: Trust code successions. A trust that merges stops submitting under its old
#: code, which looks exactly like a non-submission if you only join on codes.
#: (old code, surviving code, first period the survivor carries the old trust's
#: activity). North Bristol merged into Bristol NHS Foundation Trust on
#: 1 July 2026; RA7's July list is roughly RA7 + RVJ from June.
TRUST_SUCCESSIONS = [
    ("RVJ", "RA7", "2026-07"),
]


def apply_trust_successions(codes, period: str):
    """Map superseded trust codes to their successor, for one RTT period.

    Returns `codes` unchanged for periods before a merger took effect, so
    April-June 2026 keep RVJ and RA7 as the two distinct trusts they were.
    """
    mapping = {old: new for old, new, eff in TRUST_SUCCESSIONS if period >= eff}
    return codes.replace(mapping) if mapping else codes
