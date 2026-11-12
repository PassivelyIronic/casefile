"""`make data`: load the frozen pool from HF, verify it, build splits and eval files.

Outputs
- data/eval/golden.jsonl      (committed) 200 cases, 50 per product, monetary relief oversampled
- data/eval/injection.jsonl   (committed) 40 synthetic injection cases
- data/processed/history.parquet, train.parquet   (gitignored, rebuilt from the pool)
- data/checksums.json         (committed) sha256 of every output; a rebuild must match
- evals/reports/data/label_distributions.{json,md}  (committed)
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from casefile.config import Settings, get_settings
from casefile.data.injection import build_cases
from casefile.data.source import sha256_file
from casefile.data.taxonomy import MONETARY_RELIEF, PRODUCTS

LOCK = Path("data/snapshot.lock.json")
CACHE = Path("data/raw/hf")
EVAL_DIR = Path("data/eval")
PROCESSED = Path("data/processed")
CHECKSUMS = Path("data/checksums.json")
REPORT_DIR = Path("evals/reports/data")

SPLIT_SEED = 1729
GOLDEN_PER_PRODUCT = 50
GOLDEN_MONETARY_PER_PRODUCT = 15
HUMAN_PER_PRODUCT = 20
HUMAN_MONETARY_PER_PRODUCT = 6
TRAIN_PER_PRODUCT = 2_500
HISTORY_PER_PRODUCT = 5_000
INJECTION_PER_PRODUCT = 10

RECORD_FIELDS = [
    "complaint_id",
    "date_received",
    "date_sent",
    "product",
    "issue",
    "issue_raw",
    "sub_product",
    "sub_issue",
    "narrative",
    "company",
    "state",
    "submitted_via",
    "company_response",
    "timely",
]


def split_rank(complaint_id: str, salt: str) -> int:
    digest = hashlib.sha256(f"{SPLIT_SEED}:{salt}:{complaint_id}".encode()).digest()
    return int.from_bytes(digest[:8])


def ranked(df: pd.DataFrame, salt: str) -> pd.DataFrame:
    return (
        df.assign(_rank=[split_rank(c, salt) for c in df["complaint_id"]])
        .sort_values(["_rank", "complaint_id"])
        .drop(columns="_rank")
    )


def allocate(counts: dict[str, int], total: int) -> dict[str, int]:
    """Proportional allocation with largest remainder (ties broken by key)."""
    n = sum(counts.values())
    if n == 0 or total == 0:
        return dict.fromkeys(counts, 0)
    quotas = {k: total * v / n for k, v in counts.items()}
    alloc = {k: int(q) for k, q in quotas.items()}
    order = sorted(counts, key=lambda k: (-(quotas[k] - alloc[k]), k))
    for k in order[: total - sum(alloc.values())]:
        alloc[k] += 1
    return {k: min(alloc[k], counts[k]) for k in counts}


def stratified_take(df: pd.DataFrame, n: int, by: str, salt: str) -> pd.DataFrame:
    counts = {str(k): int(v) for k, v in df[by].value_counts().items()}
    parts = []
    for key, k in sorted(allocate(counts, n).items()):
        parts.append(ranked(df[df[by] == key], f"{salt}:{key}").head(k))
    return pd.concat(parts) if parts else df.head(0)


def make_splits(pool: pd.DataFrame) -> dict[str, pd.DataFrame]:
    golden, train, history, inj_src = [], [], [], []
    for product in PRODUCTS:
        p = pool[pool["product"] == product]
        uniform = p[p["pool_stratum"] == "uniform"]
        monetary = pd.concat(
            [
                ranked(p[p["pool_stratum"] == "monetary_extra"], "m-extra"),
                ranked(uniform[uniform["company_response"] == MONETARY_RELIEF], "m-uniform"),
            ]
        ).head(GOLDEN_MONETARY_PER_PRODUCT)
        non_monetary = uniform[uniform["company_response"] != MONETARY_RELIEF]
        rest_n = GOLDEN_PER_PRODUCT - len(monetary)
        g_rest = stratified_take(non_monetary, rest_n, "company_response", f"golden:{product}")
        g = pd.concat([monetary.assign(monetary_oversampled=True), g_rest])
        g = g.assign(monetary_oversampled=g["monetary_oversampled"].fillna(False).astype(bool))
        human_ids = set(
            ranked(g[g["company_response"] == MONETARY_RELIEF], "human-m").head(
                HUMAN_MONETARY_PER_PRODUCT
            )["complaint_id"]
        )
        others = ranked(g[g["company_response"] != MONETARY_RELIEF], "human-o")
        human_ids |= set(others.head(HUMAN_PER_PRODUCT - len(human_ids))["complaint_id"])
        g = g.assign(in_human_subset=g["complaint_id"].isin(human_ids))
        golden.append(g)

        remaining = ranked(uniform[~uniform["complaint_id"].isin(g["complaint_id"])], "split")
        train.append(remaining.iloc[:TRAIN_PER_PRODUCT])
        history.append(remaining.iloc[TRAIN_PER_PRODUCT : TRAIN_PER_PRODUCT + HISTORY_PER_PRODUCT])
        leftover = remaining.iloc[TRAIN_PER_PRODUCT + HISTORY_PER_PRODUCT :]
        inj_src.append(leftover.head(INJECTION_PER_PRODUCT))

    def cat(parts: list[pd.DataFrame]) -> pd.DataFrame:
        return pd.concat(parts).sort_values("complaint_id").reset_index(drop=True)

    return {
        "golden": cat(golden),
        "train": cat(train),
        "history": cat(history),
        "injection_source": pd.concat(inj_src).reset_index(drop=True),
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def records(df: pd.DataFrame, extra: list[str] | None = None) -> list[dict[str, Any]]:
    cols = RECORD_FIELDS + (extra or [])
    out: list[dict[str, Any]] = df[cols].to_dict(orient="records")  # type: ignore[assignment]
    return out


def fetch_pool(settings: Settings) -> tuple[Path, dict[str, Any]]:
    from huggingface_hub import hf_hub_download

    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    token = settings.hf_token.get_secret_value() if settings.hf_token else None
    paths = {}
    for name in ("pool.parquet", "manifest.json"):
        paths[name] = Path(
            hf_hub_download(
                lock["repo_id"],
                name,
                repo_type="dataset",
                revision=lock["revision"],
                token=token,
                local_dir=CACHE,
            )
        )
    actual = sha256_file(paths["pool.parquet"])
    if actual != lock["pool_sha256"]:
        raise RuntimeError(f"pool.parquet sha256 {actual} != locked {lock['pool_sha256']}")
    manifest: dict[str, Any] = json.loads(paths["manifest.json"].read_text(encoding="utf-8"))
    return paths["pool.parquet"], manifest


def distribution(df: pd.DataFrame, col: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for product in PRODUCTS:
        vc = df[df["product"] == product][col].value_counts()
        out[product] = {str(k): int(v) for k, v in vc.items()}
    return out


def build_report(manifest: dict[str, Any], splits: dict[str, pd.DataFrame]) -> dict[str, Any]:
    pop = manifest["population"]
    golden = splits["golden"]
    monetary_rates = {}
    for product in PRODUCTS:
        p = pop[product]
        real = p["company_response"].get(MONETARY_RELIEF, 0) / p["n"]
        g = golden[golden["product"] == product]
        sampled = float((g["company_response"] == MONETARY_RELIEF).mean())
        monetary_rates[product] = {"population": round(real, 4), "golden": round(sampled, 4)}
    return {
        "snapshot": {
            "date_window": manifest["date_window"],
            "source_archive": manifest["source_archive"],
            "verification": manifest["verification"],
            "issue_taxonomy": manifest["issue_taxonomy"],
        },
        "population": pop,
        "split_sizes": {k: len(v) for k, v in splits.items() if k != "injection_source"},
        "monetary_relief_rate": monetary_rates,
        "splits": {
            name: {
                "product": df["product"].value_counts().to_dict(),
                "issue": distribution(df, "issue"),
                "company_response": distribution(df, "company_response"),
            }
            for name, df in splits.items()
            if name in ("golden", "train", "history")
        },
    }


def report_markdown(rep: dict[str, Any]) -> str:
    snap = rep["snapshot"]
    lines = [
        "# Data report: label distributions",
        "",
        f"- Date window: {snap['date_window'][0]} .. {snap['date_window'][1]}",
        f"- Source archive sha256: `{snap['source_archive']['sha256']}`",
        f"- Verification vs official export: `{json.dumps(snap['verification'])}`",
        "- `company_response` is what the company did, not the correct resolution (weak label).",
        "",
        "## Split sizes",
        "",
        "| split | rows |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in rep["split_sizes"].items()],
        "",
        "## Monetary relief rate: population vs golden (oversampled)",
        "",
        "| product | population | golden |",
        "|---|---|---|",
        *[
            f"| {p} | {r['population']:.2%} | {r['golden']:.2%} |"
            for p, r in rep["monetary_relief_rate"].items()
        ],
        "",
        "## Issue taxonomy (kept issues per product; the rest -> `other`)",
        "",
    ]
    for product, issues in snap["issue_taxonomy"].items():
        lines.append(f"- **{product}**: " + "; ".join(issues))
    for product in PRODUCTS:
        p = rep["population"][product]
        lines += [
            "",
            f"## {product} (population after dedupe: {p['n']:,}, before: {p['n_raw']:,})",
            "",
            "| company_response | population | golden |",
            "|---|---|---|",
        ]
        g = rep["splits"]["golden"]["company_response"][product]
        for k, v in p["company_response"].items():
            lines.append(f"| {k or '(empty)'} | {v:,} | {g.get(k, 0)} |")
        lines += ["", "| issue (normalised) | population |", "|---|---|"]
        lines += [f"| {k} | {v:,} |" for k, v in p["issue"].items()]
    return "\n".join(lines) + "\n"


def build(settings: Settings | None = None, update_checksums: bool = False) -> None:
    settings = settings or get_settings()
    pool_path, manifest = fetch_pool(settings)
    pool = pd.read_parquet(pool_path)
    splits = make_splits(pool)

    golden_path = EVAL_DIR / "golden.jsonl"
    write_jsonl(
        golden_path,
        records(splits["golden"], ["monetary_oversampled", "in_human_subset"]),
    )
    injection_path = EVAL_DIR / "injection.jsonl"
    write_jsonl(injection_path, build_cases(records(splits["injection_source"])))

    PROCESSED.mkdir(parents=True, exist_ok=True)
    outputs = [golden_path, injection_path]
    for name in ("train", "history"):
        path = PROCESSED / f"{name}.parquet"
        splits[name][RECORD_FIELDS].to_parquet(path, index=False, compression="zstd")
        outputs.append(path)

    rep = build_report(manifest, splits)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "label_distributions.json").write_text(
        json.dumps(rep, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (REPORT_DIR / "label_distributions.md").write_text(
        report_markdown(rep), encoding="utf-8", newline="\n"
    )

    sums = {p.as_posix(): sha256_file(p) for p in outputs}
    if update_checksums or not CHECKSUMS.exists():
        CHECKSUMS.write_text(json.dumps(sums, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"wrote {CHECKSUMS}")
        return
    expected = json.loads(CHECKSUMS.read_text(encoding="utf-8"))
    bad = {k for k in expected if sums.get(k) != expected[k]}
    if bad:
        raise SystemExit(f"checksum mismatch: {sorted(bad)}")
    print("all outputs match data/checksums.json")


if __name__ == "__main__":
    build(update_checksums="--update-checksums" in sys.argv)
