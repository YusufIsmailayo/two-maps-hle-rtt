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
