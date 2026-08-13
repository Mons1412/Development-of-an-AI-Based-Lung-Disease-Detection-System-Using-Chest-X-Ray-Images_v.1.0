# TASK 8.3 — Patient/Case Metadata, Persisted Analysis, and History API Report

**Status:** PASS for backend/API scope. No frontend redesign, report-v2 work, chart, floating assistant, model change, external API, or release package was implemented.

## 1. Implemented API contract

All history endpoints retain the existing API-key dependency when configured and add a loopback-host gate because local history can hold patient/case metadata. They return controlled errors without local paths, SQL errors, or submitted patient values.

| Endpoint | Request | Successful response | Key failure behavior |
|---|---|---|---|
| `POST /api/v1/analyses/parse-filename` | JSON `{filename}` | all-or-nothing parser output | `422` for malformed request; no inference or persistence |
| `POST /api/v1/analyses` | multipart `file`, patient/case fields | `201` persisted prediction with `analysis_id`, timestamps, case metadata and `{status:"persisted", persisted:true}` | `422` invalid/unconfirmed metadata; `400` invalid image; `503` inference/storage unavailable |
| `GET /api/v1/analyses` | `page`, `page_size`, `patient_query`, `predicted_label`, `date_from`, `date_to`, `sort_order` | bounded summaries and pagination totals | `422` invalid bounds/query; `503` local history unavailable |
| `GET /api/v1/analyses/{analysis_id}` | UUID path | persisted detail, safe relative thumbnail API URL | `404` missing UUID record |
| `GET /api/v1/analyses/{analysis_id}/thumbnail` | UUID path | controlled WebP/JPEG bytes with `nosniff` and `no-store` | `404` missing/unavailable thumbnail; no local path exposed |
| `DELETE /api/v1/analyses/{analysis_id}` | UUID path | `{status:"deleted", analysis_id}` | `404` missing record; thumbnail/database recovery follows Task 8.2 contract |

## 2. Filename convention and metadata rules

The direct TASK 8.3 requirement is treated as the approved successor to the pending TASK 8.1 proposal:

```text
<PATIENT_CODE>__<PATIENT_NAME>__<YYYYMMDD>.<jpg|jpeg|png>
BN001__NGUYEN_VAN_A__20260726.png
PT-0007__TRAN_THI_B__20260726.jpg
```

Implementation identifier: `patient_code__patient_name__yyyymmdd_v1`.

- Parser input is NFC-normalized, limited to 255 characters, requires a complete basename match, refuses path separators/drive components/control characters, validates date existence, and never returns partial patient data.
- Single underscores in the name become spaces; Vietnamese Unicode name characters are preserved where valid.
- Generic names such as `image_001.png`, invalid dates, triple separators, unsupported extensions, and traversal-looking input return `matched=false` with safe validation warnings.
- `patient_name_source=filename` is server-verified: parsed code and display name must equal submitted data and still require `patient_info_confirmed=true`.
- `patient_name_source=manual` permits an explicit user correction and is never overwritten by parser output.
- Anonymous/demo records require `patient_name_source=anonymous` and no code/name. Identified cases require valid code, valid display name, source, and confirmation.
- Patient code is bounded to 2–32 safe identifier characters; display name is bounded to 2–80 Unicode letters/marks/spaces/apostrophes/hyphens and rejects HTML/path/control characters.

## 3. Backward-compatibility decision

`POST /api/v1/predict` and `/predict` remain unchanged: they accept only the legacy file upload, return the existing `PredictionResponse`, do not require metadata, and do not persist a record.

`POST /api/v1/analyses` is the explicit new persisted workflow. It validates metadata before inference, validates the image through the existing model contract, runs unchanged preprocessing/prediction, creates a UUID/thumbnail, and commits history only after prediction succeeds.

If storage fails, the new endpoint returns a controlled `503 analysis_storage_unavailable` response and withholds the prediction response so the caller cannot mistake an unsaved analysis for a saved one. Thumbnail/database compensation remains owned by `AnalysisHistoryService`; no successful inference failure creates a record.

## 4. Privacy and security controls

- No original full-resolution image bytes are added to SQLite. Only Task 8.2's optimized UUID-named thumbnail derivative and sanitized filename metadata are stored.
- The assistant receives no metadata, filename, thumbnail, history row, or report content. It contributes only the already validated production Knowledge Base version to the stored record.
- New APIs are blocked when `Settings.host` is not loopback (`127.0.0.1`, `::1`, or `localhost`), since no account/role authorization exists for PII history.
- All history filters remain parameter-bound. `patient_query` is bounded and injection-shaped input is tested.
- Thumbnail access accepts only a UUID record lookup and a controlled relative derivative; static mounting/arbitrary filesystem paths are not used.
- A request-validation handler removes FastAPI's reflected `input` field from all `422` responses, preventing patient metadata from being echoed in validation errors.
- No patient name/code/filename is logged by new code at normal log level. SQLite and filesystem errors become generic API responses.

## 5. Files changed

### New TASK 8.3 files

- `src/lung_xray_api/application/filename_metadata_parser.py`
- `src/lung_xray_api/application/analysis_service.py`
- `src/lung_xray_api/schemas/case_metadata.py`
- `src/lung_xray_api/schemas/analyses.py`
- `src/lung_xray_api/api/v1/analyses.py`
- `tests/unit/test_filename_metadata_parser.py`
- `tests/integration/test_analysis_history_api.py`

### Existing files updated

- `src/lung_xray_api/application/prediction_service.py`
- `src/lung_xray_api/schemas/analysis_history.py`
- `src/lung_xray_api/infrastructure/persistence/{records.py,analysis_repository.py,thumbnail_store.py}`
- `src/lung_xray_api/api/{dependencies.py,v1/router.py}`
- `src/lung_xray_api/main.py`
- `tests/conftest.py`

## 6. Verification

| Command | Result |
|---|---|
| `& .venv\Scripts\python.exe -m pytest tests/unit/test_filename_metadata_parser.py tests/integration/test_analysis_history_api.py -q` | PASS — 12 passed; one pre-existing Starlette TestClient deprecation warning. |
| `& .venv\Scripts\python.exe -m compileall -q src tests scripts` | PASS. |
| `& .venv\Scripts\python.exe -m ruff check src tests scripts` | PASS — all checks passed. |
| `& .venv\Scripts\python.exe -m pyright` | PASS — 0 errors, 0 warnings, 0 informations. |
| `& .venv\Scripts\python.exe -m pytest -q` | PASS — 288 passed; one pre-existing Starlette TestClient deprecation warning. |
| OpenAPI in-memory inspection | PASS — `/api/v1/analyses`, `/parse-filename`, `/{analysis_id}`, and `/{analysis_id}/thumbnail` present. |
| `git diff --check` | NOT CLEAN because pre-existing whitespace remains at `README.md:4` and `../SUBMISSION_CHECKLIST.md:4`; this task did not alter those unrelated lines. |

The focused suite covers valid/invalid and Unicode filename parsing, manual override, anonymous mode, missing confirmation, HTML rejection, filename-source mismatch, successful thumbnail persistence, inference failure, storage failure, list/filter/date/pagination/sort/detail/delete/thumbnail, SQL-injection-shaped query, arbitrary identifier/path attempts, loopback-only access, and legacy prediction compatibility.

## 7. Remaining risks and required next boundary

1. There is no account/role model or at-rest encryption. The loopback gate is a containment control, not multi-user authorization; do not bind history APIs to a non-loopback interface without an approved access-control design.
2. Retention, backup ownership, and restore drill remain unresolved release gates. No automatic deletion policy was added.
3. The existing ignored `var/data/lung_xray_history.db` local file was not deleted because it is ambiguous local state. Packaging must prove that no database, WAL/SHM, or thumbnail files enter the release artifact.
4. No metadata UI, history UI, report-v2, thumbnail/report export UI, chart, or floating assistant work is included. Those belong to later tasks.
5. No clinical validation or medical diagnosis claim is made. All returned model output retains the existing academic/non-diagnostic disclaimer.

## 8. Recommended next action

Proceed to the separately approved UI/history task only after reviewing the loopback/retention/backup constraints above. Keep legacy prediction routes non-persistent and use `analysis_id` from the new API as the sole server-side identity for later history/report operations.
