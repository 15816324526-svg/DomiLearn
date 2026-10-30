# Textbook PDF Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local-only DomiLearn 1.0 workflow that uploads 《现代西班牙语1》, converts it with Docling, persists status and version metadata, and lets the user confirm or immediately retry the result.

**Architecture:** The existing Vue application talks to a new FastAPI backend. SQLite is the source of truth for one fixed textbook, source files, import jobs, and conversion versions; large files live under `backend/storage`. One background worker launches Docling in a child process through a converter interface, while ordinary tests substitute a fast fake converter.

**Tech Stack:** Vue 3, TypeScript, Pinia, Vite, Vitest, FastAPI, SQLAlchemy 2, Alembic, SQLite, Pydantic Settings, pypdf, pytest, Docling 2.142.1, RapidOCR, onnxruntime 1.31.0

**Spec:** `docs/superpowers/specs/2026-10-26-textbook-pdf-import-design.md`

## Global Constraints

- Python 3.10 or newer; local development should use one backend virtual environment.
- Only textbook ID `modern-spanish-1` and title `现代西班牙语1` exist in 1.0.
- PDF size limit is exactly 500 MiB (`500 * 1024 * 1024` bytes).
- Conversion uses local CPU, full-page RapidOCR Chinese OCR, no remote services, no VLM, no LLM, and a two-hour timeout.
- Only one `queued` or `processing` job may exist at a time.
- An awaiting-confirmation job becomes `superseded` before its retry is created; only the latest awaiting job is confirmable.
- Previously confirmed versions and their artifacts are never deleted automatically.
- `backend/storage` is runtime data and must be ignored by Git.
- Frontend copy and styling follow the existing Chinese, low-saturation DomiLearn visual system.
- The workspace currently has no Git repository; commit steps are conditional on the user initializing Git later.

## Review Focus

- A renamed non-PDF or truncated PDF must be rejected before a job is queued; covered in Task 2 validation tests.
- Two nearly simultaneous upload/retry requests must not create two active jobs; covered in Task 3 transaction tests.
- Confirmation racing with retry must produce exactly one winner and never activate a superseded result; covered in Task 3 state tests.
- A backend restart during processing must preserve the current confirmed version while marking only the interrupted job failed; covered in Task 5 recovery tests.
- A successful child process with missing, malformed, or wrong-page-count JSON must still fail the job and never publish a version; covered in Task 4 output-validation tests.

---

### Task 1: Backend foundation, configuration, and database schema

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/textbook.py`
- Create: `backend/app/models/import_job.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_textbook_import.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_database.py`

**Interfaces:**
- Produces: `Settings`, `get_settings()`, `create_engine_from_settings(settings)`, `session_scope()`, SQLAlchemy models `Textbook`, `SourceFile`, `ImportJob`, `ConversionVersion`, and enum `ImportStatus`.
- Database timestamps are timezone-aware UTC ISO datetimes at API boundaries; paths stored in the database are relative to `storage_root`.

- [ ] **Step 1: Write failing schema tests**

Add `test_migrations_create_fixed_textbook`, `test_source_sha256_is_unique`, and `test_import_status_includes_superseded`. Assert migration creates all four tables, seeds `modern-spanish-1`, and enforces the source hash uniqueness constraint.

- [ ] **Step 2: Run the schema tests and verify failure**

Run: `cd backend; pytest tests/test_database.py -v`

Expected: FAIL because backend package and schema do not exist.

- [ ] **Step 3: Add project dependencies and settings**

Declare FastAPI, Uvicorn, SQLAlchemy, Alembic, Pydantic Settings, python-multipart, pypdf, psutil, Docling `2.142.1`, and onnxruntime `1.31.0`; add pytest/httpx development dependencies. Implement `Settings(storage_root: Path, database_url: str, max_pdf_bytes: int = 524288000, conversion_timeout_seconds: int = 7200)` and environment overrides prefixed `DOMILEARN_`.

- [ ] **Step 4: Implement models and initial migration**

Use the exact fields and relationships from the spec, including `ImportJob.display_filename`, `log_path`, `superseded_by_job_id`, and optimistic status conditions needed by later services. Seed the fixed textbook idempotently.

- [ ] **Step 5: Run migration and schema tests**

Run: `cd backend; alembic upgrade head; pytest tests/test_database.py -v`

Expected: migration succeeds and all schema tests PASS.

- [ ] **Step 6: Commit if Git exists**

Commit message: `feat: add textbook import backend foundation`

---

### Task 2: Streaming PDF validation and deduplicated source storage

**Files:**
- Create: `backend/app/services/pdf_validation.py`
- Create: `backend/app/services/source_storage.py`
- Test: `backend/tests/services/test_pdf_validation.py`
- Test: `backend/tests/services/test_source_storage.py`

**Interfaces:**
- Produces: `PdfMetadata(page_count: int, size_bytes: int, sha256: str)`, `PdfValidationError(code: str, message: str)`, `validate_staged_pdf(path: Path, original_filename: str, max_bytes: int) -> PdfMetadata`, and `SourceStorage.stage_upload(upload: UploadFile) -> StagedUpload` / `finalize(staged: StagedUpload, metadata: PdfMetadata) -> StoredSource`.
- Consumes: `Settings.storage_root` and `SourceFile` from Task 1.

- [ ] **Step 1: Write failing validation tests**

Cover valid one-page PDF, uppercase `.PDF`, empty file, wrong extension, `%PDF` spoof with invalid body, truncated PDF, zero-page parse failure, and a streamed payload crossing 500 MiB without retaining the full payload in memory.

- [ ] **Step 2: Run validation tests and verify failure**

Run: `cd backend; pytest tests/services/test_pdf_validation.py -v`

Expected: FAIL because validation functions do not exist.

- [ ] **Step 3: Implement bounded streaming and PDF validation**

Write uploads into `storage/.tmp/uploads/<uuid>.part` in chunks while counting bytes and hashing SHA-256. Validate extension, size, PDF header, and readable page count with pypdf. Always remove rejected staged files.

- [ ] **Step 4: Write and run failing storage tests**

Assert identical bytes uploaded under two names produce one `originals/<sha256>/source.pdf`, while each returned/import record keeps its own display filename. Assert final paths never contain the user filename.

Run: `cd backend; pytest tests/services/test_source_storage.py -v`

Expected: FAIL before `SourceStorage` is implemented.

- [ ] **Step 5: Implement atomic source finalization and disk-space check**

Before finalization require remaining bytes after the upload to be at least `max(2 * 1024**3, size_bytes * 3)`. Move a new source atomically into `textbooks/modern-spanish-1/originals/<sha256>/source.pdf`; discard the staged duplicate when the hash already exists.

- [ ] **Step 6: Run service tests**

Run: `cd backend; pytest tests/services/test_pdf_validation.py tests/services/test_source_storage.py -v`

Expected: all tests PASS.

- [ ] **Step 7: Commit if Git exists**

Commit message: `feat: validate and store textbook pdf sources`

---

### Task 3: Import state machine and version transactions

**Files:**
- Create: `backend/app/services/import_service.py`
- Create: `backend/app/schemas/textbook_import.py`
- Test: `backend/tests/services/test_import_service.py`

**Interfaces:**
- Produces: `ImportService.create_import(source_id: str, display_filename: str) -> ImportJob`, `retry(job_id: str) -> ImportJob`, `confirm(job_id: str) -> ConversionVersion`, `get_textbook_state() -> TextbookState`, and `get_job(job_id: str) -> ImportJobState`.
- Produces response schemas `TextbookState`, `ImportJobState`, `CurrentVersionState`, and stable `ServiceError(code, status_code, message)`.
- Consumes models and session factory from Task 1 and stored source IDs from Task 2.

- [ ] **Step 1: Write failing state-transition tests**

Test creation as `queued`; rejection when another active job exists; retry of failed job; retry of awaiting job atomically sets it to `superseded`; confirmation activates only the latest awaiting job; old current version remains active until confirmation; historical confirmed versions remain present.

- [ ] **Step 2: Add race-oriented tests**

Using two database sessions, test upload/upload and confirm/retry contention. Assert no more than one active job and no superseded version can become current.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd backend; pytest tests/services/test_import_service.py -v`

Expected: FAIL because service and schemas do not exist.

- [ ] **Step 4: Implement transactional state methods**

Use database transactions and conditional updates on expected status. Treat `queued` and `processing` as active. Preserve current confirmed version in every pending/failed response and snapshot `display_filename` per job/version.

- [ ] **Step 5: Run state tests**

Run: `cd backend; pytest tests/services/test_import_service.py -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit if Git exists**

Commit message: `feat: add textbook import state machine`

---

### Task 4: Converter contract, Docling child process, and artifact validation

**Files:**
- Create: `backend/app/converters/base.py`
- Create: `backend/app/converters/fake.py`
- Create: `backend/app/converters/docling.py`
- Create: `backend/app/converters/docling_runner.py`
- Create: `backend/app/services/artifact_validation.py`
- Test: `backend/tests/converters/test_fake_converter.py`
- Test: `backend/tests/converters/test_docling_command.py`
- Test: `backend/tests/services/test_artifact_validation.py`

**Interfaces:**
- Produces: `ConversionRequest(job_id: str, source_path: Path, work_dir: Path, expected_pages: int, timeout_seconds: int)`, `ConversionResult(markdown_path: Path, json_path: Path, report_path: Path, page_count: int, duration_seconds: float, warnings: list[str])`, and protocol `PdfConverter.convert(request: ConversionRequest) -> ConversionResult`.
- `DoclingConverter` launches `sys.executable -m app.converters.docling_runner <request-json-path>` with no shell and a hard timeout.
- Consumes no database objects; paths and plain value objects form the boundary.

- [ ] **Step 1: Write failing converter-contract and fake tests**

Assert the fake converter creates deterministic Markdown, five-page JSON, and report output for worker/API tests.

- [ ] **Step 2: Write failing Docling command tests**

Monkeypatch `subprocess.run` and assert command arguments select standard pipeline, CPU, RapidOCR `ch`, full-page OCR, Markdown and JSON outputs, remote services off, and the configured timeout without `shell=True`.

- [ ] **Step 3: Write failing artifact-validation tests**

Cover nonzero child exit, timeout, missing Markdown, empty Markdown, missing JSON, malformed JSON, missing `pages`, and page-count mismatch. Assert no final version directory is published.

- [ ] **Step 4: Run tests and verify failure**

Run: `cd backend; pytest tests/converters tests/services/test_artifact_validation.py -v`

Expected: FAIL because converter modules do not exist.

- [ ] **Step 5: Implement converter protocol and fake converter**

Keep converter code independent from SQLAlchemy. Return stable exceptions `ConversionFailed`, `ConversionTimedOut`, and `InvalidArtifacts` with safe user-facing codes.

- [ ] **Step 6: Implement Docling runner and output validator**

The runner uses Docling's Python API with fixed local options and writes `document.md`, `document.json`, and a machine-readable result file. The parent captures stdout/stderr into the task log. Validate artifacts before atomically renaming the work directory to `conversions/<version-id>`.

- [ ] **Step 7: Run converter tests**

Run: `cd backend; pytest tests/converters tests/services/test_artifact_validation.py -v`

Expected: all tests PASS without loading real Docling models.

- [ ] **Step 8: Commit if Git exists**

Commit message: `feat: add isolated docling converter`

---

### Task 5: Persistent single worker and restart recovery

**Files:**
- Create: `backend/app/workers/import_worker.py`
- Create: `backend/app/services/job_recovery.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/workers/test_import_worker.py`
- Test: `backend/tests/services/test_job_recovery.py`

**Interfaces:**
- Produces: `ImportWorker.start()`, `stop()`, `wake()`, and `run_once() -> bool`; `recover_interrupted_jobs(session) -> int`.
- Consumes `PdfConverter` from Task 4 and job/version services from Task 3.
- Worker dependency is injectable; tests use `FakeConverter`, application startup uses `DoclingConverter`.

- [ ] **Step 1: Write failing worker tests**

Assert FIFO processing, one job at a time, status `queued → processing → awaiting_confirmation`, task log creation, report/version row creation, old confirmed version preservation, and safe failure mapping for converter exceptions.

- [ ] **Step 2: Write failing restart-recovery tests**

Seed queued and processing jobs plus a confirmed current version. Assert recovery marks only interrupted jobs failed with `INTERRUPTED`, preserves the current version, and is idempotent.

- [ ] **Step 3: Run tests and verify failure**

Run: `cd backend; pytest tests/workers tests/services/test_job_recovery.py -v`

Expected: FAIL because worker/recovery do not exist.

- [ ] **Step 4: Implement worker lifecycle**

Use one application-owned daemon thread with a wake event and short database polling fallback. Open a fresh SQLAlchemy session per state transition. Shutdown must stop accepting new work and leave an in-flight job recoverable as interrupted on next startup.

- [ ] **Step 5: Add FastAPI lifespan wiring**

On startup: create storage folders, apply/verify schema, recover interrupted jobs, then start worker. On shutdown: stop worker without falsely marking success.

- [ ] **Step 6: Run worker and recovery tests**

Run: `cd backend; pytest tests/workers tests/services/test_job_recovery.py -v`

Expected: all tests PASS.

- [ ] **Step 7: Commit if Git exists**

Commit message: `feat: run persistent textbook import worker`

---

### Task 6: FastAPI textbook import endpoints

**Files:**
- Create: `backend/app/api/dependencies.py`
- Create: `backend/app/api/textbook_imports.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/api/test_textbook_imports.py`

**Interfaces:**
- Produces exactly the five endpoints in the spec under `/api` and envelope `{code: int, message: str, data: T}` compatible with the existing frontend.
- Consumes storage from Task 2, import service from Task 3, and worker `wake()` from Task 5.

- [ ] **Step 1: Write failing endpoint tests**

Cover empty state, valid multipart upload returning HTTP 202, renamed PDF, invalid PDF, oversized stream, active-job HTTP 409, job status, confirm, retry, superseded confirm rejection, unknown job HTTP 404, and current-version visibility beside newer failed/pending jobs.

- [ ] **Step 2: Run API tests and verify failure**

Run: `cd backend; pytest tests/api/test_textbook_imports.py -v`

Expected: FAIL because routes do not exist.

- [ ] **Step 3: Implement route dependency wiring and error envelope**

Map service errors to stable codes including `INVALID_PDF`, `PDF_TOO_LARGE`, `INSUFFICIENT_DISK`, `ACTIVE_JOB_EXISTS`, `INVALID_JOB_STATE`, and `JOB_NOT_FOUND`. Never return internal paths, stack traces, or PDF text.

- [ ] **Step 4: Implement the five endpoints**

Upload stages and validates the file before creating/waking a job. Confirm and retry return the updated `TextbookState`; status includes elapsed seconds computed from persisted timestamps and nullable real page progress.

- [ ] **Step 5: Add local CORS configuration**

Allow only configured development origins, defaulting to `http://localhost:5173` and `http://127.0.0.1:5173`.

- [ ] **Step 6: Run all backend fast tests**

Run: `cd backend; pytest -m "not docling" -v`

Expected: all tests PASS without downloading models.

- [ ] **Step 7: Commit if Git exists**

Commit message: `feat: expose textbook import api`

---

### Task 7: Frontend API types, multipart request support, and store

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/request.ts`
- Modify: `frontend/src/api/index.ts`
- Create: `frontend/src/stores/textbook.ts`
- Create: `frontend/src/stores/textbook.spec.ts`
- Create: `frontend/src/test/setup.ts`
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- Produces TypeScript types `ImportStatus`, `ImportJobState`, `CurrentVersionState`, `TextbookState` matching Task 3 schemas.
- Produces API functions `getTextbookState()`, `uploadTextbook(file: File)`, `getImportJob(jobId)`, `confirmImport(jobId)`, and `retryImport(jobId)`.
- Produces Pinia store actions `load()`, `upload(file)`, `confirm()`, `retry()`, `startPolling()`, and `stopPolling()`.

- [ ] **Step 1: Add Vitest tooling and write failing request/store tests**

Assert multipart requests do not force `Content-Type: application/json`; upload starts immediately; polling refreshes every three seconds while active; transient polling failure preserves server state and exposes a connection message; polling stops outside active states.

- [ ] **Step 2: Run tests and verify failure**

Run: `cd frontend; npm test -- --run src/stores/textbook.spec.ts`

Expected: FAIL because scripts, types, API, and store do not exist.

- [ ] **Step 3: Fix generic request handling**

Change `http<T>` to add JSON content type only when the body is not `FormData`. Parse the existing API envelope and preserve `ApiError` behavior.

- [ ] **Step 4: Implement types, API functions, and textbook store**

Textbook endpoints must bypass the existing general mock switch and call the real backend, while unrelated learning pages continue using mocks. Store state is always replaceable by a fresh server response after page refresh.

- [ ] **Step 5: Run frontend unit and type tests**

Run: `cd frontend; npm test -- --run; npm run typecheck`

Expected: all tests PASS.

- [ ] **Step 6: Commit if Git exists**

Commit message: `feat: add textbook import frontend state`

---

### Task 8: Textbook directory page and navigation

**Files:**
- Create: `frontend/src/views/textbook/Directory.vue`
- Create: `frontend/src/views/textbook/Directory.spec.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/AppSidebar.vue`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/assets/styles/pages.css`

**Interfaces:**
- Consumes the textbook store from Task 7.
- Produces route `/textbook` with `meta.nav = 'textbook'` and adds `'textbook'` to `NavKey`.

- [ ] **Step 1: Write failing component tests for every visible state**

Test loading, empty drop zone, immediate upload from file picker, immediate upload from drag/drop, client extension/size feedback, queued/processing elapsed time, optional real page count, awaiting-confirmation actions, confirmed card, failed actions, and current-version note beside pending/failed attempt.

- [ ] **Step 2: Run component tests and verify failure**

Run: `cd frontend; npm test -- --run src/views/textbook/Directory.spec.ts`

Expected: FAIL because page and route do not exist.

- [ ] **Step 3: Implement route and enable sidebar item**

Replace the disabled textbook anchor with a normal `RouterLink`; retain the existing book icon and active-navigation behavior.

- [ ] **Step 4: Implement the page using one upload path**

Both `<input type="file">` and drop events call `selectFile(file: File)`. Use the accepted Chinese copy from the spec; do not render Markdown/JSON bodies or history controls.

- [ ] **Step 5: Add page styles with existing design tokens**

Create textbook-prefixed classes in `pages.css`; reuse `.card`, `.btn`, `.badge`, status tint variables, existing radii, and existing responsive layout conventions.

- [ ] **Step 6: Run frontend verification**

Run: `cd frontend; npm test -- --run; npm run typecheck; npm run build`

Expected: all tests, typecheck, and production build PASS.

- [ ] **Step 7: Commit if Git exists**

Commit message: `feat: add textbook pdf import page`

---

### Task 9: Local Docling integration check and developer instructions

**Files:**
- Create: `backend/tests/integration/test_docling_sample.py`
- Create: `backend/scripts/build_docling_sample.py`
- Create: `backend/README.md`
- Create: `backend/storage/.gitkeep`
- Modify: `backend/.gitignore`
- Modify: `frontend/vite.config.ts`

**Interfaces:**
- `build_docling_sample.py --source <pdf> --output <pdf>` extracts one-based pages `10,18,19,24,29`.
- Integration test marker is `docling`; it skips with a clear reason if `TextBook/现代西班牙语1.pdf` or local models are unavailable.

- [ ] **Step 1: Write the sample builder and marked integration test**

Assert the real converter returns Markdown and JSON, JSON contains exactly five pages, report says `docling`, and remote/VLM settings remain disabled. Do not assert OCR text byte-for-byte.

- [ ] **Step 2: Run the sample integration test**

Run: `cd backend; pytest -m docling tests/integration/test_docling_sample.py -v`

Expected: PASS using the existing textbook and cached models, or an explicit SKIP if prerequisites are absent.

- [ ] **Step 3: Document environment and startup commands**

Document virtual-environment creation, dependency installation, `alembic upgrade head`, backend `uvicorn app.main:app --reload`, frontend `npm run dev`, storage location, first model download, offline behavior, and the no-LLM guarantee.

- [ ] **Step 4: Configure local frontend proxy**

Proxy `/api` from Vite port 5173 to FastAPI port 8000 so development works without changing the existing default `API_BASE`.

- [ ] **Step 5: Run the complete fast verification suite**

Run: `cd backend; pytest -m "not docling" -v`

Run: `cd frontend; npm test -- --run; npm run typecheck; npm run build`

Expected: all commands PASS.

- [ ] **Step 6: Perform one API smoke test with the five-page sample**

Start backend and frontend separately, upload the generated sample through the API/page, observe `processing → awaiting_confirmation`, confirm it, refresh the page, and verify it remains `confirmed`.

- [ ] **Step 7: Run the final full-book manual acceptance test**

Upload `D:\LearnEspa\TextBook\现代西班牙语1.pdf`, allow the job to finish, verify all 305 pages and four artifacts, then exercise confirm and retry while ensuring the confirmed version remains active. Do this once after all fast tests pass.

- [ ] **Step 8: Commit if Git exists**

Commit message: `test: verify local docling textbook import`

