# DECISIONS.md — casefile

Architecture decision log. Each entry: id, date, status (proposed / accepted /
superseded), context, decision, alternatives rejected, consequences.

---

## D-001 — Domain and data: CFPB complaints

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** The project needs real, labelled, public data to support honest evaluation.
- **Decision:** Use the CFPB Consumer Complaint Database (real narratives, product/issue
  labels, company responses, timeliness).
- **Rejected:** Synthetic insurance claims (no ground truth). τ-bench as primary data
  (a benchmark, not a product domain).
- **Consequences:** Resolution labels are weak (what the company did, not what was
  correct). This must be stated in every report.

## D-002 — Deterministic top-level graph, agentic subgraphs

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** The system must be evaluable, inspectable and have bounded cost.
- **Decision:** The top-level LangGraph flow is fixed with conditional edges. LLM autonomy
  lives only in scoped subgraphs (investigator, compliance, resolver).
- **Rejected:** Fully autonomous supervisor agent (hard to evaluate, unpredictable cost).
- **Consequences:** Trajectory checks are meaningful. Less flexibility for unusual cases.

## D-003 — Write tools gated by graph structure

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** Monetary actions must never be triggered by model output or injected text.
- **Decision:** `issue_credit` / `close_case` are bound only in the `execute` node, which
  is reachable only through the approval edge (or the policy auto-approve path).
- **Rejected:** Prompt-level restrictions ("do not call issue_credit unless…").
- **Consequences:** Needs a structural unit test proving the write tools cannot be reached
  without approval.

## D-004 — Own MCP servers consumed through adapters

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** Tools should have a protocol boundary and be reusable outside the agent.
- **Decision:** Standalone FastMCP servers (stdio + streamable HTTP), loaded into LangGraph
  via `langchain-mcp-adapters`.
- **Rejected:** Direct Python tool functions (no protocol boundary, not reusable).
- **Consequences:** Extra process and transport overhead. Servers must not import `graph/`.

## D-005 — Langfuse Cloud Hobby tier

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** Tracing is needed, with zero cost, on 16 GB RAM.
- **Decision:** Langfuse Cloud Hobby (free).
- **Rejected:** Local self-hosting (ClickHouse + Redis + blob storage + Postgres exceed the
  hardware budget alongside the app).
- **Consequences:** Traces leave the machine. Hobby-tier retention and quota limits apply.

## D-006 — Deterministic gates only

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** CI gates must be stable, and LLM judges vary from run to run.
- **Decision:** Gates use deterministic metrics only. LLM-as-judge is observational and is
  calibrated against human labels (Cohen's kappa).
- **Rejected:** Judge-based gating.
- **Consequences:** Draft quality is not gated, and reports say so.

## D-007 — Data snapshot frozen in own HF Hub dataset

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** PLAN.md assumed loading `CFPB/consumer-finance-complaints` from HF at a
  pinned revision. Inspection on 2026-11-12: that repo (rev `0a4a8d7`, last modified
  2024-07-16) contains no data files, only a loading script that downloads the live
  `files.consumerfinance.gov/ccdb/complaints.csv.zip` (≈366 MB, updated daily). Pinning
  the revision pins the script, not the data. Recent `datasets` releases also drop
  loading-script support.
- **Decision:** A one-off snapshot script downloads the CFPB export and records its sha256,
  `Last-Modified` and download date. It filters to the 4 target products with narratives
  and publishes parquet to our own HF dataset `passivelyironic/casefile-cfpb-snapshot`
  (CC0 permits redistribution). `make data` loads that dataset at a pinned commit hash
  and verifies file hashes. Small eval files stay committed in `data/eval/`.
- **Rejected:** (a) Official HF dataset at a pinned revision (does not pin data).
  (b) Re-download the live export with a `Date received` cutoff (narratives are added and
  edited after the fact, so it is not reproducible). (c) Committing the snapshot to git
  (too large).
- **Consequences:** Needs an HF write token once, at snapshot time. Reproducibility depends
  on the HF dataset staying public. The source export hash is recorded in the data card.
