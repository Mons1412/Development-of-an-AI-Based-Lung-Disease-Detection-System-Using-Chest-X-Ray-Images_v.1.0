# TASK 8.2 — SQLite Persistence Foundation Report

**Status:** PASS for the approved persistence-foundation scope. This task adds no history API, patient form, history UI, floating assistant, chart, report-v2 work, model change, or external integration.

## 1. Architecture implemented

The application now owns a narrow local persistence boundary:

```text
FastAPI lifespan
  -> AnalysisHistoryService
    -> SQLiteConnectionFactory -> ordered SQLite migrations -> AnalysisHistoryRepository
    -> ThumbnailStore (validated bytes only, atomic local derivative write)
```

- Python standard-library `sqlite3` is the only database implementation. No ORM or production dependency was added.
- `create_lifespan` initializes the store once during startup. A local history initialization failure is logged without request data, sets `app.state.history_ready = False`, and does not disable the established prediction service or assistant.
- Connections are short-lived, enable `PRAGMA foreign_keys = ON`, use a bounded `PRAGMA busy_timeout`, and use `BEGIN IMMEDIATE` transactions for writes.
- SQL values are always parameter-bound. Query text is composed only from fixed, internal filter clauses.
- The repository has no HTTP knowledge; `AnalysisHistoryService` coordinates thumbnail creation and deletion recovery.

## 2. Schema and migration version

- **Database:** `var/data/lung_xray_history.db` (resolved relative to the repository root unless `HISTORY_DB_PATH` is explicitly configured).
- **Thumbnails:** `var/data/thumbnails/` (resolved the same way unless `THUMBNAIL_DIR` is explicitly configured).
- **Current schema version:** `1` (`LATEST_SCHEMA_VERSION = 1`).
- **Migration tracking:** `schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)`.
- **Analysis table:** `analysis_history` holds the UUID analysis ID; nullable patient code/name; patient source; confirmation and anonymous flags; sanitized original filename; relative thumbnail filename; predicted label; three probabilities; model/Knowledge Base versions; processing time; analysis time; and creation time.
- **Indexes:** `analyzed_at`, `patient_code`, `patient_display_name`, and `predicted_label` have the required indexes; initialization verifies their existence.
- A database reporting a newer schema version raises `SchemaVersionError`; no destructive downgrade, reset, or data-removal migration runs automatically.

## 3. Thumbnail and privacy contract

- Only an `ImageValidator`-validated in-memory `ValidatedImage` can be supplied to `ThumbnailStore`.
- The store applies EXIF orientation, converts to RGB, bounds the long edge to **512 px**, and writes an optimized WebP derivative when Pillow supports WebP; otherwise it writes JPEG.
- The final filename is the canonical analysis UUID plus `.webp` or `.jpg`; callers receive only that relative filename.
- Temporary output is flushed and atomically replaced. A failed write removes its partial temp file. Traversal, absolute paths, nested paths, hidden files, and unsupported extensions are rejected.
- The schema contains no full-resolution-image/BLOB field. The original filename is sanitized metadata only; upload bytes are never passed to SQLite.
- Delete first stages the thumbnail by atomic rename, then deletes the record transactionally. If database deletion fails, the thumbnail is restored. If final unlink fails after database commit, the staged file remains explicitly marked `*.delete-pending`, the error is surfaced, and the next startup retries cleanup. No outcome is silently reported as a complete deletion.

## 4. Configuration and release exclusion

The following non-secret settings were added to `Settings` and `.env.example`:

| Setting | Default |
|---|---|
| `HISTORY_DB_PATH` | `var/data/lung_xray_history.db` |
| `THUMBNAIL_DIR` | `var/data/thumbnails` |
| `THUMBNAIL_MAX_DIMENSION` | `512` |
| `HISTORY_PAGE_SIZE` | `25` |
| `HISTORY_BUSY_TIMEOUT_MS` | `5000` |

`var/data/*` is ignored by Git while `var/data/.gitkeep` retains the empty directory. This prevents local SQLite files and generated thumbnails from entering source control. No release package was built in this task; final archive exclusion remains a mandatory Task 8.9/Task 09 gate.

The prediction integration fixture was also changed to use `tmp_path_factory` for its history database and thumbnail directory. Future automated runs therefore do not initialize the default local history path. An already-present, zero-record local database at the configured default path was left untouched rather than deleting an ambiguous local-data file; it is Git-ignored and must be excluded by the future package manifest check.

## 5. Files changed

### New source files

- `src/lung_xray_api/infrastructure/persistence/__init__.py`
- `src/lung_xray_api/infrastructure/persistence/connection.py`
- `src/lung_xray_api/infrastructure/persistence/migrations.py`
- `src/lung_xray_api/infrastructure/persistence/records.py`
- `src/lung_xray_api/infrastructure/persistence/analysis_repository.py`
- `src/lung_xray_api/infrastructure/persistence/thumbnail_store.py`
- `src/lung_xray_api/application/analysis_history_service.py`
- `src/lung_xray_api/schemas/analysis_history.py`
- `tests/unit/test_analysis_history_persistence.py`
- `var/data/.gitkeep`

### Existing files updated

- `src/lung_xray_api/core/config.py`
- `src/lung_xray_api/core/lifespan.py`
- `src/lung_xray_api/core/exceptions.py`
- `tests/conftest.py`
- `tests/integration/test_assistant_api.py`
- `tests/integration/test_predict_api.py`
- `.env.example`
- `.gitignore`

## 6. Verification

| Command | Result |
|---|---|
| `& .venv\Scripts\python.exe -m pytest tests/unit/test_analysis_history_persistence.py -q` | PASS — 12 passed; one existing Starlette/TestClient deprecation warning. |
| `& .venv\Scripts\python.exe -m pytest tests/integration/test_predict_api.py tests/unit/test_analysis_history_persistence.py -q` | PASS — 24 passed; confirms prediction regression and temporary test-store isolation. |
| `& .venv\Scripts\python.exe -m pytest -q` | PASS — 276 passed; one existing Starlette/TestClient deprecation warning. |
| `& .venv\Scripts\python.exe -m compileall -q src tests scripts` | PASS. |
| `& .venv\Scripts\python.exe -m ruff check src tests scripts` | PASS — all checks passed. |
| `& .venv\Scripts\python.exe -m pyright` | PASS — 0 errors, 0 warnings, 0 informations. |
| `git diff --check` | NOT CLEAN due to pre-existing trailing whitespace in `README.md:4` and `../SUBMISSION_CHECKLIST.md:4`; neither file was changed to resolve that unrelated issue. |

Persistence coverage includes first/repeated initialization, migration version and future-version rejection, lifespan initialization, create/get/list/delete, pagination, bounded filters, SQL-injection-shaped search text, Unicode patient names, filename sanitization, no original image column/bytes, thumbnail size/path traversal, failed thumbnail writes, SQLite lock timeout behavior, and thumbnail rollback after failed database deletion.

## 7. Remaining risks and explicit next boundary

1. There is intentionally no endpoint or UI that writes analysis records yet. Task 8.3 must introduce approved metadata confirmation and a server-bound analysis endpoint before normal predictions persist history.
2. Filename parsing is not implemented; the approved naming pattern remains a Task 8.3 gate.
3. Local history can contain patient metadata after Task 8.3. The unresolved local-access, retention, backup ownership, and clean-Windows package-exclusion decisions remain release blockers from TASK 8.1.
4. This task tests SQLite lock reporting, but not every OS-specific file-lock/anti-virus failure mode. Startup preserves prediction availability if the optional history foundation cannot initialize.
5. The configured default path currently contains a zero-record local database. It is ignored and was not deleted because it could be user-owned local state; final packaging must prove exclusion rather than relying on Git ignore alone.
6. No packaging, database upgrade/restore drill, history API, thumbnail serving, report v2, or browser workflow has been claimed or implemented here.

## 8. Recommended next action

Proceed only to **TASK 8.3** after the filename naming convention and local patient-information policy are explicitly approved. Keep the existing prediction endpoints unchanged and route new confirmed-analysis persistence through the service established here.
