# TASK 08 — Full Phase 3 Regression, Hardening, and Cleanup

**Date:** 2026-07-27  
**Task status:** Source regression and hardening checks pass. **No release package was created.**

## Scope outcome

This task reviewed the Phase 3 prediction, offline assistant, demo UI, teacher UI,
browser-print report, and evaluation tooling. It did not add a product feature, model,
database, external AI service, API key, dependency, or test image.

One evidenced hardening defect was corrected:

- `PredictionContext` previously allowed Pydantic coercion of `true`, numeric strings,
  and floating-point processing times. It now accepts only numeric (non-boolean)
  probability values and integer (non-boolean) processing times.
- Both assistant and report schemas now reject a `predicted_label` that does not match
  the production predictor's deterministic argmax order: `normal`, `pneumonia`,
  `tuberculosis`.
- Added unit/API/report regression coverage for these invalid client payloads.
- Removed the only in-scope trailing whitespace found by `git diff --check` in
  `src/lung_xray_api/infrastructure/ml/image_validator.py`.

## Validation results

| Area | Evidence | Result |
| --- | --- | --- |
| Prediction regression | 27 focused prediction/image/preprocessing tests; artifact verification; actual model warm-up; API smoke | PASS |
| Model contract | Artifact checksum, version `1.1.0`, class order `normal,pneumonia,tuberculosis`, input shape `[224, 224, 3]`, embedded preprocessing | PASS |
| Assistant and safety | 201 focused assistant/KB/API tests; 118 approved/pending/adversarial evaluation cases | PASS |
| Knowledge Base gate | Workspace validation; development build 55, production build 21, 34 pending clinical items excluded | PASS |
| UI and accessibility | Local Edge runtime: API readiness, assistant request, success state, focus-return for both dialogs, responsive 390 px layout, reset, no console/failed requests | PASS with manual visual approval remaining |
| Failure UI | Local Edge interception of a `503 model_not_ready` response: `analysis_failed` context and export/reference actions hidden | PASS |
| PDF preview | API tests, controlled-template review, local browser preview: branding, Vietnamese content, disclaimer, no image preview, `window.opener === null` | PASS with print-dialog check remaining |
| Evaluation tool | Mocked-inference tests cover folders, outputs, metrics, invalid files, empty dataset; no real labelled dataset supplied | PASS for tooling only |
| Security/privacy review | No external HTTP/AI client in application runtime; production KB item sources contain no Gemini source ID; no database/session/temp-file persistence path for assistant/report | PASS with provenance limitation below |
| Code quality | Full compile, Pyright, Ruff, JavaScript syntax, scoped diff check | PASS |

## Commands executed

```powershell
# Phase 3 workspace and Knowledge Base gates
.\.venv\Scripts\python.exe PHASE3_IMPLEMENTATION_WORKSPACE\12_VALIDATION\validate_workspace.py
.\.venv\Scripts\python.exe PHASE3_IMPLEMENTATION_WORKSPACE\01_KNOWLEDGE_BASE\tests\run_phase3_checks.py

# Focused regression suites
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assistant_knowledge_base.py tests\unit\test_assistant_service.py tests\unit\test_assistant_hardening.py tests\integration\test_assistant_api.py tests\integration\test_assistant_api_hardening.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_predict_api.py tests\unit\test_image_validator.py tests\unit\test_prediction_service.py tests\unit\test_predictor.py tests\unit\test_image_preprocessor.py -q
.\.venv\Scripts\python.exe -m pytest tests\integration\test_report_api.py tests\unit\test_report_ui_contract.py tests\unit\test_assistant_ui_contract.py tests\unit\test_teacher_ui_contract.py tests\integration\test_demo_ui.py tests\unit\test_evaluate_dataset.py -q
.\.venv\Scripts\python.exe -m pytest tests\unit\test_assistant_hardening.py tests\integration\test_assistant_api_hardening.py tests\integration\test_report_api.py -q

# Artifact, runtime, complete regression and static checks
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\verify_artifacts.py
.\.venv\Scripts\python.exe scripts\verify_portable_runtime.py
.\.venv\Scripts\python.exe scripts\smoke_api.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall src scripts tests
.\.venv\Scripts\python.exe -m pyright src scripts tests
.\.venv\Scripts\python.exe -m ruff check src scripts tests
node --check src\lung_xray_api\web\static\demo.js
node --check src\lung_xray_api\web\static\assistant.js
node --check src\lung_xray_api\web\static\report_export.js
git diff --check -- .
git diff --check
```

Additional source review covered external-client/secret patterns, unsafe HTML APIs,
production/development KB paths, route registration, persistence/write calls, and source
registry resolution. Local Edge was run at `http://127.0.0.1:8018/demo` against the
actual loaded model. A local logo PNG was used only to exercise the UI state machine; its
classification is not clinical or model-quality evidence.

## Test and check results

| Command/check | Result |
| --- | --- |
| Focused assistant/KB/API suite | PASS — 201 passed, 1 third-party deprecation warning |
| Focused prediction/validator/preprocessing suite | PASS — 27 passed, 1 third-party deprecation warning |
| Focused report/UI/evaluation suite | PASS — 22 passed, 1 third-party deprecation warning |
| Hardening regression suite after schema change | PASS — 195 passed, 1 third-party deprecation warning |
| Full `pytest -q` | PASS — **264 passed**, 1 `StarletteDeprecationWarning` from `TestClient/httpx` |
| `scripts/verify_artifacts.py` | PASS — 8/8 artifacts, checksum PASS |
| `scripts/verify_portable_runtime.py` | PASS — real model load and warm-up |
| `scripts/smoke_api.py` | PASS — `/health/live=200`, `/health/ready=200` |
| `compileall src scripts tests` | PASS |
| `pyright src scripts tests` | PASS — 0 errors, 0 warnings |
| `ruff check src scripts tests` | PASS |
| JavaScript syntax checks | PASS — `demo.js`, `assistant.js`, `report_export.js` |
| Workspace validator | PASS — 21 production KB items |
| Knowledge Base build/check | PASS — 55 development, 21 production, 34 pending, 118 evaluation cases |
| Scoped `git diff --check -- .` | PASS |
| Global `git diff --check` | FAIL — one pre-existing trailing whitespace in `../SUBMISSION_CHECKLIST.md:4`, outside `02_FASTAPI_INFERENCE` |

No test failed. The global diff-check failure is not hidden: it prevents a clean
repository-level release gate until the owner of the parent checklist resolves it.

## Security and privacy observations

- No Gemini, Google AI Studio, OpenAI, local LLM, external AI API, or external runtime
  network call is integrated. The production KB source registry retains seven pending
  historical source entries (including Gemini documentation), but no published production
  item references one; active runtime item source IDs were verified separately.
- `KNOWLEDGE_BASE_PATH` defaults only to
  `knowledge_base/compiled/knowledge_base.production.vi.json`; loader checks filename,
  `mode=production`, publication/review status, source IDs, and deprecated sources.
- Assistant DOM output uses `textContent`. Report input rejects unknown fields, sanitizes
  filenames, validates probabilities, constrains model metadata, and Jinja auto-escapes
  all supplied values. The popup receives only controlled server-rendered HTML.
- Uploaded image validation still enforces extension/MIME/magic-byte/Pillow decode/pixel
  limits. Original image data is not part of the report request or report preview.
- Assistant and report are in-memory request handling: no database, patient history,
  report ID, report file, image copy, cookie, or temporary report path is created.

## Code-quality and cleanup review

- No unused Phase 3 module was removed without proof. The legacy `/predict` alias remains
  intentionally because its compatibility test passes.
- No duplicate CSS/JS with shared ownership was found: `assistant.css` is panel-scoped,
  `report.css` applies to the separate print document, and `demo.css` owns the existing
  demo/teacher layout.
- The production runtime KB and rebuilt workspace KB have the same 21 item IDs, sources,
  and answer content. Their byte hashes differ only because `built_at` is regenerated and
  Windows emits `source_file` backslashes. This is a reproducibility/documentation debt,
  not an exposure of pending content.

## Coverage

`pytest-cov` is an optional development dependency, but no coverage configuration or
coverage acceptance threshold is configured in `pyproject.toml`; therefore no coverage
percentage is claimed.

## Unresolved risks and technical debt

1. The report endpoint validates a self-consistent client payload, but without a
   server-bound prediction token or persistence it cannot prove a direct HTTP request came
   from the current prediction. The demo UI enforces current-result lifecycle correctly,
   but this is not equivalent to a server-side provenance guarantee.
2. Assistant `prediction_context` is likewise untrusted client context by design. It is
   strictly shaped and non-clinical, but is not bound to a server session.
3. The browser-print approach cannot automatically prove the OS print dialog, selected
   printer, final PDF filename/location, or visual output after the user saves it.
4. No real, ground-truth-verified, training-disjoint evaluation dataset was supplied; no
   empirical accuracy, clinical validation, or patient-level claim is made.
5. The existing `StarletteDeprecationWarning` should be addressed through a separately
   approved dependency-compatibility task, not suppressed.

## Manual tests still required

1. Review desktop, tablet, and mobile Vietnamese copy/layout visually with the academic
   owner, including contrast and the final branding asset.
2. Use the native browser print dialog to save a report to PDF; verify Vietnamese glyphs,
   page breaks, content, and user-selected destination using
   `TASK_06_PDF_MANUAL_CHECKLIST.md`.
3. Confirm the spelling of the team member flagged in the approved workspace:
   `Võ Văn Nghĩa`.
4. Repeat an actual new-image selection after a success in the final human UI pass to
   confirm the old result, report/export action, reference dialog, and assistant context
   disappear before the next analysis.
5. Test the assembled portable Phase 3 package on a clean Windows machine; this task
   verified the source runtime only, not a rebuilt Phase 3 ZIP on a clean machine.
6. Before publishing model metrics, use a separately governed evaluation dataset with
   confirmed ground truth and reviewed training-set disjointness.

## Exact release blockers

| Priority | Blocker | Required resolution |
| --- | --- | --- |
| P1 | The strict claim that a report is only for a server-verified *current* prediction cannot be guaranteed for direct calls to `/api/v1/report/preview` without a server-bound provenance design. | Approve a future contract/security design (for example, short-lived server-issued prediction evidence) or explicitly scope the endpoint to trusted local-demo clients. |
| P1 | A clean Windows Phase 3 portable package has not been rebuilt and smoke-tested. | Rebuild the package and run the documented clean-machine smoke test in the release task. |
| P2 | Native Save-as-PDF and final visual/academic UI approval remain manual. | Complete the manual PDF checklist and human responsive/branding review. |
| P2 | Team-member spelling confirmation is pending. | Obtain owner confirmation or correct the approved source through its review process. |
| P3 | Repository-wide `git diff --check` fails at `../SUBMISSION_CHECKLIST.md:4`, outside this task directory. | Owner of that parent document removes the trailing whitespace; then rerun the repository-level check. |

Because these blockers remain, TASK 08 intentionally does **not** package or declare a
final Phase 3 release.
