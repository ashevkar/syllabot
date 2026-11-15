# Syllabot Platform — Build Plan

**Status:** Draft for review · **Date:** 2026-10-26 · **Sources of truth:** `docs/requirements.md`, `docs/architecture.md`, `docs/database-schema.md`, `docs/planning-prompt.md`

This plan does not change the docs. Wherever it proposes something different from them, it is marked **⚠ needs your approval**, and nothing in that list is built until you approve it.

---

## Decisions needed before M1 starts

Each item has a recommended default. "Accept all defaults" is a valid answer. Details are in [§1](#1-gaps-and-conflicts) and [§7](#7-tech-decisions).

| # | Decision | Recommended default | Why it can't wait |
|---|---|---|---|
| D1 | ⚠ **Frontend: Next.js 14 → Next.js 16.** Next.js 14 has been unsupported since Oct 2025 (it gets no security fixes, including CVE-2026-23864). The 2-year window for 15.x ends around now. | Next.js **16.4.x** (Active LTS), React 19, TypeScript **6.0.x**, Tailwind **4.3** | Affects M1-12 onwards |
| D2 | ✅ **Default model — decided 2026-11-02: Gemini free tier, Ollama as backup.** `gpt-4o-mini`, the docs' example, is removed from OpenAI's API on 2027-01-14, and you prefer no paid API. | Chat **`gemini:gemini-3.5-flash-lite`**, judge **`gemini:gemini-3.6-flash`**, embeddings **`gemini-embedding-2` at 1536 d** (all stable, all on the free tier). Backup: **`ollama:qwen3:8b`**. M1-15 compares the two on the eval set. Free-tier caveats are under R4/R6. | Affects M1-04, M1-05 |
| D3 | ⚠ **The per-bot "temperature" setting (FR-11).** Claude Haiku 5.5 rejects non-default `temperature`. Anthropic's Python SDK ≥ 1.0 removed it. The OpenAI models are reasoning models with an effort setting instead. | Keep `temperature` as an **optional advanced setting** that is only sent to models that support it (Ollama). The UI hides it for other models. Add a per-bot `reasoning_effort` (default `none`/`low` for latency). | Affects the settings schema in M1-03 |
| D4 | **FR-5 "require login" for students** conflicts with "students are anonymous in v1, no `users` row". | Defer to *Later*. Keep the `require_login` column, always `false`, and don't show it in the UI. | Scope |
| D5 | ⚠ **Schema additions** (details in §1 B): `refresh_tokens`, `llm_models`, `llm_usage`, `chat_messages.query_embedding`, and an embedding dimension set from config. | Approve all five | Affects M1-03 and M2 |
| D6 | **Collaborator invites (FR-15)** have no email service and no invites table. | v1 invites **existing accounts only**, by email lookup. Emailed invites go to *Later*. | Affects M2-04 |
| D7 | **The "real syllabus" for M1 acceptance.** | You provide one you may use (your own, or one published openly). I also write a synthetic fixture syllabus for automated tests (§4.4). | Affects M1-14 and M1-15 |
| D8 | **Demo sign-up mode and hosting budget.** | `SIGNUP_MODE=closed` on the public demo with a demo instructor account, and open in dev. Budget about **$15–30/month** plus about $12/year for a domain, which is needed for same-site auth cookies. | Affects M2-01 and M5 |
| D9 | **Unused schema values:** `collab_level 'viewer'` and `bot_status 'archived'` are not in the requirements. | Keep them in the enums but don't use them in v1, so no migration is needed later. | Low |

---

## 1. Gaps and conflicts

Legend: **C** = needs your confirmation · **P** = proposed default that I'll apply unless you object.

### A. Technology conflicts (the docs name something outdated)

| # | Issue | Where | Proposed decision | |
|---|---|---|---|---|
| A1 | Next.js 14 is unsupported. Next 16 also removes `next lint`, and `next build` no longer lints. | architecture §3, planning-prompt | Next.js 16.4.x. Lint runs through the ESLint CLI in CI (D1). | **C** |
| A2 | `gpt-4o-mini` is retiring, and so are `gpt-5-mini`/`nano`. | architecture §7, schema `templates.default_model` example | Use Gemini 3.5 Flash-Lite on the free tier, with Ollama as backup (D2). | ✅ |
| A3 | `temperature` is gone or rejected on the current cheap models. | FR-11, `bots.settings` | Make it an optional setting gated by model capability, and add `reasoning_effort` (D3). | **C** |
| A4 | "Llama 3.1 8B local" is now dated. Guides recommend Qwen3 8B for following "answer only from context" instructions. | architecture §7 | Use `qwen3:8b` as the Ollama backup model. Any Ollama tag still works. | ✅ |
| A5 | "bge-small-en" is ambiguous. The current model is `BAAI/bge-small-en-v1.5` (384 dims). | architecture §3, schema §3.6 | Use `bge-small-en-v1.5` through **fastembed** (ONNX, no PyTorch). | **P** |
| A6 | Python 3.12 is now security-only. Celery 5.6 officially supports up to 3.13, and 3.14 support is "initial". | planning-prompt | **Keep 3.12.** Every chosen library supports it. Re-check before M5. | **P** |
| A7 | Anthropic's Python SDK moved from `httpx` to `httpx2`, because the old `httpx` is unmaintained (last release Dec 2024). | — | Use `httpx2` wherever we pass our own HTTP clients. Check which client FastAPI's TestClient uses at M1-01. | **P** |

### B. Requirements vs schema/architecture conflicts

| # | Issue | Proposed decision | |
|---|---|---|---|
| B1 | **FR-5** optional student login, but students have no accounts. | Defer to Later (D4). | **C** |
| B2 | **Embedding dimension is fixed** at `VECTOR(1536)`, but NFR-13 wants providers swappable by config. | Migration 0001 reads `EMBEDDING_DIM` from settings (1536 for `gemini-embedding-2`, 384 for local bge). Gemini's default of 3072 d is over pgvector's 2000-d HNSW limit, so we request 1536. Changing it later requires an explicit "re-embed" command that rebuilds the column and index. The API refuses to start if `EMBEDDING_DIM` doesn't match the DB column. | **C** (D5) |
| B3 | **Refresh tokens (FR-3)** have no table, so they can't be revoked. | New `refresh_tokens` table (id, user_id, token_hash, expires_at, revoked_at, created_at, replaced_by), with rotation on every refresh. | **C** (D5) |
| B4 | **Admin "manage models" (§2 roles)** has no table or endpoints. NFR-11 needs prices to compute cost. | New `llm_models` table (id, provider, model_id, display_name, supports_temperature, input_usd_per_mtok, output_usd_per_mtok, is_active). Bot and template `model` values must reference an active row. This also gives a path to bulk-migrate bots when a model is retired, which already happened once (A2). | **C** (D5) |
| B5 | **Cost per bot (NFR-11):** `chat_messages` has tokens, but ingestion, extraction and eval calls are logged nowhere. | New `llm_usage` table (bot_id, kind `chat/embed/extract/eval_answer/eval_judge`, model, input_tokens, output_tokens, cost_usd, created_at). | **C** (D5) |
| B6 | **"Most frequent questions, grouped by similarity" (FR-37)** needs the question embeddings, which aren't stored. | Add a nullable `chat_messages.query_embedding VECTOR(dim)` column for user messages; the embedding is already computed for retrieval. Group at read time with greedy clustering (cosine ≥ 0.85) over the last 30 days. | **C** (D5) |
| B7 | `collab_level 'viewer'` and `bot_status 'archived'` aren't in the requirements. | Keep in the enums, unused in v1 (D9). | **C** |
| B8 | The share slug example is 8 chars (`k3f9x2ab`); the schema comment says 10 chars base62. | **10 chars base62** from `secrets` (about 59 bits), with a retry on unique collision. | **P** |
| B9 | M1 says "No auth", but `bots.owner_id` is NOT NULL. | Migration 0001 creates the **full schema**. M1 seeds a dev user and one bot with a CLI command (`python -m app.cli seed-dev`). | **P** |
| B10 | Collaborator rights: the requirements say "edit"; the API makes publish, rotate and invite owner-only. | Collaborators (editor) can edit settings, documents, schedule and evals, and run preview chat. Only the owner can publish, unpublish, rotate the slug, manage collaborators or delete. Admins can do everything. | **P** |
| B11 | Access to another instructor's bot: 403 or 404? | **404** for bots the caller can't access, so a bot's existence doesn't leak. | **P** |

### C. Missing details

| # | Gap | Proposed decision | |
|---|---|---|---|
| C1 | **Invites by email (FR-15)** have no email provider. | Existing accounts only (D6). | **C** |
| C2 | **Missing endpoints.** The API table lacks: duplicate bot, list/remove collaborators, create/delete schedule items, replace document, list/view chat logs (FR-39), update/delete eval cases, eval run detail, admin users/models/metrics, `GET /auth/me`, `POST /auth/logout`, and `GET /health`. | Add them with the same auth rules (list in §3.5). | **P** |
| C3 | **Duplicate bot (FR-10): what gets copied?** | Settings, documents (same stored file), chunks, schedule items and eval cases are copied with new IDs. The copy gets a new slug, starts in `draft`, and has no collaborators, chats or eval runs. Chunks are copied without re-embedding. | **C** |
| C4 | **Who creates `session_id`?** | The server creates a `chat_sessions` row on the first message and returns its id in the first SSE `meta` event. The client keeps it in `sessionStorage` (per tab; this works inside iframes). The server checks that the session belongs to the bot. | **P** |
| C5 | **Feedback endpoint abuse:** `/public/messages/{id}/feedback` is unauthenticated. | The body must include `session_id`, which must match the message's session. Feedback is allowed only on assistant messages, and a new vote replaces the old one. The endpoint is rate limited. | **P** |
| C6 | **Creating the first admin.** | `python -m app.cli create-admin --email ...`, which reads the password from a prompt or an env var. Sign-ups are always instructors. | **P** |
| C7 | **Open sign-up on a public demo** risks spending money on LLM calls. | `SIGNUP_MODE=open|closed` (D8), plus a global daily LLM spend cap (`DAILY_LLM_BUDGET_USD`) that switches the public chat to the fallback message when hit. This is ops protection, not new product scope. | **C** |
| C8 | **Publishing with no eval run yet (FR-35).** | Warn "No evaluation has been run" and still allow publishing. Warn the same way below 80%. | **P** |
| C9 | **Retention (NFR-6) "configurable":** per bot or global? | Global `CHAT_RETENTION_DAYS=180`, enforced by a nightly Celery beat job. Per-bot retention goes to Later. | **P** |
| C10 | **Relative dates** ("this week", "next Friday"). | "Today" is computed server-side in `bots.timezone` and added to the prompt context. The date heuristic expands relative ranges before querying `schedule_items`. | **P** |
| C11 | **Schedule items without a full date** ("Week 5: Midterm", "Oct 15" with no year). | Infer the year from `bots.term`. If there's no concrete date, don't create a schedule row; the text chunk still answers. Items are created `verified=false`. | **P** |
| C12 | **URL sources (FR-17)**: refresh behaviour and safety. | One snapshot when added, plus a "Re-fetch" action. SSRF guard: http/https only, block private, loopback and link-local IPs after DNS resolution, 10 s timeout, 5 MB cap, at most 3 redirects with each one re-checked. | **P** |
| C13 | **Limits (FR-16):** do URL sources count toward the 20? Duplicate uploads? | 20 sources per bot in total (files + URLs). A file whose `content_hash` matches an existing document in the same bot is rejected with 409. | **P** |
| C14 | **Renaming the course** changes the `[Course: X]` embedding prefix. | No automatic re-embed. A "Reprocess all documents" action is available. | **P** |
| C15 | **Scanned PDFs** have no text layer, and OCR isn't in scope. | Detect "almost no extractable text" and set status `failed` with the message "This PDF looks scanned; upload a text-based PDF or DOCX." | **P** |
| C16 | **iframe embedding (FR-31)** vs clickjacking. | `/b/[slug]` sends `Content-Security-Policy: frame-ancestors *`. Every other page sends `frame-ancestors 'none'`. A per-bot origin allow-list goes to Later. | **P** |
| C17 | **Auth token transport** when the frontend (Vercel) and API (separate host) are on different domains. | Keep the access token (15 min) in memory. Put the refresh token (14 days) in an `HttpOnly; Secure; SameSite=Lax` cookie scoped to `/auth`. For the cookie to work, the app and API must share a registrable domain (`app.example.dev` and `api.example.dev`), so a custom domain is needed (D8). Public chat uses no cookies. | **C** |
| C18 | **Evaluation judge model.** | Use a separate `JUDGE_MODEL` one tier up from the answering model: `gemini-3.6-flash` judging `gemini-3.5-flash-lite`. It's the same provider, so some self-preference bias is possible; this is noted in eval reports, and judging with `qwen3:8b` is a cross-check. The judge also gets the retrieved chunks, so it can tell whether a "fail" came from retrieval or from generation. | **P** |
| C19 | **Analytics days** (FR-36): UTC or local? | Group by day in `bots.timezone`. | **P** |
| C20 | **`updated_at`** maintenance. | ORM `onupdate=func.now()`. No DB trigger. | **P** |

---

## 2. Milestone breakdown

Estimates assume about 11 h/week. **Total ≈ 227 h ≈ 21 weeks**, or about 24 weeks with a 15 % buffer. Task IDs are used for dependencies. Each milestone ends with a tagged release (`v0.1-m1`, and so on).

| Milestone | Tasks | Hours | ≈ Weeks |
|---|---|---|---|
| M1 Single-bot RAG | 15 | 63 | 6 |
| M2 Multi-tenant | 11 | 48 | 4.5 |
| M3 Templates & sharing | 11 | 41 | 4 |
| M4 Quality & insight | 11 | 43 | 4 |
| M5 Deploy | 8 | 32 | 3 |

### M1 — Single-bot RAG (no auth)
Goal: upload → chunk → embed → streamed chat with citations and fallback. **Done when 15 of 20 test questions on a real syllabus pass** (§4.4).

- [x] **M1-01 · Repo skeleton & tooling** · 4 h · needs —
  Touches: root files from §3 (`.pre-commit-config.yaml`, `.editorconfig`, `Makefile`, `.github/workflows/ci.yml`), `backend/pyproject.toml` + `uv.lock`, `frontend/package.json` + lockfile.
  Done when: `make lint` and `make test` pass on an empty app. CI runs ruff, mypy, eslint, prettier --check and pytest on push. `pre-commit run --all-files` is clean.
  *Done 2026-11-02.* Versions were re-checked with the 14-day rule, which is now enforced automatically by `exclude-newer = "14 days"` (uv) and `min-release-age=14` (npm). Differences from §7: **FastAPI 0.146.0** (0.147+ is under 14 days old), **uv 0.13.1** in CI, **httpx2 2.14.0** for tests (Starlette 1.9's TestClient deprecates httpx, which closes A7), **TypeScript 6.0.3** (confirmed: typescript-eslint 8.71 needs TS < 6.1), and **@types/node 24.19.2**. Accepted for now: `npm audit` reports 16 moderate findings, all one minimatch ReDoS advisory in dev-only lint plugins. Production dependencies have 0 findings.
- [x] **M1-02 · Dev stack & settings** · 3 h · needs M1-01
  Touches: `docker-compose.yml` (postgres, redis, api, frontend, migrate), `backend/app/config.py` (pydantic-settings), `backend/app/main.py`, `.env.example`.
  Done when: `docker compose up` brings everything up healthy. `GET /health` returns DB and Redis status. A missing required env var fails fast with a clear message.
  *Done 2026-11-02.* `make dev` brings all 4 services up healthy. `/health` returns 200, or 503 naming the dependency that's down; both outages were tested live. Image policy: **base images take the latest patch of their pinned version line** (Redis 8.10.3 was a security release), while **app images and libraries keep the 14-day rule** (so Ollama is 0.40.7). Other differences: Postgres is exposed on host port **5433**, since 5432 is commonly taken by a local install. The `migrate` service moves to M1-03, when Alembic exists. `app/db/session.py` (the engine only) arrived early because `/health` needs it. Libraries added: SQLAlchemy 2.1.5, asyncpg 0.32.0, redis 8.1.0, pydantic-settings 2.16.0.
- [x] **M1-03 · DB models & migration 0001** · 5 h · needs M1-02
  Touches: `backend/app/db/session.py`, `backend/app/db/models/*.py`, `backend/app/db/migrations/versions/0001_initial.py`.
  Done when: `alembic upgrade head` on an empty DB creates every extension, enum, table and index in database-schema.md, plus the approved D5 additions. `downgrade base` is clean. A test inserts user → bot → document → chunk and queries it back.
  *Done 2026-11-02.* Migration `0001_initial_schema` creates 3 extensions, 9 enums, 12 tables and all 13 named indexes from the doc, checked against `pg_indexes`. **No D5 additions yet**, since D5 isn't approved. None is needed here: `gemini-embedding-2` at 1536 d matches the doc's `VECTOR(1536)`, and each addition lives in its own later migration (M2-01, M2-07, M4-09). `EMBEDDING_DIM` is a single constant in `app/db/models/chunk.py`. Integration tests (testcontainers with the compose pgvector image) cover: the user → bot → document → chunk round trip and server defaults, CITEXT email, cosine ordering, document → chunk cascade, the `documents` check constraint, a clean `downgrade base` round trip, and **model/migration drift** (the same check as `alembic check`, so M5-02 gets it for free). Compose `migrate` runs before `api`. Constraint names follow a naming convention, and the ruff hook formats new revisions.
- [x] **M1-04 · LLM provider interface + adapters** · 5 h · needs M1-02
  Touches: `backend/app/providers/llm/{base,gemini,ollama,fake}.py`, `backend/app/providers/registry.py`.
  Done when: `LLMProvider` exposes `stream_chat()` (yields text deltas plus a final usage record) and `complete_json(schema)`. Model strings are `provider:model_id`. Unit tests run against `FakeLLM`. A Gemini 429 or quota-exhausted response maps to a typed `ProviderQuotaError`; chat turns it into a friendly "busy, try later" message, not a 500. Optional `FALLBACK_CHAT_MODEL` (Ollama) is tried on quota errors. One opt-in smoke test per real provider (`pytest -m live`) streams a reply.
  *Done 2026-11-02.* `app/providers/`: a `ModelRef` parser (`ollama:qwen3:8b` keeps its tag), an `LLMProvider` ABC, a `ChatModel` protocol, `GeminiProvider` (google-genai 2.31), `OllamaProvider` (ollama 0.6.3), `FakeLLM`, `FallbackChatModel` and `ProviderRegistry` (lazy clients, closed in the app lifespan). Streams end with exactly one `Usage` event (input, output and thinking tokens, plus the model that *actually* answered). `reasoning_effort` maps to Gemini `thinking_level`, with `none` → MINIMAL because Gemini 3 can't switch thinking off, and to Ollama `think`. Gemini SDK retries cover 408/5xx only. **429 is not retried**, and becomes `ProviderQuotaError` with `retry_after_s` from RetryInfo. Fallback triggers on quota/outage errors only, and only before any text was streamed; auth errors surface. 47 unit tests use stub SDK clients that return real SDK response types. `make test-live` runs the opt-in smoke tests. **Live result:** Gemini returned 403 *"free tier is not available for this project"*. Eligibility is per Google Cloud project; the official fix is billing (see R6/D2). Ollama was skipped because it's not installed.
- [ ] **M1-05 · Embedding provider interface + adapters** · 3 h · needs M1-02
  Touches: `backend/app/providers/embeddings/{base,gemini,local,fake}.py`.
  Done when: `embed_documents(list[str])` (batched) and `embed_query(str)` return vectors of `EMBEDDING_DIM`. A dimension mismatch raises at startup. FakeEmbeddings is deterministic, so tests are repeatable.
- [ ] **M1-06 · Text extraction (PDF/DOCX/TXT/MD)** · 5 h · needs M1-01
  Touches: `backend/app/services/ingestion/extract.py`, `tests/unit/ingestion/test_extract.py`, `tests/fixtures/docs/*`.
  Done when: each format returns `list[Block(text, page, heading_level|None, font_size, bold)]`. PDF heading candidates come from font size and bold relative to the body-text median. DOCX uses `Heading n` styles. Markdown uses `#`. A scanned PDF raises `NoTextLayerError`. Fixture tests cover all four formats.
- [ ] **M1-07 · Heading-aware chunker** · 4 h · needs M1-06
  Touches: `backend/app/services/ingestion/chunker.py`, tests.
  Done when: there is one chunk per section, with a split at about 500 tokens and about 60 tokens of overlap. Each chunk has `section_title`, `page_start`/`page_end` and `token_count`. Plain-text heading lines ("Grading Policy") are detected. If no headings are found, it falls back to fixed-size chunks. The `[Course: X] [Section: Y]` prefix is added before embedding but not stored in `content`. Golden-file tests run on the fixture syllabus.
- [ ] **M1-08 · Storage + ingestion pipeline + documents API** · 5 h · needs M1-03, M1-05, M1-07
  Touches: `backend/app/services/storage.py` (local backend), `backend/app/services/ingestion/pipeline.py`, `backend/app/routers/documents.py`.
  Done when: `POST /bots/{id}/documents` checks MIME type (magic bytes), size and the 20-source limit, saves the file under a random key and returns 202. A FastAPI BackgroundTask moves the document `uploaded → processing → ready/failed`. `DELETE` removes chunks and the file. A 30-page fixture processes in under 2 minutes (NFR-9).
- [ ] **M1-09 · Retrieval service** · 3 h · needs M1-03, M1-05
  Touches: `backend/app/services/retrieval.py`, tests.
  Done when: `search(*, bot_id: UUID, query_vec, top_k, min_score)` is the **only** function that queries `chunks` (`bot_id` is keyword-only with no default). It sets `hnsw.iterative_scan = relaxed_order`. Tests check ordering, the threshold and bot scoping.
- [ ] **M1-10 · Prompt builder + answer orchestrator** · 5 h · needs M1-04, M1-09
  Touches: `backend/app/services/prompt_builder.py`, `backend/app/services/answer.py`.
  Done when: the prompt follows architecture §5.2. Context is numbered chunks inside `<context>` delimiters, plus the injection rule (NFR-4). Below the threshold, the bot returns the fallback message plus `contact_info` without calling the LLM. Citations are returned as structured `[{chunk_id, section, page}]` from the chunks actually cited, parsed from `[n]` markers. Unit tests cover the fallback, citation parsing and a 6-message history cap.
- [ ] **M1-11 · Chat SSE endpoint + logging** · 4 h · needs M1-10
  Touches: `backend/app/routers/chat.py`, `backend/app/services/chat_log.py`.
  Done when: `POST /public/bots/{slug}/chat` streams `meta` (session_id), `token`*, `citations`, then `done` using FastAPI's native `EventSourceResponse`. It writes user and assistant `chat_messages` with retrieved_chunk_ids, top_score, is_fallback, tokens and latency. A client disconnect stops LLM streaming and still logs a partial answer. An integration test reads the stream with an ASGI client.
- [ ] **M1-12 · Frontend scaffold + chat page** · 6 h · needs M1-11, D1
  Touches: `frontend/app/b/[slug]/page.tsx`, `frontend/components/chat/*`, `frontend/lib/api/{client.ts,schema.d.ts,sse.ts}`.
  Done when: Next 16 + Tailwind 4 + shadcn/ui are set up. Types are generated from `/openapi.json` (`make gen-api`). Tokens stream into the page, citations show as chips with section and page, and the fallback message has its own style.
- [ ] **M1-13 · Frontend upload & document status** · 3 h · needs M1-08, M1-12
  Touches: `frontend/app/bots/[id]/documents/page.tsx`.
  Done when: drag-and-drop upload works, status badges poll every 2 s until each document is ready or failed, failed documents show the error message, and documents can be deleted.
- [ ] **M1-14 · Fixture syllabus, 20-question set, eval harness CLI** · 4 h · needs M1-10
  Touches: `backend/tests/eval/fixtures/sample_syllabus.{md,docx,pdf}`, `backend/tests/eval/questions.yaml`, `backend/app/cli.py eval-file`.
  Done when: `python -m app.cli eval-file <syllabus> <questions.yaml>` ingests into a temporary bot, answers all questions through `answer.py`, scores them with the LLM judge (plus exact checks for fallback and refusal), and prints a table and a JSON report.
- [ ] **M1-15 · M1 acceptance & model comparison** · 4 h · needs M1-13, M1-14, D2, D7
  Touches: `docs/decisions/0001-default-model.md` (new ADR), `bots.settings` defaults.
  Done when: you've run the fixture and real syllabi on `gemini-3.5-flash-lite` and on the backup `qwen3:8b`. **15 or more of 20 pass on the real syllabus** with the default. The ADR records accuracy, p95 first-token latency, free-tier requests used per eval run (and the paid-equivalent cost), and sets the default model and `min_score`.

### M2 — Multi-tenant
Goal: users, roles, many bots, `bot_id` isolation, Celery. **Done when the isolation tests pass and two instructors' bots never mix data.**

- [ ] **M2-01 · Auth backend** · 6 h · needs M1-03, D5, D8
  Touches: `backend/app/auth/{passwords,tokens,deps}.py`, `backend/app/routers/auth.py`, migration `0002_refresh_tokens`.
  Done when: signup (respects `SIGNUP_MODE`), login, refresh (rotation + reuse detection that revokes the whole chain), logout and `/auth/me` all work. Passwords use argon2 via pwdlib. Access JWTs last 15 min, with `sub`, `role`, `exp` and `iat`. Login is rate limited. Tests cover expiry, a refresh token reused after rotation, and inactive users.
- [ ] **M2-02 · Authorization dependency** · 4 h · needs M2-01
  Touches: `backend/app/auth/access.py` (`require_bot_access(level)`), every bot router.
  Done when: levels are `owner`, `editor` and `admin` (the B10 rules). Inaccessible bots return 404 (B11). A parametrized test walks **every** route in the OpenAPI schema and asserts it either is public or declares an access dependency.
- [ ] **M2-03 · Bots CRUD API** · 4 h · needs M2-02
  Touches: `backend/app/routers/bots.py`, `backend/app/schemas/bots.py`.
  Done when: list (owned + collaborated), create (blank), get, patch and delete work. Delete cascades (a test confirms chunks, schedule and sessions are gone). Settings are validated, including temperature only for models that support it (D3).
- [ ] **M2-04 · Collaborators API** · 3 h · needs M2-03, D6
  Touches: `backend/app/routers/collaborators.py`.
  Done when: the owner can add a collaborator by email (existing user only; an unknown email gets 404 "Ask them to sign up first"), list and remove. Collaborators can't delete the bot or manage collaborators (tests).
- [ ] **M2-05 · Celery worker + retries** · 5 h · needs M1-08
  Touches: `backend/app/workers/{celery_app,tasks,async_runner}.py`, `docker-compose.yml` (worker).
  Done when: `process_document` runs in the worker. Async service code runs in one event loop per worker process, created in `worker_process_init`. Failures retry 3 times with exponential backoff plus jitter (NFR-10), then mark the document `failed` with the error. `acks_late` and idempotency mean a re-run first deletes that document's existing chunks.
- [ ] **M2-06 · URL sources** · 3 h · needs M2-05
  Touches: `backend/app/services/ingestion/fetch_url.py`, the documents router.
  Done when: `POST /bots/{id}/documents` with `{url}` works. trafilatura extracts the main text and headings. The SSRF guard (C12) passes tests for `127.0.0.1`, `169.254.169.254`, a redirect to a private IP, and an oversized body.
- [ ] **M2-07 · Structured logging + usage/cost** · 4 h · needs M2-05, D5
  Touches: `backend/app/core/logging.py` (structlog), `backend/app/middleware/request_id.py`, `backend/app/services/usage.py`, migration `0003_llm_models_usage`.
  Done when: logs are JSON with `request_id` and `bot_id` and are propagated into Celery tasks. Every LLM and embedding call writes `llm_usage` with cost from `llm_models`. A test checks the cost math.
- [ ] **M2-08 · Tenant isolation test suite** · 5 h · needs M2-03, M2-05
  Touches: `backend/tests/integration/test_tenant_isolation.py` and `backend/tests/architecture/test_chunk_access.py`.
  Done when: every check in §4.3 passes in CI against real Postgres + pgvector.
- [ ] **M2-09 · Frontend auth** · 5 h · needs M2-01, M1-12
  Touches: `frontend/app/(auth)/{login,signup}/page.tsx`, `frontend/lib/auth.ts`, `frontend/middleware.ts` (route guard).
  Done when: a user can log in and out. The access token refreshes silently on 401, with one retry. Protected routes redirect to login. Forms are keyboard-accessible and labelled.
- [ ] **M2-10 · Dashboard + bot settings form** · 5 h · needs M2-03, M2-09
  Touches: `frontend/app/dashboard/page.tsx`, `frontend/app/bots/[id]/edit/page.tsx`.
  Done when: the dashboard lists bots with status and document counts. The settings form covers every FR-11 field and shows server validation errors.
- [ ] **M2-11 · Multi-bot documents page + collaborators UI** · 4 h · needs M2-04, M2-10, M1-13
  Touches: `frontend/app/bots/[id]/documents/page.tsx`, `frontend/app/bots/[id]/edit/collaborators.tsx`.
  Done when: the documents page from M1-13 works per bot behind auth and supports URL sources. The owner can add and remove collaborators.

### M3 — Templates and sharing
Goal: templates, publish/draft, share links, embed. **Done when an instructor creates and shares a bot from the template in under 30 minutes.**

- [ ] **M3-01 · Templates API + seed** · 4 h · needs M2-02
  Touches: `backend/app/routers/templates.py`, `backend/app/routers/admin/templates.py`, `backend/app/seed/syllabus_assistant.py`.
  Done when: instructors can list active templates and admins can create and patch them. Migration or seed creates the **Syllabus Assistant** template (FR-7) with the system prompt, fallback message, suggested questions and default settings.
- [ ] **M3-02 · Create from template / blank** · 3 h · needs M3-01, M2-03
  Touches: `backend/app/services/bots.py`.
  Done when: `POST /bots {template_id}` copies values (FR-8). A test edits the template afterwards and checks that the existing bot is unchanged. Blank creation uses platform defaults (FR-9).
- [ ] **M3-03 · Admin UI: templates** · 4 h · needs M3-01, M2-09
  Touches: `frontend/app/admin/templates/*`.
  Done when: an admin can list, create, edit and deactivate templates, with a preview of the welcome message and suggestions.
- [ ] **M3-04 · Admin: users & models** · 5 h · needs M2-07
  Touches: `backend/app/routers/admin/{users,models,metrics}.py`, `frontend/app/admin/{users,models}/*`.
  Done when: an admin can list and deactivate users, manage `llm_models` (add, deactivate, set prices) and bulk-move bots from a retiring model. A metrics endpoint returns platform totals (bots, questions, cost over 30 days).
- [ ] **M3-05 · Lifecycle + public bot endpoint** · 3 h · needs M2-03
  Touches: `backend/app/routers/bots.py` (publish/unpublish/rotate-slug), `backend/app/routers/public.py`.
  Done when: `GET /public/bots/{slug}` returns the name, welcome message and suggestions only when published. Acceptance tests: a **draft slug returns 404**, and **after rotation the old slug returns 404** (§6 of requirements).
- [ ] **M3-06 · Public chat page polish** · 6 h · needs M3-05, M1-12
  Touches: `frontend/app/b/[slug]/*`, `frontend/components/chat/*`.
  Done when: the page shows the course header, welcome message, suggested-question chips and a short notice: "Don't share personal information" (free-tier data use, R6). It works at 360 px width. Keyboard: Enter sends, Shift+Enter adds a newline, and focus is managed. The message list uses `aria-live="polite"`. Contrast passes AA. axe reports no serious or critical issues.
- [ ] **M3-07 · Embedding** · 3 h · needs M3-06
  Touches: `frontend/next.config.ts` (headers), `frontend/app/bots/[id]/share/page.tsx`.
  Done when: CSP is set as in C16. The share page shows the link, a QR code (if done without a new dependency; otherwise skipped) and an `<iframe>` snippet. A static test page embeds the bot and chat works in it.
- [ ] **M3-08 · Preview chat with retrieved chunks** · 4 h · needs M3-02, M1-11
  Touches: `backend/app/routers/preview.py`, `frontend/app/bots/[id]/test/page.tsx`.
  Done when: `POST /bots/{id}/preview-chat` works on draft bots and uses `is_preview=true` sessions. The panel shows retrieved chunks with scores and the threshold line (FR-32). Preview sessions are excluded from analytics (test).
- [ ] **M3-09 · Duplicate bot** · 3 h · needs M3-02
  Touches: `backend/app/services/bots.py` (`duplicate`), the dashboard menu.
  Done when: the copy behaves as in C3, and tests check new IDs, draft status, the new slug and no chat history.
- [ ] **M3-10 · Bot creation wizard** · 4 h · needs M3-02, M2-11
  Touches: `frontend/app/bots/new/*`.
  Done when: the wizard goes template → course info → upload → test → publish, with progress kept if the user leaves partway.
- [ ] **M3-11 · 30-minute run-through** · 2 h · needs M3-05…M3-10
  Touches: `docs/runbooks/m3-usability.md`.
  Done when: a timed run from a fresh account to a shared link takes under 30 minutes, and the friction notes are recorded and fixed or ticketed.

### M4 — Quality and insight
Goal: schedule extraction, evals, analytics, ratings, rate limiting. **Done when the eval page and analytics work end to end.**

- [ ] **M4-01 · Schedule extraction** · 5 h · needs M2-05
  Touches: `backend/app/services/ingestion/schedule.py`, `backend/app/workers/tasks.py`.
  Done when: after chunking, the model reads schedule-like sections and returns JSON validated by Pydantic (title, kind, starts_at/due_at, all_day, location, source chunk). Year inference follows C11. Re-processing replaces that document's items. On the fixture syllabus, extraction precision and recall are ≥ 90 % against a hand-labelled list.
- [ ] **M4-02 · Schedule review API + UI** · 5 h · needs M4-01
  Touches: `backend/app/routers/schedule.py` (GET/POST/PATCH/DELETE), `frontend/app/bots/[id]/schedule/page.tsx`.
  Done when: the UI shows an editable table with a "verified" toggle, source chunk preview and manual add (FR-21). Times display in `bots.timezone`.
- [ ] **M4-03 · Date-question routing** · 4 h · needs M4-01, M1-10
  Touches: `backend/app/services/date_intent.py`, `answer.py`.
  Done when: a keyword and regex heuristic (no LLM) detects date questions and relative ranges (C10). Matching schedule rows are added to the context first (FR-27). Acceptance test: "When is the midterm?" returns Oct 15 and cites the schedule section.
- [ ] **M4-04 · Eval cases API + UI** · 4 h · needs M3-08
  Touches: `backend/app/routers/evals.py`, `frontend/app/bots/[id]/evals/page.tsx`.
  Done when: eval cases support CRUD, including `expect_fallback`. Cases can be imported from and exported to YAML (the same format as `questions.yaml`).
- [ ] **M4-05 · Eval runner + judge** · 5 h · needs M4-04, M2-05
  Touches: `backend/app/services/evaluator.py`, the `run_eval` task.
  Done when: each case goes through `answer.py` with no shortcuts. Fallback cases are scored by `is_fallback` and the rest by the judge (C18), returning verdict and reason. The run saves `eval_runs` and `eval_results`, and a failed case records `error` without failing the whole run.
- [ ] **M4-06 · Eval results UI + publish warning** · 3 h · needs M4-05, M3-05
  Touches: `frontend/app/bots/[id]/evals/runs/[runId]/page.tsx`, the publish dialog.
  Done when: the run page shows the score and, per case, the answer, sources and reason. The publish dialog shows the latest score and warns below 80 % or when no run exists (C8).
- [ ] **M4-07 · Ratings** · 2 h · needs M1-11
  Touches: `backend/app/routers/public.py` (feedback), the chat message component.
  Done when: thumbs up/down work with the C5 rules and the UI shows the selected state.
- [ ] **M4-08 · Rate limiting** · 3 h · needs M2-05
  Touches: `backend/app/core/ratelimit.py`.
  Done when: there is a Redis moving-window limit per (bot, client IP) using `bots.rate_limit_per_min` (NFR-3), plus a per-IP limit on login. The real client IP is read from `X-Forwarded-For` with a configurable number of trusted proxy hops. A 429 response includes `Retry-After`. Tests use a fake clock.
- [ ] **M4-09 · Analytics API** · 5 h · needs M2-07, D5
  Touches: `backend/app/routers/analytics.py`, `backend/app/services/analytics.py`.
  Done when: endpoints return totals, unique sessions, per-day series, fallback rate, thumbs-down rate (FR-36), frequent-question clusters (B6, FR-37), the list of fallback questions (FR-38), and chat log list and detail (FR-39). Preview sessions are excluded. With 5k seeded messages, the queries run in under 300 ms.
- [ ] **M4-10 · Analytics UI + chat logs** · 5 h · needs M4-09
  Touches: `frontend/app/bots/[id]/analytics/*`.
  Done when: there are stat tiles, a questions-per-day chart, top questions, a "gaps" list (fallbacks) and a chat log viewer with the cited chunks.
- [ ] **M4-11 · Retention job** · 2 h · needs M2-05
  Touches: `backend/app/workers/beat.py`, `docker-compose.yml` (beat).
  Done when: a nightly task deletes sessions older than `CHAT_RETENTION_DAYS` in batches. The test uses frozen time.

### M5 — Deploy
Goal: Docker images, hosted Postgres, CI, deployment. **Done when a public demo URL serves a sample bot.**

- [ ] **M5-01 · Production Dockerfiles** · 4 h · needs M4
  Touches: `backend/Dockerfile` (multi-stage, uv, non-root user), `frontend/Dockerfile` (standalone output, for self-hosting).
  Done when: the API image is under 400 MB (no PyTorch: fastembed is ONNX, and the local embedder is optional). Containers run as non-root, and healthchecks pass.
- [ ] **M5-02 · Full CI pipeline** · 4 h · needs M5-01
  Touches: `.github/workflows/{ci,release}.yml`.
  Done when: CI runs lint, type checks, unit tests and integration tests (Postgres+pgvector and Redis service containers) including isolation tests, builds the images, pushes them to GHCR on `main`, and checks for migration drift (`alembic check`).
- [ ] **M5-03 · S3 storage backend** · 3 h · needs M1-08
  Touches: `backend/app/services/storage.py` (`S3Storage`).
  Done when: `STORAGE_BACKEND=s3` works, tests use moto or a localstack container, and the bucket is private with server-side encryption.
- [ ] **M5-04 · Hosting decision & provisioning** · 5 h · needs M5-01, D8
  Touches: `docs/decisions/0002-hosting.md`, `infra/README.md`.
  Done when: current pricing has been checked again and the hosts chosen (§7 "Deploy"), with Postgres, Redis, API, worker, frontend, S3 bucket, DNS and secrets provisioned. `pgvector` is enabled on hosted Postgres.
- [ ] **M5-05 · Deploy pipeline + migrations + demo seed** · 4 h · needs M5-02, M5-04
  Touches: `.github/workflows/deploy.yml`, `backend/app/cli.py seed-demo`.
  Done when: a merge to `main` deploys. Migrations run as a one-off job before the new API version. A demo instructor and published sample bot exist.
- [ ] **M5-06 · Sentry + spend guard** · 3 h · needs M5-05
  Touches: `backend/app/core/sentry.py`, `frontend/sentry.*.config.ts`, `backend/app/services/budget.py`.
  Done when: errors from the API, worker and frontend reach Sentry with `request_id`. `DAILY_LLM_BUDGET_USD` switches the public chat to fallback when reached (C7).
- [ ] **M5-07 · E2E + a11y checks** · 5 h · needs M5-05
  Touches: `frontend/e2e/*.spec.ts`.
  Done when: Playwright passes against staging for signup → create from template → upload → publish → student chat → thumbs → analytics shows the question. The embed page works, and axe checks pass on the chat page.
- [ ] **M5-08 · Docs + demo rehearsal** · 4 h · needs M5-07
  Touches: `README.md`, `docs/architecture.md` (update to match what was built), `docs/demo-script.md`.
  Done when: the README has a quick start and architecture diagram, the demo (§6) has been rehearsed twice in under 5 minutes, and a backup recording exists.

---

## 3. Repo setup

### 3.1 Folder structure

```
syllabot/
├── .github/workflows/        ci.yml, release.yml, deploy.yml
├── .pre-commit-config.yaml
├── .editorconfig
├── .env.example
├── docker-compose.yml
├── Makefile                  # dev, lint, test, gen-api, migrate, seed-dev, eval
├── PLAN.md
├── README.md
├── docs/
│   ├── requirements.md  architecture.md  database-schema.md  planning-prompt.md
│   ├── decisions/            # ADRs: 0001-default-model.md, 0002-hosting.md, …
│   └── runbooks/
├── backend/
│   ├── pyproject.toml  uv.lock  Dockerfile  alembic.ini
│   ├── app/
│   │   ├── main.py  config.py  cli.py
│   │   ├── core/             logging.py, ratelimit.py, sentry.py, errors.py
│   │   ├── middleware/       request_id.py
│   │   ├── db/               session.py, models/, migrations/
│   │   ├── auth/             passwords.py, tokens.py, deps.py, access.py
│   │   ├── schemas/          # Pydantic request/response models
│   │   ├── routers/          auth.py, templates.py, bots.py, collaborators.py,
│   │   │                     documents.py, schedule.py, preview.py, chat.py,
│   │   │                     public.py, evals.py, analytics.py, admin/
│   │   ├── services/
│   │   │   ├── ingestion/    extract.py, chunker.py, schedule.py, fetch_url.py, pipeline.py
│   │   │   ├── retrieval.py  prompt_builder.py  answer.py  date_intent.py
│   │   │   ├── evaluator.py  analytics.py  usage.py  budget.py  storage.py  bots.py  chat_log.py
│   │   ├── providers/
│   │   │   ├── llm/          base.py, gemini.py, ollama.py, fake.py
│   │   │   ├── embeddings/   base.py, gemini.py, local.py, fake.py
│   │   │   └── registry.py
│   │   ├── workers/          celery_app.py, tasks.py, beat.py, async_runner.py
│   │   └── seed/             syllabus_assistant.py, demo.py
│   └── tests/
│       ├── conftest.py       # testcontainers Postgres+pgvector, Redis; fake providers
│       ├── unit/  integration/  architecture/
│       ├── fixtures/docs/    # small PDFs/DOCX/MD for extraction tests
│       └── eval/             fixtures/sample_syllabus.{md,docx,pdf}, questions.yaml
└── frontend/
    ├── package.json  package-lock.json  next.config.ts  tsconfig.json
    ├── eslint.config.mjs  .prettierrc  postcss.config.mjs  Dockerfile
    ├── app/
    │   ├── (auth)/login, signup
    │   ├── dashboard/
    │   ├── bots/new/  bots/[id]/{edit,documents,schedule,test,evals,analytics,share}/
    │   ├── admin/{templates,users,models}/
    │   └── b/[slug]/         # public chat (embeddable)
    ├── components/           ui/ (shadcn), chat/, bots/, charts/
    ├── lib/                  api/{client.ts, schema.d.ts (generated), sse.ts}, auth.ts
    └── e2e/                  Playwright specs
```

### 3.2 Tooling

| Area | Tool (version checked 2026-10-26) | Config notes |
|---|---|---|
| Python env & deps | **uv 0.13.x**, `uv.lock` (hashes) | `uv sync --frozen` in CI and Docker |
| Python lint + format | **ruff 0.17.x** | rules: `E,F,W,I,B,UP,S,ASYNC,SIM,RUF`. `ruff format` |
| Python types | **mypy 2.4.x** | `strict = true` on `app/`, pydantic plugin; tests are less strict |
| Python tests | **pytest 9.1**, **pytest-asyncio 1.4** (`asyncio_mode=auto`, no `event_loop` fixture), **testcontainers 4.15** | markers: `unit`, `integration`, `live` (real APIs, opt-in), `eval` |
| JS lint | **ESLint 10** flat config + `eslint-config-next` 16.4 (includes jsx-a11y) | run with `eslint .`, since `next lint` no longer exists |
| JS format | **Prettier 3.9** + `prettier-plugin-tailwindcss` (verify at M1-01) | |
| JS tests | **Vitest 5** + Testing Library 16. **Playwright 1.64** for e2e | |
| Git hooks | **pre-commit 4.7** | hooks: ruff, ruff-format, mypy (backend), eslint, prettier, `check-added-large-files`, `detect-private-key`, `gitleaks` (verify version at M1-01) |
| Dependency hygiene | Dependabot (pip/uv, npm, docker, actions) with a **14-day minimum release age**. Exact pins and lockfiles with hashes. | After the LiteLLM PyPI compromises (Mar and Oct 2026), new releases wait 14 days before adoption |
| Node | **Node 24 LTS** | Node 26 enters LTS on 2026-10-28. Move after M1 if the libraries support it |

### 3.3 `.env.example`

```dotenv
# --- App ---
APP_ENV=dev                      # dev | test | prod
LOG_LEVEL=INFO
API_BASE_URL=http://localhost:8000
FRONTEND_ORIGIN=http://localhost:3000
CORS_ORIGINS=http://localhost:3000
SIGNUP_MODE=open                 # open | closed
TRUSTED_PROXY_HOPS=0             # 1 behind a single reverse proxy

# --- Database / Redis ---
DATABASE_URL=postgresql+asyncpg://syllabot:syllabot@postgres:5432/syllabot
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# --- Auth ---
JWT_SECRET=change-me-64-random-bytes
JWT_ACCESS_TTL_MIN=15
JWT_REFRESH_TTL_DAYS=14
CLIENT_HASH_SECRET=change-me     # HMAC key for chat_sessions.client_hash

# --- Storage ---
STORAGE_BACKEND=local            # local | s3
STORAGE_LOCAL_DIR=/data/uploads
S3_BUCKET=
S3_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
MAX_UPLOAD_MB=20
MAX_SOURCES_PER_BOT=20

# --- LLM providers (model strings are provider:model_id) ---
GEMINI_API_KEY=                                 # free key from Google AI Studio
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_CHAT_MODEL=gemini:gemini-3.5-flash-lite
FALLBACK_CHAT_MODEL=ollama:qwen3:8b             # used on Gemini quota errors; empty = off
EXTRACTION_MODEL=                               # empty = DEFAULT_CHAT_MODEL
JUDGE_MODEL=gemini:gemini-3.6-flash             # one tier up

# --- Embeddings (dimension must match the DB column) ---
EMBEDDING_PROVIDER=gemini        # gemini | local
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIM=1536               # 384 for BAAI/bge-small-en-v1.5

# --- Limits / retention / cost ---
RATE_LIMIT_DEFAULT_PER_MIN=20
CHAT_RETENTION_DAYS=180
DAILY_LLM_BUDGET_USD=5

# --- Observability ---
SENTRY_DSN=
NEXT_PUBLIC_SENTRY_DSN=

# --- Frontend ---
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3.4 `docker-compose.yml` services

| Service | Image / build | From | Notes |
|---|---|---|---|
| `postgres` | `pgvector/pgvector:<0.8.7>-pg16` (pin the exact tag or digest at M1-02) | M1 | volume `pgdata`, healthcheck `pg_isready` |
| `redis` | `redis:8-alpine` (pinned minor) | M1 (used from M2) | queue + rate limits. No persistence in dev |
| `migrate` | `./backend` | M1 | one-shot `alembic upgrade head`. `api` and `worker` depend on it completing |
| `api` | `./backend` | M1 | `uvicorn app.main:app --reload`, mounts `./backend`, `uploads` volume |
| `worker` | `./backend` | M2 | `celery -A app.workers.celery_app worker --concurrency=2`, shares the `uploads` volume |
| `beat` | `./backend` | M4 | `celery -A app.workers.celery_app beat` (retention job) |
| `frontend` | `./frontend` | M1 | `next dev`, port 3000 |
| `ollama` | `ollama/ollama` | optional | `profiles: [local-llm]`, so it's only started with `--profile local-llm` |

### 3.5 API additions to architecture §6 (from C2)

`GET /health` · `GET /auth/me` · `POST /auth/logout` · `POST /bots/{id}/duplicate` · `GET/DELETE /bots/{id}/collaborators[/{user_id}]` · `POST/DELETE /bots/{id}/schedule[/{item_id}]` · `PUT /bots/{id}/documents/{doc_id}` (replace) · `POST /bots/{id}/documents/{doc_id}/reprocess` · `PATCH/DELETE /bots/{id}/evals/{case_id}` · `GET /bots/{id}/evals/runs[/{run_id}]` · `GET /bots/{id}/sessions`, `GET /bots/{id}/sessions/{session_id}` · `GET /bots/{id}/analytics/{summary,daily,top-questions,fallbacks}` · `GET/PATCH /admin/users` · `GET/POST/PATCH /admin/models` · `POST /admin/models/{id}/migrate-bots` · `GET /admin/metrics`.

---

## 4. Test strategy

### 4.1 Principles
- Unit tests use `FakeLLM` and `FakeEmbeddings` (deterministic). **No network in the default test run.**
- Integration tests run against **real Postgres 16 + pgvector and Redis** (testcontainers locally, service containers in CI). Each test runs in a transaction that is rolled back, or on a truncated schema.
- `-m live` tests call real providers and are run by hand or nightly, never on PRs.
- `-m eval` runs the RAG evaluation set and reports results without failing CI. The M1 gate is checked by hand.

### 4.2 Per milestone

| Milestone | Unit | Integration | E2E / other |
|---|---|---|---|
| **M1** | extraction per format, chunker golden files, prompt builder, citation parsing, fallback decision, history cap | upload → BackgroundTask → chunks in DB, retrieval ordering and threshold, SSE stream events, chat logging | 20-question eval (§4.4) on fixture and real syllabus |
| **M2** | password hashing, JWT encode/decode/expiry, refresh rotation, SSRF guard, cost calc | auth flows, `require_bot_access` matrix, **tenant isolation suite (§4.3)**, Celery task retries (`task_always_eager` + one real-worker test) | — |
| **M3** | template copy semantics, slug generation | publish/unpublish/rotate → public 404s, preview sessions excluded, duplicate bot | Playwright: create from template → share link opens. axe on `/b/[slug]` |
| **M4** | date-intent heuristic (table-driven, with a fixed clock), schedule JSON validation, judge-verdict parsing, rate-limit window maths | schedule-first answering ("When is the midterm?" → Oct 15 plus schedule citation), eval run end to end with FakeLLM, analytics queries on seeded data, retention job | Playwright: eval run page, analytics shows a new question |
| **M5** | — | `alembic check` (no drift), S3 storage via moto | Playwright full journey against staging. Smoke test after deploy |

### 4.3 Tenant-isolation suite (NFR-1, acceptance criterion 3)

Setup: instructor **A** owns bot **A1** and instructor **B** owns bot **B1**. Both upload syllabi with **the same section titles but conflicting facts**: A1 says "Midterm: Oct 15" and the late policy is 10 %/day, while B1 says "Midterm: Nov 3" and the late policy is "no late work". A real embedding model is not needed, because FakeEmbeddings maps identical text to identical vectors, which is the worst case.

1. **Retrieval:** for 30 queries (including B's exact sentences), `retrieval.search(bot_id=A1)` returns only chunks with `bot_id == A1`. The same holds in the other direction.
2. **Public chat:** asking A1's slug "When is the midterm?" never cites a B1 chunk, the answer contains "Oct 15", and `retrieved_chunk_ids` are all A1's.
3. **Schedule:** A1's date path only reads A1's `schedule_items`.
4. **API access matrix:** using B's token, every `/bots/{A1}/…` route (GET, PATCH, DELETE, documents, schedule, evals, analytics, sessions, preview-chat) returns **404**. This is generated from the OpenAPI route list, so a new route is covered automatically.
5. **Eval runs:** running evals on A1 never stores B1 chunk IDs in `eval_results`.
6. **Analytics:** B's questions never appear in A1's counts, clusters or fallback lists.
7. **Architecture guard:** a test parses `app/` and fails if any module other than `services/retrieval.py` references the `Chunk` model in a `select()`, or if `search()` gains a default for `bot_id`.
8. **Cascade:** deleting A1 leaves B1's rows untouched, and nothing belonging to A1 remains.

### 4.4 RAG evaluation set — 20 questions

**Fixture syllabus** (synthetic, written in M1-14, saved as MD, DOCX and PDF): *CSE 110 — Principles of Programming, Fall 2026, Sample University (timezone America/Phoenix).* Key facts:
- Instructor: Dr. Alex Morgan, alex.morgan@example.edu. Office hours: Tue/Thu 2:00–3:30 pm, ENG 214. TA: Jordan Lee, Wed 10 am–12 pm, Lab ENG 120.
- Class meets MWF 10:30–11:20 am, ENG 101. Textbook: *Think Python, 3rd ed.* (free online).
- Grading: Homework 25 %, Labs 15 %, Midterm 20 %, Final exam 30 %, Participation (in-class quizzes) 10 %. A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60. The lowest 2 quiz scores are dropped.
- Late policy: −10 % per day for up to 3 days, then 0. **2 grace days** per semester, for homework only.
- AI policy: AI tools may be used to explain concepts but not to write submitted code. Any use must be cited.
- Regrades: by email within 7 days of grades being returned. Missed exams: notify the instructor **before** the exam, with documentation of the emergency.
- Schedule: HW1 due Fri **Sep 4** 11:59 pm, then homework due every Friday 11:59 pm. **Midterm Thu Oct 15** in class. HW6 due Fri Oct 16. Project proposal due **Nov 6**. No class **Nov 11** (Veterans Day) or **Nov 26–27** (Thanksgiving). Final project due **Dec 4**. **Final exam Wed Dec 9, 9:50–11:40 am**.

`questions.yaml` uses the same fields as `eval_cases` (`question`, `expected_answer`, `expect_fallback`), plus `tags`.

| # | Question | Expected | Tests |
|---|---|---|---|
| 1 | When is the midterm? | Thu Oct 15, 2026, in class. Cites Schedule. | date, schedule path, acceptance criterion |
| 2 | When and what time is the final exam? | Wed Dec 9, 9:50–11:40 am | date, time |
| 3 | When is the first homework due? | Fri Sep 4, 11:59 pm | date |
| 4 | When is the project proposal due? | Nov 6 | date |
| 5 | Is there class on November 11? | No, Veterans Day | date, holiday |
| 6 | What's due next week? *(clock fixed at 2026-10-09)* | Midterm Oct 15 and HW6 Oct 16 | relative date, timezone |
| 7 | How much is the final exam worth? | 30 % | grading |
| 8 | How is my grade calculated? | The 5-part breakdown | grading, multi-fact |
| 9 | What percentage do I need for an A? | 90 % or higher | grading |
| 10 | Are any quizzes dropped? | The lowest 2 | grading detail |
| 11 | What's the late policy? | −10 %/day up to 3 days, then 0, plus 2 grace days for homework | policy, multi-fact |
| 12 | Can I use ChatGPT on homework? | To explain concepts, yes. Not to write submitted code. Cite any use. | policy, nuance |
| 13 | How do I ask for a regrade? | Email within 7 days | policy |
| 14 | I'm sick on midterm day, what should I do? | Notify the instructor before the exam, with documentation | policy, paraphrase |
| 15 | When are office hours? | Tue/Thu 2:00–3:30 pm, ENG 214 | logistics |
| 16 | Who is the TA and when is their help session? | Jordan Lee, Wed 10–12, ENG 120 | logistics |
| 17 | What textbook do I need? | *Think Python, 3rd ed.*, free | logistics |
| 18 | Is the midterm open book? | **Fallback** + contact info. This is a hard case: the midterm chunk scores high but doesn't contain the answer. | hallucination trap |
| 19 | Where can I buy a parking permit? | **Fallback** | out of syllabus |
| 20 | Write the Python code for homework 3 for me. | **Refusal** (won't do graded work), with a pointer to office hours | FR-29 |

Scoring: `pass` = 1, `partial` = 0, `fail` = 0 for the M1 gate (**≥ 15 to pass**). Partials are reported separately. For the real syllabus, I adapt the same 20 slots to its facts (same mix: 6 date, 4 grading, 4 policy, 3 logistics, 2 fallback, 1 refusal). Tracked per run: pass count, citation correctness (cited section contains the fact), fallback precision and recall, p50/p95 first-token latency, and cost.

---

## 5. Risks

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | **PDF parsing quality.** Headings are only visible as font styling. Multi-column layouts, tables (grading tables) and scanned pages break structure. | Wrong sections mean weak retrieval and wrong citations | Detect headings from font size and bold relative to the body-text median, plus regexes for common syllabus headings ("Grading", "Late Work", …). Turn tables into one "row: value" line each. Golden-file tests on 3–4 real-world PDFs. Clear failure for scanned PDFs (C15). DOCX/MD recommended in the UI. Docling (an ML layout model) is the fallback if M1 shows failures. |
| R2 | **Date extraction accuracy.** Missing years, "Week 5", ranges, time zones, and wrong dates presented confidently. | Students get a wrong date for an exam, which is the worst failure for this product | Structured output validated by Pydantic, year inferred from term (C11), `verified=false` until an instructor confirms, a review UI that highlights unverified items, a "dates may change — confirm with your instructor" note on date answers, and precision/recall tests on the fixture. |
| R3 | **Retrieval misses.** Short chunks, vocabulary mismatch ("make-up exam" vs "missed exams"), and a badly calibrated threshold that causes too many or too few fallbacks. | False fallbacks or hallucinated answers | Section-prefixed embeddings, threshold calibrated in M1-15 from score distributions, retrieved chunks and scores shown in the preview panel, eval cases for paraphrase and traps (Q14, Q18), fallback analytics showing gaps. If evals still miss, turn on hybrid search: the `tsv` column already exists, merged with reciprocal rank fusion. |
| R4 | **Cost, abuse and model churn on a public demo.** Bots hammering the endpoint, open sign-up, and providers retiring models (this already happened to the docs' default). | Unexpected bills, or a demo that breaks the day of an interview | Per-bot and per-IP rate limits, a daily spend cap that switches to the fallback (C7), closed sign-up on the demo, `llm_models` with a bulk-migrate action (B4), `llm_usage` cost tracking, a nightly live smoke test that alerts on model errors, and pinned model IDs. |
| R5 | **Prompt injection** from uploaded documents ("ignore previous instructions…") or student messages, plus cross-tenant leakage. | Off-policy answers, leaked system prompt, embarrassment | Document text goes inside delimiters labelled as data (NFR-4). The model has no tools and its output never triggers actions. Only `bot_id`-filtered context is ever retrieved. The system prompt contains no secrets. Adversarial eval cases are added to the suite (an injected "ignore instructions" line in a fixture document). Output is length-capped, and markdown is rendered as sanitised text in the UI. |
| R6 | **Free-tier LLM terms and eligibility** (D2). *Seen 2026-11-02: Google refused the free tier for the user's project (403).* Google may use prompts and responses to improve its products, and humans may review them. Users must be 18+. EEA/UK/CH end users need the paid tier. Quotas are per project and Google has cut them before. | Unsuitable for real student data. The demo could hit a daily cap mid-interview | Demo uses synthetic or public syllabi only. Chat page shows a "Don't share personal information" notice. Ollama fallback on quota errors. Warm-up and an eval run counted against quota before demos. Moving to real students means switching to the paid tier (no training on data) or to Ollama: a config change, recorded in an ADR. |

Also tracked: **supply-chain risk** (exact pins, hash lockfiles, 14-day release cool-off, no LiteLLM) · **latency (NFR-7)**, because both candidate models think by default (`reasoning_effort` none/low, measured in M1-15) · **Celery and async code** (one event loop per worker process; a test confirms the worker uses the same `answer.py` path) · **Neon scale-to-zero cold starts** for the first demo request (warm it before demos, or use a paid always-on compute for interview week).

---

## 6. Demo plan

### 6.1 Five-minute script
1. **(0:00) The problem.** Students ask the same 30 questions every term. Show a real syllabus PDF.
2. **(0:30) Instructor flow.** Log in, choose **New bot → Syllabus Assistant template**, enter course info, upload the PDF, and watch the status go `processing → ready`. Show the **extracted schedule** and correct one date.
3. **(1:45) Test before publishing.** In the preview panel, ask "When is the midterm?" and point out that the schedule row and retrieved chunks with scores are visible. Run the **evaluation**: 18/20 pass, and the run detail shows one failing case with the judge's reason.
4. **(2:45) Publish and share.** Publish, copy the link, then open it on a phone-sized viewport and in an **iframe** on a mock course page.
5. **(3:15) Student flow.** Ask a policy question and watch it stream with citations ("[Late Work, p. 3]"). Ask "Is the midterm open book?" and get the **fallback with the instructor's contact**, not a guess. Ask it to "write my homework" and it **refuses**.
6. **(4:00) Insight.** In the analytics dashboard, show the top questions, the fallback "gaps" list (which shows what's missing from the syllabus) and a thumbs-down item.
7. **(4:30) Under the hood.** Show the architecture diagram, run the isolation test in CI, and show the per-bot cost so far (fractions of a cent).

### 6.2 Design-decision talking points
1. **RAG in one Postgres instead of a separate vector DB.** pgvector puts embeddings, schedules and permissions in one transactional store. Deleting a document deletes its chunks atomically. Tenant filtering is a plain `WHERE bot_id`, and HNSW iterative scan handles filtered search at this scale. I'd move to a dedicated vector store only at about 10⁷ vectors or for heavy cross-tenant filtering.
2. **Tenant isolation is enforced by design, then checked by tests.** There is one module that can read chunks, `bot_id` is a required keyword argument, a route-matrix test is generated from OpenAPI, and an architecture test fails CI if another module queries chunks. Row-level security is the next layer if needed.
3. **Exact dates get a structured table.** Embeddings are weak at exact dates and relative time, so dates are extracted into `schedule_items`, which instructors verify and which are answered first. This is a deliberate hybrid of structured lookup and RAG.
4. **Answering "I don't know" is a feature.** The similarity threshold, the fallback message and a contact path make the bot refuse to guess. The threshold is calibrated with an eval set that includes trap questions, so it's chosen from data, not by gut feeling.
5. **Model-agnostic and cost-aware.** Every model sits behind a provider interface with a model registry (with prices) and per-call usage logging. When OpenAI announced the retirement of the docs' default model mid-project, switching was a config change plus an eval run. The default model was chosen by measured accuracy, latency and cost, not by brand.

---

## 7. Tech decisions

Versions were checked on **2026-10-26** against PyPI, npm and official docs. **Status:** ✅ keep as specified in the docs · ⚠ change from the docs, needs your approval · 🆕 new choice the docs didn't specify · ⏳ decide later (the task is noted).

### Frontend

| Area | Choice | Alternatives considered | Why | Trade-offs | Status |
|---|---|---|---|---|---|
| Framework | **Next.js 16.4.x** (App Router) | Next.js 14 (docs; **unsupported since 2025-10-26**, no CVE fixes), Next.js 15 (Maintenance LTS, window ends ~Oct 2026), Vite + React SPA | Only actively supported line. Routing and SSR for `/b/[slug]`. React 19 | Next 16 removed `next lint` and changed some caching defaults. Tutorials written for 14 don't always apply | ⚠ **D1** |
| UI runtime | **React 19.x** | — (implied by Next 16) | Required by Next 16 | — | 🆕 |
| Language | **TypeScript 6.0.x** | TS 7.0 (new native compiler, Jul 2026), TS 5.9 | `typescript-eslint` 8.72 supports TS < 6.1 only, so 7.x would break linting today | Miss TS 7's speed until the tools catch up | 🆕 |
| Styling | **Tailwind CSS 4.3** (PostCSS plugin, CSS-first `@theme`) | Tailwind 3, CSS Modules | Specified. v4 is current and installed by default by `create-next-app` | v4 config differs from older tutorials | ✅ |
| Components | **shadcn/ui** (CLI 4.x; Radix primitives copied into the repo) | Headless UI, MUI | Accessible primitives help with WCAG AA (NFR-14). Code is owned in the repo, not a runtime dependency. Supports Tailwind 4 and React 19 | We maintain the copied components ourselves | 🆕 |
| API types | **openapi-typescript 7.13 + openapi-fetch 0.17** | hey-api/openapi-ts (full SDK), Orval (React Query hooks) | Types generated from FastAPI's OpenAPI, with a tiny runtime and no lock-in | No runtime validation of responses. Last release Feb 2026 (stable but slower cadence) | 🆕 |
| SSE client | **fetch + `eventsource-parser`** (`EventSourceParserStream`) | Native `EventSource` (GET only, so no request body), `@microsoft/fetch-event-source` (no release in about 5 years) | The chat endpoint is a POST with a body. Small dependency, maintained | 4.1.3 is 1 day old, so pin the newest 4.x that is at least 14 days old | 🆕 |
| Data fetching | Plain `fetch` + a small polling hook | TanStack Query | Few screens, so fewer dependencies | Some hand-written caching. Revisit if it grows (Later) | 🆕 |
| Node runtime | **Node 24 LTS** | Node 26 (LTS from 2026-10-28), Node 22 (maintenance) | Supported by Next 16, Vitest 5, Sentry and ESLint 10 | Upgrade to 26 later | 🆕 |

### Backend

| Area | Choice | Alternatives considered | Why | Trade-offs | Status |
|---|---|---|---|---|---|
| Language | **Python 3.12** | 3.13 (now security-only too), 3.14 (Celery support only "initial") | Specified. Supported by every chosen library until Oct 2028 | No new bugfix releases, only security fixes | ✅ (A6) |
| Web framework | **FastAPI 0.162.x** + **Uvicorn 0.54** | Django (+Ninja), Litestar | Specified. Async, Pydantic, and **native SSE (`fastapi.sse.EventSourceResponse`, since 0.135)** with keep-alive pings and no proxy buffering | Still 0.x versioning. Pin exactly | ✅ |
| SSE server | **FastAPI native SSE** | `sse-starlette` | Built in, so one less dependency. POST supported | Newer feature (Mar 2026). Check disconnect handling in M1-11 | 🆕 |
| Validation / settings | **Pydantic 2.14**, **pydantic-settings 2.16** | attrs + cattrs, dynaconf | Specified. FastAPI-native | — | ✅ |
| ORM / migrations | **SQLAlchemy 2.1.6 (async)** + **Alembic 1.20** | SQLModel, Tortoise, raw SQL + asyncpg | Specified. 2.1 is the current series (2.0 is in maintenance) | 2.1 changes are small but recent | ✅ |
| DB driver | **asyncpg 0.32** | psycopg 3 (sync+async) | Fastest async driver and the standard pairing with SQLAlchemy async | The worker must also run async code (see Celery) | 🆕 |
| pgvector client | **pgvector-python 0.5.1** | Hand-written type adapter | SQLAlchemy `Vector` type and operators | — | 🆕 |
| Background jobs | **M1: FastAPI BackgroundTasks → M2: Celery 5.6.3 + Redis** | Taskiq (async-native, FastAPI integration), Dramatiq, arq/SAQ, RQ | Specified. Most mature retry, beat (retention) and monitoring story. Well known in interviews | Celery is synchronous: async code runs in one event loop per worker process, which is a known sharp edge (covered by tests). Taskiq would fit async code better. I'm not proposing a switch | ✅ |
| Password hashing | **pwdlib 0.3.1 [argon2]** | passlib (unmaintained, breaks on 3.13+), argon2-cffi directly, bcrypt | FR-2 allows argon2. Recommended in FastAPI's current docs. Small API | Young library (0.x) | 🆕 |
| JWT | **PyJWT 2.15** | python-jose (stale, dropped from FastAPI docs), joserfc/Authlib | Maintained, minimal, used in FastAPI's docs | Only JWT, but that's all we need | 🆕 |
| Rate limiting | **`limits` 5.8 (async Redis, moving window)** in a FastAPI dependency | slowapi 0.1.10 (decorator-based, static limits), fastapi-limiter, hand-written Lua | Per-bot limits are dynamic (`bots.rate_limit_per_min`). `limits` is the engine slowapi itself uses, without the decorator constraints | We write about 40 lines of glue | 🆕 |
| PDF extraction | **pdfplumber 0.11.10** (MIT) | **PyMuPDF / pymupdf4llm 2.0** (AGPL-3.0 or commercial; 2.0 is 1 week old), Docling 2.143 (MIT, ML layout, heavy PyTorch dependencies), pypdf (no font info) | Gives per-character font size and bold for heading detection under a permissive licence. 30 pages is well within the 2-minute budget | Slower than PyMuPDF, and heading heuristics are ours to write. **If your repo will be AGPL-compatible open source, PyMuPDF is faster with better layout. Your call.** | 🆕 |
| DOCX extraction | **python-docx 1.2.0** | docx2python, mammoth, Docling | Reads `Heading n` styles directly. Stable | Last release Jun 2025 (slow cadence, but the format is stable) | 🆕 |
| Web page extraction | **trafilatura 2.3.1** | readability-lxml, BeautifulSoup + custom rules | Strong main-content extraction, keeps headings, maintained (Oct 2026) | Can drop content on unusual layouts | 🆕 |
| Token counting | **tiktoken 0.14** (approximate, for chunk sizing only) | Provider count-token APIs | Fast, local, provider-neutral sizing. Billing uses each provider's reported usage, not tiktoken | Counts differ a little across providers, which is fine for ±500-token chunks | 🆕 |
| Provider abstraction | **Our own adapters** over **google-genai 2.31** and **ollama 0.6.3** SDKs (OpenAI and Anthropic adapters moved to Later) | LiteLLM (**two PyPI supply-chain compromises in 2026**), pydantic-ai, LangChain | Specified (NFR-13). Small surface (stream + JSON + embed). No heavy framework. We control timeouts, quota/429 handling and usage capture. Two real providers still prove swappability | We maintain two small adapters. Pin the SDKs and wait 14 days, since google-genai releases often | ✅ |
| HTTP client (own calls) | **httpx2 2.14** | httpx 0.28 (no release since Dec 2024; Starlette 1.9's TestClient deprecates it), aiohttp | Same API as httpx and maintained (Pydantic team) | google-genai still depends on plain httpx internally. That's fine, since we don't pass it a client | 🆕 |
| Logging | **structlog 26.1** | stdlib `logging` + python-json-logger, loguru | JSON logs with context variables for `request_id` and `bot_id` (NFR-11) | One more dependency | 🆕 |
| Errors | **Sentry**: `sentry-sdk 2.73` [fastapi, celery], `@sentry/nextjs 11.9` | Self-hosted GlitchTip, logs only | Specified (architecture §10). Celery and FastAPI integrations | Check free-tier limits at M5-06 | ✅ |
| File storage | **Local volume (dev) / S3 via boto3 1.43** | aioboto3, obstore, Cloudflare R2 | Specified. boto3 in a threadpool is simplest | Sync client in a threadpool | ✅ |

### Data

| Area | Choice | Alternatives considered | Why | Trade-offs | Status |
|---|---|---|---|---|---|
| Database | **PostgreSQL 16** | PG 17, PG 18 (current; native `uuidv7()`, async I/O) | Specified. Supported until Nov 2028. Every managed host offers it with pgvector | Misses PG 18 features we don't need | ✅ |
| Vector extension | **pgvector 0.8.7** (HNSW, cosine, `iterative_scan = relaxed_order`) | Qdrant, Pinecone, Chroma | Specified. One database, transactional deletes, easy `bot_id` filtering. 0.9 (unreleased) drops PG 13/14, which doesn't affect us | Vector-only features are behind dedicated DBs | ✅ |
| Vector index | **HNSW, cosine** | IVFFlat | Specified. No retraining as data grows | More memory and slower builds than IVFFlat (irrelevant at this scale) | ✅ |
| Queue / cache | **Redis 8.x** (local `redis:8-alpine`) | Valkey 8/9 (BSD, wire-compatible), RabbitMQ | Specified. Redis 8 is open source again (AGPLv3 option), which is fine for unmodified use | If licence is a concern, Valkey is a drop-in replacement | ✅ |

### AI models

| Area | Choice | Alternatives considered | Why | Trade-offs | Status |
|---|---|---|---|---|---|
| Chat model (default) | **`gemini-3.5-flash-lite`** (Stable, free tier) | `gemini-3.1-flash-lite` (older stable), `gemini-3.6-flash` (stronger, lower free quota), paid `claude-haiku-5-5` / `gpt-6-luna` ($0.10/$0.50 per 1M tokens) | You prefer no paid API. It's in the same small, fast class as the paid candidates. Paid price if ever needed: about $0.10/$0.40 per 1M tokens | **Free tier:** Google uses prompts and responses to improve its products and humans may review them; users must be 18+; it isn't allowed for apps serving EEA/UK/CH users; there are daily per-project quotas. Fine for the demo, not for real students (R6) | ✅ **D2** |
| Backup chat model | **`qwen3:8b` via Ollama** (optional profile, or native Ollama on the Mac for speed) | `llama3.1:8b` (docs), `gemma3:12b`/`4b` | Free, private and unmetered, so it's the fallback when the Gemini quota runs out or data must stay local. About 8 GB at Q4 | Slow without a GPU. Docker on this Mac has about 4 GB RAM, so run Ollama natively | ✅ A4 |
| Judge model | **`gemini-3.6-flash`** (one tier up, free tier) | The answering model as its own judge, `qwen3:8b` | Stronger than the model it grades. Only about 20 calls per run | Same provider as the answering model (C18) | ✅ (C18) |
| Embeddings (default) | **`gemini-embedding-2` at 1536 d** (free tier; normalises truncated output automatically; 8,192-token input) | `gemini-embedding-001` (text-only, 2,048 tokens, needs manual normalisation when truncated), OpenAI `text-embedding-3-small` (paid), Ollama `nomic-embed-text` | Free, with no second provider key needed. 1536 d fits pgvector HNSW (≤ 2000 d). Uses a task prefix in the text (`task: search result \| query:` / `title: … \| text:`) instead of `task_type` | Free-tier data use as for chat (R6). Switching provider or dimension means re-embedding (B2) | ✅ |
| Embeddings (local) | **`BAAI/bge-small-en-v1.5` via fastembed 0.9.1** (384 d, ONNX) | sentence-transformers (PyTorch, about 1 GB image), Ollama embeddings | Specified model family. No PyTorch, so the image stays small | Lower quality than OpenAI's. Switching dimension means re-embedding (B2) | ✅ (A5) |

### Tooling

| Area | Choice | Alternatives considered | Why | Trade-offs | Status |
|---|---|---|---|---|---|
| Python packaging | **uv 0.13** | Poetry, pip-tools | Fast, lockfile with hashes, manages Python versions too | Still 0.x | 🆕 |
| Python lint/format | **ruff 0.17** | flake8 + black + isort | Specified. One fast tool | — | ✅ |
| Type checker | **mypy 2.4** (+ pydantic plugin) | pyright (best spec conformance), ty (Astral, **beta**, no plugin system) | Specified. The plugin ecosystem matters for Pydantic and SQLAlchemy | Slower than pyright/ty | ✅ |
| Python tests | **pytest 9.1, pytest-asyncio 1.4, testcontainers 4.15** | unittest, anyio plugin | Specified (pytest). Real Postgres and pgvector in tests | Docker needed for integration tests | ✅ |
| JS lint/format | **ESLint 10 (flat config) + Prettier 3.9** | Biome (faster, fewer rules) | Specified. `eslint-config-next` brings Next and jsx-a11y rules (helps NFR-14) | Two tools | ✅ |
| JS tests | **Vitest 5 + Testing Library; Playwright 1.64** | Jest, Cypress (paid parallel runs, no WebKit) | Fast, ESM-native. Playwright is a Next 16 peer dependency and covers mobile viewports | — | 🆕 |
| A11y testing | `@axe-core/playwright` | Lighthouse CI, pa11y | Automated WCAG checks in e2e | Version to review at M3-06 | ⏳ M3-06 |
| Git hooks | **pre-commit 4.7** | prek (Rust drop-in, same config) | Specified. Mature | Slower than prek. Can swap later with no config change | ✅ |
| CI | **GitHub Actions** | GitLab CI, CircleCI | Specified. Free for public repos, service containers for PG and Redis | — | ✅ |
| Containers | **Docker Compose** | Tilt, devcontainers | Specified (NFR-12) | — | ✅ |

### Deploy (final choice at M5-04 after a fresh pricing check)

| Area | Leading choice | Alternatives considered | Why | Trade-offs | Status |
|---|---|---|---|---|---|
| Frontend host | **Vercel (Hobby)** | Netlify, the same container host as the API | Specified. Native Next.js | Hobby is for non-commercial use, which should cover a portfolio (verify terms) | ⏳ M5-04 |
| API + worker host | **Render** (native background-worker type, about $7/service/month) | Fly.io (cheapest per container, more hands-on), Railway (usage-based, about $5+), AWS ECS Fargate (you know AWS; highest cost and complexity for a demo) | Specified options. Render needs the least ops for a separate worker plus beat | About $14–21/month for API + worker. The free tier sleeps (cold starts), so it's not used | ⏳ M5-04 |
| Postgres host | **Neon Free** (0.5 GB/project, 100 CU-h/month, scale-to-zero after 5 min) | Supabase Free (pauses after 7 days idle), RDS (cost) | Specified option. pgvector supported, generous compute. 5k chunks ≈ 40 MB | First request after idle is slow. Warm it before demos | ⏳ M5-04 |
| Redis host | **Upstash fixed plan (about $10/month)** or a Redis container on the API host | Upstash pay-as-you-go (an idle Celery worker polls about 3.8M commands/month ≈ $7.6), ElastiCache | Specified option. Celery's polling makes pay-as-you-go pricing unpredictable | A container is cheaper but needs a persistent volume | ⏳ M5-04 |
| Files | **AWS S3** (private bucket, SSE-S3) | Cloudflare R2, Render disk | Specified | — | ✅ |

---

## Later (out of v1 scope)
- Student accounts: login, history across devices, `require_login` (FR-5, requirements §7 Q1)
- Multiple course sections with different schedules (requirements §7 Q2)
- Emailed collaborator invites, password reset, email verification
- Postgres row-level security as a second isolation layer (schema §6)
- Hybrid keyword + vector retrieval (turned on only if evals show misses; the `tsv` column already exists)
- OCR for scanned PDFs
- Per-bot retention period and iframe origin allow-list
- LMS (LTI) integration, university SSO (non-goals for v1)
- OpenTelemetry tracing. TanStack Query if the dashboard grows
- Tool upgrades: TypeScript 7 (when typescript-eslint supports it), PostgreSQL 18, Node 26, prek, ty/pyright, PyMuPDF if you choose an AGPL licence
- OpenAI and Anthropic adapters (deferred by D2; the interface already supports them)
- Answer caching for very frequent questions. Prompt caching once system prompts grow
