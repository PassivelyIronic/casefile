"""Profile label distributions in the raw CFPB export (all products, narratives only)."""

import json
import zipfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pandas as pd

COLUMNS = {
    "Date received": "date_received",
    "Product": "product_raw",
    "Sub-product": "sub_product",
    "Issue": "issue_raw",
    "Sub-issue": "sub_issue",
    "Consumer complaint narrative": "narrative",
    "Company": "company",
    "State": "state",
    "Submitted via": "submitted_via",
    "Date sent to company": "date_sent",
    "Company response to consumer": "company_response",
    "Timely response?": "timely",
    "Complaint ID": "complaint_id",
}


def iter_export(zip_path: Path, chunksize: int = 200_000) -> Iterator[pd.DataFrame]:
    """Yield chunks with normalised column names (all values str). Missing columns are skipped."""
    with zipfile.ZipFile(zip_path) as zf:
        (name,) = [n for n in zf.namelist() if n.endswith(".csv")]
        with zf.open(name) as f:
            reader = pd.read_csv(
                f,
                usecols=lambda c: c in COLUMNS,
                dtype=str,
                keep_default_na=False,
                chunksize=chunksize,
            )
            for chunk in reader:
                yield chunk.rename(columns=COLUMNS)


def profile_export(zip_path: Path) -> dict[str, object]:
    rows = 0
    with_narrative = 0
    product_all: Counter[str] = Counter()
    product_narr: Counter[str] = Counter()
    product_year: Counter[tuple[str, str]] = Counter()
    product_issue: Counter[tuple[str, str]] = Counter()
    product_response: Counter[tuple[str, str]] = Counter()
    product_timely: Counter[tuple[str, str]] = Counter()
    issue_years: dict[tuple[str, str], list[str]] = {}

    for chunk in iter_export(zip_path):
        rows += len(chunk)
        product_all.update(chunk["product_raw"])
        narr = chunk[chunk["narrative"].str.strip() != ""]
        with_narrative += len(narr)
        year = narr["date_received"].str[:4]
        product_narr.update(narr["product_raw"])
        product_year.update(zip(narr["product_raw"], year, strict=True))
        product_issue.update(zip(narr["product_raw"], narr["issue_raw"], strict=True))
        product_response.update(zip(narr["product_raw"], narr["company_response"], strict=True))
        product_timely.update(zip(narr["product_raw"], narr["timely"], strict=True))
        for key, y in zip(
            zip(narr["product_raw"], narr["issue_raw"], strict=True), year, strict=True
        ):
            span = issue_years.setdefault(key, [y, y])
            span[0], span[1] = min(span[0], y), max(span[1], y)

    def nested(c: Counter[tuple[str, str]]) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for (a, b), n in c.most_common():
            out.setdefault(a, {})[b] = n
        return out

    return {
        "rows": rows,
        "rows_with_narrative": with_narrative,
        "product_all": dict(product_all.most_common()),
        "product_with_narrative": dict(product_narr.most_common()),
        "product_year": nested(product_year),
        "product_issue": nested(product_issue),
        "product_response": nested(product_response),
        "product_timely": nested(product_timely),
        "issue_year_span": {f"{p} || {i}": s for (p, i), s in sorted(issue_years.items())},
    }


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(profile_export(src), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
