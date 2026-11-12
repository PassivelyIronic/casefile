"""Download the CFPB complaint export and record its provenance."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

CFPB_EXPORT_URL = "https://files.consumerfinance.gov/ccdb/complaints.csv.zip"
CHUNK = 1 << 20


@dataclass(frozen=True)
class SourceMeta:
    url: str
    sha256: str
    size_bytes: int
    last_modified: str
    downloaded_at: str


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(CHUNK):
            h.update(block)
    return h.hexdigest()


def download_export(dest: Path, url: str = CFPB_EXPORT_URL) -> SourceMeta:
    """Stream the export to `dest` and write `<dest>.meta.json` next to it."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    h = hashlib.sha256()
    size = 0
    with (
        httpx.stream("GET", url, follow_redirects=True, timeout=120.0) as r,
        tmp.open("wb") as f,
    ):
        r.raise_for_status()
        last_modified = r.headers.get("last-modified", "")
        for block in r.iter_bytes(CHUNK):
            f.write(block)
            h.update(block)
            size += len(block)
    tmp.replace(dest)
    meta = SourceMeta(
        url=url,
        sha256=h.hexdigest(),
        size_bytes=size,
        last_modified=last_modified,
        downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    meta_path(dest).write_text(json.dumps(asdict(meta), indent=2) + "\n", encoding="utf-8")
    return meta


def meta_path(dest: Path) -> Path:
    return dest.with_name(dest.name + ".meta.json")


def load_meta(dest: Path) -> SourceMeta:
    return SourceMeta(**json.loads(meta_path(dest).read_text(encoding="utf-8")))
