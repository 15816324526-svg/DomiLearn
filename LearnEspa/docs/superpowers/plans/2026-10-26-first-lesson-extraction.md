# First Lesson Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically classify the first lesson's passages and vocabulary when the fixed textbook PDF conversion succeeds.

**Architecture:** A backend extractor reads Docling JSON for headings and passages, and runs local RapidOCR only over the detected vocabulary tables to recover row alignment. It creates version-scoped lesson, vocabulary and passage rows within the conversion worker's successful transaction; a repeatable backfill command handles the existing conversion.

**Tech Stack:** Python 3.12, Docling JSON, pypdfium2, RapidOCR, SQLAlchemy 2, Alembic, SQLite, pytest.

**Spec:** `docs/superpowers/specs/2026-10-26-first-lesson-extraction-design.md`

## Global Constraints

- Fixed textbook `modern-spanish-1`, first lesson only.
- No LLM, remote service, frontend preview, learning plan, or additional confirmation.
- Preserve old confirmed versions and existing PDF, Markdown and Docling JSON files.
- Runtime data belongs in `backend/storage`; classes and scripts belong in `backend/app` or `backend/scripts`.

## Review Focus

- A table whose OCR lines are merged must yield individual entries instead of one giant word.
- Missing lesson headings or vocabulary region must fail clearly without publishing a half-classified version.
- A wrapped Chinese meaning stays attached to the correct Spanish word.
- Re-running backfill for one version creates no duplicates.
- Retrying a conversion preserves previously confirmed version and lesson rows.

---

### Task 1: Version-scoped lesson schema

**Files:**
- Create: `backend/app/models/lesson.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/0002_first_lesson.py`
- Test: `backend/tests/test_lesson_schema.py`

**Interfaces:**
- Produces `Lesson`, `VocabularyEntry`, `Passage` ORM models with foreign keys to `ConversionVersion`, unique lesson number per version and unique ordinals per lesson.

- [ ] Add a schema test covering foreign keys, uniqueness and version isolation.
- [ ] Run it and observe the missing schema failure.
- [ ] Add models and migration, then run the schema test and migration.

### Task 2: Docling heading and passage extraction

**Files:**
- Create: `backend/app/services/lesson_extraction.py`
- Test: `backend/tests/services/test_lesson_extraction.py`

**Interfaces:**
- Produces `extract_lesson_structure(document: dict) -> LessonStructure` with first/next unit pages, passage titles and text blocks, and vocabulary table page/bounds.

- [ ] Add synthetic JSON tests for two passages, page provenance, missing markers and exercise exclusion.
- [ ] Run tests to confirm failure.
- [ ] Implement structure extraction and rerun tests.

### Task 3: Local vocabulary row OCR

**Files:**
- Create: `backend/app/services/vocabulary_ocr.py`
- Test: `backend/tests/services/test_vocabulary_ocr.py`

**Interfaces:**
- Produces `extract_vocabulary(source_pdf: Path, tables: list[TableRegion]) -> list[VocabularyRecord]`; no network or LLM client.

- [ ] Test coordinate assignment, missing optional POS, wrapped meanings and two table pages using synthetic OCR boxes.
- [ ] Implement PDF page rendering and RapidOCR line geometry; run tests.
- [ ] Test on the real first lesson and inspect item counts and samples.

### Task 4: Persist in conversion flow and backfill

**Files:**
- Modify: `backend/app/workers/import_worker.py`
- Create: `backend/app/services/lesson_repository.py`
- Create: `backend/scripts/backfill_first_lesson.py`
- Modify: `backend/README.md`
- Test: `backend/tests/workers/test_import_worker.py`
- Test: `backend/tests/services/test_lesson_repository.py`

**Interfaces:**
- Produces `extract_first_lesson(source_pdf: Path, docling_json: Path) -> LessonExtraction`, `save_first_lesson(session: Session, version_id: str, extraction: LessonExtraction) -> Lesson`, and a repeatable CLI command for existing successful versions.

- [ ] Test successful task stores lesson, vocabulary and passages before awaiting confirmation; invalid extraction fails the job and preserves current version.
- [ ] Test backfill idempotence and version isolation.
- [ ] Wire extraction into the worker, add the CLI, document commands; run tests.
- [ ] Run real backfill for the existing 305-page conversion and verify stored counts, page provenance and no duplicate rows on a second run.
- [ ] Run backend fast suite and frontend build. No Git commit because this workspace has no Git repository.
