# TASK 8.1 — Change Impact Audit and Design Freeze

**Status:** DESIGN FREEZE PROPOSAL — no production code, model artifact, database file, API route, UI, or release package was implemented in this task.
**Date:** 2026-07-27
**Release status:** BLOCKED. The existing stable release remains unchanged.

## Task contract

- **Goal:** define the smallest safe architecture for local case metadata, SQLite-backed local history, thumbnail-only storage, report v2, a compact clinical-analysis workspace, and a floating offline-assistant widget.
- **Scope:** source and workspace audit; design decisions; exact target paths, contracts, tests, migration, rollback, and release gates for Tasks 8.2–8.9.
- **Explicitly excluded:** implementation, model retraining/weight changes, external AI/API integration, frontend framework, database creation, data migration execution, UI redesign, package creation, and release declaration.
- **Acceptance criterion for this task:** subsequent work can be implemented in small reversible tasks without changing the existing `/api/v1/predict`, `/predict`, offline assistant, or stable package contracts.

## 1. Files inspected

### Application and runtime

- `pyproject.toml`, `requirements-lock.txt`, `.env.example`, `.gitignore`, `README.md`.
- All source-owned Python modules under `src/lung_xray_api/`, including the FastAPI composition root, API routes, schemas, application service, assistant package, model runtime, image validation, preprocessing, and predictor.
- All current Jinja templates and JavaScript/CSS assets under `src/lung_xray_api/web/`.
- Model contracts under `artifacts/lung_classifier/1.1.0/` (read only).
- All current tests under `tests/` and runtime/verification scripts under `scripts/`, including portable-runtime tooling.

### Phase 3 source of truth and evidence

- `PHASE3_IMPLEMENTATION_WORKSPACE/README_FIRST.md` and `00_START_HERE/`.
- Completed reports `12_VALIDATION/TASK_01_*` through `TASK_08_*`.
- Knowledge Base production/development indexes, review gate, assistant architecture/UI notes, teacher/UI/PDF requirements, evaluation requirements, release plans, and work-order index.

## 2. Current-state inventory

### 2.1 Runtime, database, and persistence

| Area | Current fact | Impact |
|---|---|---|
| Database | No database library, SQLite file, repository, migration, or history route exists. `pyproject.toml` does not require an ORM. | SQLite can use Python's standard-library `sqlite3`; no new production dependency is justified. |
| Prediction image | `/api/v1/predict` reads upload bytes into memory; `ImageValidator` validates them and `ImagePreprocessor` re-opens them from `BytesIO`. | Original full-resolution bytes are not persisted today and must remain non-persistent by default. |
| Report | `/api/v1/report/preview` receives a browser-supplied, validated current prediction and renders controlled Jinja HTML in memory; the browser owns Print/Save as PDF. | Report v1 has no analysis ID or trusted server-side provenance. A new server-bound v2 is required; v1 remains for compatibility. |
| Assistant | One `AssistantService` is built in lifespan from only `knowledge_base.production.vi.json`; it has deterministic safety, state validation, intent rules and TF-IDF retrieval. | It must stay offline and must never receive patient metadata, filenames, thumbnails, or history rows. |
| Logs | Application logging has a generic format and no intended request-body logging. | New code must not log patient name, patient code, filename, thumbnail bytes, report HTML, or SQL values. |

### 2.2 Existing prediction contract

`POST /api/v1/predict` and the `/predict` compatibility alias accept only multipart field `file`. They must remain unchanged.

- Validation supports JPEG/PNG, normalizes basename, enforces the 10 MB limit, checks magic bytes/MIME/extension, fully decodes with Pillow, and rejects oversized pixel images.
- `PredictionService` runs `ImageValidator -> ImagePreprocessor -> Predictor` and returns `status`, `prediction`, `model_probability`, nested and flattened three-class probabilities, `model_version`, `processing_time_ms`, and disclaimer.
- Locked class/probability order is `normal`, `pneumonia`, `tuberculosis`; model input is `(1, 224, 224, 3)` `float32`; preprocessing is embedded in the MobileNetV2 artifact; model version is `1.1.0`.

### 2.3 Existing assistant state

The browser maintains exactly one `window.lungXrayAssistantContext` object. It is set to `before_analysis`, `analysis_running`, `after_analysis`, or `analysis_failed`; only a successful result supplies `predicted_label`, three probabilities, model version, and latency. New selection, removal, reset, and failure clear the usable prediction context. The assistant API validates the same probability invariants independently.

The current panel is full-width, included after the two-column demo workspace. It safely inserts text through DOM `textContent`, supports Enter-to-send and Shift+Enter newline, exposes loading/error/source/disclaimer states, and calls only `POST /api/v1/assistant/query`.

### 2.4 Existing report payload

`ReportPreviewRequest` rejects unknown fields. It accepts sanitized `filename` and a `prediction` object with `predicted_label`, the exact probability map, model version, latency, and timezone-aware timestamp. It does not accept patient data, an analysis ID, image bytes/base64, reference-body text, team information, or arbitrary HTML.

### 2.5 Existing frontend architecture

- FastAPI serves one Jinja page: `web/templates/demo.html`.
- `demo.js` owns selected file, object-URL preview, abort controllers, result state, report lifecycle, native-dialog focus restoration, and assistant context.
- `assistant.js`, `report_export.js`, and CSS files are separate assets; no frontend framework or chart library is present.
- The current page is an academic, header-plus-two-panels layout with native `<dialog>` modals. Existing animations include loading/progress/skeleton states and a reduced-motion override.

### 2.6 Current data persistence behavior

There is no user/case persistence. Browser object URLs are revoked on reset/unload. Report previews and assistant responses are request-memory only. The evaluation script writes caller-selected CSV/JSON outputs, which is unrelated to the demo and must remain outside the application history store.

## 3. Change-impact map

| Approved requirement | Existing files affected | New target files | API/schema/test impact | Privacy, migration, and release risk |
|---|---|---|---|---|
| Metadata before analysis and explicit confirmation | `demo.html`, `demo.js`, `demo.css` | `schemas/case_metadata.py`, `application/analysis_service.py` | New metadata schema and analysis endpoint; UI state/browser tests | PII validation; no analysis can start before server-valid `confirmed=true`. |
| Approved-only filename parsing | `ImageValidator` may share basename policy but must not change upload acceptance | `application/filename_metadata_parser.py`, `tests/unit/test_filename_metadata_parser.py` | New parse request/response endpoint and parser tests | Never infer from partial/non-matching names; approved regex is an unresolved sign-off gate. |
| Anonymous/demo mode | `demo.*` | `schemas/case_metadata.py` | Mode validation and UI tests | Must store no code/name and show anonymous status in history/report. |
| Local SQLite history | `core/config.py`, `core/lifespan.py`, `api/dependencies.py`, `api/v1/router.py` | `infrastructure/persistence/{__init__,migrations,sqlite_history_repository}.py`, `application/history_service.py`, `api/v1/history.py`, `schemas/history.py` | New history APIs, repository/migration/endpoint tests | First persistence boundary; writable location, PII, locking, backup, deletion and package exclusion are release gates. |
| Thumbnail-only storage | Existing image validation/preprocessing are reused but not modified | `infrastructure/media/{__init__,thumbnail_generator}.py` | Thumbnail contract, no-original-byte tests | Remove EXIF and constrain dimensions/size; BLOB only, no publicly served file path. |
| List/filter/detail/delete/history export | Router/dependencies, report assets, `demo.*` | `web/templates/history_panel.html`, `web/static/history.{js,css}` | Paginated list/detail/delete/thumbnail/report/trend tests | Avoid SQL string interpolation, path traversal and stale/foreign analysis IDs; deletion is permanent after UI confirmation. |
| Floating support chat | `demo.html`, `assistant.js`, `assistant.css`, `demo.css` | `web/templates/assistant_widget.html`, `web/static/assistant_widget.{js,css}` | Preserve assistant endpoint and add UI/accessibility tests | No patient data enters `AssistantQuery`; loading indicator must not pretend to reveal model reasoning. |
| Controlled thinking/typing animation | Existing CSS reduced-motion rules | Widget CSS/JS | Browser/static tests for busy/disabled/reduced motion | CSS-only indicator while request is pending; no fake medical reasoning or fabricated streaming. |
| Summary/table/category and history trend visualizations | `demo.*` | `web/static/visualizations.{js,css}` or narrow sections in new workspace assets | UI contract/browser tests; optional aggregate trend API | Single prediction never gets a line chart. Trend is an aggregate historical count, not patient progression. |
| Report v2 | `api/v1/report.py`, `schemas/report.py`, `report.html`, `report.css`, `report_export.js` | `web/templates/report_v2.html`, `schemas/report_v2.py` if separation remains clearer | New server-bound report-preview route and tests; v1 preserved | No client-supplied case/thumbnail/reference HTML; BLOB is controlled/inlined only in generated preview. |
| Compact product-grade workspace | `demo.html`, `demo.js`, `demo.css` | `web/templates/analysis_workspace.html`, `web/static/analysis_workspace.{js,css}` | End-to-end UI state contract and visual manual checklist | Large merge-conflict surface; implement incrementally without replacing prediction behavior. |
| Offline-only assistant/production KB | `assistant/*`, `core/lifespan.py` | No external client/module | Assistant regression/KB gate tests | Current `privacy_storage` wording says no database and must be corrected only through an approved policy/KB decision; no development item may be exposed. |

## 4. Approved target architecture

### 4.1 Module boundaries and dependency direction

```text
FastAPI routes
  -> Pydantic request/response schemas
  -> application services (analysis, history, report composition)
  -> infrastructure adapters (SQLite repository, thumbnail generator)

PredictionService (existing) -> ImageValidator -> ImagePreprocessor -> Predictor
AssistantService (existing)  -> production Knowledge Base only
```

- Routes remain thin: transport validation, dependency injection, status mapping.
- `AnalysisService` owns the single transactional sequence: validate confirmed metadata, run the existing `PredictionService`, create thumbnail from already-validated bytes, and persist the completed record.
- `HistoryService` owns query, detail, delete, thumbnail retrieval, and aggregate trend rules. It does not call the model.
- `SQLiteHistoryRepository` owns SQL, transactions, parameter binding, migrations, and row mapping. No route or UI constructs SQL.
- `ThumbnailGenerator` owns pixel/EXIF removal and JPEG encoding. It receives `ValidatedImage`, not a filename/path.
- `ReportService`/the report route owns report-v2 composition from a persisted record only. It has no client-provided model/case HTML content.
- Existing `PredictionService`, assistant service, model artifact, assistant API, and legacy report v1 remain isolated and backward compatible.

### 4.2 SQLite location and lifecycle

**Decision:** SQLite is the only approved persistence engine, using Python `sqlite3`; no ORM or new dependency.

- New `Settings` fields: `HISTORY_ENABLED`, `HISTORY_DB_PATH`, and an application data-root resolver.
- Default Windows portable location: `%LOCALAPPDATA%\\LungXrayAI\\lung_xray_history.sqlite3`. If `LOCALAPPDATA` is unavailable (tests/non-Windows source use), default to `<project-root>/var/data/lung_xray_history.sqlite3`; tests always override it to `tmp_path`.
- The database is created on first use/controlled lifespan initialization, never bundled into a release ZIP. Its parent directory is created only when history is enabled.
- Each request gets a short-lived `sqlite3` connection; `foreign_keys=ON`, parameterized queries, a bounded `busy_timeout`, and one explicit transaction for each create/delete. WAL suitability and backup behavior must be exercised on target Windows before release.
- A failed history initialization sets only the new history feature unavailable with an explicit 503. It does not stop existing prediction endpoints from starting. This is not a silent fallback: readiness/feature status and logs must show the history failure without PII.
- History must be limited to loopback binding in the portable configuration. Exposing a PII history API on a non-loopback host without an approved access-control design is a release blocker.

### 4.3 Migration strategy

There is no existing database to import. Version 1 therefore starts with an empty store.

1. Create `schema_migrations(version INTEGER PRIMARY KEY, applied_at_utc TEXT NOT NULL)`.
2. Apply ordered, idempotent Python migration functions from `infrastructure/persistence/migrations.py` in a transaction.
3. Record the migration only after its DDL succeeds; verify `PRAGMA foreign_key_check` and the expected indexes before making history available.
4. Before any future destructive migration, create a timestamped SQLite backup beside the configured database and document restore. No migration deletes or transforms medical/case data automatically in Tasks 8.2–8.9.
5. Rollback means use the prior application release against a compatible schema or restore the pre-migration backup. It never means deleting the database directory.

### 4.4 Analysis record and patient metadata schema

The first migration creates the following normalized schema. Dates are UTC ISO-8601 text values; analysis IDs are server-generated UUIDv4 strings.

```text
schema_migrations
  version PK, applied_at_utc

analysis_records
  analysis_id PK
  created_at_utc NOT NULL
  predicted_label CHECK normal|pneumonia|tuberculosis
  normal_probability REAL NOT NULL
  pneumonia_probability REAL NOT NULL
  tuberculosis_probability REAL NOT NULL
  model_probability REAL NOT NULL
  model_version TEXT NOT NULL
  processing_time_ms INTEGER NOT NULL
  knowledge_base_version TEXT NOT NULL
  disclaimer_text TEXT NOT NULL
  thumbnail_jpeg BLOB NOT NULL
  thumbnail_sha256 TEXT NOT NULL
  thumbnail_width INTEGER NOT NULL
  thumbnail_height INTEGER NOT NULL
  thumbnail_bytes INTEGER NOT NULL

analysis_case_metadata (one-to-one with analysis_records)
  analysis_id PK/FK
  case_mode CHECK identified|anonymous_demo
  patient_code TEXT NULL
  patient_name TEXT NULL
  metadata_origin CHECK manual|filename_parsed_confirmed|manual_corrected|anonymous_demo
  filename_pattern_id TEXT NULL
  confirmed_at_utc TEXT NOT NULL

analysis_sources
  analysis_id FK
  source_id NOT NULL
  source_title_snapshot NOT NULL
  PRIMARY KEY (analysis_id, source_id)
```

Required indexes: `(created_at_utc DESC)`, `(predicted_label, created_at_utc DESC)`, and `(patient_code, created_at_utc DESC)`. Patient-name search is a bounded, case-insensitive local filter only; it must not use unbounded full-table scan or dynamic SQL.

**Data minimization rules:** the original bytes, original image path, browser object URL, raw uploaded filename, EXIF, IP address, user agent, free-text clinical note, date of birth, address, phone number, medication, and symptoms are not stored. In `identified` mode both patient code and patient name are required after normalization; in `anonymous_demo` mode both must be `NULL` and the UI sends no identifying fields.

### 4.5 Filename parsing contract

No approved filename convention currently exists in source or the Phase 3 workspace. The following is the **proposed, pending-owner-approval** convention; it must not be implemented until the owner approves the exact text and regex:

```text
CASE-<PATIENT_CODE>__NAME-<PATIENT_NAME>.<jpg|jpeg|png>
Example: CASE-BN-000123__NAME-Nguyen Thi A.jpg
```

After basename extraction and Unicode NFC normalization, parsing is all-or-nothing and case-insensitive for fixed tokens:

```text
^CASE-(?P<patient_code>[A-Za-z0-9][A-Za-z0-9-]{2,31})__NAME-
(?P<patient_name>[A-Za-zÀ-ỹ][A-Za-zÀ-ỹ' -]{0,79})\.(?:jpg|jpeg|png)$
```

- A parser result is `matched` only for the entire basename. A partial match, extension mismatch, traversal-looking string, excessive length, unsupported characters, duplicate separators, or empty capture returns `not_matched` and exposes no parsed value.
- `POST /api/v1/case-metadata/parse-filename` is a convenience endpoint for the pre-analysis UI. `POST /api/v1/analyses` repeats the parse server-side and determines `metadata_origin`; the client cannot assert a trusted parsed origin.
- Parsed values populate editable fields only. They never trigger analysis automatically. The user must manually confirm the displayed/corrected fields.

### 4.6 Thumbnail storage contract

- Generate only after the existing validator accepts the upload and only in memory.
- Apply EXIF orientation, convert to RGB, resize proportionally to a maximum 512-pixel long edge, and encode an optimized JPEG with no retained metadata. Use a documented quality/byte cap and deterministically reduce quality/size if necessary.
- Persist the JPEG bytes inside `analysis_records.thumbnail_jpeg`, plus SHA-256, dimensions, MIME (`image/jpeg`), and byte count. Do not create a disk thumbnail or static URL.
- `GET /api/v1/analyses/{analysis_id}/thumbnail` streams only the stored JPEG with `X-Content-Type-Options: nosniff`; it is not mounted under `/static`.
- Report v2 may use a server-generated data URI from this BLOB. It must not accept image base64 from the browser.

### 4.7 History API contract

All endpoints use the existing API-key policy and add the history loopback/configuration gate described above. The existing prediction/report endpoints remain unchanged.

| Endpoint | Contract |
|---|---|
| `POST /api/v1/case-metadata/parse-filename` | JSON `{filename}` -> `{status, pattern_id?, patient_code?, patient_name?, requires_confirmation:true}`. No persistence. |
| `POST /api/v1/analyses` | Multipart `file`, `case_mode`, `patient_code?`, `patient_name?`, `metadata_confirmed=true`. Runs existing prediction, creates thumbnail, and atomically persists one record. Response extends the current prediction result with `analysis_id`, `created_at`, `case_metadata`, and `thumbnail_url`. |
| `GET /api/v1/analyses` | Bounded, cursor-paginated list. Filters: date range, predicted label, case mode, and bounded patient-code/name query. Returns summaries only, never full BLOBs. |
| `GET /api/v1/analyses/{analysis_id}` | One detail record: verified case metadata, output, sources, disclaimer snapshot, thumbnail URL, and report URL. |
| `GET /api/v1/analyses/{analysis_id}/thumbnail` | Controlled JPEG stream from SQLite BLOB. |
| `DELETE /api/v1/analyses/{analysis_id}` | Deletes metadata, thumbnail, sources, and record in one transaction after a client confirmation interaction. Returns 204; subsequent detail/thumbnail/report return 404. |
| `GET /api/v1/analyses/trend` | Same bounded filters plus date granularity. Returns aggregate analysis counts by date/category only when at least two date buckets exist. |
| `POST /api/v1/analyses/{analysis_id}/report-preview` | Controlled report-v2 HTML generated from the persisted record only. No arbitrary request body. |

### 4.8 Frontend application-state contract

`demo.js` will be split by ownership rather than replaced wholesale. The current prediction and state-clearing behavior remains the baseline.

```text
initial
  -> file_selected
  -> metadata_loading (optional filename parse)
  -> metadata_unconfirmed
  -> metadata_confirmed
  -> analysis_running
  -> analysis_succeeded (currentAnalysisId + prediction context)
  -> analysis_failed

Any new file / remove / reset / failed analysis
  -> initial or metadata_unconfirmed
  -> clears currentAnalysisId, result/report state, thumbnail display, and assistant after-analysis context.
```

- The analyze button is disabled unless a valid selected file and confirmed metadata state exist.
- `anonymous_demo` immediately clears both editable identifiers and still requires its own explicit confirmation.
- History selection is read-only and separate from `currentAnalysisId`; viewing an old record never makes it the current pending upload or assistant prediction context.
- A new selection does not delete prior persisted history; it only invalidates current-result actions. Existing full-width assistant history remains in-memory until replaced by the widget in Task 8.8.

### 4.9 Floating assistant UI contract

- Replace the page-wide panel with a fixed, toggleable support-chat widget using one native button and an accessible non-modal panel/`aside`; it must not block analysis controls.
- Toggle updates `aria-expanded`; opening moves focus to the input; Escape closes and returns focus to the toggle. The log, input label, source list, disclaimer, offline badge, suggestions, new conversation, and safe `textContent` rendering are retained.
- The only network call remains `POST /api/v1/assistant/query`; request context remains only stage/prediction/model data. Patient code/name, filename, thumbnail, history detail, and report body are excluded by construction.
- “Thinking/typing” is a bounded busy indicator: visually animated dots and the literal text “Đang tìm trong Knowledge Base ngoại tuyến…”, shown only while a request is pending. It has `role=status`, disables duplicate sends, respects `prefers-reduced-motion`, and must not simulate hidden reasoning or generate text before a response arrives.

### 4.10 Report v2 contract

Report v2 is a browser-print HTML preview, not a binary server PDF. It includes only server-owned persisted data:

- project/university branding, generated time, `analysis_id`, and analysis time;
- identified metadata or an explicit anonymous/demo label;
- controlled JPEG thumbnail/preview;
- Vietnamese class label, API label, all three outputs, model version, latency;
- approved source-ID/title snapshots, knowledge-base version, and the academic/non-diagnostic disclaimer;
- team information and an honest clinical-content availability notice.

It omits the original full-resolution image and raw filename by default. Jinja auto-escaping remains required; the browser cannot inject case fields, source text, or HTML into the preview. Legacy `POST /api/v1/report/preview` remains v1 until a separately approved deprecation plan exists.

### 4.11 Visualization rules

- **Summary:** default single-prediction view with Vietnamese/API label, primary model output, metadata, disclaimer, and source action.
- **Table:** semantic three-row probability table. It remains available to screen readers and print.
- **Category bar/column chart:** a vanilla-JS/CSS or DOM-created SVG representation of the same three output probabilities, paired with the table. It does not introduce a clinical threshold, confidence diagnosis, or a second model.
- **History trend chart:** only when a history query has at least two distinct chronological buckets. It represents aggregate analysis counts by date/category, labels the selected date range, provides a tabular alternative, and must say it is an operational history trend—not a disease-progression chart.
- **No temporal data:** show an unavailable/empty state; do not draw a line, interpolate, or fabricate a trend.

## 5. Explicit decisions

1. The original full-resolution image is not persisted by default.
2. Only an optimized JPEG thumbnail is persisted in SQLite.
3. Patient name parsing happens only after a full match to the explicitly approved filename pattern; otherwise no value is inferred.
4. The user must verify parsed or manually entered information before analysis.
5. Anonymous/demo cases are supported and contain no stored patient code/name.
6. Line charts are used only for actual historical time-series aggregates; a single prediction uses summary/table/category bars or columns.
7. The assistant remains local/offline-only and never receives patient/history data.
8. SQLite is the only approved database.
9. Existing stable packages/releases and existing prediction endpoints remain unchanged.
10. The production Knowledge Base remains the only runtime KB. Pending/development content is never loaded or surfaced.
11. No automatic history deletion/retention rule is approved in this design. Records are deleted only by explicit user action until a retention policy is approved.

## 6. Work breakdown: Tasks 8.2–8.9

| Task | Exact outcome | Principal paths | Required evidence / stop condition |
|---|---|---|---|
| **8.2 SQLite foundation and privacy configuration** | Add settings, app-data location, migrations v1, repository connection lifecycle, ignore/package exclusions, and migration/rollback runbook. No UI or history endpoints yet. | `core/config.py`, `core/lifespan.py`, `infrastructure/persistence/*`, tests, release docs | Idempotent temporary-DB migration tests; no DB in ZIP; explicit failure behavior. Stop if location/access policy is not approved. |
| **8.3 Case metadata and server-bound analysis** | Implement metadata schemas, approved parser, parse endpoint, and `POST /api/v1/analyses`; reuse the unchanged prediction pipeline and atomically store metadata/output/thumbnail. | `schemas/case_metadata.py`, `schemas/analysis.py`, `application/{filename_metadata_parser,analysis_service}.py`, `api/v1/analyses.py` | Exact-match parser, confirmation, anonymous, rollback/no-persist-on-failure, compatibility tests. Stop until naming regex is approved. |
| **8.4 History repository and APIs** | Implement list/filter/detail/thumbnail/delete/trend APIs with cursors and parameterized SQLite queries. | `application/history_service.py`, `api/v1/history.py`, `schemas/history.py`, repository tests | Pagination/filter, delete/404, injection/path traversal, concurrent-lock/error tests. |
| **8.5 Report v2** | Add server-bound report-v2 preview from an analysis ID; preserve legacy report v1. | `api/v1/report.py`, `schemas/report_v2.py`, `report_v2.html`, `report.css`, report tests | No arbitrary payload/HTML/image input; thumbnail, sources, disclaimer, anonymous behavior, repeated export, deleted-record 404. |
| **8.6 Compact analysis workspace and metadata gate** | Redesign only the current Jinja/vanilla page into the compact workspace; implement state machine, metadata confirmation, reset/stale-state guarantees, summary/table/category views. | `demo.html`, `demo.js`, `demo.css`, new workspace assets/templates | Browser/mobile/accessibility checks; original `/api/v1/predict` still passes unchanged tests. |
| **8.7 History interface and truthful visualizations** | Add history list/filter/detail/delete/report actions and aggregate trend view with table fallback. | `history_panel.html`, `history.js`, `history.css`, visualization assets | Empty/one-date/multi-date behavior, keyboard controls, deletion confirmation, no fabricated trend. |
| **8.8 Floating offline assistant widget** | Replace the full-width panel with accessible floating widget and controlled busy/typing indicator; retain service/API/safety/KB gate. | `assistant_widget.html`, `assistant_widget.js`, `assistant_widget.css`, assistant UI tests | No patient payload leak, only assistant endpoint, offline badge, reduced motion, focus/Escape and stale-context tests. |
| **8.9 Regression, privacy/migration hardening, and pre-release gate** | Run full regression, migration/back-up/restore drill, KB gate, Windows local-data test, report print/manual checks, accessibility/browser checks, and document release readiness. | all affected tests, validation reports, release plan | No packaging until all gates pass. This task does not overwrite the prior stable package. |

## 7. Release blockers and unresolved decisions

### Release blockers

> Current hygiene evidence: `git diff --check -- .` reports an existing trailing whitespace at `README.md:4`. TASK 8.1 did not modify that source README; it must be resolved by its owner before a clean release gate.

1. **P1 — filename convention approval:** no explicit approved pattern exists. TASK 8.3 must not parse patient data until the owner approves the proposed pattern or supplies a replacement.
2. **P1 — local PII access policy:** the current app has no accounts/roles. The owner must approve loopback-only/OS-user-only use or explicitly authorize a separate access-control scope. Non-loopback exposure with patient history is prohibited.
3. **P1 — production privacy content:** the current production KB has no approved `product.data_storage` item, while the development item remains pending. The assistant/UI privacy wording must be approved and production-published through governance, or the assistant must use a controlled non-KB technical policy statement approved by the owner; pending content cannot be copied.
4. **P1 — migration and backup evidence:** no SQLite upgrade/restore proof exists yet.
5. **P2 — retention/storage policy:** no retention, maximum size, or backup ownership policy exists. Automatic deletion is not permitted without approval.
6. **P2 — pre-existing release evidence:** current repository-level `git diff --check` has an existing parent-level trailing-whitespace issue in `../SUBMISSION_CHECKLIST.md:4`; this task does not alter it. Final package must also be re-tested on a clean Windows machine after Tasks 8.2–8.9.

### Unresolved decisions requiring approval before implementation

- Approve the proposed filename convention/regex, or provide the authoritative convention.
- Confirm whether local history is permitted only for the logged-in Windows user on a loopback-bound portable app, and define retention/backup ownership for patient metadata.

## 8. Verification performed for this audit

| Check | Result |
|---|---|
| Source, template, JS/CSS, tests, scripts, reports, workspace and artifact contract inspection | PASS — read-only audit completed. |
| Persistence/network scan of application runtime | PASS — no SQLite/ORM/database/history path or external AI client found; `requests`/`httpx` exist only as dependencies/tooling/tests, not an application AI integration. |
| Existing report/assistant state boundary review | PASS — both are currently non-persistent and client-context based as documented. |
| Production KB/review-gate inspection | PASS — production KB is version `1.0.0` with 21 items; 34 pending items remain excluded. |
| Tests/model/runtime/package execution | NOT RUN — no production code was changed in this audit-only task. Prior Task 08 evidence remains historical, not re-claimed as a TASK 8.1 test run. |

## 9. Recommended next action

Obtain written approval for the filename convention and the local PII/retention policy. Then begin **TASK 8.2 only**: SQLite configuration, migration foundation, privacy constraints, and focused tests. Do not start Task 09 packaging until Task 8.9 has passed its new persistence/privacy/pre-release gates.
