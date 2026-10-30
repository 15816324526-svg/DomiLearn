# First Lesson Vocabulary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the first lesson's two vocabulary phases playable, resumable and backed by the confirmed textbook data.

**Architecture:** FastAPI owns the learning session and grades every answer in a SQLite transaction. Vue displays the server's current question and feedback, then explicitly advances on “下一题”; the store keeps only a cached copy of server state.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, SQLite, pytest, Vue 3, Pinia, TypeScript, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-26-first-lesson-vocabulary-design.md`

## Global Constraints

- `modern-spanish-1`, first lesson only; read the current confirmed conversion version.
- Two ordered phases: meaning choice, then Chinese to Spanish spelling; every word must pass both.
- No LLM, remote speech, or imitation integration in this round; hide the inactive speaker button.
- Every answer persists before feedback is returned; advancing requires a separate click.
- Preserve old confirmed versions and their learning records. No Git commits: this workspace has no Git repository.

## Review Focus

- Closing the page after answering but before “下一题” restores feedback without scoring twice.
- Four choices contain one correct meaning even when several Spanish words share a translation.
- A missed word returns only after the other words of that pass, and one mistake permanently marks it for review.
- `alumno, na` accepts both full forms; accent-only differences pass while `ñ` remains distinct.
- A newly confirmed textbook version starts a separate session and does not display the old version's words.

---

### Task 1: Persistent session and grading

**Files:**
- Create: `backend/app/models/vocabulary_session.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0003_vocabulary_session.py`
- Create: `backend/app/services/vocabulary_study.py`
- Test: `backend/tests/services/test_vocabulary_study.py`

**Interfaces:** `VocabularyStudyService(session_factory)` provides `get_or_start() -> StudyState`, `submit(session_id, question_id, answer, request_id) -> StudyState`, and `advance(session_id) -> StudyState`. `StudyState` includes version, stage, progress, current question, pending feedback and summary. The service selects only the current confirmed version's first lesson; `request_id` makes retries safe.

- [ ] Write tests for stage transitions, delayed wrong-word return, duplicate submissions, resume with pending feedback, version isolation and the review pool; run and observe failure.
- [ ] Add session/attempt models and migration; implement transactional queue and grading; run the service tests.
- [ ] Add focused spelling tests for accents, case, `ñ`, gender variants and shared-meaning initial hints.

### Task 2: Study API

**Files:**
- Create: `backend/app/schemas/vocabulary_study.py`
- Create: `backend/app/api/vocabulary_study.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_vocabulary_api.py`

**Interfaces:** `GET /api/vocabulary/lesson/1` returns overview and active session state; `POST /api/vocabulary/lesson/1/answers` accepts question ID, response and request ID; `POST /api/vocabulary/lesson/1/next` advances after feedback. All return the existing `{code,message,data}` envelope. The spelling answer is validated on the server; correct answer is omitted until feedback.

- [ ] Add API tests for start/resume, answer, next, no confirmed version, wrong-stage calls and duplicate request IDs; run and observe failure.
- [ ] Implement schema, routes and service dependency; run API and service tests.

### Task 3: Connect the four vocabulary pages

**Files:**
- Modify: `frontend/src/api/index.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/stores/vocabulary.ts`
- Modify: `frontend/src/views/vocabulary/Lesson.vue`
- Modify: `frontend/src/views/vocabulary/Choice.vue`
- Modify: `frontend/src/views/vocabulary/Dictation.vue`
- Modify: `frontend/src/views/vocabulary/Summary.vue`
- Modify: `frontend/src/utils/text.ts` if the legacy browser-side scorer remains in use elsewhere.
- Test: `frontend/src/stores/vocabulary.spec.ts`

**Interfaces:** New vocabulary API calls always reach the backend regardless of `USE_MOCK`; imitation mock calls stay as they are. `useVocabularyStore` exposes `load`, `submit`, `next`, and the server-supplied state. Routes redirect to the server's actual stage on refresh or direct navigation.

- [ ] Add focused store tests for submit, pending feedback, explicit next, refresh resume and API failure; run and observe failure.
- [ ] Replace demo vocabulary data and timers with server state; show feedback and “下一题”, hide speaker button, and show loading/error/empty states.
- [ ] Make the summary display both phases' saved review entries and remove misleading demo imitation actions; run frontend tests and typecheck.

### Task 4: End-to-end local verification

**Files:**
- Modify: `backend/README.md` and/or `frontend/README.md` for startup and test steps, if those files exist.

**Interfaces:** No new runtime interface.

- [ ] Run the fast backend suite, frontend Vitest suite and frontend build.
- [ ] With the confirmed first lesson, answer correctly, answer wrongly, skip, refresh after feedback, resume, finish both stages and compare the summary with stored attempts. If no version is confirmed, verify the empty-state path without changing the user's confirmation choice.
