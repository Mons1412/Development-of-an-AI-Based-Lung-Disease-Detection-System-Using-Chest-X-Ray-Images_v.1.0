# TASK 04 — Offline Assistant UI Integration Report

**Task status:** PASS for automated integration and regression checks. Browser visual approval remains manual.

## Scope completed

The offline assistant is integrated into the existing FastAPI/Jinja2 `/demo` page. It is a partial and two static assets served from the same application; no second application, client-side retrieval, external AI, API key, database, model change, PDF, or teacher UI was added.

The browser sends assistant questions only to `POST /api/v1/assistant/query`. The existing upload and `POST /api/v1/predict` flow remains intact.

## Files changed

| File | Change |
| --- | --- |
| `src/lung_xray_api/web/templates/demo.html` | Includes assistant CSS, Jinja partial, and assistant JavaScript after `demo.js` |
| `src/lung_xray_api/web/templates/assistant_panel.html` | New integrated panel markup |
| `src/lung_xray_api/web/static/demo.js` | Owns prediction-context lifecycle and rejects stale prediction responses |
| `src/lung_xray_api/web/static/assistant.js` | New offline chat client calling only the assistant API |
| `src/lung_xray_api/web/static/assistant.css` | New responsive panel styles using existing demo design tokens |
| `tests/integration/test_demo_ui.py` | Verifies panel and both assistant assets are served by `/demo` |
| `tests/unit/test_assistant_ui_contract.py` | Static contract checks for endpoint-only client behavior, safe rendering, and context lifecycle hooks |
| `PHASE3_IMPLEMENTATION_WORKSPACE/12_VALIDATION/TASK_04_ASSISTANT_UI_MANUAL_CHECKLIST.md` | Manual UI, lifecycle, accessibility, and screenshot approval checklist |

## UI state model

| Application stage | Global context | Suggestions |
| --- | --- | --- |
| `before_analysis` | Empty label/probabilities/version/time | Usage, formats, locked classes, MobileNetV2, privacy, limitations |
| `analysis_running` | Empty prediction fields | Before-analysis suggestions; assistant never receives an old prediction |
| `after_analysis` | Current prediction label, three probabilities, model version, processing time | Current result, probability, limitations, predicted-class information, choose another image |
| `analysis_failed` | Empty prediction fields | Before-analysis suggestions; backend cannot explain a stale result |

The panel contains the required title `Trợ lý thông tin X-quang phổi`, visible `Ngoại tuyến` badge, welcome message, suggestions, message log, textarea, send button, Enter-to-send/Shift+Enter newline behavior, loading state, controlled error state, source IDs, disclaimer, and `Cuộc trò chuyện mới` button.

`Cuộc trò chuyện mới` only clears the local transcript; it deliberately preserves the current valid prediction context. The existing prediction reset/remove/error controls own application-context reset.

## Prediction-context lifecycle

`demo.js` is the single owner of `window.lungXrayAssistantContext`.

- Initial load and reset: `before_analysis` with empty fields.
- New file selected: immediately clears any old context before client validation/rendering.
- Prediction submit: changes to `analysis_running` before the prediction request.
- Prediction success: replaces the global object with:

  ```javascript
  window.lungXrayAssistantContext = {
    stage: "after_analysis",
    predicted_label: result.prediction,
    probabilities: { ...result.probabilities },
    model_version: result.model_version,
    processing_time_ms: result.processing_time_ms
  };
  ```

- Prediction failure: `analysis_failed` with all prediction fields cleared.
- Remove, demo reset, preview error, and initial-state return: `before_analysis` with all prediction fields cleared.
- If a prediction response arrives after a new file selection/reset, its captured file is no longer current; the response is not rendered and cannot restore an old assistant context.

The assistant client sends `prediction_context` only at `after_analysis`; no image, base64 content, development Knowledge Base content, or retrieval logic is sent to/implemented by the client.

## Accessibility and safe rendering

- Message list uses `role="log"`, `aria-live="polite"`, and no automatic focus change after responses.
- Textarea has a real visually hidden label and explicit Enter/Shift+Enter guidance.
- Suggestions, buttons, and textarea have visible `:focus-visible` outlines.
- Offline/unavailable states use text as well as color.
- Loading is announced through `role="status"`; errors use `role="alert"`.
- Dynamic response text, source IDs, errors, and suggestions are rendered via DOM nodes and `textContent`; `assistant.js` has no `innerHTML` use.
- Layout collapses actions to a single column and limits bubble width on narrow screens; the existing reduced-motion rule continues to apply.

## Automated verification

| Command | Result |
| --- | --- |
| `node --check src/lung_xray_api/web/static/demo.js` | PASS |
| `node --check src/lung_xray_api/web/static/assistant.js` | PASS |
| `.venv\\Scripts\\python.exe -m pytest tests/integration/test_demo_ui.py tests/unit/test_assistant_ui_contract.py -q` | PASS — 5 passed; 1 existing TestClient deprecation warning |
| `.venv\\Scripts\\python.exe -m compileall -q src tests` | PASS |
| `.venv\\Scripts\\python.exe -m ruff check src tests` | PASS |
| `.venv\\Scripts\\python.exe -m pyright src tests` | PASS — 0 errors, 0 warnings |
| `.venv\\Scripts\\python.exe -m pytest -q` | PASS — 238 passed; 1 existing TestClient deprecation warning |

Existing prediction and offline assistant backend tests ran as part of the full suite and passed.

## Screenshots and manual approval still required

No real-browser screenshots were captured in this task. Manual approval is still required for desktop before/after analysis, mobile layout, endpoint-unavailable state, and keyboard focus visibility.

Use [TASK_04_ASSISTANT_UI_MANUAL_CHECKLIST.md](TASK_04_ASSISTANT_UI_MANUAL_CHECKLIST.md) to capture and approve that evidence. The checklist also includes the stale-response/network-throttling lifecycle scenario that static and API tests cannot prove visually.

## Remaining limitations

- The panel reflects the existing backend rule that clinical-review-pending content is not available. A suggestion about the predicted class can therefore receive a controlled out-of-scope response rather than clinical content.
- Browser visual behavior and screenshots are `NOT VERIFIED` until the manual checklist is completed.
- The installed TestClient/httpx deprecation warning remains dependency-level and does not fail the suite.
