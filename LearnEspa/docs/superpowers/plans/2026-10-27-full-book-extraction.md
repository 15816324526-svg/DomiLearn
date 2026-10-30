# Full Book Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate every lesson's passages and vocabulary from the already converted 305-page 《现代西班牙语 1》 PDF, while preserving the confirmed conversion and first-lesson learning records.

**Architecture:** Audit the existing Docling JSON by lesson before changing the extractor; layouts are not uniform. Add a book-level extraction result and generic persistence, then backfill the confirmed conversion without rerunning Docling. A lesson only counts as ready when its source page range, passages, vocabulary, and text quality checks are recorded.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, SQLite, existing Docling JSON and vocabulary OCR pipeline.

**Spec:** `docs/superpowers/specs/2026-10-27-imitation-module-design.md`

## Global Constraints

- 1.0 release covers all 16 lessons; first lesson is only the implementation slice.
- Do not overwrite the original PDF, Docling artifacts, or confirmed source text. Preserve existing vocabulary sessions and attempts.
- Do not assume exactly two passages or a uniform six-column, two-page vocabulary layout in all lessons.
- The workspace is not a Git repository, so commit steps are unavailable; verify changed files and tests after each task.

## Review Focus

- Repeated lesson headers across pages must yield exactly one lesson boundary per number; pin in the extraction test.
- A missing or misrecognized TEXTOS/VOCABULARIO heading must produce a visible diagnostic, not silently drop a chapter; pin in the layout test.
- Re-running backfill must retain stable lesson, passage, and word IDs so existing attempts remain attached; pin in repository tests.
- A passage with no usable sentences or vocabulary with no meaning must not mark a lesson ready; pin in validation tests.
- OCR of a later lesson with a different page layout must not corrupt the first lesson; pin with first-lesson regression plus a later lesson fixture.

---

### Task 1: Audit chapter layouts in the confirmed conversion

**Files:** Create `backend/scripts/audit_book_layout.py`; test `backend/tests/integration/test_book_layout.py`.

**Interfaces:** `audit_book_layout(docling_json: Path) -> list[LessonLayout]`, where each result records number, page range, candidate passage headings, candidate vocabulary regions, and diagnostics. The report is diagnostic data, not a replacement textbook version.

- [ ] Write tests that detect all 16 ordered lesson numbers in the existing conversion, deduplicate repeated headers, and flag missing passage/vocabulary markers.
- [ ] Run `backend/.venv/Scripts/python.exe -m pytest backend/tests/integration/test_book_layout.py -q`; verify the intended failures.
- [ ] Implement the audit script and generate a compact per-lesson report for the confirmed `document.json`.
- [ ] Run the test again and inspect every chapter's diagnostics before generalizing extraction.

### Task 2: Extract full-book lesson content with per-layout validation

**Files:** Modify `backend/app/services/lesson_extraction.py` and `backend/app/services/vocabulary_ocr.py` as needed; test `backend/tests/services/test_book_extraction.py`; retain first-lesson tests.

**Interfaces:** `extract_book(source_pdf: Path, docling_json: Path) -> tuple[ExtractedLesson, ...]`; `ExtractedLesson` has lesson number, title, page range, ordered passage records, ordered vocabulary records, and diagnostics. Preserve `extract_first_lesson` as a compatibility wrapper. A detected but unextractable lesson raises a named error instead of returning a partial ready book.

- [ ] Add fixtures for the distinct layouts found in Task 1; assert ordered passages and words, source pages, and nonempty text/meanings.
- [ ] Run the targeted tests and see failures.
- [ ] Generalize boundaries and text regions; adapt vocabulary OCR only where the real later pages require it. Keep first-lesson behavior intact.
- [ ] Run first-lesson regression and book extraction tests; verify 16 validated lessons on the confirmed conversion.

### Task 3: Persist all lessons and backfill without reconversion

**Files:** Modify `backend/app/services/lesson_repository.py`, `backend/app/workers/import_worker.py`, `backend/app/main.py`; create `backend/scripts/backfill_book.py`; test `backend/tests/services/test_book_repository.py` and worker integration.

**Interfaces:** `save_lesson(session: Session, version_id: str, lesson: ExtractedLesson) -> None`; `save_book(...)` uses it transactionally. Backfill consumes the confirmed `source.pdf` and `document.json` and must not invoke Docling. Existing first-lesson IDs and attempts remain valid.

- [ ] Test first-lesson ID preservation, idempotent rerun, transactional failure on an invalid later lesson, and worker readiness only after all lessons validate.
- [ ] Run the tests to confirm failures.
- [ ] Implement generic persistence, import-worker hookup, and an explicit backfill command for the already confirmed conversion.
- [ ] Run tests and backfill against a safe copy of the local database, then inspect lesson/passage/word counts and diagnostics before applying to the user database.

### Task 4: Release coverage audit

**Files:** Extend `backend/scripts/audit_book_layout.py`; test `backend/tests/integration/test_book_coverage.py`.

**Interfaces:** `audit_book_coverage(session, version_id) -> CoverageReport` identifies every missing or unready lesson/passage/vocabulary section. The script exits nonzero when the 16-lesson release gate is not met.

- [ ] Test a missing lesson, empty passage, and complete 16-lesson case.
- [ ] Implement the audit and inspect a real 16-row summary with the confirmed conversion.
- [ ] Run existing backend tests plus the coverage audit; record any remaining manual OCR corrections as explicit data work, not silent success.

