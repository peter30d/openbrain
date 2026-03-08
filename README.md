# OpenBrain Gateway

A local, upgrade-safe canonical memory system for **OpenClaw**, with:

- **local long-term memory** stored in **Postgres + pgvector**
- a **human-readable Markdown archive**
- a thin **HTTP + CLI gateway**
- **federated expert retrieval** from **Brian Madden's live MCP endpoint**
- a deliberate architecture that keeps **OpenClaw as the assistant runtime** and **OpenBrain as the source of truth**

---

# Purpose

This project exists to solve a specific architectural problem:

> OpenClaw is an excellent assistant runtime and Telegram/chat surface, but it should **not** be the authoritative long-term memory store.

Instead, this repository implements a separate **canonical memory layer** that OpenClaw can use through stable external boundaries.

That separation gives us:

- **upgrade safety**
- **clear data ownership**
- **clean provenance**
- **human inspectability**
- **recoverability**
- **future portability to other AI runtimes**

---

# Core Idea

The system is intentionally split into 3 roles:

## 1. OpenClaw = assistant runtime
OpenClaw handles:

- Telegram and other chat surfaces
- session management
- agent behavior
- tool invocation
- user-facing interaction

OpenClaw does **not** own canonical long-term memory.

## 2. OpenBrain Gateway = memory control plane
This repository implements the **OpenBrain Gateway**, which handles:

- memory capture
- memory search
- archive writing
- metadata enrichment
- local retrieval
- expert-source federation
- promotion of external results into local memory

## 3. Brian Madden = external expert source
Brian Madden's published brain is treated as:

- external
- read-only
- queryable
- provenance-preserving
- namespaced separately from local memory

Brian is available via:

- **live MCP transport** to `https://brianmadden.ai/mcp`
- optional **repo fallback / mirror**
- never silently merged into local canonical memory

---

# Architectural Principles

These are the most important project-level rules.

## 1. Local memory is authoritative
The local memory store is the **source of truth** for:

- personal preferences
- project notes
- decisions
- summaries
- promoted external insights
- local reflections
- durable context that should survive OpenClaw upgrades

## 2. OpenClaw must remain loosely coupled
This project is deliberately externalized so OpenClaw can be upgraded independently.

The preferred integration surfaces are:

- a local CLI bridge (`openbrainctl`)
- OpenClaw workspace skills
- stable config references
- optional HTTP boundaries

## 3. External expert sources are advisory
Brian Madden's MCP content is not local memory.

It remains:

- external
- read-only
- namespaced
- explicitly attributable

## 4. Provenance matters
Every retrieval result should make it obvious whether it came from:

- `local`
- `external.brianmadden`

## 5. Human-readable and machine-retrievable must coexist
Important memories are stored in two forms:

- structured DB rows for retrieval
- mirrored Markdown files for inspection and backup

---

# High-Level System Diagram

```text
Telegram / OpenClaw
        |
        v
 OpenClaw runtime
        |
        v
 OpenBrain Bridge (skill + openbrainctl)
        |
        v
 OpenBrain Gateway
   |            |
   |            +--> Brian Madden MCP
   |                   https://brianmadden.ai/mcp
   |
   +--> Postgres + pgvector
   +--> Markdown archive
```

---

# Repository Role

This repository contains the **OpenBrain Gateway** and related operational files.

It is **not** OpenClaw itself.

It is intended to be installed locally, typically at:

```text
/opt/openbrain
```

The repository is designed to run on an Ubuntu desktop/server and provide local memory services to OpenClaw.

---

# Current Feature Set

## Implemented

### Local canonical memory
- capture memory records
- enrich captured notes with metadata
- store records in Postgres
- store embeddings in pgvector
- write mirrored Markdown archive files
- search local memory semantically

### Brian Madden federation
- direct live MCP transport to `https://brianmadden.ai/mcp`
- dynamic MCP tool discovery
- Brian-only retrieval
- federated retrieval
- clean no-result handling
- optional repo mirror fallback

### OpenClaw bridge
- local CLI interface: `openbrainctl`
- OpenClaw skill instructions for invoking the CLI
- externalized architecture to preserve upgrade safety

### Operational basics
- FastAPI HTTP service
- systemd service definition
- environment-based configuration
- status endpoints
- audit logging
- backup/refresh helper scripts

---

# Design Goals

## Primary goals
- persistent long-term memory for a personal assistant
- easy OpenClaw integration
- clean separation between runtime and canonical memory
- support for both personal memory and expert federation
- upgrade safety
- inspectability and recoverability

## Explicit non-goals
This repository is **not** currently trying to be:

- a multi-user system
- a team knowledge base
- a complete MCP server for all possible tools
- a full UI product
- an enterprise orchestration platform
- an automatic ingestion engine for every external source

---

# Repository Layout

```text
openbrain/
├── README.md
├── OPENCLAW_RETROFIT.md
├── pyproject.toml
├── requirements-lock.txt
├── sql/
│   └── 001_init.sql
├── openbrain/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── archive.py
│   ├── embeddings.py
│   ├── connectors.py
│   ├── service.py
│   ├── api.py
│   └── cli.py
├── openclaw/
│   └── SKILL.md
├── systemd/
│   ├── openbrain-gateway.service
│   └── openbrain-gateway.env
├── scripts/
│   ├── backup-openbrain.sh
│   └── refresh-brian-repo.sh
├── archive/
├── backups/
└── external/
```

Some runtime directories may exist only on installed systems, not necessarily in Git.

---

# Important Files and What They Mean

## `README.md`
This file. High-level orientation for humans and AI.

## `OPENCLAW_RETROFIT.md`
Authoritative guide for reconnecting this memory system to future OpenClaw installs/upgrades.

If you are adapting the project after an OpenClaw upgrade, read this file early.

## `openbrain/config.py`
Runtime configuration loading.

Important note:
- config loading must work for both:
  - systemd service startup
  - direct CLI use
- the project uses deterministic loading from `/opt/openbrain/.env`

## `openbrain/service.py`
The main business logic layer.

This is where the core memory workflows live:
- capture
- local search
- Brian search
- federated search
- promotion
- source status

## `openbrain/connectors.py`
External source connectors.

This includes:
- Brian repo connector
- Brian MCP connector

This file is critical for understanding how Brian is queried and how fallback behavior works.

## `openbrain/api.py`
FastAPI routes for the gateway.

## `openbrain/cli.py`
Local CLI bridge used by OpenClaw.

Main command surface:
- `openbrainctl capture`
- `openbrainctl search`
- `openbrainctl brian`
- `openbrainctl federated`
- `openbrainctl promote`

## `openclaw/SKILL.md`
OpenClaw-facing instructions for using the OpenBrain bridge.

## `sql/001_init.sql`
Database schema and vector extension setup.

## `systemd/openbrain-gateway.service`
Systemd unit for the gateway.

---

# Reading Order for Another AI Model

If you are another AI model trying to understand this repository, read the files in this order:

## 1. `README.md`
Get the overall architecture.

## 2. `OPENCLAW_RETROFIT.md`
Understand how the system reconnects to OpenClaw and why the design is externalized.

## 3. `openbrain/config.py`
Understand runtime configuration rules and environment assumptions.

## 4. `openbrain/models.py`
Understand the data model.

## 5. `sql/001_init.sql`
Understand the actual DB schema.

## 6. `openbrain/connectors.py`
Understand external Brian integration and MCP behavior.

## 7. `openbrain/service.py`
Understand the operational flows.

## 8. `openbrain/api.py`
Understand the HTTP surface.

## 9. `openbrain/cli.py`
Understand the OpenClaw bridge surface.

## 10. `openclaw/SKILL.md`
Understand the expected assistant behavior when used from OpenClaw.

---

# Canonical Memory Model

Local canonical memory is hybrid:

## Structured layer
Stored in Postgres with embeddings.

Each memory record includes fields like:

- `id`
- `title`
- `raw_text`
- `cleaned_text`
- `summary`
- `memory_type`
- `source_surface`
- `source_session_id`
- `project`
- `people`
- `topics`
- `tags`
- `action_items`
- `importance`
- `sensitivity`
- `captured_at`
- `archive_path`
- `provenance_type`
- `provenance_ref`
- `embedding`

## Human-readable layer
Each important memory is mirrored into a Markdown file with frontmatter.

This gives:

- human inspection
- backup friendliness
- potential Git archival
- disaster recovery support
- future reindexing possibilities

---

# Memory Types

Common local memory types include:

- `note`
- `decision`
- `reference`
- `project`
- `person`
- `meeting`
- `insight`
- `task`
- `reflection`
- `preference`

This taxonomy is intentionally simple and should evolve conservatively.

---

# Provenance Model

## Local memory namespace
```text
local
```

Used for:
- personal notes
- decisions
- preferences
- promoted external content
- local summaries

## External expert namespace
```text
external.brianmadden
```

Used for:
- Brian Madden live MCP results
- Brian repo mirror results
- read-only external references

## Promotion model
If external material is intentionally saved, it becomes a **new local memory item** with source backlinking.

That means:
- Brian content stays external until explicitly promoted
- promotions are traceable
- provenance is preserved

---

# Brian Madden Integration

Brian Madden is integrated in two ways.

## 1. Preferred path: live MCP
The system connects directly to:

```text
https://brianmadden.ai/mcp
```

The connector performs:
- session initialization
- tool discovery
- live search calls

Typical discovered tools include:
- `get_file`
- `list_files`
- `search`
- `get_framework`
- `get_current_thinking`
- `get_loading_instructions`

## 2. Secondary path: repo mirror
A local mirror of Brian's published repo can be used as fallback or resilience layer.

This repo mirror is useful for:
- offline-ish fallback
- backup access
- manual inspection
- resilience if MCP errors

## Important behavior
The current behavior intentionally distinguishes:

- **MCP healthy + useful match** → use MCP result
- **MCP healthy + no useful match** → return empty Brian result set
- **MCP error/failure** → fall back to repo connector

This avoids misleading users into thinking a live MCP result was returned when it was actually a repo fallback.

---

# OpenClaw Integration Strategy

This repository assumes OpenClaw is already installed separately.

OpenClaw integration is intentionally thin:

- OpenClaw calls `openbrainctl`
- `openbrainctl` calls the local OpenBrain HTTP gateway
- OpenBrain performs capture/search/federation
- OpenClaw remains decoupled from internal memory schema

## Why this matters
OpenClaw evolves quickly.

Directly patching OpenClaw core for canonical memory would create upgrade pain.

This project instead uses a stable seam:

```text
OpenClaw -> skill/exec -> openbrainctl -> OpenBrain Gateway
```

## See also
For detailed upgrade/reconnect guidance, read:

```text
OPENCLAW_RETROFIT.md
```

That file is the main reference for reattaching this system after future OpenClaw upgrades.

---

# OpenClaw Retrofit Philosophy

The correct retrofit path after a future OpenClaw upgrade should be:

1. upgrade or reinstall OpenClaw
2. ensure local tool invocation still works
3. restore or verify the OpenBrain skill bridge
4. reconnect OpenClaw to the same OpenBrain Gateway
5. leave canonical memory untouched

This is the single most important long-term architectural property of the project.

---

# API Surface

The OpenBrain Gateway exposes a small HTTP API.

## Health
```text
GET /health
```

## Source status
```text
GET /sources/status
```

## Capture memory
```text
POST /memories/capture
```

## Search local memory
```text
POST /search/local
```

## Search Brian
```text
POST /search/brian
```

## Federated search
```text
POST /search/federated
```

## Promote external result
```text
POST /external/promote
```

---

# CLI Surface

The main local command interface is:

```bash
openbrainctl
```

## Examples

### Capture
```bash
openbrainctl capture "Peter prefers concise technical explanations."
```

### Local search
```bash
openbrainctl search "What does Peter prefer?"
```

### Brian-only search
```bash
openbrainctl brian "AI and the future of knowledge work"
```

### Federated search
```bash
openbrainctl federated "Compare my architecture with Brian Madden's perspective"
```

### Promote external
```bash
openbrainctl promote "external.brianmadden" "Title" "Excerpt"
```

---

# Configuration Model

The active runtime config is loaded from:

```text
/opt/openbrain/.env
```

This file is intentionally **local and untracked**.

Tracked files include templates and service env support files such as:

- `.env.example`
- `systemd/openbrain-gateway.env`

## Important configuration keys

### Core runtime
- `OPENBRAIN_ENV`
- `OPENBRAIN_HOST`
- `OPENBRAIN_PORT`
- `OPENBRAIN_LOG_LEVEL`

### Local memory
- `OPENBRAIN_DATABASE_URL`
- `OPENBRAIN_ARCHIVE_DIR`

### Embeddings
- `OPENBRAIN_EMBED_MODEL`
- `OPENBRAIN_EMBED_DIM`

### Brian integration
- `OPENBRAIN_ENABLE_BRIAN_REPO`
- `OPENBRAIN_ENABLE_BRIAN_MCP`
- `OPENBRAIN_BRIAN_REPO_DIR`
- `OPENBRAIN_BRIAN_SITE_URL`
- `OPENBRAIN_BRIAN_MCP_URL`
- `OPENBRAIN_BRIAN_TIMEOUT_SECONDS`

---

# Runtime Assumptions

This project assumes:

- Ubuntu/Linux host
- Python virtual environment under `/opt/openbrain/.venv`
- local Postgres instance
- pgvector installed
- systemd available
- OpenClaw installed separately
- local repo path typically `/opt/openbrain`

These are conventions, not universal laws, but much of the operational guidance assumes them.

---

# Installation and Runtime Summary

A typical install looks like:

1. install Postgres and pgvector
2. create DB and user
3. place repo under `/opt/openbrain`
4. create Python venv
5. install package in editable mode
6. create `/opt/openbrain/.env`
7. clone Brian repo mirror if desired
8. start gateway via systemd
9. connect OpenClaw through the bridge skill

---

# Operational Commands

## Start/restart service
```bash
sudo systemctl restart openbrain-gateway
```

## Service status
```bash
sudo systemctl status openbrain-gateway --no-pager
```

## Logs
```bash
journalctl -u openbrain-gateway -n 100 --no-pager
```

## Health
```bash
curl http://127.0.0.1:8094/health
```

## Source status
```bash
curl http://127.0.0.1:8094/sources/status
```

---

# Expected Healthy State

A healthy system should satisfy all of the following:

## Local health
```bash
curl http://127.0.0.1:8094/health
```

returns:

```json
{"ok":true,"service":"openbrain-gateway"}
```

## Brian MCP source status
`/sources/status` should show:

- `brian_mcp.available = true`
- tool names discovered
- session id present

## Local capture
A test capture creates:
- a DB row
- an archive Markdown file

## Local search
A test search returns the captured memory.

## Brian-only retrieval
A direct Brian query should show:

```text
source_label: Brian Madden MCP
```

## Federated retrieval
Federated results should:
- use local memory when appropriate
- return Brian results when query phrasing matches well
- avoid misleading fallback substitution

---

# Known Behavioral Characteristics

## 1. Brian direct queries work best when topical
Example:

```bash
openbrainctl brian "AI and the future of knowledge work"
```

This is a strong MCP query.

## 2. Broad compare prompts may return empty Brian results
Example:

```bash
openbrainctl federated "Compare my architecture with Brian Madden's perspective"
```

This may legitimately yield:

```json
"brian": []
```

That is acceptable and intentional.

It means:
- MCP was consulted
- no useful Brian-side match was found for that phrasing
- repo fallback was not silently substituted

## 3. Repo fallback is for errors, not for masking no-results
This is an intentional design choice.

---

# Development Notes

## Editable install
The project is normally installed with:

```bash
pip install -e .
```

## Runtime artifacts
Generated Python bytecode and other runtime artifacts should not be treated as source files.

## Local `.env`
The real `.env` file is intentionally untracked.

Never commit:
- production secrets
- DB passwords
- local machine-specific runtime tokens

---

# For Another AI Model: Do Not Break These Invariants

If you are modifying this project, preserve these rules unless explicitly asked to change them.

## Invariant 1
Canonical memory remains external to OpenClaw core.

## Invariant 2
Brian remains an external, read-only expert source.

## Invariant 3
Promotion from Brian to local memory must be explicit.

## Invariant 4
Provenance must remain visible in retrieval results.

## Invariant 5
OpenClaw integration must remain a thin bridge, not a deep coupling.

## Invariant 6
Both structured DB storage and Markdown archive mirroring remain supported.

## Invariant 7
CLI behavior and service behavior must use the same configuration model.

---

# Testing Expectations

Minimum functional tests for changes touching core behavior:

## Config / runtime
- service starts
- CLI starts
- config loads from `/opt/openbrain/.env`

## Local memory
- capture works
- archive file is written
- search returns expected memory

## Brian integration
- source status discovers MCP tools
- direct Brian search works
- federated search behaves cleanly

## Git hygiene
Working tree should remain clean after tests except for intentionally local/untracked runtime files.

---

# Future Improvement Areas

These are reasonable next steps, not current guarantees.

## Better Brian-side query rewriting
Improve hit rate for broad comparison prompts by rewriting federated Brian queries into more topic-focused language.

## Richer metadata enrichment
Improve:
- people extraction
- project inference
- action item extraction
- importance/sensitivity heuristics

## Reindexing and archive recovery
Add explicit reindex tooling from Markdown archive back into structured memory.

## Better federation ranking
Improve mixed ranking across:
- local semantic memory
- Brian live MCP
- optional repo fallback

## Review workflows
Add:
- scheduled review
- archival curation
- promotion workflows
- maintenance commands

---

# Troubleshooting

## Symptom: service runs but CLI fails
Likely config-loading issue.

Check:
- `/opt/openbrain/.env` exists
- required keys are present:
  - `OPENBRAIN_DATABASE_URL`
  - `OPENBRAIN_ARCHIVE_DIR`

## Symptom: Brian MCP unavailable
Check:

```bash
curl http://127.0.0.1:8094/sources/status
```

Look at:
- `brian_mcp.available`
- `tool_names`
- `session_id_present`

## Symptom: repo works but MCP does not
Inspect:
- timeout settings
- network access
- MCP tool discovery in source status

## Symptom: OpenClaw cannot use the bridge
Check:
- `openbrainctl` is on PATH
- OpenClaw tool profile allows command execution
- the bridge skill is installed in the workspace
- see `OPENCLAW_RETROFIT.md`

---

# Security Notes

## Local memory is private by default
Treat the local DB and archive as sensitive.

## External Brian results are not local memory
Do not auto-save them.

## Secrets do not belong in Markdown archive
Avoid writing secrets into canonical notes.

## Bind locally unless intentionally exposing
The gateway is intended as a local service unless explicitly fronted by another layer.

---

# Summary

This repository implements a **personal canonical memory system** for OpenClaw.

The central model is:

- **OpenClaw** = assistant runtime
- **OpenBrain Gateway** = memory control plane
- **Postgres + pgvector + Markdown** = canonical local memory
- **Brian Madden MCP** = external expert source
- **OpenClaw bridge** = thin, upgrade-safe integration layer

The most important long-term design choice is that **canonical memory remains external to OpenClaw core**.

For future OpenClaw reconnect work, always consult:

```text
OPENCLAW_RETROFIT.md
```

That file is the operational companion to this README.

