# TASK 06 — PDF Report Export (current analysis only)

Ngày thực hiện: 2026-07-27  
Phạm vi: thêm report preview cho prediction hiện tại trong `/demo`, theo phương án browser
Print / Save as PDF đã được phê duyệt. Không tạo PDF binary ở backend.

## Architecture implemented

```text
Successful current prediction in browser
  -> report payload (filename + validated prediction context only)
  -> POST /api/v1/report/preview
  -> FastAPI validates and renders controlled HTML in memory
  -> browser popup displays preview
  -> user selects In / Lưu dưới dạng PDF
  -> browser/user owns optional saved PDF location
```

Không có database, report ID, file upload, image bytes/base64, temporary report file hoặc
server-side PDF file. The original image is intentionally omitted from the report to avoid
transmitting or retaining it outside the existing prediction request.

## Files changed

| Path | Purpose |
| --- | --- |
| `src/lung_xray_api/schemas/report.py` | Strict report-request validation, filename sanitizer, exact class/probability validation. |
| `src/lung_xray_api/api/v1/report.py` | In-memory controlled HTML report preview endpoint. |
| `src/lung_xray_api/api/v1/router.py` | Registers report router without changing existing routes. |
| `src/lung_xray_api/web/templates/report.html` | Escaped, print-optimized report template. |
| `src/lung_xray_api/web/static/report.css` | Vietnamese-friendly printable styling and responsive preview layout. |
| `src/lung_xray_api/web/static/report_export.js` | Opens popup synchronously, requests preview, renders controlled response, closes it on error. |
| `src/lung_xray_api/web/templates/demo.html` | Adds success-only `Xuất report PDF` action and report script. |
| `src/lung_xray_api/web/static/demo.js` | Builds payload from current success state, invalidates/aborts export on new image, reset, loading or failure. |
| `src/lung_xray_api/web/static/demo.css` | Allows result actions to wrap responsively. |
| `tests/integration/test_report_api.py` | Report API happy path, missing prediction, malicious input and repeated export coverage. |
| `tests/unit/test_report_ui_contract.py` | UI lifecycle/current-context/popup safety static contracts. |
| `tests/integration/test_demo_ui.py` | Verifies export UI/static assets are served. |
| `12_VALIDATION/TASK_06_PDF_MANUAL_CHECKLIST.md` | Manual visual and Save-as-PDF checklist. |

## API contract

| Item | Contract |
| --- | --- |
| Endpoint | `POST /api/v1/report/preview` |
| Authentication | Reuses existing `require_api_key` policy; remains local-open when API key protection is disabled. |
| Request | `filename` plus `prediction.{predicted_label, probabilities, model_version, processing_time_ms, analysis_timestamp}`. |
| Validation | Unknown fields rejected; filename is basename-only and control/unsafe characters are removed; class labels are fixed; probabilities must contain exactly three classes, be finite in `[0,1]`, and sum to `1 ± 1e-6`; model version is constrained; timestamp must be timezone-aware. |
| Success | `200 text/html`; no report ID, cookie, file path or persistent object is returned. |
| Invalid request | `422` from the schema boundary. |
| Unauthorized request | Existing `401` behavior when API key protection is enabled. |

The server defines Vietnamese class labels, disclaimer, production-safe reference notice, source IDs and
team information. The client cannot supply these as report content. Jinja auto-escapes template values;
there is no `safe` rendering path.

## Report contents

- Project name and NTTU branding.
- Analysis date/time captured when the current successful result is rendered.
- Sanitized original filename; image content is intentionally not attached.
- Vietnamese predicted class and original API label.
- All three output probabilities in fixed class order.
- Model version and processing time.
- Production-safe reference status: `Nội dung chuyên môn đang chờ duyệt`.
- Source references: `MODEL_ARTIFACT_1_1_0` and `PROJECT_SOURCE_V1_0_0`.
- Academic/medical disclaimer and approved team information.

## Safeguards and state lifecycle

| Scenario | Behavior |
| --- | --- |
| Before a successful prediction | Export button is hidden and disabled. |
| Success | Browser creates a single payload from `state.latestResult` and the selected file name only. |
| New image, reset, loading, failure | `clearCurrentPrediction()` / `showResultState()` hides export and aborts any in-flight preview request. |
| Popup blocked | User receives an actionable toast; no partial popup remains. |
| Repeated export | Each click requests a fresh in-memory preview; no server-side state is reused. |
| Malicious filename/content | Filename is sanitized; unapproved report fields and invalid model metadata are rejected with `422`. |

## Verification

| Check | Result |
| --- | --- |
| Focused report/UI tests | PASS — 10 passed, 1 existing Starlette/httpx deprecation warning |
| Full `pytest -q` | PASS — 250 passed, 1 existing Starlette/httpx deprecation warning |
| `python -m compileall src scripts tests` | PASS |
| `python -m pyright src scripts tests` | PASS — 0 errors, 0 warnings, 0 informations |
| `python -m ruff check src scripts tests` | PASS |
| `node --check` for `demo.js` and `report_export.js` | PASS |
| Edge headless local flow at `http://127.0.0.1:8008/demo` | PASS — pre-prediction export hidden; actual success preview contained branding/logo/Vietnamese/probabilities/gate/sources; popup had `window.opener === null`; two exports created two independent previews; reset and injected failed prediction hid export. |

The only console error in that browser run was the expected HTTP `503` from the deliberately intercepted
prediction request used to prove the failed-analysis state. There were no failed network requests.

## Manual visual checklist

Use [TASK_06_PDF_MANUAL_CHECKLIST.md](TASK_06_PDF_MANUAL_CHECKLIST.md) for a reviewer to verify the
native browser print dialog and the user-selected Save-as-PDF result. This final step is manual because
the Windows printer dialog and the user's destination cannot be asserted safely by automated browser tests.

## Limitations / remaining approval

1. This is a print-preview export, not a direct backend binary-PDF stream. It was selected by the approved
   workspace to avoid an additional binary PDF engine/font dependency and to preserve Vietnamese rendering
   through the installed browser. The browser/user controls any saved PDF location.
2. No clinical reference text is published because production Knowledge Base has no approved clinical item.
   The report deliberately states the clinical-review gate instead of using development/pending content.
3. Without persistence or a signed prediction token, the server validates the shape and safety of the
   current browser context but cannot independently prove that a well-formed direct HTTP request originated
   from a previous prediction. The demo UI itself only enables export for its current success state.
4. Confirm the spelling of `Vô Văn Nghĩa` before release; it is rendered exactly as the approved workspace
   `team.json`, which marks it for confirmation.
