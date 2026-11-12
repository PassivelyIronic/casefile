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
  and publishes parquet to our own HF dataset `PassivelyIronic/casefile-cfpb-snapshot`
  (CC0 permits redistribution). `make data` loads that dataset at a pinned commit hash
  and verifies file hashes. Small eval files stay committed in `data/eval/`.
- **Rejected:** (a) Official HF dataset at a pinned revision (does not pin data).
  (b) Re-download the live export with a `Date received` cutoff (narratives are added and
  edited after the fact, so it is not reproducible). (c) Committing the snapshot to git
  (too large).
- **Consequences:** Needs an HF write token once, at snapshot time. The source export hash
  is recorded in the data card.
- **Update 2026-11-12:** The snapshot dataset is **private for now** (owner's decision).
  `make data` authenticates with `HF_TOKEN`. CI does not need it (offline tests, committed
  eval files). Until it is made public, third parties cannot rebuild `history` / `train`,
  and README and the data card must say so. Switching to public does not change the
  pinned revision.

## D-008 — Dependency pinning and the `mcp` 1.x constraint

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** Phase 0 dependency setup. LangChain / LangGraph / MCP APIs change quickly.
  `mcp` 2.x is out (2.3.0), but `langchain-mcp-adapters` 0.3.2 (latest) requires
  `mcp>=1.24,<2`.
- **Decision:** `uv.lock` pins exact versions. In `pyproject.toml`, fast-moving libraries
  (`langchain-*`, `langgraph*`, `mcp`, `langchain-mcp-adapters`) use `~=X.Y.Z` (patch
  updates only) and the rest use `>=X.Y,<next major`. `mcp` stays on `~=1.30.0` until
  the adapters support 2.x.
- **Rejected:** `mcp` 2.x without the adapters (would mean writing our own MCP→LangChain
  tool bridge). Unpinned ranges.
- **Consequences:** MCP servers are written against the `mcp` 1.30 FastMCP API. Revisit
  when adapters release 2.x support.

## D-009 — Provider registry and default chat model

- **Date:** 2026-11-12 · **Status:** accepted
- **Context:** Switching providers must need only an env change, and adding a provider
  should not need config placeholders for providers nobody uses. The student Google AI
  Pro plan does not include API access, so the API uses an AI Studio free-tier key.
- **Decision:** `providers/registry.py` maps provider names to factories
  (`Settings -> BaseChatModel` / `Embeddings`). Built-ins (`gemini`, `ollama`, `fake`)
  are lazy import paths. New providers register via `register_chat` /
  `register_embedding`. Default chat model `gemini-3.5-flash`: `gemini-2.5-flash`
  returns 404 for new users, and `gemini-3.8-flash` returned 503 (high demand) on
  2026-11-12. Free-tier quotas are not published in the docs (shown per project in
  AI Studio).
- **Rejected:** Pre-declared env vars for every possible provider. Fallback chain now
  (deferred to Phase 8).
- **Consequences:** Free-tier RPM/RPD limits will bound eval runs. Measure them before
  Phase 6 and record them.

## D-010 — Narrative source: archived CFPB export (March 2026)

- **Date:** 2026-11-12 · **Status:** accepted (owner chose the option in chat)
- **Context:** The CFPB stopped publishing consumer complaint narratives (announced
  2026-08-14; removed from the public database in September 2026). The official export
  downloaded on 2026-11-12 (`complaints.csv.zip`, sha256 `66edecda…`, Last-Modified
  2026-11-12) has no `Consumer complaint narrative` column, so the source in PLAN.md
  Phase 1 no longer has the project's input. Narratives were public and CC0 before removal.
- **Decision:** Use the CFPB export archived on the Internet Archive in item
  `fed-archive-cfpb-combined-2026` (`complaints.csv.zip`, 1,777,418,049 bytes,
  sha1 `0a25e26f0d72d32f2b4868f0bb4fb345e0109f29` matching archive.org's listing,
  sha256 `35d4c0954b1ea59e72c563319424cf99cbd9d3f9fe7311df956ce01057bed751`).
  It was uploaded by a third party in March 2026, so authenticity is checked: for every
  complaint in our snapshot, metadata columns (product, issue, company, company response,
  timely) are compared with the current official export by Complaint ID, and the
  match rate is reported in the data card. The official export's hash is recorded too.
  The frozen snapshot is then published privately to HF as in D-007.
- **Rejected:** Wayback Machine capture of the official URL from 2026-08-15 (best
  provenance, but downloads at a few KB/s, so 1.4 GB is impractical). archive.org item
  from Feb 2025 (older, same third-party caveat). Third-party HF mirrors (unknown
  processing).
- **Consequences:** Narratives cover complaints up to ~March 2026. README and the data
  card must explain the CFPB policy change and the archive provenance. If CFPB or the
  archive item changes, our frozen HF snapshot still holds the data.
