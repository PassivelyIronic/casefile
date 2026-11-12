# Data card

## Source

**CFPB Consumer Complaint Database**: real consumer complaints about financial products,
published by the US Consumer Financial Protection Bureau. Public domain / CC0.

**Narrative availability changed in 2026.** The CFPB announced on 2026-08-14 that it
would stop publishing complaint narratives, and removed them from the public database in
September 2026. The official export downloaded on 2026-11-12
(`https://files.consumerfinance.gov/ccdb/complaints.csv.zip`, sha256
`66edecdaf4c95967a92c7cd3793b4a804cc258f4b9e16c13aa26d58a61479a5f`) has no narrative
column. See DECISIONS.md D-010.

Narratives therefore come from a copy of the official export **archived on the Internet
Archive** before removal:

| | |
|---|---|
| Item | `fed-archive-cfpb-combined-2026` (uploaded March 2026, third party) |
| File | `complaints.csv.zip`, 1,777,418,049 bytes |
| sha1 (matches archive.org listing) | `0a25e26f0d72d32f2b4868f0bb4fb345e0109f29` |
| sha256 | `35d4c0954b1ea59e72c563319424cf99cbd9d3f9fe7311df956ce01057bed751` |

**Authenticity check.** Every complaint in the sample pool was looked up in the current
official export by Complaint ID: 33,593 of 33,600 found (99.98%). Metadata match rates:
product 100%, issue 100%, date received 100%, timely 100%, company response 99.99%,
company name 99.66% (companies are occasionally renamed). Details:
[`evals/reports/data/label_distributions.md`](../evals/reports/data/label_distributions.md).

## Frozen snapshot

The sample pool is frozen in a Hugging Face dataset, pinned in
[`snapshot.lock.json`](snapshot.lock.json) (repo, commit, sha256 of `pool.parquet`).

> **The HF dataset is private for now.** `make data` needs an `HF_TOKEN` with access.
> Until it is made public, third parties cannot rebuild `history` / `train` or the
> eval files from scratch. The committed eval files (`data/eval/`) are usable as is.

Built by `python -m casefile.data.snapshot build` (one-off, needs the archive and the
official export in `data/raw/`).

## Filters

- Narrative present.
- `Date received` between **2022-01-01 and 2025-12-31**. The product/issue taxonomy is
  stable in this window apart from renames, and all of it falls after Regulation F took
  effect (2021-11-30), so the regulations corpus applies to every case.
- 4 products, mapped across CFPB renames:

| canonical | raw CFPB product names |
|---|---|
| `credit_reporting` | Credit reporting or other personal consumer reports; Credit reporting, credit repair services, or other personal consumer reports |
| `debt_collection` | Debt collection |
| `credit_card` | Credit card; Credit card or prepaid card (credit-card sub-products only, prepaid excluded) |
| `checking_savings` | Checking or savings account |

- **Exact duplicate narratives removed** (whitespace/case-normalised; lowest Complaint ID
  kept). This removed 52% of credit-reporting narratives (templated dispute letters),
  22% of debt collection, 10% of credit card, 3.5% of checking/savings.
  **Near-duplicates remain**, so similar-case retrieval may find templated twins.

## Labels

- **Product**: canonical product above.
- **Issue**: CFPB issue with renames unified (`casefile/data/taxonomy.py`). Per product,
  issues with at least 2% share (max 8) keep their own label and the rest become
  `other`. 3–8 labels per product.
- **`company_response`** (`Closed with explanation`, `... with monetary relief`,
  `... with non-monetary relief`, `Untimely response`, ...) is **what the company did,
  not the correct answer**. It is a weak label for resolution type and is never gated on.
- **`timely`** is CFPB's own flag. The system's SLA check uses dates.

## Splits

All splits are seeded and selected by hash rank of Complaint ID, so they do not depend on
row order. Products are balanced **by design**. Real distributions are in the report.

| split | size | use | committed |
|---|---|---|---|
| `golden` | 200 (50/product) | main eval set | `data/eval/golden.jsonl` |
| `human` | 80 (20/product), subset of golden (`in_human_subset`) | hand-labelled draft quality (labels added in Phase 6) | flag in golden |
| `train` | 10,000 (2,500/product) | TF-IDF baseline only | no (`data/processed/`) |
| `history` | 20,000 (5,000/product) | similar-case index, never evaluated on | no (`data/processed/`) |

**Monetary relief is oversampled in golden:** 15 of 50 per product (30%), against a real
rate of 0.16% (credit reporting), 0.50% (debt collection), 18.8% (credit card), 13.6%
(checking/savings). The human subset holds 6 monetary cases per product. Golden has no
`Untimely response` cases (about 0.1% of the population).

`make data` rebuilds all four outputs and checks them against
[`checksums.json`](checksums.json).

## Synthetic injection set

`data/eval/injection.jsonl`: **40 synthetic cases**. Each is a real narrative (from the
pool, not in any other split) with one of 8 attack templates inserted at the start, middle
or end. Templates: instruction override, fake system message, hidden note to the AI, tool
coercion, fake supervisor approval, prompt exfiltration, routing steer, spoofed
structured output. Expected behaviour: flag the injection, escalate to a human, never call
`issue_credit` / `close_case` before approval, plus attack-specific checks. Source:
`casefile/data/injection.py`.

## Known caveats

- Narratives are redacted by CFPB (`XXXX`, `XX/XX/year`), and amounts appear as `{$800.00}`.
- Credit-reporting narratives are often templated letters, even after dedupe.
- Complaint text is the consumer's account only: unverified and one-sided.
- Data ends with complaints received by 2025-12-31 (the archive is from March 2026).

## Regulations corpus

`corpora/regulations/`: 23 sections of US federal law (public domain). FCRA (15 U.S.C.
§§1681b, 1681c-2, 1681g, 1681i, 1681s-2, 2024 edition from govinfo), Regulation V
§1022.43, Regulation F §§1006.6/.14/.18/.22/.30/.34/.38, Regulation Z
§§1026.9/.12/.13/.52/.55, Regulation E §§1005.6/.11/.17, Regulation DD §§1030.4/.5
(eCFR as of 2026-11-04). Source URLs, retrieval date and hashes:
[`manifest.json`](../corpora/regulations/manifest.json). Rebuild with `make corpus`.
