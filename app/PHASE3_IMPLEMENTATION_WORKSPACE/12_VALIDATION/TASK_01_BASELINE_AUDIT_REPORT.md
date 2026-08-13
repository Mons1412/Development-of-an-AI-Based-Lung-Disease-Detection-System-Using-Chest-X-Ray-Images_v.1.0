# TASK 01 — Baseline Audit Report

**Audit date:** 2026-07-26  
**Scope:** `02_fastapi_inference` current working tree only. No application source, model artifact, UI, dependency, database, or external AI integration was changed.

## 1. Files inspected

### Phase 3 planning workspace

- `PHASE3_IMPLEMENTATION_WORKSPACE/README_FIRST.md`
- Every Markdown file in `00_START_HERE/`.
- Every work order in `10_CODEX_WORK_ORDERS/` (`README.md`, `TASK_01` through `TASK_09`).
- Assistant backend/UI design and integration-change notes required to establish target paths.
- PDF export architecture and candidates, model-evaluation runbook/script, and dependency-decision note.

### Current application and artifacts

- `.env.example`, `pyproject.toml`, `requirements-lock.txt`, and `README.md`.
- All Python modules under `src/lung_xray_api/`, including app factory, API routes, dependencies, application service, settings/lifespan/security, ML infrastructure, and schemas.
- `artifacts/lung_classifier/1.1.0/{model_metadata,inference_contract,preprocessing_config,class_indices}.json` (read only).
- Demo files: `src/lung_xray_api/web/templates/demo.html`, `web/static/demo.js`, `web/static/demo.css`, and the static-asset inventory.
- All current test files under `tests/` and all current scripts under `scripts/`.

## 2. Current architecture

`src/lung_xray_api/main.py:create_app()` is the FastAPI application factory; the module-level `app = create_app()` is the Uvicorn import target. It configures logging, mounts `/static`, registers the composed v1 router, supplies `/`, and maps `ImageValidationError` to HTTP 400 and artifact/runtime errors to HTTP 503.

`src/lung_xray_api/api/v1/router.py` composes, in order, `health.router`, `model_info.router`, `predict.router`, and `demo.router`. There is no assistant or report router in the current application.

`src/lung_xray_api/core/lifespan.py:create_lifespan()` is the startup/shutdown composition root. When model loading is enabled it calls `build_prediction_service()` once, stores `prediction_service`, `model_ready`, and `settings` on `app.state`, then closes only the `ModelRuntime` at shutdown. `build_prediction_service()` composes:

```text
ArtifactBundle (checksums + contract)
  -> ModelRuntime (load once + optional warm-up)
  -> ImageValidator + ImagePreprocessor + Predictor
  -> PredictionService
```

Runtime settings are loaded by `src/lung_xray_api/core/config.py:load_settings()`. The active names are `HOST`, `PORT`, `ARTIFACT_DIR`, `MAX_UPLOAD_MB`, `API_KEY_ENABLED`, `API_KEY`, `APP_ENV`, and `LOG_LEVEL`. `.env.example` also retains the compatibility aliases `APP_HOST`, `APP_PORT`, and `MODEL_DIR`; the current settings implementation reads the non-`APP_` host/port and `ARTIFACT_DIR` values.

The project is a Python 3.12 `src`-layout package. `pyproject.toml` declares FastAPI, Uvicorn, Pydantic, NumPy, Pillow, TensorFlow, and Keras; pytest, httpx, pyright, and ruff are supported development dependencies. No database library or persistence layer is present.

## 3. Current prediction sequence

1. `POST /api/v1/predict` is implemented in `api/v1/predict.py:predict`; `POST /predict` is a compatibility alias. Both require multipart field `file`, use the optional API-key dependency, read the upload bytes, and run `PredictionService.predict_bytes()` in FastAPI's threadpool.
2. `ImageValidator.validate()` enforces non-empty content, a configured 10 MiB maximum by default, optional filename extension (`.jpg`, `.jpeg`, `.png`), standard JPEG/PNG MIME or neutral `application/octet-stream`, magic bytes, extension/MIME agreement, Pillow `verify()`, full decode, positive dimensions, and a 20,000,000-pixel safety limit.
3. `ImagePreprocessor.preprocess()` decodes the validated image, converts it to RGB, resizes with bilinear interpolation to 224 × 224, converts to `float32`, and adds a batch dimension. The exact tensor input to the runtime is `(1, 224, 224, 3)`, `float32`, with raw pixel values in `[0, 255]`. It must not normalize again because the model embeds `Rescaling(scale=1/127.5, offset=-1)`.
4. `ModelRuntime` loads `artifacts/lung_classifier/1.1.0/lung_classifier_v1.keras` with `compile=False` (and `safe_mode=True` when supported), warms it with zeros shaped `(1, 224, 224, 3)`, and invokes it with `training=False`.
5. `Predictor` requires a finite `(1, 3)` output whose values are in `[0, 1]` and sum to approximately 1. The locked class/probability order is exactly `normal`, `pneumonia`, `tuberculosis`; it comes from `class_indices.json` and is independently checked against `model_metadata.json` and `inference_contract.json` by `ArtifactBundle.validate_contract()`.
6. `PredictionService` measures latency and returns `PredictionResult`. `PredictionResponse` exposes `status`, `prediction`, `model_probability`, nested `probabilities`, all three flattened probability fields, `model_version`, `processing_time_ms`, and `disclaimer`.

The model version source is `model_metadata.json:model_version`; `ArtifactBundle` rejects any value other than `1.1.0`. Current artifact verification reported version `1.1.0`, input `[224, 224, 3]`, and the same three-class order.

## 4. Current demo UI structure

- Template: `src/lung_xray_api/web/templates/demo.html`, rendered by `GET /demo` in `api/v1/demo.py`.
- JavaScript: `src/lung_xray_api/web/static/demo.js`.
- CSS: `src/lung_xray_api/web/static/demo.css` (responsive desktop/tablet/mobile layout, upload/result states, probability bars, focus/reduced-motion styles).
- Assets: `/static/assets/{favicon.svg,lungs-hero.svg,lungs-result.svg}`; `/static` is mounted by the app factory.

The template contains a two-panel UI: upload/preview controls in `#prediction-form` and the result states `#result-empty`, `#result-loading`, `#result-error`, and `#result-success`. JavaScript keeps only browser-local state (`selectedFile`, preview object URL, request controller, timers, and `rawPayload`). It checks readiness/model-info on page load and sends `FormData` to `/api/v1/predict`.

On a successful response, `normalizePredictionPayload()` validates the three probabilities and the predicted class. `renderPrediction()` writes the label, model probability, model version, processing time, disclaimer, raw JSON, and the three width-animated probability bars, then exposes `#result-success`. The API response—not a second model call—is the sole source for the rendered result.

`resetDemo()` is used by **Chọn lại**, remove-file, and error-reset controls. It aborts an in-flight request, stops timers, revokes the preview URL, clears selected file/native input/raw payload/raw JSON/bars, hides the preview, restores the empty result state, and rechecks API health.

Selecting a valid new file through the input/drop zone instead calls `handleFileSelection()` and `renderImagePreview()`. It replaces the file and preview and hides the visible result with `showResultState("empty")`, but it does **not** call `resetDemo()` or clear `state.rawPayload`, the raw JSON DOM value, prior probability-bar values, or the disclaimer. Those values are hidden at that moment, but this is an important state-boundary difference for the planned assistant context.

## 5. Existing test and execution results

All commands below were run with `.venv\\Scripts\\python.exe` (Python 3.12.10) against the current working tree.

| Command | Result |
| --- | --- |
| `python -m pip check` | PASS — `No broken requirements found.` |
| `python scripts/verify_artifacts.py` | PASS — 8/8 required artifact files, checksum PASS, version `1.1.0`, input `[224, 224, 3]`, class order confirmed. |
| `python -m compileall src scripts tests` | PASS — exit code 0. |
| `python -m pytest -q` | PASS — `34 passed, 1 warning in 0.81s`. |
| `python -m pyright src scripts tests` | PASS — `0 errors, 0 warnings, 0 informations`. |
| `python -m ruff check src scripts tests` | PASS — `All checks passed!` |

The pytest warning is a `StarletteDeprecationWarning` from installed `fastapi.testclient` regarding its httpx-based TestClient; it did not fail the suite.

Test coverage includes artifact contracts/checksums, validation rules, preprocessing shape, predictor output invariants, service behavior using fakes, HTTP routes using `FakePredictionService`, and demo route/static-asset availability. It does **not** prove a current real TensorFlow prediction or browser E2E interaction: `scripts/smoke_model.py` requires a valid local X-ray input and no browser automation was run in this audit.

## 6. Exact Phase 3 target path mapping

All destinations below are absent from the current source tree unless identified as an existing file to modify.

| Planned capability | Workspace source | Exact target in this repository | Integration status |
| --- | --- | --- | --- |
| Offline assistant package | `02_ASSISTANT_BACKEND/ready_to_merge/src/lung_xray_api/assistant/` | `src/lung_xray_api/assistant/` | New package; includes `knowledge_base.py`, `retriever.py`, `safety.py`, `service.py`, and optional `gemini_client.py`. |
| Assistant API route | `.../api/v1/assistant.py` | `src/lung_xray_api/api/v1/assistant.py` | New route; then controlled edit to existing `src/lung_xray_api/api/v1/router.py` to include it. |
| Assistant schemas | `.../schemas/assistant.py` | `src/lung_xray_api/schemas/assistant.py` | New schema module. |
| Assistant lifecycle/config | integration notes | Existing `src/lung_xray_api/core/lifespan.py` and `core/config.py` | Controlled diff only; create one service at startup and preserve prediction startup if KB is unavailable. |
| Assistant UI components | `03_ASSISTANT_UI/ready_to_merge/.../{assistant_panel.html,assistant.js,assistant.css}` | `src/lung_xray_api/web/templates/assistant_panel.html`; `src/lung_xray_api/web/static/assistant.js`; `src/lung_xray_api/web/static/assistant.css` | New component files. |
| Assistant UI integration | `03_ASSISTANT_UI/integration_changes/` | Existing `web/templates/demo.html`, `web/static/demo.js`, `web/static/demo.css` | Controlled diff only; do not replace demo files. |
| Knowledge Base runtime JSON | `01_KNOWLEDGE_BASE/compiled/knowledge_base.production.vi.json` | `knowledge_base/compiled/knowledge_base.production.vi.json` | New root-level runtime data. Development JSON must not be the release runtime. |
| PDF/report endpoint (no separate service class is planned) | `04_TEACHER_UI_REQUIREMENTS/pdf_export/ready_to_merge/.../api/v1/report.py` | `src/lung_xray_api/api/v1/report.py` | New report-preview route; then controlled edit to existing `api/v1/router.py`. |
| PDF/report schema and browser assets | corresponding `schemas/report.py`, `web/templates/report.html`, `web/static/{report.css,report_export.js}` | `src/lung_xray_api/schemas/report.py`, `web/templates/report.html`, `web/static/report.css`, `web/static/report_export.js` | New files; preview HTML is printed/saved by browser and is not server-persisted. |
| Evaluation script | `05_MODEL_EVALUATION/scripts/evaluate_dataset.py` | `scripts/evaluate_dataset.py` | New script; expected outputs are supplied by its caller, not model artifacts. |

## 7. Potential merge conflicts

1. **High — current demo files are already modified.** `web/templates/demo.html`, `web/static/demo.js`, and `web/static/demo.css` have uncommitted changes and are the exact three existing files Task 04 must edit. The assistant UI candidate must be merged as a small, reviewed diff; copying its partial files or replacing the current demo files would lose Phase 02 behavior and user work.
2. **Medium — shared router/lifespan/config composition points.** Tasks 03 and 07 both need router composition; Task 03 also needs lifespan/config changes. Current `router.py`, `lifespan.py`, and `config.py` are clean, but each is a central merge point and must retain the current prediction route/lifecycle semantics.
3. **Medium — UI state contract is not presently centralized.** The current new-file path hides the old result without clearing all browser-local result data. Task 04's required `lungXrayPredictionContext` must be cleared on select, remove, reset, and failure, not only on the full reset path.
4. **Medium — configuration naming must remain backward compatible.** `.env.example` intentionally carries both newer-looking `APP_HOST`/`APP_PORT`/`MODEL_DIR` names and currently-read `HOST`/`PORT`/`ARTIFACT_DIR` names. Future KB/Gemini settings must not silently redirect the model artifact path or remove the active values.
5. **Low — existing whitespace debt.** Initial `git diff --check` reported trailing whitespace in the already-modified `src/lung_xray_api/infrastructure/ml/image_validator.py` and parent `SUBMISSION_CHECKLIST.md`. It is outside TASK 01 and was not changed.

## 8. Risks and unresolved questions

- **Not a TASK 01 blocker:** the application source plus UI/tests are already dirty before this audit. Git's actual repository root is the parent `Lung_Xray_AI_Graduation_Project`, not this subdirectory; any future commit/rollback point must be created from that root and must preserve unrelated parent-level changes.
- **Not verified:** a real model inference/warm-up in this working tree. Artifact contract and checksum are verified, but no valid local X-ray fixture was provided for `smoke_model.py`.
- **Not verified:** real browser behavior, including drag/drop, reset while a request is in flight, popup-blocked PDF handling, responsive UI, or future assistant context transitions. Current integration tests only verify the demo route and static files through TestClient.
- **Design gate:** the Phase 3 workspace says clinical content must not be published before review approval. TASK 02 must establish this gate before any assistant is enabled.
- **Rollback point:** no new tag, commit, or branch was created because TASK 01 is audit-only and the working tree is already dirty. Creating one requires explicit approval and a decision about what pre-existing work belongs in it.

## 9. Recommended next action

Obtain approval to start **TASK 02 — Knowledge Base Gate** only after preserving the current dirty worktree in an agreed rollback point. TASK 02 should copy the knowledge-base directory, run its supplied checks, and confirm that only the production JSON is eligible for runtime use; it must not enable the assistant or modify the demo UI.

## Audit change record

- Created: this report only, at `PHASE3_IMPLEMENTATION_WORKSPACE/12_VALIDATION/TASK_01_BASELINE_AUDIT_REPORT.md`.
- Modified application source/model artifacts/UI/dependencies: none.
- Blocking issues for completing TASK 01: none. The dirty worktree and missing real-model/browser evidence are documented gates for later work, not failures of this audit.
