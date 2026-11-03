# Planning Prompt — Syllabot Platform

Paste this into an AI coding assistant (Claude Code, Cursor, etc.) with `requirements.md`, `architecture.md` and `database-schema.md` in the repo.

---

You are a senior full-stack engineer and tech lead. Help me plan the build of **Syllabot Platform**, a multi-instructor web app where instructors turn a course syllabus into a RAG chatbot that students can use through a share link.

## Context
Read these files first and treat them as the source of truth:
- `requirements.md` — functional and non-functional requirements, milestones M1–M5
- `architecture.md` — components, flows, API surface, technology choices
- `database-schema.md` — PostgreSQL + pgvector schema

Stack: FastAPI (Python 3.12, async SQLAlchemy 2, Alembic, Pydantic v2), Celery + Redis, PostgreSQL 16 + pgvector, Next.js 14 + TypeScript + Tailwind, Docker Compose. LLM and embedding providers sit behind an adapter interface (OpenAI, Anthropic, Ollama).

About me: I'm a software engineer comfortable with FastAPI, pgvector, RAG, React/Next.js, AWS and Docker. I'm building this alone, about 10–12 hours a week, as a portfolio project I will demo and explain in interviews.

## What I want from you
Do **not** write application code yet. Produce a plan:

1. **Gaps and conflicts.** List anything in the three docs that is unclear, contradictory, or missing. Propose a decision for each, and mark which ones you need me to confirm.
2. **Milestone breakdown.** For each milestone M1–M5, list concrete tasks (each 2–6 hours), in order, with dependencies. Each task needs:
   - a short title
   - files/modules it touches
   - acceptance check (how I know it's done)
3. **Repo setup.** The exact folder structure, tooling (ruff, mypy, pytest, eslint, prettier, pre-commit), `.env.example` variables, and the `docker-compose.yml` services.
4. **Test strategy.** Unit, integration and end-to-end tests per milestone. Include the tenant-isolation test and a RAG evaluation set of 20 questions against a sample syllabus.
5. **Risks.** Top 5 technical risks (e.g. PDF parsing quality, date extraction accuracy, retrieval misses, cost, prompt injection) with a mitigation for each.
6. **Demo plan.** What the final demo shows in 5 minutes, and 5 design-decision talking points for interviews.
7. **Tech decisions.** A table reviewing every technology and tool in the stack, following the rule below.

## Rule for choosing any technology or tool
Before choosing, adding or changing any technology, library, tool, model or service (including ones already named in the docs), review it first. Do not pick something just because it's popular or the first thing that comes to mind. For each choice:
1. **Check it's current.** Look up the latest stable version, whether it's actively maintained, and any recent breaking changes or deprecations. Don't rely on memory for versions or APIs.
2. **Compare at least 2 alternatives** against this project's needs: fit for the use case, complexity, cost, performance at our scale, learning curve, and community/docs.
3. **Check compatibility** with the rest of the stack (Python 3.12, FastAPI, async SQLAlchemy, pgvector, Next.js 14).
4. **Write down the decision** in a "Tech decisions" table in PLAN.md: what was chosen, alternatives considered, why, and trade-offs.
5. **Ask me before switching** away from anything specified in the docs, and explain why the change is better.

## Constraints
- Keep v1 scope to what `requirements.md` lists. Put any extra ideas in a separate "Later" list.
- Prefer simple solutions first (e.g. FastAPI BackgroundTasks in M1, Celery from M2).
- Every retrieval path must filter by `bot_id`.
- Default to a small, cheap model; keep the provider swappable.

## Output format
Write the plan to `PLAN.md` using headings for each of the 7 sections above and checkbox task lists (`- [ ]`) for milestone tasks. Then stop and wait for my review before starting M1.
