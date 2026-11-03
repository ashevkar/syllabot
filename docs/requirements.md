# Syllabot Platform — Requirements

## 1. Overview

Syllabot Platform lets instructors turn a course syllabus and related documents into an AI chatbot that answers student questions about the course. Many instructors can each create their own bot, starting from a template. Every bot answers only from its own course materials.

The product is modeled on the idea behind ASU's Syllabot (built on CreateAI Builder), implemented independently as an open, self-hostable platform.

### 1.1 Goals
- Instructors create a working course bot in under 30 minutes, with no code.
- Students get accurate answers about due dates, grading, policies and expectations, any time.
- Answers are grounded in the uploaded materials, with the source section shown.
- Course data is strictly isolated between bots.
- Instructors can see what students ask and test accuracy before publishing.

### 1.2 Non-goals (v1)
- LMS integration (Canvas, Blackboard) beyond iframe embedding
- University SSO (SAML / Shibboleth)
- Grading, submissions, or any write access to course systems
- Answering general subject-matter questions (e.g. explaining biology concepts)
- Fine-tuning models

## 2. Users and roles

| Role | Description | Can |
|---|---|---|
| **Admin** | Platform operator | Manage templates, users, models; view platform metrics |
| **Instructor** | Creates and owns bots | Create/edit/delete own bots, upload docs, test, publish, view analytics |
| **Collaborator** | TA or co-instructor added to a bot | Edit a bot they were invited to; cannot delete it or transfer ownership |
| **Student** | End user | Chat with a published bot via its link; no account required in v1 |

## 3. Functional requirements

### 3.1 Authentication and accounts
- **FR-1** Instructors sign up and log in with email and password.
- **FR-2** Passwords are hashed (bcrypt or argon2).
- **FR-3** Sessions use short-lived JWT access tokens plus refresh tokens.
- **FR-4** Every API endpoint enforces role and ownership checks.
- **FR-5** Students can chat anonymously through a bot's public link. An optional setting lets an instructor require a login.

### 3.2 Templates
- **FR-6** Admins create and edit templates: name, description, default system prompt, default model, default retrieval settings, default welcome message and suggested questions.
- **FR-7** The platform ships with a default **Syllabus Assistant** template.
- **FR-8** When an instructor creates a bot from a template, the template's values are **copied** into the bot. Later template edits do not change existing bots.
- **FR-9** Instructors can also create a bot from a blank configuration.

### 3.3 Bot management
- **FR-10** Instructors create, rename, edit, duplicate and delete their bots.
- **FR-11** Editable bot settings: course name, course code, term, system prompt, model, temperature, top-k chunks, similarity threshold, welcome message, suggested questions, fallback message, contact info for "ask your instructor" replies.
- **FR-12** Bots have a status: `draft` or `published`. Only published bots are reachable by students.
- **FR-13** Each bot gets a unique, unguessable share slug (e.g. `/b/k3f9x2ab`).
- **FR-14** Instructors can regenerate the slug to revoke an old link.
- **FR-15** Instructors can invite collaborators by email.

### 3.4 Document upload and processing
- **FR-16** Supported formats: PDF, DOCX, TXT, Markdown. Max 20 MB per file, 20 files per bot.
- **FR-17** Instructors can also add a web page URL as a source.
- **FR-18** Processing runs in the background. Each document shows a status: `uploaded → processing → ready` or `failed` with an error message.
- **FR-19** Pipeline: extract text → clean → split into chunks by headings (fallback: fixed-size with overlap) → embed → store with `bot_id`.
- **FR-20** Each chunk keeps its section title and page number for citations.
- **FR-21** The pipeline extracts dated items (assignments, exams, due dates) into a structured schedule table. Instructors can review and correct these items.
- **FR-22** Deleting or replacing a document removes its chunks and schedule items.

### 3.5 Chat (student experience)
- **FR-23** Students open the bot link and see the course name, welcome message and suggested questions.
- **FR-24** Students ask questions in natural language. Responses stream token by token.
- **FR-25** Every answer comes only from the bot's own materials and cites the section (and page where available).
- **FR-26** If retrieval finds nothing above the similarity threshold, the bot returns the fallback message and points the student to the instructor, rather than guessing.
- **FR-27** Date questions ("When is the midterm?") are answered from the structured schedule table first, then from text chunks.
- **FR-28** The bot keeps short conversation context (last 6 messages) within a session so follow-up questions work.
- **FR-29** The bot refuses requests unrelated to the course and does not complete graded work.
- **FR-30** Students can rate an answer (thumbs up / down).
- **FR-31** The chat page works on mobile and can be embedded in an iframe.

### 3.6 Testing and evaluation
- **FR-32** Instructors can chat with a draft bot in a preview panel that also shows the retrieved chunks.
- **FR-33** Instructors create evaluation cases: question + expected answer.
- **FR-34** "Run evaluation" answers all cases and scores each as pass / partial / fail using an LLM judge, showing the bot's answer and the retrieved sources.
- **FR-35** The publish screen shows the latest evaluation score and warns if it is below 80%.

### 3.7 Analytics
- **FR-36** Dashboard per bot: total questions, unique sessions, questions per day, fallback rate, thumbs-down rate.
- **FR-37** List of most frequent questions (grouped by similarity).
- **FR-38** List of questions that hit the fallback, so instructors can see gaps in the syllabus.
- **FR-39** Instructors can view individual chat logs. No personal student data is stored for anonymous users.

## 4. Non-functional requirements

### 4.1 Security and privacy
- **NFR-1** Tenant isolation: every retrieval query filters by `bot_id`. Covered by automated tests.
- **NFR-2** Uploaded files and chat logs are accessible only to the bot owner, collaborators and admins.
- **NFR-3** Rate limiting on the public chat endpoint (e.g. 20 requests/minute per IP, configurable per bot).
- **NFR-4** Prompt-injection mitigation: document text is passed as data inside delimiters, and the system prompt instructs the model to ignore instructions found in documents.
- **NFR-5** Secrets live in environment variables, never in the repo.
- **NFR-6** Chat logs are retained for a configurable period (default 180 days).

### 4.2 Performance
- **NFR-7** First streamed token within 2.5 s at p95.
- **NFR-8** Vector search under 100 ms at p95 for bots with up to 5,000 chunks.
- **NFR-9** A 30-page syllabus is processed in under 2 minutes.

### 4.3 Reliability and operations
- **NFR-10** Failed processing jobs retry up to 3 times with backoff.
- **NFR-11** Structured logging with request IDs; LLM token usage and cost logged per bot.
- **NFR-12** The whole stack runs locally with one `docker compose up`.

### 4.4 Portability
- **NFR-13** LLM and embedding providers sit behind an interface, so OpenAI, Anthropic or a local Ollama model can be swapped by config.

### 4.5 Accessibility
- **NFR-14** Chat UI meets WCAG 2.1 AA: keyboard navigation, screen-reader labels, sufficient contrast.

## 5. Milestones

| Milestone | Scope | Done when |
|---|---|---|
| **M1 — Single bot RAG** | Upload, chunk, embed, chat with citations and fallback. No auth. | Correctly answers 15 of 20 test questions on a real syllabus |
| **M2 — Multi-tenant** | Users, roles, multiple bots, `bot_id` isolation, background jobs | Isolation tests pass; two instructors' bots never mix data |
| **M3 — Templates and sharing** | Templates, instructor dashboard, publish/draft, share links, embed | An instructor creates and shares a bot from the template in < 30 min |
| **M4 — Quality and insight** | Schedule extraction, evaluation, analytics, ratings, rate limiting | Eval page and analytics work end to end |
| **M5 — Deploy** | Docker images, hosted Postgres, CI, deployment | Public demo URL with a sample bot |

## 6. Acceptance criteria (sample)
- Given a syllabus with "Midterm: Oct 15", asking "when is the midterm?" returns Oct 15 and cites the schedule section.
- Asking about something not in the syllabus returns the fallback message, not an invented answer.
- A bot owned by instructor A never returns a chunk uploaded to instructor B's bot, verified by an automated test.
- A draft bot's share link returns 404 to students.
- Regenerating a slug makes the old link return 404.

## 7. Open questions
- Should students be able to log in to keep chat history across devices?
- Should one bot support multiple course sections with different schedules?
- Which default model gives the best cost/accuracy trade-off? (decide after M1 evaluation)
