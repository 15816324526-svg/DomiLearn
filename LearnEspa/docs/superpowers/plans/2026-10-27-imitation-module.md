# Textbook Imitation and Model Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved 1.0 textbook imitation loop, from DeepSeek configuration through an auditable report, for every confirmed passage in all 16 lessons.

**Architecture:** Keep original textbook records immutable. Add derived sentence records and SQLite-backed imitation rounds, attempts, memory, and reports. A local DeepSeek client provides structured AI operations; deterministic backend code owns state transitions and evidence calculations. The Vue UI consumes the API and persists the draft before model calls.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, SQLite, httpx, Windows DPAPI, Vue 3, TypeScript, Vite, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-27-imitation-module-design.md`

## Global Constraints

- User explicitly authorized coding after design approval. Implement directly after planning.
- No real paid calls without a configured user Key; tests use an injected fake model client.
- Never put API Keys in browser persistence, logs, or normal API responses.
- Keep source PDF, Docling artifacts, and original passage rows intact.
- Release coverage is all 16 lessons; implement first-lesson behavior first, then run the full-book coverage process in the companion plan.
- No Git repository exists here; inspect changed files and run tests instead of committing.

## Task 1: Model service storage and connection probe

**Files:** `backend/app/services/model_settings.py`, `backend/app/services/deepseek_client.py`, `backend/app/api/model_settings.py`, `backend/app/schemas/model_settings.py`, `backend/pyproject.toml`, backend tests.

- [ ] Add a local credential store using Windows DPAPI for the Key and atomic replacement of configuration after a successful probe.
- [ ] Validate official DeepSeek HTTPS origin locally before sending a Key. Accept configurable Model ID; reject relays in 1.0.
- [ ] `GET /api/model-settings` returns `model_id`, `url`, `has_api_key` only.
- [ ] `POST /api/model-settings/test` accepts `model_id`, `url`, `api_key`; performs a small real structured-output probe. Return success only after secure persistence; failures leave active credentials unchanged.
- [ ] Translate upstream HTTP status and network/timeout errors to clear stable API errors without leaking the Key.
- [ ] Provide an injectable structured-generation method and record returned token usage by purpose when available.
- [ ] Test official URL validation, 401/429/timeouts, no-secret responses, and rollback on probe or storage failure.

## Task 2: Sentence preparation and state schema

**Files:** `backend/migrations/versions/0004_imitation.py`, `backend/migrations/versions/0005_sentence_patterns.py`, `backend/app/models/imitation.py`, `backend/app/services/sentence_preparation.py`, backend tests.

- [ ] Create immutable passage sentence records linked to passage, lesson and conversion version, with ordinal, speaker, derived Spanish text, source position, core pattern and fixed collocations.
- [ ] Build a deterministic source splitter with dialogue-turn preservation, punctuation and abbreviation safeguards, and explicit preparation diagnostics. Do not silently declare uncertain OCR or structure ready.
- [ ] Create imitation round, planned sentence, answer attempt, call usage, memory summary and report records. Store the entire approved plan before showing the first prompt.
- [ ] Apply migrations to fresh and existing database fixtures; do not delete vocabulary history.
- [ ] Test dialogue and mixed narrative/dialogue examples plus idempotent sentence preparation.

## Task 3: Start or resume a round

**Files:** `backend/app/services/imitation.py`, `backend/app/services/imitation_agents.py`, `backend/app/api/imitation.py`, `backend/app/schemas/imitation.py`, backend tests.

- [ ] Expose `GET /api/imitation/passages` grouped by lesson with preparation/readiness status, `POST /api/imitation/passages/{passage_id}/rounds` to start or resume, and `GET /api/imitation/rounds/{round_id}`.
- [ ] Retrieve review words and prior imitation evidence. Let a model-backed memory step interpret the records without inventing them.
- [ ] Ask the planning model for a sentence mapping, then a coherent full Chinese passage with a short background and optional contextual hints. Preserve dialogue/narrative form and core patterns; review words are context, never mandatory scoring targets.
- [ ] Programmatically audit every mapping, order, empty value and source pattern; use a separate model audit for semantic quality. At most one repair and re-audit; failure creates no active round.
- [ ] Persist a fixed approved plan and initial cursor; reopening an unfinished passage resumes it. Test resume, rejected plans, one-repair cap and previous round preservation.

## Task 4: Sentence feedback, progress and evidence

**Files:** same imitation backend service/API/schema and tests.

- [ ] Add idempotent `POST /api/imitation/rounds/{round_id}/answers` with `request_id`, answer and display mode/hint state. Commit the raw attempt and draft before invoking the model.
- [ ] Validate structured feedback for meaning, grammar and core-pattern use. Accept a correct alternative with an optional rewrite; reserve rejection for substantive errors.
- [ ] Preserve a pending attempt on model failure so retry with the same request ID can complete it; failures do not count toward the three rejected verdicts.
- [ ] `POST /api/imitation/rounds/{round_id}/next` advances only after a passing answer or manual pass. Manual pass is available after three actual rejected verdicts and yields neutral memory evidence.
- [ ] Save display mode, hint use, all attempts, feedback and transitions. Calculate per-pattern round evidence (1, 0.5, 0, unobserved), recent-three weighted value and the two-round familiar label from actual records.
- [ ] Test refresh/resume, idempotent retry, network failure, optional rewrite, three rejects, manual pass and evidence calculations.

## Task 5: Completion, memory and reports

**Files:** imitation backend services/API/schema and tests.

- [ ] Mark the round complete immediately when all source sentences have been advanced; subsequent AI work cannot undo completion.
- [ ] Run model-backed post-round memory reflection and a separate report explanation against deterministic counts and verified record IDs. Keep derived records retryable if model calls fail.
- [ ] Expose `GET /api/imitation/passages/{passage_id}/history`, `GET /api/imitation/rounds/{round_id}/report`, and retry endpoint for a failed derived report.
- [ ] Include answer-level history, first-pass/revised/alternative/manual counts, used/unobserved patterns, evidenced issues, comparisons and next suggestions. No fabricated mastery percentage.
- [ ] Test reports against attempts and exact citations, and confirm old round data survives a new round.

## Task 6: Vue user journey

**Files:** `frontend/src/views/Dashboard.vue`, `frontend/src/views/imitation/*.vue`, `frontend/src/api/*.ts`, `frontend/src/stores/*.ts`, `frontend/src/types/*.ts`, `frontend/src/router/*`, frontend tests.

- [ ] Add a scrollable “设置模型服务” section with three editable fields, real test button, success state, and switch-service draft reset while old active configuration remains effective.
- [ ] Display all HTTP/model failures in closable alerts with a visible ×; never auto-dismiss them. Surface status codes when one exists.
- [ ] Replace mock imitation and report data with API calls. Show all ready passages by lesson, resume existing round, short background and only current Chinese sentence.
- [ ] Render source Spanish with full/key-pattern-masked/hidden modes and a persisted default; track mode and optional hint with each submission.
- [ ] Save draft to backend before judging. Show specific feedback, rewrite/next, manual pass after three model rejects, progress and historical attempts.
- [ ] Report all past rounds by passage with expandable answers and “again” action; no false independent-mastery claim when full source was visible.
- [ ] Run TypeScript build and focused UI tests.

## Task 7: Integration and full-book release check

- [ ] Wire the three backend routers into `create_app` and keep fake clients injectable for tests.
- [ ] Complete the companion full-book extraction plan and run sentence preparation for every confirmed passage.
- [ ] Verify API flows with first lesson real data and fake model: create, reject, correct, advance, complete, report, repeat.
- [ ] Verify all 16 lessons have passages, vocabulary, prepared sentences and no unreviewed blocking diagnostics; spot-check difficult lessons 7, 12, 14, 15 and 16.
- [ ] Run backend pytest and frontend build; record remaining extraction or OCR issues explicitly instead of hiding a partial release.
