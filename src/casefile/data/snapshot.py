"""One-off: build the frozen sample pool from the archived CFPB export (D-007, D-010).

Pass 1 streams the archive and keeps a light index of eligible complaints (narrative
present, date window, 4 products). Exact duplicate narratives are dropped (lowest
Complaint ID kept). The pool is chosen per product by a seeded hash rank, so the selection
does not depend on file order. Pass 2 pulls full rows for the pool. The pool is then
checked against the current official export (metadata only, narratives are gone there).

Run: `uv run python -m casefile.data.snapshot build` then `... publish`.
"""

import hashlib
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import pandas as pd

from casefile.data.profile import iter_export
from casefile.data.source import SourceMeta, sha256_file
from casefile.data.taxonomy import (
    DATE_FROM,
    DATE_TO,
    MONETARY_RELIEF,
    PRODUCTS,
    issue_label,
    map_product,
    normalise_issue,
    select_issues,
)

SEED = 42
N_UNIFORM_PER_PRODUCT = 8_000
N_MONETARY_EXTRA_PER_PRODUCT = 400

ARCHIVE_ZIP = Path("data/raw/archive/complaints-2026-03.csv.zip")
ARCHIVE_SOURCE = {
    "url": "https://archive.org/download/fed-archive-cfpb-combined-2026/complaints.csv.zip",
    "item": "fed-archive-cfpb-combined-2026",
    "sha1_archive_org": "0a25e26f0d72d32f2b4868f0bb4fb345e0109f29",
}
OFFICIAL_ZIP = Path("data/raw/complaints.csv.zip")
OUT_DIR = Path("data/raw/snapshot")
SNAPSHOT_REPO = "PassivelyIronic/casefile-cfpb-snapshot"

POOL_COLUMNS = [
    "complaint_id",
    "date_received",
    "date_sent",
    "product",
    "product_raw",
    "sub_product",
    "issue",
    "issue_raw",
    "sub_issue",
    "narrative",
    "company",
    "state",
    "submitted_via",
    "company_response",
    "timely",
    "pool_stratum",
]


def rank(seed: int, complaint_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{seed}:{complaint_id}".encode()).digest()[:8])


def narrative_digest(text: str) -> str:
    return hashlib.sha1(" ".join(text.lower().split()).encode()).hexdigest()  # noqa: S324


def eligible(chunk: pd.DataFrame) -> pd.DataFrame:
    df = chunk[chunk["narrative"].str.strip() != ""]
    df = df[(df["date_received"] >= DATE_FROM) & (df["date_received"] <= DATE_TO + "T99")]
    products = [
        map_product(p, s) for p, s in zip(df["product_raw"], df["sub_product"], strict=True)
    ]
    df = df.assign(product=pd.Series(products, index=df.index, dtype=object))
    df = df[df["product"].notna()]
    return df.assign(issue_norm=df["issue_raw"].map(normalise_issue))


def build_index(chunks: Iterable[pd.DataFrame], seed: int) -> pd.DataFrame:
    parts = []
    for chunk in chunks:
        df = eligible(chunk)
        parts.append(
            pd.DataFrame(
                {
                    "complaint_id": df["complaint_id"],
                    "product": df["product"],
                    "issue_norm": df["issue_norm"],
                    "company_response": df["company_response"],
                    "digest": df["narrative"].map(narrative_digest),
                }
            )
        )
    idx = pd.concat(parts, ignore_index=True)
    idx["cid_int"] = idx["complaint_id"].astype("int64")
    idx["rank"] = [rank(seed, c) for c in idx["complaint_id"]]
    return idx


def dedupe(idx: pd.DataFrame) -> pd.DataFrame:
    return idx.sort_values("cid_int").drop_duplicates("digest", keep="first")


def select_pool(idx: pd.DataFrame) -> dict[str, str]:
    """complaint_id -> stratum ('uniform' | 'monetary_extra')."""
    chosen: dict[str, str] = {}
    for product in PRODUCTS:
        sub = idx[idx["product"] == product].sort_values("rank")
        uniform = sub.head(N_UNIFORM_PER_PRODUCT)
        chosen.update(dict.fromkeys(uniform["complaint_id"], "uniform"))
        rest = sub.iloc[N_UNIFORM_PER_PRODUCT:]
        extra = rest[rest["company_response"] == MONETARY_RELIEF].head(N_MONETARY_EXTRA_PER_PRODUCT)
        chosen.update(dict.fromkeys(extra["complaint_id"], "monetary_extra"))
    return chosen


def population_stats(raw: pd.DataFrame, deduped: pd.DataFrame) -> dict[str, Any]:
    stats: dict[str, Any] = {"eligible_rows": len(raw), "after_dedupe": len(deduped)}
    for product in PRODUCTS:
        sub = deduped[deduped["product"] == product]
        stats[product] = {
            "n_raw": int((raw["product"] == product).sum()),
            "n": len(sub),
            "company_response": sub["company_response"].value_counts().to_dict(),
            "issue": sub["issue_norm"].value_counts().to_dict(),
        }
    return stats


def pull_rows(
    chunks: Iterable[pd.DataFrame], chosen: dict[str, str], kept: dict[str, list[str]]
) -> pd.DataFrame:
    parts = []
    for chunk in chunks:
        df = eligible(chunk)
        df = df[df["complaint_id"].isin(chosen.keys())]
        if len(df):
            parts.append(df)
    pool = pd.concat(parts, ignore_index=True)
    pool["issue"] = [
        issue_label(i, kept[p]) for i, p in zip(pool["issue_norm"], pool["product"], strict=True)
    ]
    pool["pool_stratum"] = pool["complaint_id"].map(chosen)
    pool["cid_int"] = pool["complaint_id"].astype("int64")
    pool = pool.sort_values("cid_int").reset_index(drop=True)
    return pool[POOL_COLUMNS]


VERIFY_FIELDS = {
    "product_raw": "product_raw",
    "issue_raw": "issue_raw",
    "company": "company",
    "company_response": "company_response",
    "timely": "timely",
    "date_received": "date_received",
}


def verify_against_official(pool: pd.DataFrame, official_zip: Path) -> dict[str, Any]:
    ids = set(pool["complaint_id"])
    parts = [c[c["complaint_id"].isin(ids)] for c in iter_export(official_zip)]
    off = pd.concat(parts, ignore_index=True).drop_duplicates("complaint_id")
    merged = pool.merge(off, on="complaint_id", suffixes=("", "_official"))
    result: dict[str, Any] = {
        "pool_size": len(pool),
        "found_in_official": len(merged),
        "found_rate": round(len(merged) / len(pool), 4),
        "field_match_rate": {},
    }
    for ours, theirs in VERIFY_FIELDS.items():
        a = merged[ours].str[:10] if ours == "date_received" else merged[ours]
        b = merged[f"{theirs}_official"]
        b = b.str[:10] if ours == "date_received" else b
        result["field_match_rate"][ours] = round(float((a == b).mean()), 4)
    return result


def build(seed: int = SEED) -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("pass 1: index", flush=True)
    raw_idx = build_index(iter_export(ARCHIVE_ZIP), seed)
    idx = dedupe(raw_idx)
    kept: dict[str, list[str]] = {
        p: select_issues(
            {
                str(k): int(v)
                for k, v in idx[idx["product"] == p]["issue_norm"].value_counts().items()
            }
        )
        for p in PRODUCTS
    }
    chosen = select_pool(idx)
    print(f"pass 2: pull {len(chosen)} rows", flush=True)
    pool = pull_rows(iter_export(ARCHIVE_ZIP), chosen, kept)
    pool_path = OUT_DIR / "pool.parquet"
    pool.to_parquet(pool_path, index=False, compression="zstd")
    print("verify against official export", flush=True)
    verification = verify_against_official(pool, OFFICIAL_ZIP)
    official_meta = json.loads(
        OFFICIAL_ZIP.with_name(OFFICIAL_ZIP.name + ".meta.json").read_text(encoding="utf-8")
    )
    manifest: dict[str, Any] = {
        "seed": seed,
        "date_window": [DATE_FROM, DATE_TO],
        "n_uniform_per_product": N_UNIFORM_PER_PRODUCT,
        "n_monetary_extra_per_product": N_MONETARY_EXTRA_PER_PRODUCT,
        "source_archive": {**ARCHIVE_SOURCE, "sha256": sha256_file(ARCHIVE_ZIP)},
        "source_official_for_verification": SourceMeta(**official_meta).__dict__,
        "issue_taxonomy": kept,
        "population": population_stats(raw_idx, idx),
        "pool": {
            "rows": len(pool),
            "by_product_stratum": {
                "|".join(cast(tuple[str, str], key)): int(n)
                for key, n in pool.groupby(["product", "pool_stratum"]).size().items()
            },
            "sha256": sha256_file(pool_path),
        },
        "verification": verification,
    }
    (OUT_DIR / "README.md").write_text(dataset_card(manifest), encoding="utf-8", newline="\n")
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def publish(repo_id: str, token: str) -> str:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True)
    info = api.upload_folder(
        repo_id=repo_id,
        repo_type="dataset",
        folder_path=OUT_DIR,
        allow_patterns=["pool.parquet", "manifest.json", "README.md"],
        commit_message="Frozen CFPB complaint sample pool",
    )
    return str(info.oid)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        m = build()
        print(json.dumps({k: m[k] for k in ("pool", "verification")}, indent=2))
    elif cmd == "publish":
        from casefile.config import get_settings

        s = get_settings()
        assert s.hf_token is not None, "HF_TOKEN missing"
        print(publish(SNAPSHOT_REPO, s.hf_token.get_secret_value()))


def dataset_card(m: dict[str, Any]) -> str:
    v = m["verification"]
    src = m["source_archive"]
    return f"""---
license: cc0-1.0
language: [en]
pretty_name: casefile CFPB complaint sample pool
tags: [finance, complaints, cfpb, text-classification]
---

# casefile CFPB complaint sample pool

Frozen sample of consumer complaints **with narratives** from the CFPB Consumer Complaint
Database, used by the casefile project (https://github.com/PassivelyIronic/casefile).

**Why this exists:** the CFPB stopped publishing complaint narratives in 2026; the
current official export has no narrative column. This pool was sampled from a copy of the
official export archived on the Internet Archive (item `{src["item"]}`, sha1
`{src["sha1_archive_org"]}`, sha256 `{src["sha256"]}`).

**Authenticity check:** {v["found_in_official"]:,} of {v["pool_size"]:,} complaints
({v["found_rate"]:.2%}) exist in the official export of 2026-11-12, with metadata match
rates {json.dumps(v["field_match_rate"])}.

## Contents

- `pool.parquet`: {m["pool"]["rows"]:,} complaints; per product
  {m["n_uniform_per_product"]:,} uniformly sampled (`pool_stratum=uniform`) plus up to
  {m["n_monetary_extra_per_product"]} extra "Closed with monetary relief" cases
  (`monetary_extra`) to make escalation recall measurable.
- `manifest.json`: sources, hashes, seed, taxonomy, population statistics.

Filters: narrative present; received {m["date_window"][0]} .. {m["date_window"][1]};
products credit reporting, debt collection, credit card (prepaid excluded), checking or
savings account. Exact duplicate narratives removed (lowest Complaint ID kept).
Selection: per product, lowest `sha256(seed:complaint_id)` rank (seed {m["seed"]}).

## Caveats

- `company_response` is what the company did, not a ground-truth correct resolution.
- Narratives are redacted by CFPB (`XXXX`); near-duplicate (templated) narratives remain.
- Product balance is by design; real ratios are in `manifest.json` → `population`.
"""
